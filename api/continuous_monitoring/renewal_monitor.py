"""Auto-renewal alert system (V2-017).

Monitors contract renewal dates and generates alerts at configurable
lead times (30/60/90 days) per tenant. Integrates with the obligation
event bus to emit renewal_approaching and renewal_overdue events.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

from .event_bus import ObligationEventBus, ObligationEvent, EventType, EventPriority

logger = logging.getLogger(__name__)


class RenewalMonitor:
    """Monitors contract renewals and generates timely alerts.

    Checks contract end dates against configurable lead-time windows
    per tenant. Emits events to the obligation event bus when renewals
    are approaching or overdue.

    Usage:
        monitor = RenewalMonitor(event_bus)
        await monitor.check_renewals(contracts)
        alerts = await monitor.get_active_alerts("tenant-123")
    """

    def __init__(
        self,
        event_bus: ObligationEventBus,
        db_pool: Optional[Any] = None,
    ) -> None:
        """Initialize the renewal monitor.

        Args:
            event_bus: The obligation event bus for emitting events.
            db_pool: Optional database pool for persistence.
        """
        self._event_bus = event_bus
        self._db_pool = db_pool
        self._tenant_configs: Dict[str, Dict[str, int]] = {}
        self._default_lead_days = [90, 60, 30]
        self._emitted_renewals: Set[str] = set()

    def configure_tenant(
        self,
        tenant_id: str,
        lead_time_days_90: bool = True,
        lead_time_days_60: bool = True,
        lead_time_days_30: bool = True,
        custom_lead_days: Optional[List[int]] = None,
    ) -> None:
        """Configure renewal alert lead times for a tenant.

        Args:
            tenant_id: The tenant to configure.
            lead_time_days_90: Enable 90-day alert.
            lead_time_days_60: Enable 60-day alert.
            lead_time_days_30: Enable 30-day alert.
            custom_lead_days: Custom lead time windows (overrides defaults).
        """
        if custom_lead_days:
            self._tenant_configs[tenant_id] = {
                "lead_days": sorted(custom_lead_days, reverse=True),
            }
        else:
            days = []
            if lead_time_days_90:
                days.append(90)
            if lead_time_days_60:
                days.append(60)
            if lead_time_days_30:
                days.append(30)
            self._tenant_configs[tenant_id] = {
                "lead_days": sorted(days, reverse=True),
            }
        logger.info(
            "Configured renewal alerts for tenant %s: %s-day lead times",
            tenant_id,
            self._tenant_configs[tenant_id]["lead_days"],
        )

    def get_tenant_config(self, tenant_id: str) -> Dict[str, Any]:
        """Get the renewal alert configuration for a tenant.

        Args:
            tenant_id: The tenant identifier.

        Returns:
            Dict with lead_days list.
        """
        return self._tenant_configs.get(tenant_id, {"lead_days": self._default_lead_days})

    async def check_renewals(
        self,
        contracts: List[Dict[str, Any]],
        tenant_id: Optional[str] = None,
    ) -> List[ObligationEvent]:
        """Check all contracts for upcoming renewals and emit events.

        Args:
            contracts: List of contract dicts with end_date field.
            tenant_id: Optional tenant filter.

        Returns:
            List of emitted renewal events.
        """
        today = datetime.utcnow()
        emitted_events: List[ObligationEvent] = []

        for contract in contracts:
            ctenant = contract.get("tenant_id", "default")
            if tenant_id and ctenant != tenant_id:
                continue

            end_date_str = contract.get("end_date") or contract.get("renewal_date")
            if not end_date_str:
                continue

            try:
                end_date = datetime.fromisoformat(end_date_str)
            except (ValueError, TypeError):
                logger.warning("Invalid end_date for contract %s: %s",
                               contract.get("contract_id"), end_date_str)
                continue

            days_remaining = (end_date - today).days
            contract_id = contract.get("contract_id", "unknown")
            contract_name = contract.get("filename", contract_id)

            # Check if already overdue
            if days_remaining < 0:
                event_key = f"overdue_{contract_id}"
                if event_key not in self._emitted_renewals:
                    event = ObligationEventBus.create_event(
                        event_type=EventType.RENEWAL_OVERDUE,
                        contract_id=contract_id,
                        tenant_id=ctenant,
                        title=f"Contract renewal overdue: {contract_name}",
                        description=(
                            f"Contract {contract_name} renewal date ({end_date_str}) "
                            f"was {abs(days_remaining)} day(s) ago. Immediate attention required."
                        ),
                        priority=EventPriority.CRITICAL,
                        due_date=end_date_str,
                        days_until_due=days_remaining,
                        risk_score=min(10.0, max(5.0, 5.0 + abs(days_remaining) * 0.1)),
                        metadata={
                            "contract_name": contract_name,
                            "days_overdue": abs(days_remaining),
                            "end_date": end_date_str,
                        },
                    )
                    await self._event_bus.emit(event)
                    emitted_events.append(event)
                    self._emitted_renewals.add(event_key)
                continue

            # Check lead-time windows
            config = self.get_tenant_config(ctenant)
            lead_days = config["lead_days"]

            for lead_day in lead_days:
                if days_remaining <= lead_day and days_remaining > 0:
                    event_key = f"{lead_day}d_{contract_id}"
                    if event_key not in self._emitted_renewals:
                        priority = EventPriority.HIGH if lead_day <= 30 else EventPriority.MEDIUM
                        risk_score = max(1.0, 10.0 - (days_remaining / lead_day) * 10.0)

                        event = ObligationEventBus.create_event(
                            event_type=EventType.RENEWAL_APPROACHING,
                            contract_id=contract_id,
                            tenant_id=ctenant,
                            title=f"Contract renewal in {days_remaining} days: {contract_name}",
                            description=(
                                f"Contract {contract_name} renews on {end_date_str} "
                                f"({days_remaining} days remaining). "
                                f"Lead-time alert: {lead_day}-day window."
                            ),
                            priority=priority,
                            due_date=end_date_str,
                            days_until_due=days_remaining,
                            risk_score=round(risk_score, 2),
                            metadata={
                                "contract_name": contract_name,
                                "lead_time_days": lead_day,
                                "days_remaining": days_remaining,
                                "end_date": end_date_str,
                            },
                        )
                        await self._event_bus.emit(event)
                        emitted_events.append(event)
                        self._emitted_renewals.add(event_key)
                    break  # Only emit the closest lead-time alert

        if emitted_events:
            logger.info("Emitted %d renewal events", len(emitted_events))

        return emitted_events

    async def get_active_alerts(
        self,
        tenant_id: str,
    ) -> List[Dict[str, Any]]:
        """Get active (unresolved) renewal alerts for a tenant.

        Args:
            tenant_id: The tenant identifier.

        Returns:
            List of active renewal alert dicts.
        """
        events = await self._event_bus.get_events(
            tenant_id=tenant_id,
            unresolved_only=True,
        )
        renewal_events = [
            e for e in events
            if (e.event_type.value if isinstance(e.event_type, EventType) else e.event_type)
            in (EventType.RENEWAL_APPROACHING.value, EventType.RENEWAL_OVERDUE.value)
        ]
        return [e.to_dict() for e in renewal_events]

    async def get_renewal_summary(self, tenant_id: str) -> Dict[str, Any]:
        """Get a summary of renewal status for a tenant.

        Args:
            tenant_id: The tenant identifier.

        Returns:
            Dict with renewal summary statistics.
        """
        events = await self._event_bus.get_events(tenant_id=tenant_id)
        renewal_events = [
            e for e in events
            if (e.event_type.value if isinstance(e.event_type, EventType) else e.event_type)
            in (EventType.RENEWAL_APPROACHING.value, EventType.RENEWAL_OVERDUE.value)
        ]

        approaching = sum(
            1 for e in renewal_events
            if (e.event_type.value if isinstance(e.event_type, EventType) else e.event_type)
            == EventType.RENEWAL_APPROACHING.value
        )
        overdue = sum(
            1 for e in renewal_events
            if (e.event_type.value if isinstance(e.event_type, EventType) else e.event_type)
            == EventType.RENEWAL_OVERDUE.value
        )
        critical = sum(
            1 for e in renewal_events
            if (e.priority.value if isinstance(e.priority, EventPriority) else e.priority) == "critical"
        )

        return {
            "total_renewal_alerts": len(renewal_events),
            "approaching": approaching,
            "overdue": overdue,
            "critical": critical,
            "tenant_id": tenant_id,
        }
