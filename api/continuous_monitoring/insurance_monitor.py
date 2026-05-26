"""Insurance certificate expiration monitoring (V2-019).

Monitors insurance certificates associated with contracts and generates
configurable alerts when certificates are approaching expiration or
have expired. Integrates with the obligation event bus.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .event_bus import ObligationEventBus, ObligationEvent, EventType, EventPriority

logger = logging.getLogger(__name__)


@dataclass
class InsuranceCertificate:
    """Represents an insurance certificate associated with a contract."""

    cert_id: str
    contract_id: str
    tenant_id: str
    provider: str  # Insurance provider name
    policy_type: str  # general_liability, professional_indemnity, workers_comp, cyber, etc.
    policy_number: str
    coverage_amount: Optional[float] = None
    coverage_currency: str = "USD"
    effective_date: Optional[str] = None
    expiration_date: Optional[str] = None
    status: str = "active"  # active, expiring_soon, expired, replaced
    days_until_expiry: Optional[int] = None
    min_coverage_required: Optional[float] = None
    meets_minimum: Optional[bool] = None
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "cert_id": self.cert_id,
            "contract_id": self.contract_id,
            "tenant_id": self.tenant_id,
            "provider": self.provider,
            "policy_type": self.policy_type,
            "policy_number": self.policy_number,
            "coverage_amount": self.coverage_amount,
            "coverage_currency": self.coverage_currency,
            "effective_date": self.effective_date,
            "expiration_date": self.expiration_date,
            "status": self.status,
            "days_until_expiry": self.days_until_expiry,
            "min_coverage_required": self.min_coverage_required,
            "meets_minimum": self.meets_minimum,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class InsuranceMonitor:
    """Monitors insurance certificate expirations.

    Checks certificate expiration dates against configurable warning
    windows and emits events to the obligation event bus.

    Usage:
        monitor = InsuranceMonitor(event_bus)
        await monitor.register_certificate(cert)
        await monitor.check_expirations()
        report = await monitor.get_expiration_report("tenant-123")
    """

    def __init__(
        self,
        event_bus: ObligationEventBus,
        db_pool: Optional[Any] = None,
    ) -> None:
        """Initialize the insurance monitor.

        Args:
            event_bus: The obligation event bus.
            db_pool: Optional database pool.
        """
        self._event_bus = event_bus
        self._db_pool = db_pool
        self._certificates: Dict[str, InsuranceCertificate] = {}
        self._warning_days: int = 60  # Default: warn 60 days before expiry
        self._critical_days: int = 30  # Critical: 30 days before expiry
        self._emitted_alerts: Dict[str, str] = {}  # cert_id -> alert_type

    def configure_warning_periods(
        self,
        warning_days: int = 60,
        critical_days: int = 30,
    ) -> None:
        """Configure the warning period thresholds.

        Args:
            warning_days: Days before expiry to start warning.
            critical_days: Days before expiry to mark as critical.
        """
        self._warning_days = warning_days
        self._critical_days = critical_days
        logger.info("Configured insurance warnings: %d days warning, %d days critical",
                     warning_days, critical_days)

    async def register_certificate(self, cert: InsuranceCertificate) -> str:
        """Register an insurance certificate for monitoring.

        Args:
            cert: The insurance certificate to track.

        Returns:
            The certificate ID.
        """
        self._certificates[cert.cert_id] = cert
        logger.info("Registered insurance cert %s: %s (%s, policy %s)",
                     cert.cert_id, cert.provider, cert.policy_type, cert.policy_number)
        return cert.cert_id

    async def register_certificates_batch(self, certs: List[InsuranceCertificate]) -> List[str]:
        """Register multiple insurance certificates at once.

        Args:
            certs: List of certificates.

        Returns:
            List of certificate IDs.
        """
        ids = []
        for cert in certs:
            ids.append(await self.register_certificate(cert))
        return ids

    async def check_expirations(self) -> List[Dict[str, Any]]:
        """Check all certificates for approaching expirations.

        Computes days until expiry and emits events for certificates
        that are expiring soon or have expired.

        Returns:
            List of alert dicts for certificates needing attention.
        """
        today = datetime.utcnow()
        alerts: List[Dict[str, Any]] = []

        for cert in self._certificates.values():
            if cert.status == "replaced":
                continue

            if not cert.expiration_date:
                continue

            try:
                expiry = datetime.fromisoformat(cert.expiration_date)
            except (ValueError, TypeError):
                continue

            days_remaining = (expiry - today).days
            cert.days_until_expiry = days_remaining

            # Check minimum coverage
            if cert.min_coverage_required is not None and cert.coverage_amount is not None:
                cert.meets_minimum = cert.coverage_amount >= cert.min_coverage_required
            else:
                cert.meets_minimum = None

            if days_remaining < 0:
                # Expired
                if cert.status != "expired":
                    cert.status = "expired"
                    event = ObligationEventBus.create_event(
                        event_type=EventType.INSURANCE_EXPIRED,
                        contract_id=cert.contract_id,
                        tenant_id=cert.tenant_id,
                        title=f"Insurance expired: {cert.provider} ({cert.policy_type})",
                        description=(
                            f"Insurance certificate from {cert.provider} (policy {cert.policy_number}, "
                            f"{cert.policy_type}) expired {abs(days_remaining)} day(s) ago. "
                            f"Coverage amount: ${cert.coverage_amount:,.2f if cert.coverage_amount else 'N/A'}"
                        ),
                        priority=EventPriority.CRITICAL,
                        due_date=cert.expiration_date,
                        days_until_due=days_remaining,
                        risk_score=min(10.0, 8.0 + abs(days_remaining) * 0.1),
                        metadata={
                            "cert_id": cert.cert_id,
                            "provider": cert.provider,
                            "policy_type": cert.policy_type,
                            "policy_number": cert.policy_number,
                            "days_expired": abs(days_remaining),
                            "coverage_amount": cert.coverage_amount,
                            "meets_minimum": cert.meets_minimum,
                        },
                    )
                    await self._event_bus.emit(event)
                    alerts.append({
                        "cert_id": cert.cert_id,
                        "contract_id": cert.contract_id,
                        "status": "expired",
                        "days_expired": abs(days_remaining),
                        "severity": "critical",
                    })
            elif days_remaining <= self._critical_days:
                # Critical - expiring very soon
                if cert.status != "expiring_soon" or self._emitted_alerts.get(cert.cert_id) != "critical":
                    cert.status = "expiring_soon"
                    self._emitted_alerts[cert.cert_id] = "critical"
                    event = ObligationEventBus.create_event(
                        event_type=EventType.INSURANCE_EXPIRING,
                        contract_id=cert.contract_id,
                        tenant_id=cert.tenant_id,
                        title=f"Insurance expiring in {days_remaining} days: {cert.provider}",
                        description=(
                            f"Insurance certificate from {cert.provider} ({cert.policy_type}) "
                            f"expires in {days_remaining} days. Policy: {cert.policy_number}. "
                            f"Coverage: ${cert.coverage_amount:,.2f if cert.coverage_amount else 'N/A'}"
                        ),
                        priority=EventPriority.HIGH,
                        due_date=cert.expiration_date,
                        days_until_due=days_remaining,
                        risk_score=min(9.0, 7.0 + (self._critical_days - days_remaining) * 0.2),
                        metadata={
                            "cert_id": cert.cert_id,
                            "provider": cert.provider,
                            "policy_type": cert.policy_type,
                            "days_remaining": days_remaining,
                        },
                    )
                    await self._event_bus.emit(event)
                    alerts.append({
                        "cert_id": cert.cert_id,
                        "contract_id": cert.contract_id,
                        "status": "critical",
                        "days_remaining": days_remaining,
                        "severity": "high",
                    })
            elif days_remaining <= self._warning_days:
                # Warning - approaching expiry
                if self._emitted_alerts.get(cert.cert_id) != "warning":
                    self._emitted_alerts[cert.cert_id] = "warning"
                    event = ObligationEventBus.create_event(
                        event_type=EventType.INSURANCE_EXPIRING,
                        contract_id=cert.contract_id,
                        tenant_id=cert.tenant_id,
                        title=f"Insurance approaching expiry: {cert.provider}",
                        description=(
                            f"Insurance certificate from {cert.provider} ({cert.policy_type}) "
                            f"expires in {days_remaining} days. Policy: {cert.policy_number}."
                        ),
                        priority=EventPriority.MEDIUM,
                        due_date=cert.expiration_date,
                        days_until_due=days_remaining,
                        risk_score=round(max(1.0, 5.0 - (days_remaining / self._warning_days) * 5.0), 2),
                        metadata={
                            "cert_id": cert.cert_id,
                            "provider": cert.provider,
                            "days_remaining": days_remaining,
                        },
                    )
                    await self._event_bus.emit(event)
                    alerts.append({
                        "cert_id": cert.cert_id,
                        "contract_id": cert.contract_id,
                        "status": "warning",
                        "days_remaining": days_remaining,
                        "severity": "medium",
                    })

        return alerts

    async def get_expiration_report(self, tenant_id: str) -> Dict[str, Any]:
        """Generate an insurance expiration report for a tenant.

        Args:
            tenant_id: The tenant identifier.

        Returns:
            Dict with expiration summary and certificate details.
        """
        tenant_certs = [c for c in self._certificates.values() if c.tenant_id == tenant_id]

        active = sum(1 for c in tenant_certs if c.status == "active")
        expiring_soon = sum(1 for c in tenant_certs if c.status == "expiring_soon")
        expired = sum(1 for c in tenant_certs if c.status == "expired")
        replaced = sum(1 for c in tenant_certs if c.status == "replaced")
        not_meeting_minimum = sum(1 for c in tenant_certs if c.meets_minimum is False)

        by_type: Dict[str, int] = {}
        for c in tenant_certs:
            by_type[c.policy_type] = by_type.get(c.policy_type, 0) + 1

        return {
            "tenant_id": tenant_id,
            "total_certificates": len(tenant_certs),
            "status_breakdown": {
                "active": active,
                "expiring_soon": expiring_soon,
                "expired": expired,
                "replaced": replaced,
            },
            "coverage_issues": {
                "not_meeting_minimum": not_meeting_minimum,
            },
            "by_policy_type": by_type,
        }

    async def get_certificates_for_contract(
        self,
        contract_id: str,
    ) -> List[Dict[str, Any]]:
        """Get all insurance certificates for a contract.

        Args:
            contract_id: The contract identifier.

        Returns:
            List of certificate dicts.
        """
        certs = [
            c for c in self._certificates.values()
            if c.contract_id == contract_id
        ]
        return [c.to_dict() for c in certs]
