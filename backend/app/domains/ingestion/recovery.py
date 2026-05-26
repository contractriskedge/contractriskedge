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
    "analysis_pending",
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

    Args:
        db_factory: The shared tenant-aware session factory.

    Returns:
        A list of dicts describing each recovery action taken.
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
            SELECT upload_id::text, tenant_id::text, filename, ingestion_state,
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

            recovery_sql = sa_text("""
                UPDATE upload_sessions
                SET ingestion_state = 'failed',
                    ingestion_error = :error,
                    retry_count = retry_count + 1,
                    updated_at = NOW()
                WHERE upload_id = :upload_id::uuid
                  AND tenant_id = :tenant_id::uuid
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
