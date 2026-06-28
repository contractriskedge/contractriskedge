"""Business Calendar Engine — SLA calculations using business hours.

Supports configurable working days, hours, holidays, timezones, and half-days.
Without a calendar, defaults to 24x7 wall-clock time.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ── Dataclasses ────────────────────────────────────────────────────


@dataclass
class BusinessCalendar:
    """Configuration for a business calendar used in SLA calculations."""
    calendar_id: str = ""
    name: str = ""
    timezone: str = "UTC"
    working_days: set[int] = field(default_factory=lambda: {0, 1, 2, 3, 4})  # Mon-Fri
    working_hours: tuple[float, float] = (9.0, 17.0)  # 9 AM to 5 PM
    holidays: list[dict[str, Any]] = field(default_factory=list)
    half_days: list[dict[str, Any]] = field(default_factory=list)


# ── Business Hours Calculator ──────────────────────────────────────


class BusinessHoursCalculator:
    """Calculates business hours between dates and deadlines.

    Supports configurable working days, hours, holidays, and half-days.
    Defaults to 24x7 wall-clock time when no calendar is provided.
    """

    def calculate_duration(
        self,
        start: datetime,
        end: datetime,
        calendar: Optional[BusinessCalendar] = None,
    ) -> float:
        """Calculate business hours between two dates.

        Args:
            start: The start datetime.
            end: The end datetime.
            calendar: Optional BusinessCalendar. If None, uses 24x7 wall-clock.

        Returns:
            Number of business hours between start and end.
        """
        if calendar is None:
            # Default 24x7 wall-clock
            diff = end - start
            return max(0.0, diff.total_seconds() / 3600.0)

        if end <= start:
            return 0.0

        total_hours = 0.0
        current = start

        # Parse working hours
        if isinstance(calendar.working_hours, dict):
            start_str = calendar.working_hours.get("start", "09:00")
            end_str = calendar.working_hours.get("end", "17:00")
        else:
            start_str, end_str = calendar.working_hours
        ds_h, ds_m = map(int, start_str.split(":"))
        de_h, de_m = map(int, end_str.split(":"))

        while current < end:
            if self._is_working_day(current, calendar):
                # Calculate business hours for this day
                day_start = current.replace(
                    hour=ds_h, minute=ds_m,
                    second=0, microsecond=0,
                )
                day_end = current.replace(
                    hour=de_h, minute=de_m,
                    second=0, microsecond=0,
                )

                # Adjust for half-day
                if self._is_half_day(current, calendar):
                    # Half-day means working until noon (or half of working hours)
                    half_day_end = current.replace(hour=12, minute=0, second=0, microsecond=0)
                    day_end = min(day_end, half_day_end)

                # Clamp to actual range
                effective_start = max(current, day_start)
                effective_end = min(end, day_end)

                if effective_start < effective_end:
                    total_hours += (effective_end - effective_start).total_seconds() / 3600.0

            current = (current + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )

        return total_hours

    def calculate_deadline(
        self,
        start: datetime,
        duration_hours: float,
        calendar: Optional[BusinessCalendar] = None,
    ) -> datetime:
        """Calculate the deadline from a start time plus business hours.

        Args:
            start: The start datetime.
            duration_hours: Number of business hours to add.
            calendar: Optional BusinessCalendar. If None, uses 24x7 wall-clock.

        Returns:
            The deadline datetime.
        """
        if calendar is None:
            # Default 24x7 wall-clock
            return start + timedelta(hours=duration_hours)

        if duration_hours <= 0:
            return start

        remaining = duration_hours
        current = start

        # Parse working hours from dict or tuple
        if isinstance(calendar.working_hours, dict):
            start_str = calendar.working_hours.get("start", "09:00")
            end_str = calendar.working_hours.get("end", "17:00")
        else:
            start_str, end_str = calendar.working_hours

        day_start_h, day_start_m = map(int, start_str.split(":"))
        day_end_h, day_end_m = map(int, end_str.split(":"))

        while remaining > 0:
            if self._is_working_day(current, calendar):
                day_start = current.replace(
                    hour=day_start_h, minute=day_start_m,
                    second=0, microsecond=0,
                )
                day_end = current.replace(
                    hour=day_end_h, minute=day_end_m,
                    second=0, microsecond=0,
                )

                # Adjust for half-day
                if self._is_half_day(current, calendar):
                    half_day_end = current.replace(hour=12, minute=0, second=0, microsecond=0)
                    day_end = min(day_end, half_day_end)

                # Start counting from the later of current time and day start
                effective_start = max(current, day_start)

                if effective_start < day_end:
                    available = (day_end - effective_start).total_seconds() / 3600.0
                    if available >= remaining:
                        return effective_start + timedelta(hours=remaining)
                    remaining -= available

            current = (current + timedelta(days=1)).replace(
                hour=day_start_h if day_start_h < 24 else 0,
                minute=0, second=0, microsecond=0,
            )

        return current

    def is_within_sla(
        self,
        start: datetime,
        deadline: datetime,
        calendar: Optional[BusinessCalendar] = None,
    ) -> bool:
        """Check if the current time is within the SLA window.

        Args:
            start: The start datetime.
            deadline: The SLA deadline datetime.
            calendar: Optional BusinessCalendar.

        Returns:
            True if current time is before or at the deadline.
        """
        now = datetime.now(timezone.utc)
        return now <= deadline

    def remaining_business_hours(
        self,
        start: datetime,
        deadline: datetime,
        calendar: Optional[BusinessCalendar] = None,
    ) -> float:
        """Calculate remaining business hours between now and the deadline.

        Args:
            start: The start datetime.
            deadline: The SLA deadline datetime.
            calendar: Optional BusinessCalendar.

        Returns:
            Number of remaining business hours. Returns 0 if past deadline.
        """
        now = datetime.now(timezone.utc)
        if now >= deadline:
            return 0.0
        return self.calculate_duration(now, deadline, calendar)

    # ── Private Helpers ─────────────────────────────────────────

    def _is_working_day(
        self,
        dt: datetime,
        calendar: BusinessCalendar,
    ) -> bool:
        """Check if a given datetime falls on a working day."""
        # Check if it's a holiday
        for holiday in calendar.holidays:
            if isinstance(holiday, str):
                try:
                    h_date = datetime.fromisoformat(holiday).date()
                    if dt.date() == h_date:
                        return False
                except (ValueError, TypeError):
                    continue
            elif isinstance(holiday, dict):
                holiday_date = holiday.get("date")
                if isinstance(holiday_date, date):
                    if dt.date() == holiday_date:
                        return False
                elif isinstance(holiday_date, str):
                    try:
                        h_date = datetime.fromisoformat(holiday_date).date()
                        if dt.date() == h_date:
                            return False
                    except (ValueError, TypeError):
                        continue

        # Check if it's a working day (weekday)
        return dt.weekday() in calendar.working_days

    def _is_half_day(
        self,
        dt: datetime,
        calendar: BusinessCalendar,
    ) -> bool:
        """Check if a given datetime falls on a half-day."""
        for half_day in calendar.half_days:
            half_date = half_day.get("date")
            if isinstance(half_date, date):
                if dt.date() == half_date:
                    return True
            elif isinstance(half_date, str):
                try:
                    h_date = datetime.fromisoformat(half_date).date()
                    if dt.date() == h_date:
                        return True
                except (ValueError, TypeError):
                    continue
        return False


# ── Default 24x7 Calendar ──────────────────────────────────────────


def default_calendar() -> BusinessCalendar:
    """Return a default 24x7 business calendar for backwards compatibility.

    This calendar has all days as working days and 24-hour working hours,
    matching the legacy wall-clock behavior.
    """
    return BusinessCalendar(
        calendar_id="default_24x7",
        name="24x7 Wall Clock (Default)",
        timezone="UTC",
        working_days={0, 1, 2, 3, 4, 5, 6},  # All days
        working_hours=(0.0, 24.0),  # 24 hours
        holidays=[],
        half_days=[],
    )



