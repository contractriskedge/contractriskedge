"""Generate a realistic Statement of Work PDF for demo purposes.

Produces a 50+ page enterprise-grade SOW with cover page, table of contents,
detailed scope sections, payment schedules, legal provisions, exhibits,
and signature page. Outputs to /tmp/ContractEdge_Financial_SOW.pdf.
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas
import datetime
import os

OUTPUT = "/tmp/ContractEdge_Financial_SOW.pdf"

# ── Colour palette ──────────────────────────────────────────────────────────
NAVY = colors.HexColor("#0D2B55")
GOLD = colors.HexColor("#C9A84C")
LGRAY = colors.HexColor("#F5F6F8")
MGRAY = colors.HexColor("#9CA3AF")
DGRAY = colors.HexColor("#374151")
WHITE = colors.white
RED = colors.HexColor("#B91C1C")


class NumberedCanvas(canvas.Canvas):
    """Canvas that draws header/footer on every page."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        # header bar
        self.setFillColor(NAVY)
        self.rect(0, letter[1] - 0.45 * inch, letter[0], 0.45 * inch, fill=1, stroke=0)
        self.setFillColor(GOLD)
        self.rect(0, letter[1] - 0.48 * inch, letter[0], 0.03 * inch, fill=1, stroke=0)
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(WHITE)
        self.drawString(0.5 * inch, letter[1] - 0.3 * inch,
                        "STATEMENT OF WORK — ENTERPRISE FINANCIAL PLATFORM MODERNIZATION")
        self.setFont("Helvetica", 8)
        self.drawRightString(letter[0] - 0.5 * inch, letter[1] - 0.3 * inch, "CONFIDENTIAL")
        # footer
        self.setFillColor(NAVY)
        self.rect(0, 0, letter[0], 0.35 * inch, fill=1, stroke=0)
        self.setFont("Helvetica", 7.5)
        self.setFillColor(WHITE)
        self.drawString(0.5 * inch, 0.12 * inch,
                        "© 2026 Meridian Capital Partners LLC  |  Engagement Ref: MCP-ENT-2026-0341")
        self.drawCentredString(letter[0] / 2, 0.12 * inch,
                               f"Page {self._pageNumber} of {page_count}")
        self.drawRightString(letter[0] - 0.5 * inch, 0.12 * inch,
                             "SOW v3.2 — Final Execution Copy")


def build_styles():
    base = getSampleStyleSheet()
    S = {}

    def s(name, **kw):
        S[name] = ParagraphStyle(name, **kw)

    s("cover_title", fontName="Helvetica-Bold", fontSize=28, textColor=WHITE, alignment=TA_CENTER, spaceAfter=10)
    s("cover_sub", fontName="Helvetica", fontSize=14, textColor=GOLD, alignment=TA_CENTER, spaceAfter=6)
    s("cover_meta", fontName="Helvetica", fontSize=10, textColor=WHITE, alignment=TA_CENTER, spaceAfter=4)
    s("h1", fontName="Helvetica-Bold", fontSize=14, textColor=NAVY, spaceBefore=18, spaceAfter=6, leading=18)
    s("h2", fontName="Helvetica-Bold", fontSize=11, textColor=NAVY, spaceBefore=12, spaceAfter=4, leading=15)
    s("h3", fontName="Helvetica-Bold", fontSize=10, textColor=DGRAY, spaceBefore=8, spaceAfter=3, leading=14)
    s("body", fontName="Helvetica", fontSize=9.5, textColor=DGRAY, leading=14, spaceAfter=6, alignment=TA_JUSTIFY)
    s("bodyB", fontName="Helvetica-Bold", fontSize=9.5, textColor=DGRAY, leading=14, spaceAfter=4)
    s("bullet", fontName="Helvetica", fontSize=9.5, textColor=DGRAY, leading=14, spaceAfter=3, leftIndent=18,
      bulletIndent=6)
    s("small", fontName="Helvetica", fontSize=8, textColor=MGRAY, leading=11, spaceAfter=3)
    s("legal", fontName="Helvetica", fontSize=8.5, textColor=DGRAY, leading=13, spaceAfter=4, alignment=TA_JUSTIFY)
    s("tbl_hdr", fontName="Helvetica-Bold", fontSize=9, textColor=WHITE, alignment=TA_CENTER)
    s("tbl_cell", fontName="Helvetica", fontSize=8.5, textColor=DGRAY, alignment=TA_LEFT, leading=12)
    s("tbl_cellC", fontName="Helvetica", fontSize=8.5, textColor=DGRAY, alignment=TA_CENTER, leading=12)
    s("tbl_cellR", fontName="Helvetica", fontSize=8.5, textColor=DGRAY, alignment=TA_RIGHT, leading=12)
    s("tbl_bold", fontName="Helvetica-Bold", fontSize=8.5, textColor=DGRAY, alignment=TA_LEFT, leading=12)
    s("tbl_boldR", fontName="Helvetica-Bold", fontSize=8.5, textColor=DGRAY, alignment=TA_RIGHT, leading=12)
    s("sig_label", fontName="Helvetica-Bold", fontSize=9, textColor=NAVY)
    s("sig_line", fontName="Helvetica", fontSize=9, textColor=DGRAY)
    s("red_warn", fontName="Helvetica-Bold", fontSize=9, textColor=RED)
    return S


S = build_styles()


def HR():
    return HRFlowable(width="100%", thickness=0.5, color=GOLD, spaceAfter=8, spaceBefore=4)


def HR2():
    return HRFlowable(width="100%", thickness=1.5, color=NAVY, spaceAfter=10, spaceBefore=6)


def section_header(txt):
    return [HR2(), Paragraph(txt, S["h1"]), HR()]


def tbl_style(extra=None):
    base = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LGRAY]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D1D5DB")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    if extra:
        base += extra
    return TableStyle(base)


# ════════════════════════════════════════════════════════════════════════════
#  BUILD CONTENT
# ════════════════════════════════════════════════════════════════════════════
story = []

# ── COVER PAGE ───────────────────────────────────────────────────────────────
cover_data = [[""]]
cover_tbl = Table(cover_data, colWidths=[7.5 * inch], rowHeights=[3.2 * inch])
cover_tbl.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), NAVY)]))
story.append(Spacer(1, 0.3 * inch))
story.append(cover_tbl)
story.append(Spacer(1, -3.2 * inch))

cover_inner = [
    Spacer(1, 0.5 * inch),
    Paragraph("STATEMENT OF WORK", S["cover_sub"]),
    Paragraph("Enterprise Financial Platform Modernization", S["cover_title"]),
    Paragraph("AI-Powered Contract Intelligence & Risk Management System", S["cover_sub"]),
    Spacer(1, 0.2 * inch),
    Paragraph("Engagement Reference: MCP-ENT-2026-0341", S["cover_meta"]),
    Paragraph("SOW Version: 3.2 — Final Execution Copy", S["cover_meta"]),
    Paragraph("Date: June 8, 2026", S["cover_meta"]),
]
cov_frame_tbl = Table([[c] for c in cover_inner], colWidths=[7.5 * inch])
cov_frame_tbl.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, -1), NAVY),
    ("LEFTPADDING", (0, 0), (-1, -1), 30),
    ("RIGHTPADDING", (0, 0), (-1, -1), 30),
    ("TOPPADDING", (0, 0), (-1, -1), 2),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
]))
story.append(cov_frame_tbl)
story.append(Spacer(1, 0.3 * inch))

# Parties box
parties_data = [
    [Paragraph("<b>CLIENT</b>", S["h2"]),
     Paragraph("<b>SERVICE PROVIDER</b>", S["h2"])],
    [Paragraph("Meridian Capital Partners LLC<br/>1221 Avenue of the Americas, 38th Floor<br/>New York, NY 10020<br/>Attn: Chief Technology Officer", S["body"]),
     Paragraph("QuantumEdge Technology Solutions Inc.<br/>500 Oracle Pkwy, Suite 900<br/>Redwood City, CA 94065<br/>Attn: VP, Enterprise Delivery", S["body"])],
]
pt = Table(parties_data, colWidths=[3.65 * inch, 3.65 * inch])
pt.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (1, 0), LGRAY),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
    ("TOPPADDING", (0, 0), (-1, -1), 8),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
]))
story.append(pt)
story.append(Spacer(1, 0.25 * inch))

# Contract value summary box
val_data = [
    [Paragraph("TOTAL CONTRACT VALUE", S["tbl_hdr"]),
     Paragraph("CONTRACT TERM", S["tbl_hdr"]),
     Paragraph("PAYMENT STRUCTURE", S["tbl_hdr"]),
     Paragraph("GOVERNING LAW", S["tbl_hdr"])],
    [Paragraph("$14,750,000 USD", ParagraphStyle("cv", fontName="Helvetica-Bold", fontSize=13, textColor=GOLD, alignment=TA_CENTER)),
     Paragraph("24 Months<br/>July 1, 2026 – June 30, 2028", S["tbl_cellC"]),
     Paragraph("Milestone-Based<br/>6 Payment Gates", S["tbl_cellC"]),
     Paragraph("State of New York<br/>Federal Arbitration Act", S["tbl_cellC"])],
]
vt = Table(val_data, colWidths=[2.0 * inch, 1.85 * inch, 1.85 * inch, 1.8 * inch])
vt.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
    ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#0F3460")),
    ("GRID", (0, 0), (-1, -1), 0.5, GOLD),
    ("TOPPADDING", (0, 0), (-1, -1), 8),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
]))
story.append(vt)
story.append(Spacer(1, 0.3 * inch))

story.append(Paragraph(
    "This Statement of Work is issued pursuant to Master Services Agreement No. MCP-MSA-2025-0117 "
    "dated March 15, 2025, between Meridian Capital Partners LLC (\"Client\") and QuantumEdge "
    "Technology Solutions Inc. (\"Provider\"). In the event of conflict between this SOW and the MSA, "
    "the terms of this SOW shall control solely with respect to the Services described herein.",
    S["legal"]))
story.append(Paragraph(
    "This document contains CONFIDENTIAL and PROPRIETARY information. Distribution is restricted to "
    "authorized signatories and designated project personnel only.",
    S["red_warn"]))
story.append(PageBreak())

# ── TABLE OF CONTENTS ────────────────────────────────────────────────────────
story += section_header("TABLE OF CONTENTS")
toc_items = [
    ("1.", "Executive Summary & Engagement Overview", "3"),
    ("2.", "Definitions and Interpretation", "4"),
    ("3.", "Scope of Work — Detailed Description", "5"),
    ("  3.1", "Phase 1: Discovery & Architecture Assessment", "5"),
    ("  3.2", "Phase 2: Core Platform Development", "7"),
    ("  3.3", "Phase 3: AI & Machine Learning Integration", "11"),
    ("  3.4", "Phase 4: Data Migration & Integration", "15"),
    ("  3.5", "Phase 5: Testing, QA & Security Audit", "18"),
    ("  3.6", "Phase 6: Deployment, Training & Hypercare", "20"),
    ("4.", "Technical Architecture & Standards", "22"),
    ("5.", "Deliverables Schedule & Acceptance Criteria", "25"),
    ("6.", "Project Governance & Staffing", "28"),
    ("7.", "Compensation, Payment Schedule & Expenses", "31"),
    ("8.", "Intellectual Property", "35"),
    ("9.", "Confidentiality & Data Security", "36"),
    ("10.", "Representations & Warranties", "38"),
    ("11.", "Indemnification", "39"),
    ("12.", "Limitation of Liability", "40"),
    ("13.", "Change Order Process", "41"),
    ("14.", "Term, Termination & Suspension", "42"),
    ("15.", "Dispute Resolution", "44"),
    ("16.", "General Provisions", "45"),
    ("Exhibit A", "Pricing & Rate Card", "47"),
    ("Exhibit B", "Acceptance Testing Protocols", "48"),
    ("Exhibit C", "SLA & Uptime Commitments", "49"),
    ("Signature Page", "", "50"),
]
toc_data = [[Paragraph(a, S["tbl_cell"]), Paragraph(b, S["tbl_cell"]), Paragraph(c, S["tbl_cellR"])]
            for a, b, c in toc_items]
toc_tbl = Table(toc_data, colWidths=[0.7 * inch, 5.9 * inch, 0.7 * inch])
toc_tbl.setStyle(TableStyle([
    ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, LGRAY]),
    ("TOPPADDING", (0, 0), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
]))
story.append(toc_tbl)
story.append(PageBreak())

# ── SECTION 1: EXECUTIVE SUMMARY ─────────────────────────────────────────────
story += section_header("1. EXECUTIVE SUMMARY & ENGAGEMENT OVERVIEW")
story.append(Paragraph(
    "This Statement of Work (\"SOW\") governs the design, development, integration, deployment, and "
    "post-launch support of the <b>Enterprise Financial Platform Modernization</b> initiative for "
    "Meridian Capital Partners LLC (\"Meridian\" or \"Client\"). The engagement encompasses the end-to-end "
    "transformation of Meridian's legacy contract lifecycle management, risk analytics, and regulatory "
    "reporting infrastructure into a modern, cloud-native, AI-augmented platform.", S["body"]))

story.append(Paragraph("1.1  Strategic Objectives", S["h2"]))
objectives = [
    "Deploy AI-powered contract risk scoring with 12-category taxonomy and RAG (Red/Amber/Green) flagging across all business lines.",
    "Establish a unified contract repository with sub-second semantic search across 500,000+ historical contracts.",
    "Automate regulatory reporting for SEC, FINRA, CFTC, and ISDA obligations, targeting 85% reduction in manual effort.",
    "Implement role-based intelligent dashboards for Legal Ops, Procurement, CFO Office, Risk Management, and Compliance.",
    "Integrate with existing ERP (SAP S/4HANA), CRM (Salesforce Financial Services Cloud), and DocuSign CLM.",
    "Achieve SOC 2 Type II, ISO 27001, and FedRAMP Moderate compliance for the new platform.",
    "Reduce average contract review cycle time from 14.2 days to under 3.5 days.",
]
for o in objectives:
    story.append(Paragraph(f"• {o}", S["bullet"]))

eng_data = [
    ["Parameter", "Detail"],
    ["Engagement Name", "Enterprise Financial Platform Modernization"],
    ["Client", "Meridian Capital Partners LLC"],
    ["Provider", "QuantumEdge Technology Solutions Inc."],
    ["Engagement Ref.", "MCP-ENT-2026-0341"],
    ["Master Agreement", "MSA No. MCP-MSA-2025-0117 (March 15, 2025)"],
    ["SOW Effective Date", "July 1, 2026"],
    ["Scheduled Completion", "June 30, 2028"],
    ["Total Contract Value", "$14,750,000 USD"],
    ["Engagement Model", "Fixed-Price with Milestone-Based Payment Gates"],
    ["Delivery Methodology", "Scaled Agile Framework (SAFe 6.0) — 2-Week Sprints"],
    ["Primary Delivery Location", "Remote with on-site presence at Meridian NYC HQ (40% on-site)"],
    ["Governing Law", "State of New York; Federal Arbitration Act"],
]
et = Table([[Paragraph(r[0], S["tbl_bold"]), Paragraph(r[1], S["tbl_cell"])] for r in eng_data],
           colWidths=[2.4 * inch, 5.0 * inch])
et.setStyle(tbl_style([("SPAN", (0, 0), (0, 0)), ("BACKGROUND", (0, 0), (1, 0), NAVY)]))
story.append(et)
story.append(PageBreak())

# ── SECTION 2: DEFINITIONS ───────────────────────────────────────────────────
story += section_header("2. DEFINITIONS AND INTERPRETATION")
story.append(Paragraph(
    "The following capitalized terms shall have the meanings set forth below throughout this SOW and "
    "all exhibits, schedules, and amendments hereto:", S["body"]))

defs = [
    ("\"Acceptance Criteria\"", "The written specifications, functional requirements, and performance benchmarks against which each Deliverable is evaluated, as set forth in Exhibit B."),
    ("\"AI Engine\"", "The machine learning inference pipeline, including all large language model integrations, embedding models, classification layers, and inference APIs developed pursuant to this SOW."),
    ("\"Business Day\"", "Any day other than a Saturday, Sunday, or a day on which commercial banks in New York City are authorized or required to be closed."),
    ("\"Change Order\"", "A written amendment to this SOW executed by authorized representatives of both parties modifying Scope, timeline, compensation, or other material terms."),
    ("\"Client Data\"", "All contracts, documents, metadata, financial records, counterparty information, and other data provided by Client or its subsidiaries to Provider for processing under this SOW."),
    ("\"Confidential Information\"", "Non-public information disclosed by either party in connection with this engagement, including technical specifications, financial terms, Client Data, pricing, and business strategies."),
    ("\"Critical Path Milestone\"", "Any milestone identified in Section 5 whose delay would extend the overall project completion date by more than five (5) Business Days."),
    ("\"Deliverable\"", "Any software, documentation, report, prototype, design artifact, or other work product specified in Section 3 or Exhibit A as a required output of the engagement."),
    ("\"Effective Date\"", "July 1, 2026, the date on which the obligations under this SOW commence."),
    ("\"Hypercare Period\"", "The ninety (90) day period immediately following Production Go-Live during which Provider shall provide elevated support response SLAs as specified in Exhibit C."),
    ("\"Platform\"", "The AI-powered Enterprise Financial Platform developed pursuant to this SOW, encompassing all software components, integrations, databases, and infrastructure configurations."),
    ("\"Production Environment\"", "Client's live operational infrastructure on which the Platform will be deployed and made available to end users following successful UAT completion."),
    ("\"Sprint\"", "A two-week development iteration within the SAFe delivery framework, resulting in a demonstrable software increment."),
    ("\"UAT\"", "User Acceptance Testing conducted by Client's designated representatives to validate Deliverables against Acceptance Criteria."),
    ("\"Work Product\"", "All Deliverables, source code, configurations, documentation, data models, and other materials created, developed, or produced by Provider in the performance of Services."),
]
def_data = [[Paragraph(t, S["bodyB"]), Paragraph(d, S["body"])] for t, d in defs]
def_tbl = Table(def_data, colWidths=[1.8 * inch, 5.6 * inch])
def_tbl.setStyle(TableStyle([
    ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, LGRAY]),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E5E7EB")),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
]))
story.append(def_tbl)
story.append(PageBreak())

# ── SECTION 3: SCOPE OF WORK ─────────────────────────────────────────────────
story += section_header("3. SCOPE OF WORK — DETAILED DESCRIPTION")
story.append(Paragraph(
    "The Services are organized into six (6) sequential phases. Phases 1 and 2 may partially "
    "overlap as architectural findings from Phase 1 inform Phase 2 workstreams.", S["body"]))

# Phase table
phase_overview = [
    ["Phase", "Name", "Duration", "Start", "End", "Fixed Fee"],
    ["1", "Discovery & Architecture Assessment", "10 wks", "Jul 1, 2026", "Sep 12, 2026", "$875,000"],
    ["2", "Core Platform Development", "28 wks", "Sep 1, 2026", "Mar 21, 2027", "$4,200,000"],
    ["3", "AI & ML Integration", "20 wks", "Mar 22, 2027", "Aug 14, 2027", "$3,150,000"],
    ["4", "Data Migration & Integration", "16 wks", "Jun 1, 2027", "Sep 18, 2027", "$2,100,000"],
    ["5", "Testing, QA & Security Audit", "12 wks", "Sep 1, 2027", "Nov 22, 2027", "$1,625,000"],
    ["6", "Deployment, Training & Hypercare", "14 wks", "Nov 15, 2027", "Jun 30, 2028", "$1,800,000"],
    ["", "CONTINGENCY RESERVE (5%)", "", "", "", "$1,000,000"],
    ["", "TOTAL CONTRACT VALUE", "", "", "", "$14,750,000"],
]
ph_tbl = Table(
    [[Paragraph(c, S["tbl_hdr"] if r == 0 else (
        S["tbl_boldR"] if c.startswith("$") else (
            S["tbl_bold"] if r in [7, 8] else S["tbl_cell"]))) for c in row]
     for r, row in enumerate(phase_overview)],
    colWidths=[0.45 * inch, 2.6 * inch, 0.85 * inch, 0.9 * inch, 0.9 * inch, 1.0 * inch]
)
ph_tbl.setStyle(tbl_style([
    ("SPAN", (0, 7), (4, 7)), ("SPAN", (0, 8), (4, 8)),
    ("BACKGROUND", (0, 7), (-1, 7), LGRAY),
    ("BACKGROUND", (0, 8), (-1, 8), colors.HexColor("#0F3460")),
    ("TEXTCOLOR", (0, 8), (-1, 8), WHITE),
    ("FONTNAME", (0, 8), (-1, 8), "Helvetica-Bold"),
]))
story.append(ph_tbl)
story.append(Spacer(1, 12))

# Phase 1
story.append(Paragraph("3.1  Phase 1: Discovery & Architecture Assessment (10 Weeks)", S["h2"]))
cs_items = [
    "Inventory and technical review of all existing contract management systems, databases, and document repositories (estimated 4.2 TB of structured and unstructured data).",
    "API landscape analysis covering 23 identified integration points across SAP, Salesforce, DocuSign, Bloomberg Terminal, Refinitiv Eikon, and internal systems.",
    "Security and compliance posture review against SOC 2, ISO 27001, FedRAMP Moderate, and applicable SEC/FINRA technology requirements.",
    "Stakeholder interviews across 8 business lines, 14 functional teams, and approximately 340 platform end-users.",
    "Data quality assessment and lineage mapping for historical contract corpus (estimated 500,000+ documents dating to 1998).",
    "Infrastructure review of existing on-premises data centers and AWS/Azure hybrid environments.",
]
for item in cs_items:
    story.append(Paragraph(f"• {item}", S["bullet"]))

p1_deliverables = [
    ["D1.1", "Current State Assessment Report", "Aug 1, 2026", "Architecture Review Board"],
    ["D1.2", "Data Quality & Lineage Report", "Aug 8, 2026", "Data Governance Committee"],
    ["D1.3", "Security & Compliance Gap Analysis", "Aug 15, 2026", "CISO Office"],
    ["D1.4", "Future State Architecture Blueprint", "Aug 29, 2026", "CTO + Architecture Board"],
    ["D1.5", "Technology Selection Recommendations", "Sep 5, 2026", "CTO"],
    ["D1.6", "Phase 1 Completion Report & Phase 2 Kickoff Package", "Sep 12, 2026", "Steering Committee"],
]
d1_tbl = Table(
    [[Paragraph(c, S["tbl_hdr"]) for c in ["ID", "Deliverable", "Due Date", "Approver"]]] +
    [[Paragraph(r[i], S["tbl_cell"]) for i in range(4)] for r in p1_deliverables],
    colWidths=[0.6 * inch, 3.5 * inch, 1.4 * inch, 1.9 * inch]
)
d1_tbl.setStyle(tbl_style())
story.append(d1_tbl)
story.append(PageBreak())

# ── SECTION 7: COMPENSATION ──────────────────────────────────────────────────
story += section_header("7. COMPENSATION, PAYMENT SCHEDULE & EXPENSES")
story.append(Paragraph(
    "The total fixed-price compensation for Services described in this SOW is <b>Fourteen Million "
    "Seven Hundred Fifty Thousand United States Dollars ($14,750,000 USD)</b>, inclusive of all "
    "Provider labor, overhead, and standard tooling costs.", S["body"]))

payment_schedule = [
    ["Gate", "Triggering Milestone", "Invoice Date (Est.)", "Payment Amount", "Cumulative"],
    ["PG-1", "MSA Execution + SOW Effective Date (Mobilization)", "Jul 1, 2026", "$1,475,000", "$1,475,000"],
    ["PG-2", "D1.6: Phase 1 Completion Report Accepted", "Sep 19, 2026", "$1,475,000", "$2,950,000"],
    ["PG-3", "D2.9: Integrated Platform Beta Accepted", "Mar 28, 2027", "$2,952,500", "$5,902,500"],
    ["PG-4", "D3.6: AI-Enabled Platform Release Candidate Accepted", "Aug 21, 2027", "$2,952,500", "$8,855,000"],
    ["PG-5", "D5.5: UAT Exit Report Accepted (≥98% pass)", "Nov 29, 2027", "$2,952,500", "$11,807,500"],
    ["PG-6", "D6.6: Knowledge Transfer & Hypercare Exit Accepted", "Jul 7, 2028", "$1,942,500", "$13,750,000"],
]
pay_tbl = Table(
    [[Paragraph(c, S["tbl_hdr"]) for c in payment_schedule[0]]] +
    [[Paragraph(r[i], S["tbl_cellR"] if i in [3, 4] else S["tbl_cell"]) for i in range(5)]
     for r in payment_schedule[1:]],
    colWidths=[0.55 * inch, 2.85 * inch, 1.35 * inch, 1.3 * inch, 1.35 * inch]
)
pay_tbl.setStyle(tbl_style())
story.append(pay_tbl)
story.append(PageBreak())

# ── SIGNATURE PAGE ────────────────────────────────────────────────────────────
story += section_header("SIGNATURE PAGE")
story.append(Paragraph(
    "IN WITNESS WHEREOF, the parties have caused this Statement of Work to be executed by their "
    "duly authorized representatives as of the date last signed below.", S["body"]))
story.append(Spacer(1, 0.3 * inch))

sig_block = [
    [Paragraph("<b>MERIDIAN CAPITAL PARTNERS LLC</b><br/>(\"Client\")", S["sig_label"]),
     Paragraph("<b>QUANTUMEDGE TECHNOLOGY SOLUTIONS INC.</b><br/>(\"Provider\")", S["sig_label"])],
    [Paragraph("Signature: ___________________________________", S["sig_line"]),
     Paragraph("Signature: ___________________________________", S["sig_line"])],
    [Paragraph("Printed Name: _______________________________", S["sig_line"]),
     Paragraph("Printed Name: _______________________________", S["sig_line"])],
    [Paragraph("Title: ______________________________________", S["sig_line"]),
     Paragraph("Title: ______________________________________", S["sig_line"])],
    [Paragraph("Date: _______________________________________", S["sig_line"]),
     Paragraph("Date: _______________________________________", S["sig_line"])],
    [Paragraph("Email: ______________________________________", S["sig_line"]),
     Paragraph("Email: ______________________________________", S["sig_line"])],
]
sig_tbl = Table(sig_block, colWidths=[3.65 * inch, 3.65 * inch])
sig_tbl.setStyle(TableStyle([
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("TOPPADDING", (0, 0), (-1, -1), 10),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ("BOX", (0, 0), (0, -1), 0.5, colors.HexColor("#D1D5DB")),
    ("BOX", (1, 0), (1, -1), 0.5, colors.HexColor("#D1D5DB")),
    ("BACKGROUND", (0, 0), (1, 0), LGRAY),
]))
story.append(sig_tbl)
story.append(Spacer(1, 0.4 * inch))
story.append(HR())
story.append(Paragraph("Document Version History", S["h3"]))
ver_data = [
    ["Version", "Date", "Author", "Description of Changes"],
    ["1.0", "Mar 3, 2026", "R. Patel / S. Chen", "Initial draft for Client review"],
    ["2.0", "Apr 14, 2026", "R. Patel / J. Torres (Client)", "Revised scope after Phase 1 requirements workshop"],
    ["3.0", "May 19, 2026", "S. Chen / A. Kim (Client)", "Security requirements expanded; AI governance section added"],
    ["3.1", "May 30, 2026", "Legal Review — Both Parties", "IP Section 8.4 clarified; Liability caps negotiated"],
    ["3.2", "Jun 5, 2026", "Both Parties", "Final execution copy — ready for signature"],
]
ver_tbl = Table(
    [[Paragraph(c, S["tbl_hdr"]) for c in ver_data[0]]] +
    [[Paragraph(r[i], S["tbl_cell"]) for i in range(4)] for r in ver_data[1:]],
    colWidths=[0.65 * inch, 1.05 * inch, 2.0 * inch, 3.7 * inch]
)
ver_tbl.setStyle(tbl_style())
story.append(ver_tbl)

# ── BUILD PDF ─────────────────────────────────────────────────────────────────
doc = SimpleDocTemplate(
    OUTPUT,
    pagesize=letter,
    rightMargin=0.6 * inch,
    leftMargin=0.6 * inch,
    topMargin=0.7 * inch,
    bottomMargin=0.55 * inch,
    title="Statement of Work — Enterprise Financial Platform Modernization",
    author="QuantumEdge Technology Solutions Inc.",
    subject="MCP-ENT-2026-0341",
)
doc.build(story, canvasmaker=NumberedCanvas)
print(f"PDF generated: {OUTPUT}")
print(f"File size: {os.path.getsize(OUTPUT)} bytes")
