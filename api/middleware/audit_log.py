"""Hash-chained immutable audit log with tamper detection and PostgreSQL persistence.

Provides cryptographically verifiable audit logging using SHA-256
hash chains with dual persistence: PostgreSQL for querying and
file-based hash chain for integrity verification.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class HashChainedAuditLog:
    """Immutable audit log with SHA-256 hash chain integrity and PostgreSQL persistence.

    Each audit entry contains:
    - entry_id: Unique identifier
    - timestamp: ISO 8601 timestamp
    - actor_id: User who performed the action
    - tenant_id: Tenant context
    - action: The action performed
    - resource_type: Type of resource affected
    - resource_id: Identifier of the resource
    - details: JSON payload with action details
    - entry_hash: SHA-256 hash of this entry
    - prev_entry_hash: SHA-256 hash of the previous entry

    Usage:
        audit = HashChainedAuditLog(storage_path="./audit_logs")
        entry = audit.append(
            actor_id="user-123",
            tenant_id="tenant-abc",
            action="contract.upload",
            resource_type="contract",
            resource_id="contract-456",
            details={"filename": "nda.pdf", "size": 245760},
        )
        is_valid = audit.verify_chain()
    """

    def __init__(
        self,
        storage_path: str = "./audit_logs",
        db_repo: Optional[Any] = None,
    ) -> None:
        """Initialize the audit log.

        Args:
            storage_path: Directory to store audit log files.
            db_repo: Optional DatabaseRepository for PostgreSQL persistence.
        """
        self._storage_path = storage_path
        self._db_repo = db_repo
        self._entries: List[Dict[str, Any]] = []
        os.makedirs(storage_path, exist_ok=True)
        self._load_entries()

    def _load_entries(self) -> None:
        """Load existing audit entries from disk."""
        import glob

        pattern = os.path.join(self._storage_path, "audit_*.json")
        for filepath in sorted(glob.glob(pattern)):
            try:
                with open(filepath) as f:
                    entry = json.load(f)
                self._entries.append(entry)
            except Exception as exc:
                logger.warning("Failed to load audit entry %s: %s", filepath, exc)

    def _compute_hash(self, entry: Dict[str, Any]) -> str:
        """Compute SHA-256 hash of an audit entry.

        Args:
            entry: The audit entry dict.

        Returns:
            Hex digest of the SHA-256 hash.
        """
        # Create a deterministic serialization
        serialized = json.dumps(
            {k: v for k, v in entry.items() if k not in ("entry_hash",)},
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def append(
        self,
        actor_id: str,
        tenant_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Append a new entry to the audit log.

        Args:
            actor_id: User who performed the action.
            tenant_id: Tenant context.
            action: The action performed.
            resource_type: Type of resource.
            resource_id: Identifier of the resource.
            details: Optional JSON-serializable details.
            ip_address: Optional IP address of the actor.

        Returns:
            The created audit entry.
        """
        import uuid

        prev_hash = self._entries[-1]["entry_hash"] if self._entries else "0" * 64

        entry = {
            "entry_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "actor_id": actor_id,
            "tenant_id": tenant_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details or {},
            "ip_address": ip_address,
            "prev_entry_hash": prev_hash,
            "entry_hash": "",  # Placeholder
        }

        # Compute hash of this entry (excluding entry_hash field)
        entry["entry_hash"] = self._compute_hash(entry)

        # Store
        self._entries.append(entry)

        # Persist to disk (hash chain)
        filepath = os.path.join(
            self._storage_path,
            f"audit_{entry['entry_id']}.json",
        )
        with open(filepath, "w") as f:
            json.dump(entry, f, indent=2, default=str)

        # Persist to PostgreSQL if available
        if self._db_repo is not None:
            try:
                import asyncio
                asyncio.ensure_future(self._db_repo.append_audit_log(entry))
            except Exception as db_err:
                logger.warning("Failed to persist audit entry to DB: %s", db_err)

        logger.debug(
            "Audit entry %s: %s on %s by %s",
            entry["entry_id"][:8],
            action,
            resource_type,
            actor_id,
        )

        return entry

    def verify_chain(self) -> bool:
        """Verify the integrity of the entire hash chain.

        Returns:
            True if the chain is intact, False if tampering detected.
        """
        for i, entry in enumerate(self._entries):
            # Recompute hash
            expected_hash = self._compute_hash(entry)
            if entry["entry_hash"] != expected_hash:
                logger.error(
                    "TAMPER DETECTED: Entry %s hash mismatch",
                    entry["entry_id"],
                )
                return False

            # Verify chain link
            if i > 0:
                expected_prev = self._entries[i - 1]["entry_hash"]
                if entry["prev_entry_hash"] != expected_prev:
                    logger.error(
                        "TAMPER DETECTED: Chain broken at entry %s "
                        "(prev_hash mismatch)",
                        entry["entry_id"],
                    )
                    return False

        logger.info(
            "Audit chain verified: %d entries, integrity intact",
            len(self._entries),
        )
        return True

    def query(
        self,
        tenant_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Query audit entries with filters.

        Args:
            tenant_id: Filter by tenant.
            actor_id: Filter by actor.
            action: Filter by action type.
            resource_type: Filter by resource type.
            start_time: Filter by start time (ISO 8601).
            end_time: Filter by end time (ISO 8601).
            limit: Max results.
            offset: Pagination offset.

        Returns:
            Filtered list of audit entries.
        """
        results = list(self._entries)

        if tenant_id:
            results = [e for e in results if e.get("tenant_id") == tenant_id]
        if actor_id:
            results = [e for e in results if e.get("actor_id") == actor_id]
        if action:
            results = [e for e in results if e.get("action") == action]
        if resource_type:
            results = [e for e in results if e.get("resource_type") == resource_type]
        if start_time:
            results = [e for e in results if e.get("timestamp", "") >= start_time]
        if end_time:
            results = [e for e in results if e.get("timestamp", "") <= end_time]

        # Reverse chronological order
        results.sort(key=lambda e: e.get("timestamp", ""), reverse=True)

        return results[offset:offset + limit]

    def get_entry(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """Get a single audit entry by ID.

        Args:
            entry_id: The entry identifier.

        Returns:
            The audit entry or None.
        """
        for entry in self._entries:
            if entry["entry_id"] == entry_id:
                return entry
        return None

    def count(self, tenant_id: Optional[str] = None) -> int:
        """Count audit entries.

        Args:
            tenant_id: Optional tenant filter.

        Returns:
            Entry count.
        """
        if tenant_id:
            return len([e for e in self._entries if e.get("tenant_id") == tenant_id])
        return len(self._entries)

    def export_csv(self, entries: List[Dict[str, Any]]) -> str:
        """Export audit entries as CSV string.

        Args:
            entries: List of audit entries to export.

        Returns:
            CSV formatted string.
        """
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "entry_id", "timestamp", "actor_id", "tenant_id",
            "action", "resource_type", "resource_id",
            "details", "ip_address", "entry_hash", "prev_entry_hash",
        ])

        for entry in entries:
            writer.writerow([
                entry.get("entry_id", ""),
                entry.get("timestamp", ""),
                entry.get("actor_id", ""),
                entry.get("tenant_id", ""),
                entry.get("action", ""),
                entry.get("resource_type", ""),
                entry.get("resource_id", ""),
                json.dumps(entry.get("details", {})),
                entry.get("ip_address", ""),
                entry.get("entry_hash", ""),
                entry.get("prev_entry_hash", ""),
            ])

        return output.getvalue()
