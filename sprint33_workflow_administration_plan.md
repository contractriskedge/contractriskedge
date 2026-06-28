# Sprint 33 — Enterprise Workflow Platform

**Theme:** Configuration-first workflow engine with enterprise governance.
**Duration:** 4 weeks
**Depends on:** Sprint 32.5 (Clause Intelligence)
**After this sprint:** Sprint 34 (Rich Authoring)

---

## Architecture Philosophy

This sprint builds a **configuration-first** workflow platform. The UI is a reflection of the configuration model, not the model itself.

### Design principles

1. **Version everything** — Every workflow instance is pinned to a specific version. Never execute against "latest."
2. **Validate before publish** — Publishing is blocked until configuration errors are resolved.
3. **Simulate before publish** — The simulator exists before administrators can publish.
4. **JSON Logic for rules** — Rules serialize to JSON Logic, not flat table rows.
5. **Analytics from day one** — Usage data is collected from the first published workflow.

---

## Implementation Order

Unlike the UI-first approach, this build order ensures the **foundation** exists before the **surface**:

```
Phase 1 (Week 1)     →  Phase 2 (Week 2)    →  Phase 3 (Week 3-4)
─────────────────       ─────────────────       ────────────────────
Validation Engine        Pack Library            Workflow Monitor
Workflow Versioning      Definition Editor       Workflow Analytics
JSON Logic Engine        Stage Editor            Audit Viewer
Simulator Engine         Rule Builder            Dashboard Integration
Workflow Templates       Role Assignment
                         Simulator UI
                         Security & Publishing
```

---

## Phase 1: Foundation (Week 1)

---

### 1.1 Workflow Versioning

**Current model:**

```
WorkflowPack
  └── stages: JSONB
```

**Target model:**

```
WorkflowPack
  ├── pack_id: PK
  ├── name, description, category
  └── versions: WorkflowVersion[]

WorkflowVersion
  ├── version_id: PK
  ├── pack_id: FK → WorkflowPack
  ├── version_number: int
  ├── status: enum("draft", "published", "archived")
  ├── stages: JSONB (frozen at version creation)
  ├── rules: JSONB (frozen at version creation)
  ├── change_summary: text
  ├── published_by: user_id
  ├── published_at: timestamp
  └── created_at: timestamp

WorkflowInstance
  ├── workflow_id: PK
  ├── pack_id: FK → WorkflowPack
  ├── version_id: FK → WorkflowVersion  ← NEW
  └── ...
```

**Key constraint:** `WorkflowInstance.version_id` is set at creation time and never changes. Editing a workflow pack creates a new draft version; existing instances continue using their pinned version.

**Migration:**

```python
# New model
class WorkflowVersion(Base):
    __tablename__ = "workflow_versions"

    version_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    pack_id: Mapped[str] = mapped_column(ForeignKey("workflow_packs.pack_id"))
    tenant_id: Mapped[str]
    version_number: Mapped[int]
    status: Mapped[str]  # draft, published, archived
    stages_definition: Mapped[dict] = mapped_column(JSONB)
    rules_definition: Mapped[dict] = mapped_column(JSONB)
    change_summary: Mapped[Optional[str]]
    published_by: Mapped[Optional[str]]
    published_at: Mapped[Optional[datetime]]
    created_at: Mapped[datetime]

    __table_args__ = (
        UniqueConstraint("pack_id", "version_number", name="uq_pack_version"),
    )
```

**Note:** A `WorkflowVersion` model already exists in `workflow_packs/models.py`. This sprint extends it with `stages_definition`, `rules_definition`, `status` workflow, and the instance pinning logic.

---

### 1.2 Workflow Validation Engine

**What it validates before publishing:**

| Check | Error Type | Example |
|---|---|---|
| No start stage | Error | Workflow has no entry point |
| No terminal stage | Error | Workflow has no completion state |
| Duplicate stage names | Error | Two stages named "Legal Review" |
| Unreachable stage | Warning | Stage has no incoming transition |
| Dead-end stage | Warning | Stage has no outgoing transition (not terminal) |
| Circular reference | Error | A → B → C → A |
| Missing assignee | Error | Approval stage with no assignee configured |
| Missing role | Error | Stage references role that doesn't exist in tenant |
| Missing SLA | Warning | Stage has no SLA configured |
| Broken condition reference | Error | Rule references a field that doesn't exist |
| Deprecated role in use | Warning | Stage uses a role marked as deprecated |

**Implementation:**

```python
@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[ValidationIssue]
    warnings: list[ValidationIssue]

@dataclass
class ValidationIssue:
    severity: str  # "error" | "warning"
    code: str      # e.g., "missing_start_stage"
    stage: Optional[str]
    message: str
    suggestion: str

class WorkflowValidator:
    def validate(self, version: WorkflowVersion) -> ValidationResult:
        ...
```

**Integration:** The "Publish" button calls the validator first. If `is_valid == False`, publishing is blocked and errors are displayed inline.

---

### 1.3 JSON Logic Engine

**Current approach:** Flat `field / operator / value` rows stored in the database.

**Target approach:** Rules are stored as [JSON Logic](https://jsonlogic.com/) — a standard, portable format for conditional logic.

**Example — before (flat):**

```json
{
  "conditions": [
    {"field": "risk_score", "operator": ">", "value": 80},
    {"field": "jurisdiction", "operator": "=", "value": "Germany"}
  ],
  "combinator": "AND"
}
```

**Example — after (JSON Logic):**

```json
{
  "and": [
    {">": [{"var": "contract.risk_score"}, 80]},
    {"==": [{"var": "contract.jurisdiction"}, "Germany"]}
  ]
}
```

**Why JSON Logic:**

| Benefit | Explanation |
|---|---|
| Portable | Same format works in Python, JavaScript, Go, etc. |
| Composable | Rules can be nested arbitrarily |
| Serializable | Stored directly in JSONB columns |
| Evaluable client-side | Simulator can run in the browser |
| Standard | No custom DSL to maintain |

**Implementation:**

```python
import json_logic

class RuleEvaluator:
    def evaluate(self, rule: dict, context: dict) -> bool:
        return json_logic(rule, context)

    def explain(self, rule: dict, context: dict) -> ExplanationNode:
        """Return a tree showing which sub-rules matched and why."""
        ...
```

**Available variables in context:**

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
```

---

### 1.4 Workflow Simulator Engine

**What it does:** Given a workflow version and sample contract data, compute the exact approval path — which stages fire, who gets assigned, which rules match, and why.

**Engine interface:**

```python
@dataclass
class SimulationInput:
    workflow_version: WorkflowVersion
    contract_data: dict  # risk_score, jurisdiction, value, etc.

@dataclass
class SimulationResult:
    stages: list[SimulatedStage]
    total_sla_hours: float
    matched_rules: list[MatchedRule]
    skipped_rules: list[SkippedRule]
    warnings: list[str]

@dataclass
class SimulatedStage:
    name: str
    stage_type: str
    sla_hours: float
    assigned_to: str  # role or user name
    approval_mode: str
    resolution_strategy: str
    matched_conditions: list[str]
    escalation_chain: list[str]

@dataclass
class MatchedRule:
    rule_id: str
    rule_summary: str
    reason: str  # Human-readable explanation

class WorkflowSimulator:
    async def simulate(
        self,
        version: WorkflowVersion,
        input_data: SimulationInput,
    ) -> SimulationResult:
        ...
```

**Why the engine comes before the UI:** The simulator engine is a pure function — version + data → result. It can be:
- Unit tested independently
- Called from the admin UI
- Called from the API for "what-if" analysis
- Used in CI/CD to validate workflow changes

---

### 1.5 Workflow Templates

**Out-of-the-box packs that tenants can clone:**

| Template | Stages | Use Case |
|---|---|---|
| Standard Procurement | Intake → AI Analysis → Procurement Review → Approval → Signature | General procurement |
| High Risk Contract | Intake → AI Analysis → Legal Review → Security Review → Exec Approval → Signature | High-value or high-risk |
| NDA | Intake → AI Analysis → Legal Review → Signature | Non-disclosure agreements |
| MSA | Intake → AI Analysis → Legal Review → Negotiation → Approval → Signature | Master services agreements |
| Vendor Onboarding | Intake → Security Review → Compliance Review → Approval → Signature | New vendor setup |
| Sales Agreement | Intake → AI Analysis → Legal Review → Approval → Signature | Outbound sales |
| Renewal | Auto-check → AI Analysis → Approval → Signature | Contract renewals |

**Implementation:**

- Templates are seeded as `WorkflowPack` records with `is_built_in = True`
- Tenants see them in the Pack Library with a "Clone" button
- Cloning creates a new draft version owned by the tenant

---

## Phase 2: Configuration UI (Week 2)

---

### 2.1 Workflow Pack Library

Browse, search, filter, and manage workflow packs.

**Views:**

```
┌─────────────────────────────────────────────────────────────┐
│  Workflow Packs                                   [+ New]  │
├─────────────────────────────────────────────────────────────┤
│  [All Types ▾]  [All Status ▾]  🔍 Search packs...         │
│                                                             │
│  ┌───────────────────────────────────┐  ┌─────────────────┐ │
│  │ Contract Review        🔵 v3.2.0 │  │ Published        │ │
│  │ Standard procurement pipeline     │  │ Used 1,234x     │ │
│  │                                   │  │ Last pub 06-15  │ │
│  │ [Edit] [Versions] [Clone] [Stats]│  │                 │ │
│  └───────────────────────────────────┘  └─────────────────┘ │
│                                                             │
│  ┌───────────────────────────────────┐  ┌─────────────────┐ │
│  │ NDA Review             🟡 v2.1.0 │  │ Draft           │ │
│  │ Simple NDA approval flow         │  │ ⚠ 2 warnings    │ │
│  │                                   │  │ Last edit 06-20 │ │
│  │ [Edit] [Versions] [Clone] [Stats]│  │                 │ │
│  └───────────────────────────────────┘  └─────────────────┘ │
│                                                             │
│  ┌───────────────────────────────────┐  ┌─────────────────┐ │
│  │ Standard Procurement   📋 Built-in│  │ Template        │ │
│  │ Recommended for most orgs        │  │                  │ │
│  │                                   │  │                  │ │
│  │ [Clone] [Preview]                │  │                  │ │
│  └───────────────────────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Pack detail view:**

```
┌─────────────────────────────────────────────────────────────┐
│  Contract Review                              [Edit] [▸ ▸ ▸]│
├─────────────────────────────────────────────────────────────┤
│  Versions                                                   │
│  ┌──────┬────────┬──────────┬──────────┬──────────────────┐ │
│  │  Ver │ Status │ Published│  By      │  Stages │ Rules  │ │
│  ├──────┼────────┼──────────┼──────────┼──────────────────┤ │
│  │ 3.2  │ 🔵 Pub │ 06-15    │ JSmith   │  7      │ 12     │ │
│  │ 3.1  │ 🔵 Pub │ 05-20    │ JSmith   │  7      │ 10     │ │
│  │ 3.0  │ 📦 Arch │ 04-01    │ LWang    │  6      │ 8      │ │
│  │ 2.0  │ 📦 Arch │ 02-15    │ LWang    │  5      │ 5      │ │
│  └──────┴────────┴──────────┴──────────┴──────────────────┘ │
│                                                             │
│  Health: ✅ All stages configured · No validation errors    │
│  Active instances on v3.2: 47 · v3.1: 12 · v3.0: 3        │
└─────────────────────────────────────────────────────────────┘
```

---

### 2.2 Workflow Definition Editor

Visual canvas for arranging stages and transitions.

**Canvas features:**

- Drag-and-drop stage nodes
- Connect stages with directed edges
- Side panel for stage configuration (opens on click)
- Zoom / pan
- Mini-map for large workflows
- Validation status indicator (green check or red X)
- "Simulate" button runs the simulator engine on current config

**Stage node display:**

```
┌──────────────────────┐
│  Legal Review        │
│  ⚡ Approval Required │
│  ⏱ 48h SLA           │
│  👤 Legal Reviewer    │
│  ⚠ 1 warning         │
└──────────────────────┘
```

---

### 2.3 Stage Editor

Configuration panel for each stage.

**Fields:**

| Section | Fields |
|---|---|
| **General** | Name, Type (automatic, review, approval, condition, notification, escalation) |
| **SLA** | Duration (hours), Breach notification, Escalation on breach |
| **Assignment** | Strategy (role, specific user, manager, round robin, least loaded, random, hierarchy, business owner, contract owner, department head, legal director, custom resolver), Role picker, User picker |
| **Approval Mode** | Any One, All Required, Majority, Minimum Count, Weighted Voting, Sequential, Parallel |
| **Resolution Strategy** | Least Loaded, Random, Hierarchy, Custom |
| **Escalation Chain** | Level 1 (duration + role/user), Level 2, Level 3 |
| **Routing Rules** | JSON Logic editor (see Rule Builder) |
| **Notifications** | On assignment, On completion, On escalation, On breach |

---

### 2.4 Rule Builder

Visual editor for JSON Logic rules.

**UI:**

```
IF
  ┌──────────┐  ┌──────────┐  ┌──────────┐
  │ Risk     │  │ >        │  │ 80       │
  │ Score    │  │          │  │          │
  └──────────┘  └──────────┘  └──────────┘
  AND
  ┌──────────┐  ┌──────────┐  ┌──────────┐
  │Jurisdict-│  │ =        │  │ Germany  │
  │ion       │  │          │  │          │
  └──────────┘  └──────────┘  └──────────┘
  OR
  ┌──────────┐  ┌──────────┐  ┌──────────┐
  │Contract  │  │ >        │  │ 1,000,000│
  │Value     │  │          │  │          │
  └──────────┘  └──────────┘  └──────────┘

[+ Add Condition]  [+ Add Group (AND/OR)]
```

**Serializes to:**

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

**Preview panel:** Shows which contracts in the system would match this rule.

---

### 2.5 Role Assignment & Routing Rules

**Instead of a flat approval matrix, use routing rules:**

```json
{
  "stage": "executive_approval",
  "default_assignee": {"role": "legal_reviewer"},
  "routing_rules": [
    {
      "priority": 1,
      "condition": {">": [{"var": "contract.value"}, 5000000]},
      "assignee": {"role": "vp_legal"},
      "approval_mode": "all_required",
      "resolution": "hierarchy"
    },
    {
      "priority": 2,
      "condition": {"and": [
        {">": [{"var": "contract.value"}, 500000]},
        {"<=": [{"var": "contract.value"}, 5000000]}
      ]},
      "assignee": {"role": "legal_director"},
      "approval_mode": "all_required"
    },
    {
      "priority": 3,
      "condition": {"<=": [{"var": "contract.value"}, 500000]},
      "assignee": {"role": "legal_manager"},
      "approval_mode": "any_one"
    }
  ]
}
```

**Resolution strategies:**

| Strategy | Behavior |
|---|---|
| `role` | Assign to any user with the specified role |
| `specific_user` | Assign to a specific named user |
| `manager` | Assign to the assignee's manager |
| `round_robin` | Cycle through available users evenly |
| `least_loaded` | Assign to the user with the fewest active assignments |
| `random` | Pick randomly from eligible users |
| `hierarchy` | Assign to the most junior eligible user; escalate up |
| `business_owner` | Resolve to the business owner from contract metadata |
| `contract_owner` | Resolve to the contract owner (created_by) |
| `department_head` | Resolve to the department head from org chart |
| `legal_director` | Resolve to the legal director for the region |
| `custom_resolver` | Pluggable function (for future extension) |

---

### 2.6 Simulator UI

**Input panel:**

```
┌─────────────────────────────────────────────────────────────┐
│  Workflow Simulator · Contract Review v3.2         [Run]   │
├─────────────────────────────────────────────────────────────┤
│  Contract Details:                                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Contract Value:  [$2,000,000]                        │   │
│  │ Jurisdiction:    [Germany          ▾]                │   │
│  │ Contract Type:   [MSA              ▾]                │   │
│  │ Risk Score:      [85               ]                 │   │
│  │ Department:      [Engineering      ▾]                │   │
│  │ Region:          [EMEA             ▾]                │   │
│  │ Has Redlines:    [Yes  ▾]                            │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  Test Cases: [High Risk NDA ▾] [Save Current] [Load]       │
└─────────────────────────────────────────────────────────────┘
```

**Result panel:**

```
┌─────────────────────────────────────────────────────────────┐
│  Simulation Result                                          │
├─────────────────────────────────────────────────────────────┤
│  📋 Approval Path                                           │
│                                                             │
│  Stage 1: Intake                    Auto    0.1s           │
│  Stage 2: AI Analysis               Auto    2m             │
│  Stage 3: Legal Review              ⚡ 48h SLA              │
│    ├─ Assigned to: Legal Reviewer (role-based)              │
│    ├─ Mode: All Required                                    │
│    ├─ Escalation: 24h → Legal Manager                       │
│    └─ Condition: Value > $50K ✓                             │
│  Stage 4: Executive Approval        ⚡ 24h SLA              │
│    ├─ Assigned to: VP Legal (routing rule 1)                │
│    ├─ Mode: All Required                                    │
│    ├─ Resolution: Hierarchy                                 │
│    └─ Condition: Value > $500K ✓                            │
│  Stage 5: Finalize                 Auto    0.1s            │
│                                                             │
│  ⏱ Estimated: 74 hours  │  👤 VP Legal → Legal Director    │
│                                                             │
│  ── Why this route? ─────────────────────────────────────  │
│  ✅ Matched Rule 1: Value > $5M? No (value is $2M)         │
│  ✅ Matched Rule 2: Value $500K-$5M? Yes → VP Legal        │
│  ✅ Matched Rule 3: Value < $500K? No                      │
│                                                             │
│  [Publish v3.2]  [Edit]  [Try Different Values]            │
└─────────────────────────────────────────────────────────────┘
```

**Saved test cases:**

```
My Test Cases
  ├── High Risk NDA (risk: 92, value: $50K, jurisdiction: Germany)
  ├── Low Value Procurement (risk: 25, value: $10K, jurisdiction: US)
  ├── Enterprise MSA (risk: 70, value: $5M, jurisdiction: UK)
  └── Vendor Renewal (risk: 40, value: $200K, jurisdiction: Canada)
```

---

### 2.7 Security & Publishing

**Publishing requires explicit permission:**

```
Roles that can publish:
  ☑ Workflow Administrator
  ☑ Legal Administrator
  ☑ System Administrator

Roles that can edit (but not publish):
  ☑ Compliance Manager
  ☑ Procurement Manager
```

**Publish flow:**

1. User clicks "Publish"
2. Validation engine runs
3. If errors: show inline, block publishing
4. If warnings: show with "Publish Anyway" option
5. If clean: create new version, set status to `published`
6. Record `published_by` and `published_at`
7. Optionally notify active workflow users of new version

---

## Phase 3: Monitoring & Analytics (Weeks 3-4)

---

### 3.1 Workflow Instance Monitor

Real-time dashboard of all active workflow instances.

```
┌─────────────────────────────────────────────────────────────┐
│  Active Workflows (47)                         [Refresh]   │
├─────────────────────────────────────────────────────────────┤
│  Status: [All ▾]  Pack: [All ▾]  🔍 Search...              │
│                                                             │
│  ┌──────┬──────────┬──────────┬──────────┬────────┬──────┐  │
│  │ ID   │ Contract │ Stage    │ Assignee │ SLA    │Status│  │
│  ├──────┼──────────┼──────────┼──────────┼────────┼──────┤  │
│  │ 0421 │ Acme MSA │ Legal Rev│ JSmith   │ 18h    │ ⚠    │  │
│  │ 0420 │ Beta SOW │ Exec App │ LWang    │ 6h     │ ✅   │  │
│  │ 0419 │ Gamma NDA│ AI Analy │ Auto     │ 2h     │ ⏳   │  │
│  └──────┴──────────┴──────────┴──────────┴────────┴──────┘  │
│                                                             │
│  Summary: 22 Active · 3 At Risk · 2 Breached · 20 On Track │
└─────────────────────────────────────────────────────────────┘
```

**Columns:** ID, Contract Name, Current Stage, Assignee, SLA Remaining, Status
**Filters:** Status, Pack, Stage, Assignee, Date range
**Actions:** Click row → Timeline Viewer

---

### 3.2 Workflow Timeline Viewer

Gantt-style view of a single instance's progress.

```
Workflow: COR-2026-0421 · Contract Review v3.2

Intake       ████████████████░░░░░░░░░░░░░░  Jun 20  ✅
AI Analysis  ██████████████████████░░░░░░░░  Jun 20  ✅
Legal Review ██████████████████████████████  Jun 22  ✅
Exec Approve ████░░░░░░░░░░░░░░░░░░░░░░░░░  ⏳ In Progress
Finalize     ░░░░░░░░░░░░░░░░░░░░░░░░░░░░  ⏳ Pending

● Completed  ● In Progress  ○ Pending  ⚠ SLA Breach

SLA: Exec Approval — 18h remaining of 24h SLA
Version: Contract Review v3.2 (pinned at creation)
```

---

### 3.3 Workflow Analytics Dashboard

**Metrics:**

```
Workflow Analytics — Last 30 Days

📊 Volume
  Workflows started:       1,234
  Workflows completed:     1,189
  Completion rate:         96.4%

⏱ Speed
  Average completion:      52.3h
  Median completion:       44.0h
  P95 completion:          120.5h
  Fastest stage:           AI Analysis (2.3m avg)
  Slowest stage:           Legal Review (28.4h avg)

🚦 Quality
  Most rejected stage:     Executive Approval (12.3% rejection)
  Average SLA breaches:    4.2%
  Average escalations:     1.8 per workflow
  Auto-approvals:          23.4%

📈 Trends
  ┌──────────────────────────────────────────────────┐
  │  Completion Time (7-day rolling avg)             │
  │  ▁▃▄▆▇▆▅▄▃▂▁▁▂▃▄▅▆▇▆▅▄▃▂▁  Current: 52.3h     │
  └──────────────────────────────────────────────────┘
```

**Breakdown by stage:**

```
Stage Performance
┌──────────────────┬──────────┬──────────┬──────────┬──────────┐
│ Stage            │ Avg Time │ P95      │ Breaches │Rejections│
├──────────────────┼──────────┼──────────┼──────────┼──────────┤
│ Intake           │ 0.1m     │ 0.2m     │ 0%       │ N/A      │
│ AI Analysis      │ 2.3m     │ 5.1m     │ 0%       │ N/A      │
│ Legal Review     │ 28.4h    │ 52.1h    │ 8.2%     │ 4.1%     │
│ Exec Approval    │ 18.2h    │ 44.3h    │ 12.1%    │ 12.3%    │
│ Finalize         │ 0.1m     │ 0.3m     │ 0%       │ N/A      │
└──────────────────┴──────────┴──────────┴──────────┴──────────┘
```

---

### 3.4 Workflow Health

**Per-pack health indicator:**

```
Contract Review v3.2

🟢 Healthy

  7 stages configured
  12 rules defined
  0 validation errors
  0 warnings

  Active instances: 47 (v3.2) · 12 (v3.1) · 3 (v3.0)
  Last published: 2026-06-15 by JSmith
```

**Warning examples:**

```
⚠ 1 deprecated role in use: "senior_legal" → rename to "legal_reviewer"
⚠ 1 stage missing SLA: "Security Review"
⚠ 1 rule references deleted field: "contract.legacy_score"
```

---

### 3.5 Audit Viewer

Searchable, filterable, exportable workflow event log.

```
┌─────────────────────────────────────────────────────────────┐
│  Workflow Audit Log                                         │
├─────────────────────────────────────────────────────────────┤
│  Workflow: [All ▾]  Event: [All ▾]  From: [date]  To: [date]│
│                                                             │
│  ┌──────┬──────────┬──────────┬────────┬──────────────────┐ │
│  │ Time │ Workflow │ Event    │ Actor  │ Detail           │ │
│  ├──────┼──────────┼──────────┼────────┼──────────────────┤ │
│  │ 11:32│ COR-0421 │ Approved │ JSmith │ Exec approval    │ │
│  │ 11:30│ COR-0421 │ Assigned │ System │ → Legal Review   │ │
│  │ 11:28│ COR-0420 │ Published│ LWang  │ Contract Rev v3.2│ │
│  │ 11:25│ COR-0419 │ Started  │ System │ Contract Review  │ │
│  │ 11:20│ COR-0418 │ Rejected │ LWang  │ Missing exhibits │ │
│  │ 11:15│ COR-0417 │ Escalated│ System │ SLA breach L1    │ │
│  │ 11:10│ COR-0416 │ Validated│ System │ 0 errors, 2 warn │ │
│  └──────┴──────────┴──────────┴────────┴──────────────────┘ │
│                                                             │
│  ← Previous  1 · 2 · 3 ··· 12  Next →        [Export CSV] │
└─────────────────────────────────────────────────────────────┘
```

**Event types:** started, completed, failed, approved, rejected, assigned, escalated, published, validated, breached, cancelled, compensated

---

### 3.6 Dashboard Integration

**Widgets on the main Executive Dashboard:**

```
┌──────────────────────┐  ┌──────────────────────┐
│ Active Workflows     │  │ Pending Approvals     │
│ 47                   │  │ 12                    │
│ ▲ 8% from last week  │  │ ▼ 3% from yesterday  │
└──────────────────────┘  └──────────────────────┘

┌──────────────────────┐  ┌──────────────────────┐
│ Avg Approval Time    │  │ SLA Breaches          │
│ 52.3h                │  │ 4.2%                  │
│ ▼ 2h from last month │  │ ▲ 0.5% from last week│
└──────────────────────┘  └──────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Top Bottlenecks                                              │
│ 1. Executive Approval (avg 18.2h, 12.3% rejection)          │
│ 2. Legal Review (avg 28.4h, 8.2% breach rate)               │
│ 3. Security Review (avg 6.1h, 3.1% breach rate)             │
└─────────────────────────────────────────────────────────────┘
```

---

## Template Library Integration

**Current state:**

```json
{
  "default_workflow": "standard"
}
```

**Target state:**

```json
{
  "default_workflow_pack_id": "pk_contract_review",
  "default_workflow_version_id": "wv_3_2_0"
}
```

This means:
- Template → Contract generation automatically pins the workflow version
- Changing the template's default workflow doesn't affect in-progress contracts
- Reports can show which workflow version each contract used

---

## Summary: What changed from the previous plan

| Area | Previous Plan | Updated Plan |
|---|---|---|
| Workflow Versioning | Implicit | **Mandatory** — instances pinned to version_id |
| Validation | Not mentioned | **Validation engine** blocks publishing on errors |
| Simulator | UI-only | **Engine-first** — pure function, testable, reusable |
| Rules | Flat field/operator/value | **JSON Logic** — portable, composable, standard |
| Approval Matrix | Simple table | **Routing Rules** with priority and conditions |
| Resolution Strategies | 4 options | **12 options** including least_loaded, hierarchy, etc. |
| Approval Modes | Not mentioned | **7 modes** including sequential, parallel, weighted |
| Templates | Not mentioned | **7 built-in templates** for common workflows |
| Analytics | Not mentioned | **Full analytics dashboard** with trends and bottlenecks |
| Health | Not mentioned | **Per-pack health indicator** with warnings |
| Security | Not mentioned | **Role-based publishing** — 3 roles can publish |
| Template Integration | Text field | **Structured pack_id + version_id** |
| Implementation Order | UI-first | **Foundation-first** — validation → simulator → UI |
