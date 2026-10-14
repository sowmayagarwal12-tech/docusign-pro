import io
import uuid
import base64
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw
from pypdf import PdfReader
from app.main import app

client = TestClient(app)

def test_full_pipeline_with_security():
    print("--- 1. Testing Authentication & Identity ---")
    # Invalid login
    bad_login = client.post("/api/auth/login", json={"email": "alice@corp.com", "password": "wrongpassword"})
    assert bad_login.status_code == 401

    # Valid login as Alice
    alice_login = client.post("/api/auth/login", json={"email": "alice@corp.com", "password": "password123"})
    assert alice_login.status_code == 200
    alice_data = alice_login.json()
    alice_token = alice_data["token"]
    assert alice_data["user"]["name"] == "Alice Smith"
    print(f"Alice logged in successfully! Token: {alice_token[:10]}...")

    # Valid login as Bob
    bob_login = client.post("/api/auth/login", json={"email": "bob@partner.com", "password": "password123"})
    assert bob_login.status_code == 200
    bob_token = bob_login.json()["token"]
    print("Bob logged in successfully!")

    # Check /api/auth/me
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {alice_token}"})
    assert me_res.status_code == 200
    assert me_res.json()["name"] == "Alice Smith"

    print("--- 2. Testing Sample Document Loading ---")
    res = client.post("/api/documents/samples/nda/load", headers={"Authorization": f"Bearer {alice_token}"})
    assert res.status_code == 200
    doc_id = res.json()["document_id"]
    print(f"Sample loaded: doc_id: {doc_id}")

    # Generate dummy signature base64 image
    im = Image.new('RGBA', (200, 60), (255, 255, 255, 0))
    d = ImageDraw.Draw(im)
    d.line([(10, 40), (70, 10), (130, 50), (190, 20)], fill=(30, 64, 175, 255), width=3)
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    sig_b64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

    print("--- 3. Testing Privacy & Security: Forgery Block (Sign Only To Own Name) ---")
    # Typed forgery attempt: Alice attempts to type "Bob Jones"
    forgery_payload = {
        "document_id": doc_id,
        "title": "Unauthorized Document",
        "signer_name": "Alice Smith",
        "fields": [{
            "id": "f_sig_fake",
            "type": "signature",
            "page": 1,
            "rel_x": 0.15,
            "rel_y": 0.80,
            "rel_width": 0.25,
            "rel_height": 0.06,
            "assigned_to": "self",
            "required": True,
            "value": "Bob Jones", # TYPED TEXT FORGERY
            "signed_by_name": "Bob Jones"
        }]
    }
    forgery_res = client.post("/api/signatures/self-sign", json=forgery_payload, headers={"Authorization": f"Bearer {alice_token}"})
    assert forgery_res.status_code == 403, "Expected 403 Forbidden for typing another user's name!"
    print(f"Typed forgery blocked by security terms! Server response: {forgery_res.json()['detail']}")

    print("--- 4. Testing Draw and Upload (Unrestricted Graphical Signatures) ---")
    draw_payload = {
        "document_id": doc_id,
        "title": "Legitimate NDA Signed by Alice (Drawn / Uploaded)",
        "signer_name": "Alice Smith",
        "fields": [{
            "id": "f_sig_alice_draw",
            "type": "signature",
            "page": 1,
            "rel_x": 0.15,
            "rel_y": 0.80,
            "rel_width": 0.25,
            "rel_height": 0.06,
            "assigned_to": "self",
            "required": True,
            "value": sig_b64, # Drawn canvas or uploaded image
            "signed_by_name": "Alice Smith"
        }]
    }
    draw_res = client.post("/api/signatures/self-sign", json=draw_payload, headers={"Authorization": f"Bearer {alice_token}"})
    assert draw_res.status_code == 200, f"Drawn signature failed: {draw_res.text}"
    env_id = draw_res.json()["envelope_id"]
    print(f"Drawn / Uploaded signature accepted seamlessly! Envelope ID: {env_id}")

    print("--- 5. Testing Multi-Party Envelope & Cross-Signer Identity Restriction ---")
    envelope_payload = {
        "document_id": doc_id,
        "title": "Two-Party Mutual NDA",
        "signers": [
            {"name": "Alice Smith", "email": "alice@corp.com", "role": "Disclosing Party"},
            {"name": "Bob Jones", "email": "bob@partner.com", "role": "Receiving Party"}
        ],
        "fields": [
            {
                "id": "f_alice",
                "type": "signature",
                "page": 1,
                "rel_x": 0.1,
                "rel_y": 0.8,
                "rel_width": 0.25,
                "rel_height": 0.06,
                "assigned_to": "signer_1",
                "required": True
            },
            {
                "id": "f_bob",
                "type": "signature",
                "page": 1,
                "rel_x": 0.55,
                "rel_y": 0.8,
                "rel_width": 0.25,
                "rel_height": 0.06,
                "assigned_to": "signer_2",
                "required": True
            }
        ]
    }
    create_res = client.post("/api/envelopes/create", json=envelope_payload, headers={"Authorization": f"Bearer {alice_token}"})
    assert create_res.status_code == 200
    env_data = create_res.json()
    token_alice = env_data["signing_links"][0]["token"]
    token_bob = env_data["signing_links"][1]["token"]

    # Security Check: Alice tries to sign Bob's token
    hack_res = client.post(f"/api/signing/{token_bob}/submit", json={
        "token": token_bob,
        "signer_name": "Bob Jones",
        "fields": [{
            "id": "f_bob",
            "type": "signature",
            "page": 1,
            "rel_x": 0.55,
            "rel_y": 0.8,
            "rel_width": 0.25,
            "rel_height": 0.06,
            "assigned_to": "signer_2",
            "required": True,
            "value": sig_b64
        }]
    }, headers={"Authorization": f"Bearer {alice_token}"}) # Alice's token submitting Bob's link!
    assert hack_res.status_code == 403, "Expected 403 Forbidden when user signs someone else's envelope!"
    print(f"Unauthorized cross-party execution blocked! Server response: {hack_res.json()['detail']}")

    # Alice signs her own token
    alice_sign_res = client.post(f"/api/signing/{token_alice}/submit", json={
        "token": token_alice,
        "signer_name": "Alice Smith",
        "fields": [{
            "id": "f_alice",
            "type": "signature",
            "page": 1,
            "rel_x": 0.1,
            "rel_y": 0.8,
            "rel_width": 0.25,
            "rel_height": 0.06,
            "assigned_to": "signer_1",
            "required": True,
            "value": sig_b64
        }]
    }, headers={"Authorization": f"Bearer {alice_token}"})
    assert alice_sign_res.status_code == 200

    # Bob signs his own token
    bob_sign_res = client.post(f"/api/signing/{token_bob}/submit", json={
        "token": token_bob,
        "signer_name": "Bob Jones",
        "fields": [{
            "id": "f_bob",
            "type": "signature",
            "page": 1,
            "rel_x": 0.55,
            "rel_y": 0.8,
            "rel_width": 0.25,
            "rel_height": 0.06,
            "assigned_to": "signer_2",
            "required": True,
            "value": sig_b64
        }]
    }, headers={"Authorization": f"Bearer {bob_token}"})
    assert bob_sign_res.status_code == 200
    assert bob_sign_res.json()["all_signed"] == True
    print("Bob signed under his own verified identity! All parties executed and envelope sealed!")

    print("\n[SUCCESS] ALL PRIVACY & SECURITY AUTHENTICATION TESTS PASSED!")

def test_kyc_and_premium_payment():
    print("\n--- 6. Testing Aadhaar & Email OTP Verification on Registration ---")
    test_email = f"rohan_{uuid.uuid4().hex[:6]}@example.com"
    # 1. Request dynamic KYC OTP for Aadhaar + Email
    otp_res = client.post("/api/auth/send-kyc-otp", json={
        "doc_type": "aadhaar",
        "identifier": "548912345678",
        "email": test_email,
        "name": "Rohan Verma"
    })
    assert otp_res.status_code == 200
    otp_data = otp_res.json()
    assert "XXXX-XXXX-5678" in otp_data["masked_identifier"]
    dynamic_otp = otp_data["otp"]
    assert len(dynamic_otp) == 6

    # 2. Test Invalid OTP rejection
    bad_verify = client.post("/api/auth/verify-kyc", json={
        "doc_type": "aadhaar",
        "identifier": "548912345678",
        "otp": "000000",
        "name": "Rohan Verma",
        "email": test_email
    })
    assert bad_verify.status_code == 400
    print("Invalid OTP blocked as expected by UIDAI & Email verification engine!")

    # 3. Verify with dynamic OTP
    verify_res = client.post("/api/auth/verify-kyc", json={
        "doc_type": "aadhaar",
        "identifier": "548912345678",
        "otp": dynamic_otp,
        "name": "Rohan Verma",
        "email": test_email
    })
    assert verify_res.status_code == 200
    assert verify_res.json()["verified"] == True
    assert verify_res.json()["doc_id"] == "XXXX-XXXX-5678"

    # 4. Register user with verified KYC and OTP
    reg_res = client.post("/api/auth/register", json={
        "name": "Rohan Verma",
        "email": test_email,
        "password": "password123",
        "kyc_doc_type": "aadhaar",
        "kyc_doc_id": "548912345678",
        "kyc_otp": dynamic_otp
    })
    assert reg_res.status_code == 200, f"Registration failed: {reg_res.text}"
    user_data = reg_res.json()["user"]
    rohan_token = reg_res.json()["token"]
    assert user_data["kyc_verified"] == True
    assert user_data["kyc_doc_id"] == "XXXX-XXXX-5678"
    assert user_data["is_premium"] == False  # Standard Tier
    print("Rohan registered successfully with Aadhaar & Email verification!")

    print("\n--- 7. Testing Signature Tier Restriction (Type free, Draw/Upload requires Rs. 50) ---")
    # Load sample doc as Rohan
    sample_res = client.post("/api/documents/samples/nda/load", headers={"Authorization": f"Bearer {rohan_token}"})
    assert sample_res.status_code == 200
    doc_id = sample_res.json()["document_id"]

    # Free Type Signature: Should succeed!
    typed_payload = {
        "document_id": doc_id,
        "title": "Rohan Free Typed NDA",
        "signer_name": "Rohan Verma",
        "fields": [{
            "id": "f_rohan_typed",
            "type": "signature",
            "page": 1,
            "rel_x": 0.15,
            "rel_y": 0.80,
            "rel_width": 0.25,
            "rel_height": 0.06,
            "assigned_to": "self",
            "required": True,
            "value": "Rohan Verma",
            "signed_by_name": "Rohan Verma"
        }]
    }
    typed_res = client.post("/api/signatures/self-sign", json=typed_payload, headers={"Authorization": f"Bearer {rohan_token}"})
    assert typed_res.status_code == 200, "Type signature must be available for all users!"
    print("Free Typed signature succeeded for standard user!")

    # Attempt Drawn / Uploaded signature WITHOUT premium / Rs. 50 payment: Should return 402 Payment Required!
    im = Image.new('RGBA', (200, 60), (255, 255, 255, 0))
    d = ImageDraw.Draw(im)
    d.line([(10, 40), (190, 20)], fill=(30, 64, 175, 255), width=3)
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    sig_b64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

    draw_payload = {
        "document_id": doc_id,
        "title": "Rohan Draw Attempt",
        "signer_name": "Rohan Verma",
        "fields": [{
            "id": "f_rohan_draw",
            "type": "signature",
            "page": 1,
            "rel_x": 0.15,
            "rel_y": 0.80,
            "rel_width": 0.25,
            "rel_height": 0.06,
            "assigned_to": "self",
            "required": True,
            "value": sig_b64,
            "signed_by_name": "Rohan Verma"
        }]
    }
    blocked_draw_res = client.post("/api/signatures/self-sign", json=draw_payload, headers={"Authorization": f"Bearer {rohan_token}"})
    assert blocked_draw_res.status_code == 402, "Standard user drawing signature must return 402 Payment Required!"
    print("Non-premium draw blocked as expected with HTTP 402 Payment Required!")

    # 4. Pay Rs. 50 to unlock premium signature license
    pay_res = client.post("/api/payments/pay-signature", json={
        "amount": 50,
        "currency": "INR",
        "payment_method": "upi",
        "upi_id": "rohan@upi"
    }, headers={"Authorization": f"Bearer {rohan_token}"})
    assert pay_res.status_code == 200
    assert pay_res.json()["status"] == "PAYMENT_SUCCESS"
    assert pay_res.json()["is_premium"] == True
    print("Payment of Rs. 50 processed successfully via UPI!")

    # 5. Now submit Drawn signature: Should succeed!
    allowed_draw_res = client.post("/api/signatures/self-sign", json=draw_payload, headers={"Authorization": f"Bearer {rohan_token}"})
    assert allowed_draw_res.status_code == 200
    print("Premium Drawn signature successfully executed post-payment!")

if __name__ == "__main__":
    test_full_pipeline_with_security()
    test_kyc_and_premium_payment()
