"""UTC datetime helpers for consistent aware datetime arithmetic."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional


def utc_now() -> datetime:
    """Current time as a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def ensure_utc(value: Optional[datetime]) -> Optional[datetime]:
    """Normalize a datetime to UTC-aware.

    Naive values are treated as UTC (matches PostgreSQL timestamptz from asyncpg).
    """
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def age_minutes(later: datetime, earlier: datetime) -> float:
    """Minutes between two datetimes (both normalized to UTC)."""
    return (ensure_utc(later) - ensure_utc(earlier)).total_seconds() / 60.0
