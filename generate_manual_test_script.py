"""Generate comprehensive Manual Test Script Excel for all implemented features.

Covers all sprints (1-13) including V2 improvements with detailed test cases,
expected results, and status tracking columns.
"""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from datetime import datetime

# ── Color Palette ────────────────────────────────────────────────────────────
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
PURPLE  = "7C3AED"
LTGRAY  = "F9FAFB"

def hex_fill(c):
    return PatternFill("solid", fgColor=c)

def thin_border():
    s = Side(style="thin", color="CCCCCC")
    return Border(left=s, right=s, top=s, bottom=s)

def header_font(bold=True, color=WHITE, size=10):
    return Font(bold=bold, color=color, size=size, name="Calibri")

def body_font(size=9, color=NAVY):
    return Font(size=size, color=color, name="Calibri")

def wrap_align(h="left", v="top"):
    return Alignment(horizontal=h, vertical=v, wrap_text=True)

def center_align():
    return Alignment(horizontal="center", vertical="center", wrap_text=True)


# ── Test Case Definitions ────────────────────────────────────────────────────
# Structure: (test_id, feature_area, sprint, test_name, test_description,
#             test_steps, expected_result, test_data, priority, automation_possible)

TEST_CASES = [
    # ══════════════════════════════════════════════════════════════════════════
    # SPRINT 1: Foundation & Ingestion
    # ══════════════════════════════════════════════════════════════════════════
    ("TC-001", "Ingestion", "Sprint 1", "PDF Text Extraction",
     "Upload a PDF contract and verify text is extracted correctly",
     "1. Navigate to Upload page\n2. Select a PDF contract file (scanned + text)\n3. Click Upload\n4. Wait for processing to complete\n5. View extracted text",
     "Extracted text matches original document content with >95% accuracy. Page numbers preserved. Metadata extracted.",
     "Sample PDF contract (text-based, 10+ pages)", "P0", True),

    ("TC-002", "Ingestion", "Sprint 1", "DOCX Ingestion & Clause Segmentation",
     "Upload a DOCX contract and verify clause segmentation",
     "1. Upload a DOCX contract\n2. Wait for processing\n3. View extracted clauses\n4. Verify clause boundaries",
     "Clauses segmented correctly (F1 > 0.90). Headings preserved. Numbered lists intact. Cross-references detected.",
     "Sample DOCX contract with numbered clauses", "P0", True),

    ("TC-003", "Ingestion", "Sprint 1", "OCR Fallback (Scanned PDF)",
     "Upload a scanned PDF and verify OCR text extraction",
     "1. Upload a scanned PDF (image-based, no text layer)\n2. Verify OCR is triggered automatically\n3. View extracted text\n4. Check confidence scores per page",
     "OCR accuracy > 90%. Auto-trigger works when PyMuPDF returns <100 words/page. Cost tracked.",
     "Scanned PDF contract (image-based)", "P0", True),

    ("TC-004", "Ingestion", "Sprint 1", "Async Ingestion Queue",
     "Submit multiple contracts and verify async processing",
     "1. Upload 5+ contracts simultaneously\n2. Check job status endpoint for each\n3. Verify PENDING→PROCESSING→DONE transition\n4. Check processing order",
     "All contracts process successfully. Status transitions correct. Queue handles concurrent jobs. P95 latency < 2s.",
     "5+ contract files (mix of PDF and DOCX)", "P0", True),

    ("TC-005", "Ingestion", "Sprint 1", "Semantic Clause Chunking",
     "Verify clauses are chunked with semantic boundaries preserved",
     "1. Upload a contract with long clauses\n2. View chunked output\n3. Verify no clause is split mid-sentence\n4. Check token overlap",
     "512-token max chunks. Clause-aware boundaries. 10% token overlap. Metadata preserved per chunk.",
     "Long contract (50+ pages, complex clauses)", "P1", True),

    # ══════════════════════════════════════════════════════════════════════════
    # SPRINT 2: AI Risk Engine
    # ══════════════════════════════════════════════════════════════════════════
    ("TC-006", "Risk Engine", "Sprint 2", "12-Category Risk Taxonomy",
     "Verify all 12 risk categories are available and documented",
     "1. Open API docs (/docs)\n2. Check risk taxonomy endpoint\n3. Verify all 12 categories present\n4. Review sub-types and severity ranges",
     "All 12 categories present with IDs, names, descriptions, sub-types, and default severity ranges.",
     "API docs / taxonomy endpoint", "P0", True),

    ("TC-007", "Risk Engine", "Sprint 2", "Risk Clause Flagging",
     "Upload a contract and verify risk clauses are flagged correctly",
     "1. Upload a contract with known risk clauses\n2. Wait for AI analysis\n3. View flagged clauses\n4. Verify risk categories and severities",
     "F1 > 0.90 on clause type classification. Severity correlation > 0.85 vs attorney. JSON output parseable.",
     "Contract with indemnity, liability, confidentiality clauses", "P0", True),

    ("TC-008", "Risk Engine", "Sprint 2", "Severity Scoring (1-10)",
     "Verify severity scores are computed with confidence intervals",
     "1. Analyze a contract with varying risk levels\n2. Check severity scores for each flagged clause\n3. Verify confidence levels (low/medium/high)\n4. Check percentile vs corpus",
     "Score-attorney correlation > 0.82. Confidence intervals reflect uncertainty. Low-confidence items flagged for review.",
     "Contract with mixed risk clauses", "P0", True),

    ("TC-009", "Risk Engine", "Sprint 2", "RAG Pipeline Retrieval",
     "Verify RAG retrieval returns relevant benchmark clauses",
     "1. Run risk analysis on a contract\n2. Check linked evidence for each flagged clause\n3. Verify top-5 similar clauses from benchmark corpus\n4. Check relevance scores",
     "Retrieval latency < 100ms P95. Top-5 relevant clauses. NDCG > 0.85. Re-ranking improves precision > 10%.",
     "Contract requiring benchmark comparison", "P0", True),

    ("TC-010", "Risk Engine", "Sprint 2", "LLM Fallback (Claude→GPT-4o)",
     "Verify LLM fallback works when primary provider fails",
     "1. Configure Claude API key as invalid\n2. Run risk analysis\n3. Verify GPT-4o fallback is triggered\n4. Check results are still returned",
     "Fallback triggers on simulated Claude error. Results returned from GPT-4o. Error logged. Cost tracked.",
     "Invalid Claude API key configuration", "P1", True),

    ("TC-011", "Risk Engine", "Sprint 2", "Risk Flagging Output Schema",
     "Verify risk flagging output follows the 8-field enterprise schema",
     "1. Run risk analysis\n2. Check output JSON structure\n3. Verify all required fields present\n4. Validate schema compliance",
     "All 8 fields present: clause_text, risk_category, why_flagged, business_impact, benchmark_comparison, confidence_score, suggested_remediation, linked_evidence.",
     "Any contract for analysis", "P0", True),

    # ══════════════════════════════════════════════════════════════════════════
    # SPRINT 3: Redline & Benchmarking
    # ══════════════════════════════════════════════════════════════════════════
    ("TC-012", "Redline", "Sprint 3", "AI Redline Suggestions (8 Templates)",
     "Verify redline suggestions are generated for all 8 clause types",
     "1. Open a contract with various clause types\n2. Select a clause\n3. Request redline suggestion\n4. Verify suggestion includes: original, proposed, rationale",
     "8 clause type templates work: liability, indemnification, IP, payment, governing law, termination, confidentiality, force majeure. >40% rated 'use as-is'.",
     "Contract with 8+ clause types", "P0", True),

    ("TC-013", "Redline", "Sprint 3", "Redline Output Formatter",
     "Verify redline output shows diff with accept/reject controls",
     "1. Generate redline suggestion\n2. View diff view (original vs proposed)\n3. Accept a suggestion\n4. Reject a suggestion\n5. Modify a suggestion",
     "Diff highlighting accurate at word level. Accept/reject tracked in DB. Confidence displayed. Rationale in plain English.",
     "Redline suggestion on any clause", "P0", True),

    ("TC-014", "Export", "Sprint 3", "DOCX Tracked-Changes Export",
     "Export redlined contract as DOCX with tracked changes",
     "1. Accept some redline suggestions\n2. Click Export → DOCX\n3. Open exported file in Word\n4. Verify tracked changes display correctly",
     "Exported DOCX opens in Word 2019/2021/365. Tracked changes show correctly. Accept-all produces clean doc. Export < 10s.",
     "Contract with accepted/rejected redlines", "P0", True),

    ("TC-015", "Export", "Sprint 3", "PDF Markup Export",
     "Export contract as PDF with highlighted risk clauses",
     "1. View analyzed contract\n2. Click Export → PDF\n3. Open exported PDF\n4. Verify risk clauses highlighted in yellow\n5. Check margin annotations",
     "Annotations visible in Adobe Reader + Preview. Original layout preserved. Highlights match risk clauses. Export < 15s.",
     "Analyzed contract with risk flags", "P0", True),

    ("TC-016", "Benchmarking", "Sprint 3", "Benchmark Scoring Engine",
     "Verify benchmark percentile scores are computed correctly",
     "1. Run risk analysis\n2. View benchmark comparison for each clause\n3. Verify P25/P50/P75 percentiles\n4. Check favorable/at-market/unfavorable classification",
     "Percentile scores match manual validation. Segmentation by deal size × industry × counterparty type. Classification matches attorney > 85%.",
     "Contract with benchmark comparison", "P0", True),

    ("TC-017", "Benchmarking", "Sprint 3", "Benchmark Freshness Indicator",
     "Verify freshness indicators display correctly in UI",
     "1. View benchmark data\n2. Check freshness indicator color\n3. Verify timestamp shown\n4. Check for staleness alerts",
     "Green (< 30 days), amber (30-90 days), red (> 90 days). Alert fires at 90-day threshold. Timestamp updates on refresh.",
     "Benchmark dashboard view", "P1", True),

    # ══════════════════════════════════════════════════════════════════════════
    # SPRINT 4: Dashboard & Reporting
    # ══════════════════════════════════════════════════════════════════════════
    ("TC-018", "Dashboard", "Sprint 4", "Portfolio Risk Dashboard",
     "Verify portfolio dashboard shows all contracts with RAG status",
     "1. Log in as any user\n2. View Portfolio Dashboard\n3. Verify contract heatmap displays\n4. Check RAG (Red/Amber/Green) status\n5. Apply filters\n6. Sort by risk score",
     "Dashboard loads < 2s for 100 contracts. RAG status calculated correctly. Filters work. Click-through navigates to detail.",
     "Multiple contracts in portfolio", "P0", False),

    ("TC-019", "Dashboard", "Sprint 4", "CFO Persona View",
     "Verify CFO view shows financial exposure summary",
     "1. Log in as CFO role\n2. Navigate to CFO View\n3. Verify total $ at risk by category\n4. Check risk trend chart (30-day)\n5. Verify top 5 highest-risk contracts\n6. Export to PDF",
     "Financial figures correct. Trend chart renders. PDF export < 5s. Non-attorney can understand in < 5 min.",
     "Contracts with financial risk data", "P0", False),

    ("TC-020", "Dashboard", "Sprint 4", "Legal Persona View",
     "Verify legal view shows clause-level drill-down",
     "1. Log in as Legal role\n2. Navigate to Legal View\n3. Click contract → section → clause\n4. Verify risk score, category, rationale, redline suggestion, benchmark\n5. Accept/reject redline",
     "Navigation hierarchy works. All fields display. Accept/reject saves to DB. Keyboard navigation works. Task completion > 85%.",
     "Contracts with analyzed clauses", "P0", False),

    ("TC-021", "Dashboard", "Sprint 4", "Procurement Persona View",
     "Verify procurement view shows vendor risk comparison",
     "1. Log in as Procurement role\n2. Navigate to Procurement View\n3. View vendor comparison matrix\n4. Sort columns\n5. Export to Excel\n6. Check risk delta vs previous",
     "Comparison renders for 50 contracts. Excel export correct. Sort works on all columns. Risk delta shows when >1 version.",
     "Multiple vendor contracts", "P0", False),

    ("TC-022", "Reporting", "Sprint 4", "PDF Executive Report Generator",
     "Generate automated PDF executive report",
     "1. Navigate to Reports\n2. Configure report (executive summary, heatmap, top clauses)\n3. Generate PDF\n4. Schedule weekly report\n5. Verify email delivery",
     "PDF generates with all sections. Scheduling works. Email delivered. Branded with logo. Opens in Adobe + browser.",
     "Configured report settings", "P1", False),

    # ══════════════════════════════════════════════════════════════════════════
    # SPRINT 5: RBAC & Audit Trail
    # ══════════════════════════════════════════════════════════════════════════
    ("TC-023", "Security", "Sprint 5", "RBAC Role Permissions",
     "Verify all 6 roles have correct permissions",
     "1. Log in as Super Admin\n2. Verify full access\n3. Log in as Legal Reviewer\n4. Verify clause-level access\n5. Log in as CFO Viewer\n6. Verify read-only access\n7. Test cross-department access",
     "Each role has correct capabilities and restrictions. Cross-department access blocked. Privilege escalation prevented.",
     "Test accounts for all 6 roles", "P0", False),

    ("TC-024", "Security", "Sprint 5", "Immutable Audit Log",
     "Verify audit log is tamper-evident with hash chain",
     "1. Perform various actions (upload, analyze, export)\n2. View audit log\n3. Verify all events recorded\n4. Attempt to modify a log entry\n5. Verify tamper detection",
     "All event types logged. Hash chain verified. Tamper detection catches modified entries. Query < 500ms for 1M events.",
     "Multiple user actions to generate events", "P0", True),

    ("TC-025", "Security", "Sprint 5", "Audit Log Export (PDF + CSV)",
     "Export audit log for regulatory submission",
     "1. Filter audit log by date range\n2. Export as PDF\n3. Export as CSV\n4. Verify all fields present\n5. Check timestamp signature",
     "PDF formatted for regulatory submission. CSV includes all fields. Filters work correctly. Export < 30s for 50K events.",
     "Audit log with 10K+ events", "P1", True),

    # ══════════════════════════════════════════════════════════════════════════
    # SPRINT 6: Integrations & API
    # ══════════════════════════════════════════════════════════════════════════
    ("TC-026", "API", "Sprint 6", "REST API v1 Endpoints",
     "Verify all v1 API endpoints are documented and functional",
     "1. Open Swagger UI at /docs\n2. Verify all endpoints listed\n3. Test GET /contracts/\n4. Test POST /risks/analyze\n5. Verify authentication required",
     "All endpoints documented with examples. Swagger UI renders. Auth required (401 without token). Rate limiting active.",
     "API access token", "P0", True),

    ("TC-027", "Integrations", "Sprint 6", "Salesforce Bidirectional Sync",
     "Verify risk scores sync to Salesforce opportunities",
     "1. Configure Salesforce connection\n2. Analyze a contract\n3. Verify risk score appears in Salesforce Opportunity\n4. Update contract status\n5. Verify stage trigger fires",
     "Bidirectional sync works on 50+ records. Risk score populates correctly. Stage trigger fires. Reconnect works after token expiry.",
     "Salesforce sandbox access", "P1", False),

    ("TC-028", "Integrations", "Sprint 6", "HubSpot Deal Risk Card",
     "Verify risk data appears in HubSpot deal sidebar",
     "1. Configure HubSpot connection\n2. Analyze a contract\n3. Open linked deal in HubSpot\n4. Verify risk card displays in sidebar\n5. Check auto-sync on risk update",
     "Risk card displays in HubSpot sidebar. Auto-sync fires within 60s of update. OAuth reconnect works.",
     "HubSpot test account", "P1", False),

    # ══════════════════════════════════════════════════════════════════════════
    # SPRINT 7: Playbook & Collaboration
    # ══════════════════════════════════════════════════════════════════════════
    ("TC-029", "Playbook", "Sprint 7", "No-Code Playbook Rule Builder",
     "Create a playbook rule using the visual IF/THEN editor",
     "1. Navigate to Playbooks\n2. Click Create New Rule\n3. Set IF condition (clause type + condition)\n4. Set THEN action (severity override + suggested language)\n5. Save rule\n6. Test on sample contract",
     "Non-lawyer can create 5-rule playbook in < 15 min without training. Preview shows correct impact. Rules save/load correctly.",
     "Playbook builder access", "P0", False),

    ("TC-030", "Playbook", "Sprint 7", "Playbook Template Library",
     "Verify all 20 pre-built playbook templates load correctly",
     "1. Navigate to Playbook Templates\n2. Browse all 20 templates\n3. Load each template\n4. Verify template description\n5. Test template on matching contract type",
     "All 20 templates load without errors. Each has accurate description. Templates customizable. FP rate < 10%.",
     "Playbook template library access", "P1", False),

    ("TC-031", "Collaboration", "Sprint 7", "Clause-Level Commenting",
     "Add comments to specific clauses with @mentions",
     "1. Open a contract\n2. Select a clause\n3. Add a comment\n4. @mention another user\n5. Verify notification sent\n6. Reply to comment\n7. Mark as resolved",
     "Comments anchored to correct clause. @mention sends notification within 30s. Email delivered. Resolved comments preserved in history.",
     "Contract with multiple users", "P1", False),

    # ══════════════════════════════════════════════════════════════════════════
    # SPRINT 8: Launch Readiness
    # ══════════════════════════════════════════════════════════════════════════
    ("TC-032", "Billing", "Sprint 8", "Stripe Subscription Tiers",
     "Verify all subscription tiers create correctly in Stripe",
     "1. Navigate to Billing Settings\n2. Select Starter tier\n3. Complete checkout\n4. Verify subscription active\n5. Upgrade to Growth tier\n6. Verify prorated charge",
     "All 4 tiers create correctly. Overage billing accurate. Failed payment triggers dunning. Upgrade flow < 5s. Tax applied correctly.",
     "Stripe test mode keys", "P0", False),

    ("TC-033", "Billing", "Sprint 8", "14-Day Free Trial Flow",
     "Verify free trial onboarding and upgrade nudges",
     "1. Sign up as new user\n2. Complete 5-step onboarding checklist\n3. Upload 5 contracts (trial limit)\n4. Verify upgrade nudge at contract limit\n5. Check email sequence",
     "Onboarding checklist completion > 60%. Nudges fire at correct triggers. Email sequence delivers. Trial data preserved on upgrade.",
     "New user signup", "P1", False),

    # ══════════════════════════════════════════════════════════════════════════
    # SPRINT 9: Explainability & RAG 2.0
    # ══════════════════════════════════════════════════════════════════════════
    ("TC-034", "Explainability", "Sprint 9", "8-Field Enterprise Explainability",
     "Verify every AI finding includes all 8 explainability fields",
     "1. Run risk analysis on any contract\n2. Expand a flagged clause\n3. Verify all 8 fields are present\n4. Check each field has meaningful content\n5. Verify linked evidence is clickable",
     "All 8 fields present: clause_text, risk_category, why_flagged, business_impact, benchmark_comparison, confidence_score, suggested_remediation, linked_evidence.",
     "Any analyzed contract", "P0", False),

    ("TC-035", "Explainability", "Sprint 9", "Low-Confidence Escalation Workflow",
     "Verify low-confidence findings are routed for attorney review",
     "1. Analyze a contract with ambiguous clauses\n2. Identify low-confidence findings\n3. Verify they appear in attorney review queue\n4. Assign to attorney\n5. Resolve with manual override",
     "Low-confidence items flagged correctly. Review queue populates. Assignment works. Resolution logged in audit trail.",
     "Contract with ambiguous clauses", "P0", False),

    ("TC-036", "Explainability", "Sprint 9", "Jurisdictional Risk Context",
     "Verify jurisdiction-specific rules are applied to risk analysis",
     "1. Analyze a contract with US governing law\n2. Check jurisdiction-specific rules applied\n3. Analyze an EU-governed contract\n4. Verify GDPR-specific rules\n5. Check UK and APAC rules",
     "US/EU/UK/APAC rules applied correctly. Jurisdiction detected from governing law clause. Risk modifiers applied per jurisdiction.",
     "Contracts with different governing laws", "P1", False),

    # ══════════════════════════════════════════════════════════════════════════
    # SPRINT 10: Contract Relationship Intelligence
    # ══════════════════════════════════════════════════════════════════════════
    ("TC-037", "Relationships", "Sprint 10", "Contract Relationship Graph",
     "Create and view contract relationship hierarchy",
     "1. Upload a parent MSA\n2. Upload child SOWs and amendments\n3. View relationship graph\n4. Verify hierarchy displays correctly\n5. Click through nodes",
     "Parent/child/amendment/addendum/DPA relationships map correctly. Graph renders with D3.js. Click-through navigates to contract.",
     "Related contract documents", "P0", False),

    ("TC-038", "Relationships", "Sprint 10", "Obligation Inheritance Tracking",
     "Verify obligations flow from parent to child contracts",
     "1. Create parent MSA with obligations\n2. Create child SOW\n3. Verify obligations inherited\n4. Override an obligation on child\n5. Check override flag",
     "Child inherits parent obligations. Override flag set when explicitly changed. Inheritance chain preserved.",
     "Parent-child contract hierarchy", "P1", False),

    ("TC-039", "Relationships", "Sprint 10", "Cross-Contract Conflict Detection",
     "Detect conflicting clauses across related contracts",
     "1. Create parent contract with liability cap of $1M\n2. Create child with unlimited liability\n3. Run conflict detection\n4. Verify contradiction flagged",
     "Contradiction detected and flagged. Severity scored. Both clauses shown side-by-side. Remediation suggested.",
     "Contracts with conflicting terms", "P1", False),

    # ══════════════════════════════════════════════════════════════════════════
    # SPRINT 11: Continuous Contract Monitoring
    # ══════════════════════════════════════════════════════════════════════════
    ("TC-040", "Monitoring", "Sprint 11", "Obligation Event Bus",
     "Verify obligation events are created and dispatched",
     "1. Trigger an obligation event (e.g., renewal approaching)\n2. Verify event appears in event list\n3. Check event details (type, priority, risk score)\n4. Acknowledge event\n5. Resolve event",
     "Event created with correct type/priority/risk score. Event appears in list. Acknowledge and resolve work. Statistics update.",
     "Event bus API endpoint", "P0", True),

    ("TC-041", "Monitoring", "Sprint 11", "Auto-Renewal Alert System",
     "Verify renewal alerts fire at configurable lead times",
     "1. Configure 30/60/90-day renewal alerts\n2. Create contract with 45-day renewal\n3. Run renewal check\n4. Verify 30-day alert fires (not 60/90)\n5. Configure custom lead times",
     "Alerts fire at correct lead times. Only closest lead time alerts. Custom lead times work. Tenant-specific config respected.",
     "Contract with known renewal date", "P0", True),

    ("TC-042", "Monitoring", "Sprint 11", "SLA Obligation Deadline Tracker",
     "Register SLA obligations and track breach risk",
     "1. Register SLA obligations with deadlines\n2. Run deadline check\n3. Verify breach risk scores computed\n4. Check escalation path\n5. Verify events emitted for at-risk/breached",
     "Breach risk scores computed correctly. Escalation path returns levels. Events emitted for at-risk and breached SLAs.",
     "SLA obligation data", "P0", True),

    ("TC-043", "Monitoring", "Sprint 11", "Insurance Certificate Expiration",
     "Register insurance certs and verify expiration alerts",
     "1. Register insurance certificates with expiry dates\n2. Run expiration check\n3. Verify warning alerts (60 days)\n4. Verify critical alerts (30 days)\n5. Check expired certs flagged",
     "Warning at 60 days. Critical at 30 days. Expired certs flagged. Coverage minimum check works. Events emitted.",
     "Insurance certificate data", "P0", True),

    ("TC-044", "Monitoring", "Sprint 11", "Compliance Drift Detection (GDPR)",
     "Check contract compliance against GDPR requirements",
     "1. Select a contract\n2. Run GDPR compliance check\n3. Verify each requirement checked\n4. Review compliance score\n5. Check recommendations for missing requirements",
     "All GDPR requirements checked. Score computed correctly. Missing requirements identified. Recommendations actionable.",
     "Contract with GDPR-relevant clauses", "P0", True),

    ("TC-045", "Monitoring", "Sprint 11", "Counterparty Litigation Monitoring",
     "Register counterparty and record litigation events",
     "1. Register a counterparty\n2. Link to contracts\n3. Record litigation event\n4. Verify event emitted for high-risk litigation\n5. Check counterparty report",
     "Litigation events recorded. High-risk events trigger obligation events. Counterparty report shows all data. Risk score updated.",
     "Counterparty with litigation data", "P1", True),

    ("TC-046", "Monitoring", "Sprint 11", "Renewal Risk Forecasting",
     "Generate renewal forecast for a contract",
     "1. Select a contract with renewal date\n2. Run renewal forecast\n3. Verify probability score\n4. Check risk factors breakdown\n5. Review recommended actions\n6. Run portfolio forecast",
     "Forecast generated with probability and churn risk. Risk factors detailed. Recommendations relevant. Portfolio forecast aggregates correctly.",
     "Contracts with renewal dates", "P1", True),

    ("TC-047", "Monitoring", "Sprint 11", "Monitoring Dashboard + Calendar",
     "View consolidated monitoring dashboard",
     "1. Navigate to Monitoring Dashboard\n2. Verify all widgets load (events, renewals, SLA, insurance, compliance, counterparties, forecasts)\n3. Open Calendar view\n4. Verify events grouped by month",
     "All widgets load with data. Calendar shows events grouped by month. Each widget links to detail view.",
     "Active monitoring data", "P0", False),

    # ══════════════════════════════════════════════════════════════════════════
    # SPRINT 12: Semantic Search & Cost Governance
    # ══════════════════════════════════════════════════════════════════════════
    ("TC-048", "Semantic Search", "Sprint 12", "Cross-Contract Semantic Search",
     "Search across all contracts using natural language",
     "1. Navigate to Search\n2. Enter natural language query (e.g., 'find uncapped indemnity clauses')\n3. View results\n4. Apply faceted filters\n5. Click through to clause\n6. Check search history",
     "Results return relevant clauses. Intent detection works. Filters refine results. Search history populated. Popular searches tracked.",
     "Multiple contracts with varied clauses", "P0", False),

    ("TC-049", "Semantic Search", "Sprint 12", "Real-Time Search Index Pipeline",
     "Verify new contracts are indexed immediately after ingestion",
     "1. Upload a new contract\n2. Wait for ingestion to complete\n3. Immediately search for a clause from the contract\n4. Verify it appears in results",
     "New contract indexed within seconds of ingestion completion. Search returns results from newly ingested contract.",
     "New contract to upload and search", "P0", True),

    ("TC-050", "Cost Governance", "Sprint 12", "AI Cost Governance Dashboard",
     "View LLM cost tracking and analytics",
     "1. Navigate to Cost Dashboard\n2. Verify total cost displayed\n3. Check cost by provider breakdown\n4. View daily cost trend\n5. Check cost by model",
     "Total cost, by-provider, by-model, and daily trend all display correctly. Data matches actual usage.",
     "LLM usage history", "P0", True),

    ("TC-051", "Cost Governance", "Sprint 12", "Tenant Quota Management",
     "Set and enforce token quotas per tenant",
     "1. Set soft limit (1M tokens) and hard limit (2M tokens) for a tenant\n2. Exceed soft limit\n3. Verify warning\n4. Exceed hard limit\n5. Verify requests blocked\n6. Check quota alerts",
     "Soft limit triggers warning. Hard limit blocks requests. Alerts generated. Quota usage percentage displayed.",
     "Tenant quota configuration", "P0", True),

    ("TC-052", "Cost Governance", "Sprint 12", "Model Routing Optimization",
     "Verify optimal model is selected based on task complexity",
     "1. Configure model routing rules\n2. Request simple task (classification)\n3. Verify cheapest adequate model selected\n4. Request complex task (redline)\n5. Verify most capable model selected\n6. Check tenant-specific overrides",
     "Simple tasks route to cheap models. Complex tasks route to capable models. Tenant overrides respected. Fallback works.",
     "Model routing configuration", "P1", True),

    ("TC-053", "Cost Governance", "Sprint 12", "Batch Inference Scheduler",
     "Submit batch job and verify off-peak scheduling",
     "1. Submit a batch inference job\n2. Verify job queued\n3. Check scheduled time (off-peak)\n4. Process queue\n5. Verify results stored\n6. Check cost multiplier applied",
     "Job queued with correct priority. Scheduled for off-peak. Processed with concurrency limit. Cost multiplier applied.",
     "Batch job items", "P1", True),

    # ══════════════════════════════════════════════════════════════════════════
    # SPRINT 13: Benchmark Phase 2 & Procurement
    # ══════════════════════════════════════════════════════════════════════════
    ("TC-054", "Benchmarking", "Sprint 13", "Opt-In Benchmark Corpus Contribution",
     "Tenant opts in to contribute anonymized contract data",
     "1. Navigate to Benchmark Settings\n2. Opt in to data contribution\n3. Configure anonymization level\n4. Contribute a contract\n5. Verify PII anonymized\n6. Check contribution history",
     "Agreement registered. Contract anonymized (PII removed). Quality filtered. Contribution recorded in history.",
     "Benchmark contribution settings", "P1", True),

    ("TC-055", "Benchmarking", "Sprint 13", "Industry Segmentation Phase 2",
     "Classify contracts into 10+ industry verticals",
     "1. Upload contracts from different industries\n2. Run industry classification\n3. Verify correct industry detected\n4. Check sub-vertical detection\n5. View all available verticals",
     "12 verticals available. Classification accuracy > 87%. Sub-vertical detected when applicable. Fallback to general commercial.",
     "Contracts from diverse industries", "P1", True),

    ("TC-056", "Benchmarking", "Sprint 13", "Benchmark Confidence Scoring",
     "Verify confidence scores and reliability indicators",
     "1. Compute confidence for a benchmark segment\n2. Verify confidence score (0-1)\n3. Check reliability label\n4. Review caveats\n5. Check freshness indicator\n6. Verify recommended_for_reporting flag",
     "Confidence score computed from sample size, variance, freshness. Reliability label appropriate. Caveats relevant. Color/icon correct.",
     "Benchmark segment data", "P1", True),

    ("TC-057", "Procurement", "Sprint 13", "SAP Ariba / Coupa Integration",
     "Configure procurement platform and import purchase orders",
     "1. Configure SAP Ariba connection\n2. Import purchase orders\n3. Verify POs stored with risk linkage\n4. Link PO to contract\n5. Check PO risk summary",
     "Connection configured. Purchase orders imported. PO linked to contract. Risk summary shows aggregated data.",
     "Procurement platform credentials", "P1", False),

    ("TC-058", "Procurement", "Sprint 13", "Vendor Onboarding Workflow",
     "Onboard a new vendor through multi-stage workflow",
     "1. Initiate vendor onboarding\n2. Enter vendor details\n3. Run AI risk gate\n4. Review risk score\n5. Advance through approval stages\n6. Complete onboarding",
     "Onboarding initiated. AI risk gate scores vendor correctly. Stages advance properly. Final approval completes workflow.",
     "Vendor information", "P0", False),

    ("TC-059", "Procurement", "Sprint 13", "Supplier Concentration Analysis",
     "Analyze supplier concentration across portfolio",
     "1. Run supplier concentration analysis\n2. View HHI score\n3. Check top suppliers by concentration\n4. View risk heatmap\n5. Check category analysis\n6. Review recommendations",
     "HHI computed correctly. Top suppliers identified. Heatmap shows risk dimensions. Category analysis breaks down by type. Recommendations actionable.",
     "Contract portfolio with multiple suppliers", "P1", True),

    # ══════════════════════════════════════════════════════════════════════════
    # CROSS-CUTTING: UX & Accessibility
    # ══════════════════════════════════════════════════════════════════════════
    ("TC-060", "UX/Accessibility", "Sprint 13", "Dark Mode Toggle",
     "Toggle between light and dark mode",
     "1. Click theme toggle button\n2. Verify dark mode applied\n3. Navigate through all views\n4. Verify all components render correctly in dark mode\n5. Toggle back to light mode\n6. Verify preference saved",
     "Dark mode applies to all views. All components readable. Text contrast sufficient. Preference persists across sessions.",
     "Theme toggle in toolbar", "P1", False),

    ("TC-061", "UX/Accessibility", "Sprint 13", "WCAG 2.1 AA Keyboard Navigation",
     "Navigate the entire application using keyboard only",
     "1. Use Tab to navigate through all interactive elements\n2. Use Enter/Space to activate\n3. Use arrow keys for navigation where applicable\n4. Verify skip-to-content link works\n5. Check focus indicators visible",
     "All interactive elements reachable via keyboard. Focus indicators visible (gold outline). Skip-to-content link appears on first Tab.",
     "Keyboard-only interaction", "P1", False),

    ("TC-062", "UX/Accessibility", "Sprint 13", "Font Size Scaling",
     "Increase and decrease font size across the application",
     "1. Click Zoom In button\n2. Verify font size increases\n3. Navigate through views\n4. Verify all text scales\n5. Click Zoom Out\n6. Verify font size decreases\n7. Check preference saved",
     "Font size scales proportionally across all views. No layout breakage at 125% and 150%. Preference persists.",
     "Font size controls in toolbar", "P2", False),

    ("TC-063", "UX/Accessibility", "Sprint 13", "Reduced Motion Support",
     "Verify animations respect reduced motion preference",
     "1. Enable 'Reduce motion' in OS settings\n2. Reload application\n3. Verify animations are reduced or disabled\n4. Check transitions are instant\n5. Verify no content is hidden due to disabled animations",
     "Animations disabled or reduced. Transitions instant. No content hidden. All functionality works without animations.",
     "OS accessibility settings", "P2", False),

    # ══════════════════════════════════════════════════════════════════════════
    # CROSS-CUTTING: API & Performance
    # ══════════════════════════════════════════════════════════════════════════
    ("TC-064", "API", "Cross-Cutting", "API Authentication & Authorization",
     "Verify all endpoints require valid authentication",
     "1. Call any API endpoint without token\n2. Verify 401 response\n3. Call with expired token\n4. Call with insufficient permissions\n5. Verify 403 response",
     "Unauthenticated requests return 401. Expired tokens rejected. Insufficient permissions return 403.",
     "API test client", "P0", True),

    ("TC-065", "API", "Cross-Cutting", "Rate Limiting",
     "Verify rate limiting is enforced",
     "1. Send 101 requests in quick succession\n2. Verify 100th request succeeds\n3. Verify 101st request returns 429\n4. Wait for rate limit window to reset\n5. Verify request succeeds again",
     "Rate limit of 100 req/min enforced. 429 returned on exceed. Rate limit resets after window.",
     "API load test script", "P1", True),

    ("TC-066", "Performance", "Cross-Cutting", "Concurrent Contract Ingestion",
     "Upload 100 contracts simultaneously and measure throughput",
     "1. Prepare 100 contract files (20-50 pages each)\n2. Upload all simultaneously\n3. Measure P50/P95/P99 ingestion time\n4. Check error rate\n5. Measure queue depth\n6. Calculate cost per 1,000 contracts",
     "P95 ingestion time < 120s at 1,000 concurrent. Error rate < 0.1%. Queue depth manageable (< 2,000). Cost calculated.",
     "100 contract files", "P1", False),
]


# ── Excel Generation ─────────────────────────────────────────────────────────
def create_test_excel():
    wb = openpyxl.Workbook()

    # =========================================================================
    # SHEET 1: 📋 Manual Test Script
    # =========================================================================
    ws = wb.active
    ws.title = "📋 Manual Test Script"

    # Column widths
    col_widths = {
        "A": 10,   # Test ID
        "B": 20,   # Feature Area
        "C": 12,   # Sprint
        "D": 35,   # Test Name
        "E": 40,   # Description
        "F": 55,   # Test Steps
        "G": 45,   # Expected Result
        "H": 30,   # Test Data
        "I": 8,    # Priority
        "J": 14,   # Automation Possible
        "K": 14,   # Status
        "L": 20,   # Tester
        "M": 14,   # Date Tested
        "N": 30,   # Notes / Bugs
    }
    for col, width in col_widths.items():
        ws.column_dimensions[col].width = width

    # Title row
    ws.merge_cells("A1:N1")
    title_cell = ws["A1"]
    title_cell.value = "AI Contract Risk Analyzer — V2.2 Manual Test Script"
    title_cell.font = Font(bold=True, size=16, color=WHITE, name="Calibri")
    title_cell.fill = hex_fill(NAVY)
    title_cell.alignment = center_align()
    ws.row_dimensions[1].height = 35

    # Subtitle
    ws.merge_cells("A2:N2")
    sub_cell = ws["A2"]
    sub_cell.value = f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}  |  Total Test Cases: {len(TEST_CASES)}  |  Coverage: Sprints 1-13 + V2 Improvements"
    sub_cell.font = Font(size=10, color=NAVY, name="Calibri", italic=True)
    sub_cell.fill = hex_fill(LTGOLD)
    sub_cell.alignment = center_align()
    ws.row_dimensions[2].height = 22

    # Legend row
    ws.merge_cells("A3:N3")
    leg_cell = ws["A3"]
    leg_cell.value = "P0 = Critical (must pass)  |  P1 = High (should pass)  |  P2 = Medium (nice to have)  |  Status: ✅ Pass  ❌ Fail  ⏳ In Progress  ⬜ Not Tested"
    leg_cell.font = Font(size=9, color=WHITE, name="Calibri")
    leg_cell.fill = hex_fill(TEAL)
    leg_cell.alignment = center_align()
    ws.row_dimensions[3].height = 20

    # Column headers (row 4)
    headers = ["Test ID", "Feature Area", "Sprint", "Test Name", "Description",
               "Test Steps", "Expected Result", "Test Data / Prerequisites",
               "Pri", "Auto?", "Status", "Tester", "Date", "Notes / Bugs"]
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col_idx, value=header)
        cell.font = Font(bold=True, size=10, color=WHITE, name="Calibri")
        cell.fill = hex_fill(NAVY)
        cell.alignment = center_align()
        cell.border = thin_border()
    ws.row_dimensions[4].height = 25

    # Status colors for conditional formatting reference
    status_colors = {
        "✅ Pass": hex_fill(LTGREEN),
        "❌ Fail": hex_fill(LTRED),
        "⏳ In Progress": hex_fill(LTORANGE),
        "⬜ Not Tested": hex_fill(GRAY1),
    }

    # Data rows
    for row_idx, tc in enumerate(TEST_CASES, 5):
        test_id, feature, sprint, name, desc, steps, expected, test_data, priority, auto = tc

        row_data = [
            test_id, feature, sprint, name, desc, steps, expected,
            test_data, priority, "Yes" if auto else "No",
            "⬜ Not Tested", "", "", ""
        ]

        for col_idx, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.font = body_font()
            cell.alignment = wrap_align()
            cell.border = thin_border()

            # Alternate row shading
            if row_idx % 2 == 0:
                cell.fill = hex_fill(LTGRAY)

        # Center-align specific columns
        for c in [1, 3, 9, 10, 11, 13]:
            ws.cell(row=row_idx, column=c).alignment = center_align()

        # Priority coloring
        pri_cell = ws.cell(row=row_idx, column=9)
        if priority == "P0":
            pri_cell.fill = hex_fill(LTRED)
            pri_cell.font = Font(bold=True, size=9, color=RED, name="Calibri")
        elif priority == "P1":
            pri_cell.fill = hex_fill(LTORANGE)
            pri_cell.font = Font(bold=True, size=9, color=ORANGE, name="Calibri")
        else:
            pri_cell.fill = hex_fill(LTBLUE)
            pri_cell.font = Font(size=9, color=BLUE, name="Calibri")

        # Row height for readability
        ws.row_dimensions[row_idx].height = 85

    # Freeze panes
    ws.freeze_panes = "A5"

    # Auto-filter
    ws.auto_filter.ref = f"A4:N{4 + len(TEST_CASES)}"

    # =========================================================================
    # SHEET 2: 📊 Summary Dashboard
    # =========================================================================
    ws2 = wb.create_sheet("📊 Summary Dashboard")

    # Title
    ws2.merge_cells("A1:F1")
    ws2["A1"].value = "Test Execution Summary Dashboard"
    ws2["A1"].font = Font(bold=True, size=14, color=WHITE, name="Calibri")
    ws2["A1"].fill = hex_fill(NAVY)
    ws2["A1"].alignment = center_align()
    ws2.row_dimensions[1].height = 30

    # Summary by feature area
    ws2.merge_cells("A3:F3")
    ws2["A3"].value = "Test Coverage by Feature Area"
    ws2["A3"].font = Font(bold=True, size=11, color=NAVY, name="Calibri")
    ws2["A3"].fill = hex_fill(LTGOLD)

    feat_headers = ["Feature Area", "Total Tests", "P0 Tests", "P1 Tests", "P2 Tests", "Auto-Coverage"]
    for col_idx, h in enumerate(feat_headers, 1):
        cell = ws2.cell(row=4, column=col_idx, value=h)
        cell.font = Font(bold=True, size=9, color=WHITE, name="Calibri")
        cell.fill = hex_fill(NAVY)
        cell.alignment = center_align()
        cell.border = thin_border()

    # Aggregate by feature
    from collections import OrderedDict
    features = OrderedDict()
    for tc in TEST_CASES:
        feat = tc[1]
        if feat not in features:
            features[feat] = {"total": 0, "p0": 0, "p1": 0, "p2": 0, "auto": 0}
        features[feat]["total"] += 1
        if tc[8] == "P0":
            features[feat]["p0"] += 1
        elif tc[8] == "P1":
            features[feat]["p1"] += 1
        else:
            features[feat]["p2"] += 1
        if tc[9]:
            features[feat]["auto"] += 1

    row = 5
    for feat, counts in features.items():
        ws2.cell(row=row, column=1, value=feat).font = body_font()
        ws2.cell(row=row, column=2, value=counts["total"]).font = body_font()
        ws2.cell(row=row, column=3, value=counts["p0"]).font = Font(bold=True, size=9, color=RED, name="Calibri")
        ws2.cell(row=row, column=4, value=counts["p1"]).font = Font(size=9, color=ORANGE, name="Calibri")
        ws2.cell(row=row, column=5, value=counts["p2"]).font = Font(size=9, color=BLUE, name="Calibri")
        ws2.cell(row=row, column=6, value=f"{counts['auto']}/{counts['total']}").font = body_font()
        for c in range(1, 7):
            ws2.cell(row=row, column=c).border = thin_border()
            ws2.cell(row=row, column=c).alignment = center_align()
        if row % 2 == 0:
            for c in range(1, 7):
                ws2.cell(row=row, column=c).fill = hex_fill(LTGRAY)
        row += 1

    # Totals
    total_all = len(TEST_CASES)
    total_p0 = sum(1 for tc in TEST_CASES if tc[8] == "P0")
    total_p1 = sum(1 for tc in TEST_CASES if tc[8] == "P1")
    total_p2 = sum(1 for tc in TEST_CASES if tc[8] == "P2")
    total_auto = sum(1 for tc in TEST_CASES if tc[9])

    ws2.cell(row=row, column=1, value="TOTAL").font = Font(bold=True, size=10, color=WHITE, name="Calibri")
    ws2.cell(row=row, column=2, value=total_all).font = Font(bold=True, size=10, color=WHITE, name="Calibri")
    ws2.cell(row=row, column=3, value=total_p0).font = Font(bold=True, size=10, color=WHITE, name="Calibri")
    ws2.cell(row=row, column=4, value=total_p1).font = Font(bold=True, size=10, color=WHITE, name="Calibri")
    ws2.cell(row=row, column=5, value=total_p2).font = Font(bold=True, size=10, color=WHITE, name="Calibri")
    ws2.cell(row=row, column=6, value=f"{total_auto}/{total_all} ({round(total_auto/total_all*100)}%)").font = Font(bold=True, size=10, color=WHITE, name="Calibri")
    for c in range(1, 7):
        ws2.cell(row=row, column=c).fill = hex_fill(NAVY)
        ws2.cell(row=row, column=c).alignment = center_align()
        ws2.cell(row=row, column=c).border = thin_border()

    # Column widths
    ws2.column_dimensions["A"].width = 22
    for col in ["B", "C", "D", "E", "F"]:
        ws2.column_dimensions[col].width = 16

    # =========================================================================
    # SHEET 3: 📊 Sprint Coverage
    # =========================================================================
    ws3 = wb.create_sheet("🗓️ Sprint Coverage")

    ws3.merge_cells("A1:D1")
    ws3["A1"].value = "Test Coverage by Sprint"
    ws3["A1"].font = Font(bold=True, size=14, color=WHITE, name="Calibri")
    ws3["A1"].fill = hex_fill(NAVY)
    ws3["A1"].alignment = center_align()
    ws3.row_dimensions[1].height = 30

    sprint_headers = ["Sprint", "Test Cases", "P0 Tests", "Feature Areas Covered"]
    for col_idx, h in enumerate(sprint_headers, 1):
        cell = ws3.cell(row=3, column=col_idx, value=h)
        cell.font = Font(bold=True, size=9, color=WHITE, name="Calibri")
        cell.fill = hex_fill(NAVY)
        cell.alignment = center_align()
        cell.border = thin_border()

    # Group by sprint
    sprints = OrderedDict()
    for tc in TEST_CASES:
        sprint = tc[2]
        if sprint not in sprints:
            sprints[sprint] = {"total": 0, "p0": 0, "features": set()}
        sprints[sprint]["total"] += 1
        if tc[8] == "P0":
            sprints[sprint]["p0"] += 1
        sprints[sprint]["features"].add(tc[1])

    row = 4
    for sprint, data in sprints.items():
        ws3.cell(row=row, column=1, value=sprint).font = body_font()
        ws3.cell(row=row, column=2, value=data["total"]).font = body_font()
        ws3.cell(row=row, column=3, value=data["p0"]).font = Font(bold=True, size=9, color=RED, name="Calibri")
        ws3.cell(row=row, column=4, value=", ".join(sorted(data["features"]))).font = body_font()
        for c in range(1, 5):
            ws3.cell(row=row, column=c).border = thin_border()
            ws3.cell(row=row, column=c).alignment = wrap_align() if c == 4 else center_align()
        if row % 2 == 0:
            for c in range(1, 5):
                ws3.cell(row=row, column=c).fill = hex_fill(LTGRAY)
        row += 1

    ws3.column_dimensions["A"].width = 18
    ws3.column_dimensions["B"].width = 14
    ws3.column_dimensions["C"].width = 12
    ws3.column_dimensions["D"].width = 55

    # =========================================================================
    # SAVE
    # =========================================================================
    filepath = "/Volumes/home/ContractRiskEdge/output/Manual_Test_Script_V2.2.xlsx"
    wb.save(filepath)
    print(f"✅ Manual Test Script generated: {filepath}")
    print(f"   Total Test Cases: {len(TEST_CASES)}")
    print(f"   P0 (Critical): {total_p0}")
    print(f"   P1 (High): {total_p1}")
    print(f"   P2 (Medium): {total_p2}")
    print(f"   Automation Possible: {total_auto}/{total_all} ({round(total_auto/total_all*100)}%)")
    print(f"   Feature Areas: {len(features)}")
    print(f"   Sprints Covered: {len(sprints)}")

    # Print summary by sprint
    print("\n   Coverage by Sprint:")
    for sprint, data in sprints.items():
        print(f"     {sprint}: {data['total']} tests ({data['p0']} P0) - {', '.join(sorted(data['features']))}")


if __name__ == "__main__":
    create_test_excel()
