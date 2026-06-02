# ContractRiskEdge — Operational Runbooks

## Table of Contents

1. [Provider Outage](#1-provider-outage)
2. [Degraded AI Quality](#2-degraded-ai-quality)
3. [WebSocket Collapse](#3-websocket-collapse)
4. [Replay Corruption](#4-replay-corruption)
5. [Tenant Incident](#5-tenant-incident)
6. [Stuck Workflow](#6-stuck-workflow)
7. [Queue Saturation](#7-queue-saturation)
8. [Telemetry Outage](#8-telemetry-outage)
9. [Deployment Rollback](#9-deployment-rollback)
10. [Database Degradation](#10-database-degradation)

---

## 1. Provider Outage

### Symptoms
- AI analysis tasks failing with `OpenAIProviderError`
- Worker logs showing connection timeouts to `api.openai.com`
- Alert: "AI provider degraded" operational banner
- Executive dashboard showing 0% AI success rate

### Severity
**CRITICAL** — blocks all AI analysis, review, and copilot features.

### Immediate Actions
1. **Verify outage**: Check `https://status.openai.com` for confirmed outage
2. **Enable fallback mode**: Set `AI_FALLBACK_MODE=true` in environment
   - Falls back to rule-based analysis (reduced quality but non-blocking)
   - Copilot returns "AI temporarily unavailable" message
3. **Monitor queue**: Check Celery queue depth:
   ```bash
   celery -A app.workers.celery_app inspect active
   ```
4. **Notify users**: Operational banner automatically displays "AI provider degraded"

### Recovery
1. Verify provider恢复正常 via status page
2. Disable fallback mode: `AI_FALLBACK_MODE=false`
3. Re-queue failed tasks:
   ```bash
   python backend/scripts/requeue_failed_ai_tasks.py --hours 24
   ```
4. Verify AI success rate returns to >95%

### Post-Mortem
- Document outage duration and impact
- Review fallback mode effectiveness
- Consider adding secondary AI provider (Anthropic, Cohere)

---

## 2. Degraded AI Quality

### Symptoms
- AI confidence scores dropping below 70%
- Executive dashboard showing "AI Confidence Drift" alert
- Reviewer complaints about irrelevant suggestions
- Increased redline rejection rate

### Severity
**HIGH** — erodes trust in AI analysis, slows review throughput.

### Immediate Actions
1. **Check prompt versions**: Verify active prompt templates in prompt registry
2. **Review recent deployments**: Check if prompt changes were deployed
3. **Compare against baseline**: Run replay validation against golden dataset:
   ```bash
   python backend/scripts/validate_ai_quality.py --baseline latest
   ```
4. **Rollback prompts if needed**: Set `PROMPT_VERSION=1` to revert to stable

### Recovery
1. Identify root cause (prompt drift, model degradation, data quality)
2. Deploy fix with prompt version bump
3. Run full golden dataset validation
4. Monitor confidence scores for 24h before declaring recovery

### Prevention
- Add automated quality gates before prompt deployment
- Maintain golden dataset with >100 validated examples
- Weekly quality benchmark runs

---

## 3. WebSocket Collapse

### Symptoms
- "Live updates disconnected" operational banner on all pages
- Executive dashboard showing stale data (no refresh)
- Worker logs showing connection reset errors
- Alert: "WebSocket connection storm detected"

### Severity
**HIGH** — real-time coordination broken, dashboard becomes stale.

### Immediate Actions
1. **Check WebSocket server**: Verify events router is running:
   ```bash
   curl http://localhost:8000/api/v1/events/health
   ```
2. **Check Redis**: WebSocket uses Redis pub/sub:
   ```bash
   redis-cli ping
   redis-cli info clients
   ```
3. **Restart WebSocket server**:
   ```bash
   docker compose restart backend
   ```
4. **Enable polling fallback**: Frontend automatically falls back to 5s polling

### Recovery
1. Identify root cause (Redis connection, worker crash, network partition)
2. Fix and verify WebSocket reconnects
3. Monitor connection stability for 30min
4. Verify dashboard refresh behavior

### Prevention
- Configure WebSocket health check alerts
- Add Redis connection pool monitoring
- Ensure frontend polling fallback is always operational

---

## 4. Replay Corruption

### Symptoms
- Replay comparison showing unexpected diffs
- AI execution traces with missing steps
- Audit trail inconsistencies
- "Replay inconsistency" alert

### Severity
**HIGH** — audit integrity at risk, compliance exposure.

### Immediate Actions
1. **Isolate affected replays**: Query for replays with missing steps:
   ```bash
   python backend/scripts/find_corrupted_replays.py --hours 48
   ```
2. **Freeze affected reviews**: Set reviews to read-only:
   ```bash
   python backend/scripts/freeze_reviews.py --replay-ids <ids>
   ```
3. **Restore from backup**: If replay data is critical:
   ```bash
   python backend/scripts/restore_replay_backup.py --hours 24
   ```
4. **Notify compliance team**: Document affected audits

### Recovery
1. Identify root cause (storage corruption, race condition, deployment bug)
2. Fix and deploy
3. Re-run affected replays
4. Verify audit trail integrity
5. Unfreeze reviews

### Prevention
- Add replay checksum validation
- Regular replay backup snapshots
- Automated replay integrity checks

---

## 5. Tenant Incident

### Symptoms
- Tenant reporting data leakage or unauthorized access
- Audit logs showing unexpected access patterns
- Alert: "Suspicious tenant activity"
- Support ticket from customer

### Severity
**CRITICAL** — immediate security incident.

### Immediate Actions
1. **Isolate tenant**: Revoke tenant API keys:
   ```bash
   python backend/scripts/revoke_tenant_keys.py --tenant-id <id>
   ```
2. **Audit access logs**: Query for all access by that tenant:
   ```bash
   python backend/scripts/audit_tenant_access.py --tenant-id <id> --hours 72
   ```
3. **Check tenant isolation**: Verify no cross-tenant data leakage:
   ```bash
   python backend/scripts/verify_tenant_isolation.py --tenant-id <id>
   ```
4. **Notify security team**: Document incident timeline
5. **Consider tenant suspension**: If breach confirmed

### Recovery
1. Complete forensic audit
2. Fix identified vulnerability
3. Regenerate tenant credentials
4. Verify isolation before restoring access
5. Customer communication

### Prevention
- Regular tenant isolation penetration testing
- Automated anomaly detection for access patterns
- Immutable audit logs for forensic analysis

---

## 6. Stuck Workflow

### Symptoms
- Review stuck in "processing" state for >30min
- Ingestion stuck in "validating" or "ocr_processing" state
- Alert: "Workflow bottleneck detected"
- Executive dashboard showing stuck workflows

### Severity
**MEDIUM** — blocks specific reviews, may cascade to SLA breaches.

### Immediate Actions
1. **Identify stuck workflows**:
   ```bash
   python backend/scripts/find_stuck_workflows.py --minutes 30
   ```
2. **Check worker logs**: Identify failure reason:
   ```bash
   docker compose logs backend_worker --tail 50
   ```
3. **Retry stuck workflows**:
   ```bash
   python backend/scripts/retry_stuck_workflows.py --hours 1
   ```
4. **If retry fails**: Manual intervention required — escalate to engineering

### Recovery
1. Fix root cause (worker crash, data corruption, dependency failure)
2. Re-queue all stuck workflows
3. Verify processing resumes
4. Monitor for recurrence

### Prevention
- Add workflow timeout monitoring
- Automated retry with exponential backoff
- Dead-letter queue for permanently failed workflows

---

## 7. Queue Saturation

### Symptoms
- Celery queue depth exceeding 10,000
- Processing latency > 5 minutes
- Worker CPU at 100%
- Alert: "Ingestion backlog detected"

### Severity
**MEDIUM** — processing delay, may cascade to SLA breaches.

### Immediate Actions
1. **Scale workers**: Increase worker concurrency:
   ```bash
   kubectl scale deployment contractrisk-worker --replicas=5
   ```
   Or for Docker:
   ```bash
   docker compose up -d --scale backend_worker=5
   ```
2. **Prioritize queues**: Re-route critical tasks:
   ```bash
   celery -A app.workers.celery_app control rate-limit ingestion/task 10/m
   ```
3. **Monitor queue drain rate**:
   ```bash
   celery -A app.workers.celery_app inspect active
   ```

### Recovery
1. Monitor queue depth returning to normal (< 100)
2. Scale workers back down
3. Verify processing latency恢复正常

### Prevention
- Auto-scaling based on queue depth
- Queue depth monitoring and alerting
- Task prioritization (SLA-bound reviews first)

---

## 8. Telemetry Outage

### Symptoms
- Grafana dashboards showing no data
- Alert: "OpenTelemetry disconnected"
- Missing metrics for >5 minutes

### Severity
**LOW** — operational visibility degraded, core functionality unaffected.

### Immediate Actions
1. **Check OTel collector**:
   ```bash
   curl http://localhost:4318/health
   ```
2. **Check Grafana backend**:
   ```bash
   docker compose -f deploy/observability/docker-compose.observability.yml ps
   ```
3. **Restart OTel collector**:
   ```bash
   docker compose -f deploy/observability/docker-compose.observability.yml restart otel-collector
   ```

### Recovery
1. Verify metrics appearing in Grafana
2. Check for data gaps
3. Restart services if needed

### Prevention
- OTel collector health monitoring
- Metrics buffer in frontend telemetry (already implemented)
- Grafana alerting for metric absence

---

## 9. Deployment Rollback

### Symptoms
- Post-deployment errors
- Performance degradation
- Customer complaints
- Automated rollback trigger

### Severity
**VARIABLE** — depends on deployment impact.

### Immediate Actions
1. **Identify deployment**: Note the deployment timestamp and change set:
   ```bash
   git log --oneline -5
   ```
2. **Rollback Docker Compose**:
   ```bash
   docker compose down
   git checkout <previous-stable-tag>
   docker compose up -d --build
   ```
3. **Rollback Kubernetes**:
   ```bash
   kubectl rollout undo deployment/contractrisk-api -n contractrisk
   kubectl rollout undo deployment/contractrisk-worker -n contractrisk
   kubectl rollout undo deployment/contractrisk-frontend -n contractrisk
   ```
4. **Verify rollback**: Run smoke tests:
   ```bash
   python deploy/pilot/deploy.py --smoke-test-only --base-url <url>
   ```

### Recovery
1. Investigate root cause of failed deployment
2. Fix in development
3. Re-deploy with fix
4. Monitor for recurrence

### Prevention
- Canary deployments for critical changes
- Automated smoke tests in CI/CD
- Database migration rollback scripts
- Feature flags for risky changes

---

## 10. Database Degradation

### Symptoms
- Slow query responses (>1s)
- Connection pool exhaustion
- Replication lag
- Alert: "Database performance degraded"

### Severity
**HIGH** — affects all platform operations.

### Immediate Actions
1. **Check slow queries**:
   ```sql
   SELECT query, calls, total_time / calls AS avg_time
   FROM pg_stat_statements
   ORDER BY avg_time DESC LIMIT 20;
   ```
2. **Check connection pool**:
   ```sql
   SELECT count(*) FROM pg_stat_activity;
   ```
3. **Kill long-running queries**:
   ```sql
   SELECT pg_terminate_backend(pid)
   FROM pg_stat_activity
   WHERE state = 'active' AND now() - query_start > interval '30 seconds';
   ```
4. **Scale database**: Increase instance size or add read replicas

### Recovery
1. Identify bottleneck (missing index, slow query, lock contention)
2. Fix and deploy migration
3. Verify performance恢复正常
4. Add monitoring for recurrence

### Prevention
- Regular `EXPLAIN ANALYZE` on slow queries
- Automated index recommendations
- Connection pool sizing review
- Read replica for analytics queries
