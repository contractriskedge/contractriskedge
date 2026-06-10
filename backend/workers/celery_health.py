"""Lightweight Celery broker/worker availability checks for ingestion fallbacks."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def ingestion_workers_available(timeout: float = 1.0) -> bool:
    """Return True if at least one worker is consuming the ingestion queue."""
    try:
        from workers.celery_app import celery_app

        inspect = celery_app.control.inspect(timeout=timeout)
        if inspect is None:
            return False

        active_queues = inspect.active_queues() or {}
        for worker_queues in active_queues.values():
            for queue in worker_queues:
                if queue.get("name") == "ingestion":
                    return True
        return False
    except Exception as exc:
        logger.debug("Celery worker inspection failed: %s", exc)
        return False
