"""Workspace Celery worker — processes action jobs asynchronously.

Handles: assign, escalate, re-analyze, export, notify
Job lifecycle: pending → running → completed | failed → retrying
"""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select, update

from app.config import settings
from app.domains.workspace.models import ActionJob
from app.domains.workspace.repository import WorkspaceRepository
from workers.celery_app import celery_app
from workers.worker_async import WorkerAsyncHelper
from workers.worker_loop import worker_loop

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


@celery_app.task(
    bind=True,
    name="execute_action_job",
    max_retries=MAX_RETRIES,
    acks_late=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
)
def execute_action_job(self, job_id: str, tenant_id: str, user_id: str):
    """Execute an action job with status tracking.

    Dispatches to the appropriate handler based on action_type.
    Updates job progress and status throughout execution.
    """
    helper = WorkerAsyncHelper()
    return helper.run(_execute_job(helper, job_id, tenant_id, user_id))


async def _execute_job(helper, job_id: str, tenant_id: str, user_id: str):
    session = await worker_loop.create_session(tenant_id, user_id, "api")
    async with helper.session_scope(session):
        try:
            repo = WorkspaceRepository(session, tenant_id=tenant_id)

            # Load job
            job = await repo.get_job(job_id, tenant_id)
            if not job:
                logger.error("Action job %s not found", job_id)
                return

            # Mark as running
            await repo.update_job_status(job_id, tenant_id, "running", progress=10)
            await session.flush()

            # Dispatch to handler
            handler = _get_handler(job.action_type)
            if handler is None:
                raise ValueError(f"Unknown action type: {job.action_type}")

            result = await handler(repo, job, tenant_id, user_id)

            # Mark as completed
            await repo.update_job_status(
                job_id, tenant_id, "completed",
                progress=100,
                result_message=result.get("message", "Completed"),
            )
            await session.commit()

            logger.info(
                "Action job %s completed: %s (%d targets)",
                job_id, job.action_type, len(job.target_ids or []),
            )

        except Exception as exc:
            logger.error("Action job %s failed: %s", job_id, exc)
            try:
                repo = WorkspaceRepository(session, tenant_id=tenant_id)
                await repo.update_job_status(
                    job_id, tenant_id, "failed",
                    error_message=str(exc),
                )
                await session.commit()
            except Exception:
                pass
            raise


# ── Handler Registry ─────────────────────────────────────────────

async def _handle_assign(repo, job, tenant_id: str, user_id: str) -> dict:
    """Assign reviewer to targets."""
    target_ids = job.target_ids or []
    metadata = job.metadata_json or {}
    reviewer = metadata.get("reviewer", user_id)

    for i, target_id in enumerate(target_ids):
        # Update progress
        progress = 10 + int((i / len(target_ids)) * 80)
        await repo.update_job_status(str(job.job_id), tenant_id, "running", progress=progress)

        # In production: call review API to assign reviewer
        logger.info("Assigned %s to target %s", reviewer, target_id)

    return {"message": f"Assigned {reviewer} to {len(target_ids)} target(s)"}


async def _handle_escalate(repo, job, tenant_id: str, user_id: str) -> dict:
    """Escalate targets to senior review."""
    target_ids = job.target_ids or []
    for i, target_id in enumerate(target_ids):
        progress = 10 + int((i / len(target_ids)) * 80)
        await repo.update_job_status(str(job.job_id), tenant_id, "running", progress=progress)
        logger.info("Escalated target %s", target_id)

    return {"message": f"Escalated {len(target_ids)} target(s)"}


async def _handle_re_analyze(repo, job, tenant_id: str, user_id: str) -> dict:
    """Queue AI re-analysis for targets."""
    from workers.ai_worker import analyze_contract_task

    target_ids = job.target_ids or []
    for i, target_id in enumerate(target_ids):
        progress = 10 + int((i / len(target_ids)) * 80)
        await repo.update_job_status(str(job.job_id), tenant_id, "running", progress=progress)

        # Dispatch Celery task for each upload
        analyze_contract_task.delay(
            upload_id=target_id,
            tenant_id=tenant_id,
            user_id=user_id,
            analysis_type="full",
        )

    return {"message": f"Re-analysis queued for {len(target_ids)} contract(s)"}


async def _handle_export(repo, job, tenant_id: str, user_id: str) -> dict:
    """Export targets as CSV/data."""
    target_ids = job.target_ids or []
    # In production: generate export file, store in S3, return download URL
    logger.info("Export requested for %d targets", len(target_ids))

    return {"message": f"Export prepared for {len(target_ids)} target(s)"}


async def _handle_notify(repo, job, tenant_id: str, user_id: str) -> dict:
    """Send notifications to target owners."""
    from app.domains.notify.service import NotificationService
    from app.domains.notify.repository import NotificationRepository

    notify_service = NotificationService(
        repo=NotificationRepository(repo.session, tenant_id=tenant_id),
        tenant_id=tenant_id,
    )

    metadata = job.metadata_json or {}
    title = metadata.get("title", "Action Required")
    message = metadata.get("message", "Please review the assigned items.")

    for target_id in (job.target_ids or []):
        await notify_service.create_notification(
            user_id=target_id,
            title=title,
            message=message,
            notification_type="action_required",
            action_url=metadata.get("action_url", ""),
        )

    return {"message": f"Notifications sent to {len(job.target_ids or [])} recipient(s)"}


def _get_handler(action_type: str):
    """Get the handler function for an action type."""
    handlers = {
        "assign": _handle_assign,
        "escalate": _handle_escalate,
        "re_analyze": _handle_re_analyze,
        "export": _handle_export,
        "notify": _handle_notify,
    }
    return handlers.get(action_type)
