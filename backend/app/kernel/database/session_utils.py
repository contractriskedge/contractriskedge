"""Helpers for safe async session cleanup."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def safe_session_rollback(session: AsyncSession | None) -> None:
    """Rollback without raising when the underlying connection is already closed."""
    if session is None:
        return
    try:
        if session.is_active:
            await session.rollback()
    except Exception as exc:
        logger.warning("Session rollback skipped (connection may be stale): %s", exc)


async def release_session_before_io(session: AsyncSession | None) -> None:
    """Commit or rollback so long external I/O does not hold an idle transaction."""
    if session is None:
        return
    try:
        if session.in_transaction():
            await session.commit()
    except Exception as exc:
        logger.warning("Failed to release session before I/O, rolling back: %s", exc)
        await safe_session_rollback(session)
