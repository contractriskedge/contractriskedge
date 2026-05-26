"""
OAuth token refresh Celery task.

Periodically refreshes expiring OAuth2 tokens to maintain connectivity.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from structlog import get_logger

from app.database import get_async_session
from app.integration.models.credential import IntegrationCredential
from app.integration.models.integration import Integration, IntegrationStatus
from app.integration.services.audit_service import IntegrationAuditService
from app.integration.services.oauth_service import OAuthService
from app.integration.services.telemetry import get_telemetry
from app.integration.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(
    bind=True,
    name="refresh_oauth_tokens_task",
    queue="oauth",
    autoretry_for=(Exception,),
    max_retries=2,
    retry_backoff=60,
)
def refresh_oauth_tokens_task(
    self,
    tenant_id: str,
    batch_size: int = 50,
) -> dict[str, Any]:
    """
    Refresh all OAuth2 tokens that are expiring soon.

    Scans for tokens expiring within the next 15 minutes and refreshes them.

    Args:
        tenant_id: Tenant UUID to process
        batch_size: Maximum number of tokens to refresh in one run

    Returns:
        Summary of refresh operations
    """
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            _refresh_oauth_tokens_async(
                tenant_id=uuid.UUID(tenant_id),
                batch_size=batch_size,
            )
        )
        return result
    finally:
        loop.close()


async def _refresh_oauth_tokens_async(
    tenant_id: uuid.UUID,
    batch_size: int = 50,
) -> dict[str, Any]:
    """Async implementation of OAuth token refresh."""
    telemetry = get_telemetry()
    refreshed = 0
    failed = 0
    skipped = 0

    async with get_async_session() as db:
        audit = IntegrationAuditService(db, tenant_id)
        oauth = OAuthService(
            db=db,
            tenant_id=tenant_id,
            audit=audit,
            telemetry=telemetry,
        )

        try:
            # Find credentials expiring within 15 minutes
            now = datetime.now(timezone.utc)
            expiry_threshold = now.replace(minute=now.minute + 15)

            result = await db.execute(
                select(IntegrationCredential)
                .join(
                    Integration,
                    IntegrationCredential.integration_id == Integration.id,
                )
                .where(
                    IntegrationCredential.tenant_id == tenant_id,
                    IntegrationCredential.is_revoked == False,
                    IntegrationCredential.is_expired == False,
                    IntegrationCredential.encrypted_refresh_token.isnot(None),
                    IntegrationCredential.oauth_access_token_expires_at <= expiry_threshold,
                    Integration.status == IntegrationStatus.ACTIVE,
                    Integration.is_deleted == False,
                )
                .limit(batch_size)
            )
            credentials = list(result.scalars().all())

            if not credentials:
                logger.info(
                    "no_tokens_to_refresh",
                    tenant_id=str(tenant_id),
                )
                return {
                    "refreshed": 0,
                    "failed": 0,
                    "skipped": 0,
                    "total_found": 0,
                }

            logger.info(
                "refreshing_oauth_tokens",
                tenant_id=str(tenant_id),
                count=len(credentials),
            )

            for credential in credentials:
                try:
                    await oauth.refresh_token(
                        integration_id=credential.integration_id,
                        force=False,
                    )
                    refreshed += 1
                    logger.info(
                        "token_refreshed",
                        integration_id=str(credential.integration_id),
                        credential_id=str(credential.id),
                    )
                except Exception as exc:
                    failed += 1
                    logger.error(
                        "token_refresh_failed",
                        integration_id=str(credential.integration_id),
                        credential_id=str(credential.id),
                        error=str(exc),
                    )
                    telemetry.record_oauth_refresh(
                        provider=credential.oauth_provider or "unknown",
                        success=False,
                    )

        except Exception as exc:
            logger.error(
                "oauth_refresh_batch_failed",
                tenant_id=str(tenant_id),
                error=str(exc),
            )
            raise
        finally:
            await oauth.close()

    return {
        "refreshed": refreshed,
        "failed": failed,
        "skipped": skipped,
        "total_found": refreshed + failed + skipped,
    }
