"""SCIM and identity provisioning scaffolding for enterprise onboarding."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

from app.kernel.security.roles import Roles


@dataclass
class SCIMGroup:
    """Represents a SCIM group with optional membership details."""
    id: str
    display_name: str
    members: list[str] = field(default_factory=list)


@dataclass
class SCIMUser:
    """Represents a SCIM user record from an external identity provider."""
    id: str
    user_name: str
    email: str
    external_id: Optional[str] = None
    active: bool = True
    groups: list[SCIMGroup] = field(default_factory=list)


class SCIMClient(ABC):
    """Abstract SCIM client interface for identity provider integration."""

    @abstractmethod
    async def get_user(self, external_id: str) -> Optional[SCIMUser]:
        ...

    @abstractmethod
    async def list_users(self) -> list[SCIMUser]:
        ...

    @abstractmethod
    async def create_user(self, user: SCIMUser) -> SCIMUser:
        ...

    @abstractmethod
    async def update_user(self, user: SCIMUser) -> SCIMUser:
        ...

    @abstractmethod
    async def deactivate_user(self, external_id: str) -> None:
        ...

    @abstractmethod
    async def list_groups(self) -> list[SCIMGroup]:
        ...


class RoleMapper:
    """Maps SCIM groups to application roles."""

    GROUP_TO_ROLE: dict[str, str] = {
        "tenant_admins": Roles.ADMIN,
        "auditors": Roles.AUDITOR,
        "legal_reviewers": Roles.LEGAL_REVIEWER,
        "reviewers": Roles.REVIEWER,
        "procurement": Roles.PROCUREMENT,
        "security": Roles.SECURITY,
        "developers": Roles.DEVELOPER,
        "viewers": Roles.READ_ONLY,
    }

    ROLE_PRIORITY: list[str] = [
        Roles.ADMIN,
        Roles.AUDITOR,
        Roles.SECURITY,
        Roles.LEGAL_REVIEWER,
        Roles.PROCUREMENT,
        Roles.DEVELOPER,
        Roles.REVIEWER,
        Roles.READ_ONLY,
    ]

    @classmethod
    def resolve_role(cls, groups: Iterable[SCIMGroup]) -> str:
        """Resolve the strongest application role for a user based on SCIM groups."""
        roles: set[str] = set()
        for group in groups:
            normalized = group.display_name.lower().replace(" ", "_")
            role = cls.GROUP_TO_ROLE.get(normalized)
            if role:
                roles.add(role)

        if not roles:
            return Roles.READ_ONLY

        for priority_role in cls.ROLE_PRIORITY:
            if priority_role in roles:
                return priority_role

        return Roles.READ_ONLY


class UserProvisioningService:
    """Provision SCIM users into the local enterprise identity footprint."""

    def __init__(self, scim_client: SCIMClient):
        self.scim_client = scim_client

    async def sync_user(self, external_id: str) -> Optional[SCIMUser]:
        """Synchronize a SCIM user record into local role and group mappings."""
        user = await self.scim_client.get_user(external_id)
        if not user:
            return None

        resolved_role = RoleMapper.resolve_role(user.groups)
        user.external_id = external_id
        user.active = user.active
        user.groups = user.groups
        # Future integration point: persist tenant user record and assign permissions.
        return user

    async def list_all_users(self) -> list[SCIMUser]:
        return await self.scim_client.list_users()

    async def provision_group_membership(self, external_id: str, group_id: str) -> None:
        raise NotImplementedError("SCIM group membership provisioning is not implemented in this scaffold.")
