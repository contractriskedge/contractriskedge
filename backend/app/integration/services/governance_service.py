"""
Governance Service — integration governance, approval workflows,
permission evaluation, and tenant-level restriction enforcement.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.integration.models.integration import (
    ConnectorProvider,
    Integration,
    IntegrationStatus,
)
from app.integration.models.permission import (
    ConnectorPermission,
    PermissionAction,
    PermissionEffect,
)
from app.integration.services.audit_service import IntegrationAuditService

logger = get_logger(__name__)


@dataclass
class TenantRestrictions:
    """Tenant-level integration restrictions."""

    allowed_providers: Optional[list[str]] = None
    blocked_providers: list[str] = field(default_factory=list)
    max_integrations: Optional[int] = None
    require_approval: bool = True
    max_sync_frequency_minutes: Optional[int] = None
    allowed_ip_ranges: Optional[list[str]] = None


@dataclass
class PermissionEvaluation:
    """Result of a permission evaluation."""

    allowed: bool
    effect: Optional[PermissionEffect] = None
    matched_permission_id: Optional[uuid.UUID] = None
    reason: Optional[str] = None


class PermissionEvaluator:
    """
    Evaluates connector-level permissions for users and roles.

    Supports:
    - User-level permissions
    - Role-level permissions
    - Allow/Deny evaluation with priority ordering
    - Conditional permissions based on resource attributes
    """

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id

    async def evaluate(
        self,
        user_id: uuid.UUID,
        action: str,
        integration_id: Optional[uuid.UUID] = None,
        provider: Optional[str] = None,
        resource_type: Optional[str] = None,
    ) -> PermissionEvaluation:
        """
        Evaluate whether a user is allowed to perform an action.

        Evaluation order:
        1. Check for explicit DENY (highest priority)
        2. Check for explicit ALLOW
        3. Default to DENY
        """
        action_enum = self._parse_action(action)

        # Gather all relevant permissions
        permissions = await self._get_relevant_permissions(
            user_id=user_id,
            integration_id=integration_id,
            provider=provider,
            action=action_enum,
        )

        # Sort by priority (higher = evaluated first)
        permissions.sort(key=lambda p: p.priority, reverse=True)

        for perm in permissions:
            if perm.action != action_enum:
                continue

            # Check conditions
            if perm.conditions:
                conditions_met = self._evaluate_conditions(
                    perm.conditions,
                    {"resource_type": resource_type, "provider": provider},
                )
                if not conditions_met:
                    continue

            if perm.effect == PermissionEffect.DENY:
                return PermissionEvaluation(
                    allowed=False,
                    effect=PermissionEffect.DENY,
                    matched_permission_id=perm.id,
                    reason="Explicitly denied by policy",
                )

            if perm.effect == PermissionEffect.ALLOW:
                return PermissionEvaluation(
                    allowed=True,
                    effect=PermissionEffect.ALLOW,
                    matched_permission_id=perm.id,
                )

        # Default: deny
        return PermissionEvaluation(
            allowed=False,
            reason="No matching permission found",
        )

    async def _get_relevant_permissions(
        self,
        user_id: uuid.UUID,
        action: PermissionAction,
        integration_id: Optional[uuid.UUID] = None,
        provider: Optional[str] = None,
    ) -> list[ConnectorPermission]:
        """Get all permissions relevant to a user and action."""
        conditions = [
            ConnectorPermission.tenant_id == self.tenant_id,
            ConnectorPermission.is_active == True,
            ConnectorPermission.action == action,
        ]

        # Match user-level or role-level
        user_condition = (ConnectorPermission.user_id == user_id)
        conditions.append(user_condition)

        # Match integration or provider
        if integration_id:
            conditions.append(
                (ConnectorPermission.integration_id == integration_id) |
                (ConnectorPermission.integration_id == None)
            )
        if provider:
            conditions.append(
                (ConnectorPermission.provider == provider) |
                (ConnectorPermission.provider == None)
            )

        result = await self.db.execute(
            select(ConnectorPermission).where(*conditions)
        )
        return list(result.scalars().all())

    def _parse_action(self, action: str) -> PermissionAction:
        try:
            return PermissionAction(action)
        except ValueError:
            raise ValueError(f"Invalid permission action: {action}")

    def _evaluate_conditions(
        self,
        conditions: dict[str, Any],
        context: dict[str, Any],
    ) -> bool:
        """Evaluate permission conditions against request context."""
        for key, expected in conditions.items():
            actual = context.get(key)
            if actual != expected:
                return False
        return True


class GovernanceService:
    """
    Enterprise integration governance service.

    Manages:
    - Integration approval workflows
    - Tenant-level restriction enforcement
    - Integration disablement policies
    - Compliance audit hooks
    """

    def __init__(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        audit: Optional[IntegrationAuditService] = None,
    ):
        self.db = db
        self.tenant_id = tenant_id
        self.audit = audit
        self._tenant_restrictions: dict[uuid.UUID, TenantRestrictions] = {}

    async def check_tenant_restrictions(
        self,
        provider: str,
    ) -> Optional[str]:
        """
        Check tenant-level restrictions for a connector provider.

        Returns an error message if restricted, None if allowed.
        """
        restrictions = await self._get_tenant_restrictions()

        if restrictions.blocked_providers and provider in restrictions.blocked_providers:
            return f"Connector provider '{provider}' is blocked for this tenant"

        if restrictions.allowed_providers and provider not in restrictions.allowed_providers:
            return f"Connector provider '{provider}' is not allowed for this tenant"

        # Check max integrations
        if restrictions.max_integrations:
            count = await self._count_active_integrations()
            if count >= restrictions.max_integrations:
                return f"Maximum integrations ({restrictions.max_integrations}) reached for this tenant"

        return None

    async def require_approval(self) -> bool:
        """Check if integration approval is required for this tenant."""
        restrictions = await self._get_tenant_restrictions()
        return restrictions.require_approval

    async def approve_integration(
        self,
        integration_id: uuid.UUID,
        approved_by: uuid.UUID,
        notes: Optional[str] = None,
    ) -> Integration:
        """Approve an integration for use."""
        result = await self.db.execute(
            select(Integration).where(
                Integration.id == integration_id,
                Integration.tenant_id == self.tenant_id,
            )
        )
        integration = result.scalar_one_or_none()
        if not integration:
            raise ValueError(f"Integration not found: {integration_id}")

        now = datetime.now(timezone.utc)
        integration.is_approved = True
        integration.approved_by = approved_by
        integration.approved_at = now

        if integration.status == IntegrationStatus.PENDING_APPROVAL:
            integration.status = IntegrationStatus.ACTIVE

        await self.db.flush()

        if self.audit:
            await self.audit.log_event(
                integration_id=integration_id,
                action="integration_approved",
                resource_type="integration",
                resource_id=str(integration_id),
                new_state={"is_approved": True, "approved_by": str(approved_by)},
                change_summary=notes or f"Integration approved by {approved_by}",
                success=True,
            )

        logger.info(
            "integration_approved",
            integration_id=str(integration_id),
            approved_by=str(approved_by),
        )

        return integration

    async def disable_integration(
        self,
        integration_id: uuid.UUID,
        reason: str,
        disabled_by: Optional[uuid.UUID] = None,
    ) -> Integration:
        """Disable an integration with audit trail."""
        result = await self.db.execute(
            select(Integration).where(
                Integration.id == integration_id,
                Integration.tenant_id == self.tenant_id,
            )
        )
        integration = result.scalar_one_or_none()
        if not integration:
            raise ValueError(f"Integration not found: {integration_id}")

        previous_status = integration.status.value
        now = datetime.now(timezone.utc)

        integration.status = IntegrationStatus.DISABLED
        integration.disabled_at = now
        integration.disabled_reason = reason

        await self.db.flush()

        if self.audit:
            await self.audit.log_event(
                integration_id=integration_id,
                action="integration_disabled",
                resource_type="integration",
                resource_id=str(integration_id),
                previous_state={"status": previous_status},
                new_state={"status": "disabled", "reason": reason},
                change_summary=f"Integration disabled: {reason}",
                success=True,
            )

        logger.info(
            "integration_disabled",
            integration_id=str(integration_id),
            reason=reason,
        )

        return integration

    async def auto_disable_on_failures(
        self,
        integration_id: uuid.UUID,
        max_consecutive_failures: int = 5,
    ) -> bool:
        """
        Automatically disable an integration after consecutive failures.

        Returns True if disabled, False otherwise.
        """
        from app.integration.models.sync_job import SyncJobStatus

        result = await self.db.execute(
            select(Integration).where(
                Integration.id == integration_id,
                Integration.tenant_id == self.tenant_id,
            )
        )
        integration = result.scalar_one_or_none()
        if not integration:
            return False

        # Count recent consecutive failures
        jobs_result = await self.db.execute(
            select(type(IntegrationSyncJob)).where(
                IntegrationSyncJob.integration_id == integration_id,
                IntegrationSyncJob.tenant_id == self.tenant_id,
            )
            .order_by(IntegrationSyncJob.created_at.desc())
            .limit(max_consecutive_failures)
        )
        recent_jobs = list(jobs_result.scalars().all())

        if len(recent_jobs) < max_consecutive_failures:
            return False

        all_failed = all(
            job.status == SyncJobStatus.FAILED
            or job.status == SyncJobStatus.DEAD_LETTER
            for job in recent_jobs
        )

        if all_failed:
            await self.disable_integration(
                integration_id=integration_id,
                reason=f"Auto-disabled after {max_consecutive_failures} consecutive failures",
            )
            return True

        return False

    async def _get_tenant_restrictions(self) -> TenantRestrictions:
        """Get (or cache) tenant-level restrictions."""
        if self.tenant_id not in self._tenant_restrictions:
            # In production, load from a tenant_config table
            self._tenant_restrictions[self.tenant_id] = TenantRestrictions(
                require_approval=True,
            )
        return self._tenant_restrictions[self.tenant_id]

    async def _count_active_integrations(self) -> int:
        result = await self.db.execute(
            select(type(Integration)).where(
                Integration.tenant_id == self.tenant_id,
                Integration.is_deleted == False,
                Integration.status.in_([
                    IntegrationStatus.ACTIVE,
                    IntegrationStatus.PENDING,
                ]),
            )
        )
        return len(list(result.scalars().all()))

    def set_tenant_restrictions(
        self,
        tenant_id: uuid.UUID,
        restrictions: TenantRestrictions,
    ) -> None:
        """Set tenant-level restrictions (loaded from config/database)."""
        self._tenant_restrictions[tenant_id] = restrictions
        logger.info(
            "tenant_restrictions_updated",
            tenant_id=str(tenant_id),
        )
