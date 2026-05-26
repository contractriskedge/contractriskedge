"""
Celery application configuration for integration workers.

Provides the shared Celery instance used by all integration task modules.
"""

import os

from celery import Celery
from structlog import get_logger

logger = get_logger(__name__)

# Broker and result backend URLs
BROKER_URL = os.environ.get(
    "CELERY_BROKER_URL",
    os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
)
RESULT_BACKEND = os.environ.get(
    "CELERY_RESULT_BACKEND",
    os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
)

celery_app = Celery(
    "contractriskedge_integration",
    broker=BROKER_URL,
    result_backend=RESULT_BACKEND,
)

# Configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes
    task_soft_time_limit=300,  # 5 minutes
    worker_max_tasks_per_child=200,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_retry_delay=60,
    task_max_retries=3,
    task_always_eager=os.environ.get("CELERY_ALWAYS_EAGER", "false").lower() == "true",
)

# Auto-discover tasks
celery_app.autodiscover_tasks(
    ["app.integration.workers"],
    related_name="tasks",
    force=True,
)

logger.info(
    "celery_app_configured",
    broker=BROKER_URL,
    result_backend=RESULT_BACKEND,
)
