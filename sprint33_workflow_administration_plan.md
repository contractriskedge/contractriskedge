# Sprint 33 — Workflow Administration

**Theme:** Configuration UI for workflow lifecycle management.
**Duration:** 3 weeks
**Depends on:** Sprint 32.5 (Clause Intelligence)
**After this sprint:** Sprint 34 (Rich Authoring)

---

## Overview

The Workflow Engine is built and stress-tested. Now administrators need to **configure, publish, simulate, and monitor** workflows without writing code.

This sprint builds the administration UI that makes the engine usable.

---

## Deliverable 1: Workflow Pack Library

### What it is

A library view where administrators browse, search, and manage workflow packs.

### Views

```
┌─────────────────────────────────────────────────────────────┐
│  Workflow Packs                                   [+ New]  │
├─────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 🔍 Search packs...                     [All Types ▾] │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────┐  ┌─────────────────┐ │
│  │ Contract Review v3                │  │ 🔵 Published    │ │
│  │ Standard procurement → legal →    │  │ Used 1,234x     │ │
│  │ exec approval pipeline            │  │ v3.2.0          │ │
│  │                                   │  │                 │ │
│  │ [Configure] [Versions] [Stats]    │  │ Last published  │ │
│  └───────────────────────────────────┘  │ 2026-06-15      │ │
│                                         │                 │ │
│  ┌───────────────────────────────────┐  │                 │ │
│  │ Negotiation Review v2             │  │ 🟡 Draft        │ │
│  │ Parallel legal + security review  │  │ Used 567x       │ │
│  │ with escalation                   │  │ v2.1.0          │ │
│  │                                   │  │                 │ │
│  │ [Configure] [Versions] [Stats]    │  │ Last edited     │ │
│  └───────────────────────────────────┘  │ 2026-06-20      │ │
│                                         │                 │ │
│  ┌───────────────────────────────────┐  │                 │ │
│  │ Renewal Management v1             │  │ 🟢 Published    │ │
│  │ Auto-renewal with 90-day SLA      │  │ Used 89x        │ │
│  │                                   │  │ v1.0.0          │ │
│  │ [Configure] [Versions] [Stats]    │  │                 │ │
│  └───────────────────────────────────┘  │                 │ │
└─────────────────────────────────────────────────────────────┘
```

### States

| State | Meaning | Available Actions |
|---|---|---|
| Draft | Being built, not yet usable | Edit, Delete, Publish |
| Published | Available for use | Configure, Create Version, Archive |
| Archived | No longer available | Restore |

### Implementation

- Backend: Extend existing `WorkflowPack` model with CRUD endpoints
- Frontend: Card-based library view with filtering and search
- Each pack card shows: name, description, status, version, usage count, last updated

---

## Deliverable 2: Workflow Definition Editor

### What it is

A visual editor where administrators define the stages, rules, and assignments of a workflow.

### Canvas

```
┌─────────────────────────────────────────────────────────────┐
│  Contract Review v3 · Editor                       [Save]  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────┐  │
│  │  Intake   │───▶│   AI     │───▶│  Legal   │───▶│Approval│  │
│  │           │    │ Analysis │    │  Review  │    │       │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────┘  │
│       │               │               │               │     │
│       │               │               │               │     │
│       ▼               ▼               ▼               ▼     │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────┐  │
│  │ Escalate │    │  Review  │    │ Security │    │Finalize│  │
│  └──────────┘    └──────────┘    └──────────┘    └──────┘  │
│                                                             │
│  [+ Add Stage]                                              │
│                                                             │
│  ─── Stage Configuration ─────────────────────────────────  │
│  Name: Legal Review                                         │
│  Type: ⚡ Approval Required                                  │
│  SLA:  48 hours                                              │
│  Assignment: Role-based → Legal Reviewer                     │
│  Escalation: 24h → Legal Manager, 48h → Legal Director      │
│  Conditions: Contract Value > $50K OR High Risk              │
└─────────────────────────────────────────────────────────────┘
```

### Stage types

| Type | Behavior |
|---|---|
| Automatic | Passes through without human intervention |
| Review | Assigned to a user/role for manual review |
| Approval | Requires explicit approve/reject decision |
| Escalation | Triggered by SLA breach or failure |
| Condition | Branch based on contract metadata |
| Notification | Send email/Slack notification |

### Implementation

- Frontend: Drag-and-drop canvas (React Flow or similar)
- Each stage node is configurable via a side panel
- Connections define the transition paths
- Save serializes to the `WorkflowPack.stages` JSONB field

---

## Deliverable 3: Stage Editor

### What it is

A detail configuration panel for each stage in the workflow.

### Configuration fields

| Field | Type | Example |
|---|---|---|
| Name | Text | "Legal Review" |
| Type | Enum | `approval`, `review`, `automatic`, `condition`, `notification` |
| SLA | Duration | 48 hours |
| Assignment Strategy | Enum | `role`, `manager`, `round_robin`, `specific_user` |
| Assignee Role | Role picker | `legal_reviewer` |
| Required Approvals | Number | 1 (minimum approvals needed) |
| Allow Self-Approval | Boolean | false |
| Escalation Enabled | Boolean | true |
| Escalation Level 1 | Duration + Role | 24h → Legal Manager |
| Escalation Level 2 | Duration + Role | 48h → Legal Director |
| Conditions | Rule builder | `contract_value > 50000 AND risk_level = "high"` |
| Notifications | Channel list | Email, Slack, In-app |

### Implementation

- Side panel that opens when a stage is selected in the canvas
- Form fields with validation
- Changes are reflected immediately on the canvas

---

## Deliverable 4: Rule Builder

### What it is

A visual condition builder for stage routing and escalation triggers.

### Example

```
When a contract enters the Legal Review stage:

IF
  [Contract Value]  [>]  [$50,000]
  AND
  [Risk Level]  [=]  [High]
  OR
  [Jurisdiction]  [=]  [Germany]

THEN
  Route to: Senior Legal Reviewer
  SLA: 24 hours (instead of 48)
  Notify: Compliance Team
```

### Supported conditions

| Field | Operators |
|---|---|
| Contract Value | `>`, `>=`, `<`, `<=`, `=`, `between` |
| Risk Level | `=`, `!=`, `in` |
| Jurisdiction | `=`, `!=`, `in` |
| Contract Type | `=`, `!=`, `in` |
| Department | `=`, `!=` |
| Region | `=`, `!=` |
| AI Risk Score | `>`, `>=`, `<`, `<=` |
| Clause Present | `true`, `false` |
| Has Redlines | `true`, `false` |

### Implementation

- Condition row: `[Field] [Operator] [Value]`
- AND/OR grouping with parentheses
- Preview panel shows which contracts would match

---

## Deliverable 5: Role Assignment

### What it is

A configuration panel for defining who can perform each workflow action.

### Configuration

```
Stage: Legal Review

Assignment Strategy:
  ○ Role-based       → Legal Reviewer (role)
  ○ Manager-based    → Assignee's manager
  ○ Round Robin      → Next available in Legal team
  ○ Specific User    → [User Picker]

Escalation:
  Level 1: 24h overdue → Notify Legal Manager
  Level 2: 48h overdue → Notify Legal Director
  Level 3: 72h overdue → Notify VP Legal

Approval Matrix (if type = approval):
  ┌──────────────────────┬──────────────────────┐
  │ Condition            │ Approver             │
  ├──────────────────────┼──────────────────────┤
  │ Value < $50K         │ Legal Reviewer       │
  │ $50K - $500K         │ Legal Manager        │
  │ $500K - $5M          │ Legal Director       │
  │ > $5M                │ VP Legal             │
  └──────────────────────┴──────────────────────┘
```

### Implementation

- Role picker queries existing roles from `admin_users`
- Approval matrix supports conditional approvers based on contract metadata
- Escalation chain is configured per-level

---

## Deliverable 6: Workflow Simulator

### What it is

Before publishing a workflow, administrators can simulate how it would behave with sample contract data.

### Input

```
┌─────────────────────────────────────────────────────────────┐
│  Workflow Simulator · Contract Review v3           [Run]   │
├─────────────────────────────────────────────────────────────┤
│  Contract Details:                                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Contract Value:  [$2,000,000]                        │   │
│  │ Jurisdiction:    [Germany          ▾]                │   │
│  │ Contract Type:   [MSA              ▾]                │   │
│  │ Risk Score:      [85               ]  (0-100)        │   │
│  │ Department:      [Engineering      ▾]                │   │
│  │ Region:          [EMEA             ▾]                │   │
│  │ Has Redlines:    [Yes  ▾]                            │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Output

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
│    ├─ Escalation: 24h → Legal Manager                      │
│    └─ Condition: Value > $50K ✓                            │
│  Stage 4: Executive Approval        ⚡ 24h SLA              │
│    ├─ Assigned to: VP Legal (value > $500K)                │
│    └─ Condition: Value > $500K ✓                           │
│  Stage 5: Finalize                 Auto    0.1s            │
│                                                             │
│  ⏱ Estimated Total: 74 hours (with SLA)                    │
│  👤 Approvers: Legal Reviewer → Legal Manager → VP Legal   │
│  ⚠ Conditions matched: 2/3                                 │
│                                                             │
│  [Publish Workflow]  [Edit]  [Try Different Values]        │
└─────────────────────────────────────────────────────────────┘
```

### Value

The simulator catches configuration mistakes before they affect real contracts. An admin can test "what if a $2M contract from Germany enters this workflow?" and immediately see which approvers and stages would be selected.

---

## Deliverable 7: Workflow Timeline Viewer

### What it is

A Gantt-style view of a workflow instance's progress over time.

### View

```
Workflow: COR-2026-0421 · Contract Review

┌─────────────────────────────────────────────────────────────┐
│  Timeline                                                   │
│                                                             │
│  Intake       ████████████████░░░░░░░░░░░░░░  2026-06-20   │
│  AI Analysis  ██████████████████████░░░░░░░░  2026-06-20   │
│  Legal Review ██████████████████████████████  2026-06-22   │
│  Exec Approve ████░░░░░░░░░░░░░░░░░░░░░░░░░  ⏳ In Progress│
│  Finalize     ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  ⏳ Pending    │
│                                                             │
│  ● Completed  ● In Progress  ○ Pending  ⚠ SLA Breach      │
│                                                             │
│  SLA Status: Exec Approval — 18h remaining of 24h SLA      │
└─────────────────────────────────────────────────────────────┘
```

### Implementation

- Read from `WorkflowInstance.steps` with timestamps
- Color-code by status (green=completed, blue=in-progress, gray=pending, red=breached)
- Show SLA remaining for active steps

---

## Deliverable 8: Workflow Instance Monitor

### What it is

A real-time dashboard showing all active workflow instances.

### View

```
┌─────────────────────────────────────────────────────────────┐
│  Active Workflows (47)                         [Refresh]   │
├─────────────────────────────────────────────────────────────┤
│  Status: [All ▾]  Type: [All ▾]  🔍 Search...              │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ COR-2026-0421 │ Legal Review │ ⏳ 18h SLA │ ⚠ Breach │   │
│  │ Acme Corp MSA │ VP Legal     │ remaining │           │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │ COR-2026-0420 │ Exec Approval│ ✅ 6h early │          │   │
│  │ Beta GmbH MSA │ Legal Team   │            │           │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │ COR-2026-0419 │ AI Analysis  │ ⏳ 2h SLA  │          │   │
│  │ Gamma LLC SOW │ Auto         │ remaining  │           │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  Summary: 22 Active · 3 At Risk · 2 Breached · 20 On Track │
└─────────────────────────────────────────────────────────────┘
```

### Implementation

- Reuse existing `WorkflowRepository.list_instances()` with real-time polling
- Clicking a row opens the Timeline Viewer
- Filters: status, type, assignee, SLA status

---

## Deliverable 9: Audit Viewer

### What it is

A searchable, filterable view of all workflow execution events.

### View

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
│  │ 11:28│ COR-0420 │ Escalated│ System │ SLA breach L1    │ │
│  │ 11:25│ COR-0419 │ Started  │ System │ Contract Review  │ │
│  │ 11:20│ COR-0418 │ Rejected │ LWang  │ Missing exhibits │ │
│  └──────┴──────────┴──────────┴────────┴──────────────────┘ │
│                                                             │
│  ← Previous  1 · 2 · 3 ··· 12  Next →                      │
└─────────────────────────────────────────────────────────────┘
```

### Implementation

- Read from `WorkflowExecutionLog` and `governance_audit_events`
- Filterable by workflow, event type, date range, actor
- Exportable to CSV

---

## Implementation Order

| Week | Deliverables |
|---|---|
| Week 1 | Workflow Pack Library + Definition Editor (canvas) |
| Week 1 | Stage Editor + Rule Builder |
| Week 2 | Role Assignment + Workflow Simulator |
| Week 2 | Timeline Viewer + Instance Monitor |
| Week 3 | Audit Viewer + Integration testing + Polish |

## Dependencies

- Workflow Engine must be deployed and stress-tested (✅ Sprint 33.1)
- Consolidation layer must be operational (✅ Sprint 33.1 critical fixes)
- No dependency on Sprint 32.5 (Clause Intelligence) — these are independent tracks
