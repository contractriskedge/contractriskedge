"""Benchmark governance engine — corpus versioning, approval workflows, deduplication, and lineage.

Provides the operational governance layer for benchmark data integrity:

- ``CorpusGovernanceService``: Version snapshots, approval state machine, dedupe detection
- ``LineageService``: Recompute provenance tracking and delta computation
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.benchmark.models import (
    BenchmarkCorpus,
    BenchmarkClause,
    BenchmarkScore,
    BenchmarkJob,
    BenchmarkCorpusVersion,
    BenchmarkCorpusApproval,
    BenchmarkDedupeReport,
    BenchmarkLineage,
    ApprovalState,
    DedupeSeverity,
    ClauseCategory,
)
from app.domains.vectors.services.embedding_service import EmbeddingService, cosine_similarity

logger = logging.getLogger(__name__)


class CorpusGovernanceService:
    """Governance operations for benchmark corpus integrity.

    Manages version snapshots, approval workflows, and deduplication
    detection to ensure corpus quality and auditability.
    """

    def __init__(self, db: AsyncSession, tenant_id: str):
        self._db = db
        self._tenant_id = tenant_id

    # ── Versioning ─────────────────────────────────────────────────

    async def create_version_snapshot(
        self,
        corpus_id: uuid.UUID,
        change_description: str,
        created_by: str = "system",
        job_id: Optional[uuid.UUID] = None,
    ) -> BenchmarkCorpusVersion:
        """Create an immutable snapshot of a corpus at the current state.

        Captures all clause data as JSON for deterministic recomputation
        and rollback capability.
        """
        # Get current version number
        last_version = await self._db.execute(
            select(func.max(BenchmarkCorpusVersion.version_number)).where(
                BenchmarkCorpusVersion.corpus_id == corpus_id,
            )
        )
        version_number = (last_version.scalar() or 0) + 1

        # Fetch all clauses in the corpus
        clauses = await self._db.execute(
            select(BenchmarkClause).where(
                BenchmarkClause.corpus_id == corpus_id,
                BenchmarkClause.tenant_id == uuid.UUID(self._tenant_id),
            )
        )
        clause_rows = list(clauses.scalars().all())

        # Build snapshot payload
        snapshot_data = [
            {
                "clause_id": str(c.clause_id),
                "category": c.category.value if hasattr(c.category, 'value') else str(c.category),
                "clause_text": c.clause_text,
                "risk_score": c.risk_score,
                "is_favorable": c.is_favorable,
                "source_document": c.source_document,
            }
            for c in clause_rows
        ]

        version = BenchmarkCorpusVersion(
            version_id=uuid.uuid4(),
            corpus_id=corpus_id,
            tenant_id=uuid.UUID(self._tenant_id),
            version_number=version_number,
            version_label=f"v{version_number}",
            snapshot=snapshot_data,
            clause_count=len(clause_rows),
            change_description=change_description,
            created_by=created_by,
            job_id=job_id,
        )
        self._db.add(version)
        await self._db.flush()
        return version

    async def list_versions(
        self,
        corpus_id: uuid.UUID,
        limit: int = 20,
    ) -> list[BenchmarkCorpusVersion]:
        """List all versions for a corpus, newest first."""
        result = await self._db.execute(
            select(BenchmarkCorpusVersion).where(
                BenchmarkCorpusVersion.corpus_id == corpus_id,
                BenchmarkCorpusVersion.tenant_id == uuid.UUID(self._tenant_id),
            ).order_by(BenchmarkCorpusVersion.version_number.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def get_version(self, version_id: uuid.UUID) -> Optional[BenchmarkCorpusVersion]:
        """Get a specific version by ID."""
        result = await self._db.execute(
            select(BenchmarkCorpusVersion).where(
                BenchmarkCorpusVersion.version_id == version_id,
            )
        )
        return result.scalar_one_or_none()

    # ── Approval Workflow ──────────────────────────────────────────

    async def get_approval(self, corpus_id: uuid.UUID) -> Optional[BenchmarkCorpusApproval]:
        """Get the current approval state for a corpus."""
        result = await self._db.execute(
            select(BenchmarkCorpusApproval).where(
                BenchmarkCorpusApproval.corpus_id == corpus_id,
                BenchmarkCorpusApproval.tenant_id == uuid.UUID(self._tenant_id),
            )
        )
        return result.scalar_one_or_none()

    async def ensure_approval_record(self, corpus_id: uuid.UUID) -> BenchmarkCorpusApproval:
        """Get or create an approval record for a corpus."""
        existing = await self.get_approval(corpus_id)
        if existing:
            return existing

        approval = BenchmarkCorpusApproval(
            approval_id=uuid.uuid4(),
            corpus_id=corpus_id,
            tenant_id=uuid.UUID(self._tenant_id),
            state=ApprovalState.DRAFT,
        )
        self._db.add(approval)
        await self._db.flush()
        return approval

    async def submit_for_review(
        self,
        corpus_id: uuid.UUID,
        submitted_by: str,
        notes: Optional[str] = None,
    ) -> BenchmarkCorpusApproval:
        """Submit a corpus for review: DRAFT → PENDING_REVIEW."""
        approval = await self.ensure_approval_record(corpus_id)
        if approval.state != ApprovalState.DRAFT:
            raise ValueError(f"Cannot submit corpus in state: {approval.state.value}")

        approval.state = ApprovalState.PENDING_REVIEW
        approval.submitted_by = submitted_by
        approval.submitted_at = datetime.now(timezone.utc)
        approval.review_notes = notes
        return approval

    async def approve(
        self,
        corpus_id: uuid.UUID,
        reviewed_by: str,
        notes: Optional[str] = None,
    ) -> BenchmarkCorpusApproval:
        """Approve a corpus: PENDING_REVIEW → APPROVED."""
        approval = await self.ensure_approval_record(corpus_id)
        if approval.state != ApprovalState.PENDING_REVIEW:
            raise ValueError(f"Cannot approve corpus in state: {approval.state.value}")

        approval.state = ApprovalState.APPROVED
        approval.reviewed_by = reviewed_by
        approval.reviewed_at = datetime.now(timezone.utc)
        if notes:
            approval.review_notes = notes

        # Mark the corpus as active
        await self._db.execute(
            select(BenchmarkCorpus).where(BenchmarkCorpus.corpus_id == corpus_id)
        )
        # We need to update the corpus is_active — handled by caller
        return approval

    async def reject(
        self,
        corpus_id: uuid.UUID,
        reviewed_by: str,
        notes: str,
    ) -> BenchmarkCorpusApproval:
        """Reject a corpus: PENDING_REVIEW → REJECTED."""
        approval = await self.ensure_approval_record(corpus_id)
        if approval.state != ApprovalState.PENDING_REVIEW:
            raise ValueError(f"Cannot reject corpus in state: {approval.state.value}")

        approval.state = ApprovalState.REJECTED
        approval.reviewed_by = reviewed_by
        approval.reviewed_at = datetime.now(timezone.utc)
        approval.review_notes = notes
        return approval

    async def archive(self, corpus_id: uuid.UUID) -> BenchmarkCorpusApproval:
        """Archive a corpus: any state → ARCHIVED."""
        approval = await self.ensure_approval_record(corpus_id)
        approval.state = ApprovalState.ARCHIVED
        return approval

    # ── Deduplication ──────────────────────────────────────────────

    async def run_dedupe_analysis(
        self,
        corpus_id: uuid.UUID,
        similarity_threshold: float = 0.85,
    ) -> list[BenchmarkDedupeReport]:
        """Detect duplicate or near-duplicate clauses in a corpus.

        Uses embedding cosine similarity to find clause pairs above the
        threshold. Creates dedupe report records for each detected pair.

        Args:
            corpus_id: The corpus to analyze.
            similarity_threshold: Minimum similarity to flag (0.85 = similar, 0.95 = near).

        Returns:
            List of newly created dedupe report records.
        """
        # Fetch all clauses with embeddings
        clauses = await self._db.execute(
            select(BenchmarkClause).where(
                BenchmarkClause.corpus_id == corpus_id,
                BenchmarkClause.embedding.isnot(None),
                BenchmarkClause.tenant_id == uuid.UUID(self._tenant_id),
            ).order_by(BenchmarkClause.category)
        )
        clause_rows = list(clauses.scalars().all())

        if len(clause_rows) < 2:
            return []

        reports = []
        seen_pairs: set[tuple[str, str]] = set()

        for i in range(len(clause_rows)):
            for j in range(i + 1, len(clause_rows)):
                a, b = clause_rows[i], clause_rows[j]

                # Skip if same text (exact duplicate by text comparison)
                if a.clause_text.strip() == b.clause_text.strip():
                    severity = DedupeSeverity.EXACT
                    similarity = 1.0
                elif a.embedding and b.embedding:
                    try:
                        similarity = cosine_similarity(a.embedding, b.embedding)
                    except Exception:
                        continue

                    if similarity >= 0.95:
                        severity = DedupeSeverity.NEAR
                    elif similarity >= similarity_threshold:
                        severity = DedupeSeverity.SIMILAR
                    else:
                        continue
                else:
                    continue  # Skip pairs where either embedding is missing

                # Avoid duplicate (a,b) and (b,a) pairs
                pair_key = (str(a.clause_id), str(b.clause_id))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                report = BenchmarkDedupeReport(
                    report_id=uuid.uuid4(),
                    corpus_id=corpus_id,
                    tenant_id=uuid.UUID(self._tenant_id),
                    severity=severity,
                    clause_id_a=a.clause_id,
                    clause_id_b=b.clause_id,
                    similarity_score=round(similarity, 4),
                    clause_category=a.category,
                    detected_by="auto",
                )
                self._db.add(report)
                reports.append(report)

        await self._db.flush()

        logger.info(
            "[Dedupe] Found %d duplicate pairs in corpus %s (threshold=%.2f)",
            len(reports), corpus_id, similarity_threshold,
        )
        return reports

    async def resolve_dedupe(
        self,
        report_id: uuid.UUID,
        action: str,
        notes: Optional[str] = None,
    ) -> Optional[BenchmarkDedupeReport]:
        """Resolve a deduplication report.

        Args:
            report_id: The dedupe report to resolve.
            action: One of ``"merge"``, ``"remove"``, ``"keep"``, ``"dismiss"``.

        Returns:
            The updated report, or None if not found.
        """
        result = await self._db.execute(
            select(BenchmarkDedupeReport).where(
                BenchmarkDedupeReport.report_id == report_id,
            )
        )
        report = result.scalar_one_or_none()
        if not report:
            return None

        report.resolved = "true"
        report.resolution_action = action

        if action == "remove":
            # Remove clause_id_b (the duplicate)
            await self._db.execute(
                delete(BenchmarkClause).where(
                    BenchmarkClause.clause_id == report.clause_id_b,
                )
            )
        elif action == "merge":
            # Keep clause_id_a, remove clause_id_b
            await self._db.execute(
                delete(BenchmarkClause).where(
                    BenchmarkClause.clause_id == report.clause_id_b,
                )
            )

        return report

    async def list_dedupe_reports(
        self,
        corpus_id: Optional[uuid.UUID] = None,
        severity: Optional[str] = None,
        resolved: Optional[str] = None,
        limit: int = 50,
    ) -> list[BenchmarkDedupeReport]:
        """List deduplication reports, optionally filtered."""
        query = select(BenchmarkDedupeReport).where(
            BenchmarkDedupeReport.tenant_id == uuid.UUID(self._tenant_id),
        )
        if corpus_id:
            query = query.where(BenchmarkDedupeReport.corpus_id == corpus_id)
        if severity:
            query = query.where(BenchmarkDedupeReport.severity == DedupeSeverity(severity))
        if resolved is not None:
            query = query.where(BenchmarkDedupeReport.resolved == resolved)

        result = await self._db.execute(
            query.order_by(BenchmarkDedupeReport.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())


class LineageService:
    """Provenance tracking for benchmark recompute operations.

    Records each recompute event with corpus version, score deltas,
    and job linkage for full auditability.
    """

    def __init__(self, db: AsyncSession, tenant_id: str):
        self._db = db
        self._tenant_id = tenant_id

    async def record_recompute(
        self,
        corpus_id: uuid.UUID,
        corpus_version_id: Optional[uuid.UUID],
        job_id: Optional[uuid.UUID],
        operation: str,
        score_count_affected: int,
        corpus_clause_count: int,
        created_by: str = "system",
    ) -> BenchmarkLineage:
        """Record a recompute operation in the lineage log.

        Automatically links to the previous lineage record for delta tracking.
        """
        # Find the previous lineage record for this corpus
        prev_result = await self._db.execute(
            select(BenchmarkLineage).where(
                BenchmarkLineage.corpus_id == corpus_id,
                BenchmarkLineage.tenant_id == uuid.UUID(self._tenant_id),
            ).order_by(BenchmarkLineage.created_at.desc()).limit(1)
        )
        previous = prev_result.scalar_one_or_none()

        # Compute delta from previous recompute if available
        delta_summary = None
        if previous and previous.score_count_affected > 0:
            delta_summary = {
                "score_count_delta": score_count_affected - previous.score_count_affected,
                "clause_count_delta": corpus_clause_count - previous.corpus_clause_count,
                "days_since_last_recompute": (
                    (datetime.now(timezone.utc) - previous.created_at).days
                    if previous.created_at else None
                ),
                "previous_lineage_id": str(previous.lineage_id),
            }

        lineage = BenchmarkLineage(
            lineage_id=uuid.uuid4(),
            tenant_id=uuid.UUID(self._tenant_id),
            corpus_id=corpus_id,
            corpus_version_id=corpus_version_id,
            job_id=job_id,
            operation=operation,
            score_count_affected=score_count_affected,
            corpus_clause_count=corpus_clause_count,
            previous_lineage_id=previous.lineage_id if previous else None,
            delta_summary=delta_summary,
            created_by=created_by,
        )
        self._db.add(lineage)
        await self._db.flush()
        return lineage

    async def list_lineage(
        self,
        corpus_id: Optional[uuid.UUID] = None,
        limit: int = 50,
    ) -> list[BenchmarkLineage]:
        """List lineage records, newest first."""
        query = select(BenchmarkLineage).where(
            BenchmarkLineage.tenant_id == uuid.UUID(self._tenant_id),
        )
        if corpus_id:
            query = query.where(BenchmarkLineage.corpus_id == corpus_id)

        result = await self._db.execute(
            query.order_by(BenchmarkLineage.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def get_lineage(self, lineage_id: uuid.UUID) -> Optional[BenchmarkLineage]:
        """Get a specific lineage record."""
        result = await self._db.execute(
            select(BenchmarkLineage).where(
                BenchmarkLineage.lineage_id == lineage_id,
            )
        )
        return result.scalar_one_or_none()
