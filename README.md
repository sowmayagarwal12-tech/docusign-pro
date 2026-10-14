# DocuSign Pro - Document Signature & Workflow App 🖋️📄

A modern, full-featured electronic document signature application built with **FastAPI**, **PDF.js**, **HTML5 Canvas**, and **ReportLab**. Implements strict legal identity binding, authentication, multi-party envelopes, and cryptographic audit trails.

---

## 🔒 Privacy & Security: "Sign Only To Your Name" Enforcement

DocuSign Pro adheres to the federal **Electronic Signatures in Global and National Commerce Act (ESIGN)**, the **Uniform Electronic Transactions Act (UETA)**, and criminal anti-fraud statutes (18 U.S.C. § 1028):

1. **Sole-Identity Signature Locking**:
   - Every electronic signature is bound to the user's verified legal identity.
   - When adopting a signature (drawn, typed, or uploaded), the legal name is **locked** and cannot be altered or forged under another party's name.
2. **Access Control on Document Fields**:
   - In both Studio and multi-signer workflows, fields designated to other recipients display a padlock icon (`🔒 [Signer Name] Only`).
   - If an authenticated user attempts to interact with or sign another recipient's field, the system blocks the action with an **Electronic Signature Security Alert**.
3. **Cross-Signer Enforcement on the Backend**:
   - The backend validates session identity on every signing submission (`/api/signatures/self-sign` and `/api/signing/{token}/submit`).
   - If an authenticated user attempts to execute an envelope token assigned to a different email address, the API rejects the request with `403 Forbidden: Identity Mismatch`.
4. **Certified Certificate of Completion**:
   - Attaches an official Certificate of Completion as the final page, containing original and final document SHA-256 hashes, verified legal names, email addresses, IP addresses, and UTC timestamps.

---

## 👥 Demo Accounts (Pre-configured for 1-Click Testing)

Navigate to **[http://127.0.0.1:8000/login](http://127.0.0.1:8000/login)** to log in with 1 click:

| Name | Email | Password | Role |
| :--- | :--- | :--- | :--- |
| **Sowmay Sharma** | `sowmay@example.com` | `password123` | Account Owner & Admin |
| **Alice Smith** | `alice@corp.com` | `password123` | Disclosing Party (VP Ops) |
| **Bob Jones** | `bob@partner.com` | `password123` | Receiving Party (Contractor) |

*You can also create a new custom account anytime on the login page.*

---

## 🚀 Quick Start

### 1. Run the Server
```bash
python run.py
```

### 2. Access the Application
- **Login Portal**: [http://127.0.0.1:8000/login](http://127.0.0.1:8000/login)
- **Signing Studio**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Dedicated Signer Link**: `/sign/{token}` (generated when sending an envelope)

---

## 📁 Project Structure

```
Docu-Sign/
├── app/
│   ├── auth.py              # User authentication, password hashing, session store
│   ├── main.py              # FastAPI endpoints, identity validation, & static routes
│   ├── models.py            # Pydantic schemas (User, Envelope, Signer, Field)
│   ├── pdf_engine.py        # PDF stamping engine with coordinate transformations
│   ├── audit_certificate.py # Certificate of Completion generator
│   ├── store.py             # Persistence layer for envelopes and uploads
│   └── samples.py           # Preloaded PDF templates (NDA, Offer Letter, etc.)
├── static/
│   ├── css/style.css        # Stylesheet, pulsing flags, signature canvas
│   ├── js/
│   │   ├── app.js           # Studio state, tabs, and dashboard controller
│   │   ├── pdf_viewer.js    # PDF.js renderer with multi-page & zoom scaling
│   │   ├── field_builder.js # Interactive field overlays & sole-signer security checks
│   │   ├── signature_pad.js # Signature drawing & cursive font generator locked to user
│   │   └── signer_view.js   # Signer ceremony workflow controller & identity check
│   ├── login.html           # Corporate Login, Register, & Privacy Terms interface
│   ├── index.html           # Main Studio & Dashboard UI
│   └── sign.html            # Dedicated Signer Experience UI
├── data/                    # Storage for users, sessions, uploads, and completed PDFs
├── test_app.py              # Automated security and pipeline test suite
└── run.py                   # Server launcher with auto port discovery
```
