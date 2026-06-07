# Sprint 23 Task 3.2A — Review Data Integrity Audit

**Date**: 2026-06-05  
**Objective**: Verify consistency between reviews, findings, redlines, risk scores, and AI analysis results  
**Priority**: Higher than building new UI — findings must reach the workspace

---

## Executive Summary

| Metric | Value | Verdict |
|--------|-------|---------|
| Total reviews | 83 | — |
| Reviews WITH actual findings/redlines | **26** | ✅ Real reviews |
| Reviews with counter-only (test fixtures) | **57** | ⚠️ Test data |
| Total review_findings | 157 | ✅ |
| Total review_redlines | 142 | ✅ |
| Total ai_findings | 157 | ✅ |
| Total ai_redlines | 142 | ✅ |
| Orphan findings/redlines | **0** | ✅ |
| Reviews without AI analysis | **0** | ✅ |
| Asymmetric (findings xor redlines) | **0** | ✅ |
| NULL risk_score with findings | **0** | ✅ |

---

## Finding 1: 57 Reviews Are Test Fixtures (NOT a Bug — Expected)

**57 reviews** have `finding_count=3` and `redline_count=1` hardcoded from test fixtures (`tests/conftest.py` line 232) but **zero actual records** in `review_findings` / `review_redlines`.

### Why This Is Expected

The test fixtures create minimal review records for testing the review lifecycle, state machine, and API endpoints. They don't populate the full `review_findings` and `review_redlines` tables because:

1. That would require running the full AI pipeline
2. The test fixtures only need the `contract_reviews` row to exist
3. The counters (`finding_count=3`, `redline_count=1`) are set to non-zero values so tests can verify count-based logic

### Root Cause Confirmed

```python
# backend/tests/conftest.py line 232
finding_count=3, redline_count=1,
```

These are **fixture defaults**, not a production bug.

---

## Finding 2: 26 Real Reviews Have Correct Data (GOOD)

The **26 real reviews** (created by the AI worker pipeline) have:

| Metric | Value |
|--------|-------|
| Total review_findings | 157 (matches ai_findings exactly) |
| Total review_redlines | 142 (matches ai_redlines exactly) |
| finding_count matches actual COUNT(review_findings) | ✅ |
| redline_count matches actual COUNT(review_redlines) | ✅ |
| No orphan records | ✅ |
| No asymmetric reviews | ✅ |

### Sample Real Reviews

```
review_id                             findings  redlines  status
b44dd973-2eec-4e20-be59-81d95a60fcd9    10        7        finalized
3e8af191-7db2-4a42-8b67-cfa5b0af3f14    10        7        closed
e20d31ff-a54e-477c-aa1e-36f472fbb442    10        7        finalized
7c384eb2-1731-4cba-9f04-898bb7a71efd     9        7        closed
4ed5d824-8cfb-42a4-9803-3f3c6ec7fac3     8        7        escalated
```

The AI import chain works correctly:
```
AI Run completes
  → ai_findings / ai_redlines populated (157 + 142)
  → _populate_review() copies to review_findings / review_redlines
  → finding_count = len(ai_findings) ✓
  → redline_count = len(ai_redlines) ✓
```

---

## Finding 3: No Data Integrity Issues Found

| Check | Result |
|-------|--------|
| Orphan review_findings | **0** — all have parent reviews |
| Orphan review_redlines | **0** — all have parent reviews |
| Orphan ai_findings | **0** — all linked to runs |
| Orphan ai_redlines | **0** — all linked to runs |
| Reviews with findings but no redlines | **0** |
| Reviews with redlines but no findings | **0** |
| Reviews with NULL risk_score + findings | **0** |
| Reviews without AI analysis | **0** |

---

## Finding 4: The `get_review()` Method Recomputes Counts (GOOD DESIGN)

The `get_review()` method in `service.py` (line 149) **recomputes** `finding_count` and `redline_count` from the actual `review_findings` / `review_redlines` tables every time a single review is fetched:

```python
cnt = await self.review_repo.session.execute(
    select(sa_func.count()).select_from(ReviewFinding).where(
        ReviewFinding.review_id == review_id,
        ReviewFinding.tenant_id == self.tenant_id,
    )
)
review.finding_count = cnt.scalar() or 0
```

This means:
- **Review detail view** (`GET /reviews/{id}`) → always shows correct counts ✅
- **Review list view** (`GET /reviews`) → uses stored counter (may show 3 for test fixtures) ⚠️
- **Review workspace** → uses `get_review()` → correct counts ✅

---

## Remediation Plan

### Option A: Recompute Counts on List (Recommended)

The `get_reviews()` list endpoint should recompute counts from actual DB records, same as `get_review()` does. This would fix the discrepancy for both test fixtures and any real edge cases.

**File**: `backend/app/domains/review/repository.py`  
**Method**: `list_reviews()`  
**Change**: Add subquery to compute actual `finding_count` and `redline_count` instead of using stored columns.

### Option B: Accept Test Fixture Behavior (Low Risk)

Since:
1. The workspace (`get_review()`) always shows correct counts
2. Test fixtures don't affect production data
3. The list endpoint showing `finding_count=3` for test fixtures is cosmetic

This can be accepted as-is. The real reviews (26) have correct data.

### Option C: Clean Test Fixtures from DB

Run a one-time SQL update to set `finding_count=0, redline_count=0` for reviews that have no actual records:

```sql
UPDATE contract_reviews
SET finding_count = 0, redline_count = 0
WHERE NOT EXISTS (SELECT 1 FROM review_findings rf WHERE rf.review_id = contract_reviews.review_id);
```

This would make the list view accurate immediately.

---

## Conclusion

**The data integrity audit found no production bugs.** The 57 reviews with mismatched counters are test fixtures from `tests/conftest.py`, not real reviews. The 26 real reviews have fully correct data with:

- 157 findings matching between `ai_findings` and `review_findings`
- 142 redlines matching between `ai_redlines` and `review_redlines`
- Zero orphans
- Zero asymmetric records
- Zero NULL risk scores with findings

**Recommended action**: Apply **Option C** (clean test fixture counters) for immediate accuracy, and **Option A** (recompute counts on list) for long-term correctness.
