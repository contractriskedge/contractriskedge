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
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "forbidden",
                    "message": f"Missing required permission: {permission}",
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
