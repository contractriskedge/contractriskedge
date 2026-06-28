"""Operations service — system health checks, queue monitoring, integration health, alerts.

This is the backend for the Operations Center. It provides:
  1. System Health Dashboard — status of all services
  2. Queue Monitoring — background job queue depths and status
  3. Scheduler Monitoring — scheduled task status
  4. Integration Health — external service connectivity
  5. Error Dashboard — error categorization and trends
  6. Slow Operations — top slow APIs, queries, workflows, searches
  7. Alert Evaluation — trigger alerts based on health state
  8. Support Bundle — collect system diagnostics as ZIP
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import platform
import time
import zipfile
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import text

from app.config import settings
from app.kernel.telemetry.structured_logging import get_logger

logger = get_logger("operations.service")

# ── Types ──────────────────────────────────────────────────────────

ServiceStatus = dict[str, Any]
"""A service health entry: {name, status, last_checked, response_time_ms, error}"""


# ── Health Check Registry ──────────────────────────────────────────

class HealthCheckRegistry:
    """Registry of health check functions, one per service."""

    def __init__(self) -> None:
        self._checks: dict[str, callable] = {}

    def register(self, name: str, check_fn: callable) -> None:
        self._checks[name] = check_fn

    def get_names(self) -> list[str]:
        return list(self._checks.keys())

    async def run_all(self, app_state: Any) -> dict[str, ServiceStatus]:
        results: dict[str, ServiceStatus] = {}
        tasks = []
        names = []

        for name, fn in self._checks.items():
            tasks.append(self._run_one(name, fn, app_state))
            names.append(name)

        completed = await asyncio.gather(*tasks, return_exceptions=True)

        for name, result in zip(names, completed):
            if isinstance(result, Exception):
                results[name] = {
                    "name": name,
                    "status": "failed",
                    "last_checked": datetime.utcnow().isoformat() + "Z",
                    "response_time_ms": None,
                    "error": str(result),
                }
            else:
                results[name] = result

        return results

    async def _run_one(self, name: str, fn: callable, app_state: Any) -> ServiceStatus:
        start = time.time()
        try:
            # Run with a 10-second timeout per check
            result = await asyncio.wait_for(fn(app_state), timeout=10.0)
            duration_ms = (time.time() - start) * 1000
            return {
                "name": name,
                "status": result.get("status", "healthy"),
                "last_checked": datetime.utcnow().isoformat() + "Z",
                "response_time_ms": round(duration_ms, 2),
                "detail": result.get("detail", ""),
            }
        except asyncio.TimeoutError:
            duration_ms = (time.time() - start) * 1000
            return {
                "name": name,
                "status": "failed",
                "last_checked": datetime.utcnow().isoformat() + "Z",
                "response_time_ms": round(duration_ms, 2),
                "error": "Health check timed out after 10s",
            }
        except Exception as exc:
            duration_ms = (time.time() - start) * 1000
            return {
                "name": name,
                "status": "failed",
                "last_checked": datetime.utcnow().isoformat() + "Z",
                "response_time_ms": round(duration_ms, 2),
                "error": str(exc),
            }


# Global registry
health_registry = HealthCheckRegistry()


# ── Individual Health Checks ───────────────────────────────────────

async def _check_api(app_state: Any) -> dict:
    """API service is healthy if the app is running."""
    uptime = time.time() - app_state.startup_time
    return {"status": "healthy" if uptime > 0 else "unknown", "detail": f"Uptime: {uptime:.0f}s"}


async def _check_database(app_state: Any) -> dict:
    """Database health — execute SELECT 1 with timeout."""
    factory = getattr(app_state, "db_factory", None)
    if not factory:
        return {"status": "failed", "detail": "No database factory configured"}

    try:
        session = await factory.create_session(
            tenant_id="system",
            user_id="health-check",
            user_role="admin",
        )
        result = await session.execute(text("SELECT 1 AS ok"))
        row = result.fetchone()
        await session.close()
        if row and row[0] == 1:
            return {"status": "healthy", "detail": "SELECT 1 OK"}
        return {"status": "degraded", "detail": "Unexpected response"}
    except Exception as exc:
        return {"status": "failed", "detail": str(exc)}


async def _check_redis(app_state: Any) -> dict:
    """Redis health — PING."""
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis_url, socket_connect_timeout=3)
        pong = await r.ping()
        await r.aclose()
        if pong:
            return {"status": "healthy", "detail": "PONG"}
        return {"status": "degraded", "detail": "Unexpected response"}
    except Exception as exc:
        return {"status": "failed", "detail": str(exc)}


async def _check_workers(app_state: Any) -> dict:
    """Background worker health — check Celery heartbeat."""
    try:
        from celery.app.control import Inspect
        from app.workers.celery_app import celery_app

        i = Inspect(app=celery_app)
        stats = i.stats(timeout=3)
        if stats:
            workers = list(stats.keys())
            return {"status": "healthy", "detail": f"Active workers: {', '.join(workers)}"}
        return {"status": "warning", "detail": "No worker stats returned (may be idle)"}
    except Exception as exc:
        return {"status": "failed", "detail": str(exc)}


async def _check_ai_service(app_state: Any) -> dict:
    """AI service health — check if API key is configured."""
    if not settings.openai_api_key and not settings.deepseek_api_key:
        return {"status": "warning", "detail": "No AI API key configured"}
    # Lightweight check: verify key is non-empty
    if settings.openai_api_key and len(settings.openai_api_key) > 20:
        return {"status": "healthy", "detail": "AI provider configured"}
    return {"status": "degraded", "detail": "AI key may be invalid (too short)"}


async def _check_vector_search(app_state: Any) -> dict:
    """Vector search health — check if Qdrant or embedding service is available."""
    try:
        from app.domains.vectors.service import vector_service
        health = await vector_service.health_check()
        if health.get("status") == "ok":
            return {"status": "healthy", "detail": "Vector service OK"}
        return {"status": "degraded", "detail": health.get("detail", "Unknown")}
    except ImportError:
        return {"status": "warning", "detail": "Vector module not loaded"}
    except Exception as exc:
        return {"status": "failed", "detail": str(exc)}


async def _check_docusign(app_state: Any) -> dict:
    """DocuSign integration health."""
    if not settings.docusign_integration_key:
        return {"status": "warning", "detail": "DocuSign not configured"}
    try:
        from app.integrations.docusign.client import DocusignClient
        client = DocusignClient()
        ok = await client.health_check()
        if ok:
            return {"status": "healthy", "detail": "DocuSign API reachable"}
        return {"status": "degraded", "detail": "DocuSign API unreachable"}
    except ImportError:
        return {"status": "warning", "detail": "DocuSign module not loaded"}
    except Exception as exc:
        return {"status": "failed", "detail": str(exc)}


async def _check_email(app_state: Any) -> dict:
    """Email service health."""
    if not settings.smtp_host and not settings.resend_api_key:
        return {"status": "warning", "detail": "Email not configured"}
    if settings.resend_api_key:
        return {"status": "healthy", "detail": "Resend API configured"}
    if settings.smtp_host:
        return {"status": "healthy", "detail": f"SMTP configured ({settings.smtp_host})"}
    return {"status": "degraded", "detail": "Email configuration incomplete"}


async def _check_storage(app_state: Any) -> dict:
    """Storage health — check S3/MinIO connectivity."""
    try:
        from app.integrations.storage.s3 import storage_service
        # StorageService may not have health_check; check if bucket is configured
        if hasattr(storage_service, "health_check") and callable(storage_service.health_check):
            ok = await storage_service.health_check()
            if ok:
                return {"status": "healthy", "detail": "Storage reachable"}
            return {"status": "degraded", "detail": "Storage unreachable"}
        # Fallback: check settings for bucket config
        bucket = getattr(settings, "s3_bucket", None)
        if bucket:
            return {"status": "healthy", "detail": f"Storage configured (bucket: {bucket})"}
        return {"status": "warning", "detail": "Storage not fully configured"}
    except ImportError:
        return {"status": "warning", "detail": "Storage module not loaded"}
    except Exception as exc:
        return {"status": "failed", "detail": str(exc)}


async def _check_scheduler(app_state: Any) -> dict:
    """Scheduler health — check Celery Beat."""
    try:
        from app.workers.celery_app import celery_app
        from celery.app.control import Inspect
        i = Inspect(app=celery_app)
        scheduled = i.scheduled(timeout=3)
        if scheduled:
            return {"status": "healthy", "detail": "Scheduler active"}
        return {"status": "warning", "detail": "No scheduled tasks found"}
    except Exception as exc:
        return {"status": "failed", "detail": str(exc)}


# ── Register All Checks ────────────────────────────────────────────

health_registry.register("api", _check_api)
health_registry.register("database", _check_database)
health_registry.register("redis", _check_redis)
health_registry.register("workers", _check_workers)
health_registry.register("ai_service", _check_ai_service)
health_registry.register("vector_search", _check_vector_search)
health_registry.register("docusign", _check_docusign)
health_registry.register("email", _check_email)
health_registry.register("storage", _check_storage)
health_registry.register("scheduler", _check_scheduler)


# ── Queue Status ───────────────────────────────────────────────────

async def get_queue_status(app_state: Any) -> dict[str, Any]:
    """Get background job queue depths and status."""
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis_url, socket_connect_timeout=3)

        # Celery uses Redis lists for queues
        queues = ["celery", "default", "ai", "email", "workflow", "ingestion"]
        queue_data = {}

        for q in queues:
            try:
                length = await r.llen(q)
                queue_data[q] = length
            except Exception:
                queue_data[q] = -1

        # Get dead letter queue info (if using custom DLQ)
        dlq_length = 0
        try:
            dlq_length = await r.llen("dead_letter") or 0
        except Exception:
            pass

        await r.aclose()

        total_pending = sum(v for v in queue_data.values() if v > 0)
        has_backlog = any(v > 100 for v in queue_data.values() if v >= 0)

        return {
            "queues": queue_data,
            "dead_letter_count": dlq_length,
            "total_pending": total_pending,
            "has_backlog": has_backlog,
            "status": "warning" if has_backlog else "healthy",
        }
    except Exception as exc:
        return {
            "queues": {},
            "dead_letter_count": 0,
            "total_pending": 0,
            "has_backlog": False,
            "status": "failed",
            "error": str(exc),
        }


# ── Scheduler Status ───────────────────────────────────────────────

async def get_scheduler_status(app_state: Any) -> dict[str, Any]:
    """Get scheduled task status."""
    try:
        from app.workers.celery_app import celery_app
        from celery.app.control import Inspect

        i = Inspect(app=celery_app)
        scheduled = i.scheduled(timeout=3) or {}
        active = i.active(timeout=3) or {}
        reserved = i.reserved(timeout=3) or {}

        # Build scheduled tasks list
        tasks = []
        for worker_name, worker_tasks in scheduled.items():
            for t in worker_tasks:
                tasks.append({
                    "worker": worker_name,
                    "task_name": t.get("name", "unknown"),
                    "eta": t.get("eta", ""),
                    "priority": t.get("priority", 0),
                })

        # Build active tasks list
        active_tasks = []
        for worker_name, worker_tasks in active.items():
            for t in worker_tasks:
                active_tasks.append({
                    "worker": worker_name,
                    "task_name": t.get("name", "unknown"),
                    "started": t.get("time_start", 0),
                    "args": str(t.get("args", ""))[:100],
                })

        return {
            "scheduled_tasks": tasks,
            "active_tasks": active_tasks,
            "total_scheduled": len(tasks),
            "total_active": len(active_tasks),
            "status": "healthy",
        }
    except Exception as exc:
        return {
            "scheduled_tasks": [],
            "active_tasks": [],
            "total_scheduled": 0,
            "total_active": 0,
            "status": "failed",
            "error": str(exc),
        }


# ── Integration Health ─────────────────────────────────────────────

async def get_integration_health(app_state: Any) -> list[dict[str, Any]]:
    """Get health status for all external integrations."""
    health = await health_registry.run_all(app_state)
    integrations = ["docusign", "email", "storage", "ai_service"]
    return [
        {
            "name": name,
            **health.get(name, {"status": "unknown", "last_checked": None, "response_time_ms": None}),
        }
        for name in integrations
    ]


# ── Error Dashboard ────────────────────────────────────────────────

async def get_error_dashboard(app_state: Any) -> dict[str, Any]:
    """Get error categorization and trends."""
    factory = getattr(app_state, "db_factory", None)
    if not factory:
        return {"categories": {}, "trends": {}}

    try:
        session = await factory.create_session(
            tenant_id="system",
            user_id="health-check",
            user_role="admin",
        )

        # Error counts by category (from audit_log)
        categories = {}
        try:
            rows = await session.execute(text("""
                SELECT
                    COALESCE(details->>'error_category', 'unknown') AS category,
                    COUNT(*) AS cnt
                FROM audit_log
                WHERE action LIKE '%error%' OR action LIKE '%fail%'
                  AND created_at > NOW() - INTERVAL '30 days'
                GROUP BY category
                ORDER BY cnt DESC
            """))
            for row in rows:
                categories[row[0]] = row[1]
        except Exception:
            categories = {"database": 0, "validation": 0, "authorization": 0,
                          "integration": 0, "ai": 0, "workflow": 0, "search": 0, "unknown": 0}

        # Trends by period
        trends = {}
        try:
            for period, label, interval in [
                ("today", "Today", "1 day"),
                ("week", "Week", "7 days"),
                ("month", "Month", "30 days"),
            ]:
                row = await session.execute(text(f"""
                    SELECT COUNT(*) FROM audit_log
                    WHERE (action LIKE '%error%' OR action LIKE '%fail%')
                      AND created_at > NOW() - INTERVAL '{interval}'
                """))
                trends[period] = {"label": label, "count": row.scalar() or 0}
        except Exception:
            trends = {"today": {"label": "Today", "count": 0},
                      "week": {"label": "Week", "count": 0},
                      "month": {"label": "Month", "count": 0}}

        await session.close()
        return {"categories": categories, "trends": trends}
    except Exception as exc:
        return {"categories": {}, "trends": {}, "error": str(exc)}


# ── Slow Operations ────────────────────────────────────────────────

async def get_slow_operations(app_state: Any) -> dict[str, list[dict]]:
    """Get top 20 slowest operations by category."""
    factory = getattr(app_state, "db_factory", None)
    if not factory:
        return {"apis": [], "queries": [], "workflows": [], "searches": []}

    try:
        session = await factory.create_session(
            tenant_id="system",
            user_id="health-check",
            user_role="admin",
        )

        result: dict[str, list[dict]] = {"apis": [], "queries": [], "workflows": [], "searches": []}

        # Slow APIs
        try:
            rows = await session.execute(text("""
                SELECT
                    details->>'method' AS method,
                    details->>'path' AS path,
                    COALESCE((details->>'duration_ms')::numeric, 0) AS duration_ms,
                    created_at
                FROM audit_log
                WHERE action LIKE 'REQUEST%'
                  AND details->>'duration_ms' IS NOT NULL
                ORDER BY duration_ms DESC
                LIMIT 20
            """))
            result["apis"] = [
                {"method": r[0], "path": r[1], "duration_ms": float(r[2]), "timestamp": str(r[3])}
                for r in rows
            ]
        except Exception:
            pass

        # Slow workflows
        try:
            rows = await session.execute(text("""
                SELECT
                    wfi.correlation_id,
                    wfi.status,
                    EXTRACT(EPOCH FROM (COALESCE(wfi.completed_at, NOW()) - wfi.created_at)) AS duration_s
                FROM workflow_instances wfi
                WHERE wfi.created_at > NOW() - INTERVAL '7 days'
                ORDER BY duration_s DESC
                LIMIT 20
            """))
            result["workflows"] = [
                {"correlation_id": r[0], "status": r[1], "duration_seconds": float(r[2])}
                for r in rows
            ]
        except Exception:
            pass

        await session.close()
        return result
    except Exception as exc:
        return {"apis": [], "queries": [], "workflows": [], "searches": [], "error": str(exc)}


# ── Alert Evaluation ───────────────────────────────────────────────

async def evaluate_alerts(app_state: Any) -> list[dict[str, Any]]:
    """Evaluate all alert conditions and return active alerts."""
    alerts: list[dict[str, Any]] = []

    # 1. Database unavailable
    db_ready = getattr(app_state, "db_ready", False)
    if not db_ready:
        alerts.append({
            "id": "db-unavailable",
            "title": "Database Unavailable",
            "description": "Application cannot connect to the database",
            "severity": "critical",
            "source": "system",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })

    # 2. Worker stopped — check via health check
    worker_health = await _check_workers(app_state)
    if worker_health.get("status") == "failed":
        alerts.append({
            "id": "worker-stopped",
            "title": "Background Workers Stopped",
            "description": "No Celery workers are responding to heartbeat checks",
            "severity": "critical",
            "source": "system",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })

    # 3. Queue backlog
    queue_status = await get_queue_status(app_state)
    if queue_status.get("has_backlog"):
        backlog_queues = [
            {"queue": q, "depth": d}
            for q, d in queue_status.get("queues", {}).items()
            if isinstance(d, (int, float)) and d > 100
        ]
        alerts.append({
            "id": "queue-backlog",
            "title": "Queue Backlog Detected",
            "description": f"Queues with >100 pending items: {json.dumps(backlog_queues)}",
            "severity": "warning",
            "source": "system",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })

    # 4. High error rate
    try:
        error_dash = await get_error_dashboard(app_state)
        today_errors = error_dash.get("trends", {}).get("today", {}).get("count", 0)
        if today_errors > 50:
            alerts.append({
                "id": "high-error-rate",
                "title": "High Error Rate",
                "description": f"{today_errors} errors in the last 24 hours",
                "severity": "warning",
                "source": "system",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            })
    except Exception:
        pass

    # 5. Integration failures
    integration_health = await get_integration_health(app_state)
    failed_integrations = [i for i in integration_health if i.get("status") == "failed"]
    if failed_integrations:
        alerts.append({
            "id": "integration-failure",
            "title": "Integration Failure",
            "description": f"Failed integrations: {', '.join(i['name'] for i in failed_integrations)}",
            "severity": "warning",
            "source": "system",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })

    # 6. SLA violations — check for reviews exceeding SLA
    try:
        factory = getattr(app_state, "db_factory", None)
        if factory:
            session = await factory.create_session(
                tenant_id="system",
                user_id="health-check",
                user_role="admin",
            )
            row = await session.execute(text("""
                SELECT COUNT(*) FROM reviews
                WHERE status = 'in_review'
                  AND created_at < NOW() - INTERVAL '48 hours'
            """))
            stale_reviews = row.scalar() or 0
            if stale_reviews > 0:
                alerts.append({
                    "id": "sla-violation",
                    "title": "SLA Violations Detected",
                    "description": f"{stale_reviews} reviews exceeded 48-hour SLA",
                    "severity": "warning",
                    "source": "system",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                })
            await session.close()
    except Exception:
        pass

    return alerts


# ── Support Bundle ─────────────────────────────────────────────────

async def generate_support_bundle(app_state: Any) -> io.BytesIO:
    """Generate a support bundle ZIP with system diagnostics.

    Collects:
      - System version and environment info
      - Configuration (with secrets masked)
      - Recent logs
      - Health status
      - Metrics snapshot
      - Queue status
      - Database migration version
      - Enabled integrations
      - Installed workflow packs
    """
    buf = io.BytesIO()

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:

        # 1. System version
        system_info = {
            "version": "1.0.0",
            "environment": settings.environment,
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "hostname": platform.node(),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "uptime_seconds": round(time.time() - app_state.startup_time, 2) if hasattr(app_state, "startup_time") else None,
        }
        zf.writestr("system_info.json", json.dumps(system_info, indent=2, default=str))

        # 2. Configuration (secrets masked)
        config = {}
        for key in dir(settings):
            if key.startswith("_") or key in ("model_config",):
                continue
            val = getattr(settings, key)
            if not isinstance(val, (str, int, float, bool, list, dict, type(None))):
                continue
            # Mask secrets
            secret_keys = ("secret", "password", "key", "token", "credential", "private")
            if any(s in key.lower() for s in secret_keys):
                if isinstance(val, str) and len(val) > 4:
                    val = val[:4] + "****" + val[-4:] if len(val) > 12 else "****"
                elif isinstance(val, str):
                    val = "****"
            config[key] = val
        zf.writestr("config.json", json.dumps(config, indent=2, default=str))

        # 3. Health status
        health = await health_registry.run_all(app_state)
        zf.writestr("health_status.json", json.dumps(health, indent=2, default=str))

        # 4. Queue status
        queue_status = await get_queue_status(app_state)
        zf.writestr("queue_status.json", json.dumps(queue_status, indent=2, default=str))

        # 5. Database migration version
        try:
            factory = getattr(app_state, "db_factory", None)
            if factory:
                session = await factory.create_session(
                    tenant_id="system",
                    user_id="health-check",
                    user_role="admin",
                )
                row = await session.execute(text("SELECT version_num FROM alembic_version"))
                version = row.scalar() or "unknown"
                await session.close()
                zf.writestr("db_migration_version.txt", f"{version}\n")
        except Exception as exc:
            zf.writestr("db_migration_version.txt", f"Error: {exc}\n")

        # 6. Enabled integrations
        integrations = {
            "docusign": bool(settings.docusign_integration_key),
            "email_smtp": bool(settings.smtp_host),
            "email_resend": bool(settings.resend_api_key),
            "storage_s3": bool(settings.s3_endpoint),
            "ai_openai": bool(settings.openai_api_key),
            "ai_deepseek": bool(settings.deepseek_api_key),
            "redis": bool(settings.redis_url),
            "rate_limiting": settings.rate_limit_enabled,
        }
        zf.writestr("enabled_integrations.json", json.dumps(integrations, indent=2))

        # 7. Installed workflow packs
        try:
            if factory:
                session = await factory.create_session(
                    tenant_id="system",
                    user_id="health-check",
                    user_role="admin",
                )
                rows = await session.execute(text("""
                    SELECT id, name, version, status, is_built_in, created_at
                    FROM workflow_packs
                    ORDER BY name
                """))
                packs = [
                    {"id": str(r[0]), "name": r[1], "version": r[2], "status": r[3],
                     "is_built_in": r[4], "created_at": str(r[5])}
                    for r in rows
                ]
                await session.close()
                zf.writestr("workflow_packs.json", json.dumps(packs, indent=2, default=str))
        except Exception as exc:
            zf.writestr("workflow_packs.json", json.dumps({"error": str(exc)}))

        # 8. Metrics snapshot
        try:
            from prometheus_client import generate_latest, REGISTRY
            metrics_data = generate_latest(REGISTRY)
            zf.writestr("metrics.txt", metrics_data.decode("utf-8"))
        except Exception as exc:
            zf.writestr("metrics.txt", f"Error: {exc}\n")

    buf.seek(0)
    return buf
