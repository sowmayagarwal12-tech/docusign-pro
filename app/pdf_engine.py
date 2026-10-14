import os
import hashlib
import base64
from io import BytesIO
from typing import List, Tuple
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from PIL import Image

from app.models import Envelope, DocumentField, FieldType
from app.audit_certificate import generate_audit_certificate_pdf

def calculate_sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def calculate_sha256_file(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def stamp_pdf_document(input_pdf_path: str, fields: List[DocumentField], envelope: Envelope, attach_certificate: bool = True) -> Tuple[bytes, str]:
    """
    Burns fields (signatures, initials, date, text, checkbox) directly into the PDF pages
    with exact coordinate mapping, and appends a tamper-evident audit certificate.
    Returns (sealed_pdf_bytes, final_sha256).
    """
    with open(input_pdf_path, "rb") as f:
        original_bytes = f.read()

    reader = PdfReader(BytesIO(original_bytes))
    writer = PdfWriter()

    # Group fields by page (page is 1-indexed)
    fields_by_page = {}
    for f in fields:
        fields_by_page.setdefault(f.page, []).append(f)

    for page_idx, page in enumerate(reader.pages):
        page_num = page_idx + 1
        page_fields = fields_by_page.get(page_num, [])

        # Media box dimensions
        pw = float(page.mediabox.width)
        ph = float(page.mediabox.height)

        if not page_fields:
            writer.add_page(page)
            continue

        # Create overlay canvas for this page
        overlay_buf = BytesIO()
        c = canvas.Canvas(overlay_buf, pagesize=(pw, ph))

        for field in page_fields:
            if not field.value:
                continue

            # Normalized coordinate calculation
            fx = float(field.rel_x) * pw
            fw = float(field.rel_width) * pw
            fh = float(field.rel_height) * ph
            # In PDF coordinates, origin (0,0) is bottom-left
            fy = ph - ((float(field.rel_y) + float(field.rel_height)) * ph)

            if field.type in [FieldType.SIGNATURE, FieldType.INITIALS]:
                if str(field.value).startswith("data:image"):
                    try:
                        header_part, base64_part = field.value.split(",", 1)
                        img_bytes = base64.b64decode(base64_part)
                        pil_img = Image.open(BytesIO(img_bytes))
                        
                        img_buf = BytesIO()
                        pil_img.save(img_buf, format="PNG")
                        img_buf.seek(0)
                        ir = ImageReader(img_buf)
                        
                        # Draw signature centered in the bounding box
                        c.drawImage(ir, fx, fy, width=fw, height=fh, mask='auto', preserveAspectRatio=True, anchor='c')
                    except Exception as e:
                        print(f"Error stamping image signature: {e}")
                else:
                    # Fallback text signature
                    c.setFont("Helvetica-BoldOblique", max(10, min(18, int(fh * 0.5))))
                    c.setFillColor(colors.HexColor('#0284c7'))
                    c.drawString(fx + 4, fy + (fh * 0.25), str(field.value))

            elif field.type == FieldType.CHECKBOX:
                val = str(field.value).lower().strip()
                if val in ["true", "checked", "yes", "1", "x"]:
                    # Draw a crisp checkmark
                    c.setStrokeColor(colors.HexColor('#2563eb'))
                    c.setLineWidth(2)
                    c.line(fx + fw * 0.2, fy + fh * 0.45, fx + fw * 0.45, fy + fh * 0.2)
                    c.line(fx + fw * 0.45, fy + fh * 0.2, fx + fw * 0.85, fy + fh * 0.85)

            elif field.type in [FieldType.DATE, FieldType.TEXT]:
                # Text or Date
                c.setFont("Helvetica", max(9, min(14, int(fh * 0.55))))
                c.setFillColor(colors.HexColor('#0f172a'))
                text_val = str(field.value)
                # Position text with subtle vertical offset
                text_y = fy + (fh * 0.25)
                c.drawString(fx + 4, text_y, text_val)

        c.save()

        # Merge overlay onto base page
        overlay_buf.seek(0)
        overlay_reader = PdfReader(overlay_buf)
        if len(overlay_reader.pages) > 0:
            page.merge_page(overlay_reader.pages[0])
        writer.add_page(page)

    # Attach certificate page if requested
    if attach_certificate:
        cert_bytes = generate_audit_certificate_pdf(envelope)
        cert_reader = PdfReader(BytesIO(cert_bytes))
        for cert_page in cert_reader.pages:
            writer.add_page(cert_page)

    out_buf = BytesIO()
    writer.write(out_buf)
    final_pdf_bytes = out_buf.getvalue()
    final_sha256 = calculate_sha256_bytes(final_pdf_bytes)

    return final_pdf_bytes, final_sha256
