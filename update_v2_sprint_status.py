"""Update the V2 Sprint Plan Excel with current implementation status.

Marks V2 Improvement tasks as Done, In Progress, or To Do based on
actual codebase implementation state after Sprint 11 completion.
"""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

NAVY    = "1B3A6B"
GOLD    = "C9A84C"
WHITE   = "FFFFFF"
LTGOLD  = "FEF3C7"
LTBLUE  = "DBEAFE"
LTGREEN = "DCFCE7"
LTORANGE= "FFF7ED"
LTRED   = "FEE2E2"
GRAY1   = "F3F4F6"
GRAY2   = "E5E7EB"
TEAL    = "0F766E"
TEAL_LT = "CCFBF1"
GREEN   = "16A34A"
ORANGE  = "EA580C"
RED     = "DC2626"
BLUE    = "2563EB"
MIDGRAY = "6B7280"

def hex_fill(hex_color):
    return PatternFill("solid", fgColor=hex_color)

def border():
    s = Side(style="thin", color="CCCCCC")
    return Border(left=s, right=s, top=s, bottom=s)

# V2 Improvement task status mapping
V2_TASK_STATUS = {
    # ── Sprint 9: Explainability & RAG 2.0 (Weeks 17-18) ──
    "V2-001": "Done",   # 8-field enterprise explainability model
    "V2-002": "Done",   # RAG 2.0 hierarchical retrieval pipeline
    "V2-003": "Done",   # Unsupported claim detection module
    "V2-004": "Done",   # Low-confidence escalation workflow
    "V2-005": "Done",   # Confidence calibration engine
    "V2-006": "Done",   # Jurisdictional risk context layer
    "V2-007": "Done",   # Retrieval grounding validation
    "V2-008": "Done",   # Explainability UI panel redesign

    # ── Sprint 10: Contract Relationship Intelligence (Weeks 19-20) ──
    "V2-009": "Done",   # Contract relationship graph schema
    "V2-010": "Done",   # Relationship graph API endpoints
    "V2-011": "Done",   # Interactive relationship graph visualization
    "V2-012": "Done",   # Obligation inheritance tracking
    "V2-013": "Done",   # Cross-contract clause conflict detection
    "V2-014": "Done",   # Exposure propagation across contract families
    "V2-015": "Done",   # Regression detection

    # ── Sprint 11: Continuous Contract Monitoring (Weeks 21-22) ──
    "V2-016": "Done",   # Post-signature monitoring engine (event bus)
    "V2-017": "Done",   # Auto-renewal alert system
    "V2-018": "Done",   # SLA obligation deadline tracker
    "V2-019": "Done",   # Insurance certificate expiration monitoring
    "V2-020": "Done",   # Compliance drift detection
    "V2-021": "Done",   # Counterparty litigation monitoring
    "V2-022": "Done",   # Renewal risk forecasting ML model
    "V2-023": "Done",   # Monitoring dashboard + obligations calendar UI

    # ── Sprint 12: Semantic Search & Cost Gov. (Weeks 23-24) ──
    "V2-024": "Done",  # Cross-contract semantic search engine
    "V2-025": "Done",  # Semantic search UI
    "V2-026": "Done",  # Real-time search index pipeline
    "V2-027": "Done",  # AI cost governance dashboard
    "V2-028": "Done",  # Tenant quota management
    "V2-029": "Done",  # Model routing optimization engine
    "V2-030": "Done",  # Batch inference scheduler

    # ── Sprint 13: Benchmark Phase 2 & Procurement (Weeks 25-26) ──
    "V2-031": "Done",  # Opt-in anonymized benchmark corpus
    "V2-032": "Done",  # Industry-specific benchmark segmentation
    "V2-033": "Done",  # Benchmark confidence scoring
    "V2-034": "Done",  # SAP Ariba / Coupa integration
    "V2-035": "Done",  # Vendor onboarding workflow
    "V2-036": "Done",  # Supplier concentration analysis
    "V2-037": "Done",  # Dark mode + WCAG 2.1 AA
    "V2-038": "Done",  # V2.2 launch readiness QA
}

STATUS_COLORS = {
    "Done": (GREEN, LTGREEN),
    "In Progress": (ORANGE, LTORANGE),
    "To Do": (MIDGRAY, GRAY1),
}

def update_v2_excel():
    wb = openpyxl.load_workbook(
        "/Volumes/home/ContractRiskEdge/output/AI_Contract_Risk_Analyzer_Sprint_Plan_V2.xlsx"
    )
    ws = wb["🚀 V2 Improvements"]

    # The V2 sheet has a different layout: Sprint in col B, Task ID in col C,
    # Task Name in col D, Status in col H (index 7), Done? in col J (index 9)
    for row in ws.iter_rows(min_row=4, max_row=ws.max_row, values_only=False):
        # Skip merged sprint header rows (they have NaN in col C)
        tid_cell = row[2]  # Column C = Task ID (V2-XXX)
        status_cell = row[7]  # Column H = Status
        done_cell = row[9]  # Column J = Done checkbox

        tid = tid_cell.value
        if tid and isinstance(tid, str) and tid.startswith("V2-") and tid in V2_TASK_STATUS:
            new_status = V2_TASK_STATUS[tid]
            fg_color, bg_color = STATUS_COLORS[new_status]

            # Update status cell
            status_cell.value = new_status
            status_cell.font = Font(bold=True, size=9, color=fg_color, name="Arial")
            status_cell.fill = hex_fill(bg_color)
            status_cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            status_cell.border = border()

            # Update checkbox
            if new_status == "Done":
                done_cell.value = "✅"
                done_cell.font = Font(size=12, color=GREEN, name="Arial")
            elif new_status == "In Progress":
                done_cell.value = "◐"
                done_cell.font = Font(size=12, color=ORANGE, name="Arial")
            else:
                done_cell.value = "☐"
                done_cell.font = Font(size=12, color=NAVY, name="Arial")
            done_cell.fill = hex_fill(WHITE)
            done_cell.alignment = Alignment(horizontal="center", vertical="center")
            done_cell.border = border()

    # Count by status
    status_counts = {"Done": 0, "In Progress": 0, "To Do": 0}
    for s in V2_TASK_STATUS.values():
        status_counts[s] += 1

    print(f"V2 Sprint Plan Status Summary:")
    print(f"  Done: {status_counts['Done']} / {len(V2_TASK_STATUS)}")
    print(f"  In Progress: {status_counts['In Progress']} / {len(V2_TASK_STATUS)}")
    print(f"  To Do: {status_counts['To Do']} / {len(V2_TASK_STATUS)}")
    print(f"  Progress: {status_counts['Done']/len(V2_TASK_STATUS)*100:.1f}%")

    wb.save(
        "/Volumes/home/ContractRiskEdge/output/AI_Contract_Risk_Analyzer_Sprint_Plan_V2.xlsx"
    )
    print("\n✅ V2 Sprint Plan updated and saved!")

if __name__ == "__main__":
    update_v2_excel()
