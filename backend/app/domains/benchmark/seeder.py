"""Benchmark dataset seeder — ingestion pipeline for benchmark contracts.

Handles:
- Uploading and parsing benchmark reference contracts
- Clause extraction and normalization
- Embedding generation for similarity search
- Corpus indexing and metadata tagging
"""

from __future__ import annotations

import uuid
import logging
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.domains.benchmark.models import (
    BenchmarkCorpus,
    BenchmarkClause,
    ClauseCategory,
    CorpusSource,
    CorpusIndustry,
    Geography,
    ContractType,
)
from app.domains.benchmark.engine import BenchmarkEngine

logger = logging.getLogger(__name__)


class BenchmarkSeeder:
    """Ingestion pipeline for benchmark contract data.

    Handles corpus creation, clause ingestion with embedding generation,
    and metadata enrichment for industry/geography/contract-type segmentation.
    """

    # Pre-defined industry-standard clause templates for bootstrapping
    STANDARD_CLAUSE_TEMPLATES: dict[str, list[dict]] = {
        "indemnification": [
            {"text": "Each party shall indemnify, defend, and hold harmless the other party from and against any and all claims, damages, losses, and expenses arising out of or relating to any breach of this agreement by the indemnifying party.", "risk_score": 30, "is_favorable": "favorable"},
            {"text": "Company shall indemnify Client against all third-party claims arising from Company's gross negligence or willful misconduct.", "risk_score": 50, "is_favorable": "neutral"},
            {"text": "Provider shall indemnify Customer against all losses resulting from any third-party claim that the Services infringe any intellectual property rights.", "risk_score": 45, "is_favorable": "favorable"},
            {"text": "Vendor agrees to indemnify and hold harmless Customer from any and all claims arising out of Vendor's performance under this Agreement.", "risk_score": 35, "is_favorable": "favorable"},
            {"text": "Each party shall indemnify the other against all losses arising from third-party claims related to the indemnifying party's breach of confidentiality obligations.", "risk_score": 40, "is_favorable": "neutral"},
        ],
        "liability_cap": [
            {"text": "Neither party's liability shall exceed the total fees paid or payable by Customer during the twelve months preceding the claim.", "risk_score": 40, "is_favorable": "neutral"},
            {"text": "Company's aggregate liability shall not exceed the amount paid by Client under this Agreement.", "risk_score": 35, "is_favorable": "favorable"},
            {"text": "Total liability of either party shall be limited to the contract value, except for confidentiality breaches, IP infringement, or gross negligence.", "risk_score": 50, "is_favorable": "neutral"},
            {"text": "Liability cap shall be three times the annual contract value, with no cap for unlimited liability items including data breach and IP infringement.", "risk_score": 65, "is_favorable": "unfavorable"},
            {"text": "Neither party shall be liable for indirect, incidental, special, or consequential damages.", "risk_score": 30, "is_favorable": "favorable"},
        ],
        "termination": [
            {"text": "Either party may terminate this agreement upon 30 days written notice for convenience.", "risk_score": 30, "is_favorable": "favorable"},
            {"text": "Customer may terminate for convenience upon 60 days notice; Provider may terminate only for material breach uncured after 30 days.", "risk_score": 45, "is_favorable": "neutral"},
            {"text": "This agreement shall automatically renew for successive one-year terms unless either party provides 90 days notice of non-renewal.", "risk_score": 55, "is_favorable": "neutral"},
            {"text": "Either party may terminate immediately upon written notice if the other party becomes insolvent or files for bankruptcy.", "risk_score": 35, "is_favorable": "neutral"},
            {"text": "Customer may terminate for any reason with 15 days notice and receive a pro-rata refund of prepaid fees.", "risk_score": 25, "is_favorable": "favorable"},
        ],
        "confidentiality": [
            {"text": "The receiving party shall hold all confidential information in strict confidence for a period of three years from disclosure.", "risk_score": 30, "is_favorable": "favorable"},
            {"text": "Confidentiality obligations shall survive termination for a period of five years.", "risk_score": 40, "is_favorable": "neutral"},
            {"text": "Each party shall use reasonable care to protect the other's confidential information, but no less than the care used for its own.", "risk_score": 35, "is_favorable": "favorable"},
            {"text": "Confidential information excludes information that is or becomes publicly known through no fault of the receiving party.", "risk_score": 25, "is_favorable": "favorable"},
            {"text": "All confidential information must be returned or destroyed upon termination of this agreement.", "risk_score": 30, "is_favorable": "favorable"},
        ],
        "data_privacy": [
            {"text": "Each party shall comply with all applicable data protection laws and regulations in the performance of this agreement.", "risk_score": 30, "is_favorable": "favorable"},
            {"text": "Provider shall implement appropriate technical and organizational measures to ensure a level of security appropriate to the risk.", "risk_score": 35, "is_favorable": "favorable"},
            {"text": "Customer data shall be stored and processed only within the United States or other jurisdictions approved in writing.", "risk_score": 40, "is_favorable": "neutral"},
            {"text": "Provider shall notify Customer within 72 hours of becoming aware of any data breach involving Customer data.", "risk_score": 25, "is_favorable": "favorable"},
            {"text": "Data processing shall be governed by a separate Data Processing Agreement (DPA) incorporated by reference.", "risk_score": 35, "is_favorable": "neutral"},
        ],
        "force_majeure": [
            {"text": "Neither party shall be liable for delays or failures caused by circumstances beyond its reasonable control.", "risk_score": 25, "is_favorable": "favorable"},
            {"text": "Force majeure events include but are not limited to: acts of God, war, terrorism, pandemic, and government actions.", "risk_score": 30, "is_favorable": "neutral"},
            {"text": "If a force majeure event continues for more than 30 days, either party may terminate the affected services without liability.", "risk_score": 35, "is_favorable": "neutral"},
            {"text": "The party affected by force majeure shall provide prompt written notice and use reasonable efforts to mitigate the impact.", "risk_score": 25, "is_favorable": "favorable"},
            {"text": "Force majeure does not excuse payment obligations or confidentiality obligations.", "risk_score": 30, "is_favorable": "neutral"},
        ],
    }

    def __init__(self, db: AsyncSession, tenant_id: str):
        self._db = db
        self._tenant_id = tenant_id
        self._engine = BenchmarkEngine(db, tenant_id)

    async def create_corpus(
        self,
        name: str,
        description: Optional[str] = None,
        industry: Optional[str] = None,
        geography: Optional[str] = None,
        contract_type: Optional[str] = None,
        source: str = "industry_standard",
    ) -> BenchmarkCorpus:
        """Create a new benchmark corpus."""
        corpus = BenchmarkCorpus(
            corpus_id=uuid.uuid4(),
            tenant_id=uuid.UUID(self._tenant_id),
            name=name,
            description=description,
            source=CorpusSource(source),
            industry=CorpusIndustry(industry) if industry else None,
            geography=Geography(geography) if geography else None,
            contract_type=ContractType(contract_type) if contract_type else None,
        )
        self._db.add(corpus)
        await self._db.flush()
        return corpus

    async def seed_industry_standards(self) -> dict[str, int]:
        """Seed the database with pre-defined industry-standard clause templates.

        Creates or updates a corpus for each industry with standard clause
        benchmarks. This bootstraps the benchmark system with reference data.

        Returns:
            Dict mapping corpus names to clause counts
        """
        results = {}

        for industry_name, industry_enum in [
            ("technology", CorpusIndustry.TECHNOLOGY),
            ("financial_services", CorpusIndustry.FINANCIAL_SERVICES),
            ("healthcare", CorpusIndustry.HEALTHCARE),
        ]:
            corpus_name = f"Industry Standard - {industry_name.replace('_', ' ').title()}"
            corpus_desc = f"Industry-standard clause benchmarks for the {industry_name.replace('_', ' ')} sector. Based on analysis of publicly available contracts and legal standards."

            # Check if corpus already exists
            existing = await self._db.execute(
                select(BenchmarkCorpus).where(
                    BenchmarkCorpus.tenant_id == uuid.UUID(self._tenant_id),
                    BenchmarkCorpus.name == corpus_name,
                )
            )
            corpus = existing.scalar_one_or_none()
            if not corpus:
                corpus = await self.create_corpus(
                    name=corpus_name,
                    description=corpus_desc,
                    industry=industry_name,
                    geography="north_america",
                    source="industry_standard",
                )

            # Seed clauses for each category
            clause_count = 0
            for category_str, templates in self.STANDARD_CLAUSE_TEMPLATES.items():
                for template in templates:
                    # Check if similar clause already exists
                    existing_clause = await self._db.execute(
                        select(BenchmarkClause).where(
                            BenchmarkClause.corpus_id == corpus.corpus_id,
                            BenchmarkClause.clause_text == template["text"],
                        )
                    )
                    if not existing_clause.scalar_one_or_none():
                        await self._engine.add_clause_to_corpus(
                            corpus_id=corpus.corpus_id,
                            category=category_str,
                            clause_text=template["text"],
                            source_document=f"Industry Standard - {category_str}",
                            risk_score=template["risk_score"],
                            is_favorable=template["is_favorable"],
                        )
                        clause_count += 1

            # Update corpus counts
            total_clauses = await self._db.execute(
                select(func.count(BenchmarkClause.clause_id)).where(
                    BenchmarkClause.corpus_id == corpus.corpus_id,
                )
            )
            corpus.clause_count = total_clauses.scalar() or 0
            corpus.document_count = 1

            results[corpus_name] = corpus.clause_count

        await self._db.flush()
        logger.info("Seeded benchmark corpora: %s", results)
        return results

    async def ingest_clause(
        self,
        corpus_id: uuid.UUID,
        category: str,
        clause_text: str,
        source_document: Optional[str] = None,
        risk_score: Optional[float] = None,
        is_favorable: Optional[str] = None,
    ) -> BenchmarkClause:
        """Ingest a single clause into a benchmark corpus."""
        return await self._engine.add_clause_to_corpus(
            corpus_id=corpus_id,
            category=category,
            clause_text=clause_text,
            source_document=source_document,
            risk_score=risk_score,
            is_favorable=is_favorable,
        )

    async def bulk_ingest_clauses(
        self,
        corpus_id: uuid.UUID,
        clauses: list[dict],
    ) -> int:
        """Bulk ingest multiple clauses into a corpus."""
        count = 0
        for clause in clauses:
            await self.ingest_clause(
                corpus_id=corpus_id,
                category=clause["category"],
                clause_text=clause["clause_text"],
                source_document=clause.get("source_document"),
                risk_score=clause.get("risk_score"),
                is_favorable=clause.get("is_favorable"),
            )
            count += 1
        return count
