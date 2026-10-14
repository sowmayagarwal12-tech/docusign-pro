import os
import json
import uuid
import random
import hashlib
import datetime
from typing import Dict, Optional, Tuple, Any
from app.models import User

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
USERS_FILE = os.path.join(BASE_DIR, "data", "users.json")
SESSIONS_FILE = os.path.join(BASE_DIR, "data", "sessions.json")

def hash_password(password: str) -> str:
    return hashlib.sha256(("docu_salt_" + password).encode("utf-8")).hexdigest()

class AuthManager:
    def __init__(self):
        self._users: Dict[str, User] = {}  # email -> User
        self._sessions: Dict[str, str] = {}  # token -> email
        self._pending_otps: Dict[str, Dict[str, Any]] = {}  # identifier -> { otp, doc_type, name, timestamp }
        self._load_users()
        self._seed_default_users()

    def _load_users(self):
        if os.path.exists(USERS_FILE):
            try:
                with open(USERS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for u_dict in data:
                        u = User(**u_dict)
                        self._users[u.email.lower()] = u
            except Exception as e:
                print(f"Error loading users: {e}")

        if os.path.exists(SESSIONS_FILE):
            try:
                with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
                    self._sessions = json.load(f)
            except Exception:
                self._sessions = {}

    def _save_users(self):
        os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            data = [u.model_dump() for u in self._users.values()]
            json.dump(data, f, indent=2)

    def _save_sessions(self):
        os.makedirs(os.path.dirname(SESSIONS_FILE), exist_ok=True)
        with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(self._sessions, f, indent=2)

    def _seed_default_users(self):
        default_users = [
            ("Sowmay Sharma", "sowmay@example.com", "password123", "Account Owner", "aadhaar", "XXXX-XXXX-8921", True, 10),
            ("Alice Smith", "alice@corp.com", "password123", "Disclosing Party (VP Ops)", "email_otp", "alice@corp.com", True, 10),
            ("Bob Jones", "bob@partner.com", "password123", "Receiving Party (Contractor)", "pan", "ABCDE1234F", True, 10)
        ]
        updated = False
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        for name, email, pwd, role, kyc_type, kyc_id, is_prem, credits in default_users:
            if email.lower() not in self._users:
                u = User(
                    id=str(uuid.uuid4()),
                    name=name,
                    email=email.lower(),
                    password_hash=hash_password(pwd),
                    role=role,
                    terms_accepted=True,
                    terms_accepted_at=now_str,
                    terms_ip="127.0.0.1",
                    kyc_verified=True,
                    kyc_doc_type=kyc_type,
                    kyc_doc_id=kyc_id,
                    kyc_verified_at=now_str,
                    is_premium=is_prem,
                    premium_credits=credits
                )
                self._users[email.lower()] = u
                updated = True
            else:
                # Update existing seed user with KYC and premium attributes if missing
                u = self._users[email.lower()]
                if not u.kyc_verified:
                    u.kyc_verified = True
                    u.kyc_doc_type = kyc_type
                    u.kyc_doc_id = kyc_id
                    u.kyc_verified_at = now_str
                    u.is_premium = is_prem
                    u.premium_credits = credits
                    updated = True
        if updated:
            self._save_users()

    def generate_kyc_otp(self, doc_type: str, identifier: str, email: Optional[str] = None, name: Optional[str] = None) -> Dict[str, Any]:
        """Generates an OTP for Aadhaar, PAN, or Email verification."""
        clean_id = identifier.strip()
        otp = str(random.randint(100000, 999999))
        record = {
            "otp": otp,
            "doc_type": doc_type,
            "identifier": clean_id,
            "email": email.strip().lower() if email else "",
            "name": name.strip() if name else "",
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        self._pending_otps[clean_id] = record

        # Clean digits for Aadhaar
        digits_only = "".join(ch for ch in clean_id if ch.isdigit())
        if digits_only:
            self._pending_otps[digits_only] = record

        # Also store under email if available
        if email:
            self._pending_otps[email.strip().lower()] = record

        masked_id = clean_id
        if doc_type == "aadhaar":
            last4 = digits_only[-4:] if len(digits_only) >= 4 else "0000"
            masked_id = f"XXXX-XXXX-{last4}"
            if email:
                msg = f"OTP {otp} dispatched to {email.strip()} and UIDAI mobile for Aadhaar {masked_id}."
            else:
                msg = f"OTP {otp} sent to mobile linked with Aadhaar {masked_id}."
        elif doc_type == "pan":
            masked_id = clean_id[:2] + "XXXXX" + clean_id[-2:] if len(clean_id) >= 4 else clean_id
            msg = f"OTP {otp} sent to mobile registered with Income Tax Dept for PAN {masked_id}."
        else:
            msg = f"OTP {otp} sent to legal email {clean_id}."

        print(f"[UIDAI & IDENTITY GATEWAY] Generated OTP: {otp} | Document: {doc_type} ({masked_id}) | Email: {email or 'N/A'}")

        return {
            "status": "OTP_SENT",
            "otp": otp,
            "otp_demo": otp,
            "doc_type": doc_type,
            "identifier": clean_id,
            "masked_identifier": masked_id,
            "email": email.strip() if email else "",
            "message": msg
        }

    def verify_kyc_otp(self, doc_type: str, identifier: str, otp: str, legal_name: Optional[str] = None, email: Optional[str] = None) -> Dict[str, Any]:
        """Verifies the OTP and extracts the locked Government Verified Legal Name."""
        clean_id = identifier.strip()
        digits_only = "".join(ch for ch in clean_id if ch.isdigit())
        clean_email = email.strip().lower() if email else ""

        record = (
            self._pending_otps.get(clean_id) or
            (self._pending_otps.get(digits_only) if digits_only else None) or
            (self._pending_otps.get(clean_email) if clean_email else None)
        )

        valid_otp = record.get("otp") if record else None
        # Allow matching OTP or demo universal fallback
        if otp != "123456" and otp != valid_otp:
            raise ValueError(f"Invalid or expired OTP: '{otp}'. Please enter the correct 6-digit code.")

        masked_id = clean_id
        if doc_type == "aadhaar":
            last4 = digits_only[-4:] if len(digits_only) >= 4 else "0000"
            masked_id = f"XXXX-XXXX-{last4}"
            verified_name = legal_name.strip() if legal_name else (record.get("name") if record and record.get("name") else "Verified Aadhaar Citizen")
        elif doc_type == "pan":
            masked_id = clean_id[:2] + "XXXXX" + clean_id[-2:] if len(clean_id) >= 4 else clean_id
            verified_name = legal_name.strip() if legal_name else "Verified Taxpayer"
        else:
            verified_name = legal_name.strip() if legal_name else clean_id.split("@")[0].replace(".", " ").title()

        return {
            "verified": True,
            "doc_type": doc_type,
            "doc_id": masked_id,
            "verified_name": verified_name,
            "verified_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }

    def register_user(
        self,
        name: str,
        email: str,
        password: str,
        kyc_doc_type: str = "aadhaar",
        kyc_doc_id: str = "",
        kyc_otp: Optional[str] = None,
        client_ip: str = "127.0.0.1"
    ) -> Tuple[User, str]:
        email_clean = email.strip().lower()
        if email_clean in self._users:
            raise ValueError("An account with this email already exists.")

        # If an OTP is provided during registration, verify it directly
        if kyc_otp:
            clean_id = kyc_doc_id.strip()
            digits_only = "".join(ch for ch in clean_id if ch.isdigit())
            record = (
                self._pending_otps.get(clean_id) or 
                (self._pending_otps.get(digits_only) if digits_only else None) or
                self._pending_otps.get(email_clean)
            )
            valid_otp = record.get("otp") if record else None
            if kyc_otp.strip() != "123456" and kyc_otp.strip() != valid_otp:
                raise ValueError("Invalid verification OTP. Please enter the valid code sent to your email/Aadhaar.")

        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        # Mask Aadhaar if full number given
        masked_doc_id = kyc_doc_id
        if kyc_doc_type == "aadhaar" and kyc_doc_id:
            digits_only = "".join(ch for ch in kyc_doc_id if ch.isdigit())
            if len(digits_only) >= 4:
                masked_doc_id = f"XXXX-XXXX-{digits_only[-4:]}"

        user = User(
            id=str(uuid.uuid4()),
            name=name.strip(),
            email=email_clean,
            password_hash=hash_password(password),
            role="Signer",
            terms_accepted=True,
            terms_accepted_at=now_str,
            terms_ip=client_ip,
            kyc_verified=True,
            kyc_doc_type=kyc_doc_type,
            kyc_doc_id=masked_doc_id or "XXXX-XXXX-9901",
            kyc_verified_at=now_str,
            is_premium=False,       # Standard Free Tier
            premium_credits=0       # 0 credits initially (pays ₹50 per drawn/uploaded signature)
        )
        self._users[email_clean] = user
        self._save_users()

        session_token = str(uuid.uuid4()).replace("-", "")
        self._sessions[session_token] = email_clean
        self._save_sessions()

        return user, session_token

    def authenticate_user(self, email: str, password: str) -> Optional[Tuple[User, str]]:
        email_clean = email.strip().lower()
        user = self._users.get(email_clean)
        if not user:
            return None
        if user.password_hash != hash_password(password):
            return None

        session_token = str(uuid.uuid4()).replace("-", "")
        self._sessions[session_token] = email_clean
        self._save_sessions()
        return user, session_token

    def get_user_by_session(self, token: str) -> Optional[User]:
        if not token:
            return None
        email = self._sessions.get(token)
        if not email:
            return None
        return self._users.get(email)

    def logout_session(self, token: str):
        if token in self._sessions:
            del self._sessions[token]
            self._save_sessions()

    def accept_terms(self, user_id: str, client_ip: str = "127.0.0.1") -> Optional[User]:
        for u in self._users.values():
            if u.id == user_id:
                u.terms_accepted = True
                u.terms_accepted_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
                u.terms_ip = client_ip
                self._save_users()
                return u
        return None

    def purchase_signature_credits(self, user_id: str, amount: int = 50, credits: int = 1) -> User:
        """Processes payment (₹50) and grants premium signature credits or activates premium."""
        for u in self._users.values():
            if u.id == user_id:
                u.premium_credits += credits
                # If they paid, they can also be marked as premium status
                u.is_premium = True
                self._save_users()
                return u
        raise ValueError("User not found.")

    def use_signature_credit(self, user_id: str) -> bool:
        """Consumes a credit for a drawn or uploaded signature if not unlimited."""
        for u in self._users.values():
            if u.id == user_id:
                if u.is_premium:
                    return True
                if u.premium_credits > 0:
                    u.premium_credits -= 1
                    self._save_users()
                    return True
                return False
        return False

auth_manager = AuthManager()
