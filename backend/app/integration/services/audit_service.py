"""
Integration Audit Service — immutable audit trail for all integration operations.

Records every lifecycle event, credential change, sync operation, and
governance action with full context for compliance and observability.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.integration.models.audit import IntegrationAuditEvent

logger = get_logger(__name__)


class IntegrationAuditService:
    """
    Immutable audit event logger for integration subsystem.

    Every method creates an audit record that cannot be modified or deleted.
    """

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id

    async def log_event(
        self,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        integration_id: Optional[uuid.UUID] = None,
        actor_id: Optional[uuid.UUID] = None,
        actor_type: str = "system",
        previous_state: Optional[dict[str, Any]] = None,
        new_state: Optional[dict[str, Any]] = None,
        change_summary: Optional[str] = None,
        correlation_id: Optional[uuid.UUID] = None,
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        success: Optional[bool] = None,
        error_message: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> IntegrationAuditEvent:
        """
        Create an immutable audit event record.

        Args:
            action: The action performed (e.g., 'integration_created', 'token_refreshed')
            resource_type: Type of resource affected (e.g., 'integration', 'credential')
            resource_id: ID of the affected resource
            integration_id: Related integration ID
            actor_id: Who/what performed the action
            actor_type: 'user', 'system', 'admin', 'scheduler'
            previous_state: State before the change
            new_state: State after the change
            change_summary: Human-readable summary
            correlation_id: Trace identifier
            source_ip: Originating IP
            user_agent: Client user agent
            request_id: HTTP request ID
            success: Whether the operation succeeded
            error_message: Error details if failed
            metadata: Additional context

        Returns:
            The created audit event
        """
        event = IntegrationAuditEvent(
            integration_id=integration_id,
            tenant_id=self.tenant_id,
            actor_id=actor_id,
            actor_type=actor_type,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            previous_state=previous_state,
            new_state=new_state,
            change_summary=change_summary,
            correlation_id=correlation_id,
            source_ip=source_ip,
            user_agent=user_agent,
            request_id=request_id,
            success=success,
            error_message=error_message,
            metadata_=metadata,
            occurred_at=datetime.now(timezone.utc),
        )

        self.db.add(event)
        await self.db.flush()

        logger.info(
            "audit_event_recorded",
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            success=success,
        )

        return event

    async def log_integration_created(
        self,
        integration_id: uuid.UUID,
        actor_id: Optional[uuid.UUID] = None,
        metadata: Optional[dict] = None,
    ) -> IntegrationAuditEvent:
        return await self.log_event(
            action="integration_created",
            resource_type="integration",
            resource_id=str(integration_id),
            integration_id=integration_id,
            actor_id=actor_id,
            change_summary="Integration created",
            success=True,
            metadata=metadata,
        )

    async def log_sync_completed(
        self,
        integration_id: uuid.UUID,
        sync_job_id: uuid.UUID,
        status: str,
        items_synced: int = 0,
        correlation_id: Optional[uuid.UUID] = None,
    ) -> IntegrationAuditEvent:
        return await self.log_event(
            action=f"sync_{status}",
            resource_type="sync_job",
            resource_id=str(sync_job_id),
            integration_id=integration_id,
            correlation_id=correlation_id,
            new_state={"status": status, "items_synced": items_synced},
            change_summary=f"Sync {status}: {items_synced} items",
            success=status == "completed",
        )

    async def log_credential_change(
        self,
        integration_id: uuid.UUID,
        credential_id: uuid.UUID,
        change_type: str,
        actor_id: Optional[uuid.UUID] = None,
    ) -> IntegrationAuditEvent:
        return await self.log_event(
            action=f"credential_{change_type}",
            resource_type="integration_credential",
            resource_id=str(credential_id),
            integration_id=integration_id,
            actor_id=actor_id,
            change_summary=f"Credential {change_type}",
            success=True,
        )

    async def log_webhook_event(
        self,
        integration_id: uuid.UUID,
        webhook_event_id: uuid.UUID,
        event_type: str,
        status: str,
    ) -> IntegrationAuditEvent:
        return await self.log_event(
            action=f"webhook_{status}",
            resource_type="webhook_event",
            resource_id=str(webhook_event_id),
            integration_id=integration_id,
            new_state={"event_type": event_type, "status": status},
            change_summary=f"Webhook event {event_type} -> {status}",
            success=status == "completed",
        )
