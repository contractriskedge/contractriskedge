"""Role definitions and permission matrix for RBAC.

Provides:
  - Canonical role definitions with permission mappings
  - Policy-based authorization: can(user, action, resource)
  - Server-side permission resolution from role + tenant context

Usage:
    from app.kernel.security.roles import Roles, can, resolve_permissions

    # Check if user can perform an action
    if can(user, "review:approve", review):
        ...

    # Resolve permissions from role (server-side, not JWT-dependent)
    user.permissions = resolve_permissions(user.role)
"""

from __future__ import annotations

from typing import Optional

from app.kernel.security.auth import UserContext


class Roles:
    """Canonical role definitions with their permission sets."""

    # ── Role Constants ──
    ADMIN = "tenant_admin"
    LEGAL_REVIEWER = "legal_reviewer"
    REVIEWER = "reviewer"
    PROCUREMENT = "procurement"
    SECURITY = "security"
    READ_ONLY = "viewer"
    AUDITOR = "auditor"

    # ── Permission Sets ──
    _PERMISSIONS: dict[str, set[str]] = {
        ADMIN: {
            "contracts:read", "contracts:write", "contracts:delete", "contracts:approve",
            "ai:analyze", "ai:view", "ai:manage",
            "workflows:read", "workflows:write", "workflows:approve", "workflows:escalate",
            "vendors:read", "vendors:write",
            "audit:read", "audit:export",
            "users:read", "users:write", "users:delete",
            "admin:tenant",
            "reviews:export",
            "notifications:manage",
        },
        LEGAL_REVIEWER: {
            "contracts:read", "contracts:approve",
            "ai:view",
            "workflows:read", "workflows:write", "workflows:approve", "workflows:escalate",
            "audit:read",
            "reviews:export",
        },
        REVIEWER: {
            "contracts:read",
            "ai:view",
            "workflows:read", "workflows:write",
            "reviews:export",
        },
        PROCUREMENT: {
            "contracts:read",
            "ai:view",
            "workflows:read", "workflows:write", "workflows:escalate",
            "vendors:read",
            "reviews:export",
        },
        SECURITY: {
            "contracts:read",
            "ai:view",
            "workflows:read", "workflows:write", "workflows:approve", "workflows:escalate",
            "audit:read",
            "reviews:export",
        },
        READ_ONLY: {
            "contracts:read",
            "ai:view",
            "workflows:read",
            "audit:read",
        },
        AUDITOR: {
            "contracts:read",
            "audit:read", "audit:export",
            "reviews:export",
        },
    }

    @classmethod
    def get_permissions(cls, role: str) -> list[str]:
        """Get the permission list for a given role.

        Falls back to READ_ONLY permissions for unknown roles.
        """
        return list(cls._PERMISSIONS.get(role, cls._PERMISSIONS[cls.READ_ONLY]))

    @classmethod
    def has_permission(cls, role: str, permission: str) -> bool:
        """Check if a role has a specific permission."""
        return permission in cls._PERMISSIONS.get(role, set())

    @classmethod
    def all_roles(cls) -> list[str]:
        """Get all defined roles."""
        return list(cls._PERMISSIONS.keys())

    @classmethod
    def all_permissions(cls) -> set[str]:
        """Get the union of all permissions across all roles."""
        result: set[str] = set()
        for perms in cls._PERMISSIONS.values():
            result.update(perms)
        return result


def resolve_permissions(user: UserContext) -> list[str]:
    """Resolve permissions for a user based on their role.

    This is the server-side permission resolution that can supplement
    or override JWT-derived permissions.

    If the user already has wildcard (*) permissions (admin bypass),
    return as-is. Otherwise, merge JWT permissions with role-based permissions.

    Args:
        user: The UserContext to resolve permissions for.

    Returns:
        List of resolved permission strings.
    """
    # Super admin bypass
    if "*" in user.permissions:
        return user.permissions

    # Get role-based permissions
    role_perms = Roles.get_permissions(user.role)

    # Merge with JWT permissions (JWT can grant additional permissions)
    merged = list(set(user.permissions) | set(role_perms))
    return merged


# ── Action Constants ──────────────────────────────────────────────

class Actions:
    """Canonical action names for policy-based authorization."""

    # Reviews
    REVIEW_READ = "review:read"
    REVIEW_CREATE = "review:create"
    REVIEW_APPROVE = "review:approve"
    REVIEW_REJECT = "review:reject"
    REVIEW_DELETE = "review:delete"
    REVIEW_ASSIGN = "review:assign"
    REVIEW_ESCALATE = "review:escalate"
    REVIEW_REANALYZE = "review:reanalyze"
    REVIEW_EXPORT = "review:export"
    REVIEW_COMMENT = "review:comment"

    # Workflow-specific actions
    WORKFLOW_FINALIZE = "workflow:finalize"
    WORKFLOW_ARCHIVE = "workflow:archive"
    WORKFLOW_BULK_ACTION = "workflow:bulk_action"

    # Findings
    FINDING_RESOLVE = "finding:resolve"
    FINDING_READ = "finding:read"

    # Redlines
    REDLINE_APPROVE = "redline:approve"
    REDLINE_REJECT = "redline:reject"
    REDLINE_MODIFY = "redline:modify"
    REDLINE_BULK_ACCEPT = "redline:bulk_accept"
    REDLINE_BULK_REJECT = "redline:bulk_reject"

    # AI
    AI_ANALYZE = "ai:analyze"
    AI_VIEW = "ai:view"
    AI_MANAGE = "ai:manage"

    # Audit
    AUDIT_READ = "audit:read"
    AUDIT_EXPORT = "audit:export"

    # Admin
    ADMIN_TENANT = "admin:tenant"
    ADMIN_SYSTEM = "admin:system"

    # Notifications
    NOTIFICATIONS_READ = "notifications:read"
    NOTIFICATIONS_MANAGE = "notifications:manage"


# ── Action-to-Permission Mapping ─────────────────────────────────
# Maps canonical action names to the permission strings used in RBAC.

_ACTION_PERMISSION_MAP: dict[str, str] = {
    Actions.REVIEW_READ: "contracts:read",
    Actions.REVIEW_CREATE: "contracts:write",
    Actions.REVIEW_APPROVE: "contracts:approve",
    Actions.REVIEW_REJECT: "contracts:approve",
    Actions.REVIEW_DELETE: "contracts:delete",
    Actions.REVIEW_ASSIGN: "workflows:write",
    Actions.REVIEW_ESCALATE: "workflows:escalate",
    Actions.REVIEW_REANALYZE: "ai:analyze",
    Actions.REVIEW_EXPORT: "reviews:export",
    Actions.REVIEW_COMMENT: "workflows:write",
    Actions.WORKFLOW_FINALIZE: "workflows:approve",
    Actions.WORKFLOW_ARCHIVE: "workflows:write",
    Actions.WORKFLOW_BULK_ACTION: "workflows:write",
    Actions.FINDING_RESOLVE: "workflows:write",
    Actions.FINDING_READ: "contracts:read",
    Actions.REDLINE_APPROVE: "workflows:approve",
    Actions.REDLINE_REJECT: "workflows:write",
    Actions.REDLINE_MODIFY: "workflows:write",
    Actions.REDLINE_BULK_ACCEPT: "workflows:write",
    Actions.REDLINE_BULK_REJECT: "workflows:write",
    Actions.AI_ANALYZE: "ai:analyze",
    Actions.AI_VIEW: "ai:view",
    Actions.AI_MANAGE: "ai:manage",
    Actions.AUDIT_READ: "audit:read",
    Actions.AUDIT_EXPORT: "audit:export",
    Actions.ADMIN_TENANT: "admin:tenant",
    Actions.ADMIN_SYSTEM: "admin:system",
    Actions.NOTIFICATIONS_READ: "notifications:read",
    Actions.NOTIFICATIONS_MANAGE: "notifications:manage",
}


def _resolve_action(action: str) -> str:
    """Resolve an action name to its corresponding permission string."""
    return _ACTION_PERMISSION_MAP.get(action, action)


def can(user: UserContext, action: str, resource: Optional[object] = None) -> bool:
    """Policy-based authorization check.

    Checks if a user can perform a given action on an optional resource.
    Actions are mapped to permission strings via _ACTION_PERMISSION_MAP.

    Args:
        user: The user context to check.
        action: The action to check (e.g., Actions.REVIEW_APPROVE).
        resource: Optional resource object for resource-specific checks.

    Returns:
        True if the user is authorized, False otherwise.

    Examples:
        can(user, Actions.REVIEW_APPROVE, review)
        can(user, Actions.REVIEW_DELETE)
        can(user, Actions.AUDIT_EXPORT)
    """
    # Super admin bypass
    if "*" in user.permissions:
        return True

    # Resolve action to permission string
    permission = _resolve_action(action)

    # Direct permission check
    if permission not in user.permissions:
        return False

    # Resource-specific checks
    if resource is not None:
        # Tenant isolation: user must belong to the resource's tenant
        resource_tenant_id = getattr(resource, "tenant_id", None)
        if resource_tenant_id and str(resource_tenant_id) != user.tenant_id:
            return False

        # Ownership check for certain actions
        if action in (Actions.REVIEW_DELETE, Actions.REVIEW_REANALYZE):
            # Only admins and the reviewer/creator can perform destructive actions
            resource_created_by = getattr(resource, "created_by", None)
            resource_assigned_to = getattr(resource, "assigned_to", None)
            if (
                user.role not in (Roles.ADMIN, Roles.LEGAL_REVIEWER)
                and resource_created_by != user.id
                and resource_assigned_to != user.id
            ):
                return False

    return True
