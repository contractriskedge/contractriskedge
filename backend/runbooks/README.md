# ContractRiskEdge Operational Runbooks
# =============================================================================
# Recovery procedures for production incidents.
# These runbooks MUST be tested quarterly via DR validation suite.
# =============================================================================

# ── Table of Contents ──────────────────────────────────────────────
# 1. Provider Outage Recovery
# 2. Replay Corruption Recovery
# 3. Tenant Isolation Incident
# 4. Audit Verification Failure
# 5. Vector DB Rebuild
# 6. Stuck Workflow Recovery
# 7. Deployment Rollback
# 8. Configuration Drift Resolution
# 9. Event Bus Failure
# 10. Queue Poison Message Cleanup
# =============================================================================

# ══════════════════════════════════════════════════════════════════════════════
# 1. PROVIDER OUTAGE RECOVERY
# ══════════════════════════════════════════════════════════════════════════════
# Impact: AI analysis, redline generation, all LLM-dependent features
# Severity: Critical
# RTO: 5 minutes (automatic), 15 minutes (manual intervention)
# =============================================================================

## Detection
# - Alert: "High AI Provider Error Rate" fires
# - Alert: "Provider Circuit Breaker Open" fires
# - Dashboard: AI Performance → Provider Health shows elevated errors

## Automatic Recovery (should happen within 30 seconds)
# 1. Circuit breaker opens for failed provider
# 2. LLM registry selects next healthy provider from fallback chain
# 3. Queued requests are retried with fallback provider
# 4. Alert auto-resolves when circuit breaker closes

## Manual Recovery Steps
# 1. VERIFY provider status
#    kubectl exec -it deploy/contractriskedge-api -- python -c "
#    from app.domains.ai.providers.registry import llm_registry
#    print(llm_registry._health)
#    "
#
# 2. CHECK circuit breaker state
#    kubectl exec -it deploy/contractriskedge-api -- python -c "
#    from app.domains.ai.providers.registry import llm_registry
#    for name, health in llm_registry._health.items():
#        print(f'{name}: circuit_breaker={health.circuit_breaker_open}, health_score={health.health_score}')
#    "
#
# 3. FORCE circuit breaker closed (if provider is actually healthy)
#    kubectl exec -it deploy/contractriskedge-api -- python -c "
#    from app.domains.ai.providers.registry import llm_registry
#    health = llm_registry._health.get('openai')
#    if health:
#        health.circuit_breaker_open = False
#        health.health_score = 1.0
#        print('Circuit breaker reset')
#    "
#
# 4. VERIFY recovery
#    kubectl exec -it deploy/contractriskedge-api -- python -c "
#    from app.domains.ai.providers.registry import llm_registry
#    provider = llm_registry.select_provider()
#    print(f'Selected provider: {provider.provider_name}')
#    "

## Post-Mortem
# - Document root cause in runbook
# - Verify fallback chain configuration
# - Update provider health thresholds if needed
# =============================================================================


# ══════════════════════════════════════════════════════════════════════════════
# 2. REPLAY CORRUPTION RECOVERY
# ══════════════════════════════════════════════════════════════════════════════
# Impact: Audit reproducibility, compliance verification
# Severity: High
# RTO: 1 hour
# =============================================================================

## Detection
# - Alert: "AI Replay Drift Detected" fires
# - Drift score exceeds 0.3 threshold
# - Retrieval snapshot hash mismatch

## Recovery Steps
# 1. IDENTIFY affected executions
#    kubectl exec -it deploy/contractriskedge-api -- python -c "
#    from app.domains.ai.replay import ReplayAIExecutionService
#    from app.kernel.database.session import AsyncSessionLocal
#    import asyncio
#    async def check():
#        async with AsyncSessionLocal() as session:
#            service = ReplayAIExecutionService(session, 'TENANT_ID')
#            # List recent replays with high drift
#    asyncio.run(check())
#    "
#
# 2. VERIFY retrieval snapshot integrity
#    kubectl exec -it deploy/contractriskedge-api -- python -c "
#    from app.domains.ai.snapshots.service import RetrievalSnapshotService
#    from app.kernel.database.session import AsyncSessionLocal
#    import asyncio
#    async def verify():
#        async with AsyncSessionLocal() as session:
#            service = RetrievalSnapshotService(session, 'TENANT_ID')
#            valid, error = await service.verify_snapshot_integrity('SNAPSHOT_ID')
#            print(f'Snapshot valid: {valid}, error: {error}')
#    asyncio.run(verify())
#    "
#
# 3. REBUILD corrupted snapshots
#    - If snapshot hash mismatch: re-create snapshot from original execution context
#    - If prompt version mismatch: re-run with correct prompt version
#    - If embedding model mismatch: re-embed chunks with original model
#
# 4. RE-RUN drift comparison
#    kubectl exec -it deploy/contractriskedge-api -- python -c "
#    from app.domains.ai.replay import ReplayAIExecutionService
#    from app.kernel.database.session import AsyncSessionLocal
#    import asyncio
#    async def compare():
#        async with AsyncSessionLocal() as session:
#            service = ReplayAIExecutionService(session, 'TENANT_ID')
#            comparison = await service.compare_versions('RUN_ID_A', 'RUN_ID_B')
#            print(f'Drift: {comparison.drift_score}, severity: {comparison.drift_severity}')
#    asyncio.run(compare())
#    "

## Prevention
# - Pin embedding model versions in retrieval snapshots
# - Version all prompt templates
# - Add pre-execution snapshot integrity check
# =============================================================================


# ══════════════════════════════════════════════════════════════════════════════
# 3. TENANT ISOLATION INCIDENT
# ══════════════════════════════════════════════════════════════════════════════
# Impact: Data confidentiality, compliance (SOC2, GDPR)
# Severity: Critical
# RTO: 15 minutes
# =============================================================================

## Detection
# - Alert: "Cross-tenant access attempt" from SuspiciousActivityDetector
# - Support ticket reporting data from wrong tenant
# - Audit trail shows unexpected tenant_id patterns

## Immediate Containment
# 1. ISOLATE affected tenant
#    kubectl exec -it deploy/contractriskedge-api -- python -c "
#    from app.domains.tenant_runtime import TenantQuotaManager
#    # Temporarily suspend non-critical operations
#    "
#
# 2. VERIFY tenant_id enforcement
#    kubectl exec -it deploy/contractriskedge-api -- python -c "
#    from app.kernel.repository.base import BaseRepository
#    # Verify filter_tenant() is applied to all queries
#    "
#
# 3. AUDIT all queries for tenant boundary violations
#    Check audit_trail for event_type = 'security.tenant_access_denied'
#
# 4. NOTIFY affected tenant admin
#    - Document scope of potential exposure
#    - Provide audit trail of affected queries

## Investigation
# 1. Check if tenant_id was missing from any recent queries
#    SELECT * FROM audit_trail WHERE event_type = 'security.tenant_access_denied'
#    ORDER BY created_at DESC LIMIT 100
#
# 2. Verify vector collection isolation
#    - Check partition strategy for affected tenant tier
#    - Verify metadata filters on shared collections
#
# 3. Review recent deployments for isolation regression
#    git log --oneline -20
#    git diff HEAD~5 -- app/kernel/repository/

## Resolution
# - Patch tenant boundary gap
# - Add automated isolation test
# - Document in post-mortem
# =============================================================================


# ══════════════════════════════════════════════════════════════════════════════
# 4. AUDIT VERIFICATION FAILURE
# ══════════════════════════════════════════════════════════════════════════════
# Impact: Compliance, legal admissibility
# Severity: Critical
# RTO: 4 hours
# =============================================================================

## Detection
# - DR validation suite reports audit chain violation
# - Compliance report shows hash chain inconsistency
# - Manual audit verification fails

## Investigation
# 1. IDENTIFY broken chain point
#    kubectl exec -it deploy/contractriskedge-api -- python -c "
#    from app.domains.security import ImmutableAuditVerifier
#    from app.kernel.database.session import AsyncSessionLocal
#    import asyncio
#    async def verify():
#        async with AsyncSessionLocal() as session:
#            verifier = ImmutableAuditVerifier(session)
#            violations = await verifier.verify_chain('TENANT_ID')
#            for v in violations:
#                print(f'Violation: {v}')
#    asyncio.run(verify())
#    "
#
# 2. DETERMINE if tampered or corrupted
#    - Check if entry_hash matches recomputed hash
#    - Check if previous_hash chain is intact
#    - Check HMAC signature validity
#
# 3. If tampered:
#    - Isolate affected entries
#    - Restore from backup
#    - Initiate security incident response
#
# 4. If corrupted (not tampered):
#    - Recompute hashes from last known good entry
#    - Verify HMAC signing key is correct
#    - Re-sign affected entries

## Recovery
# 1. RESTORE audit chain from backup if tampered
# 2. RE-SIGN entries if key rotation caused failure
# 3. VERIFY chain integrity after recovery
# 4. DOCUMENT in compliance report
# =============================================================================


# ══════════════════════════════════════════════════════════════════════════════
# 5. VECTOR DB REBUILD
# ══════════════════════════════════════════════════════════════════════════════
# Impact: Search quality, AI analysis quality
# Severity: High
# RTO: 2 hours (degraded), 24 hours (full rebuild)
# =============================================================================

## Trigger Conditions
# - Embedding model upgrade (e.g., ada-002 → text-embedding-3-large)
# - Vector DB corruption detected
# - Stale chunk percentage exceeds 20%

## Pre-Rebuild Checklist
# [ ] Verify source chunks are intact
#      SELECT COUNT(*) FROM chunks WHERE is_active = true
# [ ] Verify embedding model registry has target model
#      Check EMBEDDING_MODEL_REGISTRY in vectors/partition/__init__.py
# [ ] Verify API keys for embedding provider
# [ ] Notify stakeholders of degraded search during rebuild

## Rebuild Steps
# 1. CREATE re-index job
#    kubectl exec -it deploy/contractriskedge-api -- python -c "
#    from app.domains.vectors.partition import ReIndexScheduler
#    from app.kernel.database.session import AsyncSessionLocal
#    import asyncio
#    async def reindex():
#        async with AsyncSessionLocal() as session:
#            scheduler = ReIndexScheduler(session)
#            job = await scheduler.create_reindex_job(
#                reason='model_upgrade',
#                old_model='text-embedding-ada-002',
#                target_model='text-embedding-3-large'
#            )
#            print(f'Created job: {job.job_id}')
#    asyncio.run(reindex())
#    "
#
# 2. MONITOR progress
#    kubectl exec -it deploy/contractriskedge-worker -- celery -A app.workers status
#    Check embedding_runs table for job progress
#
# 3. VERIFY after completion
#    kubectl exec -it deploy/contractriskedge-api -- python -c "
#    from app.domains.vectors.partition import StaleEmbeddingInvalidator
#    from app.kernel.database.session import AsyncSessionLocal
#    import asyncio
#    async def verify():
#        async with AsyncSessionLocal() as session:
#            invalidator = StaleEmbeddingInvalidator(session, EmbeddingLifecycleManager())
#            report = await invalidator.get_invalidation_report()
#            print(f'Stale chunks: {report[\"stale_chunks\"]}')
#    asyncio.run(verify())
#    "
#
# 4. RUN search quality validation
#    pytest tests/ai_eval/ -k "test_smoke" -v

## Rollback
# - If rebuild fails: restore from vector DB backup
# - If quality degrades: revert to previous embedding model
# =============================================================================


# ══════════════════════════════════════════════════════════════════════════════
# 6. STUCK WORKFLOW RECOVERY
# ══════════════════════════════════════════════════════════════════════════════
# Impact: Contract review delays, SLA breaches
# Severity: Medium
# RTO: 30 minutes
# =============================================================================

## Detection
# - Alert: "Workflow SLA Breach" fires
# - Dashboard: Workflow SLA shows stuck workflows
# - Support ticket: review stuck in processing

## Recovery Steps
# 1. IDENTIFY stuck workflows
#    kubectl exec -it deploy/contractriskedge-api -- python -c "
#    from app.domains.workflows.runtime import WorkflowExecutionEngine
#    engine = WorkflowExecutionEngine()
#    stuck = engine.get_workflows_by_status('running')
#    for w in stuck:
#        print(f'Workflow {w.workflow_id[:8]}: step {w.current_step}, started {w.context.started_at}')
#    "
#
# 2. CHECK worker heartbeat
#    kubectl exec -it deploy/contractriskedge-worker -- celery -A app.workers inspect active
#
# 3. FORCE recovery if worker is dead
#    kubectl exec -it deploy/contractriskedge-api -- python -c "
#    from app.domains.queue import ReliableQueueManager
#    manager = ReliableQueueManager()
#    stuck = asyncio.run(manager.scan_stuck_jobs(timeout_seconds=120))
#    print(f'Recovered {len(stuck)} stuck jobs')
#    "
#
# 4. MANUALLY advance workflow if needed
#    - Verify workflow context is valid
#    - Skip failed step if non-critical
#    - Re-run from last successful step

## Prevention
# - Configure heartbeat timeouts appropriately
# - Add SLA timers to all workflow steps
# - Monitor queue depth for worker backlog
# =============================================================================


# ══════════════════════════════════════════════════════════════════════════════
# 7. DEPLOYMENT ROLLBACK
# ══════════════════════════════════════════════════════════════════════════════
# Impact: All platform features
# Severity: Critical
# RTO: 10 minutes
# =============================================================================

## Rollback Triggers
# - Error rate increases > 5% after deployment
# - p95 latency increases > 2x
# - Critical alert fires within 10 minutes of deployment
# - Tenant isolation violation detected

## Rollback Steps (Kubernetes)
# 1. ROLLBACK API deployment
#    kubectl rollout undo deployment/contractriskedge-api -n contractriskedge
#    kubectl rollout status deployment/contractriskedge-api -n contractriskedge
#
# 2. ROLLBACK worker deployment
#    kubectl rollout undo deployment/contractriskedge-worker -n contractriskedge
#    kubectl rollout status deployment/contractriskedge-worker -n contractriskedge
#
# 3. ROLLBACK database migration (if applicable)
#    alembic downgrade -1
#
# 4. VERIFY recovery
#    kubectl exec -it deploy/contractriskedge-api -- python -c "
#    import httpx
#    r = httpx.get('http://localhost:8000/health')
#    print(f'Health: {r.status_code} - {r.json()}')
#    r = httpx.get('http://localhost:8000/ready')
#    print(f'Ready: {r.status_code} - {r.json()}')
#    "

## Helm Rollback
# helm rollback contractriskedge REVISION -n contractriskedge

## Git Rollback
# git revert HEAD
# git push origin main

## Post-Rollback
# - Verify all health checks pass
# - Run DR validation suite
# - Notify stakeholders
# - Schedule root cause analysis
# =============================================================================


# ══════════════════════════════════════════════════════════════════════════════
# 8. CONFIGURATION DRIFT RESOLUTION
# ══════════════════════════════════════════════════════════════════════════════
# Impact: Inconsistent behavior across tenants/environments
# Severity: Medium
# RTO: 1 hour
# =============================================================================

## Detection
# - ConfigDriftDetector reports drifts
# - Support tickets about inconsistent behavior
# - A/B test results show unexpected variance

## Resolution Steps
# 1. RUN full drift scan
#    kubectl exec -it deploy/contractriskedge-api -- python -c "
#    from app.domains.platform.config.drift import ConfigDriftDetector
#    detector = ConfigDriftDetector()
#    report = asyncio.run(detector.run_full_drift_scan(...))
#    for d in report.drifts:
#        print(f'{d.severity.value}: {d.config_key} - {d.details}')
#    "
#
# 2. CLASSIFY drifts by severity
#    - Critical: fix immediately
#    - Warning: schedule for next sprint
#    - Info: clean up during maintenance
#
# 3. AUTO-REPAIR if supported
#    For auto_repairable drifts:
#    runtime_config.set(key, expected_value, changed_by='drift_detector')
#
# 4. MANUAL repair for non-auto-repairable
#    - Tenant overrides: update via admin console
#    - Environment configs: update .env files
#    - Feature flags: promote rollout to 100%

## Prevention
# - Add config drift scan to CI/CD pipeline
# - Set baseline configs for all environments
# - Review tenant overrides quarterly
# =============================================================================


# ══════════════════════════════════════════════════════════════════════════════
# 9. EVENT BUS FAILURE
# ══════════════════════════════════════════════════════════════════════════════
# Impact: Async processing, notifications, audit trail
# Severity: High
# RTO: 30 minutes
# =============================================================================

## Detection
# - Dead-letter queue growing rapidly
# - Events not being delivered to subscribers
# - Outbox table growing without consumption

## Recovery Steps
# 1. CHECK event bus health
#    kubectl exec -it deploy/contractriskedge-api -- python -c "
#    from app.domains.platform.events import UnifiedEventBus
#    bus = UnifiedEventBus(...)
#    stats = bus.get_stats()
#    print(f'DLQ: {stats[\"dead_letter_count\"]}, Subscriptions: {stats[\"active_subscriptions\"]}')
#    "
#
# 2. REQUEUE dead-letter events
#    for entry in bus.get_dead_letter_queue():
#        bus.requeue_dead_letter(entry.event_id)
#
# 3. REPLAY missed events from outbox
#    events = await bus.replay_events(from_time='2024-01-01T00:00:00')
#    for event in events:
#        await bus.publish(event['event_type'], event['payload'])
#
# 4. VERIFY delivery
#    Check subscriber handlers processed events correctly
# =============================================================================


# ══════════════════════════════════════════════════════════════════════════════
# 10. QUEUE POISON MESSAGE CLEANUP
# ══════════════════════════════════════════════════════════════════════════════
# Impact: Worker degradation, delayed processing
# Severity: Medium
# RTO: 1 hour
# =============================================================================

## Detection
# - Worker logs show repeated failures for same job
# - Queue depth growing despite low processing rate
# - Alert: "Dead-Letter Queue Growing"

## Cleanup Steps
# 1. IDENTIFY poison messages
#    kubectl exec -it deploy/contractriskedge-api -- python -c "
#    from app.domains.queue import ReliableQueueManager
#    manager = ReliableQueueManager()
#    dlq = manager.get_dead_letter_queue()
#    for entry in dlq:
#        print(f'Poison: {entry.job_id[:8]} type={entry.job_type} reason={entry.failure_reason[:100]}')
#    "
#
# 2. QUARANTINE suspicious jobs
#    for entry in dlq:
#        if entry.retry_count >= 5:
#            manager.quarantine_job(entry, reason='excessive_retries')
#
# 3. ANALYZE failure pattern
#    - Is it a code bug? → Fix and requeue
#    - Is it bad data? → Clean data and requeue
#    - Is it transient? → Requeue with higher retry limit
#
# 4. REQUEUE or DISCARD
#    for entry in dlq:
#        if entry.failure_reason != 'permanent_error':
#            await manager.requeue_from_dlq(entry.job_id)
# =============================================================================
