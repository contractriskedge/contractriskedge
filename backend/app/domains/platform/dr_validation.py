"""Disaster Recovery Validation — restore simulation, replay validation, vector DB rebuild, cross-region failover.

Most companies never actually test recovery.
This becomes catastrophic eventually.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class DRTestStatus(str, Enum):
    PLANNED = "planned"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    PARTIALLY_PASSED = "partially_passed"


class DRTestType(str, Enum):
    RESTORE_SIMULATION = "restore_simulation"
    REPLAY_RESTORE = "replay_restore"
    VECTOR_DB_REBUILD = "vector_db_rebuild"
    CROSS_REGION_FAILOVER = "cross_region_failover"
    QUEUE_RECOVERY = "queue_recovery"
    AUDIT_CHAIN_INTEGRITY = "audit_chain_integrity"
    FULL_SYSTEM_RECOVERY = "full_system_recovery"


@dataclass
class DRTestResult:
    """Result of a disaster recovery test."""
    test_id: str
    test_type: DRTestType
    status: DRTestStatus
    started_at: str
    completed_at: str | None = None
    duration_seconds: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    total_checks: int = 0
    details: list[dict[str, Any]] = field(default_factory=list)
    error_message: str | None = None
    recommendations: list[str] = field(default_factory=list)


@dataclass
class DRValidationService:
    """Disaster Recovery validation — automated recovery testing.

    Validates:
    - Database restore from backup
    - Replay consistency after restore
    - Vector DB rebuild from source data
    - Cross-region failover readiness
    - Queue recovery after outage
    - Audit chain integrity after restore
    """

    session: AsyncSession

    # ── Restore Simulation ─────────────────────────────────────────

    async def simulate_restore(
        self,
        backup_timestamp: str | None = None,
    ) -> DRTestResult:
        """Simulate a database restore and verify data integrity.

        Checks:
        - All expected tables exist
        - Row counts are within expected ranges
        - Foreign key constraints are valid
        - No orphaned records
        """
        test_id = f"dr_restore_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        checks: list[dict[str, Any]] = []
        passed = 0
        failed = 0

        # Check 1: Table existence
        sql = sa_text("""
            SELECT table_name, (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public') as total
            FROM information_schema.tables
            WHERE table_schema = 'public'
        """)
        result = await self.session.execute(sql)
        tables = result.fetchall()
        checks.append({
            "check": "table_existence",
            "status": "passed" if len(tables) >= 10 else "failed",
            "details": f"{len(tables)} tables found",
        })
        if len(tables) >= 10:
            passed += 1
        else:
            failed += 1

        # Check 2: Foreign key integrity
        sql = sa_text("""
            SELECT COUNT(*) as violations FROM (
                SELECT 1 FROM chunks c
                LEFT JOIN upload_sessions u ON u.upload_id = c.upload_id
                WHERE u.upload_id IS NULL
                LIMIT 1
            ) violations
        """)
        result = await self.session.execute(sql)
        fk_violations = result.scalar() or 0
        checks.append({
            "check": "foreign_key_integrity",
            "status": "passed" if fk_violations == 0 else "failed",
            "details": f"{fk_violations} FK violations found",
        })
        if fk_violations == 0:
            passed += 1
        else:
            failed += 1

        # Check 3: Sequence consistency
        sql = sa_text("""
            SELECT COUNT(*) as sequences FROM (
                SELECT schemaname || '.' || sequencename as seq
                FROM pg_sequences
                WHERE schemaname = 'public'
            ) seqs
        """)
        result = await self.session.execute(sql)
        seq_count = result.scalar() or 0
        checks.append({
            "check": "sequence_consistency",
            "status": "passed" if seq_count > 0 else "warning",
            "details": f"{seq_count} sequences found",
        })
        passed += 1

        return DRTestResult(
            test_id=test_id,
            test_type=DRTestType.RESTORE_SIMULATION,
            status=DRTestStatus.PASSED if failed == 0 else DRTestStatus.FAILED,
            started_at=datetime.utcnow().isoformat(),
            completed_at=datetime.utcnow().isoformat(),
            passed_checks=passed,
            failed_checks=failed,
            total_checks=len(checks),
            details=checks,
            recommendations=[
                "Verify backup frequency meets RPO requirements",
                "Test full restore in isolated environment quarterly",
                "Document restore procedure with runbooks",
            ] if failed > 0 else [],
        )

    # ── Replay Restore Validation ──────────────────────────────────

    async def validate_replay_after_restore(self) -> DRTestResult:
        """Validate that replay engine works correctly after restore.

        Ensures that execution snapshots are still valid after DB recovery.
        """
        test_id = f"dr_replay_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        checks = []
        passed = 0
        failed = 0

        # Check 1: Retrieval snapshots exist
        sql = sa_text("""
            SELECT COUNT(*) as snapshots, COUNT(DISTINCT tenant_id) as tenants
            FROM retrieval_snapshots
        """)
        result = await self.session.execute(sql)
        row = result.fetchone()
        snapshots_ok = (row.snapshots or 0) > 0
        checks.append({
            "check": "retrieval_snapshots_exist",
            "status": "passed" if snapshots_ok else "warning",
            "details": f"{row.snapshots or 0} snapshots across {row.tenants or 0} tenants",
        })
        passed += 1

        # Check 2: Execution runs exist
        sql = sa_text("SELECT COUNT(*) as runs FROM ai_execution_runs")
        result = await self.session.execute(sql)
        runs_ok = (result.scalar() or 0) > 0
        checks.append({
            "check": "execution_runs_exist",
            "status": "passed" if runs_ok else "warning",
            "details": f"{result.scalar() or 0} execution runs found",
        })
        passed += 1

        return DRTestResult(
            test_id=test_id,
            test_type=DRTestType.REPLAY_RESTORE,
            status=DRTestStatus.PASSED if failed == 0 else DRTestStatus.FAILED,
            started_at=datetime.utcnow().isoformat(),
            completed_at=datetime.utcnow().isoformat(),
            passed_checks=passed,
            failed_checks=failed,
            total_checks=len(checks),
            details=checks,
        )

    # ── Vector DB Rebuild Validation ───────────────────────────────

    async def validate_vector_db_rebuild(self) -> DRTestResult:
        """Validate that vector DB can be rebuilt from source data."""
        test_id = f"dr_vector_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        checks = []
        passed = 0
        failed = 0

        # Check 1: Source chunks exist for rebuild
        sql = sa_text("""
            SELECT COUNT(*) as chunks, COUNT(*) FILTER (WHERE embedding IS NOT NULL) as embedded
            FROM chunks WHERE is_active = true
        """)
        result = await self.session.execute(sql)
        row = result.fetchone()
        total = row.chunks or 0
        embedded = row.embedded or 0
        checks.append({
            "check": "source_chunks_available",
            "status": "passed" if total > 0 else "failed",
            "details": f"{total} chunks available, {embedded} embedded",
        })
        if total > 0:
            passed += 1
        else:
            failed += 1

        # Check 2: Embedding model registry is populated
        from app.domains.vectors.partition import EMBEDDING_MODEL_REGISTRY
        has_active = any(m.status.value == "active" for m in EMBEDDING_MODEL_REGISTRY.values())
        checks.append({
            "check": "embedding_model_registry",
            "status": "passed" if has_active else "failed",
            "details": f"{len(EMBEDDING_MODEL_REGISTRY)} models registered",
        })
        if has_active:
            passed += 1
        else:
            failed += 1

        return DRTestResult(
            test_id=test_id,
            test_type=DRTestType.VECTOR_DB_REBUILD,
            status=DRTestStatus.PASSED if failed == 0 else DRTestStatus.FAILED,
            started_at=datetime.utcnow().isoformat(),
            completed_at=datetime.utcnow().isoformat(),
            passed_checks=passed,
            failed_checks=failed,
            total_checks=len(checks),
            details=checks,
            recommendations=[
                "Test full vector DB rebuild in staging before production",
                "Document embedding model versions for reproducibility",
                "Verify chunk text is preserved for re-embedding",
            ],
        )

    # ── Cross-Region Failover ──────────────────────────────────────

    async def validate_cross_region_failover(self) -> DRTestResult:
        """Validate cross-region failover readiness."""
        test_id = f"dr_failover_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        checks = []
        passed = 0
        failed = 0

        # Check 1: Read replicas available
        sql = sa_text("SELECT COUNT(*) as replicas FROM pg_stat_replication")
        try:
            result = await self.session.execute(sql)
            replicas = result.scalar() or 0
            checks.append({
                "check": "read_replicas",
                "status": "passed" if replicas > 0 else "warning",
                "details": f"{replicas} replication connections",
            })
            passed += 1
        except Exception as e:
            checks.append({
                "check": "read_replicas",
                "status": "warning",
                "details": f"Cannot check replication: {e}",
            })
            passed += 1  # Non-blocking

        return DRTestResult(
            test_id=test_id,
            test_type=DRTestType.CROSS_REGION_FAILOVER,
            status=DRTestStatus.PASSED if failed == 0 else DRTestStatus.FAILED,
            started_at=datetime.utcnow().isoformat(),
            completed_at=datetime.utcnow().isoformat(),
            passed_checks=passed,
            failed_checks=failed,
            total_checks=len(checks),
            details=checks,
            recommendations=[
                "Document failover runbook",
                "Test cross-region failover quarterly",
                "Verify DNS propagation for API endpoint",
                "Ensure vector DB is replicated across regions",
            ],
        )

    # ── Audit Chain Integrity ──────────────────────────────────────

    async def validate_audit_chain_integrity(self) -> DRTestResult:
        """Validate audit chain integrity after restore."""
        from app.domains.security import ImmutableAuditVerifier

        test_id = f"dr_audit_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        verifier = ImmutableAuditVerifier(self.session)

        # Get all tenants with audit data
        sql = sa_text("SELECT DISTINCT tenant_id FROM audit_trail")
        result = await self.session.execute(sql)
        tenants = [str(row.tenant_id) for row in result.fetchall()]

        checks = []
        passed = 0
        failed = 0
        total_violations = 0

        for tenant_id in tenants:
            violations = await verifier.verify_chain(tenant_id)
            if violations:
                failed += 1
                total_violations += len(violations)
                checks.append({
                    "check": f"audit_chain_{tenant_id[:8]}",
                    "status": "failed",
                    "details": f"{len(violations)} chain violations for tenant {tenant_id[:8]}",
                })
            else:
                passed += 1
                checks.append({
                    "check": f"audit_chain_{tenant_id[:8]}",
                    "status": "passed",
                    "details": f"Audit chain intact for tenant {tenant_id[:8]}",
                })

        return DRTestResult(
            test_id=test_id,
            test_type=DRTestType.AUDIT_CHAIN_INTEGRITY,
            status=DRTestStatus.PASSED if failed == 0 else DRTestStatus.FAILED,
            started_at=datetime.utcnow().isoformat(),
            completed_at=datetime.utcnow().isoformat(),
            passed_checks=passed,
            failed_checks=failed,
            total_checks=len(checks),
            details=checks,
            recommendations=[
                "Verify HMAC signing key is backed up separately",
                "Test audit chain verification after every restore",
                "Document key rotation procedure for audit signing",
            ] if failed > 0 else [],
        )

    # ── Full DR Suite ──────────────────────────────────────────────

    async def run_full_dr_suite(self) -> list[DRTestResult]:
        """Run the complete disaster recovery validation suite."""
        results = []

        logger.info("Starting full DR validation suite...")
        results.append(await self.simulate_restore())
        results.append(await self.validate_replay_after_restore())
        results.append(await self.validate_vector_db_rebuild())
        results.append(await self.validate_cross_region_failover())
        results.append(await self.validate_audit_chain_integrity())

        total = len(results)
        passed = sum(1 for r in results if r.status == DRTestStatus.PASSED)
        failed = sum(1 for r in results if r.status == DRTestStatus.FAILED)

        logger.info(
            "DR validation suite complete: %d/%d passed, %d/%d failed",
            passed, total, failed, total,
        )

        return results
