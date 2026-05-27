# Frontend Runtime Risk Register

**Date:** May 26, 2026
**Status:** Active — post Mini Sprint 6.1
**Owner:** Platform Engineering

---

## Overview

After Mini Sprint 6.1 (Realtime Stabilization + Session Governance), the frontend runtime has moved from "prototype with realtime attached" to "distributed runtime participant." The remaining risks are no longer architectural holes — they are advanced-scale problems that emerge under enterprise load (20+ tabs, 50+ concurrent reviews, multi-tenant SSO, global teams).

---

## Risk Inventory

### R1 — Cross-Tab Coordination (Medium)

**Problem:** Multiple browser tabs poll independently. Each tab maintains its own WebSocket connection, polling intervals, and query cache. Under enterprise usage (20+ tabs), this multiplies backend traffic linearly with open tabs.

**Current state:** No `BroadcastChannel` or `SharedWorker` usage. Each tab is fully independent.

**Impact:** Infrastructure cost grows linearly with tab count. Backend sees N× traffic where N = tabs open.

**Proposed solution (future):**
- `BroadcastChannel` for cross-tab poll coordination
- One "leader tab" maintains the WebSocket + polling
- Leader broadcasts cache updates to followers via `BroadcastChannel`
- Followers suppress their own polling while leader is active
- Fallback: if leader tab closes, election protocol promotes a follower

**Trigger for implementation:** When average active sessions per user exceeds 3 concurrent tabs, or when backend traffic analysis shows >40% duplicate requests across sessions.

---

### R2 — Memory Leaks in Long Sessions (Medium)

**Problem:** Enterprise users may keep sessions open for days. The following accumulate:
- Debounce timers in `useWorkspace.ts` (`invalidationTimers` Map)
- Event sequence tracking in `useWorkspace.ts` (`lastEventSequences` Map)
- Coalescer entries in `requestCoalescer.ts` (entries Map)
- Connection ownership registry in `realtime.ts` (`connectionOwnership` Map)
- TanStack Query cache (gcTime: 5 min)

**Current state:** No client-side memory profiling. No `performance.memory` monitoring. Maps are bounded by active reviews but not by time.

**Impact:** Over multi-day sessions, memory grows monotonically. On memory-constrained devices (older laptops, low-end Chromebooks), this causes performance degradation or tab crashes.

**Mitigation in place:**
- Coalescer has periodic cleanup (30s interval, removes entries >30s old with no callers)
- TanStack Query has gcTime (5 min) — stale queries are garbage collected
- Connection ownership registry is bounded by unique owner IDs (one per route)

**Remaining gaps:**
- `invalidationTimers` Map in `useWorkspace.ts` is never cleaned up for stale review IDs
- `lastEventSequences` Map in `useWorkspace.ts` only clears on unmount — if a user navigates away without unmounting, entries persist
- No upper bound on the number of tracked review workspaces

**Proposed solution:**
- Add LRU eviction to `invalidationTimers` and `lastEventSequences` (max 50 entries)
- Add periodic sweep of stale entries (>30 min since last update)
- Add `performance.memory` monitoring with console warning at 80% heap usage

---

### R3 — Replay Volume Growth (Medium)

**Problem:** The WebSocket replay cursor persists the last sequence ID in localStorage. After extended use, a disconnected client may need to replay thousands of missed events on reconnect. The current implementation replays all missed events without volume control.

**Current state:** `last_sequence_id` is sent on reconnect. Server replays all events since that sequence. No client-side limit on replay volume.

**Impact:** After long disconnects (laptop sleep, network outage), replay can deliver hundreds or thousands of events. This causes:
- UI freeze during replay processing
- Cache invalidation storms (each event triggers debounced invalidation)
- Excessive bandwidth usage on metered connections

**Proposed solution:**
- Add `max_replay_events` parameter to reconnect auth message (default: 100)
- If replay exceeds limit, server returns a "snapshot" event instead of individual events
- Client: batch replay events and process in microtask chunks (requestAnimationFrame)
- Client: skip cache invalidation for replayed events older than a threshold

---

### R4 — Query Cache Growth (Medium)

**Problem:** TanStack Query caches all query results for 5 minutes (gcTime). Under heavy use (50+ reviews, each with findings, redlines, comments, risk breakdown, versions), the cache can grow to thousands of entries.

**Current state:** gcTime is 5 min globally. No per-query-type gcTime differentiation. No cache size limits.

**Impact:** Memory grows with number of unique query keys. For power users reviewing 50+ contracts in a session, cache can hold 500+ query results simultaneously.

**Proposed solution:**
- Differentiate gcTime by data type:
  - Reference data (clause library, benchmarks): 30 min
  - Active review data (status, findings): 5 min
  - Historical/detail data (versions, audit logs): 2 min
- Add `maxQueries` limit to QueryClient (e.g., 500 entries)
- Implement cache compression for large response payloads

---

### R5 — Event Ordering Under Concurrency (Medium-High)

**Problem:** The WebSocket uses monotonic sequence ID tracking (highest seen), not strict ordering. Under concurrent event production (multiple workers emitting events for the same review), events can arrive out of order. The current `isStaleEvent` check rejects events with `sequence_id <= lastSeen`, which means out-of-order events are **silently dropped**.

**Current state:** `isStaleEvent` in `useWorkspace.ts` drops any event with `sequence_id <= lastSeq`. If event A (seq 5) arrives after event B (seq 6), event A is dropped. This is correct for stale rejection but wrong for out-of-order delivery.

**Impact:** Under high concurrency, events can be lost. A status transition from "processing" (seq 5) to "completed" (seq 6) arriving in order is fine. But if "processing" (seq 5) arrives after "completed" (seq 6), the "processing" event is dropped — which is correct behavior since we already have the newer state.

**However:** If the events contain different information (e.g., "finding.created" seq 5 and "review.status_changed" seq 6), dropping seq 5 means the finding is lost.

**Proposed solution:**
- Change sequence tracking to be per-event-type, not global
- Or: use causal ordering (vector clocks) instead of global sequence IDs
- Or: separate control events (status changes) from data events (findings, comments) into different sequence streams

---

### R6 — Frontend Observability Gaps (Medium)

**Problem:** There is no client-side telemetry or metrics reporting. The server has observability (logs, metrics, traces), but the frontend runtime is a black box. When users report issues, there's no way to know:
- Was the WebSocket connected?
- How many reconnects occurred?
- Were there polling storms?
- What was the cache hit rate?
- Were there coalescer conflicts?

**Current state:** Metrics exist in `realtime.ts` and `requestCoalescer.ts` but are only accessible via `getRealtimeMetrics()` / `getCoalescerMetrics()` — there's no reporting endpoint or dashboard.

**Impact:** Debugging frontend issues requires reproducing locally. Production issues are invisible.

**Proposed solution:**
- Add a `/api/v1/frontend/metrics` endpoint that accepts client-side metrics
- Periodically report (every 5 min, or on error):
  - Connection state, reconnect count, visibility pauses
  - Coalescer hit rate, active entries
  - Query cache size, active queries
  - Memory usage (if available)
- Add a frontend diagnostics panel (admin-only) that displays live metrics

---

### R7 — Browser Sleep/Wakeup Edge Cases (Medium)

**Problem:** The Visibility API pause/resume handles tab switching, but browser sleep/wakeup has additional edge cases:
- **Timer inflation:** After sleep, `setTimeout` and `setInterval` timers are compressed — all pending callbacks fire immediately on wakeup
- **WebSocket timeout:** The server may have already cleaned up the connection during sleep
- **Token expiry:** If the session was sleeping past token expiry, the resumed connection may fail auth
- **localStorage staleness:** The replay cursor in localStorage may be stale after sleep

**Current state:** `pause()` closes the WebSocket on visibility change. `resume()` calls `connect()`. But:
- The proactive token refresh timer may fire during sleep (timer inflation)
- The heartbeat interval may fire multiple times on wakeup
- The replay cursor may be hours stale after long sleep

**Proposed solution:**
- On wakeup: check token expiry before reconnecting
- On wakeup: debounce reconnect (wait 1s for all timers to settle)
- On wakeup: check if replay cursor is >15 min old — if so, request snapshot instead of replay
- Add `document.wakeup` / `visibilitychange` coalescing (ignore rapid fire events)

---

## Risk Response Plan

| Risk | When to Act | Owner | Priority |
|------|-------------|-------|----------|
| R5 — Event ordering | Before multi-worker deployment | Backend | High |
| R6 — Observability | Before customer beta | Frontend | Medium |
| R2 — Memory leaks | Before 24/7 enterprise use | Frontend | Medium |
| R3 — Replay volume | Before global team usage | Backend+Frontend | Medium |
| R4 — Cache growth | Monitor in staging | Frontend | Low |
| R1 — Cross-tab coordination | When avg tabs/user > 3 | Frontend | Low |
| R7 — Sleep/wakeup | Monitor in beta | Frontend | Low |

---

## Metrics to Track

| Metric | Source | Warning Threshold |
|--------|--------|-------------------|
| Coalescer hit rate | `getCoalescerMetrics()` | < 0.1 (too low — not enough sharing) |
| Reconnect rate | `getRealtimeMetrics().totalReconnects` | > 5 per hour |
| Visibility pauses | `getRealtimeMetrics().visibilityPauses` | Track trend |
| Duplicate preventions | `getRealtimeMetrics().duplicatePreventions` | > 0 (indicates stale component mounts) |
| Query cache size | TanStack Query `queryCache.queries.length` | > 500 |
| Memory usage | `performance.memory?.usedJSHeapSize` | > 80% of heap limit |
