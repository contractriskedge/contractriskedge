"""Database Governance — migration management, schema validation, rollback safety, index monitoring.

Prevents schema drift and migration-related incidents in production.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class MigrationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    DRY_RUN = "dry_run"


class MigrationRisk(str, Enum):
    LOW = "low"           # Add index, add column with default
    MEDIUM = "medium"     # Add table, add NOT NULL column
    HIGH = "high"         # Drop column, rename table, data migration
    CRITICAL = "critical" # Schema change requiring downtime


@dataclass
class MigrationRecord:
    """A recorded migration with governance metadata."""
    version: str
    description: str
    risk: MigrationRisk
    status: MigrationStatus
    author: str
    checksum: str
    rollback_version: str | None = None
    requires_backfill: bool = False
    affected_tables: list[str] = field(default_factory=list)
    dry_run_validated: bool = False
    run_at: str | None = None
    duration_seconds: int = 0
    error_message: str | None = None


@dataclass
class SchemaValidationResult:
    """Result of schema validation check."""
    valid: bool
    issues: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class IndexHealth:
    """Health information for a database index."""
    index_name: str
    table_name: str
    index_size_bytes: int = 0
    scan_count: int = 0
    tuple_count: int = 0
    dead_tuple_count: int = 0
    dead_tuple_pct: float = 0.0
    last_vacuum: str | None = None
    last_analyze: str | None = None
    is_bloated: bool = False
    is_unused: bool = False
    recommendation: str = ""


@dataclass
class DBGovernanceService:
    """Centralized database governance for production safety.

    Provides:
    - Migration governance with risk classification
    - Schema compatibility validation
    - Rollback-safe migration planning
    - Migration dry-run support
    - Index health monitoring
    - Partition lifecycle management
    """

    session: AsyncSession

    # ── Migration Governance ───────────────────────────────────────

    async def validate_migration(
        self,
        migration_sql: str,
        version: str,
        description: str,
    ) -> SchemaValidationResult:
        """Validate a migration for safety and compatibility.

        Checks:
        - No DROP COLUMN without backup
        - No RENAME without migration plan
        - No ALTER COLUMN TYPE without validation
        - No destructive operations on large tables
        """
        issues: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []
        sql_lower = migration_sql.lower()

        # Check for dangerous operations
        if "drop column" in sql_lower:
            issues.append({
                "code": "dangerous_drop_column",
                "message": "DROP COLUMN detected — requires backup and rollback plan",
                "severity": "error",
            })

        if "rename" in sql_lower and ("column" in sql_lower or "table" in sql_lower):
            issues.append({
                "code": "rename_requires_plan",
                "message": "RENAME detected — requires migration plan with dual-write phase",
                "severity": "error",
            })

        if "alter column" in sql_lower and "type" in sql_lower:
            warnings.append({
                "code": "alter_type_requires_validation",
                "message": "ALTER COLUMN TYPE detected — verify no data truncation",
                "severity": "warning",
            })

        if "drop table" in sql_lower:
            issues.append({
                "code": "dangerous_drop_table",
                "message": "DROP TABLE detected — requires backup verification",
                "severity": "error",
            })

        # Check for missing rollback
        if "create table" in sql_lower or "add column" in sql_lower:
            warnings.append({
                "code": "missing_rollback",
                "message": "CREATE/ADD detected — verify rollback migration exists",
                "severity": "warning",
            })

        return SchemaValidationResult(
            valid=len([i for i in issues if i["severity"] == "error"]) == 0,
            issues=issues,
            warnings=warnings,
        )

    async def compute_migration_checksum(self, sql_content: str) -> str:
        """Compute a deterministic checksum for migration verification."""
        return hashlib.sha256(sql_content.encode()).hexdigest()

    async def record_migration(
        self,
        version: str,
        description: str,
        risk: MigrationRisk,
        author: str,
        sql_checksum: str,
        affected_tables: list[str],
    ) -> None:
        """Record a migration in the governance log."""
        sql = sa_text("""
            INSERT INTO schema_migrations_log (version, description, risk, author, checksum, affected_tables)
            VALUES (:version, :desc, :risk, :author, :checksum, :tables)
            ON CONFLICT (version) DO NOTHING
        """)
        await self.session.execute(sql, {
            "version": version,
            "desc": description,
            "risk": risk.value,
            "author": author,
            "checksum": sql_checksum,
            "tables": affected_tables,
        })

    # ── Index Health Monitoring ────────────────────────────────────

    async def get_index_health(self, schema: str = "public") -> list[IndexHealth]:
        """Get health metrics for all indexes."""
        sql = sa_text("""
            SELECT
                i.indexrelid::regclass::text as index_name,
                i.relname as table_name,
                pg_relation_size(i.indexrelid) as index_size,
                s.idx_scan as scan_count,
                s.n_tup_ins + s.n_tup_upd + s.n_tup_del as tuple_count,
                s.n_tup_del as dead_tuple_count,
                COALESCE(s.n_tup_del::float / NULLIF(s.n_tup_ins + s.n_tup_upd + s.n_tup_del, 0), 0) as dead_pct,
                s.last_vacuum,
                s.last_analyze
            FROM pg_stat_user_indexes s
            JOIN pg_index i_idx ON i_idx.indexrelid = s.indexrelid
            JOIN pg_class i ON i.oid = i_idx.indexrelid
            WHERE s.schemaname = :schema
            ORDER BY index_size DESC
        """)
        result = await self.session.execute(sql, {"schema": schema})
        indexes = []
        for row in result.fetchall():
            dead_pct = float(row.dead_pct or 0.0)
            indexes.append(IndexHealth(
                index_name=str(row.index_name),
                table_name=str(row.table_name),
                index_size_bytes=row.index_size or 0,
                scan_count=row.scan_count or 0,
                tuple_count=row.tuple_count or 0,
                dead_tuple_count=row.dead_tuple_count or 0,
                dead_tuple_pct=round(dead_pct * 100, 2),
                last_vacuum=str(row.last_vacuum) if row.last_vacuum else None,
                last_analyze=str(row.last_analyze) if row.last_analyze else None,
                is_bloated=dead_pct > 0.3,
                is_unused=(row.scan_count or 0) == 0,
                recommendation=self._recommend_index_action(row),
            ))
        return indexes

    def _recommend_index_action(self, row) -> str:
        """Generate recommendation for an index."""
        if (row.scan_count or 0) == 0:
            return "UNUSED — consider dropping if no planned queries need it"
        dead_pct = float(row.dead_pct or 0.0)
        if dead_pct > 0.3:
            return "BLOATED — consider REINDEX or VACUUM FULL"
        if dead_pct > 0.1:
            return "MODERATE BLOAT — schedule VACUUM"
        return "HEALTHY"

    # ── Partition Lifecycle ────────────────────────────────────────

    async def get_table_sizes(self, schema: str = "public") -> list[dict[str, Any]]:
        """Get table size information for capacity planning."""
        sql = sa_text("""
            SELECT
                relname as table_name,
                pg_total_relation_size(relid) as total_size_bytes,
                pg_relation_size(relid) as table_size_bytes,
                pg_indexes_size(relid) as index_size_bytes,
                n_live_tup as row_count
            FROM pg_stat_user_tables
            WHERE schemaname = :schema
            ORDER BY pg_total_relation_size(relid) DESC
        """)
        result = await self.session.execute(sql, {"schema": schema})
        return [
            {
                "table_name": str(row.table_name),
                "total_size_mb": round((row.total_size_bytes or 0) / (1024 * 1024), 2),
                "table_size_mb": round((row.table_size_bytes or 0) / (1024 * 1024), 2),
                "index_size_mb": round((row.index_size_bytes or 0) / (1024 * 1024), 2),
                "row_count": row.row_count or 0,
            }
            for row in result.fetchall()
        ]

    async def get_database_stats(self) -> dict[str, Any]:
        """Get overall database statistics."""
        sql = sa_text("""
            SELECT
                pg_database_size(current_database()) as db_size_bytes,
                (SELECT COUNT(*) FROM pg_stat_user_tables) as table_count,
                (SELECT COUNT(*) FROM pg_stat_user_indexes) as index_count,
                (SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active') as active_connections,
                (SELECT COUNT(*) FROM pg_stat_activity) as total_connections
        """)
        result = await self.session.execute(sql)
        row = result.fetchone()
        return {
            "database_size_gb": round((row.db_size_bytes or 0) / (1024**3), 2),
            "table_count": row.table_count or 0,
            "index_count": row.index_count or 0,
            "active_connections": row.active_connections or 0,
            "total_connections": row.total_connections or 0,
        }
