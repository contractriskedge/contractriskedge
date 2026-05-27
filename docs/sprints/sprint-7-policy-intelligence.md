# Sprint 7 — Enterprise Intelligence + Policy Automation

**Status:** Planned
**Target:** 3 weeks
**Dependencies:** Mini Sprint 6.1 (complete), Playbook domain (exists in backend)

---

## Overview

Infrastructure is now "good enough." This sprint focuses on the layers that differentiate enterprise platforms: policy intelligence, AI explainability, clause relationships, executive analytics, and tenant customization.

The backend already has a substantial playbook domain (`backend/app/domains/playbook/`) with:
- Rule engine with AND/OR nesting, 12+ operators, effects
- Clause standard evaluation with deviation detection
- Policy override and governance audit
- Contract-level evaluation results

The gap is primarily **frontend** (policy authoring UI, explainability visualization, clause graph) and **higher-level Policy DSL** (human-readable policy definitions).

---

## Priority 1 — Policy-as-Code Engine

### Goal
Enterprise policy authoring and enforcement. Let customers define:
- "Contracts over $1M require VP approval"
- "Auto-reject indemnity above threshold"
- "GDPR clauses mandatory for EU vendors"
- "Healthcare vendors require HIPAA language"

### What exists
- `backend/app/domains/playbook/` — Full rule engine, clause standards, policy evaluation
- `RuleCondition` model with AND/OR nesting, operators, effects
- `PolicyOverride` model for per-contract overrides
- `GovernanceAudit` model for audit trail

### What to build

#### Frontend
- Policy authoring UI (rule builder with visual condition editor)
- Policy simulation mode (dry-run policy changes)
- Policy version history and rollback
- Policy audit explanation panel
- Tenant-specific policy sets

#### Backend
- Policy DSL parser (human-readable → rule engine)
- Policy evaluation graph visualization endpoint
- Policy simulation endpoint (dry-run without side effects)
- Policy recommendation engine (learn from past approvals/rejections)

### Key types
```
PolicyDefinition:
  - id, name, description
  - scope: tenant | global
  - rules: RuleCondition[]
  - effect: allow | block | flag | require_approval
  - priority: number
  - enabled: boolean
  - version: number
  - valid_from / valid_until

PolicyEvaluationResult:
  - policy_id
  - contract_id
  - triggered_rules: TriggeredRule[]
  - overall_effect: PolicyEffect
  - explanation: string
  - simulation_mode: boolean
  - evaluated_at
```

---

## Priority 2 — AI Explainability Layer

### Goal
Enterprise buyers need to understand WHY the AI reached a conclusion. Build evidence chains that show:
- Which clauses drove the risk score
- Which regulations were considered
- Which precedents were referenced
- Confidence level per finding
- Alternative recommendations

### What exists
- `router_reasoning` in routing engine — per-dimension scoring
- `mitigation_effectiveness` — per-clause-type mitigation registry with evidence basis
- `confidence` in playbook clause standard evaluation

### What to build

#### Frontend
- Evidence chain visualization (expandable tree of reasoning)
- Clause citation panel (shows exact text that triggered findings)
- Confidence score indicator per finding
- Alternative recommendation panel
- Benchmark comparison view

#### Backend
- Evidence chain endpoint (`GET /reviews/:id/evidence`)
- Confidence scoring pipeline (aggregate per-finding confidence)
- Precedent linkage (which historical contracts had similar findings)
- Regulation citation mapping

### Key types
```
EvidenceChain:
  - finding_id
  - score: number (0-100)
  - confidence: number (0-1)
  - chain: EvidenceLink[]
  - alternatives: AlternativeRecommendation[]
  - benchmark_percentile: number | null

EvidenceLink:
  - type: clause | regulation | precedent | mitigation
  - source: string
  - excerpt: string
  - relevance: number (0-1)
  - contribution: number (impact on final score)

AlternativeRecommendation:
  - title: string
  - description: string
  - impact: string (risk reduction estimate)
  - confidence: number
```

---

## Priority 3 — Clause Relationship Intelligence

### Goal
Build a knowledge graph of clause relationships:
- Approved alternatives for high-risk clauses
- Fallback language when preferred clauses are rejected
- Negotiation history per clause type
- Vendor-specific clause behavior patterns
- Clause co-occurrence patterns

### What exists
- `ClauseStandard` model with 20 categories, fallback chains
- `BenchmarkClause` model with embedding similarity
- `ClauseDeviation` detection in playbook engine

### What to build

#### Frontend
- Clause relationship graph visualization
- Alternative clause browser with comparison view
- Negotiation history timeline per clause type
- Vendor clause profile view

#### Backend
- Clause relationship graph model (nodes: clauses, edges: relationship types)
- Clause co-occurrence analysis
- Negotiation outcome tracking per clause type
- Vendor clause history aggregation

### Key types
```
ClauseNode:
  - clause_id
  - category: ClauseCategory
  - text: string
  - embedding: vector
  - metadata: ClauseMetadata

ClauseEdge:
  - source_clause_id
  - target_clause_id
  - relationship: alternative | fallback | conflicts_with | depends_on | co_occurs_with
  - strength: number (0-1)
  - context: string | null

VendorClauseProfile:
  - vendor_id
  - clause_category: ClauseCategory
  - acceptance_rate: number
  - common_alternatives: ClauseVariant[]
  - negotiation_history: NegotiationEntry[]
```

---

## Priority 4 — Executive Analytics

### Goal
Business intelligence dashboards for executives:
- Legal team throughput and bottlenecks
- Contract cycle time trends
- Risk heatmaps by department/vendor/region
- Vendor risk trends over time
- Negotiation savings tracking
- SLA forecasting
- Reviewer efficiency metrics

### What exists
- Analytics API endpoints (`GET /api/v1/analytics/*`)
- TanStack Query hooks in `useAnalytics.ts`
- Dashboard components in `frontend/components/dashboard/analytics/`

### What to build

#### Frontend
- Executive dashboard with KPI cards, trend charts, heatmaps
- Exportable reports (PDF, CSV)
- Configurable date ranges and filters
- Saved view presets
- Drill-down from aggregate to individual reviews

#### Backend
- Aggregated analytics endpoints (pre-computed for performance)
- Trend data with historical comparison
- SLA breach forecasting
- Reviewer workload heatmap data

### Key types
```
ExecutiveDashboard:
  - period: { start: string, end: string }
  - kpis: ExecutiveKPI[]
  - trends: TrendData[]
  - heatmaps: RiskHeatmap[]
  - bottlenecks: Bottleneck[]
  - forecasts: Forecast[]

ExecutiveKPI:
  - id: string
  - label: string
  - value: number
  - previous_value: number | null
  - change_pct: number | null
  - trend: up | down | stable
  - severity: positive | neutral | negative
```

---

## Priority 5 — Tenant Customization Layer

### Goal
Without this, scaling customers becomes painful. Need:
- Tenant-specific workflows
- Configurable risk models
- Custom scoring weights
- Custom routing rules
- Feature flags per tenant
- White-label branding
- Regional compliance packs

### What exists
- Tenant isolation via `tenant_id` in all models
- Multi-tenant RBAC
- Tenant-scoped replay cursors

### What to build

#### Frontend
- Tenant settings panel (branding, workflows, risk config)
- Feature flag toggles per tenant
- Custom workflow builder UI
- Regional compliance pack selector

#### Backend
- Tenant configuration model (JSON schema validated)
- Feature flag system with tenant overrides
- Custom risk weight configuration
- Workflow definition per tenant
- Compliance pack registry

### Key types
```
TenantConfiguration:
  - tenant_id: string
  - branding: { logo, primary_color, accent_color, favicon }
  - features: Record<string, boolean>
  - risk_weights: Record<string, number>
  - workflows: WorkflowDefinition[]
  - compliance_packs: string[]
  - routing_rules: RoutingRule[]
  - custom_fields: Record<string, unknown>
```

---

## Sprint 7 Execution Plan

### Week 1 — Policy Engine + Explainability
- Day 1-2: Policy authoring UI (rule builder component)
- Day 3-4: Policy simulation mode + evaluation endpoint
- Day 5: Evidence chain endpoint + frontend visualization

### Week 2 — Clause Intelligence + Analytics
- Day 1-2: Clause relationship graph model + API
- Day 3-4: Executive analytics backend aggregation
- Day 5: Analytics dashboard frontend

### Week 3 — Tenant Customization + Integration
- Day 1-2: Tenant configuration model + settings UI
- Day 3: Feature flag system
- Day 4: Compliance pack registry
- Day 5: Integration testing + documentation

---

## Success Criteria

| Area | Criteria |
|------|----------|
| Policy Engine | Customer can author, test, and deploy a policy in < 5 min |
| Explainability | Every finding has an evidence chain with clause citations |
| Clause Intelligence | Clause graph shows relationships for 20+ clause categories |
| Executive Analytics | Dashboard loads in < 2s with data from 10K+ reviews |
| Tenant Customization | Tenant can customize risk weights, workflows, and branding |
