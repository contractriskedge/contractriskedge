"""System audit recorder — persists auth, security, and API error events."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Optional

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

SYSTEM_ENTITY_ID = "00000000-0000-4000-8000-000000000099"


class AuditRecorder:
    """Write append-only rows to governance_audit_events for platform events."""

    def __init__(self, session: AsyncSession, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id

    async def record(
        self,
        *,
        event_type: str,
        actor_id: str,
        description: str,
        status: str = "success",
        severity: str = "info",
        entity_type: str = "system",
        entity_id: str = SYSTEM_ENTITY_ID,
        actor_role: Optional[str] = None,
        correlation_id: Optional[str] = None,
        request_id: Optional[str] = None,
        source: str = "platform",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        error_message: Optional[str] = None,
        before_state: Optional[dict[str, Any]] = None,
        after_state: Optional[dict[str, Any]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        meta = {
            "status": status,
            "severity": severity,
            **(metadata or {}),
        }
        if ip_address:
            meta["ip_address"] = ip_address
        if user_agent:
            meta["user_agent"] = user_agent
        if error_message:
            meta["error_message"] = error_message

        try:
            await self.session.execute(
                sa_text("""
                    INSERT INTO governance_audit_events (
                        event_id, tenant_id, event_type, entity_type, entity_id,
                        actor_id, actor_role, previous_state, new_state,
                        change_summary, correlation_id, request_id, source, metadata, created_at
                    ) VALUES (
                        :event_id, :tenant_id, :event_type, :entity_type, :entity_id,
                        :actor_id, :actor_role, :previous_state, :new_state,
                        :change_summary, :correlation_id, :request_id, :source, :metadata, NOW()
                    )
                """),
                {
                    "event_id": uuid.uuid4(),
                    "tenant_id": uuid.UUID(str(self.tenant_id)),
                    "event_type": event_type,
                    "entity_type": entity_type,
                    "entity_id": uuid.UUID(str(entity_id)),
                    "actor_id": actor_id or "system",
                    "actor_role": actor_role,
                    "previous_state": json.dumps(before_state) if before_state else None,
                    "new_state": json.dumps(after_state) if after_state else None,
                    "change_summary": description,
                    "correlation_id": correlation_id,
                    "request_id": request_id,
                    "source": source,
                    "metadata": json.dumps(meta),
                },
            )
            await self.session.flush()
        except Exception as exc:
            logger.error("Failed to record platform audit event %s: %s", event_type, exc, exc_info=True)
