# Contract Naming Strategy — Field-Level Audit

**Date**: 2026-06-05  
**Objective**: Identify the canonical display field for contract names across all surfaces

---

## 1. Database Schema

### Source of Truth: `upload_sessions.filename`

The `contract_reviews` table has **no** `name`, `title`, or `document_name` column. The review's display name comes from `upload_sessions.filename`, joined at query time.

| Table | Column | Type | Populated By | Contains |
|-------|--------|------|-------------|----------|
| `upload_sessions` | `filename` | `text` | User upload | Original uploaded filename (e.g., `NDA-2024-ABC-Corp.pdf`) |
| `upload_sessions` | `metadata` | `jsonb` | AI pipeline | `risk_score`, `last_analysis_run_id` — **no title/vendor/counterparty** |
| `contract_reviews` | — | — | — | No name column exists |
| `contract_reviews` | `metadata` | `jsonb` | AI pipeline | `risk_score`, `last_analysis_run_id` — **no title/vendor** |

### Key Finding: No AI Extraction of Contract Metadata

The AI pipeline (`ai/service.py`) stores findings, redlines, and risk scores, but does **not** extract:
- **Contract title** (e.g., "Master Service Agreement")
- **Vendor/counterparty name** (e.g., "ABC Corp")
- **Agreement type** (e.g., "NDA", "MSA", "SOW")
- **Parties** (e.g., ["ContractEdge Inc.", "ABC Corp"])

The `upload_sessions.metadata` JSONB column contains only `risk_score` and `last_analysis_run_id` — no enrichment data.

---

## 2. Current Display Fields Per Surface

### Contracts Repository (`/contracts`)

| UI Field | Backend Source | Value |
|----------|---------------|-------|
| **Contract Name** | `ContractSummary.name` = `filename` or `"Untitled"` | `completed-contract.pdf` |
| **Vendor** | `ContractSummary.vendor` = `""` (hardcoded empty) | (empty) |
| **Agreement Type** | `ContractSummary.contractType` = `"contract"` (hardcoded) | `contract` |

**File**: `backend/app/domains/contracts/router.py` lines 45-47
```python
self.name = filename or "Untitled"
self.vendor = ""
self.contractType = "contract"
```

### Review Dashboard (`/review-dashboard`)

| UI Field | Backend Source | Value |
|----------|---------------|-------|
| **Contract Name** | `ContractRecord.name` = `filename` or `"Untitled"` | `completed-contract.pdf` |
| **Type** | `ContractRecord.contractType` = `"contract"` | `contract` |

**File**: `frontend/components/review/ReviewDashboard.tsx` — uses `contract.name`

### Review Queue (`/review` view)

| UI Field | Backend Source | Value |
|----------|---------------|-------|
| **Contract Name** | `review.document_name` \|\| `review.original_filename` | `completed-contract.pdf` |

**File**: `frontend/components/review/ReviewQueue.tsx` line 142:
```typescript
const name = review.document_name || review.original_filename || "";
```

### Review Workspace (title bar)

| UI Field | Backend Source | Value |
|----------|---------------|-------|
| **Title** | `review.document_name` \|\| `review.original_filename` \|\| `"Review Detail"` | `completed-contract.pdf` |

**File**: `frontend/components/review/ReviewWorkspace.tsx` line 221

### ContractSummary (inside workspace)

| UI Field | Backend Source | Value |
|----------|---------------|-------|
| **Document** | `review.document_name` \|\| `review.original_filename` \|\| review_id | `completed-contract.pdf` |

**File**: `frontend/components/review/ContractSummary.tsx` line 85-86

---

## 3. The Naming Chain

```
User uploads file
  → upload_sessions.filename = "NDA-2024-ABC-Corp.pdf"
  → contract_reviews created with upload_id reference
  → Repository joins: SELECT u.filename, ... FROM contract_reviews r JOIN upload_sessions u
  → review._document_filename = filename (set in repository)
  → Service serializes: "document_name": filename, "original_filename": filename
  → Frontend receives: review.document_name = "NDA-2024-ABC-Corp.pdf"
  → Contracts API: ContractSummary.name = filename
```

All surfaces ultimately display the **same value**: `upload_sessions.filename`.

---

## 4. Gap: No Semantic Contract Name

The filename is the **only** name available. There is no:
- AI-extracted contract title
- User-editable display name
- Vendor name
- Agreement type classification

This means:
- `completed-contract.pdf` — 83 reviews all show this name (test data)
- Real uploads would show the original PDF filename (e.g., `MSA-ABC-Corp-signed.pdf`)
- No surface can show "Master Service Agreement" or "ABC Corp" because that data doesn't exist

---

## 5. Recommendations

### Short-Term (No Backend Changes)

| Surface | Current Field | Recommended | Rationale |
|---------|--------------|-------------|-----------|
| **Contracts Repository** | `c.name` (filename) | ✅ Keep `c.name` | Only name available. Shows filename. |
| **Review Dashboard** | `contract.name` (filename) | ✅ Keep `contract.name` | Consistent with Contracts Repository. |
| **Review Queue** | `document_name` \|\| `original_filename` | ✅ Keep as-is | Falls back correctly. |
| **Review Workspace** | `document_name` \|\| `original_filename` | ✅ Keep as-is | Shows filename, falls back to review_id. |
| **ContractSummary** | `document_name` \|\| `original_filename` | ✅ Keep as-is | Consistent. |

**All surfaces are already consistent.** They all ultimately display `upload_sessions.filename`. No changes needed.

### Medium-Term (Add AI Extraction)

Add a new AI extraction step that populates `upload_sessions.metadata` with:

```json
{
  "contract_title": "Master Service Agreement",
  "vendor_name": "ABC Corp",
  "counterparty": "ABC Corp",
  "agreement_type": "MSA",
  "parties": ["ContractEdge Inc.", "ABC Corp"],
  "effective_date": "2024-01-01",
  "governing_law": "Delaware"
}
```

This would enable:

| Surface | New Field | Source |
|---------|-----------|--------|
| **Contracts Repository** | Vendor column | `metadata->>'vendor_name'` |
| **Contracts Repository** | Agreement Type | `metadata->>'agreement_type'` |
| **Review Dashboard** | Vendor column | `metadata->>'vendor_name'` |
| **Review Workspace** | Contract title in header | `metadata->>'contract_title'` |
| **ContractSummary** | Vendor, Counterparty | `metadata->>'vendor_name'`, `metadata->>'counterparty'` |

### Long-Term (Schema Change)

Add a `display_name` column to `contract_reviews` that can be:
1. Auto-populated from AI extraction (`contract_title`)
2. Manually overridden by users
3. Falls back to `upload_sessions.filename`

```sql
ALTER TABLE contract_reviews ADD COLUMN display_name text;
```

---

## 6. Current State Summary

| Surface | Field Used | Shows Filename? | Shows Vendor? | Shows Title? | Status |
|---------|-----------|----------------|---------------|-------------|--------|
| Contracts Repository | `c.name` | ✅ Yes | ❌ No | ❌ No | ✅ Consistent |
| Review Dashboard | `contract.name` | ✅ Yes | ❌ No | ❌ No | ✅ Consistent |
| Review Queue | `document_name` | ✅ Yes | ❌ No | ❌ No | ✅ Consistent |
| Review Workspace | `document_name` | ✅ Yes | ❌ No | ❌ No | ✅ Consistent |
| ContractSummary | `document_name` | ✅ Yes | ❌ No | ❌ No | ✅ Consistent |

**All 5 surfaces are consistent** — they all show the same `upload_sessions.filename`. There is no naming discrepancy across surfaces. The limitation is that **no surface can show vendor, title, or agreement type** because the AI pipeline doesn't extract that data yet.
