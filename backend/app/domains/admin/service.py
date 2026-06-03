"""Admin service — user management, roles, tenant settings, system health."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.admin.models import AdminUser, AdminRole, TenantSettings
from app.domains.admin.repository import AdminRepository
from app.domains.admin.schemas import (
    AdminUserCreate, AdminUserUpdate, AdminUserResponse,
    AdminRoleCreate, AdminRoleUpdate, AdminRoleResponse,
    TenantSettingsUpdate, TenantSettingsResponse,
    SystemHealthResponse, DashboardResponse, DashboardKpi,
)
from app.domains.admin.heartbeat_models import WorkerHeartbeat
from app.kernel.events.realtime import EventTypes, emit_event
from app.kernel.telemetry.metrics import metrics

logger = logging.getLogger(__name__)


async def _log_audit(
    session,
    tenant_id: str,
    actor_id: str,
    action: str,
    resource_type: str,
    resource_id: str,
    before: Optional[dict] = None,
    after: Optional[dict] = None,
) -> None:
    """Create an audit event entry."""
    from app.domains.playbook.models import GovernanceAuditEvent
    from sqlalchemy import select

    event = GovernanceAuditEvent(
        tenant_id=tenant_id,
        actor_id=actor_id,
        event_type=action,
        entity_type=resource_type,
        entity_id=resource_id,
        previous_state=before,
        new_state=after,
    )
    session.add(event)
    await session.flush()


@dataclass
class AdminService:
    """Enterprise administration service."""

    repo: AdminRepository
    tenant_id: str
    user_id: str
    session: Optional[AsyncSession] = None

    # ── Users ─────────────────────────────────────────────────────

    async def create_user(self, body: AdminUserCreate) -> AdminUserResponse:
        user_id = f"user-{self.tenant_id[:8]}-{body.email.split('@')[0]}"
        user = await self.repo.create_user(
            user_id=user_id, tenant_id=self.tenant_id,
            email=body.email, name=body.name,
            role=body.role, business_unit=body.business_unit,
            invited_by=self.user_id,
        )
        logger.info("User created: %s (%s) with role %s", user_id, body.email, body.role)
        if self.session:
            await _log_audit(self.session, self.tenant_id, self.user_id,
                             "USER_CREATED", "user", user_id,
                             after={"email": body.email, "role": body.role})
        return self._user_to_response(user)

    async def list_users(self) -> list[AdminUserResponse]:
        users = await self.repo.list_users(self.tenant_id)
        return [self._user_to_response(u) for u in users]

    async def get_user(self, user_id: str) -> Optional[AdminUserResponse]:
        user = await self.repo.get_user(user_id, self.tenant_id)
        return self._user_to_response(user) if user else None

    async def update_user(self, user_id: str, body: AdminUserUpdate) -> Optional[AdminUserResponse]:
        before = await self.repo.get_user(user_id, self.tenant_id)
        kwargs = {k: v for k, v in body.model_dump(exclude_none=True).items()}
        user = await self.repo.update_user(user_id, self.tenant_id, **kwargs)
        if self.session and user:
            await _log_audit(self.session, self.tenant_id, self.user_id,
                             "USER_UPDATED", "user", user_id,
                             before={"role": before.role if before else None},
                             after={"role": user.role})
        return self._user_to_response(user) if user else None

    async def delete_user(self, user_id: str) -> bool:
        if self.session:
            await _log_audit(self.session, self.tenant_id, self.user_id,
                             "USER_DELETED", "user", user_id)
        return await self.repo.delete_user(user_id, self.tenant_id)

    # ── Roles ─────────────────────────────────────────────────────

    async def create_role(self, body: AdminRoleCreate) -> AdminRoleResponse:
        role = await self.repo.create_role(
            role_id=body.role_id, name=body.name,
            description=body.description, permissions=body.permissions,
        )
        if self.session:
            await _log_audit(self.session, self.tenant_id, self.user_id,
                             "ROLE_CREATED", "role", body.role_id,
                             after={"name": body.name, "permissions": body.permissions})
        return self._role_to_response(role)

    async def list_roles(self) -> list[AdminRoleResponse]:
        roles = await self.repo.list_roles()
        return [self._role_to_response(r) for r in roles]

    async def update_role(self, role_id: str, body: AdminRoleUpdate) -> Optional[AdminRoleResponse]:
        before = await self.repo.get_role(role_id)
        kwargs = {k: v for k, v in body.model_dump(exclude_none=True).items()}
        role = await self.repo.update_role(role_id, **kwargs)
        if self.session and role:
            await _log_audit(self.session, self.tenant_id, self.user_id,
                             "ROLE_UPDATED", "role", role_id,
                             before={"permissions": before.permissions if before else None},
                             after={"permissions": role.permissions})
        return self._role_to_response(role) if role else None

    async def delete_role(self, role_id: str) -> bool:
        role = await self.repo.get_role(role_id)
        if role and role.is_system:
            raise ValueError(f"Cannot delete system role: {role_id}")
        if self.session:
            await _log_audit(self.session, self.tenant_id, self.user_id,
                             "ROLE_DELETED", "role", role_id)
        return await self.repo.delete_role(role_id)

    # ── Tenant Settings ───────────────────────────────────────────

    async def get_settings(self) -> TenantSettingsResponse:
        settings = await self.repo.get_settings(self.tenant_id)
        if settings:
            return self._settings_to_response(settings)
        return TenantSettingsResponse(
            brand_name="ContractRiskEdge",
            risk_threshold_critical=70,
            risk_threshold_high=50,
        )

    async def update_settings(self, body: TenantSettingsUpdate) -> TenantSettingsResponse:
        kwargs = {k: v for k, v in body.model_dump(exclude_none=True).items()}
        settings = await self.repo.upsert_settings(self.tenant_id, **kwargs)
        return self._settings_to_response(settings)

    # ── Dashboard ───────────────────────────────────────────────

    async def get_dashboard(self) -> DashboardResponse:
        """Aggregate admin dashboard KPIs and counts."""
        from sqlalchemy import text

        total_users = 0
        active_users_30d = 0
        total_uploads = 0
        total_reviews = 0
        audit_events_24h = 0

        try:
            result = await self.repo.session.execute(
                text("SELECT COUNT(*)::int FROM admin_users WHERE tenant_id = :tid"),
                {"tid": self.tenant_id},
            )
            total_users = result.scalar() or 0
        except Exception:
            pass

        try:
            result = await self.repo.session.execute(
                text("SELECT COUNT(*)::int FROM admin_users WHERE tenant_id = :tid AND last_login_at >= NOW() - INTERVAL '30 days'"),
                {"tid": self.tenant_id},
            )
            active_users_30d = result.scalar() or 0
        except Exception:
            pass

        try:
            result = await self.repo.session.execute(
                text("SELECT COUNT(*)::int FROM upload_sessions WHERE tenant_id = :tid"),
                {"tid": self.tenant_id},
            )
            total_uploads = result.scalar() or 0
        except Exception:
            pass

        try:
            result = await self.repo.session.execute(
                text("SELECT COUNT(*)::int FROM contract_reviews WHERE tenant_id = :tid"),
                {"tid": self.tenant_id},
            )
            total_reviews = result.scalar() or 0
        except Exception:
            pass

        try:
            result = await self.repo.session.execute(
                text("SELECT COUNT(*)::int FROM governance_audit_events WHERE tenant_id = :tid AND created_at >= NOW() - INTERVAL '24 hours'"),
                {"tid": self.tenant_id},
            )
            audit_events_24h = result.scalar() or 0
        except Exception:
            pass

        kpis = [
            DashboardKpi(label="Total Users", value=total_users, change=0.0, trend="neutral"),
            DashboardKpi(label="Active Users (30d)", value=active_users_30d, change=0.0, trend="neutral"),
            DashboardKpi(label="Total Uploads", value=total_uploads, change=0.0, trend="neutral"),
            DashboardKpi(label="Total Reviews", value=total_reviews, change=0.0, trend="neutral"),
            DashboardKpi(label="Audit Events (24h)", value=audit_events_24h, change=0.0, trend="neutral"),
        ]

        return DashboardResponse(
            kpis=kpis,
            total_users=total_users,
            active_users_30d=active_users_30d,
            total_tenants=1,
            total_uploads=total_uploads,
            total_reviews=total_reviews,
            audit_events_24h=audit_events_24h,
            system_health="healthy",
        )

    # ── System Health ─────────────────────────────────────────────

    async def get_system_health(self) -> SystemHealthResponse:
        """Gather comprehensive system health from all infrastructure."""
        from app.kernel.events.realtime import event_manager
        from app.config import settings as app_settings
        from sqlalchemy import text

        health = SystemHealthResponse()

        # Database
        try:
            result = await self.repo.session.execute(text("SELECT COUNT(*)::int FROM upload_sessions"))
            health.storage["total_documents"] = result.scalar() or 0
            health.database["connected"] = True
        except Exception:
            health.database["connected"] = False
            health.status = "degraded"

        # Chunks count
        try:
            result = await self.repo.session.execute(text("SELECT COUNT(*)::int FROM chunks"))
            health.storage["total_chunks"] = result.scalar() or 0
        except Exception:
            pass

        # Redis / Celery
        try:
            import redis.asyncio as aioredis
            r = aioredis.from_url(app_settings.redis_url, decode_responses=True)
            await r.ping()
            health.redis["connected"] = True
            info = await r.info("memory")
            health.redis["memory_used_mb"] = round(info.get("used_memory", 0) / 1024 / 1024, 1)

            # Queue depths from Celery broker
            broker = aioredis.from_url(app_settings.celery_broker_url, decode_responses=True)
            for qname in ["ingestion", "ai", "notifications", "default"]:
                try:
                    depth = await broker.llen(qname)
                    health.celery["queue_sizes"][qname] = depth or 0
                except Exception:
                    health.celery["queue_sizes"][qname] = 0
            await broker.close()
            await r.close()
        except Exception:
            health.redis["connected"] = False
            health.status = "degraded"

        # WebSocket
        ws_stats = await event_manager.health_check()
        health.websocket["active_connections"] = ws_stats.get("active_connections", 0)
        health.websocket["messages_sent"] = ws_stats.get("messages_sent", 0)

        # AI metrics (24h)
        try:
            result = await self.repo.session.execute(text("""
                SELECT COUNT(*)::int AS failures,
                       COALESCE(SUM(total_tokens), 0)::int AS tokens,
                       COALESCE(SUM(cost_usd), 0)::float AS cost,
                       COALESCE(AVG(latency_ms), 0)::float AS avg_latency
                FROM ai_execution_runs
                WHERE tenant_id = :tid AND created_at > NOW() - INTERVAL '24 hours'
            """), {"tid": self.tenant_id})
            row = result.fetchone()
            if row:
                health.ai["failures_24h"] = row.failures or 0
                health.ai["tokens_24h"] = row.tokens or 0
                health.ai["cost_24h"] = round(row.cost or 0, 4)
                health.ai["avg_latency_ms"] = round(row.avg_latency or 0, 1)
        except Exception:
            pass

        health.ai["model"] = app_settings.default_embedding_model

        return health

    # ── Response Builders ─────────────────────────────────────────

    @staticmethod
    def _user_to_response(user: AdminUser) -> AdminUserResponse:
        return AdminUserResponse(
            user_id=user.user_id, email=user.email, name=user.name,
            role=user.role, business_unit=user.business_unit,
            is_active=user.is_active, is_invited=user.is_invited,
            last_login_at=user.last_login_at,
            created_at=user.created_at, updated_at=user.updated_at,
        )

    @staticmethod
    def _role_to_response(role: AdminRole) -> AdminRoleResponse:
        return AdminRoleResponse(
            role_id=role.role_id, name=role.name,
            description=role.description, permissions=role.permissions,
            is_system=role.is_system, created_at=role.created_at,
        )

    @staticmethod
    def _settings_to_response(settings: TenantSettings) -> TenantSettingsResponse:
        return TenantSettingsResponse(
            brand_name=settings.brand_name,
            brand_logo_url=settings.brand_logo_url,
            brand_primary_color=settings.brand_primary_color or "#1B3A6B",
            brand_accent_color=settings.brand_accent_color or "#C9A84C",
            ai_model=settings.ai_model or "gpt-4o",
            ai_temperature=settings.ai_temperature or 10,
            ai_max_tokens=settings.ai_max_tokens or 4096,
            ai_embedding_model=settings.ai_embedding_model or "text-embedding-3-small",
            ai_token_budget_daily=settings.ai_token_budget_daily or 1000000,
            ai_token_budget_monthly=settings.ai_token_budget_monthly or 30000000,
            risk_threshold_critical=settings.risk_threshold_critical or 70,
            risk_threshold_high=settings.risk_threshold_high or 50,
            risk_threshold_medium=settings.risk_threshold_medium or 30,
            sla_critical_hours=settings.sla_critical_hours or 24,
            sla_high_hours=settings.sla_high_hours or 48,
            sla_medium_hours=settings.sla_medium_hours or 72,
            sla_low_hours=settings.sla_low_hours or 168,
            default_notification_channel=settings.default_notification_channel or "in_app",
            email_redirect_enabled=bool(getattr(settings, "email_redirect_enabled", False)),
            email_redirect_to=getattr(settings, "email_redirect_to", None),
            features_enabled=settings.features_enabled or {},
            created_at=settings.created_at,
            updated_at=settings.updated_at,
        )

    # ── Worker Heartbeat ──────────────────────────────────────────

    async def record_heartbeat(
        self,
        worker_id: str,
        queue: str,
        status: str = "active",
        tasks_completed: int = 0,
        tasks_failed: int = 0,
    ) -> dict:
        """Record or update a worker heartbeat.

        Upserts the worker heartbeat row. Also updates Prometheus
        active_workers gauge and worker_heartbeats_total counter.
        """
        from datetime import datetime, timezone
        from sqlalchemy import select

        result = await self.repo.session.execute(
            select(WorkerHeartbeat).where(WorkerHeartbeat.worker_id == worker_id)
        )
        heartbeat = result.scalar_one_or_none()

        now = datetime.now(timezone.utc)
        if heartbeat:
            heartbeat.last_heartbeat_at = now
            heartbeat.status = status
            heartbeat.tasks_completed = tasks_completed
            heartbeat.tasks_failed = tasks_failed
            heartbeat.queue = queue
        else:
            heartbeat = WorkerHeartbeat(
                worker_id=worker_id,
                queue=queue,
                status=status,
                tasks_completed=tasks_completed,
                tasks_failed=tasks_failed,
                last_heartbeat_at=now,
                started_at=now,
            )
            self.repo.session.add(heartbeat)

        await self.repo.session.flush()

        # Prometheus metrics
        metrics.worker_heartbeats_total.labels(
            worker_id=worker_id, queue=queue,
        ).inc()
        metrics.active_workers.labels(queue=queue).set(
            await self._count_active_workers(queue)
        )

        return {
            "worker_id": worker_id,
            "queue": queue,
            "status": status,
            "last_heartbeat_at": now.isoformat(),
        }

    async def _count_active_workers(self, queue: Optional[str] = None) -> int:
        """Count active workers (heartbeat within last 5 minutes)."""
        from sqlalchemy import select, func, text

        query = select(func.count()).select_from(WorkerHeartbeat).where(
            WorkerHeartbeat.last_heartbeat_at
            > func.now() - text("INTERVAL '5 minutes'")
        )
        if queue:
            query = query.where(WorkerHeartbeat.queue == queue)
        result = await self.repo.session.execute(query)
        return result.scalar() or 0
