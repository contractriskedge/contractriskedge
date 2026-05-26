"""Role definitions and role-to-permission mapping for RBAC.

Defines 6 roles with granular permission sets and clause-level
access control model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set


class Role(str, Enum):
    """The 6 RBAC roles in the platform."""

    SUPER_ADMIN = "super_admin"       # System-wide access
    ORG_ADMIN = "org_admin"           # Tenant-wide configuration
    LEGAL_REVIEWER = "legal_reviewer"  # View + annotate + accept/reject redlines
    PROCUREMENT_ANALYST = "procurement_analyst"  # View contracts + comparison + export
    CFO_VIEWER = "cfo_viewer"         # Read-only dashboard + reports
    EXTERNAL_COUNSEL = "external_counsel"  # Read-only specific contracts via share link

    def __str__(self) -> str:
        return self.value


# ── Permission Constants ─────────────────────────────────────────────────────

# Contract permissions
READ_CONTRACTS = "read:contracts"
WRITE_CONTRACTS = "write:contracts"
DELETE_CONTRACTS = "delete:contracts"
ANNOTATE_CONTRACTS = "annotate:contracts"

# Redline permissions
READ_REDLINES = "read:redlines"
WRITE_REDLINES = "write:redlines"
ACCEPT_REDLINES = "accept:redlines"

# Benchmark permissions
READ_BENCHMARKS = "read:benchmarks"
WRITE_PLAYBOOKS = "write:playbooks"

# Audit permissions
READ_AUDIT = "read:audit"
EXPORT_AUDIT = "export:audit"

# Admin permissions
MANAGE_USERS = "manage:users"
MANAGE_BILLING = "manage:billing"
MANAGE_INTEGRATIONS = "manage:integrations"
ADMIN_TENANT = "admin:tenant"
ADMIN_SYSTEM = "admin:system"
EXPORT_DATA = "export:data"

# Clause-level permissions
READ_ALL_CLAUSES = "read:all_clauses"
READ_DEPARTMENT_CLAUSES = "read:department_clauses"
READ_ASSIGNED_CLAUSES = "read:assigned_clauses"


# ── Role → Permission Mapping ───────────────────────────────────────────────

ROLE_PERMISSIONS: Dict[Role, List[str]] = {
    Role.SUPER_ADMIN: [
        READ_CONTRACTS, WRITE_CONTRACTS, DELETE_CONTRACTS, ANNOTATE_CONTRACTS,
        READ_REDLINES, WRITE_REDLINES, ACCEPT_REDLINES,
        READ_BENCHMARKS, WRITE_PLAYBOOKS,
        READ_AUDIT, EXPORT_AUDIT,
        MANAGE_USERS, MANAGE_BILLING, MANAGE_INTEGRATIONS,
        ADMIN_TENANT, ADMIN_SYSTEM, EXPORT_DATA,
        READ_ALL_CLAUSES,
    ],
    Role.ORG_ADMIN: [
        READ_CONTRACTS, WRITE_CONTRACTS, DELETE_CONTRACTS, ANNOTATE_CONTRACTS,
        READ_REDLINES, WRITE_REDLINES, ACCEPT_REDLINES,
        READ_BENCHMARKS, WRITE_PLAYBOOKS,
        READ_AUDIT, EXPORT_AUDIT,
        MANAGE_USERS, MANAGE_BILLING, MANAGE_INTEGRATIONS,
        ADMIN_TENANT, EXPORT_DATA,
        READ_ALL_CLAUSES,
    ],
    Role.LEGAL_REVIEWER: [
        READ_CONTRACTS, ANNOTATE_CONTRACTS,
        READ_REDLINES, WRITE_REDLINES, ACCEPT_REDLINES,
        READ_BENCHMARKS,
        READ_AUDIT,
        READ_DEPARTMENT_CLAUSES,
    ],
    Role.PROCUREMENT_ANALYST: [
        READ_CONTRACTS,
        READ_REDLINES,
        READ_BENCHMARKS,
        EXPORT_DATA,
        READ_DEPARTMENT_CLAUSES,
    ],
    Role.CFO_VIEWER: [
        READ_CONTRACTS,
        READ_BENCHMARKS,
        READ_AUDIT,
        EXPORT_DATA,
        READ_DEPARTMENT_CLAUSES,
    ],
    Role.EXTERNAL_COUNSEL: [
        READ_CONTRACTS,
        READ_REDLINES,
        READ_ASSIGNED_CLAUSES,
    ],
}


def get_permissions_for_role(role: Role) -> List[str]:
    """Get the list of permissions for a given role.

    Args:
        role: The role to look up.

    Returns:
        List of permission strings.
    """
    return ROLE_PERMISSIONS.get(role, [])


def get_role_from_permissions(permissions: List[str]) -> Optional[Role]:
    """Reverse-lookup the role from a set of permissions.

    Args:
        permissions: List of permission strings.

    Returns:
        The matching Role or None.
    """
    perm_set = set(permissions)
    for role, role_perms in ROLE_PERMISSIONS.items():
        if set(role_perms) == perm_set:
            return role
    return None


@dataclass
class ClauseACL:
    """Clause-level access control entry.

    Defines which users can access which clauses within a contract.
    """

    contract_id: str
    clause_id: str
    user_id: str
    permission_level: str  # "read", "annotate", "admin"
    granted_by: str
    granted_at: str = ""


@dataclass
class DepartmentGroup:
    """A department group for data isolation."""

    group_id: str
    name: str
    tenant_id: str
    member_ids: List[str] = field(default_factory=list)
    created_at: str = ""
