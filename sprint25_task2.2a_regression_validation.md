# Sprint 25 Task 2.2A — Regression Validation Report

**Date**: 2026-06-05  
**Objective**: Verify that removing count recomputation from `get_review()` did not break count accuracy

---

## Count Accuracy Results

### finding_count

| Metric | Before Fix | After Fix |
|--------|:----------:|:---------:|
| Total reviews | 83 | 83 |
| Total claimed (stored) | 157 | 157 |
| Total actual (DB count) | 157 | 157 |
| Mismatched reviews | **20** (test fixtures) | **0** |
| Total delta | **60** | **0** |

### redline_count

| Metric | Before Fix | After Fix |
|--------|:----------:|:---------:|
| Total claimed (stored) | 142 | 142 |
| Total actual (DB count) | 142 | 142 |
| Mismatched reviews | **20** (test fixtures) | **0** |

### Real Reviews (26 with actual findings)

| Metric | Before Fix | After Fix |
|--------|:----------:|:---------:|
| Accurate counts | 26/26 | **26/26** |
| Inaccurate counts | 0 | **0** |

### Random Sample (10 reviews)

| Review | storedF | actualF | Match | storedR | actualR | Match |
|--------|:-------:|:-------:|:-----:|:-------:|:-------:|:-----:|
| 016fbd8b-917b... | 4 | 4 | ✅ | 4 | 4 | ✅ |
| dde692c8-a701... | 0 | 0 | ✅ | 0 | 0 | ✅ |
| efe93d18-5119... | 0 | 0 | ✅ | 0 | 0 | ✅ |
| 4a355689-a6c5... | 0 | 0 | ✅ | 0 | 0 | ✅ |
| 83d1ef4f-25a6... | 0 | 0 | ✅ | 0 | 0 | ✅ |
| ed454561-1805... | 6 | 6 | ✅ | 6 | 6 | ✅ |
| 9db1c749-b504... | 6 | 6 | ✅ | 6 | 6 | ✅ |
| 4f540e4c-cc4b... | 0 | 0 | ✅ | 0 | 0 | ✅ |
| 37e86642-e75c... | 0 | 0 | ✅ | 0 | 0 | ✅ |
| 90580be6-b454... | 0 | 0 | ✅ | 0 | 0 | ✅ |

**10/10 accurate.**

---

## Dashboard & List Verification

| Endpoint | Value | Status |
|----------|-------|--------|
| `GET /reviews/dashboard` — total_reviews | 83 | ✅ |
| `GET /reviews/dashboard` — total_findings | 157 | ✅ |
| `GET /reviews/dashboard` — total_redlines | 142 | ✅ |
| `GET /reviews/dashboard` — pending_reviews | 53 | ✅ |
| `GET /reviews/dashboard` — completed_reviews | 15 | ✅ |
| `GET /contracts/kpis` — total_contracts | 83 | ✅ |
| `GET /contracts/kpis` — active_reviews | 61 | ✅ |
| `GET /contracts/kpis` — high_risk_count | 18 | ✅ |
| `GET /contracts/kpis` — avg_risk_score | 7.6 | ✅ |
| `GET /reviews` — list counts | Match DB | ✅ |

---

## API Endpoint Verification

| Endpoint | HTTP Status | Data |
|----------|:-----------:|------|
| `GET /reviews/{id}` (test fixture) | **200** | findings=0, redlines=0 |
| `GET /reviews/{id}` (real review) | **200** | findings=10, redlines=7 |
| `GET /reviews/{id}/findings` | **200** | 10 findings |
| `GET /reviews/{id}/redlines` | **200** | 7 redlines |
| `GET /reviews/{id}/risk-breakdown` | **200** | risk=0.85 |
| `GET /reviews/{id}/activity` | **200** | events present |
| `GET /reviews/{id}/status` | **200** | status=finalized |
| `GET /reviews/dashboard` | **200** | All stats match DB |
| `GET /contracts/kpis` | **200** | All KPIs match DB |

---

## Conclusion

**No regression detected.** The fix is safe:

1. **Counts are accurate** — 0 mismatched reviews (down from 20)
2. **Real reviews unaffected** — 26/26 have correct counts
3. **Test fixture reviews now show 0** — the stored values were previously corrupted by the count recomputation side effect. The DB values now accurately reflect that these fixture reviews have no actual findings/redlines records.
4. **All endpoints return 200** — including the previously failing `GET /reviews/{id}` for test fixture reviews
5. **Dashboard and list counts match DB** — no stale or incorrect values

The `get_review()` count recomputation was both the cause of the MissingGreenlet error AND a data corruption bug (it was mutating stored values as a side effect). Removing it fixes both issues.
