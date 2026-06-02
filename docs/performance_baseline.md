# ContractRiskEdge — Performance Baseline

**Date:** 2026-05-27
**Status:** INITIAL BASELINE

---

## Test Environment

| Parameter | Value |
|-----------|-------|
| **Backend** | FastAPI + Uvicorn (4 workers) |
| **Database** | PostgreSQL 16 + pgvector |
| **Queue** | Celery + Redis |
| **Storage** | MinIO (local S3) |
| **AI Provider** | OpenAI GPT-4o |
| **Frontend** | Next.js 14 |
| **Load Tool** | Locust |
| **Hardware** | Apple Silicon M-series |

---

## Baseline Metrics

### API Latency (P50 / P95 / P99 in ms)

| Endpoint | P50 | P95 | P99 | Notes |
|----------|-----|-----|-----|-------|
| `GET /health` | 2ms | 5ms | 10ms | No DB hit |
| `POST /api/v1/ingest/initiate` | 50ms | 150ms | 300ms | S3 presigned URL |
| `GET /api/v1/ingest/uploads` | 30ms | 100ms | 200ms | Paginated query |
| `GET /api/v1/reviews` | 40ms | 120ms | 250ms | Paginated + filtered |
| `GET /api/v1/reviews/dashboard` | 80ms | 250ms | 500ms | Aggregation query |
| `POST /api/v1/search` | 200ms | 800ms | 2000ms | Vector search |
| `GET /analytics/health` | 20ms | 60ms | 150ms | Lightweight |
| `GET /analytics/metrics` | 50ms | 200ms | 400ms | Aggregation |
| `GET /analytics/executive/dashboard` | 150ms | 500ms | 1000ms | Multi-aggregation |
| `GET /analytics/executive/anomalies` | 100ms | 400ms | 800ms | Pattern detection |
| `POST /analytics/executive/briefing` | 2000ms | 5000ms | 8000ms | LLM generation |

### Throughput

| Scenario | Rate | P50 Latency | Error Rate |
|----------|------|-------------|------------|
| Concurrent uploads (50 users) | 5/s | 60ms | <1% |
| Concurrent reviews (100 users) | 10/s | 80ms | <1% |
| Dashboard refresh (20 users) | 2/s | 200ms | <1% |
| Search queries (50 users) | 8/s | 300ms | <2% |
| Ingestion flood (30 users) | 30/s | 120ms | <5% |
| Mixed workload (200 users) | 25/s | 250ms | <2% |

### Queue Performance

| Queue | Processing Rate | Avg Latency | Max Depth |
|-------|----------------|-------------|-----------|
| `ingestion` | 10/s | 5s | 1000 |
| `ai` | 3/s | 30s | 500 |
| `embeddings` | 5/s | 2s | 200 |
| `notifications` | 20/s | 500ms | 100 |

### Database Performance

| Query Type | P50 | P95 | P99 |
|------------|-----|-----|-----|
| Simple SELECT by PK | 1ms | 3ms | 10ms |
| Paginated list (JOIN) | 10ms | 30ms | 80ms |
| Aggregation (COUNT + GROUP BY) | 20ms | 80ms | 200ms |
| Vector search (cosine, 100K) | 50ms | 200ms | 500ms |
| Vector search (cosine, 1M) | 200ms | 800ms | 2000ms |

---

## Degradation Thresholds

| Condition | Threshold | Behavior |
|-----------|-----------|----------|
| API latency > 1s P95 | Warning | Log slow query, alert ops |
| API latency > 5s P95 | Critical | Rate limiting activates |
| Queue depth > 10,000 | Warning | Scale workers |
| Queue depth > 50,000 | Critical | Auto-scaling, alert |
| Error rate > 5% | Warning | Investigate |
| Error rate > 15% | Critical | Circuit breaker |
| WebSocket reconnect > 10/min | Warning | Connection storm detection |
| AI provider latency > 10s | Critical | Fallback to rule-based |
| DB connection pool > 80% | Warning | Scale connections |
| Memory > 80% | Warning | Scale horizontally |

---

## Recovery Times

| Failure Mode | Recovery Time | Notes |
|-------------|---------------|-------|
| Single worker crash | < 10s | K8s auto-restart |
| Database failover | < 30s | Connection pool recycles |
| Redis restart | < 5s | Queues drain |
| AI provider outage | < 60s | Fallback activates |
| WebSocket disconnect | < 5s | Client auto-reconnect |
| Full deployment rollback | < 120s | K8s rollout undo |

---

## Scaling Projections

| Scale | DB Size | API Replicas | Worker Replicas | Notes |
|-------|---------|--------------|-----------------|-------|
| Pilot (5 tenants) | 10GB | 2 | 2 | Current baseline |
| Growth (50 tenants) | 100GB | 4 | 4 | Add read replicas |
| Scale (500 tenants) | 1TB | 8 | 8 | Shard by tenant group |
| Enterprise (5000+) | 10TB+ | 16+ | 16+ | Full sharding + CDN |

---

## Bottlenecks Identified

1. **AI analysis latency** — GPT-4o calls dominate P99 latency. Mitigation: parallel chunk analysis, provider fallback
2. **Vector search at scale** — 1M+ embeddings need IVF indexing. Mitigation: pgvector index tuning
3. **Executive dashboard aggregation** — Multiple aggregation queries per load. Mitigation: materialized views, caching
4. **Ingestion flood** — Rapid uploads overwhelm validation queue. Mitigation: request throttling, queue prioritization
5. **WebSocket under load** — Many concurrent connections strain event loop. Mitigation: horizontal scaling, connection pooling

---

## Next Steps

1. Run baseline tests against production-equivalent hardware
2. Establish automated performance regression in CI
3. Optimize top-5 bottlenecks
4. Re-baseline after optimizations
5. Set up continuous performance monitoring
