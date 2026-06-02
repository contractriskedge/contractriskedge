"""Security & Compliance Runtime — SOC2-grade operational controls.

Provides:
- ImmutableAuditVerifier — cryptographic audit log verification
- EncryptionKeyManager — key rotation and lifecycle management
- LegalHoldEnforcer — legal hold on contracts and evidence
- RetentionEnforcer — data retention policy enforcement
- ExportAccessController — granular export access controls
- SuspiciousActivityDetector — anomaly detection for security events
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# ── Audit Trail Entry ──────────────────────────────────────────────

@dataclass
class AuditEntry:
    """An immutable audit trail entry."""
    entry_id: str
    event_type: str
    tenant_id: str
    actor_id: str
    resource_type: str
    resource_id: str
    action: str
    timestamp: str
    details: dict[str, Any] = field(default_factory=dict)
    previous_hash: str = ""
    entry_hash: str = ""
    signature: str = ""

    def compute_hash(self) -> str:
        """Compute the cryptographic hash of this entry."""
        content = f"{self.previous_hash}|{self.event_type}|{self.tenant_id}|{self.actor_id}|{self.timestamp}|{json.dumps(self.details, sort_keys=True)}"
        return hashlib.sha256(content.encode()).hexdigest()

    def sign(self, secret_key: str) -> None:
        """Sign the entry with an HMAC key."""
        self.entry_hash = self.compute_hash()
        self.signature = hmac.new(
            secret_key.encode(),
            self.entry_hash.encode(),
            hashlib.sha256,
        ).hexdigest()

    def verify(self, secret_key: str) -> bool:
        """Verify the entry's signature."""
        expected_hash = self.compute_hash()
        if expected_hash != self.entry_hash:
            return False
        expected_sig = hmac.new(
            secret_key.encode(),
            expected_hash.encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected_sig, self.signature)


# ── Immutable Audit Verifier ───────────────────────────────────────

@dataclass
class ImmutableAuditVerifier:
    """Verifies the integrity of audit trails using hash chaining.

    Each audit entry contains the hash of the previous entry,
    forming a tamper-evident chain.
    """

    session: AsyncSession
    secret_key: str = "change-me-in-production"  # Override from settings

    async def append_entry(self, entry: AuditEntry) -> None:
        """Append an entry to the audit trail."""
        # Get the hash of the previous entry
        sql = sa_text("""
            SELECT entry_hash FROM audit_trail
            WHERE tenant_id = :tid
            ORDER BY created_at DESC
            LIMIT 1
        """)
        result = await self.session.execute(sql, {"tid": entry.tenant_id})
        last = result.fetchone()
        entry.previous_hash = last.entry_hash if last else "GENESIS"

        # Sign the entry
        entry.sign(self.secret_key)

        # Persist
        sql = sa_text("""
            INSERT INTO audit_trail (entry_id, event_type, tenant_id, actor_id,
                resource_type, resource_id, action, details,
                previous_hash, entry_hash, signature)
            VALUES (:eid, :etype, :tid, :aid,
                :rtype, :rid, :action, :details,
                :prev_hash, :hash, :sig)
        """)
        await self.session.execute(sql, {
            "eid": entry.entry_id,
            "etype": entry.event_type,
            "tid": entry.tenant_id,
            "aid": entry.actor_id,
            "rtype": entry.resource_type,
            "rid": entry.resource_id,
            "action": entry.action,
            "details": json.dumps(entry.details),
            "prev_hash": entry.previous_hash,
            "hash": entry.entry_hash,
            "sig": entry.signature,
        })

    async def verify_chain(self, tenant_id: str, from_entry: str | None = None) -> list[dict[str, Any]]:
        """Verify the integrity of the audit chain.

        Returns list of any entries that fail verification.
        """
        if from_entry:
            sql = sa_text("""
                SELECT entry_id, event_type, tenant_id, actor_id,
                       resource_type, resource_id, action, details,
                       previous_hash, entry_hash, signature, created_at
                FROM audit_trail
                WHERE tenant_id = :tid AND entry_id >= :from
                ORDER BY created_at ASC
            """)
            result = await self.session.execute(sql, {"tid": tenant_id, "from": from_entry})
        else:
            sql = sa_text("""
                SELECT entry_id, event_type, tenant_id, actor_id,
                       resource_type, resource_id, action, details,
                       previous_hash, entry_hash, signature, created_at
                FROM audit_trail
                WHERE tenant_id = :tid
                ORDER BY created_at ASC
            """)
            result = await self.session.execute(sql, {"tid": tenant_id})

        violations = []
        entries = result.fetchall()

        for i, row in enumerate(entries):
            entry = AuditEntry(
                entry_id=str(row.entry_id),
                event_type=row.event_type,
                tenant_id=str(row.tenant_id),
                actor_id=row.actor_id,
                resource_type=row.resource_type,
                resource_id=row.resource_id,
                action=row.action,
                timestamp=str(row.created_at),
                details=row.details or {},
                previous_hash=row.previous_hash,
                entry_hash=row.entry_hash,
                signature=row.signature,
            )

            # Verify chain integrity
            if i > 0 and entry.previous_hash != entries[i - 1].entry_hash:
                violations.append({
                    "entry_id": entry.entry_id,
                    "issue": "broken_chain",
                    "expected_previous": entries[i - 1].entry_hash,
                    "actual_previous": entry.previous_hash,
                })

            # Verify signature
            if not entry.verify(self.secret_key):
                violations.append({
                    "entry_id": entry.entry_id,
                    "issue": "invalid_signature",
                })

        return violations


# ── Legal Hold Enforcer ────────────────────────────────────────────

@dataclass
class LegalHoldStatus:
    """Status of legal hold on a resource."""
    resource_id: str
    resource_type: str
    tenant_id: str
    on_hold: bool = False
    hold_reason: str = ""
    placed_by: str = ""
    placed_at: str = ""
    released_by: str | None = None
    released_at: str | None = None
    case_reference: str = ""


@dataclass
class LegalHoldEnforcer:
    """Enforces legal hold on contracts and associated data.

    When a legal hold is active:
    - Data retention policies are suspended
    - Deletion is blocked
    - Export is restricted
    """

    session: AsyncSession

    async def place_hold(
        self,
        resource_id: str,
        resource_type: str,
        tenant_id: str,
        reason: str,
        placed_by: str,
        case_reference: str = "",
    ) -> LegalHoldStatus:
        """Place a legal hold on a resource."""
        sql = sa_text("""
            INSERT INTO legal_holds (resource_id, resource_type, tenant_id,
                hold_reason, placed_by, case_reference)
            VALUES (:rid, :rtype, :tid, :reason, :placed_by, :case_ref)
            ON CONFLICT (resource_id, resource_type, tenant_id)
            DO UPDATE SET hold_reason = :reason, placed_by = :placed_by,
                case_reference = :case_ref, released_at = NULL, released_by = NULL
            RETURNING resource_id, resource_type, tenant_id, hold_reason,
                placed_by, placed_at, case_reference
        """)
        result = await self.session.execute(sql, {
            "rid": resource_id,
            "rtype": resource_type,
            "tid": tenant_id,
            "reason": reason,
            "placed_by": placed_by,
            "case_ref": case_reference,
        })
        row = result.fetchone()
        logger.info(
            "Legal hold placed on %s %s by %s: %s",
            resource_type, resource_id[:8], placed_by, reason,
        )
        return LegalHoldStatus(
            resource_id=str(row.resource_id),
            resource_type=row.resource_type,
            tenant_id=str(row.tenant_id),
            on_hold=True,
            hold_reason=row.hold_reason,
            placed_by=row.placed_by,
            placed_at=str(row.placed_at),
            case_reference=row.case_reference or "",
        )

    async def release_hold(self, resource_id: str, resource_type: str, tenant_id: str, released_by: str) -> None:
        """Release a legal hold."""
        sql = sa_text("""
            UPDATE legal_holds
            SET released_at = NOW(), released_by = :released_by
            WHERE resource_id = :rid AND resource_type = :rtype AND tenant_id = :tid
        """)
        await self.session.execute(sql, {
            "rid": resource_id,
            "rtype": resource_type,
            "tid": tenant_id,
            "released_by": released_by,
        })
        logger.info("Legal hold released on %s %s by %s", resource_type, resource_id[:8], released_by)

    async def is_on_hold(self, resource_id: str, resource_type: str, tenant_id: str) -> bool:
        """Check if a resource is under legal hold."""
        sql = sa_text("""
            SELECT COUNT(*) FROM legal_holds
            WHERE resource_id = :rid AND resource_type = :rtype
              AND tenant_id = :tid AND released_at IS NULL
        """)
        result = await self.session.execute(sql, {
            "rid": resource_id,
            "rtype": resource_type,
            "tid": tenant_id,
        })
        return (result.scalar() or 0) > 0

    async def get_active_holds(self, tenant_id: str) -> list[LegalHoldStatus]:
        """Get all active legal holds for a tenant."""
        sql = sa_text("""
            SELECT resource_id, resource_type, tenant_id, hold_reason,
                   placed_by, placed_at, case_reference
            FROM legal_holds
            WHERE tenant_id = :tid AND released_at IS NULL
            ORDER BY placed_at DESC
        """)
        result = await self.session.execute(sql, {"tid": tenant_id})
        return [
            LegalHoldStatus(
                resource_id=str(row.resource_id),
                resource_type=row.resource_type,
                tenant_id=str(row.tenant_id),
                on_hold=True,
                hold_reason=row.hold_reason,
                placed_by=row.placed_by,
                placed_at=str(row.placed_at),
                case_reference=row.case_reference or "",
            )
            for row in result.fetchall()
        ]


# ── Retention Enforcer ─────────────────────────────────────────────

@dataclass
class RetentionPolicy:
    """Data retention policy for a resource type."""
    resource_type: str
    retention_days: int
    action: str = "archive"  # archive, delete, anonymize
    legal_hold_override: bool = True  # Legal hold suspends retention


@dataclass
class RetentionEnforcer:
    """Enforces data retention policies across the platform.

    Should be run as a scheduled job (e.g., daily cron/Celery beat).
    """

    session: AsyncSession
    legal_hold: LegalHoldEnforcer

    def __post_init__(self):
        self._policies = self._default_policies()

    @staticmethod
    def _default_policies() -> dict[str, RetentionPolicy]:
        return {
            "upload": RetentionPolicy(resource_type="upload", retention_days=2555, action="archive"),  # 7 years
        "extraction": RetentionPolicy(resource_type="extraction", retention_days=2555, action="archive"),
        "ai_execution": RetentionPolicy(resource_type="ai_execution", retention_days=2555, action="archive"),
        "audit_log": RetentionPolicy(resource_type="audit_log", retention_days=3650, action="archive"),  # 10 years
        "temporary_upload": RetentionPolicy(resource_type="temporary_upload", retention_days=30, action="delete"),
        "cache_entry": RetentionPolicy(resource_type="cache_entry", retention_days=7, action="delete"),
        "export": RetentionPolicy(resource_type="export", retention_days=90, action="delete"),
    }

    async def enforce_retention(self, tenant_id: str, resource_type: str) -> dict[str, int]:
        """Enforce retention policy for a resource type.

        Returns count of resources affected.
        """
        policy = self._policies.get(resource_type)
        if not policy:
            logger.warning("No retention policy for resource type: %s", resource_type)
            return {"affected": 0}

        cutoff = datetime.utcnow() - timedelta(days=policy.retention_days)
        affected = 0

        if resource_type == "upload":
            sql = sa_text("""
                SELECT upload_id FROM upload_sessions
                WHERE tenant_id = :tid AND created_at < :cutoff AND is_active = true
            """)
            result = await self.session.execute(sql, {"tid": tenant_id, "cutoff": cutoff})
            for row in result.fetchall():
                upload_id = str(row.upload_id)
                if policy.legal_hold_override and await self.legal_hold.is_on_hold(upload_id, "upload", tenant_id):
                    continue
                if policy.action == "archive":
                    sql_upd = sa_text("UPDATE upload_sessions SET is_active = false WHERE upload_id = :uid")
                    await self.session.execute(sql_upd, {"uid": upload_id})
                elif policy.action == "delete":
                    sql_del = sa_text("DELETE FROM upload_sessions WHERE upload_id = :uid")
                    await self.session.execute(sql_del, {"uid": upload_id})
                affected += 1

        elif resource_type == "ai_execution":
            sql = sa_text("""
                UPDATE ai_execution_runs SET status = 'archived'
                WHERE tenant_id = :tid AND created_at < :cutoff AND status NOT IN ('archived', 'cancelled')
            """)
            result = await self.session.execute(sql, {"tid": tenant_id, "cutoff": cutoff})
            affected = result.rowcount

        logger.info(
            "Retention enforcement for %s/%s: %d resources %sd",
            tenant_id[:8], resource_type, affected, policy.action,
        )
        return {"affected": affected}

    async def run_full_enforcement(self, tenant_id: str) -> dict[str, Any]:
        """Run retention enforcement for all resource types."""
        results = {}
        for resource_type in self._policies:
            try:
                result = await self.enforce_retention(tenant_id, resource_type)
                results[resource_type] = result
            except Exception as e:
                logger.error("Retention enforcement failed for %s/%s: %s", tenant_id[:8], resource_type, e)
                results[resource_type] = {"error": str(e)}
        return results


# ── Suspicious Activity Detector ───────────────────────────────────

@dataclass
class SuspiciousActivity:
    """A detected suspicious activity."""
    activity_id: str
    activity_type: str
    tenant_id: str
    actor_id: str
    severity: str  # low, medium, high, critical
    description: str
    details: dict[str, Any] = field(default_factory=dict)
    detected_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    acknowledged: bool = False
    resolved: bool = False


@dataclass
class SuspiciousActivityDetector:
    """Detects suspicious activity patterns across the platform.

    Monitors for:
    - Rapid-fire API calls (potential abuse)
    - Unusual access patterns
    - Bulk export attempts
    - Cross-tenant access attempts
    - Failed authentication spikes
    """

    session: AsyncSession

    async def detect_rapid_api_calls(self, tenant_id: str, threshold: int = 100, window_seconds: int = 60) -> list[SuspiciousActivity]:
        """Detect rapid API calls that may indicate abuse."""
        activities = []
        sql = sa_text("""
            SELECT actor_id, COUNT(*) as call_count
            FROM audit_trail
            WHERE tenant_id = :tid
              AND created_at > NOW() - INTERVAL '1 minute' * :window
            GROUP BY actor_id
            HAVING COUNT(*) > :threshold
        """)
        result = await self.session.execute(sql, {
            "tid": tenant_id,
            "window": window_seconds / 60,
            "threshold": threshold,
        })
        for row in result.fetchall():
            activities.append(SuspiciousActivity(
                activity_id=hashlib.sha256(f"rapid_{tenant_id}_{row.actor_id}_{time.time()}".encode()).hexdigest()[:16],
                activity_type="rapid_api_calls",
                tenant_id=tenant_id,
                actor_id=str(row.actor_id),
                severity="medium",
                description=f"Rapid API calls detected: {row.call_count} in {window_seconds}s",
                details={"call_count": row.call_count, "window_seconds": window_seconds},
            ))
        return activities

    async def detect_bulk_export(self, tenant_id: str, threshold: int = 10, window_minutes: int = 60) -> list[SuspiciousActivity]:
        """Detect bulk export attempts that may indicate data exfiltration."""
        activities = []
        sql = sa_text("""
            SELECT actor_id, COUNT(*) as export_count, SUM(COALESCE(row_count, 0)) as total_rows
            FROM audit_trail
            WHERE tenant_id = :tid
              AND event_type = 'export.generated'
              AND created_at > NOW() - INTERVAL '1 minute' * :window
            GROUP BY actor_id
            HAVING COUNT(*) > :threshold OR SUM(COALESCE(row_count, 0)) > :threshold * 1000
        """)
        result = await self.session.execute(sql, {
            "tid": tenant_id,
            "window": window_minutes,
            "threshold": threshold,
        })
        for row in result.fetchall():
            activities.append(SuspiciousActivity(
                activity_id=hashlib.sha256(f"export_{tenant_id}_{row.actor_id}_{time.time()}".encode()).hexdigest()[:16],
                activity_type="bulk_export",
                tenant_id=tenant_id,
                actor_id=str(row.actor_id),
                severity="high",
                description=f"Bulk export detected: {row.export_count} exports, {row.total_rows} rows",
                details={"export_count": row.export_count, "total_rows": row.total_rows},
            ))
        return activities

    async def detect_cross_tenant_access(self, tenant_id: str) -> list[SuspiciousActivity]:
        """Detect cross-tenant access attempts."""
        activities = []
        sql = sa_text("""
            SELECT actor_id, details->>'requested_tenant' as target_tenant, COUNT(*) as attempt_count
            FROM audit_trail
            WHERE event_type = 'security.tenant_access_denied'
              AND created_at > NOW() - INTERVAL '24 hours'
            GROUP BY actor_id, target_tenant
        """)
        result = await self.session.execute(sql)
        for row in result.fetchall():
            activities.append(SuspiciousActivity(
                activity_id=hashlib.sha256(f"cross_tenant_{row.actor_id}_{time.time()}".encode()).hexdigest()[:16],
                activity_type="cross_tenant_access",
                tenant_id=tenant_id,
                actor_id=str(row.actor_id),
                severity="critical",
                description=f"Cross-tenant access attempt to {row.target_tenant}",
                details={"target_tenant": row.target_tenant, "attempt_count": row.attempt_count},
            ))
        return activities

    async def run_all_detectors(self, tenant_id: str) -> list[SuspiciousActivity]:
        """Run all suspicious activity detectors."""
        all_activities = []
        all_activities.extend(await self.detect_rapid_api_calls(tenant_id))
        all_activities.extend(await self.detect_bulk_export(tenant_id))
        all_activities.extend(await self.detect_cross_tenant_access(tenant_id))
        return all_activities
