# Sprint 26 Task 4 — AI Rate Limiting: Implementation Revision

**Date:** 2026-06-05  
**Status:** Design Revision (Post-Review)  

---

## Finding 1: Endpoint Matching Logic

**Current behavior:** `ENDPOINT_OVERRIDES` uses **`startswith`** matching:

```python
for endpoint_path, limit in ENDPOINT_OVERIDES.items():
    if path.startswith(endpoint_path):
        return limit
```

**Implication for AI endpoints:**

| Proposed Override Path | Matches | Does NOT Match |
|------------------------|---------|----------------|
| `/api/v1/ai/analyze` | `POST /api/v1/ai/analyze` ✅ | — |
| `/api/v1/reviews/analyze` | `POST /api/v1/reviews/{id}/analyze` ❌ | Path is `/api/v1/reviews/{uuid}/analyze` — **startswith fails** |
| `/api/v1/reviews/re-analyze` | `POST /api/v1/reviews/{id}/re-analyze` ❌ | Same issue — UUID in path breaks matching |

**Fix:** Use path pattern matching instead of simple `startswith`:

```python
import re

# Compile endpoint patterns
ENDPOINT_PATTERNS: list[tuple[re.Pattern, int]] = [
    (re.compile(r"^/api/v1/ai/analyze$"), 5),
    (re.compile(r"^/api/v1/ai/copilot/suggest$"), 20),
    (re.compile(r"^/api/v1/reviews/[^/]+/analyze$"), 5),
    (re.compile(r"^/api/v1/reviews/[^/]+/re-analyze$"), 3),
    (re.compile(r"^/api/v1/search/?$"), 60),
    (re.compile(r"^/api/v1/search/clauses$"), 60),
]
```

**Updated plan:** Replace `ENDPOINT_OVERRIDES` dict with `ENDPOINT_PATTERNS` list of (regex, limit) tuples. Keep the existing simple overrides as-is, add regex-based matching for AI paths with UUID segments.

---

## Finding 2: Remove In-Memory Concurrent Analysis Counter

**Rejected approach from v1:**
```python
self._active_analyses: dict[str, int] = {}  # ❌ per-process, unsafe in K8s
```

**Why:** In-memory counters are per-process. With multiple Celery workers (Docker concurrency=4) or Kubernetes pods (HPA 3-20 replicas), each process has its own counter. A tenant could run 3× replicas × 3 limit = 9 concurrent analyses.

**Decision:** ❌ Remove in-memory counter entirely from middleware.

---

## Finding 3: Redis-Backed Concurrency Tracking

**Design:**

```
Key format:    ai_active:{tenant_id}
Value:         integer count of active analyses
TTL:           300 seconds (renewed on each check)
```

**Implementation location:** `analyze_contract_task` in `backend/workers/ai_worker.py`

**Flow:**

```
analyze_contract_task(upload_id, tenant_id, ...):
    1. INCR ai_active:{tenant_id}
    2. If result > max_concurrent:
         DECR ai_active:{tenant_id}
         raise MaxConcurrentAnalysisError
    3. EXPIRE ai_active:{tenant_id} 300  (safety TTL)
    4. TRY:
         await service.analyze(...)
       FINALLY:
         DECR ai_active:{tenant_id}
```

**TTL safety mechanism:** If a worker crashes mid-analysis (SIGKILL, OOM), the Redis key has a 300-second TTL. After 5 minutes, the counter auto-decrements. This prevents permanent lockout. The TTL is refreshed on each check, so long-running analyses (>5 min) keep the key alive.

**Max concurrent per tenant:** Configurable via `settings.ai_max_concurrent_analyses` (default: 3).

**Redis client:** Reuse the existing Celery Redis connection or the rate limiter's Redis client. The worker already depends on Redis (Celery broker), so no new infrastructure.

---

## Finding 4: Move Concurrency to AI Execution Layer

**Decision:** ❌ Do NOT enforce concurrency in middleware.

**Rationale:**
1. Middleware runs per HTTP request — analysis is dispatched asynchronously via Celery. The HTTP request returns before analysis completes.
2. Concurrency is about **running analyses**, not about HTTP requests hitting an endpoint.
3. The correct enforcement point is in `analyze_contract_task` (Celery worker), which is where analysis actually executes.

**New architecture:**

| Layer | Enforces | Mechanism |
|-------|----------|-----------|
| **Middleware** (`RateLimitMiddleware`) | Request rate per user | Redis sliding window — 5 POST/min/user to `/ai/analyze` |
| **Worker** (`analyze_contract_task`) | Concurrent analyses per tenant | Redis INCR/DECR — max 3 simultaneous per tenant |
| **Worker** (`analyze_contract_task`) | Cost governance | Future: check tenant token budget before executing |

**Middleware still enforces:**
- Per-user request rate limits (5 POST/min to `/ai/analyze`)
- Per-tenant request rate limits (50 POST/hr to `/ai/analyze`)
- Rate limit headers on all responses

**Worker enforces:**
- Per-tenant concurrent analysis limit (3 max)
- TTL-based crash recovery (300s auto-decrement)
- Task retry on concurrency failure

---

## Finding 5: Actual Production AI Model Configuration

**Current configuration:**

| Setting | Value | Source |
|---------|-------|--------|
| `OpenAIProvider.DEFAULT_MODEL` | **`gpt-4o`** | `backend/app/domains/ai/llm.py:104` |
| `analysis_request.model or "gpt-4o"` | **`gpt-4o`** | `backend/app/domains/ai/service.py:277` |
| `settings.ai_allowed_models` | `["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"]` | `backend/app/config.py:175` |

**The system uses `gpt-4o` by default**, not `gpt-4o-mini`. This is the expensive model.

**Cost comparison:**

| Model | Input/1K tokens | Output/1K tokens | Cost vs gpt-4o-mini |
|-------|----------------|------------------|-------------------|
| **gpt-4o** (current) | $0.0025 | $0.01 | **17× more expensive** |
| gpt-4o-mini | $0.00015 | $0.0006 | Baseline |

**Revised cost estimates:**

| Operation | Previous Estimate (gpt-4o-mini) | **Actual (gpt-4o)** |
|-----------|-------------------------------|-------------------|
| Risk analysis (10K tokens) | ~$0.002 | **~$0.04** |
| Redline gen per finding (3K tokens) | ~$0.001 | **~$0.013** |
| Full analysis (1 risk + 7 redlines) | ~$0.009 | **~$0.12** |
| Copilot suggest (3.5K tokens) | ~$0.001 | **~$0.013** |

**Worst-case cost scenario (recalculated):**

```
1 user × 5 req/min (proposed limit) × $0.12 = $0.60/min
= $36/hour  ← with rate limiting
vs.
$708/hour without rate limiting
```

**Recommendation:** Keep `gpt-4o` as default for analysis quality. The rate limits protect against cost overruns regardless of model. Consider `gpt-4o-mini` for copilot suggestions (cheaper, faster, good enough for suggestions).

---

## Finding 6: Search Endpoint Limits

**Revised search limits:**

| Endpoint | Previous Proposal | **Revised** | Rationale |
|----------|------------------|-------------|-----------|
| `POST /search/` | 60/min/user | **120/min/user** | Search is read-only, embeddings cost ~$0.000007/call |
| `GET /search/` | 120/min/user | **No limit** (default 100/min) | GET searches are idempotent, cheap |
| `GET /search/clauses` | 60/min/user | **No limit** (default 100/min) | Same as above |

**Search costs are negligible:**
- 1 embedding call = $0.000007 (text-embedding-3-large, ~50 tokens)
- 1000 searches = $0.007
- 100,000 searches = $0.70

**No need for AI-specific search limits.** The default 100 req/min authenticated rate limit is sufficient for search. Save the AI-specific rate limit configuration for expensive endpoints only.

---

## Revised Implementation Plan

### Files to Create

| File | Purpose |
|------|---------|
| `backend/app/kernel/middleware/ai_rate_limits.py` | AI endpoint regex patterns and limit constants |

### Files to Modify

| File | Change |
|------|--------|
| `backend/app/kernel/middleware/rate_limit.py` | Add regex-based `ENDPOINT_PATTERNS` alongside existing `ENDPOINT_OVERRIDES`. Add tenant-level rate limit check. |
| `backend/app/config.py` | Add `ai_rate_limit_analyze_per_user`, `ai_rate_limit_analyze_per_tenant`, `ai_max_concurrent_analyses` settings. |
| `backend/workers/ai_worker.py` | Add Redis INCR/DECR concurrency tracking around `service.analyze()` call. |

### Files NOT to Modify

| File | Reason |
|------|--------|
| `backend/app/domains/ai/orchestration/orchestrator.py` | Orchestrator is called by the worker, not directly. Concurrency enforcement at worker level is sufficient. |
| `backend/app/domains/ai/service.py` | Service layer is stateless. Rate limiting and concurrency are infrastructure concerns. |

### Implementation Steps

#### Step 1: Add config settings

In `backend/app/config.py`:

```python
# ── AI Rate Limiting ─────────────────────────────────────────────
ai_rate_limit_analyze_per_user: int = 5
ai_rate_limit_analyze_per_tenant: int = 50
ai_rate_limit_analyze_window_seconds: int = 60
ai_rate_limit_tenant_window_seconds: int = 3600
ai_max_concurrent_analyses: int = 3
```

#### Step 2: Add regex endpoint patterns

In `backend/app/kernel/middleware/ai_rate_limits.py`:

```python
import re

# Regex patterns for AI endpoints (path has UUID segments)
AI_ENDPOINT_PATTERNS: list[tuple[re.Pattern, int, int]] = [
    # (regex, per_user_limit, per_tenant_limit)
    (re.compile(r"^/api/v1/ai/analyze$"), 5, 50),
    (re.compile(r"^/api/v1/ai/copilot/suggest$"), 20, 200),
    (re.compile(r"^/api/v1/reviews/[^/]+/analyze$"), 5, 50),
    (re.compile(r"^/api/v1/reviews/[^/]+/re-analyze$"), 3, 20),
]
```

#### Step 3: Update middleware to use regex patterns

In `backend/app/kernel/middleware/rate_limit.py`, update `_get_rate_limit()`:

```python
def _get_rate_limit(self, request: Request) -> int:
    path = request.url.path

    # Check regex-based AI endpoint patterns first
    from app.kernel.middleware.ai_rate_limits import AI_ENDPOINT_PATTERNS
    for pattern, user_limit, tenant_limit in AI_ENDPOINT_PATTERNS:
        if pattern.match(path):
            # Store tenant limit on request state for later check
            request.state._ai_tenant_limit = tenant_limit
            request.state._ai_operation = pattern.pattern
            return user_limit

    # Check existing simple prefix overrides
    for endpoint_path, limit in ENDPOINT_OVERRIDES.items():
        if path.startswith(endpoint_path):
            return limit

    # Role-based defaults
    ...
```

Add tenant-level check in `dispatch()`:

```python
async def dispatch(self, request, call_next):
    # ... existing per-user rate check ...

    # Tenant-level AI rate limit check
    tenant_limit = getattr(request.state, "_ai_tenant_limit", None)
    if tenant_limit is not None:
        tenant_id = getattr(request.state.user, "tenant_id", None)
        if tenant_id:
            tenant_key = f"ai_tenant:{tenant_id}:{request.state._ai_operation}"
            redis_client = await self._get_redis()
            if redis_client:
                allowed = await self._check_redis(
                    redis_client, tenant_key, tenant_limit,
                    settings.ai_rate_limit_tenant_window_seconds
                )
            else:
                allowed = self._check_local(
                    tenant_key, tenant_limit,
                    settings.ai_rate_limit_tenant_window_seconds
                )
            if not allowed:
                return JSONResponse(status_code=429, ...)

    response = await call_next(request)
    # ... existing rate limit headers ...
```

#### Step 4: Add Redis concurrency tracking in worker

In `backend/workers/ai_worker.py`, wrap the analysis call:

```python
import aioredis

async def _analyze_contract(...):
    session = await worker_loop.create_session(...)
    async with helper.session_scope(session):
        redis = None
        try:
            # Check concurrent analysis limit
            redis = await _get_redis()
            if redis:
                active_key = f"ai_active:{tenant_id}"
                count = await redis.incr(active_key)
                await redis.expire(active_key, 300)  # safety TTL
                if count > settings.ai_max_concurrent_analyses:
                    await redis.decr(active_key)
                    raise MaxConcurrentAnalysisError(
                        f"Max {settings.ai_max_concurrent_analyses} concurrent analyses. Retry later."
                    )

            # Execute analysis
            result = await service.analyze(...)

        except MaxConcurrentAnalysisError:
            # Retry with delay
            raise self.retry(countdown=30)
        finally:
            if redis:
                await redis.decr(active_key)
```

#### Step 5: Add `MaxConcurrentAnalysisError`

In `backend/workers/ai_worker.py` or a new exceptions module:

```python
class MaxConcurrentAnalysisError(Exception):
    """Raised when tenant has reached max concurrent analyses."""
```

### Test Plan

#### Unit Tests (8)

| # | Test | Layer |
|---|------|-------|
| 1 | Regex pattern matches `/api/v1/reviews/{uuid}/analyze` | Middleware |
| 2 | Regex pattern matches `/api/v1/ai/analyze` | Middleware |
| 3 | Regex pattern does NOT match `/api/v1/reviews/{uuid}` | Middleware |
| 4 | Regex pattern does NOT match `/api/v1/reviews/{uuid}/findings` | Middleware |
| 5 | Redis INCR sets TTL on `ai_active:{tenant_id}` | Worker |
| 6 | Redis DECR on successful analysis completion | Worker |
| 7 | Redis DECR on analysis failure (finally block) | Worker |
| 8 | Max concurrent exceeded raises `MaxConcurrentAnalysisError` | Worker |

#### Integration Tests (4)

| # | Test |
|---|------|
| 1 | 6th analyze request in 60s returns 429 |
| 2 | Tenant-level limit: 51st analyze request in 1 hour returns 429 |
| 3 | Concurrent limit: 4th simultaneous analysis blocks |
| 4 | Worker crash: TTL auto-decrements after 300s |

### Dependency Changes

| Dependency | Change |
|-----------|--------|
| `redis-py` | ✅ Already installed |
| `slowapi` | ❌ **Not needed** |
| New packages | **Zero** |

### Deployment Compatibility

| Deployment Model | Rate Limits | Concurrency |
|-----------------|-------------|-------------|
| Single server | ✅ Redis + in-memory fallback | ✅ Redis INCR/DECR |
| Multi-worker (Docker) | ✅ Redis-backed (shared) | ✅ Redis-backed (shared) |
| Kubernetes (HPA) | ✅ Redis-backed (shared) | ✅ Redis-backed (shared) |
| Redis down | ✅ In-memory fallback (per-process) | ⚠️ Falls back to no limit (safe — per-process limits still apply) |

---

## Summary of Changes from v1

| Aspect | v1 (Previous) | v2 (Revised) | Rationale |
|--------|--------------|--------------|-----------|
| Endpoint matching | `startswith` | **Regex patterns** | UUID in path breaks `startswith` |
| Concurrency location | Middleware | **Worker (ai_worker.py)** | Middleware can't track async Celery tasks |
| Concurrency storage | In-memory dict | **Redis INCR/DECR** | Multi-worker/K8s safe |
| Crash safety | None | **300s TTL** | Worker crash auto-recovers |
| Search limits | 60/min/user | **No AI-specific limit** | Search costs are negligible ($0.007/1K) |
| Model assumption | gpt-4o-mini | **gpt-4o (actual)** | Cost estimates updated 17× higher |
| Files to create | 1 | **1** (ai_rate_limits.py) | Unchanged |
| Files to modify | 3 | **3** (rate_limit.py, config.py, ai_worker.py) | Unchanged |
| Estimated effort | 6.5h | **7h** (+0.5h for Redis concurrency) | Slightly higher due to Redis logic |
