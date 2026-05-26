"""Opt-in anonymized benchmark corpus pipeline (V2-031).

Provides a customer data contribution pipeline that allows tenants to
opt-in to sharing anonymized contract data for benchmark improvement.
Handles consent, anonymization, quality filtering, and ingestion.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ContributionAgreement:
    """A tenant's agreement to contribute benchmark data."""

    agreement_id: str
    tenant_id: str
    organization_name: str
    agreed_at: str
    expires_at: Optional[str] = None
    scope: str = "full"  # full, metadata_only, anonymized_only
    status: str = "active"  # active, revoked, expired
    data_categories: List[str] = field(default_factory=lambda: [
        "clause_text", "risk_scores", "contract_types", "benchmark_comparisons"
    ])
    anonymization_level: str = "high"  # high, medium, low
    revocable: bool = True
    consent_version: str = "v1.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agreement_id": self.agreement_id,
            "tenant_id": self.tenant_id,
            "organization_name": self.organization_name,
            "agreed_at": self.agreed_at,
            "expires_at": self.expires_at,
            "scope": self.scope,
            "status": self.status,
            "data_categories": self.data_categories,
            "anonymization_level": self.anonymization_level,
            "consent_version": self.consent_version,
        }


@dataclass
class ContributionRecord:
    """A single contribution of contract data to the benchmark corpus."""

    contribution_id: str
    tenant_id: str
    contract_id: str
    contract_type: str
    clause_count: int
    anonymization_level: str
    quality_score: float
    contributed_at: str
    included_clauses: int
    rejected_clauses: int
    rejection_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contribution_id": self.contribution_id,
            "tenant_id": self.tenant_id,
            "contract_id": self.contract_id,
            "contract_type": self.contract_type,
            "clause_count": self.clause_count,
            "anonymization_level": self.anonymization_level,
            "quality_score": self.quality_score,
            "contributed_at": self.contributed_at,
            "included_clauses": self.included_clauses,
            "rejected_clauses": self.rejected_clauses,
            "rejection_reasons": self.rejection_reasons,
        }


class BenchmarkCorpusPipeline:
    """Opt-in anonymized benchmark corpus contribution pipeline.

    Manages tenant consent, data anonymization, quality filtering,
    and ingestion into the benchmark corpus.

    Usage:
        pipeline = BenchmarkCorpusPipeline()
        await pipeline.register_agreement(agreement)
        result = await pipeline.contribute_contract(tenant_id, contract_id, clauses)
    """

    def __init__(
        self,
        anonymizer: Optional[Any] = None,
        quality_filter: Optional[Any] = None,
        corpus_ingestion: Optional[Any] = None,
        db_pool: Optional[Any] = None,
    ) -> None:
        """Initialize the benchmark corpus pipeline.

        Args:
            anonymizer: PII anonymization module.
            quality_filter: Quality filtering module.
            corpus_ingestion: Corpus ingestion module.
            db_pool: Optional database pool.
        """
        self._anonymizer = anonymizer
        self._quality_filter = quality_filter
        self._corpus_ingestion = corpus_ingestion
        self._db_pool = db_pool
        self._agreements: Dict[str, ContributionAgreement] = {}
        self._contributions: List[ContributionRecord] = []

    async def register_agreement(
        self,
        tenant_id: str,
        organization_name: str,
        scope: str = "full",
        data_categories: Optional[List[str]] = None,
        anonymization_level: str = "high",
    ) -> ContributionAgreement:
        """Register a tenant's consent to contribute benchmark data.

        Args:
            tenant_id: The tenant identifier.
            organization_name: The organization name.
            scope: Contribution scope.
            data_categories: Categories of data to contribute.
            anonymization_level: Anonymization level.

        Returns:
            The created ContributionAgreement.
        """
        agreement = ContributionAgreement(
            agreement_id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            organization_name=organization_name,
            agreed_at=datetime.utcnow().isoformat(),
            scope=scope,
            data_categories=data_categories or [
                "clause_text", "risk_scores", "contract_types", "benchmark_comparisons"
            ],
            anonymization_level=anonymization_level,
        )
        self._agreements[agreement.agreement_id] = agreement
        logger.info("Registered benchmark contribution agreement for tenant %s (%s)",
                     tenant_id, organization_name)
        return agreement

    async def revoke_agreement(self, agreement_id: str) -> bool:
        """Revoke a tenant's contribution agreement.

        Args:
            agreement_id: The agreement identifier.

        Returns:
            True if revoked.
        """
        agreement = self._agreements.get(agreement_id)
        if not agreement:
            return False
        agreement.status = "revoked"
        logger.info("Revoked benchmark contribution agreement %s", agreement_id)
        return True

    async def contribute_contract(
        self,
        tenant_id: str,
        contract_id: str,
        contract_type: str,
        clauses: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Contribute a contract's data to the benchmark corpus.

        Args:
            tenant_id: The tenant identifier.
            contract_id: The contract identifier.
            contract_type: The contract type.
            clauses: List of clause dicts.

        Returns:
            Dict with contribution results.
        """
        # Find active agreement
        agreement = next(
            (a for a in self._agreements.values()
             if a.tenant_id == tenant_id and a.status == "active"),
            None
        )
        if not agreement:
            return {
                "error": "No active contribution agreement found for tenant",
                "contributed": False,
            }

        # Anonymize clauses
        anonymized_clauses = await self._anonymize_clauses(
            clauses, agreement.anonymization_level
        )

        # Quality filter
        passed_clauses = []
        rejected_clauses = []
        rejection_reasons = []

        for clause in anonymized_clauses:
            if self._quality_filter:
                quality_result = await self._quality_filter.check_quality(
                    clause.get("text", "")
                )
                if quality_result.get("passed", True):
                    passed_clauses.append(clause)
                else:
                    rejected_clauses.append(clause)
                    rejection_reasons.append(
                        quality_result.get("reason", "Quality check failed")
                    )
            else:
                passed_clauses.append(clause)

        # Ingest into corpus
        if self._corpus_ingestion and passed_clauses:
            await self._corpus_ingestion.ingest_clauses(
                contract_id=contract_id,
                contract_type=contract_type,
                clauses=passed_clauses,
                source="customer_contribution",
            )

        # Record contribution
        record = ContributionRecord(
            contribution_id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            contract_id=contract_id,
            contract_type=contract_type,
            clause_count=len(clauses),
            anonymization_level=agreement.anonymization_level,
            quality_score=len(passed_clauses) / max(len(clauses), 1),
            contributed_at=datetime.utcnow().isoformat(),
            included_clauses=len(passed_clauses),
            rejected_clauses=len(rejected_clauses),
            rejection_reasons=rejection_reasons,
        )
        self._contributions.append(record)

        logger.info(
            "Contract %s contributed to benchmark corpus: %d/%d clauses accepted",
            contract_id, len(passed_clauses), len(clauses),
        )

        return {
            "contribution_id": record.contribution_id,
            "contributed": True,
            "total_clauses": len(clauses),
            "included_clauses": len(passed_clauses),
            "rejected_clauses": len(rejected_clauses),
            "quality_score": record.quality_score,
            "rejection_reasons": rejection_reasons[:5],
        }

    async def _anonymize_clauses(
        self,
        clauses: List[Dict[str, Any]],
        level: str,
    ) -> List[Dict[str, Any]]:
        """Anonymize PII in clauses.

        Args:
            clauses: List of clause dicts.
            level: Anonymization level.

        Returns:
            Anonymized clauses.
        """
        if self._anonymizer:
            anonymized = []
            for clause in clauses:
                text = clause.get("text", "") or clause.get("clause_text", "")
                result = await self._anonymizer.anonymize(text, level)
                clause["text"] = result.get("anonymized_text", text)
                clause["anonymized"] = True
                anonymized.append(clause)
            return anonymized

        # Basic fallback anonymization
        import re
        for clause in clauses:
            text = clause.get("text", "") or clause.get("clause_text", "")
            # Replace email addresses
            text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',
                          '[EMAIL_REDACTED]', text)
            # Replace phone numbers
            text = re.sub(r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b',
                          '[PHONE_REDACTED]', text)
            # Replace SSNs
            text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN_REDACTED]', text)
            clause["text"] = text
            clause["anonymized"] = True

        return clauses

    async def get_tenant_contributions(
        self,
        tenant_id: str,
    ) -> Dict[str, Any]:
        """Get contribution history for a tenant.

        Args:
            tenant_id: The tenant identifier.

        Returns:
            Dict with contribution history.
        """
        tenant_contributions = [
            c for c in self._contributions if c.tenant_id == tenant_id
        ]
        agreement = next(
            (a for a in self._agreements.values()
             if a.tenant_id == tenant_id),
            None
        )

        total_clauses = sum(c.clause_count for c in tenant_contributions)
        accepted_clauses = sum(c.included_clauses for c in tenant_contributions)

        return {
            "tenant_id": tenant_id,
            "has_active_agreement": agreement is not None and agreement.status == "active",
            "agreement": agreement.to_dict() if agreement else None,
            "total_contributions": len(tenant_contributions),
            "total_clauses_contributed": total_clauses,
            "total_clauses_accepted": accepted_clauses,
            "acceptance_rate": round(accepted_clauses / max(total_clauses, 1) * 100, 1),
            "recent_contributions": [c.to_dict() for c in tenant_contributions[-10:]],
        }

    async def get_corpus_stats(self) -> Dict[str, Any]:
        """Get overall corpus contribution statistics.

        Returns:
            Dict with corpus stats.
        """
        total_contributions = len(self._contributions)
        total_clauses = sum(c.clause_count for c in self._contributions)
        accepted_clauses = sum(c.included_clauses for c in self._contributions)
        active_agreements = sum(
            1 for a in self._agreements.values() if a.status == "active"
        )

        by_type: Dict[str, int] = {}
        for c in self._contributions:
            by_type[c.contract_type] = by_type.get(c.contract_type, 0) + 1

        return {
            "total_contributions": total_contributions,
            "total_clauses_contributed": total_clauses,
            "total_clauses_accepted": accepted_clauses,
            "overall_acceptance_rate": round(
                accepted_clauses / max(total_clauses, 1) * 100, 1
            ),
            "active_agreements": active_agreements,
            "contributions_by_contract_type": by_type,
            "average_quality_score": round(
                sum(c.quality_score for c in self._contributions) / max(len(self._contributions), 1), 3
            ),
        }
