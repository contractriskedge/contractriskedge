"""User management API endpoints.

Provides CRUD operations for managing users within a tenant,
including role assignment, permission management, and user status.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from middleware.auth import TokenPayload, get_current_user, require_permission, Permissions

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])


async def _get_repo(request: Request):
    """Get the database repository from the app's state.

    Uses request.app.state to access the shared application state,
    avoiding circular import issues with the main module.
    """
    db_repo = getattr(request.app.state, "db_repo", None)
    if db_repo is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not available",
        )
    return db_repo


@router.get("")
@router.get("/")
async def list_users(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.MANAGE_USERS)),
) -> Dict[str, Any]:
    """List all users for the current tenant.

    Args:
        request: FastAPI request (used to access app state).
        page: Page number.
        page_size: Items per page.
        user: Authenticated user.

    Returns:
        Dict with users list and pagination.
    """
    repo = await _get_repo(request)
    tenant_id = user.tenant_id or "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    users = await repo.list_users(tenant_id, limit=page_size, offset=(page - 1) * page_size)
    return {
        "users": users,
        "total": len(users),
        "page": page,
        "page_size": page_size,
    }


@router.get("/{user_id}")
async def get_user(
    request: Request,
    user_id: str,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.MANAGE_USERS)),
) -> Dict[str, Any]:
    """Get a user by ID.

    Args:
        request: FastAPI request (used to access app state).
        user_id: The user identifier.
        user: Authenticated user.

    Returns:
        User details.

    Raises:
        HTTPException: If user not found.
    """
    repo = await _get_repo(request)
    found = await repo.get_user(user_id)
    if found is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )
    return found


@router.post("")
@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(
    request: Request,
    user_data: Dict[str, Any],
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.MANAGE_USERS)),
) -> Dict[str, Any]:
    """Create a new user.

    Args:
        request: FastAPI request (used to access app state).
        user_data: User data with required fields: user_id, email.
        user: Authenticated user.

    Returns:
        Created user.

    Raises:
        HTTPException: If user_id or email missing.
    """
    if "user_id" not in user_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Field 'user_id' is required",
        )
    if "email" not in user_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Field 'email' is required",
        )

    repo = await _get_repo(request)

    # Check if user already exists
    existing = await repo.get_user(user_data["user_id"])
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User {user_data['user_id']} already exists",
        )

    # Set tenant from current user if not specified
    if "tenant_id" not in user_data:
        user_data["tenant_id"] = user.tenant_id or "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

    created = await repo.create_user(user_data)
    logger.info("User %s created by %s", created["user_id"], user.sub)
    return created


@router.patch("/{user_id}")
async def update_user(
    request: Request,
    user_id: str,
    updates: Dict[str, Any],
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.MANAGE_USERS)),
) -> Dict[str, Any]:
    """Update a user.

    Args:
        request: FastAPI request (used to access app state).
        user_id: The user to update.
        updates: Fields to update (email, name, role, is_active, permissions).
        user: Authenticated user.

    Returns:
        Updated user.

    Raises:
        HTTPException: If user not found.
    """
    repo = await _get_repo(request)
    existing = await repo.get_user(user_id)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    # Only allow updating allowed fields
    allowed = {"email", "name", "role", "is_active", "permissions", "metadata"}
    filtered = {k: v for k, v in updates.items() if k in allowed}

    if not filtered:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No valid fields to update. Allowed: {', '.join(sorted(allowed))}",
        )

    updated = await repo.update_user(user_id, filtered)
    logger.info("User %s updated by %s: %s", user_id, user.sub, set(filtered.keys()))
    return updated


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    request: Request,
    user_id: str,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.MANAGE_USERS)),
) -> None:
    """Delete a user.

    Args:
        request: FastAPI request (used to access app state).
        user_id: The user to delete.
        user: Authenticated user.

    Raises:
        HTTPException: If user not found or cannot delete self.
    """
    if user_id == user.sub:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own user account",
        )

    repo = await _get_repo(request)
    deleted = await repo.delete_user(user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )
    logger.info("User %s deleted by %s", user_id, user.sub)
