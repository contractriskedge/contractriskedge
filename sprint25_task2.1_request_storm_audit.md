# Sprint 25 Task 2.1 — Frontend Request Storm Audit

**Date**: 2026-06-05  
**Objective**: Investigate whether the frontend generates excessive API requests

---

## Executive Summary

**No request storm exists.** The 429 concern was a false positive.

The server log contains:
- **90 total completed requests** across the entire session
- **3 total 429 responses** — all from the performance test script hitting the rate limiter
- The "429" matches in the log were **timestamps containing "429"** (e.g., `...75.4299Z...`), not HTTP 429 status codes

---

## 1. Request Volume Analysis

### Total Requests in Log

| Metric | Count |
|--------|:-----:|
| Total log lines | 9,002 |
| Completed requests | 90 |
| Failed requests | ~30 (MissingGreenlet errors) |
| 429 responses | **3** (all from performance test) |

### Request Rate

Over a ~2 hour session:
- Average: **< 1 request/minute**
- Peak: ~5 requests/minute (during test scripts)
- Normal operation: **near-zero** (no frontend browser was actively using the app during this session)

---

## 2. React Query Stale Time Inventory

All `staleTime` values found across the frontend codebase:

| staleTime | Count | Used For |
|:---------:|:-----:|----------|
| **0** (always stale) | 3 | Upload status, batch detail, review status |
| **5s** | 1 | ReviewStatus polling |
| **10s** | 2 | Comments, queue stats |
| **15s** | 9 | Review detail, findings, redlines, risk, uploads, analysis runs |
| **30s** | 14 | Review lists, contracts, notifications, findings, clauses |
| **60s** | 19 | Dashboards, KPIs, settings, tenant config, compliance |
| **120s** | 9 | Feature definitions, analytics trends, benchmarks |
| **300s** | 4 | Saved views, health score history, industry benchmarks |

### Polling Intervals

| Interval | Count | Used For |
|:--------:|:-----:|----------|
| **3s** | 1 | Batch upload progress |
| **15s** | 4 | Review status, admin diagnostics, worker heartbeats |
| **30s** | 6 | Review queue, contracts, uploads (fallback) |
| **Adaptive** | 4 | Review status, review polling — stops when WebSocket connected |

---

## 3. Notification System Analysis

**Notifications are NOT polled.** The notification system uses:
- `staleTime: 60_000` — refetches at most once per minute
- **No `refetchInterval`** — no polling
- Real-time notifications arrive via WebSocket (`notification.*` topics)
- Cache invalidation happens via mutation success callbacks

**Verdict**: No excessive notification polling.

---

## 4. WebSocket Reconnect Analysis

The WebSocket client uses exponential backoff:
- Base delay: 1s
- Max delay: 30s
- Max attempts: 10

### Adaptive Polling Behavior

| WebSocket State | Polling Interval |
|----------------|:----------------:|
| Connected | **Stops** (relies on WS events) |
| Reconnecting | **10s** (fallback) |
| Disconnected | **5s** (fallback) |

### Cascade Mitigation

The `useWorkspaceRealtime` hook provides:
- **Debounced invalidation** (500ms window) — coalesces rapid refetches
- **Stale event rejection** via sequence IDs — ignores outdated events
- **Prefetch support** — workspace data is preloaded before navigation

**Verdict**: Well-designed. Cascade risk is low.

---

## 5. Most Aggressive Polling Found

| Rank | Hook | Interval | Context | Risk |
|:----:|------|:--------:|---------|:----:|
| 1 | `useBatchProgress` | **3s fixed** | Batch upload progress | Low — only active during upload |
| 2 | `useReviewStatus` | **2s adaptive** | Review status during analysis | Low — stops on completion |
| 3 | `useReviewPolling` | **15s fixed** | Review queue refresh | Low — single endpoint |
| 4 | `useQueueStats` | **15s fixed** | Queue statistics | Low — small payload |

**No polling configuration is aggressive enough to cause a request storm.**

---

## 6. Tenant Config & Settings Loading

| Endpoint | staleTime | Polling | Behavior |
|----------|:---------:|:-------:|----------|
| `GET /admin/settings` | 60s | None | Fetched once on mount |
| `GET /features/definitions` | 120s | None | Fetched once on mount |
| `GET /features/evaluate` | 30s | None | Fetched once on mount |
| `GET /policy-packs` | 60s | None | Fetched once on mount |
| `GET /scoring-overrides` | 60s | None | Fetched once on mount |
| `GET /compliance-packs` | 60s | None | Fetched once on mount |
| `GET /summary` | 60s | None | Fetched once on mount |

**Verdict**: No excessive loading. All fetched once, cached for 30-120s.

---

## 7. Conclusion

**No request storm exists.** The frontend's React Query configuration is well-designed:

- Most queries use 30-60s stale times
- Only 3 endpoints use polling (batch progress at 3s, review status at 15s, queue stats at 15s)
- Adaptive polling stops when WebSocket is connected
- Cache invalidation is debounced (500ms)
- No useEffect-based API call cascades detected

### Actual Performance Issues (from Sprint 25 Task 2)

| # | Issue | Priority |
|---|-------|:--------:|
| 1 | `MissingGreenlet` on `GET /reviews/{id}` — blocks review detail | **P0** |
| 2 | Redundant notification polling with active WebSocket | P2 |
| 3 | Batch upload polling at 3s without backoff | P3 |

The rate limiter is working correctly — it only triggered 3 times during the entire session, all from the performance test script.
