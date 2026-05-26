"""Admin repository — users, roles, tenant settings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select, update, delete, func

from app.kernel.repository.base import BaseRepository
from app.domains.admin.models import AdminUser, AdminRole, TenantSettings


@dataclass
class AdminRepository(BaseRepository):

    # ── Users ─────────────────────────────────────────────────────

    async def create_user(self, user_id: str, tenant_id: str, email: str,
                           name: Optional[str], role: str, business_unit: Optional[str],
                           invited_by: Optional[str] = None) -> AdminUser:
        user = AdminUser(
            user_id=user_id, tenant_id=tenant_id, email=email,
            name=name, role=role, business_unit=business_unit,
            is_invited=True, invited_by=invited_by,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def get_user(self, user_id: str, tenant_id: str) -> Optional[AdminUser]:
        stmt = select(AdminUser).where(
            AdminUser.user_id == user_id, AdminUser.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_users(self, tenant_id: str) -> list[AdminUser]:
        stmt = (
            select(AdminUser)
            .where(AdminUser.tenant_id == tenant_id)
            .order_by(AdminUser.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_user(self, user_id: str, tenant_id: str, **kwargs) -> Optional[AdminUser]:
        stmt = (
            update(AdminUser)
            .where(AdminUser.user_id == user_id, AdminUser.tenant_id == tenant_id)
            .values(**kwargs, updated_at=func.now())
        )
        await self.session.execute(stmt)
        return await self.get_user(user_id, tenant_id)

    async def delete_user(self, user_id: str, tenant_id: str) -> bool:
        stmt = delete(AdminUser).where(
            AdminUser.user_id == user_id, AdminUser.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    # ── Roles ─────────────────────────────────────────────────────

    async def create_role(self, role_id: str, name: str,
                           description: Optional[str], permissions: list[str]) -> AdminRole:
        role = AdminRole(role_id=role_id, name=name, description=description, permissions=permissions)
        self.session.add(role)
        await self.session.flush()
        return role

    async def get_role(self, role_id: str) -> Optional[AdminRole]:
        stmt = select(AdminRole).where(AdminRole.role_id == role_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_roles(self) -> list[AdminRole]:
        stmt = select(AdminRole).order_by(AdminRole.role_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_role(self, role_id: str, **kwargs) -> Optional[AdminRole]:
        stmt = (
            update(AdminRole)
            .where(AdminRole.role_id == role_id)
            .values(**kwargs)
        )
        await self.session.execute(stmt)
        return await self.get_role(role_id)

    async def delete_role(self, role_id: str) -> bool:
        stmt = delete(AdminRole).where(AdminRole.role_id == role_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    # ── Tenant Settings ───────────────────────────────────────────

    async def get_settings(self, tenant_id: str) -> Optional[TenantSettings]:
        stmt = select(TenantSettings).where(TenantSettings.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_settings(self, tenant_id: str, **kwargs) -> TenantSettings:
        existing = await self.get_settings(tenant_id)
        if existing:
            stmt = (
                update(TenantSettings)
                .where(TenantSettings.tenant_id == tenant_id)
                .values(**kwargs, updated_at=func.now())
            )
            await self.session.execute(stmt)
        else:
            settings = TenantSettings(tenant_id=tenant_id, **kwargs)
            self.session.add(settings)
            await self.session.flush()
        return await self.get_settings(tenant_id)
