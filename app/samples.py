import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

SAMPLE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "samples")

def ensure_samples():
    os.makedirs(SAMPLE_DIR, exist_ok=True)
    nda_path = os.path.join(SAMPLE_DIR, "mutual_nda.pdf")
    offer_path = os.path.join(SAMPLE_DIR, "employment_offer_letter.pdf")
    contract_path = os.path.join(SAMPLE_DIR, "consulting_agreement.pdf")

    if not os.path.exists(nda_path):
        create_nda(nda_path)
    if not os.path.exists(offer_path):
        create_offer_letter(offer_path)
    if not os.path.exists(contract_path):
        create_consulting_agreement(contract_path)

def create_nda(output_path: str):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1e293b'),
        alignment=1, # Center
        spaceAfter=14
    )
    h2_style = ParagraphStyle(
        'DocH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#0f172a'),
        spaceBefore=10,
        spaceAfter=4
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor('#334155'),
        spaceAfter=8
    )

    story = []
    story.append(Paragraph("MUTUAL NON-DISCLOSURE AGREEMENT", title_style))
    story.append(Paragraph("<b>Effective Date:</b> Current Date &nbsp;&nbsp;|&nbsp;&nbsp; <b>Jurisdiction:</b> Delaware, USA", ParagraphStyle('Sub', parent=body_style, alignment=1)))
    story.append(Spacer(1, 12))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cbd5e1'), spaceAfter=14))

    story.append(Paragraph(
        "This Mutual Non-Disclosure Agreement (\"Agreement\") is entered into between <b>Party A</b> and <b>Party B</b> "
        "(each a \"Party\", and collectively the \"Parties\") for the purpose of preventing the unauthorized disclosure "
        "and use of Confidential Information discussed in connection with a potential business relationship.",
        body_style
    ))

    story.append(Paragraph("1. Definition of Confidential Information", h2_style))
    story.append(Paragraph(
        "\"Confidential Information\" refers to any proprietary information, technical data, trade secrets, software code, "
        "know-how, product roadmaps, customer lists, financial forecasts, and business strategies disclosed by one Party "
        "to the other, whether orally, in writing, or electronically.",
        body_style
    ))

    story.append(Paragraph("2. Obligations of Receiving Party", h2_style))
    story.append(Paragraph(
        "The Receiving Party agrees to: (a) hold Confidential Information in strict confidence; (b) exercise at least reasonable "
        "care to prevent unauthorized disclosure; (c) use Confidential Information exclusively for evaluating the business relationship; "
        "and (d) not reverse-engineer, decompile, or copy any confidential assets without express written consent.",
        body_style
    ))

    story.append(Paragraph("3. Term & Termination", h2_style))
    story.append(Paragraph(
        "This Agreement and the obligations hereunder shall survive for a period of two (2) years from the date of execution, "
        "or until such time as the Confidential Information enters the public domain through no fault of the Receiving Party.",
        body_style
    ))

    story.append(Paragraph("4. Governing Law and Execution", h2_style))
    story.append(Paragraph(
        "This Agreement shall be governed by the laws of the State of Delaware. The Parties consent to the validity and "
        "enforceability of electronic signatures affixed via DocuSign or compliant digital signing applications under the "
        "federal Electronic Signatures in Global and National Commerce Act (ESIGN) and Uniform Electronic Transactions Act (UETA).",
        body_style
    ))

    story.append(Spacer(1, 30))
    story.append(Paragraph("<b>IN WITNESS WHEREOF</b>, the Parties have executed this Mutual Non-Disclosure Agreement:", body_style))
    story.append(Spacer(1, 15))

    # Signature layout table
    sig_data = [
        [
            Paragraph("<b>DISCLOSING PARTY (Party A)</b>", body_style),
            Paragraph("<b>RECEIVING PARTY (Party B)</b>", body_style)
        ],
        [
            Paragraph("By: _______________________________<br/>Name: ____________________________<br/>Title: ____________________________<br/>Date: ____________________________", body_style),
            Paragraph("By: _______________________________<br/>Name: ____________________________<br/>Title: ____________________________<br/>Date: ____________________________", body_style)
        ]
    ]
    t = Table(sig_data, colWidths=[240, 240])
    t.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t)

    doc.build(story)

def create_offer_letter(output_path: str):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0f766e'),
        alignment=0,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=15,
        textColor=colors.HexColor('#1e293b'),
        spaceAfter=10
    )

    story = []
    story.append(Paragraph("VERTEX TECHNOLOGIES INC.", title_style))
    story.append(Paragraph("EMPLOYMENT OFFER & APPOINTMENT LETTER", ParagraphStyle('Sub', parent=body_style, fontName='Helvetica-Bold', textColor=colors.HexColor('#475569'))))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0f766e'), spaceAfter=16))

    story.append(Paragraph("Dear Candidate,", body_style))
    story.append(Paragraph(
        "We are thrilled to offer you the position of <b>Senior Software Architect</b> at Vertex Technologies Inc. "
        "We were exceptionally impressed with your technical background, leadership experience, and product vision, "
        "and we believe you will play a pivotal role in shaping our next-generation platform.",
        body_style
    ))

    story.append(Paragraph("<b>Position Details:</b>", body_style))
    story.append(Paragraph("• <b>Title:</b> Senior Software Architect<br/>• <b>Department:</b> Engineering & Platform Infrastructure<br/>• <b>Start Date:</b> First Monday of next month<br/>• <b>Base Salary:</b> $165,000 per annum, paid bi-weekly<br/>• <b>Equity Grant:</b> 25,000 Stock Options subject to standard 4-year vesting schedule with a 1-year cliff", body_style))

    story.append(Paragraph(
        "This offer is contingent upon your acceptance and satisfactory completion of background verification. "
        "Please indicate your acceptance by electronically signing this agreement below.",
        body_style
    ))
    story.append(Spacer(1, 40))

    sig_data = [
        [
            Paragraph("<b>FOR THE COMPANY:</b><br/><br/>By: _______________________________<br/>Sarah Jenkins, VP of Engineering<br/>Vertex Technologies Inc.", body_style),
            Paragraph("<b>CANDIDATE ACCEPTANCE:</b><br/><br/>By: _______________________________<br/>Candidate Full Name: ________________<br/>Accepted Date: ____________________", body_style)
        ]
    ]
    t = Table(sig_data, colWidths=[240, 240])
    t.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t)

    doc.build(story)

def create_consulting_agreement(output_path: str):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#1e1b4b'),
        alignment=1,
        spaceAfter=12
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor('#334155'),
        spaceAfter=8
    )

    story = []
    story.append(Paragraph("INDEPENDENT CONSULTING AGREEMENT", title_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#6366f1'), spaceAfter=14))

    story.append(Paragraph(
        "This Independent Consulting Agreement (\"Agreement\") is entered into between <b>Client Global Corp</b> (\"Client\") "
        "and <b>Independent Consultant</b> (\"Consultant\").",
        body_style
    ))

    story.append(Paragraph("<b>1. Services & Deliverables:</b> Consultant shall provide technical architecture, code reviews, and cloud deployment consulting services as outlined in Statement of Work #1.", body_style))
    story.append(Paragraph("<b>2. Compensation:</b> Client agrees to pay Consultant an agreed project fee of $120/hr, invoiced bi-weekly with net-15 payment terms.", body_style))
    story.append(Paragraph("<b>3. Intellectual Property:</b> All work product, inventions, and source code generated during this engagement shall be deemed \"work made for hire\" and belong exclusively to the Client.", body_style))
    story.append(Paragraph("<b>4. Independent Contractor Status:</b> Nothing in this Agreement shall create an employer-employee relationship, partnership, or joint venture.", body_style))

    story.append(Spacer(1, 30))
    sig_data = [
        [
            Paragraph("<b>CLIENT:</b><br/><br/>Signature: _________________________<br/>Name: ____________________________<br/>Date: ____________________________", body_style),
            Paragraph("<b>CONSULTANT:</b><br/><br/>Signature: _________________________<br/>Name: ____________________________<br/>Date: ____________________________", body_style)
        ]
    ]
    t = Table(sig_data, colWidths=[240, 240])
    story.append(t)

    doc.build(story)
