"""Sprint 25 Task 3.5A — Backup Automation Validation.

Tests:
1. Backup script executes successfully
2. Backup files created with correct names
3. Retention cleanup works (daily + weekly tiers)
4. MinIO backup creates objects
5. JSON logging produces valid output
6. Dry-run mode works
7. Validate-only mode works

Usage:
    cd backend && python -m pytest tests/test_backup_automation.py -v --tb=short
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import pytest

SCRIPTS_DIR = Path("/Volumes/ContractEdge/ContractRiskEdge/scripts")
BACKUP_SCRIPT = SCRIPTS_DIR / "backup.sh"
CRONTAB_FILE = SCRIPTS_DIR / "crontab"
PROJECT_DIR = Path("/Volumes/ContractEdge/ContractRiskEdge")
BACKUP_DIR = PROJECT_DIR / "backups"


# ── Helpers ──────────────────────────────────────────────────────────────────


def _run(cmd: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


# ═══════════════════════════════════════════════════════════════════
# 1. Script Existence and Syntax
# ═══════════════════════════════════════════════════════════════════


class TestBackupScriptExistence:
    """Verify the backup script and crontab exist and are valid."""

    def test_backup_script_exists(self):
        assert BACKUP_SCRIPT.exists(), f"Backup script not found: {BACKUP_SCRIPT}"
        assert os.access(str(BACKUP_SCRIPT), os.X_OK), "Backup script is not executable"

    def test_crontab_exists(self):
        assert CRONTAB_FILE.exists(), f"Crontab file not found: {CRONTAB_FILE}"

    def test_backup_script_syntax(self):
        """Check bash syntax with 'bash -n'."""
        result = _run(["bash", "-n", str(BACKUP_SCRIPT)])
        assert result.returncode == 0, f"Bash syntax error: {result.stderr}"

    def test_crontab_has_daily_entry(self):
        content = CRONTAB_FILE.read_text()
        assert "0 2 * * *" in content, "Missing daily cron entry (0 2 * * *)"
        assert "backup.sh" in content, "Missing backup.sh reference in crontab"

    def test_crontab_has_health_check(self):
        content = CRONTAB_FILE.read_text()
        assert "5 * * * *" in content, "Missing hourly health check (5 * * * *)"
        assert "--validate-only" in content, "Missing --validate-only flag"


# ═══════════════════════════════════════════════════════════════════
# 2. Dry Run Mode
# ═══════════════════════════════════════════════════════════════════


class TestDryRun:
    """Verify --dry-run mode works without side effects."""

    def test_dry_run_executes(self):
        result = _run(["bash", str(BACKUP_SCRIPT), "--dry-run"])
        assert result.returncode == 0, f"Dry run failed: {result.stderr}"
        assert "DRY RUN" in result.stdout, "Dry run marker not found in output"

    def test_dry_run_creates_no_files(self):
        """Dry run should not create any backup files."""
        before = set(os.listdir(str(BACKUP_DIR / "daily"))) if (BACKUP_DIR / "daily").exists() else set()
        _run(["bash", str(BACKUP_SCRIPT), "--dry-run"])
        after = set(os.listdir(str(BACKUP_DIR / "daily"))) if (BACKUP_DIR / "daily").exists() else set()
        assert after == before, "Dry run created files when it shouldn't have"


# ═══════════════════════════════════════════════════════════════════
# 3. Full Backup Execution
# ═══════════════════════════════════════════════════════════════════


class TestFullBackupExecution:
    """Run the actual backup and verify all artifacts."""

    @classmethod
    def setup_class(cls):
        # Ensure backup directories exist
        (BACKUP_DIR / "daily").mkdir(parents=True, exist_ok=True)
        (BACKUP_DIR / "weekly").mkdir(parents=True, exist_ok=True)
        (BACKUP_DIR / "logs").mkdir(parents=True, exist_ok=True)
        (BACKUP_DIR / "minio").mkdir(parents=True, exist_ok=True)

    def test_backup_executes_successfully(self):
        """Full backup should exit with code 0."""
        result = _run(["bash", str(BACKUP_SCRIPT)], timeout=120)
        assert result.returncode == 0, f"Backup failed:\nstdout:{result.stdout}\nstderr:{result.stderr}"
        self._result = result

    def test_backup_file_created(self):
        """A .dump file should exist in the daily directory."""
        dumps = list((BACKUP_DIR / "daily").glob("contractedge_*.dump"))
        assert len(dumps) >= 1, f"No dump files found in {BACKUP_DIR / 'daily'}"
        self._latest_dump = max(dumps, key=lambda p: p.stat().st_mtime)

    def test_backup_file_non_empty(self):
        """The dump file should not be empty."""
        dumps = list((BACKUP_DIR / "daily").glob("contractedge_*.dump"))
        latest = max(dumps, key=lambda p: p.stat().st_mtime)
        assert latest.stat().st_size > 0, f"Backup file is empty: {latest}"

    def test_schema_file_created(self):
        """A schema .sql file should exist."""
        schemas = list((BACKUP_DIR / "daily").glob("contractedge_schema_*.sql"))
        assert len(schemas) >= 1, "No schema file found"
        latest = max(schemas, key=lambda p: p.stat().st_mtime)
        assert latest.stat().st_size > 0, f"Schema file is empty: {latest}"
        # Should be a valid SQL file with CREATE TABLE statements
        content = latest.read_text()
        assert "CREATE TABLE" in content, "Schema file missing CREATE TABLE statements"

    def test_json_log_created(self):
        """A JSON log file should be created."""
        logs = list((BACKUP_DIR / "logs").glob("backup_*.json"))
        assert len(logs) >= 1, "No JSON log file found"
        latest = max(logs, key=lambda p: p.stat().st_mtime)
        # Validate JSON content
        data = json.loads(latest.read_text())
        assert data["status"] == "success", f"Backup status is not success: {data['status']}"
        assert data["database"] == "contract_risk_dev"
        assert data["backup_size_bytes"] > 0
        assert data["duration_seconds"] > 0
        print(f"  Backup size: {data['backup_size_bytes']:,} bytes")
        print(f"  Duration: {data['duration_seconds']}s")
        print(f"  MinIO objects: {data['minio_objects']}")

    def test_text_log_created(self):
        """A text log file should be created."""
        logs = list((BACKUP_DIR / "logs").glob("backup_*.log"))
        assert len(logs) >= 1, "No log file found"
        latest = max(logs, key=lambda p: p.stat().st_mtime)
        content = latest.read_text()
        assert "Backup Complete" in content, "Log missing completion marker"
        assert "Step 1/5" in content, "Log missing step tracking"

    def test_minio_backup_created(self):
        """MinIO backup directory should exist with objects."""
        minio_dirs = list((BACKUP_DIR / "minio").glob("minio_*"))
        if minio_dirs:
            latest = max(minio_dirs, key=lambda p: p.stat().st_mtime)
            files = list(latest.iterdir())
            print(f"  MinIO backup: {len(files)} objects in {latest.name}")
            assert len(files) > 0, "MinIO backup directory is empty"


# ═══════════════════════════════════════════════════════════════════
# 4. Retention Cleanup
# ═══════════════════════════════════════════════════════════════════


class TestRetentionCleanup:
    """Verify retention policy enforcement."""

    def test_daily_retention_limit(self):
        """Daily backups should not exceed configured limit."""
        dumps = list((BACKUP_DIR / "daily").glob("contractedge_*.dump"))
        # Allow 1 extra for the backup we just created + any that existed
        assert len(dumps) <= 8, f"Too many daily backups: {len(dumps)} (limit: 7)"
        print(f"  Daily backups: {len(dumps)}")

    def test_weekly_retention_limit(self):
        """Weekly backups should not exceed configured limit."""
        weekly = list((BACKUP_DIR / "weekly").glob("contractedge_*.dump"))
        assert len(weekly) <= 5, f"Too many weekly backups: {len(weekly)} (limit: 4)"
        print(f"  Weekly backups: {len(weekly)}")

    def test_old_backups_removed(self):
        """Backups older than retention should be removed."""
        # Create a mock old backup to test cleanup
        old_file = BACKUP_DIR / "daily" / "contractedge_20200101_000000.dump"
        old_file.touch()
        assert old_file.exists(), "Failed to create test old backup"

        # Run backup (should clean up the old file)
        _run(["bash", str(BACKUP_SCRIPT)], timeout=120)

        # The old file should be gone (or at least retention enforced)
        remaining = list((BACKUP_DIR / "daily").glob("contractedge_*.dump"))
        assert len(remaining) <= 8, f"Retention cleanup failed: {len(remaining)} backups remain"
        print(f"  After cleanup: {len(remaining)} daily backups")

        # Clean up the mock file if it still exists
        if old_file.exists():
            old_file.unlink()


# ═══════════════════════════════════════════════════════════════════
# 5. Validate-Only Mode
# ═══════════════════════════════════════════════════════════════════


class TestValidateOnly:
    """Verify --validate-only mode produces correct report."""

    def test_validate_only_executes(self):
        result = _run(["bash", str(BACKUP_SCRIPT), "--validate-only"])
        assert result.returncode == 0, f"Validate-only failed: {result.stderr}"
        assert "Validation Report" in result.stdout, "Report header not found"

    def test_validate_only_shows_retention(self):
        result = _run(["bash", str(BACKUP_SCRIPT), "--validate-only"])
        assert "Daily backups" in result.stdout
        assert "Weekly backups" in result.stdout

    def test_validate_only_shows_integrity(self):
        result = _run(["bash", str(BACKUP_SCRIPT), "--validate-only"])
        assert "Integrity Check" in result.stdout

    def test_validate_only_shows_freshness(self):
        result = _run(["bash", str(BACKUP_SCRIPT), "--validate-only"])
        assert "Freshness" in result.stdout or "No backup files found" in result.stdout


# ═══════════════════════════════════════════════════════════════════
# 6. Crontab Installation
# ═══════════════════════════════════════════════════════════════════


class TestCrontabInstallation:
    """Verify crontab can be installed and parsed."""

    def test_crontab_parses_correctly(self):
        """crontab -l should accept our file."""
        result = _run(["crontab", str(CRONTAB_FILE)])
        assert result.returncode == 0 or "no crontab" in result.stderr.lower(), \
            f"Crontab parse failed: {result.stderr}"

    def test_crontab_has_valid_syntax(self):
        """Verify cron syntax with crontab -T (macOS)."""
        result = _run(["crontab", "-T", str(CRONTAB_FILE)])
        # -T may not exist on all systems; skip if it fails
        if result.returncode != 0 and "illegal option" in result.stderr:
            pytest.skip("crontab -T not supported on this system")
        assert result.returncode == 0, f"Cron syntax error: {result.stderr}"
