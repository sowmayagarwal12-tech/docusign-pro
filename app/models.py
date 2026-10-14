from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field as PydanticField

class User(BaseModel):
    id: str
    name: str
    email: str
    password_hash: str
    role: str = "Signer"
    terms_accepted: bool = False
    terms_accepted_at: Optional[str] = None
    terms_ip: Optional[str] = None
    
    # Government & Legal Identity Verification
    kyc_verified: bool = False
    kyc_doc_type: Optional[str] = None  # "aadhaar", "pan", "passport", "email_otp"
    kyc_doc_id: Optional[str] = None    # masked document ID e.g. "XXXX-XXXX-8921"
    kyc_verified_at: Optional[str] = None

    # Premium Signature Status (Draw & Upload unlocked via ₹50 / signature)
    is_premium: bool = False
    premium_credits: int = 0

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    kyc_doc_type: str = "aadhaar"  # "aadhaar", "pan", "passport", "email_otp"
    kyc_doc_id: str = ""           # Document number / identifier
    kyc_otp: Optional[str] = None

class KycOtpRequest(BaseModel):
    doc_type: str = "aadhaar"  # "aadhaar", "pan", "passport", "email_otp"
    identifier: str            # 12-digit aadhaar, PAN, or email
    email: Optional[str] = None
    name: Optional[str] = None

class KycVerifyRequest(BaseModel):
    doc_type: str = "aadhaar"  # "aadhaar", "pan", "passport", "email_otp"
    identifier: str
    otp: str
    email: Optional[str] = None
    name: Optional[str] = None

class SignaturePaymentRequest(BaseModel):
    amount: int = 50
    currency: str = "INR"
    payment_method: str = "upi"  # "upi", "card", "netbanking"
    upi_id: Optional[str] = None
    card_last4: Optional[str] = None

class AcceptTermsRequest(BaseModel):
    accepted: bool = True

class FieldType(str, Enum):
    SIGNATURE = "signature"
    INITIALS = "initials"
    DATE = "date"
    TEXT = "text"
    CHECKBOX = "checkbox"

class EnvelopeStatus(str, Enum):
    DRAFT = "draft"
    WAITING = "waiting"
    PARTIALLY_SIGNED = "partially_signed"
    COMPLETED = "completed"
    VOIDED = "voided"

class DocumentField(BaseModel):
    id: str
    type: FieldType
    page: int  # 1-indexed
    rel_x: float  # 0.0 - 1.0 (relative to page width)
    rel_y: float  # 0.0 - 1.0 (relative to page height from top)
    rel_width: float
    rel_height: float
    assigned_to: Optional[str] = "self"  # signer id, user id, or "self"
    assigned_name: Optional[str] = None
    assigned_email: Optional[str] = None
    required: bool = True
    value: Optional[str] = None  # text or data:image/png;base64,...
    label: Optional[str] = None
    signed_at: Optional[str] = None
    signed_by_name: Optional[str] = None
    signed_by_email: Optional[str] = None
    font_family: Optional[str] = None
    signature_mode: Optional[str] = "type"  # "type", "draw", "upload"

class Signer(BaseModel):
    id: str
    name: str
    email: str
    role: Optional[str] = "Signer"
    color: str = "#2563eb"
    token: str
    status: str = "WAITING"  # WAITING, VIEWED, SIGNED
    viewed_at: Optional[str] = None
    signed_at: Optional[str] = None
    ip_address: Optional[str] = None
    kyc_verified: bool = False
    kyc_doc_type: Optional[str] = None
    is_premium: bool = False

class AuditEvent(BaseModel):
    id: str
    timestamp: str
    action: str
    actor_name: str
    actor_email: Optional[str] = None
    ip_address: Optional[str] = "127.0.0.1"
    details: Optional[str] = None

class Envelope(BaseModel):
    id: str
    title: str
    created_at: str
    status: EnvelopeStatus = EnvelopeStatus.WAITING
    original_filename: str
    document_path: str
    document_sha256: str
    completed_document_path: Optional[str] = None
    completed_sha256: Optional[str] = None
    completed_at: Optional[str] = None
    is_self_sign: bool = False
    page_count: int = 1
    creator_email: Optional[str] = None
    signers: List[Signer] = []
    fields: List[DocumentField] = []
    audit_trail: List[AuditEvent] = []

class SelfSignRequest(BaseModel):
    document_id: str
    title: Optional[str] = "Self Signed Document"
    signer_name: str
    signer_email: Optional[str] = "self@signer.local"
    fields: List[DocumentField]

class CreateEnvelopeRequest(BaseModel):
    document_id: str
    title: str
    signers: List[Dict[str, Any]]
    fields: List[DocumentField]

class SignerSubmissionRequest(BaseModel):
    token: str
    signer_name: str
    fields: List[DocumentField]
