"""Celery Beat schedule — periodic task configuration for workflow recovery and metrics.

Run with:
    celery -A app.workers.celery_beat beat --loglevel=info

Or combined with a worker:
    celery -A app.workers.celery_app worker --beat --loglevel=info
"""

from __future__ import annotations

from celery.schedules import crontab
from app.workers.celery_app import celery_app

# ── Periodic Task Schedule ─────────────────────────────────────────

celery_app.conf.beat_schedule = {
    # Workflow recovery — every 5 minutes
    "recover-stuck-workflows": {
        "task": "recover_stuck_workflows",
        "schedule": crontab(minute="*/5"),  # Every 5 minutes
        "args": (),
        "options": {"queue": "default"},
    },

    # SLA overdue check — every 5 minutes
    "check-sla-overdue": {
        "task": "check_sla_overdue",
        "schedule": crontab(minute="*/5"),  # Every 5 minutes
        "args": (),
        "options": {"queue": "default"},
    },

    # Obligation overdue check — every 5 minutes
    "check-obligations-overdue": {
        "task": "check_obligations_overdue",
        "schedule": crontab(minute="*/5"),  # Every 5 minutes
        "args": (),
        "options": {"queue": "default"},
    },

    # System metrics aggregation — every 15 minutes
    "aggregate-system-metrics": {
        "task": "aggregate_system_metrics",
        "schedule": crontab(minute="*/15"),  # Every 15 minutes
        "args": (),
        "options": {"queue": "default"},
    },

    # Idempotency record cleanup — every hour
    "cleanup-idempotency-records": {
        "task": "recover_stuck_workflows",  # Reuses the recovery task which includes cleanup
        "schedule": crontab(minute="0"),  # Every hour at :00
        "args": (),
        "options": {"queue": "default"},
    },

    # ── Benchmark Orchestration ───────────────────────────────────

    # Stale score detection — every 6 hours
    "benchmark-detect-stale": {
        "task": "benchmark.detect_stale",
        "schedule": crontab(minute="0", hour="*/6"),
        "args": (),
        "options": {"queue": "default"},
    },

    # Full benchmark recompute — nightly at 2:00 AM
    "benchmark-recompute-daily": {
        "task": "benchmark.recompute",
        "schedule": crontab(minute="0", hour="2"),
        "args": (),
        "options": {"queue": "default"},
    },

    # Embedding refresh — weekly on Sunday at 3:00 AM
    "benchmark-refresh-embeddings-weekly": {
        "task": "benchmark.refresh_embeddings",
        "schedule": crontab(minute="0", hour="3", day_of_week="sunday"),
        "args": (),
        "options": {"queue": "default"},
    },
}

# ── Timezone ───────────────────────────────────────────────────────

celery_app.conf.timezone = "UTC"
