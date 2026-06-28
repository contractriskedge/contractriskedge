"""Celery shared tasks — document ingestion, obligation overdue checks, and system maintenance."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from celery import shared_task
from sqlalchemy import select, text as sa_text

from app.domains.obligations.models import Obligation, ObligationAuditLog

logger = logging.getLogger(__name__)


@shared_task(name="check_obligations_overdue", bind=True, max_retries=3, default_retry_delay=60)
def check_obligations_overdue(self):
    """Periodic task: mark obligations as overdue when due_date has passed.

    Runs every 5 minutes via Celery Beat.
    Finds all obligations where:
      - due_date < now
      - status NOT IN ('completed', 'waived', 'cancelled', 'archived', 'overdue')
    and sets status = 'overdue', logs an audit event.
    """
    from app.kernel.database.sync_session import get_sync_factory

    now = datetime.now(timezone.utc)
    factory = get_sync_factory()
    session = factory.create_session(tenant_id="system", user_id="system", user_role="admin")
    updated = 0

    try:
        # Get all active tenants
        tenants_sql = sa_text("SELECT tenant_id FROM tenants WHERE is_active = TRUE")
        tenants = session.execute(tenants_sql).fetchall()

        for (tenant_id,) in tenants:
            tenant_id_str = str(tenant_id)

            # Find obligations past due that aren't already resolved
            stmt = select(Obligation).where(
                Obligation.tenant_id == tenant_id_str,
                Obligation.due_date.isnot(None),
                Obligation.due_date < now,
                ~Obligation.status.in_(["completed", "waived", "cancelled", "archived", "overdue"]),
            )
            result = session.execute(stmt)
            obligations = result.scalars().all()

            for o in obligations:
                o.status = "overdue"
                o.updated_at = now

                # Log audit event
                audit = ObligationAuditLog(
                    tenant_id=o.tenant_id,
                    obligation_id=o.id,
                    contract_uuid_id=o.contract_uuid_id,
                    action="obligation.overdue",
                    actor="system",
                    changes={"reason": "due_date passed", "due_date": str(o.due_date)},
                    comment=f"Auto-marked overdue: due date {o.due_date.date()} has passed",
                )
                session.add(audit)
                updated += 1
                logger.info(
                    "Obligation overdue: id=%s tenant=%s due_date=%s",
                    o.id, tenant_id_str, o.due_date.date(),
                )

        session.commit()
    finally:
        session.close()

    logger.info("check_obligations_overdue complete: %d obligations marked overdue", updated)
    return {"marked_overdue": updated, "checked_at": now.isoformat()}


@shared_task(name="sync_signature_envelopes", bind=True, max_retries=3, default_retry_delay=60)
def sync_signature_envelopes(self):
    """Periodic task: poll DocuSign for completed envelopes and update local status."""
    from workers.worker_loop import worker_loop

    return worker_loop.run(_sync_signature_envelopes_async())


async def _sync_signature_envelopes_async():
    """Async implementation using the persistent worker event loop."""
    from workers.worker_loop import worker_loop

    session = await worker_loop.create_session("system", "system", "admin")
    async with worker_loop.session_scope(session):
        rows = await session.execute(
            sa_text("""
                SELECT id, tenant_id, provider_reference
                FROM signature_requests
                WHERE status = 'sent' AND provider_reference IS NOT NULL
            """)
        )
        requests = rows.fetchall()
        logger.info("sync_signature_envelopes: found %d sent envelopes to check", len(requests))

        synced = 0
        for row in requests:
            try:
                from app.domains.signature.service import SignatureService
                from app.domains.signature.repository import SignatureRepository
                from app.domains.signature.providers.factory import create_provider
                from app.config import settings

                repo = SignatureRepository(session, str(row.tenant_id))
                service = SignatureService(repo, actor_id="system")

                pname = "dev_auto_sign" if settings.environment == "development" else "docusign"
                provider = create_provider(pname)
                service.register_provider(pname, provider)

                result = await service.sync_envelope_status(str(row.id))
                if result:
                    synced += 1
                    logger.info(
                        "Synced envelope %s: %s", str(row.id)[:20], result.get("status"),
                    )
            except Exception as exc:
                logger.warning("Failed to sync envelope %s: %s", str(row.id)[:20], exc)

        await session.commit()
        logger.info("sync_signature_envelopes complete: %d/%d synced", synced, len(requests))
        return {
            "synced": synced,
            "total": len(requests),
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }