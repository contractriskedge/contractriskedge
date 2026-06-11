"""
Generate a Word document (.docx) containing the ContractEdge contract lifecycle
reference — all statuses, where they're visible, required actions, and workflow rules.

Usage:
    cd /Volumes/ContractEdge/ContractRiskEdge
    python generate_lifecycle_docx.py
    # Outputs: ContractEdge_Lifecycle_Reference.docx
"""

from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml
import datetime

doc = Document()

# ── Styles ────────────────────────────────────────────────────────

style = doc.styles["Normal"]
font = style.font
font.name = "Calibri"
font.size = Pt(10)

# ── Title Page ─────────────────────────────────────────────────────

doc.add_paragraph()
doc.add_paragraph()
title = doc.add_paragraph()
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = title.add_run("ContractEdge\nContract Lifecycle Reference")
run.bold = True
run.font.size = Pt(26)
run.font.color.rgb = RGBColor(0x1E, 0x29, 0x3B)

subtitle = doc.add_paragraph()
subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = subtitle.add_run(f"Generated: {datetime.date.today().strftime('%B %d, %Y')}")
run.font.size = Pt(12)
run.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)

doc.add_paragraph()
doc.add_paragraph()

# ── Table of Contents ─────────────────────────────────────────────

doc.add_heading("Table of Contents", level=1)
toc_items = [
    "1. Lifecycle Stages Overview",
    "2. Status Reference Table",
    "3. Where to See Each Status",
    "4. Required Actions by Status",
    "5. Lifecycle Flow Diagram",
    "6. Key Business Rules",
    "7. Obligation Status Reference",
    "   - Obligation Status Table",
    "   - Obligation Lifecycle Flow",
    "   - Obligation Completion Requirements",
    "8. Redline Coverage Reference",
    "9. Status Transition Matrix",
]
for item in toc_items:
    p = doc.add_paragraph(item)
    p.paragraph_format.space_after = Pt(2)

doc.add_page_break()

# ── 1. Overview ────────────────────────────────────────────────────

doc.add_heading("1. Lifecycle Stages Overview", level=1)
doc.add_paragraph(
    "Every contract in ContractEdge progresses through a defined lifecycle from creation "
    "to closure. Each stage has a specific status, visibility in the UI, and required "
    "user actions. This document serves as the complete reference for all lifecycle states."
)

# ── 2. Status Reference Table ──────────────────────────────────────

doc.add_heading("2. Status Reference Table", level=1)

headers = ["Stage", "Status", "Badge Color", "Description"]
rows = [
    ["Draft", "draft, ai_analyzed", "⚪ Gray", "Contract uploaded, AI analysis complete. Waiting for reviewer assignment."],
    ["In Review", "in_review, legal_review, security_review, procurement_review, negotiation, escalated", "🔵 Blue", "Reviewer is analyzing findings, redlines, and policy violations."],
    ["Approved", "approved", "🔵 Blue", "Review approved by authorized user. Ready to finalize."],
    ["Rejected", "rejected", "🔴 Red", "Review rejected with reason. Terminal state — contract is returned."],
    ["Finalized", "finalized", "🔵 Blue", "Document version locked. Ready to execute."],
    ["Active", "executed", "🟢 Green", "Contract is live. Obligations are being tracked and monitored."],
    ["Expiring Soon", "executed + SLA < 30 days", "🟡 Yellow", "Contract approaching expiration. Renewal review recommended."],
    ["Expired", "executed + SLA overdue", "🔴 Red", "Contract past its expiration date. Close required."],
    ["Closed", "archived", "⚫ Gray", "Contract lifecycle complete. Terminal state."],
]

table = doc.add_table(rows=1 + len(rows), cols=4)
table.style = "Light Grid Accent 1"
table.alignment = WD_TABLE_ALIGNMENT.CENTER

# Header row
for i, h in enumerate(headers):
    cell = table.rows[0].cells[i]
    cell.text = h
    for paragraph in cell.paragraphs:
        for run in paragraph.runs:
            run.bold = True
            run.font.size = Pt(9)

# Data rows
for r_idx, row_data in enumerate(rows):
    for c_idx, cell_text in enumerate(row_data):
        cell = table.rows[r_idx + 1].cells[c_idx]
        cell.text = cell_text
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.font.size = Pt(9)

# Set column widths
for row in table.rows:
    row.cells[0].width = Cm(3)
    row.cells[1].width = Cm(4.5)
    row.cells[2].width = Cm(2.5)
    row.cells[3].width = Cm(7)

doc.add_paragraph()

# ── 3. Where to See Each Status ────────────────────────────────────

doc.add_heading("3. Where to See Each Status", level=1)

location_headers = ["Location", "What's Shown", "Details"]
location_rows = [
    ["Review Queue\n(/reviews)", "Lifecycle badge + SLA status", "Shows Active, Expired, Closed, Approved, Finalized badges per row. Color-coded by lifecycle stage."],
    ["Contract 360\n(/contracts/{id})", "Status badge in header\n+ MetadataPanel sidebar", "Color-coded badge in the action bar. 'Next Action' hint in the right sidebar MetadataPanel."],
    ["Review Workspace\n(/reviews/ai-workspace)", "Status in context indicator", "Shows current review status with color badge in the top command bar."],
    ["Review Actions Bar", "Context-sensitive action buttons", "Buttons change based on current status: Approve/Reject during review, Finalize when approved, Close when executed."],
]

table2 = doc.add_table(rows=1 + len(location_rows), cols=3)
table2.style = "Light Grid Accent 1"
table2.alignment = WD_TABLE_ALIGNMENT.CENTER

for i, h in enumerate(location_headers):
    cell = table2.rows[0].cells[i]
    cell.text = h
    for paragraph in cell.paragraphs:
        for run in paragraph.runs:
            run.bold = True
            run.font.size = Pt(9)

for r_idx, row_data in enumerate(location_rows):
    for c_idx, cell_text in enumerate(row_data):
        cell = table2.rows[r_idx + 1].cells[c_idx]
        cell.text = cell_text
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.font.size = Pt(9)

for row in table2.rows:
    row.cells[0].width = Cm(3.5)
    row.cells[1].width = Cm(4)
    row.cells[2].width = Cm(9.5)

doc.add_paragraph()

# ── 4. Required Actions by Status ──────────────────────────────────

doc.add_heading("4. Required Actions by Status", level=1)

action_headers = ["Current Status", "Next Action", "Available Button(s)", "Location"]
action_rows = [
    ["draft, ai_analyzed", "Assign a reviewer to start the review process", "Assign", "Review Queue, Actions Bar"],
    ["in_review, legal_review, security_review, procurement_review, negotiation, escalated", "Review findings, resolve issues, then approve or reject", "Approve, Reject", "Review Queue, Workspace, Actions Bar"],
    ["approved", "Finalize to lock the document version and move to execution", "Finalize", "Contract 360, Actions Bar"],
    ["finalized", "Execute the contract (moves to Active) or cancel", "Execute, Cancel", "Contract 360, Actions Bar"],
    ["executed (Active)", "Monitor obligations until expiry. Close when complete.", "Close", "Contract 360, Actions Bar"],
    ["executed (Expiring Soon)", "Review renewal terms before expiration", "Close", "Contract 360"],
    ["executed (Expired)", "Review obligations and close the contract", "Close", "Contract 360, Actions Bar"],
    ["archived / closed", "Terminal state. No further action.", "None", "Review Queue (filtered)"],
    ["rejected", "Terminal state. Contract returned to originator.", "None (may archive)", "Review Queue (filtered)"],
]

table3 = doc.add_table(rows=1 + len(action_rows), cols=4)
table3.style = "Light Grid Accent 1"
table3.alignment = WD_TABLE_ALIGNMENT.CENTER

for i, h in enumerate(action_headers):
    cell = table3.rows[0].cells[i]
    cell.text = h
    for paragraph in cell.paragraphs:
        for run in paragraph.runs:
            run.bold = True
            run.font.size = Pt(9)

for r_idx, row_data in enumerate(action_rows):
    for c_idx, cell_text in enumerate(row_data):
        cell = table3.rows[r_idx + 1].cells[c_idx]
        cell.text = cell_text
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.font.size = Pt(9)

for row in table3.rows:
    row.cells[0].width = Cm(4)
    row.cells[1].width = Cm(6)
    row.cells[2].width = Cm(3.5)
    row.cells[3].width = Cm(3.5)

doc.add_paragraph()

# ── 5. Lifecycle Flow Diagram ──────────────────────────────────────

doc.add_heading("5. Lifecycle Flow Diagram", level=1)

flow_text = """
                        ┌─────────────┐
                        │    Draft     │
                        │ (ai_analyzed)│
                        └──────┬──────┘
                               │ Assign Reviewer
                               ▼
                        ┌─────────────┐
                        │  In Review   │
                        │ (in_review,  │
                        │  legal, etc.)│
                        └──┬──────┬───┘
                           │      │
                  Approve  │      │  Reject
                           │      ▼
                           │  ┌──────────┐
                           │  │ Rejected  │
                           │  │ (Terminal)│
                           │  └──────────┘
                           ▼
                    ┌───────────┐
                    │ Approved   │
                    └─────┬─────┘
                          │ Finalize
                          ▼
                    ┌───────────┐
                    │ Finalized  │
                    └─────┬─────┘
                          │ Execute
                          ▼
                    ┌───────────┐
                    │  Active    │
                    │ (executed) │
                    └──┬────┬───┘
                       │    │
              Expiring │    │ SLA Overdue
                       │    ▼
                       │  ┌───────────┐
                       │  │  Expired   │
                       │  └─────┬─────┘
                       │        │
                       └──┬─────┘
                          │ Close
                          ▼
                    ┌───────────┐
                    │  Closed    │
                    │ (archived) │
                    │ (Terminal) │
                    └───────────┘
"""

p = doc.add_paragraph()
run = p.add_run(flow_text.strip())
run.font.size = Pt(8)
run.font.name = "Consolas"

doc.add_paragraph()

# ── 6. Key Business Rules ──────────────────────────────────────────

doc.add_heading("6. Key Business Rules", level=1)

rules = [
    "Close Blocked by Open Obligations: A contract cannot be closed if any linked obligation has a status other than 'completed', 'closed', or 'waived'. The backend enforces this rule on the 'Close' action only — Finalize is NOT blocked by open obligations since obligations may not yet be active at that stage.",
    "Approval Requires Override for Critical Findings: If critical or high findings are unresolved, approval is blocked. An override dialog with a required reason is presented to the user instead of relying on text parsing of comments.",
    "Read-Only After Approval: Once a contract is approved, findings, redlines, and obligations become read-only. Editing requires reopening the review.",
    "Rejection Requires Reason: A rejection reason is mandatory. The backend validates this at the API level.",
    "Evidence Required for Obligation Completion: Completion notes are required when marking an obligation as completed. Evidence attachments are optional but recommended.",
    "Finalize Locks Version: Finalizing an approved review locks the current document version. No further edits to the document are allowed after finalization.",
    "Terminal States: 'archived' (closed) and 'rejected' are terminal states. No transitions out of these states are allowed by the workflow engine. Rejected → Archived is permitted as a cleanup action.",
]

for i, rule in enumerate(rules, 1):
    p = doc.add_paragraph()
    run = p.add_run(f"{i}. {rule}")
    run.font.size = Pt(10)
    p.paragraph_format.space_after = Pt(6)

doc.add_paragraph()

# ── 7. Obligation Status Reference ─────────────────────────────────

doc.add_heading("7. Obligation Status Reference", level=1)
doc.add_paragraph(
    "Obligations track post-signature commitments extracted from contract clauses. "
    "Each obligation follows its own lifecycle independent of the parent contract."
)

obl_headers = ["Obligation Status", "Badge Color", "Description", "Next Action"]
obl_rows = [
    ["draft", "⚪ Gray", "Obligation created but not yet active.", "Review and activate when contract is executed."],
    ["open", "🔵 Blue", "Obligation is active and awaiting fulfillment.", "Assign owner and track until completion."],
    ["in_progress", "🔵 Blue", "Work on the obligation has started.", "Monitor progress toward completion."],
    ["pending_supplier", "🟣 Purple", "Awaiting response or evidence from supplier/counterparty.", "Follow up with supplier. Upload evidence when received."],
    ["overdue", "🔴 Red", "Obligation past its due date.", "Escalate immediately. Send reminder to owner."],
    ["completed", "🟢 Green", "Obligation fulfilled with completion notes and evidence.", "Verify completion notes and evidence attachments."],
    ["cancelled", "⚫ Gray", "Obligation cancelled and no longer required.", "No further action. Record reason for audit."],
    ["archived", "⚫ Gray", "Obligation archived (soft-delete).", "No further action. Can be restored if needed."],
    ["waived", "⚫ Gray", "Obligation waived by authorized user.", "No further action. Record waiver reason for audit."],
]

table_obl = doc.add_table(rows=1 + len(obl_rows), cols=4)
table_obl.style = "Light Grid Accent 1"
table_obl.alignment = WD_TABLE_ALIGNMENT.CENTER

for i, h in enumerate(obl_headers):
    cell = table_obl.rows[0].cells[i]
    cell.text = h
    for paragraph in cell.paragraphs:
        for run in paragraph.runs:
            run.bold = True
            run.font.size = Pt(9)

for r_idx, row_data in enumerate(obl_rows):
    for c_idx, cell_text in enumerate(row_data):
        cell = table_obl.rows[r_idx + 1].cells[c_idx]
        cell.text = cell_text
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.font.size = Pt(9)

for row in table_obl.rows:
    row.cells[0].width = Cm(3)
    row.cells[1].width = Cm(2.5)
    row.cells[2].width = Cm(5.5)
    row.cells[3].width = Cm(6)

doc.add_paragraph()

# ── Obligation Lifecycle Flow ──────────────────────────────────────

doc.add_heading("Obligation Lifecycle Flow", level=2)

obl_flow = """
                    ┌───────────┐
                    │   Draft    │
                    └─────┬─────┘
                          │ Activate
                          ▼
                    ┌───────────┐
                    │    Open    │
                    └─────┬─────┘
                          │ Start work
                          ▼
                    ┌───────────┐
                    │In Progress │
                    └──┬────┬───┘
                       │    │
              Needs    │    │ Complete
              Supplier │    ▼
                       │  ┌───────────┐
                       │  │ Completed  │
                       │  └───────────┘
                       │
                       ▼
                ┌───────────────┐
                │Pending Supplier│
                └───────┬───────┘
                        │ Evidence received
                        ▼
                  ┌───────────┐
                  │ Completed  │
                  └───────────┘

    Any open status can also be:
    → Overdue (if past due date)
    → Cancelled (with reason)
    → Archived (soft-delete)
    → Waived (with authorization)
"""

p = doc.add_paragraph()
run = p.add_run(obl_flow.strip())
run.font.size = Pt(8)
run.font.name = "Consolas"

doc.add_paragraph()

# ── Obligation Completion Requirements ─────────────────────────────

doc.add_heading("Obligation Completion Requirements", level=2)

completion_reqs = [
    "Completion Notes (Required): User must explain how the obligation was satisfied.",
    "Completion Date (Optional, defaults to today): When the obligation was fulfilled.",
    "Evidence Attachments (Optional): Supporting documents (PDF, DOCX, images) uploaded as evidence.",
    "Completed By (Auto-recorded): The logged-in user who performed the completion.",
    "Audit Event: An OBLIGATION_COMPLETED event is recorded in the audit log.",
    "Contract Timeline: A timeline entry is created on the parent contract's activity feed.",
    "Evidence Count: The evidence_attachment_count field is updated automatically.",
]

for i, req in enumerate(completion_reqs, 1):
    p = doc.add_paragraph()
    run = p.add_run(f"{i}. {req}")
    run.font.size = Pt(10)
    p.paragraph_format.space_after = Pt(4)

doc.add_paragraph()

# ── 8. Redline Coverage Reference ─────────────────────────────────

doc.add_heading("8. Redline Coverage Reference", level=1)
doc.add_paragraph(
    "The redline generation engine maps AI-identified findings to recommended clause language. "
    "Each finding's clause_type is looked up in the mitigation template registry. "
    "If no exact match is found, a generic fallback redline is generated instead of returning an error."
)

doc.add_heading("Clause Type Coverage", level=2)

cov_headers = ["Clause Type", "Category", "Mitigation Template", "Status"]
cov_rows = [
    ["liability", "liability_indemnity", "adding_liability_cap", "✅"],
    ["indemnification", "liability_indemnity", "narrowing_indemnity_scope", "✅"],
    ["data_protection", "data_protection", "adding_dpa", "✅"],
    ["data_privacy", "data_protection", "adding_dpa", "✅"],
    ["confidentiality", "confidentiality", "broadening_confidentiality", "✅"],
    ["ip", "intellectual_property", "restricting_derivative_works", "✅"],
    ["intellectual_property", "intellectual_property", "restricting_derivative_works", "✅"],
    ["term", "term_termination", "extending_notice_period", "✅"],
    ["termination", "term_termination", "adding_for_cause_termination", "✅"],
    ["payment", "payment_audit", "adding_price_protection", "✅"],
    ["audit", "payment_audit", "adding_audit_rights", "✅"],
    ["sla", "sla_support", "adding_sla_guarantees", "✅"],
    ["support", "sla_support", "adding_service_levels", "✅"],
    ["assignment", "assignment_change_control", "adding_change_of_control", "✅"],
    ["force_majeure", "force_majeure", "clarifying_warranty_scope", "✅"],
    ["governing_law", "governing_law_jurisdiction", "clarifying_governing_law", "✅"],
    ["jurisdiction", "governing_law_jurisdiction", "clarifying_governing_law", "✅"],
    ["insurance", "insurance", "adding_liability_cap", "✅"],
    ["non_compete", "non_compete_exclusivity", "narrowing_ip_license", "✅"],
    ["exclusivity", "non_compete_exclusivity", "narrowing_ip_license", "✅"],
    ["other", "liability_indemnity", "adding_liability_cap (fallback)", "✅"],
]

table_cov = doc.add_table(rows=1 + len(cov_rows), cols=4)
table_cov.style = "Light Grid Accent 1"
table_cov.alignment = WD_TABLE_ALIGNMENT.CENTER

for i, h in enumerate(cov_headers):
    cell = table_cov.rows[0].cells[i]
    cell.text = h
    for paragraph in cell.paragraphs:
        for run in paragraph.runs:
            run.bold = True
            run.font.size = Pt(8)

for r_idx, row_data in enumerate(cov_rows):
    for c_idx, cell_text in enumerate(row_data):
        cell = table_cov.rows[r_idx + 1].cells[c_idx]
        cell.text = cell_text
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.font.size = Pt(8)

for row in table_cov.rows:
    row.cells[0].width = Cm(3)
    row.cells[1].width = Cm(4)
    row.cells[2].width = Cm(5.5)
    row.cells[3].width = Cm(1.5)

doc.add_paragraph()

doc.add_heading("Fallback Strategy", level=2)
doc.add_paragraph(
    "When a finding's clause_type does not match any known mitigation template "
    "(e.g., 'other' or a future unmapped type), the system now uses a two-level fallback:"
)
fallback_steps = [
    "Level 1 — Backend Service: If get_mitigation_effectiveness() returns no results, a generic fallback effect with zero effectiveness is created so redline generation can proceed.",
    "Level 2 — Router: If the service returns None, a generic redline is generated with a descriptive placeholder: '[Proposed clause for {mitigation_type} — please review and customize.]'",
    "Result: Every finding can now produce a redline. Coverage is 100% of known clause_types plus fallback for unknown types.",
]
for i, step in enumerate(fallback_steps, 1):
    p = doc.add_paragraph()
    run = p.add_run(f"{i}. {step}")
    run.font.size = Pt(10)
    p.paragraph_format.space_after = Pt(4)

doc.add_paragraph()

# ── 9. Status Transition Matrix ────────────────────────────────────

doc.add_heading("9. Status Transition Matrix", level=1)
doc.add_paragraph(
    "The following matrix shows all allowed transitions between statuses. "
    "A checkmark (✓) means the transition is permitted by the workflow engine."
)

trans_headers = ["From \\ To", "ai_analyzed", "in_review", "approved", "rejected", "finalized", "executed", "archived"]
trans_rows = [
    ["ai_analyzed",    "—", "✓", "—", "—", "—", "—", "✓"],
    ["in_review",      "—", "—", "✓", "✓", "—", "—", "✓"],
    ["approved",       "—", "—", "—", "—", "✓", "—", "—"],
    ["rejected",       "—", "—", "—", "—", "—", "—", "✓"],
    ["finalized",      "—", "—", "—", "—", "—", "✓", "✓"],
    ["executed",       "—", "—", "—", "—", "—", "—", "✓"],
    ["archived",       "—", "—", "—", "—", "—", "—", "—"],
]

table4 = doc.add_table(rows=1 + len(trans_rows), cols=len(trans_headers))
table4.style = "Light Grid Accent 1"
table4.alignment = WD_TABLE_ALIGNMENT.CENTER

for i, h in enumerate(trans_headers):
    cell = table4.rows[0].cells[i]
    cell.text = h
    for paragraph in cell.paragraphs:
        for run in paragraph.runs:
            run.bold = True
            run.font.size = Pt(8)

for r_idx, row_data in enumerate(trans_rows):
    for c_idx, cell_text in enumerate(row_data):
        cell = table4.rows[r_idx + 1].cells[c_idx]
        cell.text = cell_text
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.font.size = Pt(8)
                if cell_text == "✓":
                    run.font.color.rgb = RGBColor(0x16, 0xA3, 0x4A)

for row in table4.rows:
    for cell in row.cells:
        cell.width = Cm(2.5)

# ── Footer ─────────────────────────────────────────────────────────

doc.add_paragraph()
doc.add_paragraph()
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("— End of Document —")
run.font.size = Pt(10)
run.font.color.rgb = RGBColor(0x94, 0xA3, 0xB8)
run.italic = True

# ── Save ───────────────────────────────────────────────────────────

output_path = "ContractEdge_Lifecycle_Reference.docx"
doc.save(output_path)
print(f"✅ Document saved to: {output_path}")
