# Sprint 25 Task 3 — Failure Recovery & Resilience Audit

**Date**: 2026-06-05  
**Objective**: Validate failure recovery and resilience across all critical paths

---

## Resilience Score: **72/100**

| Category | Score | Key Strengths | Key Gaps |
|----------|:-----:|---------------|----------|
| LLM/AI Resilience | **55** | 3 retries, rate limit handling, existing run reuse | No fallback provider, no circuit breaker |
| Worker Crash Recovery | **80** | Recovery daemon, cooldown, escalation limits, audit trail | Sync session, no auto-restart |
| Database Resilience | **85** | Connection pool, timeouts, slow query monitoring | No transaction retry |
| Upload/Storage | **70** | Checksum validation, retry chain, state machine | `confirm_storage` missing retry_backoff |
| Idempotency | **75** | 24h TTL, request hash validation, response replay | Cleanup scheduled to wrong task |
| Event Outbox | **80** | Persistent store, dead-letter, TTL cleanup, metrics | No outbox reader/publisher |
| Rate Limiting | **70** | Sliding window, tiered limits, Redis fallback | Per-process in-memory, no per-tenant |
| **Overall** | **72** | | |

---

## Scenario-by-Scenario Analysis

### 1. OpenAI Timeout During Analysis

| Aspect | Assessment |
|--------|-----------|
| **Expected behavior** | Retry with backoff, fallback to alternative model/provider, mark analysis as failed if all retries exhausted |
| **Actual behavior** | 3 retries with exponential backoff (2s-30s) for rate limits only. Non-rate-limit errors (timeout, 500, auth) raise immediately. **No fallback provider** — `_resolve_provider_fallback` in `orchestrator.py` is a no-op. |
| **Recovery mechanism** | Celery autoretry (3 attempts, max 300s). After exhaustion, AI run marked as `FAILED` in DB. Recovery daemon can re-trigger after 30 min. |
| **User-visible impact** | Analysis fails with error. User sees "AI analysis failed" status. Must manually re-analyze. |
| **Data loss risk** | None — AI findings are stored atomically on success. Failed runs leave no partial data. |
| **Gap** | ❌ **No fallback LLM provider configured.** If OpenAI is down, every task retries 3 times then fails. |

### 2. OpenAI 429 Rate Limit

| Aspect | Assessment |
|--------|-----------|
| **Expected behavior** | Detect 429, back off, retry |
| **Actual behavior** | ✅ Handled correctly. `OpenAIProvider.complete()` catches rate limit errors, extracts `Retry-After` header, and raises `AIPolicyViolation` which triggers Celery retry with backoff. |
| **Recovery mechanism** | Celery autoretry with exponential backoff up to 300s. |
| **User-visible impact** | Transient delay. Analysis completes on retry. |
| **Data loss risk** | None. |
| **Rating** | ✅ **Adequate** |

### 3. Worker Crash During Analysis

| Aspect | Assessment |
|--------|-----------|
| **Expected behavior** | Stuck analysis detected by recovery daemon, re-triggered or marked as failed |
| **Actual behavior** | ✅ Recovery daemon (`recover_stuck_workflows`) runs every 5 minutes. Detects AI runs stuck in `processing`/`pending` for >30 min. Re-dispatches via `ingestion_dispatch`. Cooldown of 2h prevents rapid re-triggering. |
| **Recovery mechanism** | Polling-based recovery with priority scoring, cooldown, and max escalation limits. |
| **User-visible impact** | Analysis delayed by up to 30 min (stuck detection threshold) + 5 min (recovery cycle). |
| **Data loss risk** | None — AI findings are stored atomically. A crashed worker leaves no partial data. |
| **Rating** | ✅ **Adequate** |

### 4. PostgreSQL Restart During Analysis

| Aspect | Assessment |
|--------|-----------|
| **Expected behavior** | Connection pool reconnects automatically, query retries |
| **Actual behavior** | ⚠️ Connection pool has `pool_pre_ping=True` which tests connections before use. However, there is **no transaction retry logic** — if a query fails due to connection drop, the operation fails immediately. |
| **Recovery mechanism** | Pool reconnects on next query. No automatic retry of failed transactions. |
| **User-visible impact** | Request fails with 500. User must retry. |
| **Data loss risk** | Low — transactions are atomic. A failed transaction leaves no partial data. |
| **Gap** | ❌ **No transaction retry.** PostgreSQL `SerializationFailure` or `AdminShutdown` errors are not retried. |

### 5. MinIO Unavailable During Upload

| Aspect | Assessment |
|--------|-----------|
| **Expected behavior** | Upload fails, retry with backoff, user can re-upload |
| **Actual behavior** | ✅ Upload pipeline has retry chain (3 attempts, 300s backoff) for most tasks. Checksum validation ensures data integrity. `confirm_storage` verifies object existence. |
| **Recovery mechanism** | User can retry via `POST /uploads/{id}/retry`. Ingestion state machine allows retry from `FAILED` back to `UPLOADED`. |
| **User-visible impact** | Upload fails with error. User sees "Upload failed" status. Can retry. |
| **Data loss risk** | None — file is stored in MinIO before pipeline starts. If MinIO is down, upload itself fails. |
| **Gap** | ❌ **`confirm_storage` task is missing `retry_backoff`** — unlike all other ingestion tasks. A transient error here causes permanent failure. |

### 6. Browser Refresh During Analysis

| Aspect | Assessment |
|--------|-----------|
| **Expected behavior** | Analysis continues in background. User sees progress on reload. |
| **Actual behavior** | ✅ Analysis runs in Celery worker, independent of browser session. Status polling (`GET /reviews/{id}/status`) returns progress. Review is created atomically on completion. |
| **Recovery mechanism** | Status endpoint returns `progress` field. Frontend polls with adaptive interval (2s base, exponential backoff, stops on terminal states). |
| **User-visible impact** | Brief progress reset on reload, then resumes from server-side state. |
| **Data loss risk** | None. |
| **Rating** | ✅ **Adequate** |

### 7. WebSocket Disconnect

| Aspect | Assessment |
|--------|-----------|
| **Expected behavior** | Reconnect with backoff, fall back to polling, replay missed events |
| **Actual behavior** | ✅ Exponential backoff (1s-30s), max 10 attempts. Adaptive polling falls back to 5s (disconnected) or 10s (reconnecting). On reconnect, sequence IDs prevent stale event replay. |
| **Recovery mechanism** | `useWorkspaceRealtime` hook with debounced invalidation (500ms) and stale event rejection. |
| **User-visible impact** | Brief delay in realtime updates. Polling fills the gap. |
| **Data loss risk** | None — all state is server-side. |
| **Rating** | ✅ **Well-designed** |

### 8. Network Interruption

| Aspect | Assessment |
|--------|-----------|
| **Expected behavior** | API calls fail, frontend shows error state, retry on reconnection |
| **Actual behavior** | ✅ React Query retries failed queries (default: 3 retries). Error states display "Retry" button. Cache serves stale data during offline periods. |
| **Recovery mechanism** | React Query `gcTime` keeps cached data for 5+ minutes. On reconnection, queries refetch automatically (refetchOnReconnect). |
| **User-visible impact** | Stale data shown during outage. "Failed to load" errors if no cache. Auto-recovers on reconnection. |
| **Data loss risk** | None — all mutations use idempotency keys. |
| **Rating** | ✅ **Adequate** |

---

## Top Remediation Items

| # | Issue | Severity | Effort | Fix |
|---|-------|----------|--------|-----|
| 1 | **No LLM provider fallback** | **HIGH** | 2-3h | Configure secondary provider (e.g., Anthropic Claude) in `settings.ai_provider_fallback_order`. Implement actual provider switching in `orchestrator.py._resolve_provider_fallback()`. |
| 2 | **`confirm_storage` missing `retry_backoff`** | **HIGH** | 15min | Add `@CeleryTaskRetry.retry_backoff=True, retry_backoff_max=300` to `confirm_storage_task`. |
| 3 | **Idempotency cleanup scheduled to wrong task** | **MEDIUM** | 10min | Fix beat schedule in `celery_app.py` line 93: change task from `recover_stuck_workflows` to `cleanup_expired_idempotency_records`. |
| 4 | **No transaction retry for deadlocks** | **MEDIUM** | 1-2h | Add retry decorator for `SerializationFailure` and `AdminShutdown` PostgreSQL errors in the session factory. |
| 5 | **SLA check creates new event loop** | **MEDIUM** | 30min | Refactor `sla_check.py` to use `WorkerAsyncHelper` instead of creating a new event loop. |
| 6 | **No circuit breaker for OpenAI** | **LOW** | 1-2h | Add circuit breaker pattern in `OpenAIProvider` — after N consecutive failures, stop calling for M seconds. |

---

## Production Readiness Score: **72/100**

| Category | Score | Assessment |
|----------|:-----:|------------|
| Failure Detection | **85** | Slow query monitoring, worker heartbeats, SLA breach detection, recovery daemon |
| Failure Recovery | **70** | Retry chains exist but gaps in LLM fallback and storage confirmation |
| Data Durability | **90** | Idempotency keys, event outbox, atomic transactions, checksum validation |
| User Experience | **75** | Error states, retry buttons, polling fallback, stale cache |
| Operational Tooling | **60** | No circuit breakers, no auto-scaling, no transaction retry |

### What's Working Well
- Recovery daemon with cooldown, escalation limits, and audit trail
- Idempotency keys with 24h TTL and response replay
- Event outbox with dead-letter queue and auto-replay
- Connection pool with statement/lock/idle-transaction timeouts
- Adaptive polling with WebSocket awareness
- Checksum + magic byte validation on uploads
- Rate limiting with Redis fallback

### What Needs Improvement
1. **LLM fallback provider** — single point of failure
2. **`confirm_storage` retry_backoff** — missing configuration
3. **Idempotency cleanup task** — wrong task scheduled
4. **Transaction retry** — no deadlock recovery
5. **Circuit breaker for OpenAI** — no protection against sustained failures
