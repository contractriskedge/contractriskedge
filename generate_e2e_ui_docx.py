#!/usr/bin/env python3
"""Generate E2E UI Testing Guide as Word .docx"""

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

doc = Document()

# ── Style Setup ────────────────────────────────────────────────────
style = doc.styles['Normal']
font = style.font
font.name = 'Calibri'
font.size = Pt(11)
style.paragraph_format.space_after = Pt(6)

# Heading styles
for level in range(1, 4):
    hs = doc.styles[f'Heading {level}']
    hs.font.color.rgb = RGBColor(15, 23, 42)  # navy-900

# ── Helper Functions ───────────────────────────────────────────────

def add_step_box(step_num: str, title: str, instructions: list[str], expected: str):
    """Add a step with number, title, bullet instructions, and expected result."""
    p = doc.add_paragraph()
    run = p.add_run(f"Step {step_num}: {title}")
    run.bold = True
    run.font.size = Pt(12)
    run.font.color.rgb = RGBColor(180, 83, 9)  # gold-700

    for instr in instructions:
        doc.add_paragraph(instr, style='List Bullet')

    exp = doc.add_paragraph()
    exp_run = exp.add_run("✅ Expected: ")
    exp_run.bold = True
    exp_run.font.color.rgb = RGBColor(22, 163, 74)  # green-600
    exp_run2 = exp.add_run(expected)
    exp_run2.font.color.rgb = RGBColor(22, 163, 74)
    doc.add_paragraph()  # spacer


def add_info_table(headers: list[str], rows: list[list[str]]):
    """Add a styled table."""
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = 'Light Grid Accent 1'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    # Header row
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = h
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.bold = True
                run.font.size = Pt(10)

    # Data rows
    for r_idx, row in enumerate(rows):
        for c_idx, val in enumerate(row):
            cell = table.rows[r_idx + 1].cells[c_idx]
            cell.text = val
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(10)

    doc.add_paragraph()


# ══════════════════════════════════════════════════════════════════════
# TITLE PAGE
# ══════════════════════════════════════════════════════════════════════

doc.add_paragraph()
doc.add_paragraph()

title = doc.add_heading('ContractRiskEdge', level=0)
title.alignment = WD_ALIGN_PARAGRAPH.CENTER

subtitle = doc.add_paragraph()
subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = subtitle.add_run('End-to-End UI Testing Guide')
run.font.size = Pt(18)
run.font.color.rgb = RGBColor(180, 83, 9)

sub2 = doc.add_paragraph()
sub2.alignment = WD_ALIGN_PARAGRAPH.CENTER
run2 = sub2.add_run('Workflow Lifecycle & Operations Observability')
run2.font.size = Pt(14)
run2.font.color.rgb = RGBColor(100, 116, 139)

doc.add_paragraph()
doc.add_paragraph()

meta = doc.add_paragraph()
meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
meta.add_run('Version 1.0\n').bold = True
meta.add_run('June 28, 2026\n')
meta.add_run('Sprint 34 — Production Readiness')

doc.add_page_break()

# ══════════════════════════════════════════════════════════════════════
# TABLE OF CONTENTS
# ══════════════════════════════════════════════════════════════════════

doc.add_heading('Table of Contents', level=1)
toc_items = [
    ("1", "Prerequisites — Starting the Stack"),
    ("2", "Login & Navigate to Workflow Admin"),
    ("3", "Create a Workflow Pack"),
    ("4", "Open the Pack & View Details"),
    ("5", "Design Stages (Workflow Designer)"),
    ("6", "Build Rules (Rule Builder)"),
    ("7", "Validate the Pack"),
    ("8", "Simulate the Workflow"),
    ("9", "Publish the Workflow"),
    ("10", "Create a Contract (Triggers Workflow)"),
    ("11", "View Workflow Instance (Workflow Center)"),
    ("12", "Approve / Reject Stages"),
    ("13", "Monitor via Operations Center"),
    ("14", "Generate a Support Bundle"),
    ("15", "Check Instance Monitor (Workflow Operations)"),
    ("", "Complete Validation Checklist"),
]
for num, item in toc_items:
    p = doc.add_paragraph(f"Step {num} — {item}" if num else item, style='List Number')

doc.add_page_break()

# ══════════════════════════════════════════════════════════════════════
# 1. PREREQUISITES
# ══════════════════════════════════════════════════════════════════════

doc.add_heading('Step 1: Prerequisites — Starting the Stack', level=1)
doc.add_paragraph('Before running the E2E tests, ensure all services are started:')

add_info_table(
    ["Service", "Command", "Port"],
    [
        ["Backend (FastAPI)", "cd backend && source .venv/bin/activate && uvicorn app.main:app --reload", "8000"],
        ["Redis Cache", "redis-server", "6379"],
        ["Frontend (Next.js)", "cd frontend && npm run dev", "3000"],
        ["Celery Workers (optional)", "cd backend && celery -A app.workers.celery_app worker --loglevel=info --beat", "—"],
    ]
)

doc.add_paragraph('Open http://localhost:3000 in your browser.', style='Intense Quote')

doc.add_page_break()

# ══════════════════════════════════════════════════════════════════════
# 2. LOGIN & NAVIGATE
# ══════════════════════════════════════════════════════════════════════

doc.add_heading('Step 2: Login & Navigate to Workflow Admin', level=1)

add_step_box(
    "2.1", "Login",
    [
        "Open http://localhost:3000 in your browser.",
        "You will land on the main dashboard. The sidebar navigation is on the left.",
    ],
    "Dashboard loads with sidebar visible."
)

add_step_box(
    "2.2", "Navigate to Workflow Admin",
    [
        "In the sidebar, scroll down to the Operations section.",
        "Click Workflows to expand the submenu.",
        "Two entries appear: Workflow Center (end-user view) and Workflow Admin (admin view).",
        "Click Workflow Admin.",
    ],
    "Workflow Administration page opens with the pack library grid."
)

doc.add_page_break()

# ══════════════════════════════════════════════════════════════════════
# 3. CREATE WORKFLOW PACK
# ══════════════════════════════════════════════════════════════════════

doc.add_heading('Step 3: Create a Workflow Pack', level=1)

add_step_box(
    "3.1", "Open Create Dialog",
    [
        "On the Workflow Admin page, locate the gold \"+ New Workflow Pack\" button at the top-right.",
        "Click it to open the CreateWorkflowDialog.",
    ],
    "A modal dialog appears with fields for Name, Category, and Description."
)

add_step_box(
    "3.2", "Fill in Pack Details",
    [
        "Name: Enter \"NDA Approval v1\".",
        "Category: Select \"Legal\" from the dropdown.",
        "Description: Enter \"Standard NDA review and approval workflow\".",
    ],
    "All fields are populated."
)

add_step_box(
    "3.3", "Create the Pack",
    [
        "Click the \"Create\" button in the dialog.",
    ],
    "Dialog closes. The new pack appears as a card in the grid with status \"Draft\"."
)

doc.add_page_break()

# ══════════════════════════════════════════════════════════════════════
# 4. OPEN PACK DETAILS
# ══════════════════════════════════════════════════════════════════════

doc.add_heading('Step 4: Open the Pack & View Details', level=1)

add_step_box(
    "4.1", "Open Detail Drawer",
    [
        "Click the pack card you just created (\"NDA Approval v1\").",
    ],
    "A detail drawer slides in from the right side of the screen."
)

add_step_box(
    "4.2", "Explore the Drawer",
    [
        "Quick Actions bar at the top: Designer, Simulator, Validate, Publish, Clone, Export.",
        "Tabs below: Overview, Versions, Analytics, Timeline.",
        "Overview tab shows: health score, status, version, owner, category, stages, dependencies.",
    ],
    "All pack metadata is displayed correctly."
)

add_step_box(
    "4.3", "Close the Drawer",
    [
        "Click the X button in the top-right corner, or click the backdrop area outside the drawer.",
    ],
    "Drawer closes. You return to the pack library grid."
)

doc.add_page_break()

# ══════════════════════════════════════════════════════════════════════
# 5. DESIGN STAGES
# ══════════════════════════════════════════════════════════════════════

doc.add_heading('Step 5: Design Stages (Workflow Designer)', level=1)

add_step_box(
    "5.1", "Open the Designer",
    [
        "Click the pack card to open the detail drawer.",
        "In the Quick Actions bar, click \"Designer\".",
    ],
    "Workflow Designer opens. Left panel shows an empty stage list. Right panel shows configuration options."
)

add_step_box(
    "5.2", "Add Stages",
    [
        "Click the \"+ Stage\" button to add a new stage.",
        "Configure Stage 1 — Name: \"Legal Review\", Assignee Role: \"legal_reviewer\", SLA Hours: 24.",
        "Click \"+ Stage\" again for Stage 2 — Name: \"Management Approval\", Assignee Role: \"reviewer\", SLA Hours: 48.",
        "Click \"+ Stage\" again for Stage 3 — Name: \"Final Sign-off\", Assignee Role: \"admin\", SLA Hours: 24.",
        "Drag stages to reorder if needed.",
    ],
    "Three stages appear in the list with configured properties."
)

add_step_box(
    "5.3", "Save Stages",
    [
        "Click the \"Save\" button at the top-right of the Designer.",
    ],
    "Designer closes. You return to the pack library."
)

doc.add_page_break()

# ══════════════════════════════════════════════════════════════════════
# 6. BUILD RULES
# ══════════════════════════════════════════════════════════════════════

doc.add_heading('Step 6: Build Rules (Rule Builder)', level=1)

add_step_box(
    "6.1", "Open the Rule Builder",
    [
        "Open the pack detail drawer again.",
        "Click \"Designer\" to open the Workflow Designer.",
        "In the Designer, click the \"Rules\" tab or \"Edit Rules\" button.",
    ],
    "Rule Builder opens with a visual ALL/ANY group builder."
)

add_step_box(
    "6.2", "Create a Rule",
    [
        "Click \"+ Add Condition\" to create a new rule group.",
        "Select ALL (all conditions must match).",
        "Add a condition: Field = \"Contract Value\", Operator = \"==\", Value = \"0\".",
        "Add an Action: Type = \"Skip Stage\", Target = \"Management Approval\".",
    ],
    "The rule appears in the builder. A preview shows the generated JSON Logic."
)

add_step_box(
    "6.3", "Test the Rule",
    [
        "Click the \"Test Rule\" button.",
        "A test panel opens. Enter test data: {\"contract_value\": 0}.",
        "Click \"Run Test\".",
    ],
    "The evaluator shows the rule matched and the action (skip stage) would be triggered."
)

add_step_box(
    "6.4", "Save Rules",
    [
        "Click \"Save Rules\".",
    ],
    "Rules are saved to the workflow pack. Rule Builder closes."
)

doc.add_page_break()

# ══════════════════════════════════════════════════════════════════════
# 7. VALIDATE
# ══════════════════════════════════════════════════════════════════════

doc.add_heading('Step 7: Validate the Pack', level=1)

add_step_box(
    "7.1", "Run Validation",
    [
        "Open the pack detail drawer.",
        "Click \"Validate\" in the Quick Actions bar.",
    ],
    "The Publishing Flow opens showing a validation score (0–100) and a list of checks."
)

add_step_box(
    "7.2", "Review Validation Results",
    [
        "Each check has a status: ✅ Pass or ❌ Fail.",
        "Checks include: stage definitions complete, no circular dependencies, rules reference valid stages, SLA hours are positive, etc.",
        "If any check fails, the score is < 100 and the Publish button is disabled.",
    ],
    "Target: score = 100 with all checks passing (✅)."
)

add_step_box(
    "7.3", "Fix Issues (if needed)",
    [
        "If score < 100, note which checks failed.",
        "Go back to Designer or Rule Builder to fix the issues.",
        "Re-run Validate until score = 100.",
    ],
    "All validation checks pass."
)

doc.add_page_break()

# ══════════════════════════════════════════════════════════════════════
# 8. SIMULATE
# ══════════════════════════════════════════════════════════════════════

doc.add_heading('Step 8: Simulate the Workflow', level=1)

add_step_box(
    "8.1", "Open the Simulator",
    [
        "Open the pack detail drawer.",
        "Click \"Simulator\" in the Quick Actions bar.",
    ],
    "Workflow Simulator opens with input fields: Contract Type, Contract Value, Department."
)

add_step_box(
    "8.2", "Run a Simulation (Value = 0)",
    [
        "Contract Type: Select \"nda\".",
        "Contract Value: Enter \"0\" (tests your skip-stage rule).",
        "Department: Enter \"engineering\".",
        "Click \"Run Simulation\".",
    ],
    "The simulator shows: execution path skips \"Management Approval\", explanation tree shows why, timeline shows expected duration per visited stage."
)

add_step_box(
    "8.3", "Run a Simulation (Value = 50000)",
    [
        "Contract Value: Change to \"50000\".",
        "Click \"Run Simulation\" again.",
    ],
    "The simulator shows all 3 stages are visited (no skip). The execution path differs from the previous run."
)

doc.add_page_break()

# ══════════════════════════════════════════════════════════════════════
# 9. PUBLISH
# ══════════════════════════════════════════════════════════════════════

doc.add_heading('Step 9: Publish the Workflow', level=1)

add_step_box(
    "9.1", "Open Publishing Flow",
    [
        "Open the pack detail drawer.",
        "Click \"Publish\" in the Quick Actions bar.",
    ],
    "Publishing Flow opens showing: Validation Score, Impact Analysis, Change Summary, Effective Date picker."
)

add_step_box(
    "9.2", "Review Impact Analysis",
    [
        "The Impact Analysis shows which templates and contracts would be affected by this workflow.",
        "The Change Summary shows what changed since the last version.",
    ],
    "Impact analysis is populated (or shows \"No dependencies\" for a new pack)."
)

add_step_box(
    "9.3", "Set Effective Date & Publish",
    [
        "Set the Effective Date to today's date.",
        "Click the \"Publish\" button.",
    ],
    "Pack status changes to \"Published\". You return to the pack library. The pack card now shows a \"Published\" badge."
)

doc.add_page_break()

# ══════════════════════════════════════════════════════════════════════
# 10. CREATE CONTRACT
# ══════════════════════════════════════════════════════════════════════

doc.add_heading('Step 10: Create a Contract (Triggers Workflow)', level=1)

add_step_box(
    "10.1", "Navigate to Contracts",
    [
        "In the sidebar, click \"Contracts\".",
    ],
    "Contracts page opens showing the contract repository."
)

add_step_box(
    "10.2", "Create a New Contract",
    [
        "Click the \"+ New Contract\" button (top-right).",
        "Title: Enter \"Vendor NDA - Acme Corp\".",
        "Contract Type: Select \"nda\".",
        "Value: Enter \"0\" (to test the auto-skip rule).",
        "Click \"Create\".",
    ],
    "Contract is created. A workflow instance is automatically triggered and linked to this contract."
)

doc.add_page_break()

# ══════════════════════════════════════════════════════════════════════
# 11. VIEW WORKFLOW INSTANCE
# ══════════════════════════════════════════════════════════════════════

doc.add_heading('Step 11: View Workflow Instance (Workflow Center)', level=1)

add_step_box(
    "11.1", "Open Workflow Center",
    [
        "In the sidebar, click Workflows → Workflow Center.",
    ],
    "Workflow Center opens showing: KPI Cards (total active, at risk, breached), Kanban Board (instances by stage), SLA Center (breach charts, team workload), Approval Table (pending approvals)."
)

add_step_box(
    "11.2", "Find Your Workflow Instance",
    [
        "Look in the Kanban Board for your contract's workflow instance.",
        "It should appear in the first stage column (\"Legal Review\").",
    ],
    "The workflow instance is visible in the Kanban board with the contract name, current stage, and SLA timer."
)

add_step_box(
    "11.3", "Open Instance Details",
    [
        "Click the workflow card in the Kanban board.",
    ],
    "Workflow Detail Drawer opens showing: current stage, progress bar, SLA countdown timer, activity log, approval history."
)

doc.add_page_break()

# ══════════════════════════════════════════════════════════════════════
# 12. APPROVE / REJECT
# ══════════════════════════════════════════════════════════════════════

doc.add_heading('Step 12: Approve / Reject Stages', level=1)

add_step_box(
    "12.1", "Approve Stage 1",
    [
        "In the Workflow Center, find your workflow instance in the \"Legal Review\" column.",
        "Click it to open the detail drawer.",
        "Click the \"Approve\" button.",
        "Add a comment: \"Reviewed and approved.\"",
        "Confirm.",
    ],
    "The workflow advances to the next stage. If your rule matched (value=0), it skips \"Management Approval\" and goes directly to \"Final Sign-off\"."
)

add_step_box(
    "12.2", "Verify Stage Advancement",
    [
        "Refresh the Workflow Center page.",
        "Check the Kanban Board — the instance should have moved to the next column.",
    ],
    "Workflow instance is now in the next stage column with updated SLA timer."
)

add_step_box(
    "12.3", "Complete the Workflow",
    [
        "Repeat the approval process for remaining stages.",
        "After the final stage is approved, the workflow status changes to \"Completed\".",
    ],
    "Workflow instance shows \"Completed\" status. The contract is marked as approved."
)

doc.add_page_break()

# ══════════════════════════════════════════════════════════════════════
# 13. OPERATIONS CENTER
# ══════════════════════════════════════════════════════════════════════

doc.add_heading('Step 13: Monitor via Operations Center', level=1)

doc.add_paragraph('The Operations Center provides system-wide observability. Access it from the sidebar: Operations → Operations Center.')

doc.add_heading('13.1 Health Tab', level=2)
doc.add_paragraph('The default tab shows the System Health Dashboard:')
add_info_table(
    ["Element", "Description"],
    [
        ["Overall Status Banner", "Healthy / Warning / Critical with color coding, uptime, version, environment"],
        ["Service Cards (10)", "API, Database, Redis, Workers, AI Service, Vector Search, DocuSign, Email, Storage, Scheduler"],
        ["Per-Service Info", "Status icon, response time, detail message, last checked timestamp"],
        ["Healthy Count", "X of Y services healthy"],
    ]
)

doc.add_heading('13.2 Metrics Tab', level=2)
doc.add_paragraph('Shows Prometheus metrics reference:')
add_info_table(
    ["Metric", "Description"],
    [
        ["http_requests_total", "Total HTTP requests by method, endpoint, status"],
        ["http_request_duration_seconds", "Request latency histogram"],
        ["workflow_instances_started_total", "Workflows started"],
        ["workflow_instances_completed_total", "Workflows completed"],
        ["ai_analysis_total", "AI analysis runs"],
        ["ai_token_usage_total", "Token consumption"],
        ["search_queries_total", "Search queries by strategy"],
        ["queue_depth", "Queue depth by name"],
        ["db_pool_stats", "Connection pool statistics"],
    ]
)

doc.add_heading('13.3 Logs Tab', level=2)
doc.add_paragraph('Structured log viewer with:')
add_info_table(
    ["Feature", "Description"],
    [
        ["Filter bar", "Search logs by any field (timestamp, severity, module, correlation ID, etc.)"],
        ["Log table", "Columns: Timestamp, Severity, Module, Action, Outcome, Duration, Correlation ID, Message"],
        ["Raw JSON toggle", "Switch between formatted table and raw JSON view"],
        ["Severity badges", "Color-coded: ERROR (red), WARNING (amber), INFO (green)"],
    ]
)

doc.add_heading('13.4 Queues Tab', level=2)
doc.add_paragraph('Background job queue monitoring:')
add_info_table(
    ["Metric", "Description"],
    [
        ["Queue Depths", "Per-queue counts: celery, default, ai, email, workflow, ingestion"],
        ["Total Pending", "Sum of all pending jobs"],
        ["Dead Letter Count", "Failed messages in DLQ"],
        ["Backlog Indicator", "Yes/No — triggers when any queue exceeds 100 items"],
        ["Active Tasks", "Currently executing tasks with worker name and start time"],
    ]
)

doc.add_heading('13.5 Errors Tab', level=2)
doc.add_paragraph('Error categorization and trends:')
add_info_table(
    ["Section", "Description"],
    [
        ["Trend Cards", "Today / Week / Month — error counts with color coding"],
        ["Categories Bar", "Validation, Authorization, Database, Integration, AI, Workflow, Search, Unknown"],
        ["Distribution", "Horizontal bar chart showing relative error proportions"],
    ]
)

doc.add_heading('13.6 Integrations Tab', level=2)
doc.add_paragraph('External service health:')
add_info_table(
    ["Integration", "Status Shown"],
    [
        ["DocuSign", "API reachable, response time, last checked"],
        ["Email", "SMTP or Resend configured"],
        ["Storage", "S3/MinIO bucket connectivity"],
        ["AI Service", "API key configured and valid"],
    ]
)

doc.add_heading('13.7 Scheduler Tab', level=2)
doc.add_paragraph('Scheduled task monitoring:')
add_info_table(
    ["Metric", "Description"],
    [
        ["Scheduled Count", "Number of scheduled tasks"],
        ["Active Count", "Currently executing tasks"],
        ["Status", "Healthy / Failed"],
        ["Task List", "Task name, worker, ETA for each scheduled task"],
    ]
)

doc.add_heading('13.8 Alerts Tab', level=2)
doc.add_paragraph('Active alert evaluation. Alerts trigger for:')
add_info_table(
    ["Alert", "Severity", "Condition"],
    [
        ["Database Unavailable", "Critical", "Application cannot connect to database"],
        ["Background Workers Stopped", "Critical", "No Celery workers responding"],
        ["Queue Backlog", "Warning", "Any queue exceeds 100 pending items"],
        ["High Error Rate", "Warning", ">50 errors in the last 24 hours"],
        ["Integration Failure", "Warning", "Any external integration in failed state"],
        ["SLA Violations", "Warning", "Reviews exceeding 48-hour SLA"],
    ]
)

doc.add_heading('13.9 Slow Operations Panel', level=2)
doc.add_paragraph('Always visible below the tabs. Shows Top 20 slowest:')
add_info_table(
    ["Category", "Columns"],
    [
        ["Slow APIs", "Method, Path, Duration (ms), Timestamp"],
        ["Slow Queries", "(Database query details)"],
        ["Slow Workflows", "Correlation ID, Status, Duration (seconds)"],
        ["Slow Searches", "(Search query details)"],
    ]
)

doc.add_page_break()

# ══════════════════════════════════════════════════════════════════════
# 14. SUPPORT BUNDLE
# ══════════════════════════════════════════════════════════════════════

doc.add_heading('Step 14: Generate a Support Bundle', level=1)

add_step_box(
    "14.1", "Download Support Bundle",
    [
        "In the Operations Center, locate the \"Generate Support Bundle\" button (top-right, dark button).",
        "Click it. A loading spinner appears while the bundle is generated.",
    ],
    "A ZIP file downloads automatically."
)

doc.add_paragraph('The support bundle ZIP contains 8 diagnostic files:')
add_info_table(
    ["File", "Contents"],
    [
        ["system_info.json", "Version, environment, Python version, platform, hostname, uptime"],
        ["config.json", "All application settings (secrets masked with ****)"],
        ["health_status.json", "Full health snapshot for all 10 services"],
        ["queue_status.json", "Queue depths and dead letter count"],
        ["db_migration_version.txt", "Current Alembic migration version"],
        ["enabled_integrations.json", "Which integrations are configured (DocuSign, Email, Storage, AI, Redis, rate limiting)"],
        ["workflow_packs.json", "All installed workflow packs with versions and statuses"],
        ["metrics.txt", "Full Prometheus metrics dump"],
    ]
)

doc.add_page_break()

# ══════════════════════════════════════════════════════════════════════
# 15. WORKFLOW OPERATIONS
# ══════════════════════════════════════════════════════════════════════

doc.add_heading('Step 15: Check Instance Monitor (Workflow Operations)', level=1)

add_step_box(
    "15.1", "Open Workflow Operations",
    [
        "Navigate to Workflows → Workflow Admin.",
        "Click the \"Operations\" button at the top-left of the page (next to \"+ New Workflow Pack\").",
    ],
    "Workflow Operations Center opens with 6 sub-tabs."
)

doc.add_paragraph('The Workflow Operations Center provides workflow-specific monitoring:')
add_info_table(
    ["Tab", "Description"],
    [
        ["Instance Monitor", "Live grid of all workflow instances with auto-refresh (15s polling), status filters, search, pagination"],
        ["Task Queue", "Pending tasks and assignments"],
        ["Bottlenecks", "Stage-level performance analysis showing where workflows get stuck"],
        ["Workflow Health", "Per-pack health scores with progress bars and summary cards"],
        ["Audit Explorer", "Searchable, filterable workflow event log with export capability"],
        ["Usage Dashboard", "Aggregated usage metrics and trends across all packs"],
    ]
)

doc.add_page_break()

# ══════════════════════════════════════════════════════════════════════
# VALIDATION CHECKLIST
# ══════════════════════════════════════════════════════════════════════

doc.add_heading('Complete Validation Checklist', level=1)

doc.add_paragraph('Use this checklist to verify the entire workflow lifecycle end-to-end:')

add_info_table(
    ["#", "Step", "What to Verify", "Status"],
    [
        ["1", "Create pack", "Card appears in grid with status \"Draft\"", "☐"],
        ["2", "Open drawer", "Details load (health, stages, dependencies)", "☐"],
        ["3", "Designer", "Can add/reorder/configure stages", "☐"],
        ["4", "Rule Builder", "Can create ALL/ANY conditions with actions", "☐"],
        ["5", "Test Rule", "Evaluator returns correct match/no-match", "☐"],
        ["6", "Validate", "Score = 100, no errors", "☐"],
        ["7", "Simulate (value=0)", "Path skips stage per rule", "☐"],
        ["8", "Simulate (value=50000)", "Path visits all stages", "☐"],
        ["9", "Publish", "Status changes to \"Published\"", "☐"],
        ["10", "Create contract", "Workflow instance auto-created", "☐"],
        ["11", "Workflow Center", "Instance visible in Kanban board", "☐"],
        ["12", "Approve stage", "Instance advances to next stage", "☐"],
        ["13", "Complete workflow", "Status changes to \"Completed\"", "☐"],
        ["14", "Operations Health", "Shows 6+/10 services healthy", "☐"],
        ["15", "Operations Queues", "Shows queue depths", "☐"],
        ["16", "Operations Errors", "Trends and categories display", "☐"],
        ["17", "Operations Alerts", "Shows active alerts (worker-stopped if Celery not running)", "☐"],
        ["18", "Support Bundle", "ZIP downloads with 8 files", "☐"],
        ["19", "Workflow Ops Monitor", "Instance visible in live grid", "☐"],
        ["20", "Workflow Health", "Per-pack health scores display", "☐"],
    ]
)

doc.add_paragraph()

# Footer
doc.add_paragraph()
footer = doc.add_paragraph()
footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = footer.add_run('— End of Document —')
run.font.color.rgb = RGBColor(156, 163, 175)
run.font.size = Pt(10)

# ── Save ───────────────────────────────────────────────────────────
output_path = 'e2e_ui_testing_guide.docx'
doc.save(output_path)
print(f"✅ Generated: {output_path}")
