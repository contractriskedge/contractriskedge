# Sprint 33 — Enterprise Workflow Platform (Architecture Locked)

**Status:** Architecture frozen. No further structural changes.
**Version:** 2.0 (final)
**Theme:** Configuration-first business process engine with enterprise governance.
**Duration:** 3 sprints (33.1 Foundation + 33.2 Admin UI + 33.3 Operations)
**Depends on:** Sprint 32.5 (Clause Intelligence)
**After this:** Sprint 34 (Rich Authoring) → Sprint 35 (Production Readiness) → Sprint 36 (Enterprise Integrations) → Sprint 37 (AI Copilot)

---

## Architecture Vision: Business Process Engine

This isn't just a workflow engine. It's a **business process engine** that orchestrates the full contract lifecycle:

```
AI Review
    ↓
Negotiation
    ↓
Approval
    ↓
Signature (DocuSign / providers)
    ↓
Obligations
    ↓
Renewal
    ↓
Archive
```

Every action is a configurable step. Every step can call internal services or external APIs. The engine is provider-abstracted, just like the e-signature layer. Every action emits a standard event to the **Event Bus** for downstream consumers (SAP, Salesforce, ServiceNow, Slack, Teams, analytics).

---

## Core Architecture

### Event Bus (Cross-Cutting)

Every workflow action emits a standard event:

```
WorkflowStarted
StageEntered
StageCompleted
ApprovalGranted
ApprovalRejected
SignatureSent
SignatureCompleted
ObligationCreated
WorkflowCompleted
WorkflowCancelled
WorkflowEscalated
WorkflowBreached
RuleMatched
RuleSkipped
```

Consumers connect without modifying the engine:

- SAP connector
- Salesforce connector
- ServiceNow connector
- Teams / Slack notifications
- Analytics pipeline
- Audit log

### Dynamic Metadata Provider

The rule engine doesn't hardcode field access. Instead, it queries providers:

```
ContractProvider    → contract.risk_score, contract.value, ...
SupplierProvider    → supplier.region, supplier.tier, ...
RiskProvider        → risk.score, risk.category, ...
AIProvider          → ai.findings_count, ai.top_risk, ...
ERPProvider         → erp.po_number, erp.budget_code, ...
IdentityProvider    → user.role, user.department, ...
TemplateProvider    → template.clauses_present, ...
ObligationProvider  → obligation.count, obligation.status, ...
```

Adding a new integration means adding a new provider — no rule engine changes needed.

### Business Calendar Engine

SLA calculations use **business hours**, not wall clock:

```
BusinessCalendar
  ├── calendar_id
  ├── name ("US Calendar", "UK Calendar", "Germany Calendar", "24x7")
  ├── timezone ("America/New_York", "Europe/London", ...)
  ├── working_days: [1,2,3,4,5]  # Monday-Friday
  ├── working_hours: { "start": "09:00", "end": "18:00" }
  ├── holidays: [ "2026-01-01", "2026-12-25", ... ]
  └── half_days: [ "2026-12-24": { "end": "13:00" } ]
```

Every stage SLA references a `calendar_id`. Without one, defaults to 24x7.

### Action Catalog

Stage actions are not hardcoded. Each is a provider:

```
ActionProvider
  ├── ApproveAction
  ├── RejectAction
  ├── NotifyAction
  ├── GeneratePDFAction
  ├── CreateObligationAction
  ├── SendSignatureAction
  ├── WebhookAction
  ├── RestAPIAction
  ├── SAPAction
  ├── SalesforceAction
  ├── SlackAction
  ├── TeamsAction
  ├── EmailAction
  └── DelayAction
```

New actions are added by implementing the `ActionProvider` interface — no engine changes.

---

## Sprint 33.1 — Foundation (Week 1-2)

**Theme:** Build the engine internals before any UI. Everything here is testable as pure functions.

---

### 1.1 Workflow Versioning (Mandatory)

**Principle:** Every `WorkflowInstance` is pinned to a specific `WorkflowVersion`. Never execute against "latest."

**Model:**

```
WorkflowPack
  ├── pack_id: PK
  ├── name, description, category, industry, region
  ├── is_built_in: bool (for system templates / marketplace packs)
  ├── parent_pack_id: FK → WorkflowPack (NULL for root)
  └── versions: WorkflowVersion[]

WorkflowVersion
  ├── version_id: PK
  ├── pack_id: FK → WorkflowPack
  ├── version_number: int
  ├── status: enum("draft", "published", "archived")
  ├── stages_definition: JSONB
  ├── rules_definition: JSONB (JSON Logic format)
  ├── variables: JSONB (workflow-level overridable variables)
  ├── change_summary: text
  ├── published_by: user_id
  ├── published_at: timestamp
  ├── effective_date: timestamp
  ├── expiration_date: timestamp
  └── created_at: timestamp

WorkflowInstance
  ├── workflow_id: PK
  ├── pack_id: FK → WorkflowPack
  ├── version_id: FK → WorkflowVersion (PINNED AT CREATION)
  ├── execution_context: JSONB (snapshot of data at evaluation time)
  └── ...
```

**Workflow Pack Hierarchy:**

```
Global Procurement (parent_pack_id = NULL)
  ├── US Procurement (parent_pack_id = Global Procurement)
  │   └── Acme Corp Procurement (parent_pack_id = US Procurement)
  ├── EU Procurement (parent_pack_id = Global Procurement)
  └── India Procurement (parent_pack_id = Global Procurement)
```

Child packs inherit stages, rules, and variables from their parent. Only overrides are stored.

---

### 1.2 Workflow Validation Engine

| Code | Severity | Check |
|---|---|---|
| `missing_start_stage` | Error | No stage marked as entry point |
| `missing_terminal_stage` | Error | No path to a terminal stage |
| `duplicate_stage_name` | Error | Two stages with the same name |
| `circular_reference` | Error | A → B → C → A |
| `unreachable_stage` | Warning | Stage has no incoming transitions |
| `dead_end_stage` | Warning | Stage has no outgoing transitions |
| `missing_assignee` | Error | Approval stage with no assignee |
| `missing_role` | Error | Stage references a role that doesn't exist |
| `missing_sla` | Warning | Stage has no SLA configured |
| `broken_condition` | Error | Rule references a deleted context field |
| `deprecated_role` | Warning | Stage uses a role marked deprecated |
| `cyclic_hierarchy` | Error | Pack hierarchy contains a cycle |
| `unused_rule` | Warning | Rule condition can never be true |
| `missing_calendar` | Warning | SLA references a calendar that doesn't exist |
| `rule_conflict` | Warning | Two rules have identical conditions but different outcomes |

**Workflow Health Score (0-100):**

```
Workflow Health: 96/100

  ✅ Validation: 0 errors, 2 warnings (-4)
  ✅ All stages have assignees
  ✅ No circular references
  ⚠ 1 stage missing SLA (-2)
  ⚠ 1 deprecated role in use (-2)
  ✅ All rules reference valid fields
```

---

### 1.3 JSON Logic Engine + Business Rule Catalog

Rules are stored and evaluated as [JSON Logic](https://jsonlogic.com/).

**Reusable Business Rules** (not embedded in workflows):

```
BusinessRuleCatalog
  ├── rule_id: PK
  ├── name: "High Risk Detection"
  ├── tenant_id: FK
  ├── logic: JSON Logic expression
  ├── category: "risk", "compliance", "regulatory"
  ├── tags: ["GDPR", "SOX", "HIPAA", "Export Control"]
  ├── version: int
  └── status: "active", "deprecated"
```

Multiple workflow versions reference the same business rule. Changing a rule creates a new version; workflows pin to a specific rule version.

**Context providers (extensible):**

```
contract.risk_score
contract.jurisdiction
contract.contract_type
contract.value
contract.department
contract.region
contract.industry
contract.has_redlines
contract.has_ai_findings
contract.clause_present.<clause_name>
supplier.region
supplier.tier
risk.score
risk.category
ai.findings_count
ai.top_risk
user.role
user.department
user.tenant_id
template.clauses_present
obligation.count
system.current_date
system.current_time
```

**Explanation engine:**

```python
class RuleExplainer:
    def explain(self, rule: dict, context: dict) -> ExplanationTree:
        """Return a tree showing which sub-rules matched and why."""

@dataclass
class ExplanationNode:
    operator: str
    result: bool
    children: list[ExplanationNode]
    summary: str  # "Risk Score 85 > 80 ✓"
```

---

### 1.4 Workflow Simulator Engine

Pure function: `(version, contract_data) → SimulationResult`

```python
@dataclass
class SimulationInput:
    workflow_version: WorkflowVersion
    contract_data: dict
    sandbox_mode: bool = False  # No notifications, no signatures, no obligations

@dataclass
class SimulationResult:
    stages: list[SimulatedStage]
    total_sla_hours: float
    matched_rules: list[RuleMatch]
    skipped_rules: list[RuleSkip]
    execution_context: dict  # Snapshot of all evaluated data
    warnings: list[str]

@dataclass
class SimulatedStage:
    name: str
    stage_type: str
    sla_hours: float
    calendar_id: Optional[str]
    assigned_to: str
    approval_mode: str
    resolution_strategy: str
    resolved_user: Optional[str]
    candidates: list[str]  # All eligible users considered
    selection_reason: str  # "Least loaded — Lisa has 3 open tasks"
    matched_conditions: list[str]
    escalation_chain: list[str]

@dataclass
class RuleMatch:
    rule_id: str
    rule_summary: str
    reason: str
    execution_time_ms: float

class WorkflowSimulator:
    async def simulate(self, input: SimulationInput) -> SimulationResult: ...
```

**Sandbox mode:** When enabled, no notifications, emails, signatures, or obligations are actually executed. Safe for experimentation.

**Simulation History:** Every simulation is saved:

```
SimulationLog
  ├── simulation_id: PK
  ├── version_id: FK
  ├── user_id: who ran it
  ├── input: JSONB
  ├── output: JSONB
  ├── matched_rules: JSONB
  ├── created_at: timestamp
  └── led_to_publish: bool (was this version published after this simulation?)
```

**Dry run mode:** Run simulator against last N real contracts:

```
Dry Run: Last 100 contracts
  97 → Same routing as current version
  3  → Different routing (would change behavior)
```

---

### 1.6 Workflow Impact Analysis

Before publishing, show what would be affected:

```
Publishing Contract Review v3.2 will affect:

  📄 Templates (124)
     ├── 12 templates use this as default workflow
     └── 112 templates reference it as an option

  🔄 Active Contracts (18)
     ├── 15 will continue using current version (pinned)
     └── 3 are on 'latest' and will use new version

  🏢 Departments (3)          🌐 Regions (5)
     ├── Legal                    ├── US, UK, DE, FR, IN
     ├── Procurement
     └── Compliance
```

---

### 1.7 Feature Flags

Per-tenant feature flags for workflow capabilities:

```json
{
  "parallel_approval": true,
  "delegation": false,
  "auto_approval": false,
  "escalation": true,
  "weighted_voting": false,
  "hierarchy_resolution": true,
  "webhook_actions": false,
  "sla_notifications": true,
  "business_calendar": true,
  "sandbox_mode": true,
  "ai_recommendation": false
}
```

---

### 1.8 Built-in Workflow Packs (Marketplace)

Organized by category:

| Category | Packs |
|---|---|
| **Legal** | Legal Review, NDA, DPA, IP Agreement |
| **Sales** | MSA, Sales Agreement, Software License, Reseller |
| **Procurement** | Standard Procurement, Supplier Onboarding, Vendor Review |
| **HR** | Employment Contract, Contractor Agreement, Offer Letter |
| **Privacy** | GDPR Review, CCPA Review, Data Processing Agreement |
| **Government** | Federal Procurement, State Contract, Grant Agreement |
| **Healthcare** | HIPAA Review, BAA, Clinical Trial Agreement |
| **Manufacturing** | Supply Agreement, Quality Agreement, Distributor |
| **Financial Services** | Compliance Review, SOX Review, Investment Agreement |

Each pack is a template. Tenants clone and customize.

---

### 1.9 Environment Promotion + Sandbox

```
┌─────────────────────────────────────────────────────────────┐
│  Environment: Development  [Promote ▾]                      │
├─────────────────────────────────────────────────────────────┤
│  Current: Contract Review v3.2 (draft)                      │
│                                                             │
│  Promote to:                                                │
│    ○ Sandbox   — Safe experimentation, no side effects      │
│    ○ Test      — Validate against sample contracts          │
│    ○ UAT       — Business user acceptance testing           │
│    ○ Production— Live for all contracts                     │
│                                                             │
│  [Export JSON]  [Export YAML]  [Import]  [Clone]            │
└─────────────────────────────────────────────────────────────┘
```

**Sandbox:** Full simulator access. No notifications, emails, signatures, or obligations executed. Safe for any admin to experiment.

---

### 1.10 Contract-Type Mapping

Admin-configurable mapping:

```
| Contract Type    | Workflow Pack        | Version |
|------------------|----------------------|---------|
| NDA              | NDA Review           | v2.1    |
| MSA              | Legal Review         | v3.2    |
| Procurement      | Standard Procurement | v1.4    |
| Software License | Software Review      | v1.0    |
| Employment       | HR Workflow          | v2.0    |
| Amendment        | Legal Review         | v3.2    |
```

When a contract is created or uploaded, the system auto-selects the workflow. Users can override.

---

### 1.11 AI Workflow Recommendation

Before a workflow starts, AI can recommend:

```
Recommended Workflow: Legal Review
Confidence: 92%

Reasons:
  ✓ Risk Score 84 > 70 (high risk threshold)
  ✓ Contains GDPR clauses detected
  ✓ Contains AI-specific clauses
  ✓ Vendor is new supplier (tier 3)
  ✓ Contract type matches 'MSA' pattern

[Accept] [Choose Different] [Configure Automatically]
```

Uses the existing AI infrastructure — no new model needed.

---

### 1.12 Event Bus (Cross-Cutting)

Standard events emitted by every workflow action:

```
WorkflowStarted        { workflow_id, pack_id, version_id, tenant_id, contract_id, initiated_by }
StageEntered           { workflow_id, stage_name, stage_type, assigned_to }
StageCompleted         { workflow_id, stage_name, result, duration_ms }
ApprovalGranted        { workflow_id, stage_name, approver_id, approval_mode }
ApprovalRejected       { workflow_id, stage_name, approver_id, reason }
SignatureSent          { workflow_id, envelope_id, provider }
SignatureCompleted     { workflow_id, envelope_id, signed_at }
ObligationCreated      { workflow_id, obligation_id, clause, due_date }
WorkflowCompleted      { workflow_id, total_duration_ms, sla_met }
WorkflowCancelled      { workflow_id, reason, cancelled_by }
WorkflowEscalated      { workflow_id, stage_name, level, escalated_to }
WorkflowBreached       { workflow_id, stage_name, sla_seconds, calendar_id }
RuleMatched            { workflow_id, rule_id, rule_name, execution_time_ms }
RuleSkipped            { workflow_id, rule_id, rule_name, reason }
```

Consumers subscribe without modifying the engine.

---

## Sprint 33.2 — Administration UI (Week 3-4)

**Theme:** Visual configuration surface for the foundation built in 33.1.

---

### 2.1 Workflow Pack Library

Browse, search, filter, clone, manage packs. Hierarchical view toggle.

---

### 2.2 Workflow Definition Editor

Visual canvas with drag-and-drop stages, connections, side-panel configuration.

---

### 2.3 Stage Editor

Full stage configuration: type, SLA (with calendar picker), assignment (12 strategies), approval mode (7 modes), escalation chain, routing rules, notifications, actions.

---

### 2.4 Rule Builder (JSON Logic)

Visual condition builder with field/operator/value rows that serialize to JSON Logic. Business Rule Catalog integration (reuse existing rules). Assignment preview with candidate list and selection reason.

---

### 2.5 Simulator UI

Input form + saved test cases + sandbox toggle. Output shows approval path, matched/skipped rules with explanations, execution context snapshot, execution time per rule. Dry run mode.

---

### 2.6 Workflow Context Viewer

During simulation or active execution, admins can inspect the full evaluation context:

```
Execution Context at Stage "Legal Review"

  contract.risk_score: 84
  contract.jurisdiction: "Germany"
  contract.value: 2300000
  contract.contract_type: "MSA"
  contract.department: "Procurement"
  contract.region: "EMEA"
  contract.has_redlines: true
  contract.clause_present.gdpr: true
  supplier.region: "Germany"
  supplier.tier: 2
  ai.findings_count: 8
  ai.top_risk: "GDPR compliance"
  user.role: "legal_reviewer"
  user.department: "Legal"
  template.clauses_present: ["gdpr", "indemnification", "limitation"]
```

---

### 2.7 Debug Mode

Per-instance debug view:

```
Workflow COR-2026-0421 — Debug View

Stage: Executive Approval
  Entered: 2026-06-27 14:30 UTC
  SLA: 24h (calendar: US Business)
  SLA remaining: 18h (business hours)

  Matched Rule #14 (priority 1)
    Condition: Value > $5M? No ($2.3M) → SKIPPED

  Matched Rule #17 (priority 2)
    Condition: Value $500K-$5M? Yes ($2.3M) → SELECTED
    Assigned Role: VP Legal
    Resolution Strategy: Least Loaded
    Candidates: John (5 tasks), Lisa (3 tasks), Mike (7 tasks)
    Selected: Lisa (least loaded — 3 tasks)
    Approval Mode: All Required

  Skipped Rules:
    Rule #12: Value < $500K? No → skipped
    Rule #3:  Low Risk? No (risk 84) → skipped

  Execution time: 142ms
```

---

### 2.8 Visual Diff

Side-by-side version comparison with additions, changes, removals highlighted.

---

### 2.9 Impact Analysis UI

Before publishing, show affected templates, active contracts, departments, regions.

---

### 2.10 Environment Manager + Sandbox

Dev → Sandbox → Test → UAT → Production with export/import.

---

## Sprint 33.3 — Operations (Week 5-6)

**Theme:** Monitoring, analytics, and production governance.

---

### 3.1 Workflow Instance Monitor

Real-time dashboard of active instances with filtering, search, and debug mode entry.

---

### 3.2 Workflow Timeline Viewer

Gantt-style view with SLA tracking and calendar-aware remaining time.

---

### 3.3 Workflow Analytics Dashboard

**KPIs:**

```
Average Completion Time      52.3h
Average Approval Time        18.2h
Longest Stage                Legal Review (28.4h)
Most Rejected Stage          Exec Approval (12.3%)
SLA Breach Rate              4.2%
Escalation Rate              1.8/workflow
Auto-Approval Rate           23.4%
Manual Override Rate         3.2%
Pending Approvals            12
Cancelled Workflows          3
Withdrawn Workflows          1
Reassigned Stages            8
Workflow Restart Count       2
Average Queue Time           4.2h
Average User Response Time   6.1h
Rule Execution Time (P95)    45ms
Most Frequently Matched Rule "High Risk Detection" (342x)
Most Frequently Skipped Rule "Low Value Auto-Approve" (1,234x)
Rule Conflict Count          0
```

**Stage breakdown:** avg/P95/breach/rejection per stage.
**Trend charts:** 7-day rolling avg for completion time, breach rate, volume.

---

### 3.4 Workflow Health Dashboard

Per-pack health scores (0-100) with drill-down into individual warnings.

---

### 3.5 AI Explain for Workflow

Reuses existing Explain infrastructure:

```
Why did this workflow choose VP Legal?

Because:
  ✓ Contract Value $5.2M > $5M threshold (Rule 17)
  ✓ Risk Score 92 > 80 threshold (Rule 17)
  ✓ Country Germany matches jurisdiction (Rule 17)
  ✗ Value < $500K? No (Rule 12 skipped)
  ✗ Low Risk? No (Rule 3 skipped)
```

---

### 3.6 Audit Viewer

Searchable, filterable, exportable workflow event log. Includes simulation history.

---

### 3.7 Dashboard Integration

Widgets on main Executive Dashboard: active workflows, pending approvals, avg approval time, SLA breaches, top bottlenecks.

---

## Template Library Integration

**Before:**

```json
{ "default_workflow": "standard" }
```

**After:**

```json
{
  "default_workflow_pack_id": "pk_contract_review",
  "default_workflow_version_id": "wv_3_2_0"
}
```

Plus contract-type mapping at the administration level.

---

## Summary: Complete Architecture (Frozen)

| Component | Status |
|---|---|
| Workflow Versioning (mandatory, pinned instances) | ✅ Locked |
| Workflow Pack Hierarchy (parent/child inheritance) | ✅ Locked |
| Workflow Validation Engine (13 checks + health score) | ✅ Locked |
| JSON Logic Engine (portable, composable rules) | ✅ Locked |
| Business Rule Catalog (reusable rules across workflows) | ✅ Locked |
| Dynamic Metadata Provider (extensible context providers) | ✅ Locked |
| Business Calendar Engine (business hours SLA) | ✅ Locked |
| Workflow Simulator Engine (pure function + sandbox) | ✅ Locked |
| Simulation History (audit trail of design decisions) | ✅ Locked |
| Dry Run (simulate against last N contracts) | ✅ Locked |
| Workflow Impact Analysis (templates, contracts, depts) | ✅ Locked |
| Action Catalog (provider-abstracted stage actions) | ✅ Locked |
| Event Bus (standard events for all consumers) | ✅ Locked |
| Environment Promotion (Dev → Sandbox → Test → UAT → Prod) | ✅ Locked |
| Feature Flags (per-tenant capability toggles) | ✅ Locked |
| Workflow Variables (overridable per tenant) | ✅ Locked |
| Contract-Type Mapping (auto-select workflow) | ✅ Locked |
| AI Workflow Recommendation (confidence + reasons) | ✅ Locked |
| Workflow Context Viewer (full evaluation snapshot) | ✅ Locked |
| Workflow Debug Mode (per-instance rule trace) | ✅ Locked |
| Assignment Preview (candidates + selection reason) | ✅ Locked |
| Visual Diff Between Versions | ✅ Locked |
| 14 Built-in Marketplace Packs | ✅ Locked |
| 20 KPI Metrics | ✅ Locked |
| AI Explain for Workflow | ✅ Locked |

---

## Full Roadmap

```
Sprint 32.5   Sprint 33.1    Sprint 33.2    Sprint 33.3    Sprint 34     Sprint 35      Sprint 36        Sprint 37
───────────   ───────────    ───────────    ───────────    ──────────    ──────────     ───────────      ───────────
Clause        Foundation     Admin UI       Operations     Rich          Production     Enterprise       AI Copilot
Intelligence  • Validation   • Pack Lib     • Monitor      Authoring     Readiness      Integrations     • NL workflow
• AI→Clause   • Versioning   • Editor       • Timeline     • TipTap      • Multi-       • SAP              creation
  mapping     • JSON Logic   • Stage Ed     • Analytics      editor        tenant        • Salesforce     • Draft
• Insert/     • Simulator    • Rule Builder • Health       • Clause      • Backup/      • Microsoft        assistance
  Replace     • Impact       • Simulator    • AI Explain     insertion     Restore        365             • Intelligent
• Bulk        • Templates    • Context      • Audit        • Compare     • Monitoring   • OneDrive/        search
  Actions     • Environments   Viewer      • Dashboard    • Variables   • Docs           SharePoint      • Workflow
• Compare     • Feature      • Debug Mode     Widgets     • Exhibits    • Onboarding   • Slack/Teams       recommend
• Analytics     Flags        • Visual Diff                              • Perf          • Webhooks
               • Health      • Impact                                                                   
               • Calendar       Analysis
               • Rule        • Environ
                 Catalog        Manager
               • Event Bus   • Sandbox
               • Contract-
                 Type Map
               • AI Recommend
```

**Architecture is frozen. Begin implementation.**
