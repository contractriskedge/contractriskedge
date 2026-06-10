"""Startup recovery for stuck uploads — production-grade resilience.

This module provides a startup hook that detects and recovers uploads
stuck in non-terminal states (e.g., ``uploaded``, ``validating``,
``validated``) that were abandoned due to a worker crash or restart.

It complements the periodic ``recover_stuck_workflows`` Celery Beat task
by catching uploads that became stuck *before* the next Beat cycle.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import text as sa_text

from app.config import settings
from app.kernel.database.session import TenantAwareSessionFactory

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────

# States that are NOT terminal — uploads in these states are "stuck"
# if they haven't progressed beyond the grace period.
_NON_TERMINAL_STATES = (
    "uploaded",
    "validating",
    "validated",
    "storage_confirmed",
    "ocr_pending",
    "ocr_processing",
    "ocr_complete",
    "chunking_pending",
    "embedding_pending",
    "analysis_pending",  # Re-dispatched, not marked as failed
)

# How long an upload can stay in a non-terminal state before we consider it stuck
STUCK_GRACE_MINUTES = 15


async def recover_stuck_uploads_on_startup(
    db_factory: TenantAwareSessionFactory,
) -> list[dict]:
    """Detect and recover uploads stuck in non-terminal states on startup.

    This is called during the FastAPI lifespan startup. It finds uploads
    that have been in a non-terminal state for longer than the grace period
    and marks them as ``failed`` with an appropriate error message.

    Uploads stuck in ``analysis_pending`` are handled differently — the AI
    analysis task is re-dispatched to Celery instead of marking as failed,
    since this state means the task was queued but not yet processed by a
    worker (e.g., during a deployment restart).
    """
    session = await db_factory.create_session(
        tenant_id="system",
        user_id="system",
        user_role="admin",
    )
    recovered: list[dict] = []

    try:
        # Find all stuck uploads across all tenants
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=STUCK_GRACE_MINUTES)

        stuck_sql = sa_text("""
            SELECT upload_id::text, tenant_id::text, user_id, filename, ingestion_state,
                   retry_count, updated_at
            FROM upload_sessions
            WHERE ingestion_state = ANY(:states)
              AND updated_at < :cutoff
            ORDER BY updated_at ASC
            LIMIT 50
        """)

        result = await session.execute(
            stuck_sql,
            {
                "states": list(_NON_TERMINAL_STATES),
                "cutoff": cutoff,
            },
        )
        stuck_uploads = result.fetchall()

        if not stuck_uploads:
            logger.info("[StartupRecovery] No stuck uploads found (threshold=%dmin)", STUCK_GRACE_MINUTES)
            return recovered

        logger.warning(
            "[StartupRecovery] Found %d stuck upload(s) — recovering...",
            len(stuck_uploads),
        )

        for row in stuck_uploads:
            upload_id = row.upload_id
            tenant_id = row.tenant_id
            state = row.ingestion_state
            age_minutes = round((datetime.now(timezone.utc) - row.updated_at).total_seconds() / 60, 1)

            # Re-dispatch pipeline work for recoverable states (worker may have died mid-step).
            if state in _NON_TERMINAL_STATES and (row.retry_count or 0) < 3:
                try:
                    from app.domains.ingestion.models import coerce_ingestion_state
                    from workers.ingestion_dispatch import redispatch_ingestion

                    ing_state = coerce_ingestion_state(state)
                    action_label = redispatch_ingestion(
                        upload_id,
                        tenant_id,
                        str(row.user_id or "system"),
                        ing_state,
                    )
                    if action_label:
                        await session.execute(
                            sa_text("""
                                UPDATE upload_sessions
                                SET retry_count = retry_count + 1,
                                    ingestion_error = :error,
                                    updated_at = NOW()
                                WHERE upload_id = CAST(:upload_id AS uuid)
                                  AND tenant_id = CAST(:tenant_id AS uuid)
                            """),
                            {
                                "upload_id": upload_id,
                                "tenant_id": tenant_id,
                                "error": (
                                    f"Startup recovery: re-queued {action_label} "
                                    f"after {age_minutes}min in {state}"
                                ),
                            },
                        )
                        action = {
                            "upload_id": upload_id,
                            "tenant_id": tenant_id[:8],
                            "filename": row.filename,
                            "previous_state": state,
                            "age_minutes": age_minutes,
                            "action": f"redispatched_{action_label}",
                        }
                        recovered.append(action)
                        logger.info(
                            "[StartupRecovery] Re-dispatched %s for upload %s "
                            "(stuck in %s for %dmin)",
                            action_label, upload_id[:8], state, int(age_minutes),
                        )
                        continue
                except Exception as exc:
                    logger.error(
                        "[StartupRecovery] Redispatch failed for %s: %s",
                        upload_id[:8], exc,
                    )

            recovery_sql = sa_text("""
                UPDATE upload_sessions
                SET ingestion_state = 'failed',
                    ingestion_error = :error,
                    retry_count = retry_count + 1,
                    updated_at = NOW()
                WHERE upload_id = CAST(:upload_id AS uuid)
                  AND tenant_id = CAST(:tenant_id AS uuid)
                  AND ingestion_state = :expected_state
            """)

            update_result = await session.execute(
                recovery_sql,
                {
                    "upload_id": upload_id,
                    "tenant_id": tenant_id,
                    "expected_state": state,
                    "error": (
                        f"Auto-recovered on startup: stuck in '{state}' "
                        f"for {age_minutes}min (grace={STUCK_GRACE_MINUTES}min)"
                    ),
                },
            )

            if update_result.rowcount > 0:
                action = {
                    "upload_id": upload_id,
                    "tenant_id": tenant_id[:8],
                    "filename": row.filename,
                    "previous_state": state,
                    "age_minutes": age_minutes,
                }
                recovered.append(action)
                logger.warning(
                    "[StartupRecovery] Recovered stuck upload %s (tenant=%s, file=%s, "
                    "state=%s, age=%dmin)",
                    upload_id[:8], tenant_id[:8], row.filename, state, int(age_minutes),
                )

        await session.commit()

    except Exception:
        await session.rollback()
        logger.exception("[StartupRecovery] Failed to recover stuck uploads")
        raise
    finally:
        await session.close()

    return recovered
