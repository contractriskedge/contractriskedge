# Sprint 32.5 — Contract Authoring & Clause Intelligence

**Theme:** Close the gap between AI detection and real contract editing.
**Goal:** Make the Clause Library the source of truth for AI recommendations, enable bulk actions, and provide rich contract authoring.
**Duration:** 2 weeks

---

## Why this sprint exists

The product today detects issues well but doesn't let users fix them efficiently:

| Gap | Symptom | Fix |
|---|---|---|
| AI finds missing clauses | Shows "No Template Available" | Map findings → Clause Library → one-click insert |
| Bulk checkboxes do nothing | Users select items, no action bar appears | Real bulk actions: approve, reject, insert, assign, export |
| Generated contracts are read-only | Users must download DOCX, edit externally, re-upload | Rich in-app authoring with clause insertion, AI rewrite, track changes |
| Placeholder text has no fix button | AI says "Placeholder Governing Law" but no action | One-click replace with approved library clause |

---

## Feature 1: Clause Recommendations

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
Clause Type = GDPR
Status = Published
Jurisdiction = EU
Risk = Critical
```

↓

```
Suggested Clauses (3)

☐ GDPR Standard v5     ★★★★☆  Published  Legal Approved
☐ GDPR EU v2           ★★★★☆  Published  Legal Approved
☐ GDPR UK v1           ★★★☆☆  Draft      Pending Review

[Insert Selected]  [View Full Clause]
```

### Implementation

1. **Backend: `RecommendationEngine.lookup_clauses(finding)`**
   - Accept an AI finding
   - Extract `clause_type`, `jurisdiction`, `risk_level` from finding metadata
   - Query `clause_library` table for matching published clauses
   - Return ranked results (by match score, star rating, version)

2. **Backend: `POST /api/v1/recommendations/resolve`**
   - Body: `{ finding_id, clause_id, action: "insert" | "replace" | "dismiss" }`
   - On "insert": add clause text to document at the appropriate section
   - On "replace": swap placeholder/weak clause text with library clause
   - On "dismiss": mark finding as resolved with a note

3. **Frontend: Finding card update**
   - Replace "No Template Available" with `SuggestedClauses` component
   - Show clause name, rating, status, version
   - "Insert Clause" button triggers API call
   - After insertion, finding transitions to "resolved"

### Acceptance criteria

- [ ] Every AI finding with a `clause_type` returns at least one suggestion if a matching published clause exists
- [ ] "No Template Available" only shows when zero published clauses match
- [ ] One-click insert adds clause text to the document
- [ ] One-click replace swaps placeholder text with approved language
- [ ] Insertion/replacement is recorded in the authoring audit trail

---

## Feature 2: Real Bulk Actions

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

▼ Bulk Actions
  ✓ Approve Selected (3)
  ✗ Reject Selected
  ✎ Accept AI Rewrite
  + Insert Clauses
  👤 Assign To...
  🚫 Mark False Positive
  📥 Export Selected
  🗑 Delete
```

### Implementation

1. **Backend: `POST /api/v1/findings/bulk`**
   - Body: `{ finding_ids: [...], action: "approve" | "reject" | "accept_rewrite" | "insert_clauses" | "assign" | "false_positive" | "export" | "delete" }`
   - Processes all findings in a single transaction
   - Returns `{ succeeded: [...], failed: [...] }`

2. **Frontend: Bulk action bar**
   - Appears when ≥ 1 finding is selected
   Shows count: "3 selected"
   - Dropdown menu with all applicable actions
   - Confirmation dialog for destructive actions (delete, reject)
   - Progress indicator during bulk processing

### Acceptance criteria

- [ ] Bulk actions bar appears when findings are selected
- [ ] Bulk approve/reject works across findings from different reviews
- [ ] Bulk assign opens user picker, assigns all selected
- [ ] Bulk export generates a single report with all selected findings
- [ ] Partial failures are reported per-finding
- [ ] All bulk actions are recorded in the audit trail

---

## Feature 3: Rich Contract Authoring

### Current behavior

Template → Generate → Download DOCX → Edit externally → Re-upload

### Target behavior

Template → Generate → **Author Mode** → Edit in-app

```
┌──────────────────────────────────────────────────────┐
│  📝 Author Mode                                      │
│  ┌──────────────────────────────────────────────────┐│
│  │ [Insert Clause] [Insert Table] [AI Rewrite] [TC] ││
│  ├──────────────────────────────────────────────────┤│
│  │                                                  ││
│  │  MASTER SERVICES AGREEMENT                       ││
│  │                                                  ││
│  │  1. Definitions. [{{Vendor}} means...]           ││
│  │                                                  ││
│  │  2. Payment. Net 30 days from invoice.           ││
│  │                                                  ││
│  │  ╔══════════════════════════════════════════════╗ ││
│  │  ║ [Insert Clause from Library...]              ║ ││
│  │  ╚══════════════════════════════════════════════╝ ││
│  │                                                  ││
│  │  IN WITNESS WHEREOF...                           ││
│  │                                                  ││
│  └──────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────┘
```

### Editor capabilities

| Feature | Implementation |
|---|---|
| Rich text editing | TipTap/ProseMirror-based editor (already partially in use) |
| Clause insertion | Command palette → search Clause Library → insert at cursor |
| Table insertion | Insert/edit tables with header rows |
| Exhibit support | Insert exhibit placeholders with auto-numbering |
| Signature blocks | Insert signature block with party name, title, date fields |
| Variable synchronization | `{{Vendor}}` → all instances update when one changes |
| Track changes | Built-in document diff (existing `VersionDiffViewer`) |
| Comments | Sidebar comments on any selection (existing) |
| Version history | Auto-save on edit, explicit version snapshots (existing) |

### Authoring audit trail

Every edit is recorded:

```
2026-06-28 11:32  Legal Team  Inserted clause "GDPR Standard v5" at §8.3
2026-06-28 11:15  Business    Changed "Net 30" to "Net 45" at §2.1
2026-06-28 10:58  AI          Rewrote §3.2 for clarity (suggestion accepted)
```

### Implementation approach

Rather than building a full Word processor from scratch:

1. **Extend existing TipTap editor** — already used in redline workspace
2. **Add Clause Library integration** — command palette searches published clauses
3. **Add variable awareness** — `{{VARIABLE}}` tokens render as editable fields; changing one updates all
4. **Auto-save** — debounced save to `contract_document_versions` every 30 seconds
5. **Version on explicit save** — user clicks "Save Version" → creates snapshot

### Acceptance criteria

- [ ] Generated contracts open in editable mode
- [ ] Users can type, format, and restructure text
- [ ] Clause Library is accessible from an "Insert Clause" command
- [ ] Inserting a clause adds it to the document and records the action in the audit trail
- [ ] `{{VARIABLE}}` tokens are editable; changing one updates all occurrences
- [ ] Tables can be inserted, edited, and deleted
- [ ] Auto-save preserves work on browser close
- [ ] Version history is accessible from the document workspace

---

## Feature 4: Clause Replacement Workflow

### Current behavior

AI Finding:

> Placeholder Governing Law — "Delaware" may not be appropriate for UK entity

No action available.

### Target behavior

```
Placeholder Governing Law

⚠ Current: "Delaware" — may not be appropriate for UK entity

Suggested Replacements:
  ○ Governing Law (UK) — English law, exclusive jurisdiction of London
  ● Governing Law (EU) — Irish law, CJEU jurisdiction
  ○ Governing Law (US) — Delaware law (current)

[Replace] [Dismiss] [View Comparison]
```

### Implementation

1. **Backend: `POST /api/v1/findings/{id}/replace`**
   - Body: `{ replacement_clause_id: "...", section: "12.1" }`
   - Finds the target text range in the document
   - Replaces with the selected clause text
   - Creates a new document version
   - Records the replacement in the audit trail
   - Resolves the finding

2. **Frontend: Replacement dialog**
   - Shows current text vs. replacement text side-by-side
   - "Replace" button executes the swap
   - "View Comparison" shows redline diff

### Acceptance criteria

- [ ] Findings with `suggested_replacement` show replacement options
- [ ] One-click replace swaps text and creates a new document version
- [ ] Replacement is shown in the version diff viewer
- [ ] Audit trail records who replaced what and why

---

## Feature 5: Variable Synchronization

### Current behavior

Template variables are rendered once at generation time. Changing a value requires regenerating the entire document.

### Target behavior

```
{{Vendor}} = Acme Corp

All 14 occurrences update simultaneously.

┌────────────────────────────────────┐
│  Vendor Name                       │
│  ┌──────────────────────────────┐  │
│  │ Acme Corp                    │  │
│  └──────────────────────────────┘  │
│                                    │
│  Update all 14 occurrences?        │
│                                    │
│  [Update All]  [Update This Only]  │
└────────────────────────────────────┘
```

### Implementation

1. **Variable registry** — on document generation, scan for `{{VARIABLE}}` tokens and build a registry
2. **Variable editor** — clicking any variable opens an inline editor
3. **Propagation** — "Update All" changes every occurrence; "Update This Only" breaks the link
4. **Persistence** — variable values stored in `contract_document_versions.variables` JSONB column

### Acceptance criteria

- [ ] All `{{VARIABLE}}` tokens are detected at generation time
- [ ] Clicking a variable opens an inline editor
- [ ] "Update All" changes every linked occurrence
- [ ] "Update This Only" changes one occurrence and delinks it
- [ ] Variable changes create a new document version

---

## Feature 6: Authoring Audit Trail

### Current behavior

Audit trail exists for review transitions but not for document edits.

### Target behavior

```
Document Activity

Today
  11:32  Legal Team    Inserted clause "GDPR Standard v5" at §8.3
  11:15  Business      Changed "Net 30" to "Net 45" at §2.1
  10:58  AI            Rewrote §3.2 for clarity (accepted)

Yesterday
  16:45  System        Generated from template "MSA v3"
  14:30  Legal Team    Published clause "GDPR Standard v5"
```

### Implementation

Add a new event type to the existing `governance_audit_events` table:

```python
event_type = "document.edited"
entity_type = "document_version"
```

Each edit records:
- `actor_id` — who made the change
- `description` — what changed (e.g., "Inserted clause 'GDPR Standard v5' at §8.3")
- `metadata` — `{ "edit_type": "clause_insert" | "text_change" | "variable_update" | "ai_rewrite", "section": "8.3", "clause_id": "..." }`

### Acceptance criteria

- [ ] Every clause insertion is recorded
- [ ] Every text change over 50 characters is recorded
- [ ] Every variable update is recorded
- [ ] Every AI rewrite accept/reject is recorded
- [ ] Audit trail is visible from the document workspace

---

## Implementation Order

| Week | Features | Dependencies |
|---|---|---|
| Week 1 | Clause Recommendations + Clause Replacement | Existing Clause Library, AI Finding schema |
| Week 1 | Real Bulk Actions | Existing finding API |
| Week 2 | Rich Contract Authoring (basic) | Existing TipTap editor, document version model |
| Week 2 | Variable Sync + Authoring Audit Trail | Authoring implementation |

## What this enables

After Sprint 32.5, the product will feel like a complete CLM:

- AI finds issues **and** fixes them with one click
- Bulk operations work like users expect
- Contracts are editable in-app, not just downloadable
- Every change is tracked and auditable

Then Sprint 33.2 (Workflow Administration) becomes the final layer that orchestrates this polished authoring experience.
