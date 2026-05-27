#!/usr/bin/env python3
"""Generate the FULL ENTERPRISE ARCHITECTURE + PRODUCT MATURITY AUDIT for ContractEdge as a Word document."""

from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import datetime

doc = Document()

# ── Style Configuration ─────────────────────────────────────────────
style = doc.styles['Normal']
font = style.font
font.name = 'Calibri'
font.size = Pt(10.5)
style.paragraph_format.space_after = Pt(4)
style.paragraph_format.space_before = Pt(2)

# Heading styles
for level in range(1, 5):
    hs = doc.styles[f'Heading {level}']
    hs.font.name = 'Calibri'
    hs.font.color.rgb = RGBColor(15, 23, 42)

def add_colored_heading(text, level=1, color=None):
    h = doc.add_heading(text, level=level)
    if color:
        for run in h.runs:
            run.font.color.rgb = color
    return h

def add_score_row(table, label, score, color):
    row = table.add_row()
    row.cells[0].text = label
    row.cells[1].text = str(score) + '/10'
    # Color the score cell
    shading = OxmlElement('w:shd')
    shading.set(qn('w:fill'), color)
    shading.set(qn('w:val'), 'clear')
    row.cells[1]._tc.get_or_add_tcPr().append(shading)
    for paragraph in row.cells[1].paragraphs:
        for run in paragraph.runs:
            run.font.bold = True
            run.font.size = Pt(12)
    return row

def add_rating_bar(score):
    """Return a visual rating string."""
    filled = '█' * score
    empty = '░' * (10 - score)
    return f"{filled}{empty}"

def add_severity_tag(text, level):
    """Add a colored severity paragraph."""
    p = doc.add_paragraph()
    run = p.add_run(f"[{text}]")
    run.bold = True
    if level == 'critical':
        run.font.color.rgb = RGBColor(220, 38, 38)
    elif level == 'high':
        run.font.color.rgb = RGBColor(234, 88, 12)
    elif level == 'medium':
        run.font.color.rgb = RGBColor(202, 138, 4)
    elif level == 'low':
        run.font.color.rgb = RGBColor(22, 163, 74)
    elif level == 'positive':
        run.font.color.rgb = RGBColor(2, 132, 199)
    return p

def add_bullet(text, bold_prefix=None):
    p = doc.add_paragraph(style='List Bullet')
    if bold_prefix:
        run = p.add_run(bold_prefix)
        run.bold = True
        p.add_run(text)
    else:
        p.add_run(text)
    return p

def add_table(headers, rows):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = 'Light Grid Accent 1'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        table.rows[0].cells[i].text = h
    for row_data in rows:
        row = table.add_row()
        for i, cell_data in enumerate(row_data):
            row.cells[i].text = str(cell_data)
    return table

# ═══════════════════════════════════════════════════════════════════
# TITLE PAGE
# ═══════════════════════════════════════════════════════════════════

doc.add_paragraph()
doc.add_paragraph()
title = doc.add_heading('ContractEdge Platform', level=0)
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
for run in title.runs:
    run.font.size = Pt(28)
    run.font.color.rgb = RGBColor(15, 23, 42)

subtitle = doc.add_heading('Enterprise Architecture & Product Maturity Audit', level=1)
subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
for run in subtitle.runs:
    run.font.size = Pt(18)
    run.font.color.rgb = RGBColor(100, 116, 139)

doc.add_paragraph()

meta = doc.add_paragraph()
meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
meta.add_run('Audit Classification: ').bold = True
meta.add_run('Confidential — Principal Architect Review\n')

meta.add_run('Date: ').bold = True
meta.add_run(f'{datetime.date.today().strftime("%B %d, %Y")}\n')

meta.add_run('Scope: ').bold = True
meta.add_run('Full Platform Architecture, AI Governance, Product UX, Commercial Viability\n')

meta.add_run('Reviewer Role: ').bold = True
meta.add_run('Principal Enterprise Architect / Staff Platform Engineer / AI Governance Auditor')

doc.add_paragraph()
doc.add_paragraph()

disclaimer = doc.add_paragraph()
disclaimer.add_run('DISCLAIMER: ').bold = True
disclaimer.add_run('This audit is conducted as an independent architectural review. '
    'It is not a code review, nor a generic feature suggestion exercise. '
    'Findings are based on deep evaluation of the current codebase, architecture documentation, '
    'and inferred operational characteristics. The intent is to identify risks, gaps, '
    'and opportunities with brutal honesty — no marketing language, no generic advice.')

doc.add_page_break()

# ═══════════════════════════════════════════════════════════════════
# 1. EXECUTIVE ASSESSMENT
# ═══════════════════════════════════════════════════════════════════

add_colored_heading('1. Executive Assessment', level=1, color=RGBColor(15, 23, 42))

doc.add_paragraph()
add_colored_heading('Maturity Scores', level=2)

score_table = doc.add_table(rows=1, cols=3)
score_table.style = 'Light Grid Accent 1'
score_table.alignment = WD_TABLE_ALIGNMENT.CENTER
headers = score_table.rows[0].cells
headers[0].text = 'Dimension'
headers[1].text = 'Score'
headers[2].text = 'Rating'

scores = [
    ('Overall Maturity', '6.5', 'E4C0'),
    ('Enterprise Readiness', '5.5', 'E48C0'),
    ('Operational Maturity', '6.0', 'D4A017'),
    ('AI Governance Maturity', '6.0', 'D4A017'),
    ('Scalability Readiness', '5.0', 'E48C0'),
    ('Commercial Differentiation', '7.0', '228B22'),
]

for label, score, color in scores:
    row = score_table.add_row()
    row.cells[0].text = label
    row.cells[1].text = score
    row.cells[2].text = add_rating_bar(int(float(score)))
    shading = OxmlElement('w:shd')
    shading.set(qn('w:fill'), color)
    shading.set(qn('w:val'), 'clear')
    row.cells[1]._tc.get_or_add_tcPr().append(shading)
    for paragraph in row.cells[1].paragraphs:
        for run in paragraph.runs:
            run.font.bold = True
            run.font.size = Pt(12)

doc.add_paragraph()

add_colored_heading('Biggest Strengths', level=3)
add_bullet('Domain-driven backend architecture with clean separation across 20+ domains, '
    'showing real architectural discipline uncommon at this stage.')
add_bullet('Comprehensive AI governance layer — prompt registry with versioning, evaluation harness, '
    'regression detection, hallucination detection, and confidence calibration. This is ahead of most competitors.')
add_bullet('Event outbox pattern with replay capability, dead-letter queues, and Prometheus observability — '
    'production-grade eventing infrastructure.')
add_bullet('Multi-tenant RBAC with route-level permission validation at startup. This catches '
    'misconfigured endpoints before they reach production.')
add_bullet('Rich dashboard ecosystem spanning executive, reviewer, governance, AI operations, '
    'and workflow intelligence — real attempt at persona-based UX.')
add_bullet('WebSocket infrastructure with exponential backoff, replay cursors, connection ownership guards, '
    'and visibility-API pause/resume. Sophisticated frontend networking.')
add_bullet('Workflow packs system with built-in industry-specific templates (procurement, compliance, etc.) '
    'showing productization thinking.')

add_colored_heading('Biggest Risks', level=3)
add_bullet('Dual-backend architecture (api/ and backend/) is a dangerous anti-pattern. '
    'Two separate FastAPI applications with overlapping domains creates confusion about where logic lives, '
    'duplicated middleware, split routing, and eventual divergence. This is architectural debt that will compound.')
add_bullet('Hallucination detection is entirely rule-based (keyword overlap, sentence splitting). '
    'No LLM-as-judge, no embedding-based semantic verification, no adversarial testing. '
    'This will miss sophisticated hallucinations.')
add_bullet('No SSO/SAML, no SCIM, no LDAP integration. For enterprise procurement, this is a hard blocker. '
    'No Fortune 500 company will adopt without SSO.')
add_bullet('In-memory event bus with no persistence layer for cross-process events. '
    'The outbox persists events but the bus itself is in-memory — crashes lose in-flight events.')
add_bullet('No dedicated API gateway, no service mesh, no rate limiting at the edge. '
    'Single FastAPI instance handles everything — auth, routing, business logic. '
    'This will not scale beyond a few hundred concurrent users.')
add_bullet('Frontend dashboard sprawl is already visible. 7+ dashboard types with overlapping concerns '
    'will create maintenance burden and user confusion.')
add_bullet('No disaster recovery architecture, no multi-region deployment, no regional isolation strategy.')

add_colored_heading('Most Impressive Architectural Decisions', level=3)
add_bullet('Route permission validation at startup — blocks deployment if any route lacks auth. '
    'This is a pattern most enterprise platforms miss.')
add_bullet('Event outbox with versioned schemas (1.0), delivery state machine, and dead-letter queue. '
    'Proper at-least-once delivery semantics.')
add_bullet('Tenant-aware session factory with statement timeouts, lock timeouts, idle transaction '
    'timeouts, and slow query thresholds. Production-grade database governance.')
add_bullet('Cost governance with model-tier routing, budget enforcement, and per-tenant quotas. '
    'This is a genuinely differentiated capability for AI platforms.')
add_bullet('Request coalescing on the frontend — deduplicating in-flight GET requests. '
    'Shows real attention to frontend performance at scale.')

add_colored_heading('Most Dangerous Future Risks', level=3)
add_bullet('The dual-backend split will become a crisis within 6-12 months. '
    'As the codebase grows, developers will inconsistently place logic, creating hard-to-trace bugs.')
add_bullet('Dashboard sprawl without a unified design system or component library. '
    'Each dashboard appears independently built — inconsistency will compound.')
add_bullet('AI governance quality checks are shallow. The hallucination detector uses simple term overlap. '
    'As AI outputs become more sophisticated, these checks will become ineffective.')
add_bullet('No offline or degradation mode. If Redis goes down, the entire platform fails. '
    'If PostgreSQL goes down, everything fails. No graceful degradation strategy.')
add_bullet('Single-region, single-database deployment. No read replicas, no sharding, no CDN strategy '
    'beyond basic CloudFront mention in docs.')

doc.add_page_break()

# ═══════════════════════════════════════════════════════════════════
# 2. ARCHITECTURE AUDIT
# ═══════════════════════════════════════════════════════════════════

add_colored_heading('2. Architecture Audit', level=1, color=RGBColor(15, 23, 42))

arch_sections = [
    {
        'title': 'Domain Separation',
        'rating': '7/10',
        'strengths': [
            'Clean domain-driven structure with 20+ well-named domains in backend/app/domains/',
            'Each domain has consistent structure: router.py, service.py, schemas.py, repository.py',
            'Clear separation between kernel (infrastructure) and domains (business logic)',
            'Workflow packs, human oversight, cost governance — well-bounded domain concepts',
        ],
        'weaknesses': [
            'The api/ directory duplicates many domain concepts from backend/ — unclear boundary',
            'Some domains are thin wrappers over SQL with minimal business logic',
            'Cross-domain dependencies are not explicitly managed or documented',
            'No bounded context map — unclear which domains can reference which others',
        ],
        'risk': 'Medium',
        'recommendations': [
            'Eliminate the api/ backend entirely by migrating its routes into backend/',
            'Document bounded context relationships with explicit dependency rules',
            'Introduce domain events for cross-domain communication instead of direct imports',
        ],
    },
    {
        'title': 'Coupling Risks',
        'rating': '6/10',
        'strengths': [
            'Domains import through service/repository pattern — not directly coupled to DB',
            'Event bus provides loose coupling for cross-domain notifications',
            'Dependency injection via FastAPI Depends() is used consistently',
        ],
        'weaknesses': [
            'Services directly import SQLAlchemy sessions — no repository abstraction layer in many domains',
            'Cross-domain service calls happen synchronously (e.g., review service calling AI service directly)',
            'The api/ and backend/ apps share no common code — duplicated models and utilities',
            'No interface/contract layer between domains — any domain can import any other',
        ],
        'risk': 'High',
        'recommendations': [
            'Introduce formal repository interfaces for all data access',
            'Move to async domain events for cross-domain workflows',
            'Consolidate api/ into backend/ to eliminate the primary coupling risk',
        ],
    },
    {
        'title': 'Event Architecture',
        'rating': '7/10',
        'strengths': [
            'Event outbox pattern with delivery state machine (pending → delivered → acknowledged → failed → dead_letter)',
            'Persistent event storage with replay capability and sequence ordering',
            'Prometheus metrics for all outbox operations — creation, delivery, dead-letter, replay',
            'Event versioning (1.0) for schema evolution',
            'Correlation IDs across event chains',
        ],
        'weaknesses': [
            'In-memory EventBus — crashes lose undelivered events (outbox persists, bus does not)',
            'No event schema registry — event shapes are implicit, not validated',
            'No event sourcing — current state is always authoritative, no audit trail of state changes',
            'No schema evolution strategy beyond version numbers — no compatibility checking',
            'No event retention policy — dead-letter events accumulate indefinitely',
        ],
        'risk': 'Medium',
        'recommendations': [
            'Replace in-memory EventBus with Redis pub/sub or RabbitMQ for process-safe delivery',
            'Implement a schema registry with backward/forward compatibility checks',
            'Define event retention and archival policies per event type',
        ],
    },
    {
        'title': 'Realtime Architecture',
        'rating': '7/10',
        'strengths': [
            'Sophisticated WebSocket client with exponential backoff, heartbeat, replay cursors',
            'Connection ownership guard prevents duplicate connections',
            'Topic-based subscription with fnmatch wildcard patterns',
            'Visibility API pause/resume — respects browser tab lifecycle',
            'Route transition persistence — survives SPA navigation',
            'Prometheus metrics for connections, messages, delivery latency',
        ],
        'weaknesses': [
            'WebSocket server is tied to the FastAPI process — no dedicated WebSocket service',
            'No horizontal scaling for WebSocket connections — sticky sessions required',
            'No fallback to polling when WebSocket fails (e.g., corporate proxies)',
            'No message compression for large payloads',
            'No rate limiting per WebSocket connection — potential abuse vector',
        ],
        'risk': 'Medium',
        'recommendations': [
            'Extract WebSocket into a dedicated service (e.g., using Socket.IO or a Go-based WS gateway)',
            'Implement Redis-backed WebSocket pub/sub for multi-process scaling',
            'Add HTTP long-polling fallback for restrictive network environments',
        ],
    },
    {
        'title': 'Graph Architecture',
        'rating': '5/10',
        'strengths': [
            'Relationship graph exists in both frontend (RelationshipGraph.tsx) and backend (relationship_graph.py)',
            'Knowledge graph concepts present in clause intelligence domain',
        ],
        'weaknesses': [
            'Graph is stored in PostgreSQL using adjacency lists — no dedicated graph database',
            'No graph traversal API — relationships are queried via SQL joins',
            'No graph visualization beyond basic D3 integration',
            'No entity resolution or deduplication across the graph',
            'No temporal graph — relationship history is not tracked',
        ],
        'risk': 'Medium',
        'recommendations': [
            'Evaluate whether a dedicated graph DB (Neo4j, Amazon Neptune) is warranted for production',
            'Implement graph traversal endpoints (shortest path, subgraph extraction)',
            'Add temporal edge tracking for relationship audit trails',
        ],
    },
    {
        'title': 'Governance Architecture',
        'rating': '7/10',
        'strengths': [
            'Multi-tenant RBAC with fine-grained permissions (contracts:read, ai:analyze, etc.)',
            'Route permission validation at startup — blocks deployment of unprotected routes',
            'Prompt registry with versioning, diff tracking, and activation workflow',
            'Evaluation harness with dataset management and regression testing',
            'Human oversight layer with approval workflows, policy exceptions, and decision impact tracking',
        ],
        'weaknesses': [
            'No attribute-based access control (ABAC) — RBAC alone is insufficient for enterprise',
            'No audit trail for permission changes — who granted what to whom and when?',
            'No approval delegation or temporary authority grants',
            'No separation of duties enforcement for sensitive operations',
            'No governance for API key management — keys appear to be long-lived with no rotation policy',
        ],
        'risk': 'High',
        'recommendations': [
            'Implement ABAC for document/field-level access control',
            'Add audit logging for all RBAC changes',
            'Implement approval delegation with temporal boundaries',
        ],
    },
    {
        'title': 'Multi-Tenant Isolation',
        'rating': '6/10',
        'strengths': [
            'TenantContextMiddleware sets tenant_id on every request',
            'TenantAwareSessionFactory provides tenant-scoped database sessions',
            'All queries appear to filter by tenant_id',
            'Tenant isolation tests exist (test_tenant_isolation.py)',
        ],
        'weaknesses': [
            'Single shared database for all tenants — no tenant-per-database or tenant-per-schema',
            'No tenant-level resource quotas beyond what cost governance provides',
            'No tenant-level backup/restore capability',
            'No tenant data deletion workflow (GDPR Article 17 compliance gap)',
            'No tenant-level rate limiting — one noisy tenant can degrade others',
        ],
        'risk': 'High',
        'recommendations': [
            'Implement tenant-per-schema or tenant-per-database for production deployments',
            'Add tenant-level rate limiting and resource quotas',
            'Build tenant data export/deletion workflows for GDPR compliance',
        ],
    },
    {
        'title': 'Scalability Boundaries',
        'rating': '5/10',
        'strengths': [
            'Celery workers for async processing with multiple queues (ingestion, ai, notifications, embeddings)',
            'Redis for caching and queue broker',
            'MinIO/S3 for object storage — horizontally scalable',
        ],
        'weaknesses': [
            'Single PostgreSQL instance is the critical bottleneck — no read replicas, no sharding',
            'FastAPI runs as a single process — no horizontal scaling of the API tier',
            'No connection pooling configuration for high concurrency (pool_size=10 in config)',
            'No CDN for static/frontend assets beyond basic mention',
            'No database read-write splitting — all traffic hits the primary',
        ],
        'risk': 'Critical',
        'recommendations': [
            'Implement PostgreSQL read replicas with read-write splitting in the session factory',
            'Increase connection pool sizing based on expected concurrency',
            'Deploy API behind a load balancer with multiple replicas',
            'Implement CDN for frontend assets and static content',
        ],
    },
    {
        'title': 'Observability Maturity',
        'rating': '6/10',
        'strengths': [
            'Prometheus metrics endpoint with business-level instruments',
            'Structured logging with request IDs and correlation IDs',
            'Sentry integration for error tracking',
            'OpenTelemetry tracing support (disabled by default)',
            'Grafana and Prometheus configured in deploy/observability/',
            'Slow query logging at 500ms threshold',
        ],
        'weaknesses': [
            'OpenTelemetry is disabled by default — tracing is not operational',
            'No distributed tracing across Celery tasks — hard to debug async workflows',
            'No custom dashboards for business KPIs — only infrastructure metrics',
            'No SLO/SLI tracking — no way to measure reliability against targets',
            'No alerting rules defined in the observability stack',
            'No log aggregation beyond console output — no ELK/Loki stack',
        ],
        'risk': 'High',
        'recommendations': [
            'Enable OpenTelemetry by default and instrument all critical paths',
            'Implement distributed tracing across Celery task chains',
            'Define SLOs for critical user journeys and build dashboards',
            'Add Loki or ELK for log aggregation and search',
        ],
    },
    {
        'title': 'Frontend Architecture',
        'rating': '6/10',
        'strengths': [
            'Next.js 14 with SSR — good for SEO and initial load performance',
            'TanStack Query for server state management — proper caching and refetching',
            'Sophisticated API client with request coalescing, retry, timeout, and idempotency',
            'WebSocket client with advanced features (replay, backoff, connection guard)',
            'Adaptive polling hook — reduces server load intelligently',
            'Session governance on frontend',
        ],
        'weaknesses': [
            'No component library or design system — UI appears to be built ad-hoc',
            'No Storybook or component documentation',
            'No end-to-end tests (Cypress/Playwright) — only Jest unit tests',
            'No performance monitoring (Web Vitals, Lighthouse CI)',
            'No error boundary strategy beyond a single ErrorBoundary.tsx',
            'No mobile-responsive design evident in component structure',
            'No accessibility (a11y) audit or compliance strategy',
        ],
        'risk': 'High',
        'recommendations': [
            'Build a shared component library with Storybook documentation',
            'Implement E2E testing with Playwright for critical user journeys',
            'Add Web Vitals monitoring and Lighthouse CI to the build pipeline',
            'Conduct an accessibility audit and establish WCAG 2.1 AA compliance targets',
        ],
    },
    {
        'title': 'API Discipline',
        'rating': '7/10',
        'strengths': [
            'Consistent RESTful API design with /api/v1 prefix',
            'OpenAPI documentation via FastAPI auto-generation',
            'Structured error responses with error codes and request IDs',
            'Idempotency-Key support for mutation endpoints',
            'Route permission validation ensures all endpoints have auth checks',
        ],
        'weaknesses': [
            'No API versioning strategy beyond URL prefix — no content negotiation',
            'No rate limit headers in responses (X-RateLimit-Remaining is exposed but not consistently)',
            'No pagination standards — each endpoint appears to implement pagination independently',
            'No API deprecation policy or sunset headers',
            'No GraphQL or gRPC for complex query scenarios',
            'No API documentation beyond auto-generated Swagger — no developer portal',
        ],
        'risk': 'Medium',
        'recommendations': [
            'Standardize pagination across all list endpoints',
            'Implement API versioning via Accept header or URL prefix with deprecation policy',
            'Build a developer portal with API keys, usage tracking, and interactive docs',
        ],
    },
    {
        'title': 'Dependency Management',
        'rating': '5/10',
        'strengths': [
            'requirements.txt and requirements-dev.txt exist',
            'Docker-based development environment',
        ],
        'weaknesses': [
            'No dependency pinning — requirements use loose version constraints',
            'No automated dependency vulnerability scanning (Dependabot, Snyk)',
            'No SBOM (Software Bill of Materials) generation',
            'No license compliance checking for dependencies',
            'Python version not explicitly pinned in Dockerfiles',
            'No monorepo tooling (Nx, Turborepo) for managing the multi-package workspace',
        ],
        'risk': 'Medium',
        'recommendations': [
            'Pin all dependency versions and automate updates with Dependabot',
            'Add Snyk or Trivy for vulnerability scanning in CI',
            'Generate SBOM as part of the build pipeline',
        ],
    },
]

for section in arch_sections:
    add_colored_heading(section['title'], level=2)
    
    p = doc.add_paragraph()
    p.add_run('Rating: ').bold = True
    p.add_run(section['rating'])
    
    p = doc.add_paragraph()
    p.add_run('Risk Level: ').bold = True
    risk_run = p.add_run(section['risk'])
    if section['risk'] == 'Critical':
        risk_run.font.color.rgb = RGBColor(220, 38, 38)
    elif section['risk'] == 'High':
        risk_run.font.color.rgb = RGBColor(234, 88, 12)
    elif section['risk'] == 'Medium':
        risk_run.font.color.rgb = RGBColor(202, 138, 4)
    risk_run.bold = True
    
    add_colored_heading('Strengths', level=3)
    for s in section['strengths']:
        add_bullet(s)
    
    add_colored_heading('Weaknesses', level=3)
    for w in section['weaknesses']:
        add_bullet(w)
    
    add_colored_heading('Recommendations', level=3)
    for r in section['recommendations']:
        add_bullet(r)
    
    doc.add_paragraph()

doc.add_page_break()

# ═══════════════════════════════════════════════════════════════════
# 3. PRODUCT & UX AUDIT
# ═══════════════════════════════════════════════════════════════════

add_colored_heading('3. Product & UX Audit', level=1, color=RGBColor(15, 23, 42))

add_colored_heading('Dashboard Usability', level=2)
add_bullet('Executive Command Center, AI Operations Dashboard, Governance Dashboard, '
    'Workflow Intelligence Dashboard, Portfolio Dashboard, Procurement Dashboard, '
    'CFO View, Legal View — 8+ distinct dashboard surfaces.')
add_bullet('STRENGTH: Role-based dashboards show persona awareness — different users get different views.')
add_bullet('WEAKNESS: No unified dashboard framework. Each dashboard appears independently built '
    'with different widget patterns, layouts, and interaction models.')
add_bullet('WEAKNESS: Dashboard overload risk — users will not use 8 dashboards. '
    'Enterprise buyers want ONE configurable dashboard, not eight fixed ones.')
add_bullet('RISK: react-grid-layout for drag-and-drop widgets is fragile — '
    'layout state management, persistence, and multi-device sync are non-trivial.')

add_colored_heading('Operational Complexity', level=2)
add_bullet('The reviewer workspace has 15+ components (ActivityTimeline, ApprovalModal, CommentThread, '
    'ContractSummary, DocumentVersionsPanel, EscalationModal, EvidenceViewer, FindingsTable, '
    'GovernanceAnalytics, RedlineCard, RedlineContent, RedlineEditModal, ReviewActions, '
    'ReviewQueue, ReviewWorkspace, RiskBreakdownPanel, VersionDiffViewer).')
add_bullet('WEAKNESS: This is cognitive overload for a reviewer. 15+ UI panels means the reviewer '
    'spends more time managing UI than reviewing contracts.')
add_bullet('WEAKNESS: No guided workflow — the reviewer must know which panel to use and when.')
add_bullet('WEAKNESS: No progressive disclosure — all features are visible at once.')

add_colored_heading('Workflow Clarity', level=2)
add_bullet('Workflow packs concept is strong — predefined workflows for procurement, compliance, etc.')
add_bullet('WEAKNESS: No visual workflow builder — workflows are code-defined, not configurable by power users.')
add_bullet('WEAKNESS: Workflow state is not visible to end users — no "where am I in the process" indicator.')
add_bullet('WEAKNESS: No workflow templates marketplace or sharing mechanism.')

add_colored_heading('Reviewer Experience', level=2)
add_bullet('STRENGTH: Redline comparison with inline diff viewer is a strong feature.')
add_bullet('STRENGTH: Evidence viewer with source clause grounding is enterprise-grade.')
add_bullet('WEAKNESS: The review workspace packs too much information into one screen. '
    'Risk of "dashboard fatigue" where reviewers stop noticing important signals.')
add_bullet('WEAKNESS: No batch review mode — each review is opened individually.')
add_bullet('WEAKNESS: No keyboard shortcuts or power-user optimizations for high-volume reviewers.')

add_colored_heading('Executive Usability', level=2)
add_bullet('STRENGTH: Executive Command Center with widgets for AI quality, cost governance, '
    'SLA risk, tenant health, reviewer load, and anomaly feed.')
add_bullet('WEAKNESS: No natural language query interface — executives must navigate dashboards.')
add_bullet('WEAKNESS: No scheduled report delivery (PDF to email).')
add_bullet('WEAKNESS: No benchmark comparison against industry peers — executives want to know '
    '"how are we doing compared to others?"')

add_colored_heading('Governance Usability', level=2)
add_bullet('STRENGTH: AI governance dashboard provides visibility into prompt versions, '
    'evaluation results, and model audit logs.')
add_bullet('WEAKNESS: Governance workflows require deep platform knowledge — '
    'approval chains, policy exceptions, and escalation paths are not visually mapped.')
add_bullet('WEAKNESS: No governance health score or compliance status at a glance.')

add_colored_heading('AI Explainability Trustworthiness', level=2)
add_bullet('STRENGTH: Evidence chain builder with source clause grounding, policy violations, '
    'benchmark comparisons, precedent evidence, and regulation mapping.')
add_bullet('STRENGTH: Confidence breakdown with component scores — shows WHY the AI is confident.')
add_bullet('WEAKNESS: Explainability is post-hoc — the AI runs first, then explanations are built. '
    'No intrinsic explainability (models that explain as they reason).')
add_bullet('WEAKNESS: No counterfactual explanations — "what would change this finding?"')
add_bullet('WEAKNESS: No confidence calibration visualization — users see a score but not its reliability.')

add_colored_heading('Notification Overload Risk', level=2)
add_bullet('STRENGTH: Real-time WebSocket infrastructure for instant notifications.')
add_bullet('WEAKNESS: No notification preferences — users cannot control what they receive.')
add_bullet('WEAKNESS: No notification grouping or digest mode.')
add_bullet('WEAKNESS: No notification priority levels visible to users.')
add_bullet('RISK: As more governance and monitoring features are added, notification volume will '
    'increase exponentially. Users will either ignore all notifications or disable them entirely.')

add_colored_heading('Cognitive Load Assessment', level=2)
add_bullet('Current state: HIGH. The platform requires users to navigate multiple dashboards, '
    'understand AI confidence scores, manage approval workflows, interpret redlines, '
    'and track obligations — all without guided onboarding.')
add_bullet('No progressive onboarding or contextual help system.')
add_bullet('No "quick start" or "day 1" experience for new users.')
add_bullet('No role-specific training mode or sandbox environment.')

add_colored_heading('Enterprise Adoption Readiness', level=2)
add_bullet('GREEN FLAGS: Multi-tenant, RBAC, audit logging, AI explainability, workflow governance.')
add_bullet('RED FLAGS: No SSO, no SCIM, no bulk user provisioning, no white-labeling, '
    'no brand customization, no localization/i18n beyond basic infrastructure.')
add_bullet('BLOCKER: Without SSO/SAML, enterprise procurement is impossible. '
    'This should be the #1 priority for the next sprint.')

doc.add_page_break()

# ═══════════════════════════════════════════════════════════════════
# 4. AI GOVERNANCE AUDIT
# ═══════════════════════════════════════════════════════════════════

add_colored_heading('4. AI Governance Audit', level=1, color=RGBColor(15, 23, 42))

add_colored_heading('Hallucination Controls', level=2)
add_bullet('Current approach: Rule-based claim extraction + keyword overlap verification.')
add_bullet('WEAKNESS: Keyword overlap is NOT hallucination detection. A sentence can have 100% keyword '
    'overlap and still be semantically wrong. Example: "This clause limits liability to $1M" vs '
    '"This clause limits liability to $1M for intentional breach" — keyword overlap misses the nuance.')
add_bullet('WEAKNESS: No LLM-as-judge evaluation — using a separate LLM to verify outputs is the '
    'current industry best practice and is not implemented.')
add_bullet('WEAKNESS: No embedding-based semantic similarity comparison against source material.')
add_bullet('WEAKNESS: No adversarial testing — the system is not tested against known hallucination patterns.')
add_bullet('WEAKNESS: No human-in-the-loop for hallucination detection — all automated.')

add_colored_heading('Regression Protection', level=2)
add_bullet('STRENGTH: SemanticRegressionTester compares old vs new outputs for finding drift.')
add_bullet('STRENGTH: RegressionDetector in api/ tracks F1 scores week-over-week with alerting.')
add_bullet('WEAKNESS: Regression detection is text-based (keyword extraction) — not semantic.')
add_bullet('WEAKNESS: No automated rollback — regression is detected but not acted upon.')
add_bullet('WEAKNESS: No A/B testing framework for comparing model versions in production.')
add_bullet('WEAKNESS: Regression test sets are static — not updated with real-world edge cases.')

add_colored_heading('Evaluation Harness', level=2)
add_bullet('STRENGTH: EvaluationHarness with dataset management, test case execution, and outcome tracking.')
add_bullet('STRENGTH: Prompt registry with versioning enables reproducible evaluations.')
add_bullet('WEAKNESS: Evaluation datasets appear to be manually created — no automated extraction '
    'from production feedback.')
add_bullet('WEAKNESS: No canary deployment — new prompts go to all users or none.')
add_bullet('WEAKNESS: No evaluation result visualization — hard to spot trends.')
add_bullet('WEAKNESS: No cost-aware evaluation — evaluating every prompt version against every '
    'dataset could become expensive at scale.')

add_colored_heading('Prompt Governance', level=2)
add_bullet('STRENGTH: Prompt registry with versioning, diff tracking, and state machine '
    '(draft → active → deprecated → archived).')
add_bullet('STRENGTH: Schema validation for prompt responses.')
add_bullet('WEAKNESS: No prompt testing sandbox — prompt authors cannot test changes before creating a version.')
add_bullet('WEAKNESS: No prompt performance metrics per version — which version performs best?')
add_bullet('WEAKNESS: No approval workflow for prompt changes — any admin can activate a new version.')
add_bullet('WEAKNESS: No prompt chaining governance — multi-step AI workflows are not tracked.')

add_colored_heading('Deployment Gating', level=2)
add_bullet('WEAKNESS: No formal deployment gate for AI model changes.')
add_bullet('WEAKNESS: No staged rollout (e.g., 10% → 50% → 100% of users).')
add_bullet('WEAKNESS: No automatic rollback triggers based on evaluation metrics.')
add_bullet('WEAKNESS: No shadow deployment — new models cannot run in parallel for comparison.')
add_bullet('WEAKNESS: No model registry — which model version is serving which prompt is not tracked.')

add_colored_heading('Explainability Systems', level=2)
add_bullet('STRENGTH: EvidenceChainBuilder with multiple evidence types — source clauses, '
    'policy violations, benchmarks, precedents, regulations.')
add_bullet('STRENGTH: ConfidenceBreakdown with component scores — transparency into AI reasoning.')
add_bullet('WEAKNESS: Explainability is entirely post-hoc and rule-based — no model introspection.')
add_bullet('WEAKNESS: No interactive explainability — users cannot ask "why not?" or drill deeper.')
add_bullet('WEAKNESS: No explanation confidence — how reliable is the explanation itself?')
add_bullet('WEAKNESS: No visualization of the evidence chain — users see text, not a graph.')

add_colored_heading('Confidence Scoring', level=2)
add_bullet('STRENGTH: Confidence calibration levels defined (very_high through very_low).')
add_bullet('STRENGTH: Cost governance includes model tier routing based on quality scores.')
add_bullet('WEAKNESS: No empirical calibration — confidence scores are heuristic, not statistically calibrated.')
add_bullet('WEAKNESS: No confidence histograms — users cannot see how confidence is distributed.')
add_bullet('WEAKNESS: No selective prediction — the system cannot say "I don\'t know" and abstain.')

add_colored_heading('Benchmark Reliability', level=2)
add_bullet('STRENGTH: Corpus governance with versioning, approval workflows, and deduplication.')
add_bullet('STRENGTH: BenchmarkConfidenceScorer for evaluating benchmark quality.')
add_bullet('WEAKNESS: Benchmark corpus size is unknown — small corpora lead to unreliable metrics.')
add_bullet('WEAKNESS: No benchmark diversity metrics — is the corpus representative of real contracts?')
add_bullet('WEAKNESS: No benchmark contamination detection — are test cases leaking into training data?')

add_colored_heading('Oversight Systems', level=2)
add_bullet('STRENGTH: Human oversight layer with approval workflows, policy exceptions, '
    'decision impact preview, and bulk decision support.')
add_bullet('STRENGTH: Multiple approval types (ai_recommendation, policy_exception, '
    'escalation_review, compliance_check, executive_sign_off).')
add_bullet('WEAKNESS: No mandatory human-in-the-loop for high-risk decisions — '
    'the system can operate fully autonomously.')
add_bullet('WEAKNESS: No oversight SLA tracking — how long do approvals take?')
add_bullet('WEAKNESS: No oversight effectiveness metrics — are humans catching AI mistakes?')
add_bullet('WEAKNESS: No calibration between human and AI decisions — who is more accurate?')

add_colored_heading('Model Routing Governance', level=2)
add_bullet('STRENGTH: ModelRouter with tier-based routing (economy, standard, premium).')
add_bullet('STRENGTH: Cost governance integrates with model routing for budget-aware decisions.')
add_bullet('WEAKNESS: Model catalog is hardcoded — not configurable per tenant.')
add_bullet('WEAKNESS: No model fallback chain — if gpt-4o fails, does it try claude or fail entirely?')
add_bullet('WEAKNESS: No latency-aware routing — fastest model is not considered.')
add_bullet('WEAKNESS: No multi-provider load balancing — all traffic goes to OpenAI by default.')

doc.add_page_break()

# ═══════════════════════════════════════════════════════════════════
# 5. SCALABILITY & RELIABILITY AUDIT
# ═══════════════════════════════════════════════════════════════════

add_colored_heading('5. Scalability & Reliability Audit', level=1, color=RGBColor(15, 23, 42))

scalability_sections = [
    {
        'title': 'Database Growth Risk',
        'rating': '4/10',
        'findings': [
            'Single PostgreSQL instance with pgvector — no read replicas, no sharding, no partitioning strategy',
            'No data archival policy — the event_outbox table grows unboundedly',
            'No connection pooling at the application level beyond basic SQLAlchemy pool',
            'pgvector indexes grow linearly with data — ANN search degrades without proper index maintenance',
            'No database monitoring for bloat, index usage, or query performance trends',
        ],
        'risk': 'Critical',
        'recommendation': 'Implement table partitioning, data archival, read replicas, and pgvector index maintenance before production scale.',
    },
    {
        'title': 'Event Replay Scalability',
        'rating': '5/10',
        'findings': [
            'Event outbox uses a single PostgreSQL table — replay scans the entire table',
            'No event retention policy — old events are never archived or deleted',
            'No event replay rate limiting — a replay request could overwhelm the system',
            'No parallel replay for different event types',
            'WebSocket replay cursor uses localStorage — not server-side cursor management',
        ],
        'risk': 'High',
        'recommendation': 'Implement time-based partitioning, event archival to cold storage, and server-side cursor management.',
    },
    {
        'title': 'Graph Scaling Risk',
        'rating': '4/10',
        'findings': [
            'Knowledge graph stored in PostgreSQL with adjacency lists — O(n) traversal for deep relationships',
            'No graph-specific indexing (no pgvector for graph embeddings, no path indexing)',
            'Graph queries will degrade non-linearly as the number of contracts and relationships grows',
            'No graph partitioning strategy for multi-tenant isolation',
        ],
        'risk': 'High',
        'recommendation': 'Evaluate dedicated graph database or implement materialized path patterns in PostgreSQL.',
    },
    {
        'title': 'WebSocket Scaling',
        'rating': '5/10',
        'findings': [
            'WebSocket server is in-process with FastAPI — single process, no horizontal scaling',
            'No Redis-backed pub/sub for multi-process WebSocket broadcasting',
            'No WebSocket connection limit per IP or per tenant',
            'No message backpressure — a slow consumer can block the event loop',
            'No WebSocket health check or dead connection cleanup beyond basic disconnect handling',
        ],
        'risk': 'High',
        'recommendation': 'Extract WebSocket to a dedicated service with Redis pub/sub for horizontal scaling.',
    },
    {
        'title': 'Queue Scaling',
        'rating': '6/10',
        'findings': [
            'Celery with Redis broker — multiple queues (ingestion, ai, notifications, embeddings)',
            'Concurrency=4 per worker — reasonable for initial deployment',
            'No queue depth monitoring or alerting',
            'No dead letter queue for failed tasks beyond Celery default',
            'No task priority within queues — all tasks are equal',
            'No queue autoscaling — worker count is fixed',
        ],
        'risk': 'Medium',
        'recommendation': 'Implement queue depth monitoring, autoscaling workers, and task priority levels.',
    },
    {
        'title': 'Caching Strategy',
        'rating': '5/10',
        'findings': [
            'Redis used primarily as Celery broker and for rate limiting',
            'No application-level caching strategy — each request hits the database',
            'No CDN for static assets or API responses',
            'No cache invalidation strategy — stale data risk is not addressed',
            'No distributed caching for multi-process deployments',
            'Frontend has request coalescing but no client-side cache beyond TanStack Query defaults',
        ],
        'risk': 'High',
        'recommendation': 'Implement Redis caching for frequent queries, CDN for static assets, and a cache invalidation strategy.',
    },
    {
        'title': 'Multi-Tenant Scaling',
        'rating': '5/10',
        'findings': [
            'Row-level tenant isolation in shared database — no tenant-per-database option',
            'No tenant-level resource quotas enforced at the application layer',
            'No tenant-level rate limiting — one noisy tenant can degrade all others',
            'No tenant onboarding/offboarding workflow in the application',
            'No tenant data isolation certification (SOC 2, HIPAA) evident',
        ],
        'risk': 'High',
        'recommendation': 'Implement tenant-per-schema option, tenant-level rate limiting, and resource quotas.',
    },
    {
        'title': 'Observability Scaling',
        'rating': '5/10',
        'findings': [
            'Prometheus metrics are in-process — no remote write for multi-instance aggregation',
            'No log aggregation — debugging requires SSH access to instances',
            'No distributed tracing — hard to diagnose cross-service latency',
            'No business-level dashboards — only infrastructure metrics',
            'No alerting rules defined — operators must watch dashboards manually',
            'Metrics cardinality is unmanaged — unbounded label values could explode Prometheus',
        ],
        'risk': 'High',
        'recommendation': 'Implement remote write for Prometheus, add Loki/ELK for logs, and define SLO-based alerting.',
    },
]

for section in scalability_sections:
    add_colored_heading(section['title'], level=2)
    
    p = doc.add_paragraph()
    p.add_run('Rating: ').bold = True
    p.add_run(section['rating'])
    
    p = doc.add_paragraph()
    p.add_run('Risk Level: ').bold = True
    risk_run = p.add_run(section['risk'])
    if section['risk'] == 'Critical':
        risk_run.font.color.rgb = RGBColor(220, 38, 38)
    elif section['risk'] == 'High':
        risk_run.font.color.rgb = RGBColor(234, 88, 12)
    risk_run.bold = True
    
    for finding in section['findings']:
        add_bullet(finding)
    
    p = doc.add_paragraph()
    p.add_run('Recommendation: ').bold = True
    p.add_run(section['recommendation'])
    doc.add_paragraph()

doc.add_page_break()

# ═══════════════════════════════════════════════════════════════════
# 6. COMMERCIAL & STRATEGIC AUDIT
# ═══════════════════════════════════════════════════════════════════

add_colored_heading('6. Commercial & Strategic Audit', level=1, color=RGBColor(15, 23, 42))

add_colored_heading('Market Differentiation', level=2)
add_bullet('STRONG DIFFERENTIATOR: AI governance depth — prompt registry, evaluation harness, '
    'hallucination detection, confidence calibration. Most competitors treat AI as a black box.')
add_bullet('STRONG DIFFERENTIATOR: Cost governance with model routing — enterprises care deeply about AI costs.')
add_bullet('STRONG DIFFERENTIATOR: Multi-tenant architecture with tenant-specific configuration.')
add_bullet('STRONG DIFFERENTIATOR: Workflow packs — industry-specific pre-built workflows reduce implementation time.')
add_bullet('WEAKNESS: Core contract analysis (redlining, risk scoring, clause extraction) is table stakes — '
    'Ironclad, Icertis, and DocuSign CLM all do this competently.')

add_colored_heading('Competitive Comparison', level=2)

comp_table = doc.add_table(rows=1, cols=5)
comp_table.style = 'Light Grid Accent 1'
comp_table.alignment = WD_TABLE_ALIGNMENT.CENTER
comp_headers = comp_table.rows[0].cells
comp_headers[0].text = 'Capability'
comp_headers[1].text = 'ContractEdge'
comp_headers[2].text = 'Ironclad'
comp_headers[3].text = 'Icertis'
comp_headers[4].text = 'DocuSign CLM'

competitors = [
    ('AI Governance', 'Strong', 'Weak', 'Weak', 'None'),
    ('Cost Control', 'Strong', 'None', 'None', 'None'),
    ('Multi-Tenant', 'Strong', 'Limited', 'Strong', 'Limited'),
    ('Workflow Builder', 'Code-defined', 'Visual', 'Visual', 'Visual'),
    ('SSO/SAML', 'Missing', 'Built-in', 'Built-in', 'Built-in'),
    ('Contract Repository', 'Good', 'Excellent', 'Excellent', 'Excellent'),
    ('API Ecosystem', 'Developing', 'Mature', 'Mature', 'Mature'),
    ('Marketplace', 'None', 'Growing', 'Growing', 'Extensive'),
    ('Mobile', 'None', 'Available', 'Available', 'Available'),
    ('eDiscovery', 'None', 'Available', 'Available', 'Available'),
    ('CLM Depth', 'Developing', 'Mature', 'Mature', 'Mature'),
    ('AI Explainability', 'Strong', 'None', 'Basic', 'None'),
    ('Open Source', 'No', 'No', 'No', 'No'),
    ('Deployment Options', 'Docker-only', 'SaaS/On-prem', 'SaaS/On-prem', 'SaaS'),
]

for row_data in competitors:
    row = comp_table.add_row()
    for i, cell_data in enumerate(row_data):
        row.cells[i].text = cell_data

doc.add_paragraph()

add_colored_heading('Where ContractEdge Is Stronger', level=3)
add_bullet('AI governance and explainability — significantly ahead of all incumbents.')
add_bullet('Cost governance — unique in the CLM space. Enterprises will value this.')
add_bullet('Multi-tenant architecture — better than most incumbents for platform play.')
add_bullet('Modern tech stack (FastAPI + Next.js 14 + PostgreSQL 16) — easier to extend than legacy Java/.NET stacks.')
add_bullet('Event-driven architecture — more scalable than most competitors\' monolithic designs.')

add_colored_heading('Where ContractEdge Is Weaker', level=3)
add_bullet('SSO/SAML — a hard enterprise blocker that all competitors have solved.')
add_bullet('CLM workflow depth — Ironclad and Icertis have 10+ years of workflow refinement.')
add_bullet('Integration ecosystem — no Salesforce, SAP, Workday, or ServiceNow connectors.')
add_bullet('Mobile — no mobile app in a world where legal teams work from anywhere.')
add_bullet('Brand and trust — incumbents have enterprise certifications (SOC 2, HIPAA, FedRAMP).')
add_bullet('Visual workflow builder — enterprises expect to configure workflows without code.')

add_colored_heading('Where ContractEdge Risks Overengineering', level=3)
add_bullet('Dashboard proliferation — 8+ dashboards when most enterprises need 2-3.')
add_bullet('AI governance may be too sophisticated for the market\'s current maturity level — '
    'most enterprises are still figuring out basic AI usage.')
add_bullet('Workflow packs introduce abstraction overhead that may confuse simple use cases.')
add_bullet('Event outbox with full replay capability may be overkill for the current scale.')

add_colored_heading('Category-Defining Potential', level=3)
add_bullet('ContractEdge has a REAL shot at defining the "AI-Native CLM" category — '
    'not CLM with AI bolted on, but AI-first contract intelligence.')
add_bullet('The AI governance layer is genuinely differentiated. No competitor has prompt versioning, '
    'evaluation harnesses, hallucination detection, and cost governance in one platform.')
add_bullet('To win this category: simplify the UX, add SSO, build the integration ecosystem, '
    'and tell a clear story about "AI you can trust" that resonates with enterprise risk aversion.')

doc.add_page_break()

# ═══════════════════════════════════════════════════════════════════
# 7. TECHNICAL DEBT & COMPLEXITY RISKS
# ═══════════════════════════════════════════════════════════════════

add_colored_heading('7. Technical Debt & Complexity Risks', level=1, color=RGBColor(15, 23, 42))

add_colored_heading('Systems Likely to Become Hard to Maintain', level=2)
add_bullet('Dual-backend (api/ + backend/) — the single biggest maintenance risk. '
    'Two separate FastAPI apps with overlapping concerns will diverge.')
add_bullet('Dashboard sprawl — 8+ independently built dashboards with no shared component library.')
add_bullet('Rule-based hallucination detection — will require constant tuning and will fail silently.')
add_bullet('In-memory event bus — works in single-process dev, fails in multi-process production.')
add_bullet('Hardcoded model catalog — requires code changes to add/remove models.')

add_colored_heading('Dangerous Coupling Patterns', level=2)
add_bullet('Services importing other services directly instead of through events or interfaces.')
add_bullet('SQLAlchemy sessions passed directly to services — no repository abstraction in many domains.')
add_bullet('Frontend components importing from multiple dashboard directories — no clear hierarchy.')
add_bullet('Configuration spread across .env, config.py, and hardcoded values in main.py.')

add_colored_heading('Dashboard Sprawl Risks', level=2)
add_bullet('Each dashboard has its own layout, widget system, and state management pattern.')
add_bullet('No unified dashboard configuration — users cannot customize their view.')
add_bullet('Widget duplication — same metrics appear in multiple dashboards with different code.')
add_bullet('No dashboard performance monitoring — which dashboards are slow?')

add_colored_heading('Event Schema Drift Risks', level=2)
add_bullet('Events have version numbers but no schema registry or compatibility checking.')
add_bullet('No event documentation — consumers must read the producer code to understand the schema.')
add_bullet('No event contract testing — producers can change event shapes without consumers knowing.')

add_colored_heading('AI Infrastructure Complexity Risks', level=2)
add_bullet('Multiple AI-related domains (ai, ai_governance, evaluation, llm, ml, rag) with unclear boundaries.')
add_bullet('Hallucination detection exists in both api/ and backend/ — duplicated and potentially divergent.')
add_bullet('No unified AI pipeline — each AI feature implements its own LLM calling pattern.')

add_colored_heading('Frontend State Explosion Risks', level=2)
add_bullet('TanStack Query caches all API responses — no cache size limits or garbage collection strategy.')
add_bullet('WebSocket events update state from multiple sources — race conditions are likely.')
add_bullet('No frontend state persistence strategy beyond localStorage for auth tokens and replay cursors.')
add_bullet('No offline support — losing connectivity means losing all functionality.')

add_colored_heading('Risk Timeline', level=2)

risk_table = doc.add_table(rows=1, cols=4)
risk_table.style = 'Light Grid Accent 1'
risk_table.alignment = WD_TABLE_ALIGNMENT.CENTER
risk_headers = risk_table.rows[0].cells
risk_headers[0].text = 'Risk'
risk_headers[1].text = 'Severity'
risk_headers[2].text = 'Timeline'
risk_headers[3].text = 'Impact'

risks = [
    ('Dual-backend divergence', 'Critical', 'Immediate', 'Development velocity drops 50%+'),
    ('No SSO/SAML', 'Critical', 'Immediate', 'Enterprise sales blocked'),
    ('Single PostgreSQL bottleneck', 'Critical', '6 months', 'Production outages at scale'),
    ('Dashboard sprawl', 'High', '6 months', 'UX inconsistency, maintenance burden'),
    ('In-memory event bus', 'High', '6 months', 'Event loss in multi-process deployment'),
    ('No disaster recovery', 'Critical', '12 months', 'Data loss in region failure'),
    ('Rule-based hallucination detection', 'High', '6 months', 'False sense of AI safety'),
    ('No visual workflow builder', 'High', '12 months', 'Losing deals to Ironclad/Icertis'),
    ('No mobile support', 'Medium', '12 months', 'Missing executive adoption channel'),
    ('No integration ecosystem', 'High', '12 months', 'Cannot replace incumbent CLM systems'),
    ('No performance testing', 'High', '6 months', 'Unexpected production degradation'),
    ('No E2E tests', 'Medium', '6 months', 'Regressions in critical user journeys'),
]

for row_data in risks:
    row = risk_table.add_row()
    for i, cell_data in enumerate(row_data):
        row.cells[i].text = cell_data

doc.add_paragraph()

doc.add_page_break()

# ═══════════════════════════════════════════════════════════════════
# 8. MISSING ENTERPRISE CAPABILITIES
# ═══════════════════════════════════════════════════════════════════

add_colored_heading('8. Missing Enterprise Capabilities', level=1, color=RGBColor(15, 23, 42))

cap_table = doc.add_table(rows=1, cols=4)
cap_table.style = 'Light Grid Accent 1'
cap_table.alignment = WD_TABLE_ALIGNMENT.CENTER
cap_headers = cap_table.rows[0].cells
cap_headers[0].text = 'Capability'
cap_headers[1].text = 'Priority'
cap_headers[2].text = 'Impact'
cap_headers[3].text = 'Effort'

capabilities = [
    ('SSO/SAML (OIDC, SAML 2.0)', 'Critical', 'Enterprise procurement gate', 'Medium'),
    ('SCIM Provisioning', 'Critical', 'Enterprise user management', 'Medium'),
    ('SOC 2 Type II Certification', 'Critical', 'Enterprise trust', 'High'),
    ('Disaster Recovery / Multi-Region', 'Critical', 'Data loss prevention', 'Very High'),
    ('Tenant Data Export/Deletion (GDPR)', 'Critical', 'Legal compliance', 'Medium'),
    ('Visual Workflow Builder', 'High', 'Competitive parity with Ironclad', 'High'),
    ('Integration Ecosystem (SF, SAP, Workday)', 'High', 'Enterprise adoption', 'Very High'),
    ('eDiscovery / Legal Hold', 'High', 'Legal team requirement', 'High'),
    ('Advanced Reporting / BI', 'High', 'Executive adoption', 'Medium'),
    ('API Developer Portal', 'High', 'Ecosystem growth', 'Medium'),
    ('Audit Export (PDF, CSV, SOC-compatible)', 'High', 'Compliance requirement', 'Low'),
    ('Role-Based Dashboard Configuration', 'High', 'UX personalization', 'Medium'),
    ('Notification Preferences / Digests', 'Medium', 'User satisfaction', 'Low'),
    ('White-Labeling / Brand Customization', 'Medium', 'Enterprise procurement', 'Medium'),
    ('Mobile App (iOS/Android)', 'Medium', 'Executive adoption', 'Very High'),
    ('Offline Support', 'Medium', 'Field usage', 'Very High'),
    ('Approval Delegation', 'Medium', 'Workflow flexibility', 'Medium'),
    ('External Collaboration / Customer Portals', 'Medium', 'Expansion revenue', 'High'),
    ('Plugin / Extension Framework', 'Medium', 'Ecosystem moat', 'Very High'),
    ('Localization / i18n (beyond basic)', 'Medium', 'Global enterprise', 'Medium'),
    ('Marketplace for Workflow Packs', 'Low', 'Ecosystem play', 'Very High'),
    ('Contract Template Marketplace', 'Low', 'User acquisition', 'High'),
    ('FedRAMP / IL5 Compliance', 'Low', 'Government sector', 'Extreme'),
]

for row_data in capabilities:
    row = cap_table.add_row()
    for i, cell_data in enumerate(row_data):
        row.cells[i].text = cell_data
        if i == 1:  # Priority column
            if cell_data == 'Critical':
                shading = OxmlElement('w:shd')
                shading.set(qn('w:fill'), 'FEE2E2')
                shading.set(qn('w:val'), 'clear')
                row.cells[i]._tc.get_or_add_tcPr().append(shading)
            elif cell_data == 'High':
                shading = OxmlElement('w:shd')
                shading.set(qn('w:fill'), 'FEF3C7')
                shading.set(qn('w:val'), 'clear')
                row.cells[i]._tc.get_or_add_tcPr().append(shading)

doc.add_paragraph()

doc.add_page_break()

# ═══════════════════════════════════════════════════════════════════
# 9. RECOMMENDED NEXT 10 SPRINTS
# ═══════════════════════════════════════════════════════════════════

add_colored_heading('9. Recommended Next 10 Sprints', level=1, color=RGBColor(15, 23, 42))

doc.add_paragraph()
p = doc.add_paragraph()
p.add_run('Strategic Philosophy: ').bold = True
p.add_run('The next 10 sprints must shift from feature velocity to enterprise hardening. '
    'The platform has impressive depth but critical gaps in SSO, scalability, and operational maturity. '
    'The goal is to make the platform PROCURABLE, RELIABLE, and MAINTAINABLE — not to add more features.')

sprints = [
    {
        'num': 11,
        'name': 'Enterprise Identity & Access Gateway',
        'goal': 'Remove the #1 enterprise procurement blocker',
        'why': 'No Fortune 500 company will evaluate a platform without SSO/SAML. This is the single highest-impact sprint.',
        'deliverables': [
            'SAML 2.0 / OIDC SSO integration',
            'SCIM provisioning (create/update/deactivate users)',
            'Enterprise directory sync (LDAP, Azure AD, Okta)',
            'Just-In-Time user provisioning',
            'Session management with idle timeout and concurrent session limits',
        ],
        'backend': 'SAML assertion handling, SCIM endpoints, directory sync service, session governance',
        'frontend': 'SSO login flow, SCIM configuration UI, session management UI',
        'infra': 'SAML certificate management, identity provider configuration',
        'governance': 'SSO audit logging, session governance policies',
        'value': 'Unlocks enterprise sales. Without this, no deal >$100k ARR.',
        'risk': 'Medium — SAML implementations vary across IdPs, edge cases are common',
        'complexity': 'Medium',
        'priority': 'P0 — BLOCKER',
    },
    {
        'num': 12,
        'name': 'Backend Consolidation & Architecture Hardening',
        'goal': 'Eliminate the dual-backend anti-pattern before it becomes a crisis',
        'why': 'The api/ and backend/ split will cause increasing pain. Consolidate now before the codebase doubles.',
        'deliverables': [
            'Migrate all api/ routes into backend/ domains',
            'Eliminate duplicated code (models, middleware, utilities)',
            'Unified middleware stack',
            'Common repository pattern across all domains',
            'Domain dependency documentation',
        ],
        'backend': 'Route migration, code deduplication, repository pattern implementation',
        'frontend': 'Update API client base URLs to unified backend',
        'infra': 'Remove api/ Dockerfile, update docker-compose',
        'governance': 'Route permission re-validation after consolidation',
        'value': 'Reduces maintenance burden 2x. Prevents future architectural crises.',
        'risk': 'High — migration risk, potential regression in existing endpoints',
        'complexity': 'Very High',
        'priority': 'P0 — ARCHITECTURAL',
    },
    {
        'num': 13,
        'name': 'Production Database Scaling',
        'goal': 'Remove the single PostgreSQL bottleneck',
        'why': 'Single database is the most likely cause of production outages at scale.',
        'deliverables': [
            'PostgreSQL read replicas with read/write splitting',
            'Connection pooling optimization (PgBouncer or built-in)',
            'Table partitioning for event_outbox, audit_logs, and large tables',
            'Data archival policy and implementation',
            'pgvector index maintenance automation',
            'Database performance monitoring dashboards',
        ],
        'backend': 'Read/write session factory, partitioned table models, archival service',
        'frontend': 'N/A',
        'infra': 'Read replica deployment, PgBouncer, monitoring stack',
        'governance': 'Data retention policy, archival audit trail',
        'value': 'Enables 10x scale without database becoming the bottleneck.',
        'risk': 'High — read/write splitting introduces consistency challenges',
        'complexity': 'High',
        'priority': 'P0 — SCALABILITY',
    },
    {
        'num': 14,
        'name': 'Observability & Reliability Foundation',
        'goal': 'Build the operational visibility needed for enterprise SLAs',
        'why': 'Current observability is insufficient for production. No distributed tracing, no SLO tracking, no alerting.',
        'deliverables': [
            'Enable OpenTelemetry tracing across all services',
            'Distributed tracing for Celery task chains',
            'SLO definition and tracking for critical user journeys',
            'Alerting rules for all critical metrics',
            'Log aggregation with Loki or ELK',
            'Business KPI dashboards in Grafana',
            'Synthetic monitoring for critical APIs',
        ],
        'backend': 'OpenTelemetry instrumentation, SLO service, alert generation',
        'frontend': 'Web Vitals monitoring, error tracking',
        'infra': 'Loki/ELK stack, Grafana dashboards, synthetic monitoring',
        'governance': 'SLO governance, error budget policies',
        'value': 'Enables operational teams to detect and respond to issues before customers notice.',
        'risk': 'Low — well-understood patterns, low regression risk',
        'complexity': 'Medium',
        'priority': 'P0 — OPERATIONAL',
    },
    {
        'num': 15,
        'name': 'Event Architecture Maturation',
        'goal': 'Replace in-memory event bus with production-grade event infrastructure',
        'why': 'In-memory EventBus loses events on crash. No schema registry enables drift.',
        'deliverables': [
            'Replace in-memory EventBus with Redis pub/sub or RabbitMQ',
            'Event schema registry with compatibility checking',
            'Event contract tests in CI',
            'Event retention and archival policies',
            'Dead-letter queue management UI',
            'Event replay UI for operators',
        ],
        'backend': 'Event bus migration, schema registry, contract testing',
        'frontend': 'Dead-letter queue UI, replay UI, event inspector',
        'infra': 'Message broker deployment and configuration',
        'governance': 'Event schema governance, retention policies',
        'value': 'Eliminates event loss risk. Enables reliable async architecture.',
        'risk': 'Medium — migration of existing event consumers needs careful coordination',
        'complexity': 'High',
        'priority': 'P1 — ARCHITECTURAL',
    },
    {
        'num': 16,
        'name': 'AI Quality Hardening',
        'goal': 'Replace rule-based AI quality checks with production-grade evaluation',
        'why': 'Current hallucination detection is keyword-based and will miss sophisticated hallucinations.',
        'deliverables': [
            'LLM-as-judge evaluation pipeline',
            'Embedding-based semantic verification against source material',
            'Adversarial test set generation',
            'Automated canary deployment for prompt changes',
            'Confidence calibration with empirical validation',
            'Selective prediction (model abstains when confidence is low)',
            'Human-in-the-loop hallucination review workflow',
        ],
        'backend': 'LLM-as-judge service, embedding verification, calibration service',
        'frontend': 'Hallucination review UI, confidence calibration visualization',
        'infra': 'Evaluation compute resources, model serving infrastructure',
        'governance': 'Deployment gates, human review workflows, calibration governance',
        'value': 'Makes AI safety claims credible. Required for regulated industries.',
        'risk': 'Medium — LLM-as-judge has its own quality challenges',
        'complexity': 'High',
        'priority': 'P1 — AI GOVERNANCE',
    },
    {
        'num': 17,
        'name': 'Enterprise UX Consolidation',
        'goal': 'Unify the dashboard ecosystem into a coherent, configurable experience',
        'why': '8+ independently built dashboards create confusion and maintenance burden.',
        'deliverables': [
            'Shared component library with Storybook',
            'Unified dashboard framework with configurable widgets',
            'Role-based default dashboard configuration',
            'Dashboard personalization (save, share, reset layouts)',
            'Progressive onboarding experience',
            'Notification preferences and digest settings',
            'Keyboard shortcuts for power users',
        ],
        'backend': 'Dashboard configuration API, notification preference service',
        'frontend': 'Component library, dashboard framework, onboarding tour, notification settings',
        'infra': 'N/A',
        'governance': 'Dashboard permission governance, notification policy',
        'value': 'Reduces UX fragmentation. Improves user adoption and satisfaction.',
        'risk': 'Medium — large refactoring effort, potential for regression',
        'complexity': 'High',
        'priority': 'P1 — PRODUCT QUALITY',
    },
    {
        'num': 18,
        'name': 'Integration Ecosystem & API Platform',
        'goal': 'Build the foundation for ecosystem growth',
        'why': 'Enterprise CLM buying decisions are heavily influenced by existing ecosystem integrations.',
        'deliverables': [
            'REST API developer portal with API keys and usage tracking',
            'Webhook management UI (create, test, monitor webhooks)',
            'Salesforce connector (contract records, approval sync)',
            'DocuSign/eSignature integration',
            'Slack/Microsoft Teams notification integration',
            'API rate limiting with clear headers and documentation',
            'API versioning strategy with deprecation policy',
        ],
        'backend': 'Developer portal service, connector framework, webhook management',
        'frontend': 'Developer portal UI, webhook configuration UI, connector management',
        'infra': 'API gateway, connector hosting',
        'governance': 'API key governance, webhook audit logging, connector security review',
        'value': 'Unlocks ecosystem growth. Reduces churn by integrating with existing workflows.',
        'risk': 'Medium — connector maintenance is ongoing work',
        'complexity': 'High',
        'priority': 'P1 — COMMERCIAL',
    },
    {
        'num': 19,
        'name': 'Disaster Recovery & Multi-Region Foundation',
        'goal': 'Build the resilience architecture for enterprise SLAs',
        'why': 'Current single-region deployment is unacceptable for enterprise mission-critical use.',
        'deliverables': [
            'Multi-region PostgreSQL replication',
            'Cross-region failover automation',
            'Backup/restore for tenant data',
            'Tenant-level backup and restore capability',
            'Graceful degradation mode (read-only when primary DB is down)',
            'Offline mode for frontend (cached data access)',
            'DR testing automation',
        ],
        'backend': 'Multi-region session factory, failover service, degradation mode',
        'frontend': 'Offline mode, connection status indicator, cached data access',
        'infra': 'Multi-region infrastructure, replication, DNS failover',
        'governance': 'DR plan documentation, RTO/RPO definition, DR testing governance',
        'value': 'Required for enterprise SLAs. Enables regulated industry adoption.',
        'risk': 'Very High — multi-region is complex and expensive',
        'complexity': 'Very High',
        'priority': 'P1 — ENTERPRISE',
    },
    {
        'num': 20,
        'name': 'Compliance Certification & Advanced Governance',
        'goal': 'Achieve the certifications required for enterprise procurement',
        'why': 'SOC 2, HIPAA, and GDPR compliance are procurement prerequisites for most enterprises.',
        'deliverables': [
            'SOC 2 Type II certification readiness',
            'HIPAA compliance (BAAs, PHI handling, audit controls)',
            'GDPR compliance (data export, deletion, consent management)',
            'Tenant data lifecycle management',
            'Advanced audit export (SOC 2 compatible format)',
            'Compliance reporting dashboard',
            'Penetration testing and remediation',
        ],
        'backend': 'Compliance controls, data lifecycle service, audit export service',
        'frontend': 'Compliance dashboard, data management UI, consent management',
        'infra': 'Compliance-aligned infrastructure, penetration testing',
        'governance': 'Compliance policies, certification evidence collection',
        'value': 'Unlocks regulated industries (healthcare, finance, government).',
        'risk': 'High — certification processes are lengthy and expensive',
        'complexity': 'Very High',
        'priority': 'P2 — ENTERPRISE',
    },
]

for sprint in sprints:
    add_colored_heading(f"Sprint {sprint['num']}: {sprint['name']}", level=2)
    
    p = doc.add_paragraph()
    p.add_run('Strategic Goal: ').bold = True
    p.add_run(sprint['goal'])
    
    p = doc.add_paragraph()
    p.add_run('Why It Matters: ').bold = True
    p.add_run(sprint['why'])
    
    add_colored_heading('Major Deliverables', level=3)
    for d in sprint['deliverables']:
        add_bullet(d)
    
    # Work breakdown
    work_table = doc.add_table(rows=6, cols=2)
    work_table.style = 'Light Grid Accent 1'
    work_data = [
        ('Area', 'Scope'),
        ('Backend Work', sprint['backend']),
        ('Frontend Work', sprint['frontend']),
        ('Infrastructure', sprint['infra']),
        ('Governance', sprint['governance']),
        ('Enterprise Value', sprint['value']),
    ]
    for i, (label, value) in enumerate(work_data):
        work_table.rows[i].cells[0].text = label
        work_table.rows[i].cells[1].text = value
    
    doc.add_paragraph()
    
    p = doc.add_paragraph()
    p.add_run('Technical Risk: ').bold = True
    p.add_run(sprint['risk'])
    
    p = doc.add_paragraph()
    p.add_run('Complexity: ').bold = True
    p.add_run(sprint['complexity'])
    
    p = doc.add_paragraph()
    p.add_run('Priority: ').bold = True
    priority_run = p.add_run(sprint['priority'])
    priority_run.bold = True
    if 'P0' in sprint['priority']:
        priority_run.font.color.rgb = RGBColor(220, 38, 38)
    elif 'P1' in sprint['priority']:
        priority_run.font.color.rgb = RGBColor(234, 88, 12)
    
    doc.add_paragraph()

doc.add_page_break()

# ═══════════════════════════════════════════════════════════════════
# 10. FINAL VERDICT
# ═══════════════════════════════════════════════════════════════════

add_colored_heading('10. Final Verdict', level=1, color=RGBColor(15, 23, 42))

doc.add_paragraph()

add_colored_heading('Is this becoming a real enterprise platform?', level=2)
doc.add_paragraph(
    'PARTIALLY YES, WITH RESERVATIONS. ContractEdge has the architectural skeleton of an enterprise platform — '
    'multi-tenant RBAC, event outbox, AI governance, workflow orchestration. The domain structure is clean, '
    'the middleware stack is thoughtful, and the AI governance layer is genuinely ahead of competitors.\n\n'
    'However, it is NOT yet an enterprise platform because:\n'
    '1. No SSO/SAML — the single hardest enterprise procurement blocker\n'
    '2. No SOC 2 or equivalent certification — enterprises require this\n'
    '3. Single-region, single-database deployment — no disaster recovery\n'
    '4. Dual-backend architecture — introduces unacceptable maintenance risk\n'
    '5. No visual workflow builder — enterprises expect configurability without code\n\n'
    'The foundation is strong. The next 6 months need to focus on enterprise hardening, not feature growth.'
)

add_colored_heading('What is the biggest architectural risk?', level=2)
doc.add_paragraph(
    'THE DUAL-BACKEND ARCHITECTURE. The coexistence of api/ and backend/ as two separate FastAPI applications '
    'with overlapping domains is the single most dangerous architectural decision. It creates:\n'
    '- Duplicated business logic that will inevitably diverge\n'
    '- Confusion about where new features should be built\n'
    '- Split middleware stacks with inconsistent behavior\n'
    '- Duplicated database models and migrations\n'
    '- Twice the maintenance burden for every change\n\n'
    'This must be consolidated in Sprint 12 before the codebase grows further. Every sprint that passes '
    'with this dual-backend structure increases the migration cost exponentially.'
)

add_colored_heading('What is the biggest commercial opportunity?', level=2)
doc.add_paragraph(
    'THE AI GOVERNANCE LAYER. ContractEdge has built something that no competitor has: '
    'a comprehensive AI governance system with prompt versioning, evaluation harnesses, '
    'hallucination detection, confidence calibration, cost governance, and human oversight — '
    'all integrated into a single platform.\n\n'
    'The market opportunity is to define the "AI-Native CLM" category. Incumbents like Ironclad and Icertis '
    'are bolting AI onto legacy CLM systems. ContractEdge can be the platform built for AI from the ground up.\n\n'
    'The narrative should be: "AI you can trust, with governance you can prove." '
    'This resonates with enterprise risk aversion and legal department compliance requirements.\n\n'
    'To capture this opportunity:\n'
    '1. Fix SSO (Sprint 11) — without it, no enterprise will evaluate the platform\n'
    '2. Harden AI quality (Sprint 16) — make the AI governance claims bulletproof\n'
    '3. Build the integration ecosystem (Sprint 18) — enterprises need to connect to existing systems\n'
    '4. Get SOC 2 certified (Sprint 20) — turns trust into a procurement checkbox'
)

add_colored_heading('What could kill the platform if ignored?', level=2)
doc.add_paragraph(
    '1. NO SSO/SAML — this is existential. Every month without SSO is a month of zero enterprise revenue.\n\n'
    '2. DATABASE BOTTLENECK — when the first enterprise customer goes live with real data volumes, '
    'the single PostgreSQL instance will become a crisis. No read replicas, no sharding, no partitioning.\n\n'
    '3. DUAL-BACKEND DIVERGENCE — if the api/ and backend/ codebases continue to grow independently, '
    'consolidation will become prohibitively expensive within 12 months.\n\n'
    '4. HALLUCINATION DETECTION FAILURE — when a customer finds a hallucination that the current '
    'keyword-based system missed, trust in the entire AI layer will be damaged. The current detection '
    'is not adequate for production use in regulated industries.\n\n'
    '5. DASHBOARD SPRAWL — the proliferation of independently built dashboards will create a UX crisis '
    'that frustrates users and multiplies maintenance costs.'
)

add_colored_heading('What should the founders obsess over for the next 12 months?', level=2)
doc.add_paragraph(
    '1. ENTERPRISE PROCURABILITY (Months 1-3)\n'
    '   - SSO/SAML is the #1 priority. Nothing else matters until this is done.\n'
    '   - Start SOC 2 readiness process. It takes 6-12 months.\n'
    '   - Build the security questionnaire response package.\n\n'
    '2. ARCHITECTURAL DISCIPLINE (Months 1-4)\n'
    '   - Consolidate the dual-backend into one.\n'
    '   - Implement read replicas and connection pooling.\n'
    '   - Replace in-memory event bus with Redis pub/sub.\n\n'
    '3. AI TRUSTWORTHINESS (Months 3-6)\n'
    '   - Replace rule-based hallucination detection with LLM-as-judge.\n'
    '   - Implement canary deployments for prompt changes.\n'
    '   - Build empirical confidence calibration.\n\n'
    '4. ECOSYSTEM & INTEGRATIONS (Months 4-8)\n'
    '   - Build the API developer portal.\n'
    '   - Build Salesforce and DocuSign connectors.\n'
    '   - Create a webhook ecosystem.\n\n'
    '5. SCALE & RESILIENCE (Months 6-12)\n'
    '   - Multi-region deployment foundation.\n'
    '   - Disaster recovery automation.\n'
    '   - Performance testing at 10x current scale.\n\n'
    'DO NOT:\n'
    '- Add more dashboards. Consolidate what exists.\n'
    '- Add more AI features. Harden what exists.\n'
    '- Chase enterprise logos before SSO is done.\n'
    '- Build a marketplace or plugin system yet. Too early.\n\n'
    'The next 12 months are about making ContractEdge PROCURABLE, RELIABLE, and TRUSTWORTHY — '
    'not about adding features. The features are already impressive. The enterprise readiness is not.'
)

doc.add_paragraph()
doc.add_paragraph()

# Final summary box
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run('─' * 60)
run.font.color.rgb = RGBColor(148, 163, 184)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run('END OF AUDIT REPORT')
run.bold = True
run.font.size = Pt(14)
run.font.color.rgb = RGBColor(15, 23, 42)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run('ContractEdge Platform — Enterprise Architecture & Product Maturity Audit')
run.font.color.rgb = RGBColor(100, 116, 139)
run.font.size = Pt(10)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run(f'Generated: {datetime.date.today().strftime("%B %d, %Y")}')
run.font.color.rgb = RGBColor(148, 163, 184)
run.font.size = Pt(9)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run('Classification: Confidential — Principal Architect Review')
run.font.color.rgb = RGBColor(148, 163, 184)
run.font.size = Pt(9)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run('─' * 60)
run.font.color.rgb = RGBColor(148, 163, 184)

# ── Save ───────────────────────────────────────────────────────────
output_path = '/Volumes/home/ContractRiskEdge/output/ContractEdge_Enterprise_Audit_Report.docx'
doc.save(output_path)
print(f"Audit report saved to: {output_path}")
print("Done.")
