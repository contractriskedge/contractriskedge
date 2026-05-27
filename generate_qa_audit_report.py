"""Generate the comprehensive QA Audit Report as a Word document.

Usage: python generate_qa_audit_report.py
"""
from docx import Document
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import datetime

doc = Document()

# ── Styles ──────────────────────────────────────────────────────────────────
style = doc.styles['Normal']
font = style.font
font.name = 'Calibri'
font.size = Pt(10.5)

for level in range(1, 4):
    heading_style = doc.styles[f'Heading {level}']
    heading_style.font.color.rgb = RGBColor(0x1B, 0x3A, 0x6B)

def add_colored_table(doc, headers, rows, col_widths=None):
    """Add a styled table."""
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = 'Table Grid'
    
    # Header row
    for i, header in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = header
        for paragraph in cell.paragraphs:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in paragraph.runs:
                run.bold = True
                run.font.size = Pt(9)
                run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        shading = OxmlElement('w:shd')
        shading.set(qn('w:fill'), '1B3A6B')
        shading.set(qn('w:val'), 'clear')
        cell._tc.get_or_add_tcPr().append(shading)
    
    # Data rows
    for r_idx, row_data in enumerate(rows):
        for c_idx, cell_text in enumerate(row_data):
            cell = table.rows[r_idx + 1].cells[c_idx]
            cell.text = str(cell_text)
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(9)
            if r_idx % 2 == 1:
                shading = OxmlElement('w:shd')
                shading.set(qn('w:fill'), 'F3F4F6')
                shading.set(qn('w:val'), 'clear')
                cell._tc.get_or_add_tcPr().append(shading)
    
    doc.add_paragraph()
    return table

def add_status_box(doc, text, level):
    """Add a colored status box."""
    colors = {
        'CRITICAL': ('DC2626', 'FEE2E2'),
        'HIGH': ('EA580C', 'FFF7ED'),
        'MEDIUM': ('CA8A04', 'FEF3C7'),
        'LOW': ('16A34A', 'DCFCE7'),
        'IMPLEMENTED': ('16A34A', 'DCFCE7'),
        'PARTIAL': ('CA8A04', 'FEF3C7'),
        'NOT IMPLEMENTED': ('DC2626', 'FEE2E2'),
        'BACKEND ONLY': ('EA580C', 'FFF7ED'),
        'UI ONLY': ('EA580C', 'FFF7ED'),
    }
    fg, bg = colors.get(level.upper(), ('6B7280', 'F3F4F6'))
    p = doc.add_paragraph()
    run = p.add_run(f' [{level.upper()}] {text}')
    run.bold = True
    run.font.size = Pt(10)
    run.font.color.rgb = RGBColor(*[int(fg[i:i+2], 16) for i in (0, 2, 4)])
    return p

# ══════════════════════════════════════════════════════════════════════════════
# TITLE PAGE
# ══════════════════════════════════════════════════════════════════════════════
doc.add_paragraph()
doc.add_paragraph()
title = doc.add_paragraph()
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = title.add_run('CONTRACTRISKEDGE')
run.bold = True
run.font.size = Pt(28)
run.font.color.rgb = RGBColor(0x1B, 0x3A, 0x6B)

subtitle = doc.add_paragraph()
subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = subtitle.add_run('Enterprise Codebase Implementation Audit')
run.bold = True
run.font.size = Pt(20)
run.font.color.rgb = RGBColor(0xC9, 0xA8, 0x4C)

doc.add_paragraph()
meta = doc.add_paragraph()
meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
meta.add_run(f'Date: {datetime.date.today().strftime("%B %d, %Y")}\n').font.size = Pt(11)
meta.add_run('Auditor: Senior Enterprise Software Auditor\n').font.size = Pt(11)
meta.add_run('Platform: AI Contract Risk Analyzer v1.0.0\n').font.size = Pt(11)
meta.add_run('Codebase: ~42,000+ lines across backend + frontend\n').font.size = Pt(11)

doc.add_page_break()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1: CURRENT ARCHITECTURE
# ══════════════════════════════════════════════════════════════════════════════
doc.add_heading('1. Current Architecture', level=1)

doc.add_heading('1.1 Technology Stack', level=2)
add_colored_table(doc,
    ['Layer', 'Technology', 'Version / Details'],
    [
        ['Frontend Framework', 'Next.js 14 (App Router)', 'React 18, TypeScript 5.4'],
        ['UI Libraries', 'Tailwind CSS v4, Radix UI, Framer Motion', 'Recharts, D3.js, react-dropzone'],
        ['State / Data', 'TanStack React Query v5', 'Client-side cache + polling'],
        ['Backend Framework', 'FastAPI', 'Python 3.12, async/await throughout'],
        ['ORM', 'SQLAlchemy 2.0 (async)', 'asyncpg driver, Alembic migrations'],
        ['Database', 'PostgreSQL 16 + pgvector', 'RLS, table partitioning, GIN/ivfflat indexes'],
        ['Cache / Queue', 'Redis 7', 'Celery broker + result backend'],
        ['Task Queue', 'Celery 5.4', '5 queues: ingestion, ai, notifications, playbook, default'],
        ['Object Storage', 'MinIO (S3-compatible)', 'Document storage, 100MB limit'],
        ['Auth Provider', 'Auth0', 'RS256 JWT, JWKS caching, RBAC'],
        ['AI Provider', 'OpenAI API', 'GPT-4o, text-embedding-3-small (1536d)'],
        ['Vector Store', 'pgvector', 'ivfflat index, cosine similarity'],
        ['Observability', 'Prometheus + OpenTelemetry + Sentry', '/metrics endpoint, OTLP export'],
        ['Containerization', 'Docker Compose', '6 services: postgres, redis, minio, backend, worker, frontend'],
        ['Async Events', 'In-memory EventBus + WebSocket', 'Real-time event streaming'],
    ]
)

doc.add_heading('1.2 Directory Structure', level=2)
p = doc.add_paragraph()
p.style.font.size = Pt(9)
lines = """backend/
  app/
    domains/          # 16 domain modules (ingestion, ai, review, search, ...)
    kernel/           # Core framework (database, security, telemetry, events, middleware)
    integrations/     # External storage (MinIO/S3)
    integration/      # External connectors (SharePoint, Google Drive, DocuSign, ...)
  workers/            # Celery workers (9 worker modules)
  alembic/            # Database migrations

frontend/
  app/                # Next.js App Router (single page SPA)
  components/         # ~195 React components across 20+ subdirectories
  services/           # API client + TanStack Query hooks
  lib/                # Legacy API client

infra/                # SQL schema, seed data, production schema
docs/                 # Architecture documentation"""
p.add_run(lines).font.size = Pt(9)

doc.add_page_break()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2: IMPLEMENTED SCREENS
# ══════════════════════════════════════════════════════════════════════════════
doc.add_heading('2. Implemented Screens', level=1)

doc.add_paragraph('The application is a Single Page Application (SPA) rendered under a single Next.js route (/). View switching is handled client-side via the DashboardLayout component.')

add_colored_table(doc,
    ['Screen / View', 'Route (SPA View)', 'Backend Connected?', 'Mock Data?', 'Production Ready?'],
    [
        ['Login Page', 'Default (no auth)', 'Yes', 'No', 'Yes'],
        ['Ingestion Center', 'ingestion', 'Yes', 'Partial (connectors, queue controls, analytics tabs are mock)', 'Partial'],
        ['Review Queue', 'review (list)', 'Yes', 'No', 'Yes'],
        ['Review Workspace', 'review (detail)', 'Yes', 'No', 'Yes'],
        ['Search & Discovery', 'search', 'Yes', 'No', 'Yes'],
        ['Analytics Center', 'analytics', 'Yes', 'No', 'Yes'],
        ['Admin Console', 'admin', 'Yes', 'No', 'Yes'],
        ['Notification Center', 'TopNav dropdown', 'Yes', 'No', 'Yes'],
        ['AI Copilot Chat', 'Floating panel', 'No', 'Yes (mock responses)', 'No'],
        ['Executive Dashboard', 'N/A (component exists)', 'Yes', 'No', 'Yes'],
        ['Portfolio Dashboard', 'N/A (component exists)', 'Partial (uses legacy api.ts)', 'No', 'Partial'],
        ['Benchmark Page', 'N/A (component exists)', 'Partial (uses legacy api.ts)', 'No', 'Partial'],
        ['Relationship Graph', 'N/A (component exists)', 'Partial (uses legacy api.ts)', 'No', 'Partial'],
        ['Negotiation Center', 'N/A (component exists)', 'No', 'Yes (full mock)', 'No'],
        ['Benchmark Detail', 'N/A (component exists)', 'No', 'Yes (full mock)', 'No'],
    ]
)

doc.add_page_break()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3: FEATURE MATRIX TABLE
# ══════════════════════════════════════════════════════════════════════════════
doc.add_heading('3. Feature Implementation Matrix', level=1)

doc.add_heading('3.1 Authentication & Authorization', level=2)
add_colored_table(doc,
    ['Feature', 'Status', 'Backend Evidence', 'Frontend Evidence', 'Missing Pieces'],
    [
        ['Auth0 JWT Integration', 'IMPLEMENTED',
         'app/kernel/security/auth.py: JWTValidator, JWKSProvider, RS256 + HS256 dev fallback',
         'components/auth/AuthProvider.tsx, LoginPage.tsx',
         'None'],
        ['RBAC / Permissions', 'IMPLEMENTED',
         'app/kernel/security/rbac.py: require_permission, require_any_permission decorators; 20+ permissions defined',
         'Sidebar.tsx filters nav by role',
         'None'],
        ['Multi-Tenant Isolation', 'IMPLEMENTED',
         'app/kernel/middleware/tenant_context.py, app/kernel/database/session.py: RLS via session variables',
         'All API calls include tenant context',
         'None'],
        ['Dev Auth Bypass', 'IMPLEMENTED',
         'app/kernel/dev_token.py, app/domains/health/dev_auth.py: /auth/token endpoint',
         'AuthProvider uses dev token in localStorage',
         'None'],
        ['API Key Auth', 'NOT IMPLEMENTED',
         'No API key model or validation found',
         'N/A',
         'No machine-to-machine API key support'],
    ]
)

doc.add_heading('3.2 Contract Upload & Ingestion', level=2)
add_colored_table(doc,
    ['Feature', 'Status', 'Backend Evidence', 'Frontend Evidence', 'Missing Pieces'],
    [
        ['File Upload (Multipart)', 'IMPLEMENTED',
         'app/domains/ingestion/router.py: POST /uploads/, 751-line router, 279-line service',
         'components/dashboard/ingestion/: UploadZone, JobCard, PipelineVisualizer',
         'None'],
        ['File Validation', 'IMPLEMENTED',
         'app/domains/ingestion/security.py: extension, magic bytes, checksum, size validation',
         'Client-side validation in UploadZone',
         'None'],
        ['MinIO/S3 Storage', 'IMPLEMENTED',
         'app/integrations/storage/s3.py: storage_service, warm_up(), bucket management',
         'N/A (backend only)',
         'None'],
        ['Duplicate Detection', 'IMPLEMENTED',
         'app/domains/ingestion/service.py: checksum-based duplicate detection',
         'IngestionInsightsPanel.tsx (shows empty arrays)',
         'Frontend shows duplicate groups but data is empty'],
        ['Rate Limiting', 'IMPLEMENTED',
         'app/domains/ingestion/service.py: per-tenant rate limiting',
         'N/A',
         'None'],
        ['Ingestion State Machine', 'IMPLEMENTED',
         'app/domains/ingestion/models.py: 15-state machine (UPLOADED through REVIEW_READY)',
         'PipelineVisualizer.tsx maps states to stages',
         'None'],
        ['Celery Async Pipeline', 'IMPLEMENTED',
         'workers/ingestion_pipeline.py: extract_document_task, chunk_document_task, generate_embeddings_task, finalize_task',
         'Status polling via useUploadStatus',
         'None'],
        ['OCR Pipeline', 'IMPLEMENTED',
         'workers/ingestion_ocr.py, app/domains/extraction/: parsers.py, quality.py',
         'N/A (backend only)',
         'None'],
        ['Source Connectors (Google Drive, SharePoint, etc.)', 'BACKEND ONLY',
         'app/integration/connectors/: google_drive.py, sharepoint.py, onedrive.py, docusign.py, salesforce.py, sap_ariba.py, servicenow.py, jira.py, slack.py, teams.py',
         'IngestionSourcesPanel.tsx (buttons exist, calls are no-ops)',
         'Integration router NOT registered in main.py. Connector code exists but not wired.'],
    ]
)

doc.add_heading('3.3 OCR & Text Extraction', level=2)
add_colored_table(doc,
    ['Feature', 'Status', 'Backend Evidence', 'Frontend Evidence', 'Missing Pieces'],
    [
        ['PDF Text Extraction', 'IMPLEMENTED',
         'app/domains/extraction/parsers.py: PyMuPDF parser, quality.py: quality evaluation',
         'N/A (backend only)',
         'None'],
        ['OCR Fallback', 'IMPLEMENTED',
         'app/domains/extraction/models.py: ExtractionRun with 5 methods including ocr_textract, ocr_fallback',
         'N/A (backend only)',
         'None'],
        ['Extraction Quality Metrics', 'IMPLEMENTED',
         'app/domains/extraction/quality.py, models.py: ExtractedPage with confidence, blank_ratio, has_text_layer',
         'N/A (backend only)',
         'None'],
        ['DOCX Extraction', 'IMPLEMENTED',
         'python-docx in requirements.txt, parsers.py handles DOCX',
         'N/A (backend only)',
         'None'],
    ]
)

doc.add_heading('3.4 Clause Extraction', level=2)
add_colored_table(doc,
    ['Feature', 'Status', 'Backend Evidence', 'Frontend Evidence', 'Missing Pieces'],
    [
        ['Clause Segmentation', 'IMPLEMENTED',
         'app/domains/extraction/normalizer.py: clause boundary detection, section parsing',
         'N/A (backend only)',
         'None'],
        ['Clause Type Classification', 'IMPLEMENTED',
         'app/domains/ai/service.py: 30+ clause type canonicalization mappings',
         'N/A (backend only)',
         'None'],
        ['Chunking Strategies', 'IMPLEMENTED',
         'app/domains/vectors/models.py: DocumentChunk with 4 chunking strategies',
         'N/A (backend only)',
         'None'],
    ]
)

doc.add_heading('3.5 AI Risk Analysis', level=2)
add_colored_table(doc,
    ['Feature', 'Status', 'Backend Evidence', 'Frontend Evidence', 'Missing Pieces'],
    [
        ['AI Analysis Pipeline', 'IMPLEMENTED',
         'app/domains/ai/router.py: POST /ai/analyze, service.py: 814-line orchestration',
         'UploadService: triggerAnalysis, getAnalysisRun, getAnalysisFindings',
         'None'],
        ['OpenAI Integration', 'IMPLEMENTED',
         'openai dependency, structured output parsing, prompt versioning',
         'N/A (backend only)',
         'None'],
        ['Risk Scoring', 'IMPLEMENTED',
         'app/domains/ai/service.py: confidence calibration, risk_score computation',
         'RiskBreakdownPanel.tsx, RiskGauge',
         'None'],
        ['Finding Classification', 'IMPLEMENTED',
         'app/domains/ai/models.py: AiFinding with 6 finding types, 5 severities',
         'FindingsList.tsx, FindingCard.tsx',
         'None'],
        ['AI Response Caching', 'IMPLEMENTED',
         'app/domains/ai/models.py: AiResponseCache (tenant-isolated)',
         'N/A (backend only)',
         'None'],
        ['Prompt Versioning', 'IMPLEMENTED',
         'app/domains/ai/models.py: AiPromptTemplate (versioned registry)',
         'N/A (backend only)',
         'None'],
        ['AI Explainability Layer', 'PARTIAL',
         'Risk flags include why_flagged, potential_business_impact, linked_evidence, jurisdictional_considerations in legacy api.ts types',
         'No dedicated explainability UI component',
         'No frontend explainability panel. Backend schema supports it but no dedicated endpoint.'],
    ]
)

doc.add_heading('3.6 Redline Generation', level=2)
add_colored_table(doc,
    ['Feature', 'Status', 'Backend Evidence', 'Frontend Evidence', 'Missing Pieces'],
    [
        ['AI Redline Suggestions', 'IMPLEMENTED',
         'app/domains/ai/models.py: AiRedline with 8 field types, operation, anchor_text',
         'RedlineCard.tsx, RedlineEditor.tsx, RedlineDiff.tsx',
         'None'],
        ['Redline Acceptance/Rejection', 'IMPLEMENTED',
         'app/domains/review/router.py: PUT /reviews/{id}/redlines/{rl_id} with status transitions',
         'RedlineCard.tsx: accept/reject/modify buttons',
         'None'],
        ['Redline Locator (Section Parser)', 'IMPLEMENTED',
         'app/domains/review/redline_scope.py: section-based locator',
         'N/A (backend only)',
         'None'],
        ['Tracked-Changes DOCX', 'IMPLEMENTED',
         'app/domains/review/router.py: GET /reviews/{id}/versions/{v}/tracked-changes',
         'Export button in ReviewWorkspace',
         'None'],
        ['Bulk Redline Operations', 'IMPLEMENTED',
         'app/domains/review/router.py: POST /reviews/bulk-auto-accept, POST /reviews/bulk-reject',
         'N/A (no frontend bulk UI)',
         'No frontend bulk redline operations'],
    ]
)

doc.add_heading('3.7 Benchmark Analysis', level=2)
add_colored_table(doc,
    ['Feature', 'Status', 'Backend Evidence', 'Frontend Evidence', 'Missing Pieces'],
    [
        ['Market Benchmark Scoring', 'NOT IMPLEMENTED',
         'No dedicated benchmark domain in backend/app/domains/',
         'BenchmarkPage.tsx, BenchmarkCharts.tsx (full mock data)',
         'No backend benchmark engine. Legacy api.ts references /benchmarks/score but no router exists.'],
        ['Benchmark Corpus', 'NOT IMPLEMENTED',
         'No corpus storage or benchmark database tables found',
         'BenchmarkPage.tsx shows "Not Loaded"',
         'No corpus ingestion, no comparison engine, no percentile scoring.'],
    ]
)

doc.add_heading('3.8 Contract Relationship Mapping', level=2)
add_colored_table(doc,
    ['Feature', 'Status', 'Backend Evidence', 'Frontend Evidence', 'Missing Pieces'],
    [
        ['Contract Relationship Graph', 'PARTIAL',
         'infra/schema.sql: contract_relationships table with parent/child/amendment/addendum/dpa types. No backend API router for relationships found.',
         'RelationshipGraph.tsx (447 lines, uses D3.js, calls legacy api.ts)',
         'No backend API endpoints for CRUD on relationships. Schema exists but no service/router.'],
    ]
)

doc.add_heading('3.9 Semantic Search', level=2)
add_colored_table(doc,
    ['Feature', 'Status', 'Backend Evidence', 'Frontend Evidence', 'Missing Pieces'],
    [
        ['Hybrid Search (Vector + Keyword)', 'IMPLEMENTED',
         'app/domains/search/router.py: POST /search, service.py: 415 lines, pgvector integration',
         'SearchHub.tsx, SearchResultsPanel.tsx, SearchFiltersPanel.tsx',
         'None'],
        ['Semantic Caching', 'IMPLEMENTED',
         'app/domains/search/models.py: SearchResultCache with query embedding',
         'N/A (backend only)',
         'None'],
        ['Click Tracking / Ranking', 'IMPLEMENTED',
         'app/domains/search/router.py: POST /search/click, models.py: SearchClick',
         'N/A (backend only)',
         'None'],
        ['Query Analytics', 'IMPLEMENTED',
         'app/domains/search/router.py: GET /search/popular, GET /search/zero-result',
         'N/A (backend only)',
         'None'],
        ['Portfolio Intelligence (Search Pulse)', 'IMPLEMENTED',
         'app/domains/search/router.py: GET /search/pulse',
         'SearchHub.tsx calls on load',
         'None'],
    ]
)

doc.add_heading('3.10 Dashboard & Reporting', level=2)
add_colored_table(doc,
    ['Feature', 'Status', 'Backend Evidence', 'Frontend Evidence', 'Missing Pieces'],
    [
        ['Executive Dashboard', 'IMPLEMENTED',
         'app/domains/analytics/router.py: GET /analytics/executive-summary, GET /analytics/metrics-summary',
         'ExecutiveDashboard.tsx (uses useReviewDashboard hook)',
         'None'],
        ['Analytics Center', 'IMPLEMENTED',
         'app/domains/analytics/router.py: 11 endpoints (errors, stuck workflows, health, metrics, uploads, risk, findings, cost, aging)',
         'AnalyticsCenter.tsx, ExecutiveInsights.tsx, SimpleCharts.tsx',
         'None'],
        ['Portfolio Dashboard', 'PARTIAL',
         'Legacy api.ts calls /contracts/ endpoint (no contracts router in current domains)',
         'PortfolioDashboard.tsx (uses legacy api.ts)',
         'Uses legacy API layer. No modern contracts router.'],
        ['Report Export (PDF/DOCX)', 'IMPLEMENTED',
         'app/domains/exports/router.py: GET /exports/reviews/{id}/report, GET /exports/audit-report',
         'Export button in ReviewWorkspace',
         'None'],
    ]
)

doc.add_heading('3.11 Continuous Monitoring', level=2)
add_colored_table(doc,
    ['Feature', 'Status', 'Backend Evidence', 'Frontend Evidence', 'Missing Pieces'],
    [
        ['SLA Monitoring', 'IMPLEMENTED',
         'app/workers/sla_check.py: check_sla_overdue task (Celery Beat every 5 min)',
         'Review aging analytics in AnalyticsCenter',
         'None'],
        ['Stuck Workflow Recovery', 'IMPLEMENTED',
         'app/workers/recovery.py: recover_stuck_workflows task (Celery Beat every 5 min)',
         'N/A (backend only)',
         'None'],
        ['System Metrics Aggregation', 'IMPLEMENTED',
         'workers/celery_app.py: aggregate_system_metrics task (Celery Beat every 15 min)',
         'N/A (backend only)',
         'None'],
        ['Real-time Event Streaming', 'IMPLEMENTED',
         'app/kernel/events/router.py: WebSocket /api/v1/ws/events',
         'N/A (no frontend WebSocket consumer)',
         'No frontend WebSocket client connected'],
    ]
)

doc.add_heading('3.12 Workflow / Review Queue', level=2)
add_colored_table(doc,
    ['Feature', 'Status', 'Backend Evidence', 'Frontend Evidence', 'Missing Pieces'],
    [
        ['Review Lifecycle (19 states)', 'IMPLEMENTED',
         'app/domains/review/models.py: ContractReview with 19-state status machine',
         'ReviewStatusBadge.tsx, status polling',
         'None'],
        ['Review Queue with Filters', 'IMPLEMENTED',
         'app/domains/review/router.py: GET /reviews/ with filtering/pagination',
         'ReviewQueue.tsx: My Reviews, Legal, Executive, Compliance, Overdue tabs',
         'None'],
        ['Assignment & Escalation', 'IMPLEMENTED',
         'app/domains/review/router.py: POST /reviews/{id}/assign, POST /reviews/{id}/escalate',
         'AssignDialog.tsx, EscalationDialog.tsx',
         'None'],
        ['Approval Workflow', 'IMPLEMENTED',
         'app/domains/review/router.py: POST /reviews/{id}/approve (approve/reject/conditional), POST /reviews/{id}/finalize',
         'ApproveDialog.tsx',
         'None'],
        ['Bulk Operations', 'IMPLEMENTED',
         'app/domains/review/router.py: bulk assign, escalate, approve, export, auto-accept, reject',
         'No frontend bulk operations UI',
         'No frontend bulk action UI'],
        ['Document Versioning', 'IMPLEMENTED',
         'app/domains/review/router.py: GET/POST /reviews/{id}/versions, version diff, tracked-changes',
         'VersionHistory.tsx',
         'None'],
        ['Comments (Threaded)', 'IMPLEMENTED',
         'app/domains/review/router.py: GET/POST /reviews/{id}/comments',
         'CommentThread.tsx, CommentList.tsx',
         'None'],
    ]
)

doc.add_heading('3.13 Audit Trail', level=2)
add_colored_table(doc,
    ['Feature', 'Status', 'Backend Evidence', 'Frontend Evidence', 'Missing Pieces'],
    [
        ['Audit Event Logging', 'IMPLEMENTED',
         'app/domains/audit/router.py: GET /audit/events, GET /audit/summary. infra/schema.sql: audit_logs table (monthly partitioned)',
         'N/A (no frontend audit viewer)',
         'No frontend audit log viewer screen'],
        ['Immutable Status History', 'IMPLEMENTED',
         'app/domains/review/models.py: ReviewStatusHistory (immutable transition log)',
         'ActivityHistory.tsx in ReviewWorkspace',
         'None'],
        ['Security Event Logging', 'IMPLEMENTED',
         'app/kernel/middleware/auth_context.py: structured security events for SIEM',
         'N/A (backend only)',
         'None'],
    ]
)

doc.add_heading('3.14 Notifications', level=2)
add_colored_table(doc,
    ['Feature', 'Status', 'Backend Evidence', 'Frontend Evidence', 'Missing Pieces'],
    [
        ['Notification System', 'IMPLEMENTED',
         'app/domains/notify/router.py: list, unread count, mark read, mark all read',
         'NotificationCenter.tsx, NotificationBell in TopNav',
         'None'],
        ['Notification Preferences', 'IMPLEMENTED',
         'app/domains/notify/router.py: GET/PUT /notifications/preferences',
         'N/A (no preferences UI)',
         'No frontend notification preferences screen'],
        ['SLA Policies & Escalation Rules', 'IMPLEMENTED',
         'app/domains/notify/router.py: CRUD for SLA policies and escalation rules',
         'N/A (no frontend SLA management UI)',
         'No frontend SLA/escalation rule management'],
        ['Email Notifications', 'PARTIAL',
         'SMTP config in config.py, notification models support email channel',
         'N/A',
         'SMTP configured but no email delivery service implementation verified'],
    ]
)

doc.add_heading('3.15 Procurement Dashboards', level=2)
add_colored_table(doc,
    ['Feature', 'Status', 'Backend Evidence', 'Frontend Evidence', 'Missing Pieces'],
    [
        ['Procurement View', 'NOT IMPLEMENTED',
         'No procurement-specific backend domain',
         'ProcurementView.tsx (component exists in dashboard/)',
         'Component exists but not wired in DashboardLayout. No backend support.'],
        ['CFO View', 'NOT IMPLEMENTED',
         'No CFO-specific backend domain',
         'CfoView.tsx (component exists in dashboard/)',
         'Component exists but not wired in DashboardLayout. No backend support.'],
        ['Legal View', 'NOT IMPLEMENTED',
         'No legal-specific backend domain beyond review',
         'LegalView.tsx (component exists in dashboard/)',
         'Component exists but not wired in DashboardLayout.'],
    ]
)

doc.add_heading('3.16 Batch Processing', level=2)
add_colored_table(doc,
    ['Feature', 'Status', 'Backend Evidence', 'Frontend Evidence', 'Missing Pieces'],
    [
        ['Batch Upload', 'PARTIAL',
         'Legacy api.ts references /ingest/batch-upload. No current router endpoint found.',
         'IngestionSourcesPanel.tsx has BulkImportButton (no-op)',
         'No current batch upload endpoint in modern router'],
        ['Bulk Review Operations', 'IMPLEMENTED',
         'app/domains/review/router.py: bulk assign, escalate, approve, export endpoints',
         'No frontend bulk operations UI',
         'Backend supports bulk ops, frontend has no bulk UI'],
    ]
)

doc.add_heading('3.17 Tenant Isolation', level=2)
add_colored_table(doc,
    ['Feature', 'Status', 'Backend Evidence', 'Frontend Evidence', 'Missing Pieces'],
    [
        ['RLS Tenant Isolation', 'IMPLEMENTED',
         'infra/schema.sql: RLS policies on all tables via app.tenant_id session variable',
         'All API calls include tenant context',
         'None'],
        ['Tenant Settings', 'IMPLEMENTED',
         'app/domains/admin/router.py: GET/PUT /admin/tenant-settings (branding, AI config, risk thresholds, SLA, features)',
         'AdminConsole.tsx calls tenant settings',
         'None'],
        ['Tenant Provisioning', 'PARTIAL',
         'app/domains/tenants/models.py: minimal Tenant model. No provisioning API.',
         'N/A',
         'No self-service tenant provisioning. Manual DB insert required.'],
    ]
)

doc.add_heading('3.18 AI Explainability Layer', level=2)
add_colored_table(doc,
    ['Feature', 'Status', 'Backend Evidence', 'Frontend Evidence', 'Missing Pieces'],
    [
        ['Risk Flag Explainability', 'PARTIAL',
         'Legacy api.ts types include 8 explainability fields (why_flagged, potential_business_impact, linked_evidence, jurisdictional_considerations). Modern ai/models.py AiFinding has recommendation, confidence, risk_score.',
         'No dedicated explainability panel',
         'No frontend explainability UI. Backend schema supports it but not fully wired.'],
    ]
)

doc.add_heading('3.19 Cost Governance', level=2)
add_colored_table(doc,
    ['Feature', 'Status', 'Backend Evidence', 'Frontend Evidence', 'Missing Pieces'],
    [
        ['AI Cost Tracking', 'IMPLEMENTED',
         'app/domains/ai/models.py: AiExecutionRun has cost_usd, token counts. app/kernel/telemetry/metrics.py: ai_cost_usd_total counter.',
         'AnalyticsCenter shows AI cost trends',
         'None'],
        ['Cost Analytics', 'IMPLEMENTED',
         'app/domains/analytics/router.py: GET /analytics/ai-cost-trend',
         'AnalyticsCenter cost charts',
         'None'],
        ['Cost Budgets / Alerts', 'NOT IMPLEMENTED',
         'No budget or spending limit features found',
         'N/A',
         'No spending caps, budget alerts, or cost governance policies'],
    ]
)

doc.add_heading('3.20 Admin Settings', level=2)
add_colored_table(doc,
    ['Feature', 'Status', 'Backend Evidence', 'Frontend Evidence', 'Missing Pieces'],
    [
        ['User Management', 'IMPLEMENTED',
         'app/domains/admin/router.py: CRUD users, invite, list',
         'AdminConsole.tsx: user list, role management',
         'None'],
        ['Role Management', 'IMPLEMENTED',
         'app/domains/admin/router.py: CRUD roles, custom role creation',
         'AdminConsole.tsx: role management',
         'None'],
        ['Tenant Settings', 'IMPLEMENTED',
         'app/domains/admin/router.py: GET/PUT tenant settings (branding, AI, risk thresholds, SLA, features)',
         'AdminConsole.tsx',
         'None'],
        ['System Health', 'IMPLEMENTED',
         'app/domains/admin/router.py: GET /admin/system-health',
         'AdminConsole.tsx',
         'None'],
    ]
)

doc.add_heading('3.21 Playbook Management', level=2)
add_colored_table(doc,
    ['Feature', 'Status', 'Backend Evidence', 'Frontend Evidence', 'Missing Pieces'],
    [
        ['Playbook CRUD', 'IMPLEMENTED',
         'app/domains/playbook/router.py: 783-line router, full CRUD with versioning',
         'N/A (no frontend playbook management UI)',
         'No frontend playbook management screen'],
        ['Clause Standards Library', 'IMPLEMENTED',
         'app/domains/playbook/router.py: CRUD clause standards (20 categories, 5 clause types)',
         'N/A',
         'No frontend clause library UI'],
        ['Policy Rule Engine', 'IMPLEMENTED',
         'app/domains/playbook/router.py: CRUD policy rules (conditional engine with operators)',
         'N/A',
         'No frontend policy rule editor'],
        ['Policy Evaluation', 'IMPLEMENTED',
         'app/domains/playbook/router.py: POST /playbooks/{id}/evaluate, GET evaluations',
         'N/A',
         'No frontend policy evaluation UI'],
        ['Override Workflow', 'IMPLEMENTED',
         'app/domains/playbook/router.py: request/review override, governance audit trail',
         'N/A',
         'No frontend override request UI'],
        ['AI Context Injection', 'IMPLEMENTED',
         'app/domains/playbook/router.py: POST /playbooks/inject-context',
         'N/A',
         'No frontend integration'],
    ]
)

doc.add_heading('3.22 API / Webhooks', level=2)
add_colored_table(doc,
    ['Feature', 'Status', 'Backend Evidence', 'Frontend Evidence', 'Missing Pieces'],
    [
        ['REST API', 'IMPLEMENTED',
         'Full FastAPI app with 16 domain routers, OpenAPI docs at /docs, /redoc',
         'services/api/client.ts: 897-line API client',
         'None'],
        ['Webhook Subscriptions', 'IMPLEMENTED',
         'app/integration/routers/webhooks.py: CRUD webhook subscriptions, event delivery',
         'N/A',
         'Integration router NOT registered in main.py. Webhook endpoints exist but not accessible.'],
        ['WebSocket Events', 'IMPLEMENTED',
         'app/kernel/events/router.py: WebSocket /api/v1/ws/events',
         'No frontend WebSocket consumer',
         'No frontend real-time event consumer'],
        ['API Key Auth for M2M', 'NOT IMPLEMENTED',
         'No API key model or validation found',
         'N/A',
         'No machine-to-machine authentication'],
    ]
)

doc.add_heading('3.23 Observability & Monitoring', level=2)
add_colored_table(doc,
    ['Feature', 'Status', 'Backend Evidence', 'Frontend Evidence', 'Missing Pieces'],
    [
        ['Prometheus Metrics', 'IMPLEMENTED',
         'app/kernel/telemetry/metrics.py: 50+ metric instruments across HTTP, ingestion, AI, search, reviews, queues, DB pool. /metrics endpoint.',
         'N/A (infrastructure)',
         'None'],
        ['OpenTelemetry Tracing', 'IMPLEMENTED',
         'app/kernel/telemetry/tracer.py: OTLP export, FastAPI + SQLAlchemy instrumentation',
         'N/A (infrastructure)',
         'None'],
        ['Sentry Error Tracking', 'IMPLEMENTED',
         'app/main.py: Sentry SDK init with configurable DSN',
         'N/A (infrastructure)',
         'None'],
        ['Structured Logging', 'IMPLEMENTED',
         'app/kernel/telemetry/logger.py: structlog setup, request ID middleware',
         'N/A (infrastructure)',
         'None'],
        ['Health / Readiness Probes', 'IMPLEMENTED',
         'app/domains/health/router.py: /health, /ready endpoints with pool stats',
         'N/A (infrastructure)',
         'None'],
    ]
)

doc.add_heading('3.24 Infrastructure & Async Processing', level=2)
add_colored_table(doc,
    ['Feature', 'Status', 'Backend Evidence', 'Frontend Evidence', 'Missing Pieces'],
    [
        ['Celery Task Queue', 'IMPLEMENTED',
         'workers/celery_app.py: 5 queues (ingestion, ai, notifications, playbook, default), 9 worker modules',
         'N/A (infrastructure)',
         'None'],
        ['Celery Beat Scheduler', 'IMPLEMENTED',
         'workers/celery_app.py: 4 scheduled tasks (recovery, SLA, metrics, cleanup)',
         'N/A (infrastructure)',
         'None'],
        ['Docker Compose', 'IMPLEMENTED',
         'docker-compose.yml: 6 services (postgres, redis, minio, backend, worker, frontend)',
         'N/A (infrastructure)',
         'None'],
        ['Database Migrations (Alembic)', 'IMPLEMENTED',
         'backend/alembic/ directory, alembic.ini configured',
         'N/A (infrastructure)',
         'None'],
        ['Database Connection Pooling', 'IMPLEMENTED',
         'app/kernel/database/session.py: configurable pool, timeout protections, slow query tracking',
         'N/A (infrastructure)',
         'None'],
        ['Worker Recovery Daemon', 'IMPLEMENTED',
         'app/workers/recovery.py: 454-line recovery module for stuck workflows',
         'N/A (infrastructure)',
         'None'],
    ]
)

doc.add_page_break()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4: CRITICAL MISSING FEATURES
# ══════════════════════════════════════════════════════════════════════════════
doc.add_heading('4. Critical Missing Features', level=1)

doc.add_heading('4.1 CRITICAL Gaps', level=2)

add_status_box(doc, 'Integration Router Not Registered — The entire integration subsystem (connectors, webhooks, sync, OAuth) exists in app/integration/ but is NOT registered in main.py. SharePoint, Google Drive, DocuSign, Salesforce, SAP Ariba connectors are dead code.', 'CRITICAL')

add_status_box(doc, 'Benchmark Analysis Engine — No backend benchmark domain exists. The frontend benchmark pages use 100% mock data. No corpus storage, no comparison engine, no percentile scoring.', 'CRITICAL')

add_status_box(doc, 'Batch Upload — No current batch upload endpoint in modern routers. Legacy api.ts references /ingest/batch-upload but no matching router exists. Frontend BulkImportButton is a no-op.', 'CRITICAL')

add_status_box(doc, 'No Frontend WebSocket Consumer — Real-time event streaming (WebSocket /api/v1/ws/events) exists on backend but no frontend component connects to it. Users must refresh to see updates.', 'CRITICAL')

add_status_box(doc, 'No Frontend Playbook Management UI — Full playbook/policy engine backend exists (783-line router, 496-line service, Celery workers) but no frontend screens for playbook CRUD, clause library, policy rules, or evaluations.', 'CRITICAL')

add_status_box(doc, 'No Frontend Bulk Operations UI — Backend supports bulk assign, escalate, approve, auto-accept, reject. No frontend bulk action UI exists.', 'CRITICAL')

doc.add_heading('4.2 IMPORTANT Gaps', level=2)

add_status_box(doc, 'No Frontend Audit Log Viewer — Audit event logging backend is fully implemented (partitioned tables, query endpoints) but no frontend screen exists to view audit logs.', 'HIGH')

add_status_box(doc, 'No Frontend Notification Preferences — Backend supports notification preferences CRUD but no frontend preferences screen.', 'HIGH')

add_status_box(doc, 'No Frontend SLA/ Escalation Rule Management — Backend supports SLA policies and escalation rules CRUD but no frontend management UI.', 'HIGH')

add_status_box(doc, 'No Frontend AI Explainability Panel — Backend AI findings include recommendation, confidence, risk_score but no dedicated explainability UI. Legacy types support 8 explainability fields.', 'HIGH')

add_status_box(doc, 'Contract Relationship Graph — Database schema exists (contract_relationships table) but no backend API router. Frontend D3.js graph exists but uses legacy API calls that may not work.', 'HIGH')

add_status_box(doc, 'No API Key / M2M Authentication — No API key model or validation. External system integration requires API key auth.', 'HIGH')

add_status_box(doc, 'AI Copilot is Mock Only — Floating chat panel exists but all responses are hardcoded. No real LLM backend endpoint for conversational AI.', 'HIGH')

add_status_box(doc, 'No Email Delivery Service — SMTP is configured but no email sending service implementation verified. Notification models support email channel.', 'HIGH')

doc.add_heading('4.3 NICE-TO-HAVE Gaps', level=2)

add_status_box(doc, 'Procurement / CFO / Legal Dashboards — Components exist but are not wired into the main navigation. No dedicated backend endpoints.', 'MEDIUM')

add_status_box(doc, 'Cost Governance Budgets — AI cost tracking exists but no spending caps, budget alerts, or cost governance policies.', 'MEDIUM')

add_status_box(doc, 'Tenant Self-Service Provisioning — No tenant registration/signup flow. Manual DB insert required.', 'MEDIUM')

add_status_box(doc, 'Source Connector UI Integration — Connector backend code exists but not registered. Frontend buttons are no-ops.', 'MEDIUM')

add_status_box(doc, 'Ingestion Analytics / Duplicate Detection UI — Backend supports it but frontend shows empty arrays.', 'LOW')

doc.add_page_break()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5: PRODUCTION RISKS
# ══════════════════════════════════════════════════════════════════════════════
doc.add_heading('5. Production Risks', level=1)

risks = [
    ['Celery Worker Tasks Use Sync Sessions', 'HIGH',
     'workers/ingestion_tasks.py uses synchronous SQLAlchemy sessions while the main app uses async. The sync session factory creates separate connection pools, risking connection leaks.',
     'Convert workers to use async sessions or ensure sync session cleanup is robust.'],
    ['OpenAI API Key Required for Core Pipeline', 'HIGH',
     'Ingestion pipeline (chunking, embeddings), AI analysis, and search all require OPENAI_API_KEY. Without it, the entire AI pipeline is non-functional.',
     'Add graceful degradation, local embedding fallback, or clear configuration documentation.'],
    ['Integration Router is Dead Code', 'CRITICAL',
     '~3,000+ lines of connector/webhook/sync code in app/integration/ is never registered in main.py. This represents significant untested, unexposed functionality.',
     'Register integration_router in main.py or remove dead code.'],
    ['No Rate Limiting on API Endpoints', 'MEDIUM',
     'Ingestion has per-tenant rate limiting, but general API endpoints have no rate limiting middleware.',
     'Add rate limiting middleware (e.g., slowapi) for production deployment.'],
    ['Dev Auth Bypass in Production Risk', 'MEDIUM',
     'Dev JWT secret is hardcoded in config.py (dev-secret-change-in-production). If deployed with default, anyone can forge admin tokens.',
     'Add startup check that fails if dev_jwt_secret is default in production mode.'],
    ['Single Next.js Route', 'LOW',
     'Entire app is a single SPA under /. No code splitting by route. All ~195 components load on initial page load.',
     'Implement proper Next.js App Router pages for code splitting.'],
    ['No Frontend Error Boundary Strategy', 'MEDIUM',
     'ErrorBoundary.tsx exists but only wraps the root. Individual feature areas lack granular error boundaries.',
     'Add error boundaries per view (ingestion, review, search, analytics).'],
    ['WebSocket Without Frontend Consumer', 'MEDIUM',
     'Backend WebSocket streams real-time events but no frontend connects. Users must poll or refresh.',
     'Implement frontend WebSocket client for real-time updates.'],
    ['No Data Retention / PII Compliance', 'MEDIUM',
     'No document retention policies, data purge mechanisms, or PII redaction found.',
     'Implement data retention, purge workflows, and PII detection/redaction for GDPR/CCPA compliance.'],
    ['No Backup / Disaster Recovery', 'MEDIUM',
     'No backup scripts, point-in-time recovery, or replication configuration found.',
     'Add pg_dump scripts, WAL archiving, and recovery procedures.'],
]

add_colored_table(doc,
    ['Risk', 'Severity', 'Description', 'Recommendation'],
    risks
)

doc.add_page_break()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6: RECOMMENDED NEXT 10 SPRINTS
# ══════════════════════════════════════════════════════════════════════════════
doc.add_heading('6. Recommended Next 10 Sprints', level=1)

sprints = [
    ['Sprint 1', 'Integration Router Activation',
     'CRITICAL',
     'Register integration_router in main.py. Test all connector/webhook/sync endpoints. Build frontend OAuth connection UI for Google Drive, SharePoint connectors.'],
    ['Sprint 2', 'Benchmark Analysis Engine',
     'CRITICAL',
     'Build benchmark domain: corpus storage, comparison engine, percentile scoring, market benchmark API. Connect frontend BenchmarkPage to real data.'],
    ['Sprint 3', 'Playbook Management UI',
     'CRITICAL',
     'Build frontend screens: playbook CRUD, clause standards library, policy rule editor with visual condition builder, evaluation results viewer, override request workflow.'],
    ['Sprint 4', 'Bulk Operations & Batch Upload',
     'CRITICAL',
     'Implement batch upload endpoint. Build frontend bulk action UI: multi-select reviews, bulk assign/escalate/approve, bulk auto-accept redlines, bulk CSV export.'],
    ['Sprint 5', 'Real-Time Events & Notifications',
     'HIGH',
     'Build frontend WebSocket consumer for live updates. Implement notification preferences UI. Build SLA policy and escalation rule management screens. Add email delivery service.'],
    ['Sprint 6', 'Audit Log Viewer & AI Explainability',
     'HIGH',
     'Build audit log viewer screen with filters, timeline, export. Build AI explainability panel: why-flagged, business impact, linked evidence, confidence breakdown, jurisdictional considerations.'],
    ['Sprint 7', 'Contract Relationship Graph',
     'HIGH',
     'Build backend API for contract_relationships CRUD. Connect frontend D3.js graph to real data. Add relationship management UI. Implement risk exposure propagation across related contracts.'],
    ['Sprint 8', 'API Gateway & M2M Auth',
     'HIGH',
     'Implement API key authentication for machine-to-machine access. Add rate limiting middleware. Build webhook delivery dashboard with retry/status monitoring. Add frontend API keys management screen.'],
    ['Sprint 9', 'Production Hardening',
     'MEDIUM',
     'Implement data retention policies. Add PII detection/redaction. Configure backup/DR procedures. Add startup security validation. Implement proper Next.js route splitting. Add granular error boundaries.'],
    ['Sprint 10', 'Advanced Dashboards & Cost Governance',
     'MEDIUM',
     'Build Procurement/CFO/Legal dashboards with dedicated backend endpoints. Implement AI cost budgets and alerts. Build tenant self-service provisioning. Add ingestion analytics and duplicate resolution UI.'],
]

add_colored_table(doc,
    ['Sprint', 'Focus Area', 'Priority', 'Key Deliverables'],
    sprints
)

# ══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════════════════════
doc.add_paragraph()
doc.add_paragraph()
footer = doc.add_paragraph()
footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = footer.add_run('— End of Audit Report —')
run.font.size = Pt(10)
run.font.color.rgb = RGBColor(0x9C, 0xA3, 0xAF)
run.italic = True

# ── Save ─────────────────────────────────────────────────────────────────────
output_path = '/Volumes/home/ContractRiskEdge/output/qa_audit_report.docx'
doc.save(output_path)
print(f'✅ Audit report saved to: {output_path}')
