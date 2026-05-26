"""Compliance benchmarking API endpoints.

Provides endpoints for retrieving compliance benchmarks,
comparing contract clauses against industry standards, and
managing benchmark datasets.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from middleware.auth import TokenPayload, get_current_user, require_permission, Permissions
from benchmarking.corpus_ingestion import CorpusIngestionPipeline
from benchmarking.models import (
    BenchmarkClause,
    ContractType,
    IndustryCategory,
    CounterpartyType,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/benchmarks", tags=["Benchmarks"])

# Corpus ingestion pipeline instance
_corpus_pipeline = CorpusIngestionPipeline(
    quality_threshold=0.70,
    dedup_threshold=0.92,
)


# Built-in benchmark categories
BENCHMARK_CATEGORIES = {
    "gdpr": {
        "name": "GDPR Compliance",
        "description": "General Data Protection Regulation compliance benchmarks",
        "jurisdiction": "EU",
        "clauses": [
            "data_processing_agreement",
            "data_breach_notification",
            "data_subject_rights",
            "cross_border_transfer",
            "data_protection_officer",
        ],
    },
    "ccpa": {
        "name": "CCPA Compliance",
        "description": "California Consumer Privacy Act compliance benchmarks",
        "jurisdiction": "California, USA",
        "clauses": [
            "consumer_rights",
            "opt_out_provision",
            "data_sale_definition",
            "non_discrimination",
        ],
    },
    "hipaa": {
        "name": "HIPAA Compliance",
        "description": "Health Insurance Portability and Accountability Act",
        "jurisdiction": "USA",
        "clauses": [
            "phi_definition",
            "safeguards",
            "breach_notification",
            "business_associate_agreement",
        ],
    },
    "standard_contract": {
        "name": "Standard Contract Terms",
        "description": "Industry standard contract clause benchmarks",
        "jurisdiction": "General",
        "clauses": [
            "indemnification",
            "limitation_of_liability",
            "termination",
            "confidentiality",
            "force_majeure",
            "governing_law",
            "assignment",
        ],
    },
}


@router.get("/")
async def list_benchmarks(
    category: Optional[str] = None,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_BENCHMARKS)),
) -> Dict[str, Any]:
    """List available compliance benchmarks.

    Args:
        category: Optional benchmark category filter.
        user: Authenticated user.

    Returns:
        Dict with available benchmark categories.
    """
    if category:
        if category not in BENCHMARK_CATEGORIES:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Benchmark category '{category}' not found. "
                f"Available: {list(BENCHMARK_CATEGORIES.keys())}",
            )
        return {"category": category, "benchmarks": BENCHMARK_CATEGORIES[category]}

    return {
        "categories": BENCHMARK_CATEGORIES,
        "total_categories": len(BENCHMARK_CATEGORIES),
    }


@router.get("/compare")
async def compare_against_benchmark(
    contract_id: str = Query(..., description="Contract to compare"),
    benchmark_category: str = Query(
        "standard_contract", description="Benchmark category"
    ),
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_BENCHMARKS)),
) -> Dict[str, Any]:
    """Compare a contract's clauses against a benchmark standard.

    Args:
        contract_id: The contract to evaluate.
        benchmark_category: The benchmark standard to compare against.
        user: Authenticated user.

    Returns:
        Dict with comparison results and compliance scores.
    """
    if benchmark_category not in BENCHMARK_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Benchmark category '{benchmark_category}' not found",
        )

    from routers.contracts import _contracts_store

    contract = _contracts_store.get(contract_id)
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract {contract_id} not found",
        )

    tenant_id = user.tenant_id or "default"
    if contract.get("tenant_id") != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    benchmark = BENCHMARK_CATEGORIES[benchmark_category]
    clauses = contract.get("clauses", [])
    clause_types = {c.get("clause_type") for c in clauses if c.get("clause_type")}

    # Compute compliance scores
    required_clauses = benchmark["clauses"]
    found_clauses = [c for c in required_clauses if c in clause_types]
    missing_clauses = [c for c in required_clauses if c not in clause_types]

    compliance_score = len(found_clauses) / len(required_clauses) * 100 if required_clauses else 100

    result = {
        "contract_id": contract_id,
        "benchmark_category": benchmark_category,
        "benchmark_name": benchmark["name"],
        "jurisdiction": benchmark["jurisdiction"],
        "compliance_score": round(compliance_score, 1),
        "total_required_clauses": len(required_clauses),
        "present_clauses": found_clauses,
        "missing_clauses": missing_clauses,
        "recommendations": _generate_recommendations(missing_clauses),
    }

    logger.info(
        "Benchmark comparison: contract=%s, benchmark=%s, score=%.1f%%",
        contract_id,
        benchmark_category,
        compliance_score,
    )

    return result


@router.get("/categories/{category}/clauses/{clause_name}")
async def get_benchmark_clause_detail(
    category: str,
    clause_name: str,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_BENCHMARKS)),
) -> Dict[str, Any]:
    """Get detailed information about a specific benchmark clause.

    Args:
        category: Benchmark category.
        clause_name: The clause type name.
        user: Authenticated user.

    Returns:
        Dict with clause definition and criteria.
    """
    if category not in BENCHMARK_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category '{category}' not found",
        )

    benchmark = BENCHMARK_CATEGORIES[category]
    if clause_name not in benchmark["clauses"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clause '{clause_name}' not found in {category}",
        )

    return {
        "category": category,
        "clause": clause_name,
        "benchmark_name": benchmark["name"],
        "jurisdiction": benchmark["jurisdiction"],
        "description": f"Standard {clause_name.replace('_', ' ')} clause for {benchmark['name']}",
    }


@router.get("/score")
async def score_clause_benchmark(
    clause_text: str = Query(..., description="Clause text to score"),
    clause_type: str = Query(..., description="Type of clause"),
    contract_type: Optional[str] = Query(None, description="Contract type for segmentation"),
    industry: Optional[str] = Query(None, description="Industry for segmentation"),
    counterparty_type: Optional[str] = Query(None, description="Counterparty type"),
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_BENCHMARKS)),
) -> Dict[str, Any]:
    """Score a clause against market benchmarks.

    Args:
        clause_text: The clause text to score.
        clause_type: The type of clause.
        contract_type: Optional contract type for segmentation.
        industry: Optional industry for segmentation.
        counterparty_type: Optional counterparty type.
        user: Authenticated user.

    Returns:
        Dict with percentile score, distribution stats, and classification.
    """
    from benchmarking.api import BenchmarkAPI
    from benchmarking.scoring_engine import ScoringEngine
    from benchmarking.segmentation import SegmentationEngine
    from benchmarking.classification import ClauseClassifier

    # Initialize engines
    scoring_engine = ScoringEngine()
    segmentation_engine = SegmentationEngine()
    classifier = ClauseClassifier()

    api = BenchmarkAPI(
        scoring_engine=scoring_engine,
        segmentation_engine=segmentation_engine,
        classifier=classifier,
    )

    # Parse optional enums
    ct = None
    if contract_type:
        from benchmarking.models import ContractType
        try:
            ct = ContractType(contract_type)
        except ValueError:
            pass

    ind = None
    if industry:
        from benchmarking.models import IndustryCategory
        try:
            ind = IndustryCategory(industry)
        except ValueError:
            pass

    cpt = None
    if counterparty_type:
        from benchmarking.models import CounterpartyType
        try:
            cpt = CounterpartyType(counterparty_type)
        except ValueError:
            pass

    score = api.score_clause(
        clause_text=clause_text,
        clause_type=clause_type,
        contract_type=ct,
        industry=ind,
        counterparty_type=cpt,
    )

    if score is None:
        return {
            "clause_type": clause_type,
            "scored": False,
            "message": "No benchmark data available for this clause type and segment. "
            "Try ingesting more data or using a broader segment.",
        }

    return {
        "scored": True,
        "clause_type": clause_type,
        "percentile": score.percentile,
        "classification": score.classification,
        "classification_confidence": score.classification_confidence,
        "similar_clause_count": score.similar_clause_count,
        "distribution_stats": score.distribution_stats.model_dump(),
        "segment": {
            "match_type": score.segment.match_type,
            "matching_clause_count": score.segment.matching_clause_count,
            "fallback_path": score.segment.fallback_path,
        },
    }


@router.get("/freshness")
async def get_benchmark_freshness(
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_BENCHMARKS)),
) -> Dict[str, Any]:
    """Get benchmark corpus freshness status.

    Returns:
        Dict with freshness summary for all segments.
    """
    from benchmarking.freshness import FreshnessTracker

    tracker = FreshnessTracker()
    summary = tracker.get_freshness_summary()

    return {
        "freshness_summary": summary,
        "thresholds": {
            "green": "< 30 days",
            "amber": "30-90 days",
            "red": "> 90 days",
        },
    }


def _generate_recommendations(missing_clauses: List[str]) -> List[Dict[str, str]]:
    """Generate recommendations for missing clauses.

    Args:
        missing_clauses: List of missing clause types.

    Returns:
        List of recommendation dicts.
    """
    recommendations = {
        "indemnification": {
            "clause": "Indemnification",
            "priority": "high",
            "recommendation": "Add mutual indemnification clause defining scope of indemnity, "
            "notice provisions, and defense obligations.",
        },
        "limitation_of_liability": {
            "clause": "Limitation of Liability",
            "priority": "high",
            "recommendation": "Include limitation of liability clause with caps on damages, "
            "exclusions for gross negligence, and IP infringement.",
        },
        "termination": {
            "clause": "Termination",
            "priority": "high",
            "recommendation": "Add termination clause covering for cause, for convenience, "
            "notice periods, and post-termination obligations.",
        },
        "confidentiality": {
            "clause": "Confidentiality",
            "priority": "high",
            "recommendation": "Include confidentiality clause defining confidential information, "
            "exclusions, disclosure obligations, and term.",
        },
        "force_majeure": {
            "clause": "Force Majeure",
            "priority": "medium",
            "recommendation": "Add force majeure clause covering events, notice requirements, "
            "and remedies including termination rights.",
        },
        "governing_law": {
            "clause": "Governing Law",
            "priority": "medium",
            "recommendation": "Include governing law and jurisdiction clause specifying "
            "applicable law and dispute venue.",
        },
        "assignment": {
            "clause": "Assignment",
            "priority": "medium",
            "recommendation": "Add assignment clause covering consent requirements, "
            "permitted assignments, and change of control.",
        },
    }

    return [
        recommendations.get(clause, {
            "clause": clause.replace("_", " ").title(),
            "priority": "medium",
            "recommendation": f"Review and add standard {clause.replace('_', ' ')} clause.",
        })
        for clause in missing_clauses
    ]


# ── Corpus Management Endpoints ─────────────────────────────────────────────


@router.post("/corpus/ingest", status_code=status.HTTP_201_CREATED)
async def ingest_benchmark_clauses(
    clauses: List[Dict[str, Any]],
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.WRITE_PLAYBOOKS)),
) -> Dict[str, Any]:
    """Ingest clauses into the benchmark corpus.

    Processes raw clause data through the full pipeline:
    receive → anonymize PII → classify → quality filter → deduplicate → store.

    Args:
        clauses: List of raw clause data dicts. Each must have 'clause_text'.
                 Optional: source_document_id, clause_type, contract_type,
                 industry, counterparty_type, deal_size_range, jurisdiction.

    Returns:
        Ingestion result with counts.

    Raises:
        HTTPException: If ingestion fails.
    """
    if not clauses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No clauses provided for ingestion",
        )

    if len(clauses) > 1000:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Maximum 1,000 clauses per batch. Use batch ingestion for larger sets.",
        )

    try:
        result = _corpus_pipeline.ingest(clauses)
        metadata = _corpus_pipeline.get_metadata()

        return {
            "ingestion_id": result.ingestion_id,
            "total_received": result.total_received,
            "passed_quality_filter": result.passed_quality_filter,
            "duplicates_removed": result.duplicates_removed,
            "stored": result.stored,
            "failed": result.failed,
            "duration_ms": round(result.duration_ms, 2),
            "corpus_total": metadata.total_clauses,
            "errors": result.errors[:10] if result.errors else [],
        }

    except Exception as exc:
        logger.error("Corpus ingestion failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Corpus ingestion failed: {exc}",
        )


@router.post("/corpus/ingest/batch", status_code=status.HTTP_202_ACCEPTED)
async def batch_ingest_benchmark_clauses(
    file_path: str = Query(..., description="Path to JSON file with clauses array"),
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.WRITE_PLAYBOOKS)),
) -> Dict[str, Any]:
    """Batch ingest clauses from a JSON file.

    Processes a JSON file containing an array of clause objects.
    Each object must have at minimum 'clause_text'.

    Args:
        file_path: Path to JSON file with clauses array.

    Returns:
        Batch ingestion job info.
    """
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {file_path}",
        )

    try:
        with open(file_path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read file: {exc}",
        )

    clauses = data if isinstance(data, list) else data.get("clauses", data.get("data", []))

    if not clauses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No clauses found in file",
        )

    # Process in batches of 1000
    batch_id = str(uuid.uuid4())
    total = len(clauses)
    batches = [clauses[i:i + 1000] for i in range(0, total, 1000)]

    results = []
    for batch in batches:
        result = _corpus_pipeline.ingest(batch)
        results.append({
            "batch_size": len(batch),
            "stored": result.stored,
            "failed": result.failed,
            "duplicates_removed": result.duplicates_removed,
        })

    metadata = _corpus_pipeline.get_metadata()

    return {
        "batch_id": batch_id,
        "total_clauses": total,
        "batches_processed": len(batches),
        "results": results,
        "corpus_total": metadata.total_clauses,
    }


@router.get("/corpus/stats")
async def get_corpus_stats(
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_BENCHMARKS)),
) -> Dict[str, Any]:
    """Get benchmark corpus statistics.

    Returns:
        Corpus metadata with counts and quality metrics.
    """
    metadata = _corpus_pipeline.get_metadata()
    return metadata.model_dump()


@router.get("/corpus/clauses")
async def list_corpus_clauses(
    clause_type: Optional[str] = None,
    contract_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_BENCHMARKS)),
) -> Dict[str, Any]:
    """List clauses in the benchmark corpus.

    Args:
        clause_type: Optional filter by clause type.
        contract_type: Optional filter by contract type.
        page: Page number.
        page_size: Items per page.

    Returns:
        Paginated list of benchmark clauses.
    """
    all_clauses = list(_corpus_pipeline._corpus.values())

    if clause_type:
        all_clauses = [c for c in all_clauses if c.clause_type == clause_type]
    if contract_type:
        all_clauses = [c for c in all_clauses if c.contract_type.value == contract_type]

    total = len(all_clauses)
    start = (page - 1) * page_size
    end = start + page_size

    return {
        "clauses": [
            c.model_dump(exclude={"embedding"}) for c in all_clauses[start:end]
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
