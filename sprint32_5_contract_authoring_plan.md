# Sprint 32.5 — Clause Intelligence & Recommendation Engine

**Theme:** Close the gap between AI detection and actionable clause resolution.
**Duration:** 2 weeks
**After this sprint:** Sprint 33 (Workflow Administration) → Sprint 34 (Rich Authoring)

---

## Why this scope

The original plan bundled four products into one sprint. This version scopes to **six focused deliverables** that unblock Workflow Administration:

| Deliverable | Why now | Why not later |
|---|---|---|
| AI → Clause Library mapping | "No Template Available" is actively confusing users | Blocks every AI finding from being actionable |
| One-click Insert / Replace | Users need to act on recommendations | Without this, Clause Library feels disconnected |
| Bulk Actions | Checkboxes exist but do nothing | Visible UX gap that erodes trust |
| Clause Comparison | Lawyers need before/after before replacing | Without this, one-click replace is too risky |
| Recommendation Engine (platform service) | Multiple consumers (AI Review, Templates, Negotiation) | Will be harder to extract later |
| Clause Analytics & Usage | Legal Ops needs adoption metrics | Data is already there, just not exposed |

**Removed from this sprint:** Rich in-browser authoring (TipTap, tables, exhibits, variable sync). That moves to Sprint 34 after Workflow Administration is complete.

---

## Deliverable 1: AI → Clause Library Mapping

### Current behavior

AI Finding:

> Missing GDPR Compliance Clause

↓

"No Template Available"

### Target behavior

AI Finding:

> Missing GDPR Compliance Clause

↓

Recommendation Engine queries Clause Library

```
Suggested Clauses (3)

  ☐ GDPR Standard v7     96%  ★★★★★  Published  Used 412x
  ☐ GDPR EU v2           88%  ★★★★☆  Published  Used 189x
  ☐ GDPR UK v1           72%  ★★★☆☆  Draft      Used 23x

[Preview] [Insert] [Replace] [Dismiss]
```

### Implementation

1. **Backend: `RecommendationEngine.lookup_clauses(finding, tenant_context)`**
   - Extract `clause_type`, `jurisdiction`, `industry`, `risk_level` from finding metadata
   - Query `clause_library` for matching published clauses
   - Score each match (see Deliverable 5 for scoring model)
   - Exclude deprecated/superseded/archived clauses
   - Return top-5 ranked results

2. **Backend: `POST /api/v1/recommendations/resolve`**
   - Body: `{ finding_id, clause_id, action: "insert" | "replace" | "dismiss" }`
   - On "insert": add clause text to document, create new version
   - On "replace": swap target text with clause text, create new version with diff
   - On "dismiss": mark finding resolved with audit note

3. **Frontend: Finding card update**
   - Replace "No Template Available" with `SuggestedClauses` component
   - Show: clause name, match score, rating, health status, usage count
   - Actions: Preview (modal), Insert, Replace, Dismiss

### Acceptance criteria

- [ ] Every AI finding with a `clause_type` returns suggestions if matching published clauses exist
- [ ] "No Template Available" only shows when zero published clauses match
- [ ] Deprecated/superseded clauses are excluded from results
- [ ] Match score is displayed as a percentage
- [ ] Clicking Preview opens a read-only modal with full clause text
- [ ] Insert/Replace creates a new document version

---

## Deliverable 2: One-click Insert / Replace with Preview

### Current behavior

Finding says "Placeholder Governing Law" but there's no fix button.

### Target behavior

```
Placeholder Governing Law

⚠ Current: "Delaware" — may not be appropriate for UK entity

Suggested Replacements:
  ○ Governing Law (UK) — English law, exclusive jurisdiction of London Courts
  ● Governing Law (EU) — Irish law, subject to CJEU jurisdiction

[Preview]  [Compare]  [Replace]  [Dismiss]
```

Clicking **Compare** shows:

```
┌─────────────────────┬─────────────────────────┐
│ Current (§12.1)     │ Suggested               │
├─────────────────────┼─────────────────────────┤
│ This Agreement shall│ This Agreement shall be │
│ be governed by the  │ governed by the laws of │
│ laws of the State of│ England and Wales. The  │
│ Delaware.           │ parties submit to the   │
│                     │ exclusive jurisdiction  │
│                     │ of the London Courts.   │
├─────────────────────┼─────────────────────────┤
│                     │ [Accept Replacement]    │
└─────────────────────┴─────────────────────────┘
```

### Implementation

1. **Backend: `POST /api/v1/findings/{id}/preview-replacement`**
   - Body: `{ replacement_clause_id: "..." }`
   - Returns `{ current_text, suggested_text, section, diff_html }`

2. **Backend: `POST /api/v1/findings/{id}/replace`**
   - Body: `{ replacement_clause_id: "...", section: "12.1" }`
   - Replaces text in document, creates new version
   - Records replacement in audit trail
   - Resolves the finding

3. **Frontend: Comparison dialog**
   - Side-by-side view: current vs suggested
   - Inline diff highlighting
   - "Accept Replacement" button
   - "Cancel" returns to finding card

### Acceptance criteria

- [ ] Every finding with `suggested_replacement` shows a "Compare" button
- [ ] Comparison shows current text vs suggested text side-by-side
- [ ] Diff is highlighted inline
- [ ] Accepting a replacement creates a new document version
- [ ] Replacement is recorded in the audit trail

---

## Deliverable 3: Bulk Actions

### Current behavior

```
☑ Finding 1
☑ Finding 2
☑ Finding 3

[Bulk] → nothing happens
```

### Target behavior

```
☑ Finding 1
☑ Finding 2
☑ Finding 3

▼ Bulk Actions (3 selected)
  ✓ Approve Selected
  ✗ Reject Selected
  ✓ Resolve Selected
  ✎ Accept AI Rewrite
  + Insert Clauses
  👤 Assign To...
  🚫 Mark False Positive
  📥 Export Selected
```

### Actions

| Action | Behavior |
|---|---|
| Approve | Sets finding status to `approved`, records audit event |
| Reject | Sets finding status to `rejected`, requires reason |
| Resolve | Sets finding status to `resolved` (for duplicates, intentional accepts) |
| Accept AI Rewrite | Applies the AI-suggested rewrite to each finding |
| Insert Clauses | Opens clause picker, inserts selected clause for each finding |
| Assign To | Opens user picker, assigns all selected to chosen user |
| Mark False Positive | Sets finding status to `false_positive` |
| Export | Generates CSV/PDF report of selected findings |

### Implementation

1. **Backend: `POST /api/v1/findings/bulk`**
   - Body: `{ finding_ids: [...], action: "approve" \| "reject" \| "resolve" \| "accept_rewrite" \| "insert_clauses" \| "assign" \| "false_positive" \| "export", params: {...} }`
   - Processes all findings in a single transaction
   - Returns `{ succeeded: [{id, status}], failed: [{id, error}] }`

2. **Frontend: Bulk action bar**
   - Appears when ≥ 1 finding is selected
   - Shows count: "3 selected"
   - Dropdown menu with all applicable actions
   - Confirmation dialog for destructive actions
   - Progress indicator during bulk processing

### Acceptance criteria

- [ ] Bulk actions bar appears when findings are selected
- [ ] All 8 actions work correctly
- [ ] Partial failures are reported per-finding
- [ ] Every bulk action is recorded in the audit trail
- [ ] Bulk export generates a valid CSV/PDF

---

## Deliverable 4: Clause Comparison

### What it is

A dedicated comparison view that lets users see **exactly what changes** before accepting a clause replacement.

### Why it's separate from Insert/Replace

Insert/Replace is the action. Comparison is the **review step** before the action. Lawyers will not replace contract text without seeing the diff first.

### Implementation

1. **Backend: Text diff engine**
   - Compute word-level diff between current text and replacement text
   - Return structured diff data (insertions, deletions, unchanged segments)
   - Store diff in the document version metadata

2. **Frontend: Comparison view**
   - Reuse existing `VersionDiffViewer` component
   - Left pane: current text
   - Right pane: replacement text
   - Highlighted insertions (green) and deletions (red)
   - "Accept" button at bottom

### Acceptance criteria

- [ ] Comparison view opens from any finding with a suggested replacement
- [ ] Word-level diff is displayed with insertions in green, deletions in red
- [ ] Unchanged text is shown in normal weight
- [ ] Accepting navigates back to the finding and triggers the replace action

---

## Deliverable 5: Recommendation Engine (Platform Service)

### Architecture

```
                    ┌─────────────────────────────┐
                    │   Recommendation Engine      │
                    │                              │
Input:              │  ┌───────────────────────┐   │  Output:
context             │  │  Scoring Pipeline      │   │  Ranked clauses
entity              │  │                        │   │  with scores
tenant              │  │  1. Type Match (30%)   │   │  and explanations
document            │  │  2. Jurisdiction (20%) │   │
                    │  │  3. Industry (15%)     │   │
                    │  │  4. Risk Level (15%)   │   │
                    │  │  5. Usage Rate (10%)   │   │
                    │  │  6. Freshness (10%)    │   │
                    │  └───────────────────────┘   │
                    └─────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────────────────┐
                    │      Consumers               │
                    │                              │
                    │  • AI Review (Sprint 32.5)   │
                    │  • Template Generation (exists)│
                    │  • Negotiation (future)      │
                    │  • Workflow (future)         │
                    │  • Policy Engine (future)    │
                    └─────────────────────────────┘
```

### Scoring model

Each candidate clause gets a score 0-100 based on:

| Factor | Weight | Source |
|---|---|---|
| Clause type match | 30% | Finding metadata vs clause category |
| Jurisdiction match | 20% | Finding jurisdiction vs clause jurisdiction |
| Industry match | 15% | Tenant industry vs clause industry tags |
| Risk level alignment | 15% | Finding severity vs clause risk level |
| Usage / acceptance rate | 10% | How often this clause is used and accepted |
| Freshness (version recency) | 10% | Newer versions score higher |

### Explanation output

```json
{
  "clause_id": "cl_gdpr_v7",
  "score": 96,
  "explanation": [
    {"factor": "Jurisdiction", "match": true, "weight": 20, "score": 20},
    {"factor": "Industry", "match": true, "weight": 15, "score": 15},
    {"factor": "Contract Type", "match": true, "weight": 30, "score": 30},
    {"factor": "Risk Level", "match": true, "weight": 15, "score": 15},
    {"factor": "Usage Rate", "value": "82% acceptance", "weight": 10, "score": 8},
    {"factor": "Freshness", "value": "Published 2026-03", "weight": 10, "score": 8}
  ]
}
```

### Service interface

```python
class RecommendationEngine:
    async def recommend_clauses(
        self,
        *,
        tenant_id: str,
        context: RecommendationContext,
        limit: int = 5,
    ) -> list[ScoredClause]:
        ...

@dataclass
class RecommendationContext:
    clause_type: Optional[str] = None
    jurisdiction: Optional[str] = None
    industry: Optional[str] = None
    risk_level: Optional[str] = None
    contract_type: Optional[str] = None
    document_text: Optional[str] = None
    finding_id: Optional[str] = None
```

### Acceptance criteria

- [ ] Recommendation Engine is a standalone service, not coupled to AI Review
- [ ] Scoring considers all 6 factors
- [ ] Each result includes a breakdown explanation
- [ ] Engine can be called from AI Review, Template Generation, and API
- [ ] Deprecated/superseded clauses are filtered out before scoring

---

## Deliverable 6: Clause Analytics & Usage Metrics

### What it exposes

For every clause in the Clause Library:

```
GDPR Standard v7

Health: ✅ Published (v7) · Supersedes v4, v5, v6

Usage:
  Templates:      321  (in 12 active templates)
  Contracts:    5,412  (inserted into generated contracts)
  Acceptance:     69%  (accepted vs rejected when AI-suggested)
  AI Suggestions: 812  (times recommended by AI)
  AI Acceptance:  87%  (of those, accepted by users)

Trend:
  Last 30 days: +42 insertions, 91% acceptance rate
  Last 90 days: +156 insertions, 85% acceptance rate

Top Users:
  Legal Team:    2,341 insertions
  Procurement:   1,892 insertions
  Compliance:    1,179 insertions
```

### Why this matters

Legal Operations teams need adoption metrics to:
- Identify which clauses are most valuable
- Retire clauses that are always rejected
- Negotiate better terms based on usage data
- Prove ROI of the Clause Library to leadership

### Implementation

1. **Backend: Analytics queries**
   - Aggregate from `contract_document_versions`, `governance_audit_events`, `clause_library`
   - Cache computed metrics (refresh daily or on-demand)
   - Expose via `GET /api/v1/clause-analytics/{clause_id}`

2. **Frontend: Analytics panel**
   - Tab on the Clause Detail page
   - Usage summary cards
   - Trend chart (30/90 day)
   - Top users table

### Acceptance criteria

- [ ] Every published clause has an analytics view
- [ ] Usage counts (templates, contracts) are accurate
- [ ] Acceptance rate is computed from audit events
- [ ] AI suggestion/accepted counts are tracked
- [ ] 30/90 day trends are charted
- [ ] Analytics data is cached for performance

---

## What this sprint does NOT include

| Feature | Moved to | Rationale |
|---|---|---|
| Rich in-browser authoring (TipTap, tables, exhibits) | Sprint 34 | Would delay Workflow Administration |
| Variable synchronization | Sprint 34 | Part of rich authoring |
| Auto-save / version snapshots | Sprint 34 | Part of rich authoring |
| Track changes UI | Sprint 34 | Part of rich authoring |
| Comments on document selections | Sprint 34 | Part of rich authoring |
| Word Content Controls / Salesforce / SAP metadata | Future | Requires variable sync foundation first |

---

## Sequencing after this sprint

```
Sprint 32.5  →  Sprint 33  →  Sprint 34
(Clause       (Workflow     (Rich Authoring)
 Intelligence)  Administration)
```

This sequence:
1. Fixes the visible UX gaps (no more "No Template Available", bulk actions work)
2. Builds the Workflow Administration layer on a stable foundation
3. Delivers rich authoring last, when the platform is fully orchestrated
