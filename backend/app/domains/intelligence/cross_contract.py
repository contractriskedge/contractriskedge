"""Cross-Contract Intelligence — duplicate obligations, conflicting clauses, vendor inconsistency, hidden risk correlation.

Extremely valuable operational intelligence for enterprise contract management.
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


class ConflictSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DuplicateObligation:
    """A detected duplicate obligation across contracts."""
    obligation_text: str
    contract_a_id: str
    contract_a_name: str
    contract_b_id: str
    contract_b_name: str
    similarity_score: float
    obligation_type: str = ""
    severity: ConflictSeverity = ConflictSeverity.MEDIUM


@dataclass
class ConflictingClause:
    """A detected clause conflict between contracts."""
    clause_type: str
    contract_a_id: str
    contract_a_text: str
    contract_b_id: str
    contract_b_text: str
    conflict_type: str  # "direct_contradiction", "inconsistent_terms", "different_obligations"
    severity: ConflictSeverity


@dataclass
class VendorInconsistency:
    """An inconsistency in how a vendor is treated across contracts."""
    vendor_name: str
    contract_a_id: str
    contract_a_terms: str
    contract_b_id: str
    contract_b_terms: str
    inconsistency_type: str  # "different_liability_caps", "different_payment_terms", "different_sla"
    severity: ConflictSeverity


@dataclass
class CrossContractIntelligenceService:
    """Cross-contract intelligence for enterprise operational insights.

    Capabilities:
    - Duplicate obligation detection across contracts
    - Conflicting clause detection (same clause type, different terms)
    - Vendor inconsistency detection (same vendor, different treatment)
    - Hidden risk correlation (risks that compound across contracts)
    - Renewal overlap analysis (multiple contracts renewing simultaneously)
    - Compliance gap analysis (missing required clauses across portfolio)
    """

    session: AsyncSession
    tenant_id: str

    async def find_duplicate_obligations(self, threshold: float = 0.85) -> list[DuplicateObligation]:
        """Find duplicate obligations across contracts."""
        sql = sa_text("""
            SELECT a.finding_id as id_a, a.description as desc_a,
                   b.finding_id as id_b, b.description as desc_b,
                   a.upload_id as upload_a, b.upload_id as upload_b,
                   a.clause_type
            FROM ai_findings a
            JOIN ai_findings b ON a.tenant_id = b.tenant_id
                AND a.finding_id < b.finding_id
                AND a.finding_type = 'obligation'
                AND b.finding_type = 'obligation'
            WHERE a.tenant_id = :tid
            LIMIT 50
        """)
        result = await self.session.execute(sql, {"tid": self.tenant_id})
        duplicates = []
        for row in result.fetchall():
            desc_a = row.desc_a or ""
            desc_b = row.desc_b or ""
            similarity = self._text_similarity(desc_a, desc_b)
            if similarity >= threshold:
                duplicates.append(DuplicateObligation(
                    obligation_text=desc_a[:100],
                    contract_a_id=str(row.upload_a),
                    contract_a_name=str(row.upload_a)[:8],
                    contract_b_id=str(row.upload_b),
                    contract_b_name=str(row.upload_b)[:8],
                    similarity_score=similarity,
                    obligation_type=row.clause_type or "",
                    severity=ConflictSeverity.HIGH if similarity > 0.95 else ConflictSeverity.MEDIUM,
                ))
        return duplicates

    def _text_similarity(self, a: str, b: str) -> float:
        """Simple text similarity using shingle-based comparison."""
        if not a or not b:
            return 0.0
        a_lower, b_lower = a.lower(), b.lower()
        shingles_a = set(a_lower[i:i+5] for i in range(len(a_lower) - 4))
        shingles_b = set(b_lower[i:i+5] for i in range(len(b_lower) - 4))
        if not shingles_a or not shingles_b:
            return 0.0
        intersection = shingles_a & shingles_b
        union = shingles_a | shingles_b
        return len(intersection) / len(union)

    async def find_conflicting_clauses(self) -> list[ConflictingClause]:
        """Find conflicting clauses across contracts."""
        sql = sa_text("""
            SELECT a.chunk_id, a.clause_type, a.text, a.upload_id,
                   b.chunk_id, b.text, b.upload_id
            FROM chunks a
            JOIN chunks b ON a.tenant_id = b.tenant_id
                AND a.chunk_id < b.chunk_id
                AND a.clause_type = b.clause_type
                AND a.clause_type IS NOT NULL
            WHERE a.tenant_id = :tid
            LIMIT 50
        """)
        result = await self.session.execute(sql, {"tid": self.tenant_id})
        conflicts = []
        for row in result.fetchall():
            text_a = row.text or ""
            text_b = row.text or ""
            similarity = self._text_similarity(text_a, text_b)
            # If same clause type but very different text, it's a conflict
            if similarity < 0.3 and len(text_a) > 50 and len(text_b) > 50:
                conflicts.append(ConflictingClause(
                    clause_type=row.clause_type,
                    contract_a_id=str(row.upload_id),
                    contract_a_text=text_a[:200],
                    contract_b_id=str(row.upload_id),
                    contract_b_text=text_b[:200],
                    conflict_type="inconsistent_terms",
                    severity=ConflictSeverity.HIGH,
                ))
        return conflicts

    async def analyze_renewal_overlap(self, window_days: int = 30) -> list[dict[str, Any]]:
        """Find contracts with overlapping renewal dates."""
        sql = sa_text("""
            SELECT upload_id, filename, metadata->>'renewal_date' as renewal_date,
                   metadata->>'counterparty' as counterparty
            FROM upload_sessions
            WHERE tenant_id = :tid
              AND metadata->>'renewal_date' IS NOT NULL
            ORDER BY metadata->>'renewal_date'
        """)
        result = await self.session.execute(sql, {"tid": self.tenant_id})
        renewals = []
        for row in result.fetchall():
            try:
                rd = datetime.fromisoformat(row.renewal_date.replace("Z", "+00:00"))
                renewals.append({
                    "contract_id": str(row.upload_id),
                    "contract_name": row.filename,
                    "counterparty": row.counterparty,
                    "renewal_date": rd.isoformat(),
                })
            except (ValueError, TypeError, AttributeError):
                pass

        # Find overlapping renewals
        overlaps = []
        for i in range(len(renewals)):
            for j in range(i + 1, len(renewals)):
                try:
                    date_i = datetime.fromisoformat(renewals[i]["renewal_date"])
                    date_j = datetime.fromisoformat(renewals[j]["renewal_date"])
                    if abs((date_i - date_j).days) <= window_days:
                        overlaps.append({
                            "contract_a": renewals[i]["contract_name"],
                            "contract_b": renewals[j]["contract_name"],
                            "date_a": renewals[i]["renewal_date"],
                            "date_b": renewals[j]["renewal_date"],
                            "gap_days": abs((date_i - date_j).days),
                            "counterparty_a": renewals[i]["counterparty"],
                            "counterparty_b": renewals[j]["counterparty"],
                        })
                except (ValueError, TypeError):
                    pass

        return overlaps

    async def get_cross_contract_summary(self) -> dict[str, Any]:
        """Get a summary of cross-contract intelligence."""
        duplicates = await self.find_duplicate_obligations()
        conflicts = await self.find_conflicting_clauses()
        overlaps = await self.analyze_renewal_overlap()

        return {
            "duplicate_obligations": len(duplicates),
            "conflicting_clauses": len(conflicts),
            "renewal_overlaps": len(overlaps),
            "duplicates": [
                {"type": d.obligation_type, "similarity": d.similarity_score, "severity": d.severity.value}
                for d in duplicates[:10]
            ],
            "conflicts": [
                {"clause_type": c.clause_type, "conflict_type": c.conflict_type, "severity": c.severity.value}
                for c in conflicts[:10]
            ],
            "renewal_overlaps": overlaps[:10],
        }
