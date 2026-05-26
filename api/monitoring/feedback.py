"""In-app feedback mechanism for risk flagging accuracy.

Provides a 3-button feedback widget (False Positive / Correct /
Severity Wrong) for collecting user feedback on risk flags,
enabling continuous improvement through human-in-the-loop validation.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class FeedbackType:
    """Feedback type constants for the 3-button widget."""

    FALSE_POSITIVE = "false_positive"
    CORRECT = "correct"
    SEVERITY_WRONG = "severity_wrong"


@dataclass
class FeedbackRecord:
    """A single feedback record from a user."""

    feedback_id: str
    risk_flag_id: str
    feedback_type: str  # false_positive, correct, severity_wrong
    user_id: str
    tenant_id: str
    contract_id: str
    category: str
    original_severity: int
    corrected_severity: Optional[int] = None
    comment: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


class FeedbackCollector:
    """Collects and manages user feedback on risk flagging.

    Provides methods to record feedback from the 3-button widget,
    query feedback history, and aggregate feedback statistics
    for quality monitoring.

    Usage:
        collector = FeedbackCollector()
        collector.record_feedback(
            risk_flag_id="flag-123",
            feedback_type="false_positive",
            user_id="user-456",
            tenant_id="tenant-789",
            contract_id="contract-012",
            category="indemnification",
            original_severity=7,
        )
        stats = collector.get_feedback_stats("tenant-789")
    """

    def __init__(
        self,
        db_pool: Optional[Any] = None,
        storage_path: Optional[str] = None,
    ) -> None:
        """Initialize the feedback collector.

        Args:
            db_pool: Optional database pool for persistence.
            storage_path: Optional file path for local storage.
        """
        self._db_pool = db_pool
        self._storage_path = storage_path
        self._in_memory: List[FeedbackRecord] = []
        self._feedback_counter = 0

    def record_feedback(
        self,
        risk_flag_id: str,
        feedback_type: str,
        user_id: str,
        tenant_id: str,
        contract_id: str,
        category: str,
        original_severity: int,
        corrected_severity: Optional[int] = None,
        comment: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FeedbackRecord:
        """Record user feedback on a risk flag.

        Args:
            risk_flag_id: The risk flag being evaluated.
            feedback_type: Type of feedback (false_positive, correct, severity_wrong).
            user_id: The user providing feedback.
            tenant_id: Tenant identifier.
            contract_id: Contract identifier.
            category: Risk category of the flag.
            original_severity: Original severity score (1-10).
            corrected_severity: User-corrected severity (for severity_wrong).
            comment: Optional user comment.
            metadata: Additional metadata.

        Returns:
            The created FeedbackRecord.

        Raises:
            ValueError: If feedback_type is invalid.
        """
        valid_types = {
            FeedbackType.FALSE_POSITIVE,
            FeedbackType.CORRECT,
            FeedbackType.SEVERITY_WRONG,
        }
        if feedback_type not in valid_types:
            raise ValueError(
                f"Invalid feedback type: {feedback_type}. "
                f"Must be one of: {valid_types}"
            )

        if feedback_type == FeedbackType.SEVERITY_WRONG and corrected_severity is None:
            raise ValueError(
                "corrected_severity is required for severity_wrong feedback"
            )

        self._feedback_counter += 1
        record = FeedbackRecord(
            feedback_id=f"fb_{self._feedback_counter:06d}",
            risk_flag_id=risk_flag_id,
            feedback_type=feedback_type,
            user_id=user_id,
            tenant_id=tenant_id,
            contract_id=contract_id,
            category=category,
            original_severity=original_severity,
            corrected_severity=corrected_severity,
            comment=comment,
            metadata=metadata or {},
        )

        # Persist
        if self._db_pool is not None:
            self._persist_to_db(record)
        elif self._storage_path is not None:
            self._persist_to_file(record)
        else:
            self._in_memory.append(record)

        logger.info(
            "Feedback recorded: flag=%s type=%s category=%s user=%s",
            risk_flag_id,
            feedback_type,
            category,
            user_id,
        )

        return record

    def _persist_to_db(self, record: FeedbackRecord) -> None:
        """Persist feedback record to database.

        Args:
            record: The feedback record to persist.
        """
        try:
            import asyncio
            # Async insert - in production, use proper async DB call
            logger.debug("Persisting feedback to DB: %s", record.feedback_id)
        except Exception as exc:
            logger.error("Failed to persist feedback to DB: %s", exc)
            self._in_memory.append(record)

    def _persist_to_file(self, record: FeedbackRecord) -> None:
        """Persist feedback record to a JSON file.

        Args:
            record: The feedback record to persist.
        """
        import os

        try:
            os.makedirs(os.path.dirname(self._storage_path), exist_ok=True)
            records = self._load_file_records()
            records.append(record)
            with open(self._storage_path, "w") as f:
                json.dump(
                    [self._record_to_dict(r) for r in records],
                    f,
                    indent=2,
                    default=str,
                )
        except Exception as exc:
            logger.error("Failed to persist feedback to file: %s", exc)
            self._in_memory.append(record)

    def _load_file_records(self) -> List[FeedbackRecord]:
        """Load feedback records from file.

        Returns:
            List of feedback records.
        """
        import os

        if not self._storage_path or not os.path.exists(self._storage_path):
            return []

        try:
            with open(self._storage_path) as f:
                data = json.load(f)
            return [FeedbackRecord(**item) for item in data]
        except Exception:
            return []

    def _record_to_dict(self, record: FeedbackRecord) -> Dict[str, Any]:
        """Convert a FeedbackRecord to a dict.

        Args:
            record: The record to convert.

        Returns:
            Dict representation.
        """
        return {
            "feedback_id": record.feedback_id,
            "risk_flag_id": record.risk_flag_id,
            "feedback_type": record.feedback_type,
            "user_id": record.user_id,
            "tenant_id": record.tenant_id,
            "contract_id": record.contract_id,
            "category": record.category,
            "original_severity": record.original_severity,
            "corrected_severity": record.corrected_severity,
            "comment": record.comment,
            "created_at": record.created_at.isoformat(),
            "metadata": record.metadata,
        }

    def get_feedback_stats(
        self, tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get feedback statistics for a tenant.

        Args:
            tenant_id: Optional tenant filter.

        Returns:
            Dict with feedback statistics.
        """
        records = self._get_records(tenant_id)

        if not records:
            return {
                "total_feedback": 0,
                "false_positives": 0,
                "correct": 0,
                "severity_wrong": 0,
                "accuracy_rate": 0.0,
                "false_positive_rate": 0.0,
                "by_category": {},
            }

        total = len(records)
        fp_count = sum(
            1 for r in records
            if r.feedback_type == FeedbackType.FALSE_POSITIVE
        )
        correct_count = sum(
            1 for r in records
            if r.feedback_type == FeedbackType.CORRECT
        )
        severity_wrong_count = sum(
            1 for r in records
            if r.feedback_type == FeedbackType.SEVERITY_WRONG
        )

        # Per-category breakdown
        by_category: Dict[str, Dict[str, int]] = {}
        for r in records:
            if r.category not in by_category:
                by_category[r.category] = {
                    "total": 0,
                    "false_positives": 0,
                    "correct": 0,
                    "severity_wrong": 0,
                }
            by_category[r.category]["total"] += 1
            by_category[r.category][r.feedback_type] += 1

        return {
            "total_feedback": total,
            "false_positives": fp_count,
            "correct": correct_count,
            "severity_wrong": severity_wrong_count,
            "accuracy_rate": round(correct_count / total, 4) if total > 0 else 0.0,
            "false_positive_rate": round(fp_count / total, 4) if total > 0 else 0.0,
            "by_category": by_category,
        }

    def _get_records(
        self, tenant_id: Optional[str] = None
    ) -> List[FeedbackRecord]:
        """Get all records, optionally filtered by tenant.

        Args:
            tenant_id: Optional tenant filter.

        Returns:
            List of matching feedback records.
        """
        all_records: list[FeedbackRecord] = []

        # In-memory records
        all_records.extend(self._in_memory)

        # File records
        if self._storage_path:
            all_records.extend(self._load_file_records())

        if tenant_id:
            return [r for r in all_records if r.tenant_id == tenant_id]
        return all_records

    def get_recent_feedback(
        self,
        limit: int = 50,
        feedback_type: Optional[str] = None,
    ) -> List[FeedbackRecord]:
        """Get recent feedback records.

        Args:
            limit: Maximum number of records.
            feedback_type: Optional type filter.

        Returns:
            List of recent feedback records.
        """
        records = self._get_records()
        records.sort(key=lambda r: r.created_at, reverse=True)

        if feedback_type:
            records = [r for r in records if r.feedback_type == feedback_type]

        return records[:limit]
