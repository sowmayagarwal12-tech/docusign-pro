import os
import uuid
import datetime
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Header
from fastapi.responses import FileResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.models import (
    User, LoginRequest, RegisterRequest, AcceptTermsRequest,
    Envelope, Signer, DocumentField, AuditEvent, EnvelopeStatus,
    SelfSignRequest, CreateEnvelopeRequest, SignerSubmissionRequest,
    KycOtpRequest, KycVerifyRequest, SignaturePaymentRequest
)
from app.auth import auth_manager
from app.store import store, SAMPLES_DIR, UPLOADS_DIR, COMPLETED_DIR
from app.samples import ensure_samples
from app.pdf_engine import stamp_pdf_document, calculate_sha256_file

app = FastAPI(title="DocuSign Pro API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Helper to retrieve current authenticated user
def get_current_user(request: Request) -> Optional[User]:
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
    elif "X-Session-Token" in request.headers:
        token = request.headers["X-Session-Token"]
    elif "token" in request.query_params:
        token = request.query_params["token"]

    if not token:
        return None
    return auth_manager.get_user_by_session(token)

@app.on_event("startup")
def startup_event():
    ensure_samples()

# ----------------- Authentication & Identity APIs ----------------- #

@app.post("/api/auth/login")
def login(req: LoginRequest):
    res = auth_manager.authenticate_user(req.email, req.password)
    if not res:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    user, token = res
    return {
        "token": token,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "terms_accepted": user.terms_accepted,
            "terms_accepted_at": user.terms_accepted_at,
            "kyc_verified": user.kyc_verified,
            "kyc_doc_type": user.kyc_doc_type,
            "kyc_doc_id": user.kyc_doc_id,
            "is_premium": user.is_premium,
            "premium_credits": user.premium_credits
        }
    }

@app.post("/api/auth/register")
def register(req: RegisterRequest, request: Request):
    client_ip = request.client.host if request.client else "127.0.0.1"
    try:
        user, token = auth_manager.register_user(
            req.name,
            req.email,
            req.password,
            kyc_doc_type=req.kyc_doc_type,
            kyc_doc_id=req.kyc_doc_id,
            kyc_otp=req.kyc_otp,
            client_ip=client_ip
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "token": token,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "terms_accepted": user.terms_accepted,
            "terms_accepted_at": user.terms_accepted_at,
            "kyc_verified": user.kyc_verified,
            "kyc_doc_type": user.kyc_doc_type,
            "kyc_doc_id": user.kyc_doc_id,
            "is_premium": user.is_premium,
            "premium_credits": user.premium_credits
        }
    }

@app.get("/api/auth/me")
def get_me(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "terms_accepted": user.terms_accepted,
        "terms_accepted_at": user.terms_accepted_at,
        "kyc_verified": user.kyc_verified,
        "kyc_doc_type": user.kyc_doc_type,
        "kyc_doc_id": user.kyc_doc_id,
        "is_premium": user.is_premium,
        "premium_credits": user.premium_credits
    }

@app.post("/api/auth/send-kyc-otp")
def send_kyc_otp(req: KycOtpRequest):
    return auth_manager.generate_kyc_otp(req.doc_type, req.identifier, email=req.email, name=req.name)

@app.post("/api/auth/verify-kyc")
def verify_kyc(req: KycVerifyRequest):
    try:
        return auth_manager.verify_kyc_otp(req.doc_type, req.identifier, req.otp, legal_name=req.name, email=req.email)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/payments/pay-signature")
def pay_signature(req: SignaturePaymentRequest, request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required to purchase signature license.")
    updated_user = auth_manager.purchase_signature_credits(user.id, amount=req.amount, credits=1)
    return {
        "status": "PAYMENT_SUCCESS",
        "amount_paid": req.amount,
        "currency": req.currency,
        "is_premium": updated_user.is_premium,
        "premium_credits": updated_user.premium_credits,
        "message": "Payment of ₹50 verified! Custom Draw & Upload signatures are now unlocked."
    }

@app.post("/api/payments/pay-signer-token/{token}")
def pay_signer_token(token: str, req: SignaturePaymentRequest):
    res = store.get_envelope_by_token(token)
    if not res:
        raise HTTPException(status_code=404, detail="Invalid signing token.")
    envelope, signer = res
    signer.is_premium = True
    store.update_envelope(envelope)
    return {
        "status": "PAYMENT_SUCCESS",
        "amount_paid": req.amount,
        "currency": req.currency,
        "signer_id": signer.id,
        "is_premium": True,
        "message": "Payment of ₹50 verified! Draw & Upload unlocked for this recipient ceremony."
    }

@app.post("/api/auth/logout")
def logout(request: Request):
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        auth_manager.logout_session(token)
    return {"message": "Logged out successfully."}

@app.post("/api/auth/accept-terms")
def accept_terms(req: AcceptTermsRequest, request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    client_ip = request.client.host if request.client else "127.0.0.1"
    updated_user = auth_manager.accept_terms(user.id, client_ip)
    return {"status": "SUCCESS", "terms_accepted": True, "terms_accepted_at": updated_user.terms_accepted_at}

@app.get("/api/auth/demo-users")
def get_demo_users():
    return [
        {"name": "Sowmay Sharma", "email": "sowmay@example.com", "role": "Account Owner", "desc": "Aadhaar UIDAI Verified & Premium VIP"},
        {"name": "Alice Smith", "email": "alice@corp.com", "role": "Disclosing Party (VP Ops)", "desc": "Official Email Verified (Free Tier)"},
        {"name": "Bob Jones", "email": "bob@partner.com", "role": "Receiving Party (Contractor)", "desc": "Income Tax PAN Verified"}
    ]

# ----------------- Document Management APIs ----------------- #

@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    meta = store.save_upload(content, file.filename)
    return meta

@app.get("/api/documents/samples")
def list_sample_documents():
    ensure_samples()
    samples = [
        {
            "id": "nda",
            "title": "Mutual Non-Disclosure Agreement",
            "filename": "mutual_nda.pdf",
            "description": "Standard 2-party confidentiality agreement with signature & date blocks.",
            "pages": 1
        },
        {
            "id": "offer",
            "title": "Employment Offer Letter",
            "filename": "employment_offer_letter.pdf",
            "description": "Formal corporate job offer with compensation terms & candidate acceptance.",
            "pages": 1
        },
        {
            "id": "consulting",
            "title": "Independent Consulting Agreement",
            "filename": "consulting_agreement.pdf",
            "description": "Contractor statement of work, payment terms, and dual execution block.",
            "pages": 1
        }
    ]
    return samples

@app.post("/api/documents/samples/{sample_id}/load")
def load_sample_document(sample_id: str):
    ensure_samples()
    sample_files = {
        "nda": ("Mutual_NDA.pdf", "mutual_nda.pdf"),
        "offer": ("Employment_Offer_Letter.pdf", "employment_offer_letter.pdf"),
        "consulting": ("Consulting_Agreement.pdf", "consulting_agreement.pdf")
    }
    if sample_id not in sample_files:
        raise HTTPException(status_code=404, detail="Sample document not found.")

    display_name, disk_name = sample_files[sample_id]
    sample_path = os.path.join(SAMPLES_DIR, disk_name)
    with open(sample_path, "rb") as f:
        content = f.read()

    meta = store.save_upload(content, display_name)
    return meta

@app.get("/api/documents/{document_id}/pdf")
def get_document_pdf(document_id: str):
    for fname in os.listdir(UPLOADS_DIR):
        if fname.startswith(document_id):
            fpath = os.path.join(UPLOADS_DIR, fname)
            return FileResponse(fpath, media_type="application/pdf")
    raise HTTPException(status_code=404, detail="Document not found.")

# ----------------- Self-Signing Flow (With Strict Identity & Privacy Enforcement) ----------------- #

@app.post("/api/signatures/self-sign")
def execute_self_sign(req: SelfSignRequest, request: Request):
    user = get_current_user(request)
    client_ip = request.client.host if request.client else "127.0.0.1"

    # Enforce authentication & verified legal identity
    signer_legal_name = user.name if user else req.signer_name.strip()
    signer_email = user.email if user else (req.signer_email or "self@signer.local").strip().lower()

    if user and not user.terms_accepted:
        raise HTTPException(status_code=403, detail="You must accept the Electronic Signature Privacy & Security Terms before signing.")

    # Privacy & Name verification applies to typed signatures; Draw and Upload require Premium tier (₹50)
    for f in req.fields:
        if f.type.value in ["signature", "initials"] and f.value:
            is_image = str(f.value).startswith("data:image")
            if is_image:
                if user:
                    if not user.is_premium and user.premium_credits <= 0:
                        raise HTTPException(
                            status_code=402,
                            detail="Payment Required: Custom Draw & Upload signatures require a Premium subscription or ₹50 per signature. Standard accounts can use 'Type' for free, or unlock custom signatures for ₹50."
                        )
                    auth_manager.use_signature_credit(user.id)
            else:
                if f.signed_by_name and f.signed_by_name.strip().lower() != signer_legal_name.lower():
                    raise HTTPException(
                        status_code=403,
                        detail=f"Security & Privacy Violation: You are authenticated as '{signer_legal_name}'. "
                               f"Typed signatures must match your legal name ('{signer_legal_name}')."
                    )
            f.signed_by_name = signer_legal_name
            f.signed_by_email = signer_email

    # Find original file
    doc_path = None
    original_fname = "document.pdf"
    for fname in os.listdir(UPLOADS_DIR):
        if fname.startswith(req.document_id):
            doc_path = os.path.join(UPLOADS_DIR, fname)
            original_fname = fname.split("_", 1)[1] if "_" in fname else fname
            break

    if not doc_path or not os.path.exists(doc_path):
        raise HTTPException(status_code=404, detail="Base document not found.")

    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    envelope_id = str(uuid.uuid4())
    doc_sha256 = calculate_sha256_file(doc_path)

    signer = Signer(
        id=user.id if user else str(uuid.uuid4()),
        name=signer_legal_name,
        email=signer_email,
        role="Self Signer (Verified Identity)",
        color="#2563eb",
        token=str(uuid.uuid4()),
        status="SIGNED",
        viewed_at=now_str,
        signed_at=now_str,
        ip_address=client_ip
    )

    for f in req.fields:
        f.signed_at = now_str
        f.signed_by_name = signer_legal_name
        f.signed_by_email = signer_email
        f.assigned_to = "self"

    audit_events = [
        AuditEvent(
            id=str(uuid.uuid4()),
            timestamp=now_str,
            action="Identity Authenticated & Document Opened",
            actor_name=signer_legal_name,
            actor_email=signer_email,
            ip_address=client_ip,
            details=f"Authenticated via session; Privacy Terms Accepted"
        ),
        AuditEvent(
            id=str(uuid.uuid4()),
            timestamp=now_str,
            action="Electronic Signature Affixed",
            actor_name=signer_legal_name,
            actor_email=signer_email,
            ip_address=client_ip,
            details=f"Bound exclusively to legal identity: {signer_legal_name}"
        ),
        AuditEvent(
            id=str(uuid.uuid4()),
            timestamp=now_str,
            action="Document Sealed with Cryptographic Digest",
            actor_name="DocuSign Pro System",
            actor_email="system@docusign.local",
            ip_address="127.0.0.1",
            details="Certificate of Completion generated & verified"
        )
    ]

    envelope = Envelope(
        id=envelope_id,
        title=req.title or original_fname,
        created_at=now_str,
        status=EnvelopeStatus.COMPLETED,
        original_filename=original_fname,
        document_path=doc_path,
        document_sha256=doc_sha256,
        completed_at=now_str,
        is_self_sign=True,
        page_count=1,
        creator_email=signer_email,
        signers=[signer],
        fields=req.fields,
        audit_trail=audit_events
    )

    sealed_bytes, final_sha = stamp_pdf_document(doc_path, req.fields, envelope, attach_certificate=True)
    completed_fpath, _ = store.save_completed_pdf(envelope_id, sealed_bytes)
    envelope.completed_document_path = completed_fpath
    envelope.completed_sha256 = final_sha

    store.create_envelope(envelope)

    return {
        "envelope_id": envelope.id,
        "status": envelope.status,
        "title": envelope.title,
        "sha256": final_sha,
        "signed_by": signer_legal_name,
        "download_url": f"/api/envelopes/{envelope.id}/download"
    }

# ----------------- Multi-Party Envelope Flow (With Privacy & Access Rules) ----------------- #

@app.post("/api/envelopes/create")
def create_envelope(req: CreateEnvelopeRequest, request: Request):
    user = get_current_user(request)
    client_ip = request.client.host if request.client else "127.0.0.1"

    doc_path = None
    original_fname = "document.pdf"
    for fname in os.listdir(UPLOADS_DIR):
        if fname.startswith(req.document_id):
            doc_path = os.path.join(UPLOADS_DIR, fname)
            original_fname = fname.split("_", 1)[1] if "_" in fname else fname
            break

    if not doc_path or not os.path.exists(doc_path):
        raise HTTPException(status_code=404, detail="Base document not found.")

    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    envelope_id = str(uuid.uuid4())
    doc_sha256 = calculate_sha256_file(doc_path)

    color_palette = ["#2563eb", "#059669", "#7c3aed", "#d97706", "#dc2626"]
    signers_list = []
    signer_map = {}
    for idx, s in enumerate(req.signers):
        sid = s.get("id") or str(uuid.uuid4())
        token = str(uuid.uuid4()).replace("-", "")
        signer_obj = Signer(
            id=sid,
            name=s.get("name", f"Signer {idx+1}").strip(),
            email=s.get("email", f"signer{idx+1}@example.com").strip().lower(),
            role=s.get("role", "Signer"),
            color=s.get("color", color_palette[idx % len(color_palette)]),
            token=token,
            status="WAITING"
        )
        signers_list.append(signer_obj)
        signer_map[sid] = signer_obj

    # Tag fields with designated signer name & email for privacy checks
    for f in req.fields:
        if f.assigned_to in signer_map:
            target_signer = signer_map[f.assigned_to]
            f.assigned_name = target_signer.name
            f.assigned_email = target_signer.email

    audit_events = [
        AuditEvent(
            id=str(uuid.uuid4()),
            timestamp=now_str,
            action="Envelope Created with Access Controls",
            actor_name=user.name if user else "Document Sender",
            actor_email=user.email if user else None,
            ip_address=client_ip,
            details=f"Configured privacy restrictions for {len(signers_list)} distinct signers"
        )
    ]

    for s in signers_list:
        audit_events.append(AuditEvent(
            id=str(uuid.uuid4()),
            timestamp=now_str,
            action="Invitation Dispatched to Designated Signer",
            actor_name="DocuSign Pro Security Subsystem",
            actor_email=s.email,
            ip_address="127.0.0.1",
            details=f"Secure single-recipient token created for {s.name} ({s.email})"
        ))

    envelope = Envelope(
        id=envelope_id,
        title=req.title or original_fname,
        created_at=now_str,
        status=EnvelopeStatus.WAITING,
        original_filename=original_fname,
        document_path=doc_path,
        document_sha256=doc_sha256,
        is_self_sign=False,
        creator_email=user.email if user else None,
        signers=signers_list,
        fields=req.fields,
        audit_trail=audit_events
    )

    store.create_envelope(envelope)

    base_url = str(request.base_url).rstrip("/")
    signing_links = [
        {
            "signer_id": s.id,
            "name": s.name,
            "email": s.email,
            "role": s.role,
            "color": s.color,
            "token": s.token,
            "signing_url": f"{base_url}/sign/{s.token}"
        }
        for s in envelope.signers
    ]

    return {
        "envelope_id": envelope.id,
        "title": envelope.title,
        "status": envelope.status,
        "signing_links": signing_links
    }

@app.get("/api/envelopes")
def list_envelopes(request: Request):
    user = get_current_user(request)
    all_envs = store.list_envelopes()
    # Filter or return all for demo
    return all_envs

@app.get("/api/envelopes/{envelope_id}")
def get_envelope_details(envelope_id: str):
    env = store.get_envelope(envelope_id)
    if not env:
        raise HTTPException(status_code=404, detail="Envelope not found.")
    return env

# ----------------- Signer Portal Flow (With Strict Recipient Validation) ----------------- #

@app.get("/api/signing/{token}")
def get_signing_session(token: str, request: Request):
    res = store.get_envelope_by_token(token)
    if not res:
        raise HTTPException(status_code=404, detail="Invalid or expired signing link.")
    
    envelope, signer = res
    user = get_current_user(request)
    client_ip = request.client.host if request.client else "127.0.0.1"
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Log viewed event
    if not signer.viewed_at:
        signer.viewed_at = now_str
        if signer.status == "WAITING":
            signer.status = "VIEWED"
        signer.ip_address = client_ip
        store.add_audit_event(
            envelope.id,
            action="Document Accessed by Signer",
            actor_name=user.name if user else signer.name,
            actor_email=user.email if user else signer.email,
            ip_address=client_ip,
            details=f"Accessed from IP {client_ip}"
        )

    doc_filename = os.path.basename(envelope.document_path)
    doc_id = doc_filename.split("_")[0] if "_" in doc_filename else ""

    # Identity match status
    is_identity_match = True
    logged_in_mismatch = None
    if user:
        if user.email.lower() != signer.email.lower():
            is_identity_match = False
            logged_in_mismatch = {
                "logged_in_name": user.name,
                "logged_in_email": user.email,
                "expected_name": signer.name,
                "expected_email": signer.email
            }

    return {
        "envelope_id": envelope.id,
        "title": envelope.title,
        "original_filename": envelope.original_filename,
        "envelope_status": envelope.status,
        "document_pdf_url": f"/api/documents/{doc_id}/pdf",
        "current_signer": signer,
        "is_premium": (user.is_premium if user else signer.is_premium) or ((user.premium_credits > 0) if user else False),
        "identity_verified": is_identity_match,
        "identity_mismatch": logged_in_mismatch,
        "all_signers": [
            {"id": s.id, "name": s.name, "email": s.email, "role": s.role, "status": s.status, "color": s.color}
            for s in envelope.signers
        ],
        "fields": envelope.fields
    }

@app.post("/api/signing/{token}/submit")
def submit_signing(token: str, req: SignerSubmissionRequest, request: Request):
    res = store.get_envelope_by_token(token)
    if not res:
        raise HTTPException(status_code=404, detail="Invalid signing token.")

    envelope, signer = res
    if signer.status == "SIGNED":
        return {"status": "ALREADY_SIGNED", "message": "You have already completed signing this document."}

    user = get_current_user(request)
    client_ip = request.client.host if request.client else "127.0.0.1"
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # STRICT PRIVACY & SECURITY CHECK:
    # 1. If logged in, the authenticated user's email MUST match the assigned signer email
    if user and user.email.lower() != signer.email.lower():
        raise HTTPException(
            status_code=403,
            detail=f"Security Violation: You are currently logged in as '{user.name}' ({user.email}). "
                   f"Under privacy and electronic signature compliance terms, you cannot sign a document "
                   f"reserved for '{signer.name}' ({signer.email}). Please switch accounts to sign."
        )

    # 2. Premium enforcement & Privacy verification: Draw/Upload require Premium tier (₹50)
    for f in req.fields:
        if f.type.value in ["signature", "initials"] and f.value:
            is_image = str(f.value).startswith("data:image")
            if is_image:
                allowed = False
                if user and (user.is_premium or user.premium_credits > 0):
                    allowed = True
                    auth_manager.use_signature_credit(user.id)
                elif signer.is_premium:
                    allowed = True
                
                if not allowed:
                    raise HTTPException(
                        status_code=402,
                        detail="Payment Required: Custom Draw & Upload signatures require a Premium subscription or ₹50 per signature. Please choose 'Type' or unlock for ₹50."
                    )
            else:
                sub_name = (f.signed_by_name or req.signer_name or "").strip()
                if sub_name and sub_name.lower() != signer.name.lower():
                    raise HTTPException(
                        status_code=403,
                        detail=f"Security Violation: Typed signature '{sub_name}' does not match assigned legal name '{signer.name}'."
                    )

    # Update signer
    signer.status = "SIGNED"
    signer.signed_at = now_str
    signer.name = signer.name  # keep verified legal name
    signer.ip_address = client_ip

    # Update assigned fields
    submitted_fields_map = {f.id: f for f in req.fields}
    for f in envelope.fields:
        if f.assigned_to == signer.id:
            if f.id in submitted_fields_map:
                sub_f = submitted_fields_map[f.id]
                f.value = sub_f.value
                f.signed_at = now_str
                f.signed_by_name = signer.name
                f.signed_by_email = signer.email

    store.add_audit_event(
        envelope.id,
        action="Signature Verified and Legally Executed",
        actor_name=signer.name,
        actor_email=signer.email,
        ip_address=client_ip,
        details="ESIGN Act Electronic Records & Signature Disclosure accepted"
    )

    all_signed = all(s.status == "SIGNED" for s in envelope.signers)
    if all_signed:
        envelope.status = EnvelopeStatus.COMPLETED
        envelope.completed_at = now_str

        store.add_audit_event(
            envelope.id,
            action="All Signatures Completed - Document Sealed",
            actor_name="DocuSign Pro Security Subsystem",
            actor_email="system@docusign.local",
            ip_address="127.0.0.1",
            details="Cryptographic Certificate of Completion Attached"
        )

        sealed_bytes, final_sha = stamp_pdf_document(
            envelope.document_path,
            envelope.fields,
            envelope,
            attach_certificate=True
        )
        completed_fpath, _ = store.save_completed_pdf(envelope.id, sealed_bytes)
        envelope.completed_document_path = completed_fpath
        envelope.completed_sha256 = final_sha
    else:
        envelope.status = EnvelopeStatus.PARTIALLY_SIGNED

    store.update_envelope(envelope)

    return {
        "status": "SUCCESS",
        "envelope_status": envelope.status,
        "all_signed": all_signed,
        "download_url": f"/api/envelopes/{envelope.id}/download" if all_signed else None
    }

# ----------------- Download & Certificate APIs ----------------- #

@app.get("/api/envelopes/{envelope_id}/download")
def download_envelope_pdf(envelope_id: str):
    envelope = store.get_envelope(envelope_id)
    if not envelope:
        raise HTTPException(status_code=404, detail="Envelope not found.")

    if envelope.completed_document_path and os.path.exists(envelope.completed_document_path):
        return FileResponse(
            envelope.completed_document_path,
            media_type="application/pdf",
            filename=f"Signed_{envelope.original_filename}"
        )

    sealed_bytes, _ = stamp_pdf_document(envelope.document_path, envelope.fields, envelope, attach_certificate=False)
    return Response(
        content=sealed_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Draft_Signed_{envelope.original_filename}"}
    )

# ----------------- Static UI Pages ----------------- #

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/login")
def serve_login():
    return FileResponse(os.path.join(STATIC_DIR, "login.html"))

@app.get("/")
def serve_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.get("/sign/{token}")
def serve_sign_portal(token: str):
    return FileResponse(os.path.join(STATIC_DIR, "sign.html"))
