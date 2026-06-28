# Sprint 33 — Enterprise Workflow Platform

**Theme:** Configuration-first business process engine with enterprise governance.
**Duration:** 3 sprints (33.1 Foundation + 33.2 Admin UI + 33.3 Operations)
**Depends on:** Sprint 32.5 (Clause Intelligence)
**After this:** Sprint 34 (Rich Authoring) → Sprint 35 (Production Readiness)

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

Every action is a configurable step. Every step can call internal services or external APIs. The engine is provider-abstracted, just like the e-signature layer.

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
  ├── is_built_in: bool (for system templates)
  ├── parent_pack_id: FK → WorkflowPack (NULL for root)  ← HIERARCHY
  └── versions: WorkflowVersion[]

WorkflowVersion
  ├── version_id: PK
  ├── pack_id: FK → WorkflowPack
  ├── version_number: int
  ├── status: enum("draft", "published", "archived")
  ├── stages_definition: JSONB
  ├── rules_definition: JSONB (JSON Logic format)
  ├── change_summary: text
  ├── published_by: user_id
  ├── published_at: timestamp
  ├── effective_date: timestamp  ← SCHEDULED PUBLISHING
  ├── expiration_date: timestamp  ← AUTO-ARCHIVE
  └── created_at: timestamp

WorkflowInstance
  ├── workflow_id: PK
  ├── pack_id: FK → WorkflowPack
  ├── version_id: FK → WorkflowVersion  ← PINNED AT CREATION
  └── ...
```

**Workflow Pack Hierarchy:**

```
Global Procurement  (parent_pack_id = NULL)
  ├── US Procurement  (parent_pack_id = Global Procurement)
  │   └── Acme Corp Procurement (parent_pack_id = US Procurement)
  ├── EU Procurement   (parent_pack_id = Global Procurement)
  └── India Procurement (parent_pack_id = Global Procurement)
```

Child packs inherit stages and rules from their parent. Only overrides are stored. This makes enterprise maintenance feasible — update the parent, and all children optionally receive the change.

---

### 1.2 Workflow Validation Engine

**What it validates:**

| Code | Severity | Check |
|---|---|---|
| `missing_start_stage` | Error | No stage marked as entry point |
| `missing_terminal_stage` | Error | No path to a terminal stage |
| `duplicate_stage_name` | Error | Two stages with the same name |
| `circular_reference` | Error | A → B → C → A |
| `unreachable_stage` | Warning | Stage has no incoming transitions |
| `dead_end_stage` | Warning | Stage has no outgoing transitions (not terminal) |
| `missing_assignee` | Error | Approval stage with no assignee |
| `missing_role` | Error | Stage references a role that doesn't exist |
| `missing_sla` | Warning | Stage has no SLA configured |
| `broken_condition` | Error | Rule references a deleted context field |
| `deprecated_role` | Warning | Stage uses a role marked deprecated |
| `cyclic_hierarchy` | Error | Pack hierarchy contains a cycle |
| `unused_rule` | Warning | Rule condition can never be true |

**Workflow Health Score:**

```
Workflow Health: 96/100

  ✅ Validation: 0 errors, 2 warnings (-4)
  ✅ All stages have assignees
  ✅ No circular references
  ⚠ 1 stage missing SLA (-2)
  ⚠ 1 deprecated role in use (-2)
  ✅ All rules reference valid fields
```

**Interface:**

```python
@dataclass
class ValidationResult:
    score: int  # 0-100 health score
    is_valid: bool  # True if zero errors
    errors: list[ValidationIssue]
    warnings: list[ValidationIssue]

class WorkflowValidator:
    def validate(self, version: WorkflowVersion) -> ValidationResult: ...
    def validate_hierarchy(self, pack: WorkflowPack) -> ValidationResult: ...
```

---

### 1.3 JSON Logic Engine

Rules are stored and evaluated as [JSON Logic](https://jsonlogic.com/).

**Example rule:**

```json
{
  "and": [
    {">": [{"var": "contract.risk_score"}, 80]},
    {"==": [{"var": "contract.jurisdiction"}, "Germany"]},
    {"or": [
      {">": [{"var": "contract.value"}, 1000000]},
      {"==": [{"var": "contract.has_redlines"}, true]}
    ]}
  ]
}
```

**Context variables available in rules:**

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
user.role
user.department
user.region
user.tenant_id
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
    operator: str  # "and", "or", ">", "==", etc.
    result: bool
    children: list[ExplanationNode]
    summary: str  # Human-readable: "Risk Score 85 > 80 ✓"
```

---

### 1.4 Workflow Simulator Engine

Pure function: `(version, contract_data) → SimulationResult`

```python
@dataclass
class SimulationInput:
    workflow_version: WorkflowVersion
    contract_data: dict

@dataclass
class SimulationResult:
    stages: list[SimulatedStage]
    total_sla_hours: float
    matched_rules: list[RuleMatch]
    skipped_rules: list[RuleSkip]
    warnings: list[str]

@dataclass
class SimulatedStage:
    name: str
    stage_type: str
    sla_hours: float
    assigned_to: str
    approval_mode: str
    resolution_strategy: str
    resolved_user: Optional[str]  ← ASSIGNMENT PREVIEW
    matched_conditions: list[str]
    escalation_chain: list[str]

@dataclass
class RuleMatch:
    rule_id: str
    rule_summary: str
    reason: str  # Human-readable explanation
    score_contribution: float

class WorkflowSimulator:
    async def simulate(self, input: SimulationInput) -> SimulationResult: ...
```

**Dry run mode:** Run simulator against last N real contracts:

```
Dry Run: Last 100 contracts
  97 → Same routing as current version
  3  → Different routing (would change behavior)
```

---

### 1.5 Workflow Impact Analysis

Before publishing, show what would be affected:

```
Publishing Contract Review v3.2 will affect:

  📄 Templates (124)
     ├── 12 templates use this as default workflow
     └── 112 templates reference it as an option

  🔄 Active Contracts (18)
     ├── 15 will continue using current version (pinned)
     └── 3 are on 'latest' and will use new version

  🏢 Departments (3)
     ├── Legal
     ├── Procurement
     └── Compliance

  🌐 Regions (5)
     ├── US, UK, DE, FR, IN
```

---

### 1.6 Feature Flags

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
  "sla_notifications": true
}
```

Stored in `tenant_settings.workflow_features` JSONB.

---

### 1.7 Built-in Workflow Packs

Shipped out-of-the-box:

| Pack | Stages | Use Case |
|---|---|---|
| **Standard Review** | Intake → AI → Review → Approval → Finalize | General purpose |
| **AI Review** | Intake → AI → Auto-approve → Finalize | Low-risk, high-volume |
| **Legal Review** | Intake → AI → Legal Review → Approval → Finalize | Legal-required |
| **Sales Contract** | Intake → AI → Review → Negotiation → Approval → Signature | Outbound sales |
| **Procurement** | Intake → AI → Procurement Review → Approval → Signature | Vendor contracts |
| **Supplier** | Intake → AI → Security → Compliance → Approval | Supplier onboarding |
| **HR** | Intake → AI → Legal → Approval → Signature | Employment contracts |
| **Renewal** | Auto-check → AI → Approval → Signature | Contract renewals |
| **High Risk** | Intake → AI → Legal → Security → Exec Approval → Finalize | Risk > 70 |
| **Low Risk** | Intake → AI → Auto-approve → Finalize | Risk < 30 |
| **Privacy / DPA** | Intake → AI → Legal → Privacy → Approval → Signature | Data privacy |
| **Software License** | Intake → AI → Legal → Tech Review → Approval → Signature | Software deals |
| **NDA** | Intake → AI → Legal → Signature | Non-disclosure |
| **MSA** | Intake → AI → Legal → Negotiation → Approval → Signature | Master services |

---

### 1.8 Environment Promotion

```
┌─────────────────────────────────────────────────────────────┐
│  Environment: Development  [Promote ▾]                      │
├─────────────────────────────────────────────────────────────┤
│  Current branch: Contract Review v3.2 (draft)               │
│                                                             │
│  Promote to:                                                │
│    ○ Test        — Validate against sample contracts        │
│    ○ UAT         — Business user acceptance testing         │
│    ○ Production  — Live for all contracts                   │
│                                                             │
│  [Export JSON]  [Export YAML]  [Import]  [Clone]            │
└─────────────────────────────────────────────────────────────┘
```

**Export format (JSON):**

```json
{
  "pack": {
    "name": "Contract Review",
    "description": "...",
    "category": "procurement"
  },
  "version": {
    "version_number": 3,
    "status": "draft",
    "stages_definition": {...},
    "rules_definition": {...}
  }
}
```

**Import:** Validates before importing. Rejects if validation errors exist.

---

### 1.9 Visual Diff Between Versions

```
Comparing v3.1 → v3.2

  Stages:
    + Security Review          (added)
    ~ Legal Review             (SLA changed: 48h → 24h)
    ~ Exec Approval            (approval mode: any_one → all_required)
    - Negotiation              (removed)

  Rules:
    + Rule 17: Value > $5M → VP Legal
    ~ Rule 12: Risk threshold changed from 80 to 75
    - Rule 9:  Deprecated (jurisdiction = "UK" → use Rule 17)
```

---

### 1.10 Action Model (Future Connectors)

Workflow stages shouldn't be limited to approval. The action model supports:

| Action | Type | Future |
|---|---|---|
| Assign | Built-in | ✅ Now |
| Notify | Built-in | ✅ Now |
| Approve | Built-in | ✅ Now |
| Reject | Built-in | ✅ Now |
| Generate PDF | Built-in | Sprint 34 |
| Create Obligation | Built-in | Sprint 34 |
| Send Signature | Provider | ✅ (DocuSign exists) |
| Call REST API | Connector | Future |
| Webhook | Connector | Future |
| SAP Integration | Connector | Future |
| Salesforce Sync | Connector | Future |
| Slack Notification | Connector | Future |
| Teams Notification | Connector | Future |
| Email | Built-in | ✅ Now |
| Delay / Wait | Built-in | Future |

**Provider abstraction** (mirrors e-signature pattern):

```python
class WorkflowActionProvider(ABC):
    @abstractmethod
    async def execute(self, context: ActionContext) -> ActionResult: ...

class WebhookActionProvider(WorkflowActionProvider): ...
class SalesforceActionProvider(WorkflowActionProvider): ...
```

---

## Sprint 33.2 — Administration UI (Week 3-4)

**Theme:** Visual configuration surface for the foundation built in 33.1.

---

### 2.1 Workflow Pack Library

Browse, search, filter, clone, and manage packs.

```
┌─────────────────────────────────────────────────────────────┐
│  Workflow Packs                                   [+ New]  │
├─────────────────────────────────────────────────────────────┤
│  [All Types ▾]  [All Status ▾]  🔍 Search...               │
│                                                             │
│  ┌───────────────────────────────────┐  ┌─────────────────┐ │
│  │ Contract Review        🔵 v3.2.0 │  │ Published        │ │
│  │ Standard procurement pipeline     │  │ Health: 96%      │ │
│  │ [Edit] [Versions] [Clone] [Stats]│  │ Used 1,234x      │ │
│  └───────────────────────────────────┘  └─────────────────┘ │
│                                                             │
│  ┌───────────────────────────────────┐  ┌─────────────────┐ │
│  │ NDA Review             🟡 v2.1.0 │  │ Draft           │ │
│  │ Simple NDA flow                  │  │ Health: 72%      │ │
│  │ [Edit] [Versions] [Clone] [Stats]│  │ ⚠ 2 warnings     │ │
│  └───────────────────────────────────┘  └─────────────────┘ │
│                                                             │
│  ┌───────────────────────────────────┐  ┌─────────────────┐ │
│  │ Standard Procurement  📋 Built-in│  │ Template         │ │
│  │ Recommended for most orgs        │  │ Health: 100%     │ │
│  │ [Clone] [Preview]                │  │                  │ │
│  └───────────────────────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Hierarchy view (toggle):**

```
▶ Global Procurement (parent)
  ├── ▶ US Procurement
  │     └── ▶ Acme Corp (customer override)
  ├── ▶ EU Procurement
  └── ▶ India Procurement
```

---

### 2.2 Workflow Definition Editor

Visual canvas with drag-and-drop stages, connections, and side-panel configuration.

- React Flow / similar canvas library
- Stage nodes with status indicators (health, warnings)
- Directed edges between stages
- Mini-map for large workflows
- Side panel opens on stage click
- Validation status indicator (green check / red X)
- "Simulate" button runs the simulator engine

---

### 2.3 Stage Editor

Configuration panel for each stage.

| Section | Fields |
|---|---|
| **General** | Name, Type (automatic, review, approval, condition, notification, escalation, webhook, delay) |
| **SLA** | Duration, Breach notification, Escalation on breach |
| **Assignment** | Strategy (12 options), Role picker, User picker |
| **Approval Mode** | Any One, All Required, Majority, Minimum Count, Weighted Voting, Sequential, Parallel |
| **Resolution** | Least Loaded, Random, Hierarchy, Custom |
| **Escalation Chain** | Level 1-3 (duration + role/user) |
| **Routing Rules** | JSON Logic builder |
| **Notifications** | On assignment, completion, escalation, breach |
| **Actions** | What this stage does (approve, notify, webhook, generate PDF, etc.) |

---

### 2.4 Rule Builder (JSON Logic)

Visual condition builder.

```
IF
  ┌──────────┐  ┌──────┐  ┌──────────┐
  │ Risk     │  │ >    │  │ 80       │
  │ Score    │  │      │  │          │
  └──────────┘  └──────┘  └──────────┘
  AND
  ┌──────────┐  ┌──────┐  ┌──────────┐
  │Jurisdict-│  │ =    │  │ Germany  │
  │ion       │  │      │  │          │
  └──────────┘  └──────┘  └──────────┘

[+ Add Condition]  [+ Add Group]

Assignment Preview:
  Value = $2M  →  VP Legal  →  John Smith (least loaded)
```

---

### 2.5 Simulator UI

**Input:** Contract metadata form + saved test cases.
**Output:** Approval path with matched/skipped rules and explanations.
**Dry run:** Run against last N contracts, show routing differences.

---

### 2.6 Visual Diff

Side-by-side version comparison with additions, changes, and removals highlighted.

---

### 2.7 Impact Analysis UI

Before publishing, show affected templates, active contracts, departments, and regions.

---

### 2.8 Environment Manager

Development → Test → UAT → Production promotion with export/import.

---

## Sprint 33.3 — Operations (Week 5-6)

**Theme:** Monitoring, analytics, and production governance.

---

### 3.1 Workflow Instance Monitor

Real-time dashboard of active instances with filtering and search.

---

### 3.2 Workflow Timeline Viewer

Gantt-style view of a single instance's progress with SLA tracking.

---

### 3.3 Workflow Analytics Dashboard

**KPIs:**

```
Average Completion Time    52.3h
Average Approval Time      18.2h
Longest Stage              Legal Review (28.4h)
Most Rejected Stage        Exec Approval (12.3%)
SLA Breach Rate            4.2%
Escalation Rate            1.8/workflow
Auto-Approval Rate         23.4%
Pending Approvals          12
Cancelled Workflows        3
Withdrawn Workflows        1
Reassigned Stages          8
```

**Stage breakdown table** with avg/P95/breach/rejection per stage.

**Trend charts** (7-day rolling avg for completion time, breach rate, volume).

---

### 3.4 Workflow Health Dashboard

Per-pack health scores with drill-down into warnings.

---

### 3.5 AI Explain for Workflow

Reuse the existing Explain infrastructure from the Review Workspace:

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

Searchable, filterable, exportable workflow event log.

---

### 3.7 Dashboard Integration

Widgets on the main Executive Dashboard: active workflows, pending approvals, avg approval time, SLA breaches, top bottlenecks.

---

## Template Library Integration

**Before:**

```json
{
  "default_workflow": "standard"
}
```

**After:**

```json
{
  "default_workflow_pack_id": "pk_contract_review",
  "default_workflow_version_id": "wv_3_2_0"
}
```

Structured references enable impact analysis, version pinning, and cross-environment migration.

---

## Summary: What was added in this revision

| Addition | Type | Sprint |
|---|---|---|
| Workflow Pack Hierarchy (parent/child) | Architecture | 33.1 |
| Environment Promotion (Dev → Test → UAT → Prod) | Architecture | 33.1 |
| Effective Dates (scheduled publishing) | Feature | 33.1 |
| Feature Flags (per-tenant capability toggles) | Feature | 33.1 |
| Workflow Import / Export (JSON/YAML) | Feature | 33.1 |
| Visual Diff Between Versions | UI | 33.2 |
| Workflow Impact Analysis | Feature | 33.1 |
| Dry Run (simulate against last N contracts) | Feature | 33.1 |
| Assignment Preview (shows actual resolved user) | UI | 33.2 |
| Workflow Health Score (0-100) | Feature | 33.1 |
| AI Explain for Workflow (reuse existing) | UI | 33.3 |
| Future Connectors (webhook, REST, SAP, Slack, etc.) | Architecture | 33.1 |
| Expanded Built-in Packs (14 packs) | Content | 33.1 |
| Expanded KPIs (14 metrics) | Analytics | 33.3 |
| Business Process Engine Vision | Architecture | All |

---

## Overall Roadmap

```
Sprint 32.5    Sprint 33.1     Sprint 33.2     Sprint 33.3     Sprint 34      Sprint 35
───────────    ───────────     ───────────     ───────────     ───────────     ───────────
Clause         Foundation      Admin UI        Operations      Rich            Production
Intelligence   • Validation    • Pack Library  • Monitor       Authoring       Readiness
• AI→Clause    • Versioning    • Editor        • Timeline      • TipTap        • Multi-tenant
  mapping      • JSON Logic    • Stage Editor  • Analytics     • Clause        • Backup/
• Insert/      • Simulator     • Rule Builder  • Health          insertion     • Restore
  Replace      • Impact        • Simulator UI  • AI Explain    • Compare       • Monitoring
• Bulk         • Templates     • Visual Diff   • Audit         • Variables     • Docs
  Actions      • Environments  • Environment   • Dashboard     • Exhibits      • Onboarding
• Compare      • Feature Flags   Manager         Widgets
• Analytics    • Health Score
               • Connectors
```
