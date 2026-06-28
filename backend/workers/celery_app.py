"""Celery application configuration.

All worker tasks must include tenant_id in kwargs.
Tasks without tenant_id are rejected at submission time.
"""

from __future__ import annotations

from celery import Celery, signals
from celery.schedules import crontab
from kombu import Queue

from app.config import settings
from app.kernel.database.orm_registry import register_orm_models

# Register FK targets (tenants, etc.) before any worker task touches the ORM.
# Note: This runs in the parent process before fork. After fork, each child
# process re-registers via worker_process_init below.
register_orm_models()

celery_app = Celery(
    "contractrisk",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    broker_transport_options={
        "socket_connect_timeout": 3,
        "socket_timeout": 3,
    },
    # Task timeouts — prevent stuck jobs from running indefinitely
    task_time_limit=1800,       # 30 minutes hard limit
    task_soft_time_limit=1200,  # 20 minutes soft limit (raises SoftTimeLimitExceeded)
    # Unrouted tasks must land on a queue the worker consumes (not Celery's legacy "celery" queue).
    task_default_queue="default",
    task_queues=[
        Queue("ingestion"),
        Queue("ai"),
        Queue("notifications"),
        Queue("email"),
        Queue("default"),
        Queue("celery"),  # drain legacy backlog from before routes were fixed
    ],
    task_routes={
        # Ingestion pipeline (registered with short names, not workers.ingestion.*)
        "ingest_document": {"queue": "ingestion"},
        "validate_upload": {"queue": "ingestion"},
        "confirm_storage": {"queue": "ingestion"},
        "start_ocr_pipeline": {"queue": "ingestion"},
        "extract_document": {"queue": "ingestion"},
        "chunk_document": {"queue": "ingestion"},
        "generate_embeddings": {"queue": "ingestion"},
        "ingestion.extract_document": {"queue": "ingestion"},
        "ingestion.chunk_document": {"queue": "ingestion"},
        "ingestion.generate_embeddings": {"queue": "ingestion"},
        "ingestion.finalize": {"queue": "ingestion"},
        # Other workers
        "analyze_contract": {"queue": "ai"},
        "deliver_notification": {"queue": "notifications"},
        "process_workflow_timers": {"queue": "notifications"},
        "send_email": {"queue": "email"},
        "check_sla_overdue": {"queue": "default"},
        "check_obligations_overdue": {"queue": "default"},
    },
    beat_schedule={
        # Workflow recovery — every 5 minutes
        "recover-stuck-workflows": {
            "task": "recover_stuck_workflows",
            "schedule": crontab(minute="*/5"),
            "args": (),
            "options": {"queue": "default"},
        },
        # SLA overdue check — every 5 minutes
        "check-sla-overdue": {
            "task": "check_sla_overdue",
            "schedule": crontab(minute="*/5"),
            "args": (),
            "options": {"queue": "default"},
        },
        # Obligation overdue check — every 5 minutes
        "check-obligations-overdue": {
            "task": "check_obligations_overdue",
            "schedule": crontab(minute="*/5"),
            "args": (),
            "options": {"queue": "default"},
        },
        # System metrics aggregation — every 15 minutes
        "aggregate-system-metrics": {
            "task": "aggregate_system_metrics",
            "schedule": crontab(minute="*/15"),
            "args": (),
            "options": {"queue": "default"},
        },
        # Idempotency record cleanup — every hour
        # Note: _cleanup_idempotency_records() is also called inside
        # recover_stuck_workflows (every 5 min), so this hourly entry
        # is redundant but kept for explicit visibility. It runs the
        # same recovery task which includes cleanup as a sub-step.
        "cleanup-idempotency-records": {
            "task": "recover_stuck_workflows",
            "schedule": crontab(minute="0"),
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

        # Email queue processing — every minute
        "process-email-queue": {
            "task": "send_email",
            "schedule": crontab(minute="*"),  # Every minute
            "args": (),
            "options": {"queue": "email"},
        },

        # Signature envelope status sync — every 2 minutes
        "sync-signature-envelopes": {
            "task": "sync_signature_envelopes",
            "schedule": crontab(minute="*/2"),
            "args": (),
            "options": {"queue": "default"},
        },
    },
    timezone="UTC",
)

# Task modules are loaded by the worker via `imports` below.
# Do NOT import task modules here — that creates a circular import with
# workers.ingestion (which imports celery_app).
celery_app.conf.imports = (
    "workers.ingestion_tasks",
    "workers.ingestion",
    "workers.ingestion_ocr",
    "workers.extraction",
    "workers.vectors",
    "workers.ai_worker",
    "workers.notifications",
    "app.workers.ingestion_pipeline",
    "app.workers.sla_check",
    "app.workers.recovery",
    "app.workers.benchmark",
    "app.workers.email_worker",
    "app.workers.tasks",
)


# ── Fork Safety ────────────────────────────────────────────────────
# Celery uses ``prefork`` pool by default, which forks worker processes.
# After fork, the child process inherits the parent's async event loop
# and SQLAlchemy engine in an inconsistent state, which can cause
# SIGSEGV (signal 11) when the child tries to create a new sync session.
#
# We reset the WorkerLoop after each fork so each child gets a fresh
# event loop and engine.  This also avoids ``Event loop is closed`` and
# ``Future attached to a different loop`` errors.


@signals.worker_process_init.connect
def _reset_worker_loop_after_fork(**kwargs) -> None:
    """Reset the WorkerLoop after Celery forks a new worker process.

    The parent process's event loop and engine are invalid in the child.
    We must clear them so the child creates fresh ones on first use.
    """
    from workers.worker_loop import worker_loop

    worker_loop.reset()
    logger = logging.getLogger(__name__)
    logger.info("WorkerLoop reset after fork (pid=%s)", os.getpid())


import logging
import os
