import os
import json
import uuid
import datetime
from typing import Dict, List, Optional, Tuple
from pypdf import PdfReader

from app.models import Envelope, Signer, DocumentField, AuditEvent, EnvelopeStatus
from app.pdf_engine import calculate_sha256_file, calculate_sha256_bytes

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
COMPLETED_DIR = os.path.join(DATA_DIR, "completed")
ENVELOPES_DIR = os.path.join(DATA_DIR, "envelopes")
SAMPLES_DIR = os.path.join(DATA_DIR, "samples")

for d in [UPLOADS_DIR, COMPLETED_DIR, ENVELOPES_DIR, SAMPLES_DIR]:
    os.makedirs(d, exist_ok=True)

class EnvelopeStore:
    def __init__(self):
        self._envelopes: Dict[str, Envelope] = {}
        self._token_to_envelope_id: Dict[str, str] = {}
        self._load_from_disk()

    def _load_from_disk(self):
        if not os.path.exists(ENVELOPES_DIR):
            return
        for fname in os.listdir(ENVELOPES_DIR):
            if fname.endswith(".json"):
                fpath = os.path.join(ENVELOPES_DIR, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        envelope = Envelope(**data)
                        self._envelopes[envelope.id] = envelope
                        for s in envelope.signers:
                            self._token_to_envelope_id[s.token] = envelope.id
                except Exception as e:
                    print(f"Error loading envelope {fname}: {e}")

    def _persist_envelope(self, envelope: Envelope):
        fpath = os.path.join(ENVELOPES_DIR, f"{envelope.id}.json")
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(envelope.model_dump_json(indent=2))

    def save_upload(self, file_bytes: bytes, original_filename: str) -> Dict[str, any]:
        doc_id = str(uuid.uuid4())
        safe_name = f"{doc_id}_{original_filename.replace(' ', '_')}"
        file_path = os.path.join(UPLOADS_DIR, safe_name)
        with open(file_path, "wb") as f:
            f.write(file_bytes)

        sha256 = calculate_sha256_bytes(file_bytes)
        try:
            reader = PdfReader(file_path)
            page_count = len(reader.pages)
        except Exception:
            page_count = 1

        return {
            "document_id": doc_id,
            "filename": original_filename,
            "file_path": file_path,
            "sha256": sha256,
            "page_count": page_count
        }

    def save_completed_pdf(self, envelope_id: str, pdf_bytes: bytes) -> Tuple[str, str]:
        fname = f"sealed_{envelope_id}.pdf"
        fpath = os.path.join(COMPLETED_DIR, fname)
        with open(fpath, "wb") as f:
            f.write(pdf_bytes)
        sha256 = calculate_sha256_bytes(pdf_bytes)
        return fpath, sha256

    def create_envelope(self, envelope: Envelope) -> Envelope:
        self._envelopes[envelope.id] = envelope
        for s in envelope.signers:
            self._token_to_envelope_id[s.token] = envelope.id
        self._persist_envelope(envelope)
        return envelope

    def get_envelope(self, envelope_id: str) -> Optional[Envelope]:
        return self._envelopes.get(envelope_id)

    def get_envelope_by_token(self, token: str) -> Optional[Tuple[Envelope, Signer]]:
        envelope_id = self._token_to_envelope_id.get(token)
        if not envelope_id:
            # Fallback search
            for env in self._envelopes.values():
                for s in env.signers:
                    if s.token == token:
                        self._token_to_envelope_id[token] = env.id
                        return env, s
            return None

        envelope = self._envelopes.get(envelope_id)
        if not envelope:
            return None
        for s in envelope.signers:
            if s.token == token:
                return envelope, s
        return None

    def update_envelope(self, envelope: Envelope) -> Envelope:
        self._envelopes[envelope.id] = envelope
        for s in envelope.signers:
            self._token_to_envelope_id[s.token] = envelope.id
        self._persist_envelope(envelope)
        return envelope

    def list_envelopes(self) -> List[Envelope]:
        return sorted(list(self._envelopes.values()), key=lambda e: e.created_at, reverse=True)

    def add_audit_event(self, envelope_id: str, action: str, actor_name: str, actor_email: str = None, ip_address: str = "127.0.0.1", details: str = None):
        envelope = self.get_envelope(envelope_id)
        if not envelope:
            return
        event = AuditEvent(
            id=str(uuid.uuid4()),
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            action=action,
            actor_name=actor_name,
            actor_email=actor_email,
            ip_address=ip_address,
            details=details
        )
        envelope.audit_trail.append(event)
        self.update_envelope(envelope)

store = EnvelopeStore()
