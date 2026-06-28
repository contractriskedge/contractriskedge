# Sprint 33.2 — Workflow Administration UI

**Theme:** Administrator product — not workflow logic, but workflow configuration.
**Foundation:** ✅ Sprint 33.1 frozen. No engine changes unless defects found.
**Duration:** 2 weeks
**After this:** Sprint 33.3 (Operations) → Sprint 34 (Production Readiness)

---

## Design Principle

Administrators should never have to edit JSON or think about database tables. Every workflow operation — create, edit, simulate, validate, publish, version, compare, archive, and monitor — should be achievable through the UI.

**No drag-and-drop canvas, no BPMN editor, no fancy animations.** Large enterprise products use structured form-based designers because they're easier to validate, version, diff, and maintain.

---

## Implementation Order

Dependency chain drives the order:

```
Week 1                    Week 2
─────────                 ─────────
Pack Library              Simulator UI (depends on Rule Builder)
Workflow Details Page     Publishing Flow (depends on Validation)
Workflow Designer         Version Comparison (depends on Versioning)
Rule Builder              Usage Dashboard (depends on Execution)
```

---

## Week 1 Deliverables

---

### 1. Workflow Pack Library

Browse, search, filter, clone, and manage workflow packs.

**Views:**

```
┌─────────────────────────────────────────────────────────────┐
│  Workflow Packs                                   [+ New]  │
├─────────────────────────────────────────────────────────────┤
│  🔍 Search packs...                    [All Categories ▾]  │
│                                                             │
│  ┌────────────────────────┐  ┌────────────────────────┐    │
│  │ ⭐ NDA Review     🔵   │  │ Procurement     🔵     │    │
│  │ v3 · Published          │  │ v2 · Published          │    │
│  │ Used 1,234x · ✅ 100/100│  │ Used 892x · ✅ 96/100  │    │
│  │ [Clone] [Edit] [▸ ▸ ▸]│  │ [Clone] [Edit] [▸ ▸ ▸]│    │
│  └────────────────────────┘  └────────────────────────┘    │
│                                                             │
│  ┌────────────────────────┐  ┌────────────────────────┐    │
│  │ Sales Contract   🟡   │  │ 📋 High Value          │    │
│  │ v1 · Draft             │  │ Built-in · v2           │    │
│  │ ⚠ 2 warnings · 72/100 │  │ [Clone] [Preview]       │    │
│  │ [Edit] [Validate] [Pub]│  │                        │    │
│  └────────────────────────┘  └────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

**Actions per pack:**
- Clone (create tenant copy of built-in or existing pack)
- Duplicate (copy within same tenant)
- Export (JSON/YAML for cross-environment migration)
- Import (validate before importing)
- Archive / Restore
- Favorite (⭐)

**Version history (flyout):**

```
NDA Review — Versions
┌──────┬──────────┬──────────┬──────────┬─────────┬──────────┐
│  Ver │ Status   │ Published│  By      │  Score  │ Stages  │
├──────┼──────────┼──────────┼──────────┼─────────┼──────────┤
│  v3  │ 🔵 Pub  │ 06-15    │ JSmith   │ 100/100 │ 5       │
│  v2  │ 🔵 Pub  │ 05-20    │ JSmith   │ 96/100  │ 5       │
│  v1  │ 📦 Arch │ 04-01    │ LWang    │ 88/100  │ 4       │
└──────┴──────────┴──────────┴──────────┴─────────┴──────────┘
[Compare v2 vs v3]  [Clone v2]
```

---

### 2. Workflow Details Page

A summary page for each workflow pack, similar to Contract Details. Becomes the "home page" of every workflow.

```
┌─────────────────────────────────────────────────────────────┐
│  NDA Review v3                                   [Edit]   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Overview                                                   │
│  Status:    🔵 Published · v3 · Health: 96/100              │
│  Owner:     Legal Team                                       │
│  Category:  Legal                                            │
│  Created:   2026-01-15 by JSmith                             │
│  Published: 2026-06-15 by JSmith                             │
│  Last Used: Yesterday (12 instances)                         │
│                                                             │
│  Usage                                                      │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐   │
│  │ Running  │ Completed│ Avg Dur  │ Avg App  │ SLA      │   │
│  │ 47       │ 1,234    │ 48h      │ 18.2h    │ 4.2%     │   │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘   │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐   │
│  │ Templates│ Contracts│ Failed   │ Cancelled│ Sim Runs │   │
│  │ 12       │ 183      │ 23       │ 8        │ 156      │   │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘   │
│                                                             │
│  Version                                                    │
│  Current: v3 (Published) · Draft: v4 (in progress)          │
│  [Compare v2 vs v3]  [View All Versions]                    │
│                                                             │
│  Quick Actions                                              │
│  [Designer] [Simulator] [Validate] [Publish] [Clone]        │
│  [Export] [Archive] [Impact Analysis] [Audit]               │
│                                                             │
│  ── Templates Using This Workflow ────────────────────────  │
│  • Standard NDA (v2)                                        │
│  • International NDA (v3)                                    │
│  • Employee NDA (v1)                                        │
│                                                             │
│  ── Timeline ─────────────────────────────────────────────  │
│  06-28  JSmith  Published v3                                │
│  06-27  LWang   Updated Legal Review SLA (24h → 48h)       │
│  06-25  JSmith  Validated v3 — 100/100                      │
│  06-22  System  Simulation run (High Risk NDA test case)    │
│  06-20  LWang   Created v3 (draft)                          │
│  05-15  System  Archived v2 (superseded by v3)              │
│  04-01  LWang   Published v2                                │
│  02-15  LWang   Published v1                                │
└─────────────────────────────────────────────────────────────┘
```

---

### 3. Workflow Designer

A structured, step-by-step workflow builder. Not a free-form canvas.

```
┌─────────────────────────────────────────────────────────────┐
│  Edit: NDA Review v3                              [Save]   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Workflow Stages                                           │
│                                                             │
│  ┌── 1 ──────────────────────────────────────────────────┐  │
│  │  ↑ ↓  Intake           (Start)             [Edit] [X] │  │
│  └────────────────────────────────────────────────────────┘  │
│       │                                                     │
│       ▼                                                     │
│  ┌── 2 ──────────────────────────────────────────────────┐  │
│  │  ↑ ↓  AI Analysis      (Automatic)           [Edit] [X] │  │
│  └────────────────────────────────────────────────────────┘  │
│       │                                                     │
│       ▼                                                     │
│  ┌── 3 ──────────────────────────────────────────────────┐  │
│  │  ↑ ↓  Legal Review     (Approval · ⚡ 48h)    [Edit] [X] │  │
│  └────────────────────────────────────────────────────────┘  │
│       │                                                     │
│       ├──→ ┌── 3a ───────────────────────────────────────┐  │
│       │    │  Escalate to Legal Manager  (24h) [Edit] [X] │  │
│       │    └──────────────────────────────────────────────┘  │
│       ▼                                                     │
│  ┌── 4 ──────────────────────────────────────────────────┐  │
│  │  ↑ ↓  Finalize         (Automatic)           [Edit] [X] │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                             │
│  [+ Add Stage]  [+ Add Escalation]                          │
│                                                             │
│  ═════════════════════════════════════════════════════════  │
│  Stage Configuration                                        │
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

**Behaviors:**
- Click a stage → side panel opens with full configuration
- "Add Stage" appends to the end
- ↑↓ arrows for reordering
- Stage type determines available configuration fields
- Validation indicator at top (green/red)
- SLA calendar picker references Business Calendars

---

### 4. Rule Builder

Visual condition builder that generates JSON Logic automatically. Supports nested groups.

```
┌─────────────────────────────────────────────────────────────┐
│  Routing Rules — Legal Review Stage                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─ Rule 1 ──────────────────────────────────────────────┐  │
│  │  IF                                                     │  │
│  │    ┌─ ALL ──────────────────────────────────────────┐  │  │
│  │    │  ┌──────────┐  ┌──────┐  ┌──────────┐          │  │  │
│  │    │  │ Risk     │  │ >    │  │ 80       │          │  │  │
│  │    │  │ Score    │  │      │  │          │          │  │  │
│  │    │  └──────────┘  └──────┘  └──────────┘          │  │  │
│  │    │  AND                                           │  │  │
│  │    │  ┌─ ANY ───────────────────────────────────┐   │  │  │
│  │    │  │  ┌──────────┐  ┌──────┐  ┌──────────┐  │   │  │  │
│  │    │  │  │Jurisdict-│  │ =    │  │ Germany  │  │   │  │  │
│  │    │  │  │ion       │  │      │  │          │  │   │  │  │
│  │    │  │  └──────────┘  └──────┘  └──────────┘  │   │  │  │
│  │    │  │  OR                                     │   │  │  │
│  │    │  │  ┌──────────┐  ┌──────┐  ┌──────────┐  │   │  │  │
│  │    │  │  │Jurisdict-│  │ =    │  │ France   │  │   │  │  │
│  │    │  │  │ion       │  │      │  │          │  │   │  │  │
│  │    │  │  └──────────┘  └──────┘  └──────────┘  │   │  │  │
│  │    │  └─────────────────────────────────────────┘   │  │  │
│  │    └────────────────────────────────────────────────┘  │  │
│  │                                                         │  │
│  │  THEN                                                   │  │
│  │    Assign to:  [VP Legal          ▾]                    │  │
│  │    Mode:       [All Required      ▾]                    │  │
│  │    Strategy:   [Least Loaded      ▾]                    │  │
│  │                                                         │  │
│  │  [+ Add Condition]  [+ Add Group (ALL/ANY)]             │  │
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
│  ── Assignment Preview ───────────────────────────────────  │
│  Matched Rule 1: Risk 92 > 80 AND Country = Germany         │
│  → VP Legal (All Required, Least Loaded)                    │
│  → Candidates: John (5 tasks), Lisa (3 tasks), Mike (7)     │
│  → Selected: Lisa (least loaded — 3 open tasks)             │
│  → Avg completion: 1.2 days · On-time rate: 94%             │
└─────────────────────────────────────────────────────────────┘
```

**Engine receives (hidden from admin):**

```json
{
  "and": [
    {">": [{"var": "contract.risk_score"}, 80]},
    {"or": [
      {"==": [{"var": "contract.jurisdiction"}, "Germany"]},
      {"==": [{"var": "contract.jurisdiction"}, "France"]}
    ]}
  ]
}
```

**Available fields come from Metadata Providers:**
- Contract: Risk Score, Value, Jurisdiction, Type, Department, Region, Has Redlines
- Supplier: Region, Tier
- AI: Findings Count, Top Risk
- User: Role, Department

---

## Week 2 Deliverables

---

### 5. Simulator UI

One of the flagship features. Input contract metadata → see exact approval path.

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
│  Test Cases: [High Risk NDA ▾]  [Save Current]  [Load]     │
│                                                             │
│  ═════════════════════════════════════════════════════════  │
│  Result                                                     │
│                                                             │
│  ✅ Selected: High Value Workflow (v3)                      │
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

### 6. Publishing Flow

Never a simple button. Always shows validation + impact analysis first.

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

### 7. Version Comparison

Compare business concepts, not JSON. Highlight additions, changes, removals.

```
┌─────────────────────────────────────────────────────────────┐
│  Comparing v2 → v3                                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Stages:                                                    │
│    ┌────────────────────────────────────────────────────┐   │
│    │ v2:  Intake → AI → Legal → Finalize                │   │
│    │ v3:  Intake → AI → Legal → Security → Finalize     │   │
│    │                                                   │   │
│    │  + Security Review                  (added)        │   │
│    │  ~ Legal Review                     (SLA 24→48h)   │   │
│    │  ~ Legal Review                     (escalation +)  │   │
│    └────────────────────────────────────────────────────┘   │
│                                                             │
│  Rules:                                                     │
│    + Rule 4: Value > $5M → VP Legal   (added)               │
│    ~ Rule 2: Risk threshold           (80 → 75)             │
│    - Rule 3: Low Risk Auto-Approve    (removed)             │
│                                                             │
│  Health: 96 → 100                    (improved)             │
└─────────────────────────────────────────────────────────────┘
```

---

### 8. Workflow Usage Dashboard

Actionable operational metrics, not just charts.

```
┌─────────────────────────────────────────────────────────────┐
│  Workflow Analytics — Last 30 Days                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📊 Volume
│  ┌──────────────┬──────────────┬──────────────┬──────────┐  │
│  │ Running      │ Completed    │ Avg Duration │ Pending  │  │
│  │ 47           │ 1,234        │ 52.3h        │ 12       │  │
│  └──────────────┴──────────────┴──────────────┴──────────┘  │
│                                                             │
│  ⏱ Performance                                              │
│  ┌──────────────┬──────────────┬──────────────┬──────────┐  │
│  │ Avg Approval │ Avg Stage    │ Slowest      │ Fastest  │  │
│  │ 18.2h        │ 6.4h         │ Legal 28.4h  │ AI 2.3m  │  │
│  └──────────────┴──────────────┴──────────────┴──────────┘  │
│                                                             │
│  🚦 Quality                                                 │
│  ┌──────────────┬──────────────┬──────────────┬──────────┐  │
│  │ Rejected %   │ Escalated %  │ Auto-Approved│ SLA Breach│  │
│  │ 12.3%        │ 8.2%         │ 23.4%        │ 4.2%     │  │
│  └──────────────┴──────────────┴──────────────┴──────────┘  │
│                                                             │
│  🔥 Top Bottlenecks                                         │
│  1. Exec Approval   (avg 18.2h · 12.3% rejection)          │
│  2. Legal Review    (avg 28.4h · 8.2% breach rate)          │
│  3. Security Review (avg 6.1h  · 3.1% breach rate)          │
│                                                             │
│  📈 Most Used Workflows                                     │
│  1. NDA Review             1,234 runs   48h avg             │
│  2. Procurement            892 runs     72h avg             │
│  3. Legal Review           567 runs     96h avg             │
│                                                             │
│  📉 Trends (7-day rolling)                                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Completion Time                                     │   │
│  │  ▁▃▄▆▇▆▅▄▃▂▁▁▂▃▄▅▆▇▆▅▄▃▂▁   Current: 52.3h         │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## UX Notes (15-20% of sprint)

- **Empty states:** "No workflows yet. Clone a built-in pack to get started."
- **Loading:** Skeleton screens for pack library, simulator results
- **Validation:** Inline validation on stage editor, rule builder
- **Keyboard shortcuts:** `Ctrl+Enter` save, `Esc` close panels, `↑↓` reorder
- **Error messages:** Human-readable, actionable ("Stage name is required" not "Field cannot be null")
- **Responsive:** Side panels collapse on narrow screens
- **Consistent terminology:** "Publish" not "Deploy", "Stage" not "Step", "Rule" not "Condition"

---

## What NOT to build

- Drag-and-drop canvas designer
- BPMN editor
- Fancy animations
- Real-time collaborative editing
- These can be added later if customers request them
