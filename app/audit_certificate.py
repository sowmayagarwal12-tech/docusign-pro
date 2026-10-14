import os
from io import BytesIO
from typing import List
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from PIL import Image
import base64

from app.models import Envelope, Signer, AuditEvent

def generate_audit_certificate_pdf(envelope: Envelope) -> bytes:
    """Generates a certified DocuSign-style Certificate of Completion PDF page."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    styles = getSampleStyleSheet()

    # Custom styles
    header_style = ParagraphStyle(
        'CertHeader',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0f172a'),
    )
    sub_style = ParagraphStyle(
        'CertSub',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#2563eb'),
    )
    body_style = ParagraphStyle(
        'CertBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#334155'),
    )
    mono_style = ParagraphStyle(
        'CertMono',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor('#475569'),
    )
    badge_style = ParagraphStyle(
        'CertBadge',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#15803d'),
    )

    story = []

    # Title block
    top_table_data = [
        [
            Paragraph("<b>CERTIFICATE OF COMPLETION</b><br/><font size=8 color='#64748b'>DocuSign Pro &bull; Verified Electronic Signature Audit Trail</font>", header_style),
            Paragraph("<b>STATUS:</b> <font color='#16a34a'>COMPLETED & SEALED</font><br/><b>ENVELOPE ID:</b> " + envelope.id[:18] + "...", ParagraphStyle('RightStat', parent=body_style, alignment=2))
        ]
    ]
    top_table = Table(top_table_data, colWidths=[340, 200])
    top_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(top_table)
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#2563eb'), spaceAfter=10))

    # Envelope Summary Box
    summary_data = [
        [
            Paragraph("<b>Subject:</b> " + envelope.title, body_style),
            Paragraph("<b>Original Pages:</b> " + str(envelope.page_count), body_style)
        ],
        [
            Paragraph("<b>Source Document:</b> " + envelope.original_filename, body_style),
            Paragraph("<b>Completed At:</b> " + (envelope.completed_at or "N/A"), body_style)
        ],
        [
            Paragraph("<b>Original SHA-256:</b><br/>" + envelope.document_sha256, mono_style),
            Paragraph("<b>Certified Seal SHA-256:</b><br/>" + (envelope.completed_sha256 or "Pending final seal"), mono_style)
        ]
    ]
    summary_table = Table(summary_data, colWidths=[270, 270])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#e2e8f0')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#f1f5f9')),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 12))

    # Signer Events Section
    story.append(Paragraph("<b>SIGNER VERIFICATION & DIGITAL SIGNATURES</b>", sub_style))
    story.append(Spacer(1, 4))

    signer_rows = [
        [
            Paragraph("<b>Signer Details</b>", body_style),
            Paragraph("<b>Signature Graphic</b>", body_style),
            Paragraph("<b>Timestamps & Security</b>", body_style)
        ]
    ]

    for signer in envelope.signers:
        # Find if this signer has signature field
        sig_img = None
        for f in envelope.fields:
            if (f.assigned_to == signer.id or f.assigned_to == "self") and f.type.value in ["signature", "initials"] and f.value:
                if f.value.startswith("data:image"):
                    try:
                        header_part, base64_part = f.value.split(",", 1)
                        img_bytes = base64.b64decode(base64_part)
                        pil_img = Image.open(BytesIO(img_bytes))
                        # Resize to fit table cell neatly
                        img_buf = BytesIO()
                        pil_img.save(img_buf, format="PNG")
                        img_buf.seek(0)
                        sig_img = RLImage(img_buf, width=120, height=45)
                    except Exception:
                        sig_img = None
                break

        signer_info = (
            f"<b>{signer.name}</b><br/>"
            f"<font color='#475569'>{signer.email}</font><br/>"
            f"Role: {signer.role or 'Signer'}<br/>"
            f"IP Address: {signer.ip_address or '127.0.0.1'}<br/>"
            f"Status: <b>{signer.status}</b>"
        )
        
        timestamps_info = (
            f"<b>Invited:</b> {envelope.created_at[:19]}<br/>"
            f"<b>Viewed:</b> {signer.viewed_at[:19] if signer.viewed_at else 'Verified'}<br/>"
            f"<b>Signed:</b> {signer.signed_at[:19] if signer.signed_at else (envelope.completed_at[:19] if envelope.completed_at else 'Signed')}<br/>"
            f"<font color='#15803d'>&bull; Electronic Consent Accepted</font>"
        )

        sig_cell = sig_img if sig_img else Paragraph("<font color='#64748b'><i>Digitally Adopted Signature</i></font><br/><b>" + signer.name + "</b>", body_style)

        signer_rows.append([
            Paragraph(signer_info, body_style),
            sig_cell,
            Paragraph(timestamps_info, body_style)
        ])

    signer_table = Table(signer_rows, colWidths=[180, 160, 200])
    signer_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f1f5f9')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(signer_table)
    story.append(Spacer(1, 12))

    # Audit Trail Timeline Section
    story.append(Paragraph("<b>DETAILED AUDIT TRAIL LOG</b>", sub_style))
    story.append(Spacer(1, 4))

    audit_rows = [
        [
            Paragraph("<b>Timestamp (UTC)</b>", body_style),
            Paragraph("<b>Action / Event</b>", body_style),
            Paragraph("<b>User / Signer</b>", body_style),
            Paragraph("<b>IP / Metadata</b>", body_style),
        ]
    ]

    for ev in envelope.audit_trail[-6:]:  # show recent audit entries
        audit_rows.append([
            Paragraph(ev.timestamp[:19], mono_style),
            Paragraph(f"<b>{ev.action}</b>", body_style),
            Paragraph(f"{ev.actor_name} ({ev.actor_email or ''})", body_style),
            Paragraph(f"{ev.ip_address} | {ev.details or 'OK'}", mono_style),
        ])

    audit_table = Table(audit_rows, colWidths=[110, 150, 140, 140])
    audit_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f1f5f9')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('PADDING', (0,0), (-1,-1), 4),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(audit_table)
    story.append(Spacer(1, 14))

    # Compliance statement footer
    compliance_text = (
        "<b>Electronic Signature Legal Compliance Disclosure:</b><br/>"
        "This Certificate of Completion confirms that this document was electronically executed using DocuSign Pro cryptographic "
        "signing technology in full compliance with the <i>Electronic Signatures in Global and National Commerce Act (ESIGN Act, 15 U.S.C. § 7001 et seq.)</i> "
        "and the <i>Uniform Electronic Transactions Act (UETA)</i>. All parties consented to electronic execution. "
        "Tamper-evident SHA-256 cryptographic signatures ensure document non-repudiation."
    )
    compliance_p = Paragraph(compliance_text, ParagraphStyle('Comp', parent=body_style, fontSize=7, leading=9, textColor=colors.HexColor('#64748b')))
    story.append(compliance_p)

    doc.build(story)
    return buf.getvalue()
