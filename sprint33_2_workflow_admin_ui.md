# Sprint 33.2 — Workflow Administration UI

**Theme:** Administrator product — not workflow logic, but workflow configuration.
**Foundation:** ✅ Sprint 33.1 frozen. No engine changes unless defects found.
**Duration:** 2 weeks
**After this:** Sprint 33.3 (Operations) → Sprint 34 (Production Readiness)

---

## Design Principle

Administrators should never have to edit JSON or think about database tables. Every workflow operation — create, edit, simulate, validate, publish, version, archive, and monitor — should be achievable through the UI.

---

## Deliverable 1: Workflow Pack Library

### Views

**Library grid:**

```
┌─────────────────────────────────────────────────────────────┐
│  Workflow Packs                                   [+ New]  │
├─────────────────────────────────────────────────────────────┤
│  🔍 Search packs...                    [All Categories ▾]  │
│                                                             │
│  ┌────────────────────────┐  ┌────────────────────────┐    │
│  │ NDA Review        🔵   │  │ Procurement     🔵     │    │
│  │ v3 · Published         │  │ v2 · Published          │    │
│  │ Used 1,234x            │  │ Used 892x               │    │
│  │ [Clone] [Edit] [▸ ▸ ▸]│  │ [Clone] [Edit] [▸ ▸ ▸]│    │
│  └────────────────────────┘  └────────────────────────┘    │
│                                                             │
│  ┌────────────────────────┐  ┌────────────────────────┐    │
│  │ Sales Contract   🟡   │  │ High Value       📋   │    │
│  │ v1 · Draft             │  │ Built-in               │    │
│  │ ⚠ 2 validation warns   │  │ [Clone] [Preview]      │    │
│  │ [Edit] [Validate] [Pub]│  │                        │    │
│  └────────────────────────┘  └────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

**Version history (flyout):**

```
NDA Review — Versions
┌──────┬──────────┬──────────┬──────────┬──────────────────┐
│  Ver │ Status   │ Published│  By      │  Stages │ Rules  │
├──────┼──────────┼──────────┼──────────┼──────────────────┤
│  v3  │ 🔵 Pub  │ 06-15    │ JSmith   │  5      │ 8      │
│  v2  │ 🔵 Pub  │ 05-20    │ JSmith   │  5      │ 6      │
│  v1  │ 📦 Arch │ 04-01    │ LWang    │  4      │ 4      │
└──────┴──────────┴──────────┴──────────┴──────────────────┘
[Compare v2 vs v3]  [Clone v2]
```

**Pack detail:**

```
NDA Review v3
  Status: ✅ Published · Health: 96/100
  Stages: 5 · Rules: 8 · Active instances: 47
  Last published: 2026-06-15 by JSmith
  ⚠ 1 warning: Stage 'Security Review' has no SLA configured
```

---

## Deliverable 2: Workflow Designer

### What it is

A structured, step-by-step workflow builder. Not a free-form canvas — a reliable form-based designer that administrators can use without training.

### View

```
┌─────────────────────────────────────────────────────────────┐
│  Edit: NDA Review v3                              [Save]   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Workflow Stages                                           │
│                                                             │
│  ┌── 1 ──────────────────────────────────────────────────┐  │
│  │  Intake           (Start)                   [Edit] [X]│  │
│  └────────────────────────────────────────────────────────┘  │
│       │                                                     │
│       ▼                                                     │
│  ┌── 2 ──────────────────────────────────────────────────┐  │
│  │  AI Analysis      (Automatic)                [Edit] [X]│  │
│  └────────────────────────────────────────────────────────┘  │
│       │                                                     │
│       ▼                                                     │
│  ┌── 3 ──────────────────────────────────────────────────┐  │
│  │  Legal Review     (Approval · ⚡ 48h SLA)     [Edit] [X]│  │
│  └────────────────────────────────────────────────────────┘  │
│       │                                                     │
│       ├──→ ┌── 3a ───────────────────────────────────────┐  │
│       │    │  Escalate to Legal Manager  (24h) [Edit] [X] │  │
│       │    └──────────────────────────────────────────────┘  │
│       ▼                                                     │
│  ┌── 4 ──────────────────────────────────────────────────┐  │
│  │  Finalize        (Automatic)                  [Edit] [X]│  │
│  └────────────────────────────────────────────────────────┘  │
│                                                             │
│  [+ Add Stage]  [+ Add Escalation]                          │
│                                                             │
│  ── Stage Configuration ──────────────────────────────────  │
│  (opens when a stage is selected)                           │
│                                                             │
│  Name:     [Legal Review              ]                     │
│  Type:     [⚡ Approval Required  ▾]                        │
│  SLA:      [48] [Hours ▾]  Calendar: [US Business ▾]       │
│  Assignee: [Legal Reviewer ▾]                               │
│  Strategy: [Least Loaded ▾]                                 │
│  Mode:     [All Required ▾]                                 │
│                                                             │
│  [Save Stage]  [Delete Stage]                               │
└─────────────────────────────────────────────────────────────┘
```

### Key behaviors

- Click a stage → side panel opens with full configuration
- "Add Stage" appends to the end
- Drag handles for reordering (simple up/down arrows)
- Stage type determines available configuration fields
- Validation status indicator at the top (green/red)

---

## Deliverable 3: Rule Builder

### What it is

A visual condition builder that generates JSON Logic automatically. Administrators choose fields, operators, and values — they never see raw JSON.

### View

```
┌─────────────────────────────────────────────────────────────┐
│  Routing Rules — Legal Review Stage                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─ Rule 1 ──────────────────────────────────────────────┐  │
│  │  IF                                                     │  │
│  │    ┌──────────┐  ┌──────┐  ┌──────────┐                │  │
│  │    │ Risk     │  │ >    │  │ 80       │                │  │
│  │    │ Score    │  │      │  │          │                │  │
│  │    └──────────┘  └──────┘  └──────────┘                │  │
│  │    AND                                                 │  │
│  │    ┌──────────┐  ┌──────┐  ┌──────────┐                │  │
│  │    │Jurisdict-│  │ =    │  │ Germany  │                │  │
│  │    │ion       │  │      │  │          │                │  │
│  │    └──────────┘  └──────┘  └──────────┘                │  │
│  │                                                         │  │
│  │  THEN                                                   │  │
│  │    Assign to:  [VP Legal          ▾]                    │  │
│  │    Mode:       [All Required      ▾]                    │  │
│  │    Strategy:   [Least Loaded      ▾]                    │  │
│  │                                                         │  │
│  │  [+ Add Condition]  [+ Add Group (AND/OR)]              │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─ Rule 2 ──────────────────────────────────────────────┐  │
│  │  IF                                                     │  │
│  │    ┌──────────┐  ┌──────────┐  ┌──────────┐            │  │
│  │    │ Contract │  │ <        │  │ 500,000  │            │  │
│  │    │ Value    │  │          │  │          │            │  │
│  │    └──────────┘  └──────────┘  └──────────┘            │  │
│  │                                                         │  │
│  │  THEN                                                   │  │
│  │    Assign to:  [Legal Reviewer    ▾]                    │  │
│  │    Mode:       [Any One           ▾]                    │  │
│  │    Strategy:   [Round Robin       ▾]                    │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                             │
│  [+ Add Rule]                                               │
│                                                             │
│  ── Available Fields ─────────────────────────────────────  │
│  Contract: Risk Score, Value, Jurisdiction, Type, ...       │
│  Supplier: Region, Tier                                     │
│  AI: Findings Count, Top Risk                                │
│  User: Role, Department                                      │
└─────────────────────────────────────────────────────────────┘
```

### What the engine receives (hidden from admin)

```json
{
  "and": [
    {">": [{"var": "contract.risk_score"}, 80]},
    {"==": [{"var": "contract.jurisdiction"}, "Germany"]}
  ]
}
```

### Assignment Preview

When conditions are set, show:

```
Assignment Preview
  Matched Rule 1: Risk > 80 AND Country = Germany
  → VP Legal (All Required, Least Loaded)
  → Current candidates: John (5), Lisa (3), Mike (7)
  → Would select: Lisa (least loaded — 3 open tasks)
```

---

## Deliverable 4: Simulator UI

### What it is

A form where administrators enter contract metadata and see the exact approval path.

### View

```
┌─────────────────────────────────────────────────────────────┐
│  Simulator — NDA Review v3                         [Run]   │
├─────────────────────────────────────────────────────────────┤
│  Contract Details:                                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Risk Score:    [92               ]  (0-100)          │   │
│  │ Jurisdiction:  [Germany          ▾]                  │   │
│  │ Contract Type: [MSA              ▾]                  │   │
│  │ Value:         [$1,500,000       ]                   │   │
│  │ Department:    [Procurement      ▾]                  │   │
│  │ Has Redlines:  [Yes  ▾]                              │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  Test Cases: [High Risk NDA ▾]  [Save]  [Load]              │
│                                                             │
│  ── Result ───────────────────────────────────────────────  │
│                                                             │
│  ✅ Matched: High Value Workflow                            │
│                                                             │
│  Stage 1: Intake                    Auto    0.1s            │
│  Stage 2: AI Analysis               Auto    2m              │
│  Stage 3: Legal Review              ⚡ 48h SLA               │
│    ├─ Assigned to: VP Legal (Rule 1 matched)                │
│    ├─ Mode: All Required                                    │
│    ├─ Resolution: Least Loaded → Lisa (3 tasks)             │
│    └─ Escalation: 24h → Legal Manager                       │
│  Stage 4: Finalize                 Auto    0.1s             │
│                                                             │
│  ⏱ Estimated: 50 business hours (US Calendar)               │
│                                                             │
│  ── Why this route? ─────────────────────────────────────  │
│  ✅ Rule 1: Risk 92 > 80 AND Country = Germany → VP Legal   │
│  ❌ Rule 2: Value < $500K? No ($1.5M) → Skipped             │
│  ❌ Rule 3: Low Risk? No (92) → Skipped                     │
│                                                             │
│  [Run with Different Values]                                │
└─────────────────────────────────────────────────────────────┘
```

---

## Deliverable 5: Publishing Flow

### What it is

Publishing is never a simple button. It always shows validation results and impact analysis first.

### View

```
┌─────────────────────────────────────────────────────────────┐
│  Publish NDA Review v3                            [Cancel] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ✅ Validation Score: 100/100                               │
│     No errors. 1 warning (stage without SLA).               │
│                                                             │
│  📊 Impact Analysis                                         │
│     Templates using this workflow:  12                      │
│     Active contracts on current version:  47                │
│     Contracts that will use new version:  3                 │
│     (44 are pinned to previous versions)                    │
│                                                             │
│  ⏱ Effective Date: [2026-07-01           ]                  │
│     (optional — leave blank for immediate)                  │
│                                                             │
│  📝 Change Summary:                                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Added Security Review stage, updated Legal SLA to    │   │
│  │ 48h, added escalation to Legal Manager               │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  [Publish]  [Schedule]  [Save as Draft]                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Deliverable 6: Version Comparison

### What it is

Side-by-side view of two versions showing what changed.

### View

```
┌─────────────────────────────────────────────────────────────┐
│  Comparing v2 → v3                                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Stages:                                                    │
│    + Security Review                  (added)                │
│    ~ Legal Review                     (SLA: 24h → 48h)      │
│    ~ Legal Review                     (escalation added)    │
│                                                             │
│  Rules:                                                     │
│    + Rule 4: Value > $5M → VP Legal   (added)               │
│    ~ Rule 2: Risk threshold           (80 → 75)             │
│                                                             │
│  Health: 96 → 100                    (improved)             │
└─────────────────────────────────────────────────────────────┘
```

---

## Deliverable 7: Workflow Usage Dashboard

### What it is

Aggregated metrics for all published workflows.

### View

```
┌─────────────────────────────────────────────────────────────┐
│  Workflow Analytics — Last 30 Days                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📊 Most Used Workflows                                     │
│  1. NDA Review             1,234 runs   48h avg             │
│  2. Procurement            892 runs     72h avg             │
│  3. Legal Review           567 runs     96h avg             │
│                                                             │
│  ⏱ Performance                                              │
│  Average completion:       52.3h                            │
│  Slowest stage:            Legal Review (28.4h)             │
│  Most rejected stage:      Exec Approval (12.3%)            │
│  Most escalated workflow:  High Value (8.2%)                │
│  Approval bottlenecks:     Legal Review → Exec Approval     │
│                                                             │
│  🚦 Current Status                                           │
│  Active instances:         47                               │
│  Pending approvals:        12                               │
│  SLA breaches:             4.2%                             │
│  Running workflows:        22                               │
│                                                             │
│  📈 Trends (7-day rolling)                                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Completion Time                                     │   │
│  │  ▁▃▄▆▇▆▅▄▃▂▁▁▂▃▄▅▆▇▆▅▄▃▂▁   Current: 52.3h         │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Order

| Day | Deliverable |
|---|---|
| 1-2 | Workflow Pack Library (list, detail, version history, clone) |
| 3-5 | Workflow Designer (stage list, configuration panel, add/reorder/delete) |
| 5-7 | Rule Builder (field/operator/value rows, assignment preview) |
| 7-9 | Simulator UI (input form, results display, explanation tree, test cases) |
| 9-10 | Publishing Flow (validation results, impact analysis, effective date) |
| 10-11 | Version Comparison (side-by-side diff) |
| 11-12 | Workflow Usage Dashboard (metrics, trends, bottlenecks) |
| 12-14 | Integration testing, polish, UX refinement |

## UX Notes (15-20% of sprint)

- Empty states: "No workflows yet. Clone a built-in pack to get started."
- Loading: Skeleton screens for pack library, simulator results
- Validation: Inline validation on stage editor, rule builder
- Keyboard shortcuts: `Ctrl+Enter` to save, `Esc` to close panels
- Error messages: Human-readable, actionable ("Stage name is required" not "Field cannot be null")
- Responsive: Side panels collapse on narrow screens
