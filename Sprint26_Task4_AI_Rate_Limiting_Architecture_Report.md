# Sprint 26 Task 4 — AI Rate Limiting Architecture Report

**Date:** 2026-06-05  
**Author:** Production Readiness Audit  
**Status:** Design Phase — No Implementation Yet  

---

## Phase 1: AI Endpoint Audit

### Complete Inventory of AI-Consuming Endpoints

| # | Endpoint | Service Method | AI Operation | Model | Est. Cost/Call | Auth | Permission | Current Rate Limit |
|---|----------|---------------|--------------|-------|---------------|------|-----------|-------------------|
| 1 | `POST /api/v1/ai/analyze` | `AIService.analyze()` → `analyze_contract_task` | Risk analysis + redlines | `gpt-4o` | **~$0.12** (1 risk + up to 7 redlines) | JWT | `contracts:write` | Default (100/min) |
| 2 | `POST /api/v1/ai/copilot/suggest` | `ReviewCopilotService.suggest()` | AI suggestion | `gpt-4o` | **~$0.013** | JWT | `contracts:read` | Default (100/min) |
| 3 | `POST /api/v1/reviews/{id}/re-analyze` | `ReviewService.re_analyze()` → `analyze_contract_task` | Full re-analysis | `gpt-4o` | **~$0.12** (same as #1) | JWT | `contracts:write` | Default (100/min) |
| 4 | `POST /api/v1/ingestion/upload` | `IngestionService.upload()` → Celery pipeline → embeddings | Document embeddings | `text-embedding-3-large` | **~$0.03** (500p contract) | JWT | `contracts:write` | 30/min (upload limit) |
| 5 | `POST /api/v1/search/` | `SearchService.search()` → `HybridRetrievalEngine` → embedding | Query embedding | `text-embedding-3-large` | **~$0.000007** | JWT | `contracts:read` | Default (100/min) |
| 6 | `GET /api/v1/search/` | `SearchService.search()` → embedding | Query embedding | `text-embedding-3-large` | **~$0.000007** | JWT | `contracts:read` | Default (100/min) |
| 7 | `GET /api/v1/search/clauses` | `SearchService.search_clauses()` → embedding | Query embedding | `text-embedding-3-large` | **~$0.000007` | JWT | `contracts:read` | Default (100/min) |
| 8 | `POST /api/v1/reviews/{id}/analyze` | `ReviewService.analyze()` → `analyze_contract_task` | Full analysis | `gpt-4o` | **~$0.12** | JWT | `contracts:write` | Default (100/min) |

### AI Cost Profile

| Operation | Model | Input Tokens | Output Tokens | Cost/Op | Monthly Cost at 1K ops |
|-----------|-------|-------------|--------------|---------|----------------------|
| Risk analysis (50 chunks) | `gpt-4o` | ~8,000 | ~2,000 | **$0.040** | $40 |
| Redline gen per finding (×7 max) | `gpt-4o` | ~2,500 | ~500 | **$0.011** each | $77 |
| **Full analysis (1 risk + 7 redlines)** | `gpt-4o` | ~25,500 | ~5,500 | **~$0.118** | **$118** |
| Copilot suggest | `gpt-4o` | ~3,000 | ~500 | **$0.013** | $13 |
| Query embedding | `text-embedding-3-large` | ~50 | — | **~$0.000007** | $0.007 |
| Document embedding (500p) | `text-embedding-3-large` | ~250K | — | **~$0.033** | $33 |

### Worst-Case Cost Scenario (No Rate Limiting)

```
1 user × 100 req/min (default rate limit) × $0.118/analysis = $11.80/min
= $708/hour  ← from a single user
= $16,992/day ← worst case
```

---

## Phase 2: Recommended Rate Limits

### Per-User Limits

| Endpoint | Limit | Window | Rationale |
|----------|-------|--------|-----------|
| `POST /ai/analyze` | **5** | 1 minute | Full analysis is expensive ($0.12/call). 5/min = $0.60/min max |
| `POST /reviews/{id}/re-analyze` | **3** | 1 minute | Re-analysis is same cost but less frequent need |
| `POST /reviews/{id}/analyze` | **5** | 1 minute | Same as analyze |
| `POST /ai/copilot/suggest` | **20** | 1 minute | Cheap ($0.013) but can be spammed. 20/min = $0.26/min |
| `POST /search/` | **60** | 1 minute | Embedding cost is negligible. Limit by search abuse potential |
| `GET /search/` | **120** | 1 minute | Read-only, cheap embeddings |
| `GET /search/clauses` | **60** | 1 minute | Same as search |

### Per-Tenant Limits

| Endpoint | Limit | Window | Rationale |
|----------|-------|--------|-----------|
| `POST /ai/analyze` | **50** | 1 hour | Tenant-wide ceiling. 50/hr × $0.12 = $6/hr max |
| `POST /reviews/{id}/re-analyze` | **20** | 1 hour | Re-analysis is a fraction of total |
| `POST /reviews/{id}/analyze` | **50** | 1 hour | Same as analyze |
| `POST /ai/copilot/suggest` | **200** | 1 hour | Cheap, but tenant-level cap prevents runaway |
| `POST /search/` | **600** | 1 hour | Tenant-level search ceiling |
| Concurrent active analyses | **3** | — | Max 3 full analyses running simultaneously per tenant |

### Burst vs Sustained

| Endpoint | Burst (per user) | Burst Window | Sustained (per tenant) | Sustained Window |
|----------|-----------------|-------------|----------------------|-----------------|
| AI analyze | 5 | 1 min | 50 | 1 hour |
| Re-analyze | 3 | 1 min | 20 | 1 hour |
| Copilot suggest | 20 | 1 min | 200 | 1 hour |
| Search | 60 | 1 min | 600 | 1 hour |

---

## Phase 3: Infrastructure Review

### Redis Availability

| Component | URL | Available? | Used For |
|-----------|-----|-----------|----------|
| Rate limiting | `redis://localhost:6379/0` | ✅ Already configured | Sliding window counters |
| Celery broker | `redis://localhost:6379/1` | ✅ In production | Task queue |
| Celery results | `redis://localhost:6379/2` | ✅ In production | Task results |

**Redis is already in the stack** and already used for rate limiting. No new infrastructure needed.

### Existing Rate Limiting Infrastructure

| Component | Status | Notes |
|-----------|--------|-------|
| `RateLimitMiddleware` | ✅ Existing | Redis-backed sliding window, in-memory fallback |
| `ENDPOINT_OVERRIDES` dict | ✅ Existing | Per-endpoint limit overrides (currently 3 entries) |
| `_get_client_key()` | ✅ Existing | Derives user/tenant/IP key from request state |
| `_get_rate_limit()` | ✅ Existing | Role-based defaults + endpoint overrides |
| `Retry-After` headers | ✅ Existing | Already set on 429 responses |
| `X-RateLimit-Limit` headers | ✅ Existing | Already set on all responses |
| `X-RateLimit-Remaining` headers | ✅ Existing | Already set on all responses |
| Structured logging | ✅ Existing | Rate limit warnings already logged |

### Context Access

| Context | Available Via | Used By Rate Limiter? |
|---------|--------------|----------------------|
| User ID | `request.state.user.id` | ✅ Already used |
| Tenant ID | `request.state.user.tenant_id` | ✅ Already used |
| User role | `request.state.user.role` | ✅ Already used |
| Request path | `request.url.path` | ✅ Already used |

### Recommendation: **Extend Existing RateLimitMiddleware**

**Do NOT add a new library or middleware.** The existing `RateLimitMiddleware` already has:

1. Redis-backed sliding window counters ✅
2. In-memory fallback when Redis is down ✅
3. Per-endpoint override dictionary ✅
4. User/tenant key derivation ✅
5. Rate limit headers on responses ✅
6. Retry-After headers on 429 ✅
7. Structured logging on violations ✅

The implementation is simply adding AI-specific entries to `ENDPOINT_OVERRIDES`.

**Why not SlowAPI?**
- SlowAPI would add a new dependency
- SlowAPI doesn't natively support tenant-aware limits
- SlowAPI doesn't integrate with existing auth context
- The existing middleware already does everything needed

---

## Phase 4: Implementation Plan

### Files to Create

| File | Purpose |
|------|---------|
| `backend/app/kernel/middleware/ai_rate_limits.py` | AI-specific rate limit constants and configuration |

### Files to Modify

| File | Change |
|------|--------|
| `backend/app/kernel/middleware/rate_limit.py` | Add AI endpoint overrides to `ENDPOINT_OVERRIDES` dict. Add concurrent analysis tracking. |
| `backend/app/config.py` | Add `ai_rate_limit_analyze`, `ai_rate_limit_copilot`, `ai_rate_limit_search` settings. Add `ai_max_concurrent_analyses` setting. |
| `backend/app/domains/ai/service.py` | Add rate limit check before dispatching analysis. Add concurrent analysis counter. |

### Middleware Placement

The `RateLimitMiddleware` is already registered in the correct position:

```
Request → CORS → SecurityHeaders → RateLimit → Deadline → BodySize → Logging → RequestID → Tenant → Auth → App
                                                                    ↑
                                                    AI rate limits checked here
```

No middleware position change needed. The existing `ENDPOINT_OVERRIDES` check runs inside `_get_rate_limit()` which is called per-request.

### Dependency Changes

| Dependency | Change |
|-----------|--------|
| `redis` | ✅ Already installed (`redis-py`) |
| `slowapi` | ❌ **Not needed** |
| New packages | **Zero** — no new dependencies |

### Configuration Settings to Add (`backend/app/config.py`)

```python
# ── AI Rate Limiting ─────────────────────────────────────────────
ai_rate_limit_analyze_per_user: int = 5
ai_rate_limit_analyze_per_tenant: int = 50
ai_rate_limit_analyze_window_seconds: int = 60

ai_rate_limit_tenant_window_seconds: int = 3600  # 1 hour

ai_rate_limit_copilot_per_user: int = 20
ai_rate_limit_copilot_per_tenant: int = 200

ai_rate_limit_search_per_user: int = 60
ai_rate_limit_search_per_tenant: int = 600

ai_max_concurrent_analyses: int = 3
```

### Implementation Steps

#### Step 1: Add AI endpoint overrides to `ENDPOINT_OVERRIDES`

In `backend/app/kernel/middleware/rate_limit.py`, add to the `ENDPOINT_OVERRIDES` dict:

```python
ENDPOINT_OVERRIDES: dict[str, int] = {
    # Existing
    "/api/v1/auth/token": 10,
    "/api/v1/integration/webhooks/ingest": 200,
    "/api/v1/ingestion/upload": 30,
    # AI endpoints (per-user limits)
    "/api/v1/ai/analyze": 5,
    "/api/v1/ai/copilot/suggest": 20,
    "/api/v1/reviews/analyze": 5,      # catches POST /reviews/{id}/analyze
    "/api/v1/reviews/re-analyze": 3,   # catches POST /reviews/{id}/re-analyze
}
```

#### Step 2: Add tenant-level rate limit tracking

Add a new Redis key namespace for tenant-level AI rate limits:

```python
TENANT_AI_LIMITS: dict[str, int] = {
    "analyze": 50,      # per hour
    "copilot": 200,     # per hour
    "search": 600,      # per hour
}
```

Add tenant-level check in `dispatch()`:

```python
# After per-user rate limit check passes, check tenant-level limit
if path.startswith(("/api/v1/ai/", "/api/v1/reviews/")):
    tenant_id = getattr(request.state.user, "tenant_id", None)
    if tenant_id:
        tenant_key = f"tenant_ai:{tenant_id}:{self._get_ai_operation(path)}"
        tenant_limit = self._get_tenant_ai_limit(path)
        if redis_client:
            allowed = await self._check_redis(redis_client, tenant_key, tenant_limit, 3600)
        else:
            allowed = self._check_local(tenant_key, tenant_limit, 3600)
        if not allowed:
            return JSONResponse(status_code=429, ...)
```

#### Step 3: Add concurrent analysis tracking

Add an in-memory counter for concurrent analyses:

```python
# In RateLimitMiddleware.__init__
self._active_analyses: dict[str, int] = {}  # tenant_id → count

# In dispatch(), before allowing an analysis request:
if self._is_analysis_path(path):
    tenant_id = getattr(request.state.user, "tenant_id", None)
    if tenant_id:
        current = self._active_analyses.get(tenant_id, 0)
        if current >= settings.ai_max_concurrent_analyses:
            return JSONResponse(status_code=429, content={
                "error": "concurrent_analysis_limit",
                "message": f"Max {settings.ai_max_concurrent_analyses} concurrent analyses. Wait for current analysis to complete."
            })
```

#### Step 4: Add structured audit logging

The existing rate limit logging already captures violations:

```python
logger.warning("Rate limit exceeded", extra={
    "client_key": client_key,
    "rate_limit": rate_limit,
    "path": request.url.path,
    "method": request.method,
})
```

Add AI-specific fields:

```python
logger.warning("AI rate limit exceeded", extra={
    "client_key": client_key,
    "rate_limit": rate_limit,
    "path": request.url.path,
    "ai_operation": self._get_ai_operation(path),
    "estimated_cost": self._get_estimated_cost(path),
    "tenant_id": getattr(request.state.user, "tenant_id", None),
    "user_id": getattr(request.state.user, "id", None),
})
```

### Unit Tests Required

| Test | Description |
|------|-------------|
| `test_ai_analyze_rate_limit` | Verify 6th request in 60s returns 429 |
| `test_ai_analyze_tenant_limit` | Verify 51st request in 1 hour returns 429 |
| `test_copilot_rate_limit` | Verify 21st copilot request in 60s returns 429 |
| `test_search_rate_limit` | Verify 61st search request in 60s returns 429 |
| `test_concurrent_analysis_limit` | Verify 4th concurrent analysis returns 429 |
| `test_rate_limit_headers` | Verify X-RateLimit-Limit and X-RateLimit-Remaining on AI endpoints |
| `test_rate_limit_redis_fallback` | Verify in-memory fallback works when Redis is down |
| `test_rate_limit_different_users` | Verify user A hitting limit doesn't block user B |
| `test_rate_limit_different_tenants` | Verify tenant A hitting limit doesn't block tenant B |

### Integration Tests Required

| Test | Description |
|------|-------------|
| `test_ai_endpoint_under_limit` | Verify normal usage succeeds |
| `test_ai_endpoint_burst_then_steady` | Verify burst + sustained limits work together |
| `test_concurrent_analysis_completion` | Verify counter decrements when analysis completes |
| `test_tenant_isolation_under_load` | Verify one tenant's heavy usage doesn't affect others |

### Load Tests Required

| Test | Description |
|------|-------------|
| `test_ai_rate_limit_throughput` | Verify rate limiter adds < 5ms overhead per request |
| `test_redis_rate_limit_throughput` | Verify Redis-backed checks handle 1000+ req/s |
| `test_concurrent_analysis_contention` | Verify 10 simultaneous analyze requests handle correctly |

### Deployment Compatibility

| Deployment Model | Compatible? | Notes |
|-----------------|-------------|-------|
| Single server | ✅ | Redis + in-memory both work |
| Multi-worker (Docker) | ✅ | Redis-backed limits are shared across workers |
| Kubernetes (HPA) | ✅ | Redis-backed limits survive pod scaling |
| Load-balanced | ✅ | Redis is the single source of truth |
| Redis down | ✅ | Falls back to per-process in-memory (limits reset on restart) |

### Fail-Safe Behavior

| Failure Mode | Behavior | Risk |
|-------------|----------|------|
| Redis connection timeout | Falls back to in-memory counters | 🟢 Low — limits are per-process but still enforced |
| Redis completely down | Falls back to in-memory | 🟢 Low — rate limits still work, just not shared across workers |
| Rate limit check exception | Request is allowed through | 🟡 Medium — fail-open prevents blocking legitimate traffic |
| Concurrent counter overflow | Stops counting (max int) | 🟢 Low — Python int is unbounded |

---

## Summary

### What to Build

1. **6 new entries** in `ENDPOINT_OVERRIDES` dict (5 minutes)
2. **Tenant-level rate limit tracking** in `RateLimitMiddleware` (2 hours)
3. **Concurrent analysis counter** in `RateLimitMiddleware` (1 hour)
4. **Config settings** in `app/config.py` (15 minutes)
5. **Unit tests** — 9 test cases (2 hours)
6. **Integration tests** — 4 test cases (1 hour)

### What NOT to Build

- ❌ New middleware class
- ❌ New rate limiting library (SlowAPI)
- ❌ Token-based rate limiting (over-engineered for v1)
- ❌ Cost-based throttling (requires budget tracking integration)
- ❌ Per-model rate limits (unnecessary — only gpt-4o is used)
- ❌ Embedding cache (separate concern, lower priority)

### Estimated Implementation Time

| Step | Effort |
|------|--------|
| Add endpoint overrides | 5 min |
| Add tenant-level limits | 2 h |
| Add concurrent analysis limit | 1 h |
| Add config settings | 15 min |
| Unit tests (9) | 2 h |
| Integration tests (4) | 1 h |
| **Total** | **~6.5 hours** |

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Rate limits too restrictive | Medium | Low — users get 429, can retry | Config-driven, adjust per-tenant |
| Rate limits too permissive | Medium | High — cost overrun | Start conservative, monitor, relax |
| Concurrent limit blocks legitimate use | Low | Medium — sequential analysis still works | Set to 3, monitor queue depth |
| Redis failure breaks limits | Low | Low — in-memory fallback | Already implemented |
