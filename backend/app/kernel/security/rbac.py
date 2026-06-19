"""Role-based access control — permission checking dependency.

Provides the ``require_permission`` decorator / dependency factory
used across all domain routers.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Depends, HTTPException, status

from app.dependencies import get_current_user
from app.kernel.security.auth import UserContext
from app.kernel.security.permissions import Permissions

logger = logging.getLogger(__name__)


def require_permission(permission: str) -> Any:
    """Decorator / dependency factory: require a specific permission.

    Usage as a decorator::

        @router.get("/contracts")
        @require_permission(Permissions.CONTRACTS_READ)
        async def list_contracts(...):
            ...

    Usage as a dependency::

        @router.get("/contracts")
        async def list_contracts(
            _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
            ...
        ):
            ...
    """

    async def _check(user: UserContext = Depends(get_current_user)) -> None:
        if Permissions.ALL in user.permissions:
            return  # super_admin bypass
        if permission not in user.permissions:
            logger.warning(
                "Permission denied: user %s lacks '%s' (has: %s)",
                user.id,
                permission,
                user.permissions,
            )
            # Map technical permission names to user-friendly messages
            _friendly_messages = {
                "contracts:approve": "Approval is restricted to authorized reviewers. Please contact your administrator if you need approval access.",
                "contracts:write": "You have read-only access to contracts. Changes require additional permissions.",
                "contracts:delete": "Contract deletion is restricted to administrators.",
                "workflows:write": "You have read-only access to workflows. Changes require additional permissions.",
                "workflows:approve": "Workflow approval is restricted to authorized reviewers.",
                "workflows:escalate": "Escalation is restricted to authorized reviewers.",
                "admin:tenant": "Tenant settings are restricted to administrators.",
                "admin:system": "System administration is restricted to administrators.",
                "users:write": "User management is restricted to administrators.",
                "audit:export": "Audit export is restricted to authorized users.",
            }
            friendly = _friendly_messages.get(permission, f"Access denied. You need '{permission}' permission to perform this action.")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "forbidden",
                    "message": friendly,
                },
            )

    return _check


def require_any_permission(*permissions: str) -> Any:
    """Dependency factory: require at least one of the given permissions."""

    async def _check(user: UserContext = Depends(get_current_user)) -> None:
        if Permissions.ALL in user.permissions:
            return
        if not any(p in user.permissions for p in permissions):
            logger.warning(
                "Permission denied: user %s lacks any of %s (has: %s)",
                user.id,
                permissions,
                user.permissions,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "forbidden",
                    "message": f"Missing required permission (need one of): {', '.join(permissions)}",
                },
            )

    return _check
