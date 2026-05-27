"""Benchmark API router — endpoints for corpus management, scoring, comparison, orchestration, and governance.

Endpoints:
- POST   /benchmarks/corpora — Create a benchmark corpus
- GET    /benchmarks/corpora — List benchmark corpora
- GET    /benchmarks/corpora/{corpus_id} — Get corpus details
- POST   /benchmarks/corpora/{corpus_id}/clauses — Add a clause to a corpus
- GET    /benchmarks/corpora/{corpus_id}/clauses — List clauses in a corpus
- POST   /benchmarks/score — Score a contract's clauses against a corpus
- GET    /benchmarks/score — Score a single clause text
- GET    /benchmarks/corpora/{corpus_id}/similar — Find similar clauses
- GET    /benchmarks/industry/{industry} — Industry comparison
- GET    /benchmarks/dashboard — Dashboard KPIs and aggregate data
- POST   /benchmarks/seed — Seed industry-standard benchmark data
- GET    /benchmarks/export/csv — Export benchmark data as CSV
- POST   /benchmarks/jobs/recompute — Trigger async recompute
- POST   /benchmarks/jobs/refresh-embeddings — Trigger async embedding refresh
- GET    /benchmarks/jobs — List orchestration jobs
- GET    /benchmarks/jobs/{job_id} — Get job status
- GET    /benchmarks/corpora/{corpus_id}/versions — List corpus versions
- POST   /benchmarks/corpora/{corpus_id}/approval — Approval workflow actions
- GET    /benchmarks/corpora/{corpus_id}/approval — Get approval state
- POST   /benchmarks/corpora/{corpus_id}/dedupe — Run deduplication analysis
- GET    /benchmarks/corpora/{corpus_id}/dedupe — List dedupe reports
- POST   /benchmarks/dedupe/{report_id}/resolve — Resolve a dedupe report
- GET    /benchmarks/corpora/{corpus_id}/lineage — List recompute lineage
"""

from __future__ import annotations

import csv
import io
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user, get_tenant_id
from app.domains.benchmark.engine import BenchmarkEngine
from app.domains.benchmark.seeder import BenchmarkSeeder
from app.domains.benchmark.governance import CorpusGovernanceService, LineageService
from app.domains.benchmark.schemas import (
    BenchmarkCorpusCreate,
    BenchmarkCorpusResponse,
    BenchmarkCorpusListResponse,
    BenchmarkClauseResponse,
    BenchmarkClauseCreate,
    BenchmarkScoreRequest,
    BenchmarkScoreResponse,
    ClauseBenchmarkScore,
    SimilarClauseInfo,
    IndustryComparisonResponse,
    BenchmarkDashboardResponse,
    BenchmarkKpiResponse,
    BenchmarkJobResponse,
    BenchmarkJobListResponse,
    BenchmarkJobCreateResponse,
    BenchmarkCorpusVersionResponse,
    BenchmarkCorpusVersionListResponse,
    ApprovalAction,
    BenchmarkCorpusApprovalResponse,
    BenchmarkDedupeReportResponse,
    BenchmarkDedupeReportListResponse,
    DedupeResolveRequest,
    BenchmarkLineageResponse,
    BenchmarkLineageListResponse,
)
from app.kernel.security.auth import UserContext
from app.kernel.security.rbac import require_permission
from app.kernel.security.permissions import Permissions

router = APIRouter(prefix="/benchmarks", tags=["Benchmarks"])


def _get_engine(db: AsyncSession, user: UserContext) -> BenchmarkEngine:
    return BenchmarkEngine(db, user.tenant_id)


def _get_seeder(db: AsyncSession, user: UserContext) -> BenchmarkSeeder:
    return BenchmarkSeeder(db, user.tenant_id)


# ── Corpus Management ──────────────────────────────────────────────


@router.post("/corpora", response_model=BenchmarkCorpusResponse, status_code=status.HTTP_201_CREATED)
async def create_corpus(
    body: BenchmarkCorpusCreate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.BENCHMARK_WRITE)),
):
    """Create a new benchmark corpus."""
    seeder = _get_seeder(db, user)
    corpus = await seeder.create_corpus(
        name=body.name,
        description=body.description,
        industry=body.industry,
        geography=body.geography,
        contract_type=body.contract_type,
        source=body.source,
    )
    await db.commit()
    await db.refresh(corpus)
    return _corpus_to_response(corpus)


@router.get("/corpora", response_model=BenchmarkCorpusListResponse)
async def list_corpora(
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.BENCHMARK_READ)),
):
    """List all active benchmark corpora."""
    engine = _get_engine(db, user)
    corpora = await engine.list_corpora()
    return BenchmarkCorpusListResponse(
        items=[_corpus_to_response(c) for c in corpora],
        total=len(corpora),
    )


@router.get("/corpora/{corpus_id}", response_model=BenchmarkCorpusResponse)
async def get_corpus(
    corpus_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.BENCHMARK_READ)),
):
    """Get a single benchmark corpus."""
    engine = _get_engine(db, user)
    corpus = await engine.get_corpus(corpus_id)
    if not corpus:
        raise HTTPException(status_code=404, detail="Corpus not found")
    return _corpus_to_response(corpus)


@router.post("/corpora/{corpus_id}/clauses", response_model=BenchmarkClauseResponse, status_code=status.HTTP_201_CREATED)
async def add_clause(
    corpus_id: uuid.UUID,
    body: BenchmarkClauseCreate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.BENCHMARK_WRITE)),
):
    """Add a clause to a benchmark corpus."""
    engine = _get_engine(db, user)
    corpus = await engine.get_corpus(corpus_id)
    if not corpus:
        raise HTTPException(status_code=404, detail="Corpus not found")

    clause = await engine.add_clause_to_corpus(
        corpus_id=corpus_id,
        category=body.category,
        clause_text=body.clause_text,
        source_document=body.source_document,
        risk_score=body.risk_score,
        is_favorable=body.is_favorable,
    )
    await db.commit()
    return _clause_to_response(clause)


@router.get("/corpora/{corpus_id}/clauses", response_model=list[BenchmarkClauseResponse])
async def list_clauses(
    corpus_id: uuid.UUID,
    category: Optional[str] = Query(None, description="Filter by clause category"),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.BENCHMARK_READ)),
):
    """List clauses in a benchmark corpus."""
    engine = _get_engine(db, user)
    clauses = await engine.get_corpus_clauses(corpus_id, category=category)
    return [_clause_to_response(c) for c in clauses]


# ── Scoring ────────────────────────────────────────────────────────


@router.post("/score", response_model=BenchmarkScoreResponse)
async def score_clauses(
    body: BenchmarkScoreRequest,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.BENCHMARK_READ)),
):
    """Score a contract's clauses against a benchmark corpus."""
    engine = _get_engine(db, user)

    # Verify corpus exists
    corpus = await engine.get_corpus(body.corpus_id)
    if not corpus:
        raise HTTPException(status_code=404, detail="Corpus not found")

    clause_inputs = [(c.category, c.score) for c in body.clauses]
    clause_texts = {c.category: c.clause_text for c in body.clauses if c.clause_text}
    results = await engine.compute_percentile(
        body.upload_id, body.corpus_id, clause_inputs,
        clause_texts=clause_texts or None,
    )
    await db.commit()

    scores = [
        ClauseBenchmarkScore(
            clause_type=r["clause_type"],
            your_score=r["your_score"],
            market_median=r["market_median"],
            market_p25=r.get("market_p25"),
            market_p75=r.get("market_p75"),
            deviation=r.get("deviation"),
            deviation_percent=r.get("deviation_percent"),
            direction=r.get("direction"),
            percentile=r["percentile"],
            sample_size=r["sample_size"],
            confidence=r.get("confidence"),
            category=r["category"],
            similar_clauses=[SimilarClauseInfo(**s) for s in r.get("similar_clauses", [])],
            explainability=r.get("explainability"),
        )
        for r in results
    ]

    overall_percentile = (
        sum(s.percentile for s in scores) / len(scores)
        if scores else None
    )

    return BenchmarkScoreResponse(
        upload_id=body.upload_id,
        corpus_id=body.corpus_id,
        scores=scores,
        overall_percentile=round(overall_percentile, 2) if overall_percentile else None,
        overall_risk_level=_classify_risk(overall_percentile) if overall_percentile else None,
    )


@router.get("/score")
async def score_single_clause(
    clause_text: str = Query(..., description="The clause text to score"),
    clause_type: str = Query(..., description="The clause category/type"),
    corpus_id: Optional[uuid.UUID] = Query(None, description="Corpus ID (uses first available if not specified)"),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.BENCHMARK_READ)),
):
    """Score a single clause text against the benchmark corpus.

    Uses AI-based risk scoring and compares against the corpus distribution.
    """
    engine = _get_engine(db, user)

    # Find similar clauses in the corpus
    corpora = await engine.list_corpora()
    if not corpora:
        raise HTTPException(status_code=404, detail="No benchmark corpora available")

    target_corpus_id = corpus_id or corpora[0].corpus_id

    similar = await engine.find_similar_clauses(clause_text, target_corpus_id, top_k=3)

    return {
        "clause_type": clause_type,
        "clause_text": clause_text[:300],
        "similar_clauses": similar,
        "corpus_id": str(target_corpus_id),
        "scored": len(similar) > 0,
    }


# ── Similarity Search ──────────────────────────────────────────────


@router.get("/corpora/{corpus_id}/similar")
async def find_similar(
    corpus_id: uuid.UUID,
    clause_text: str = Query(..., description="Clause text to find similar matches for"),
    top_k: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.BENCHMARK_READ)),
):
    """Find similar clauses in a corpus using vector similarity."""
    engine = _get_engine(db, user)
    results = await engine.find_similar_clauses(clause_text, corpus_id, top_k=top_k)
    return {"clause_text": clause_text[:300], "corpus_id": str(corpus_id), "matches": results}


# ── Industry Comparison ────────────────────────────────────────────


@router.get("/industry/{industry}")
async def industry_comparison(
    industry: str,
    upload_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.BENCHMARK_READ)),
):
    """Compare against industry-specific benchmarks."""
    engine = _get_engine(db, user)
    comparisons = await engine.get_industry_comparison(
        upload_id or uuid.uuid4(), industry,
    )
    return {"industry": industry, "comparisons": comparisons}


# ── Dashboard ──────────────────────────────────────────────────────


@router.get("/dashboard", response_model=BenchmarkDashboardResponse)
async def benchmark_dashboard(
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.BENCHMARK_READ)),
):
    """Get benchmark dashboard KPIs and aggregate data."""
    engine = _get_engine(db, user)

    kpis = await engine.get_dashboard_kpis()
    corpora = await engine.list_corpora()

    kpi_responses = [
        BenchmarkKpiResponse(**kpi) for kpi in kpis
    ]

    return BenchmarkDashboardResponse(
        kpis=kpi_responses,
        clause_benchmarks=[],
        industry_comparisons=[],
        total_corpora=len(corpora),
        total_clauses=sum(c.clause_count or 0 for c in corpora),
    )


# ── Seed Data ──────────────────────────────────────────────────────


@router.post("/seed", response_model=dict)
async def seed_benchmark_data(
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.BENCHMARK_SEED)),
):
    """Seed the database with industry-standard benchmark clause data."""
    seeder = _get_seeder(db, user)
    results = await seeder.seed_industry_standards()
    await db.commit()
    return {
        "message": "Benchmark data seeded successfully",
        "corpora": results,
    }


# ── CSV Export ─────────────────────────────────────────────────────


@router.get("/export/csv")
async def export_benchmarks_csv(
    corpus_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.BENCHMARK_EXPORT)),
):
    """Export benchmark data as CSV."""
    engine = _get_engine(db, user)

    if corpus_id:
        corpora = [await engine.get_corpus(corpus_id)]
        corpora = [c for c in corpora if c]
    else:
        corpora = await engine.list_corpora()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Corpus Name", "Industry", "Geography", "Clause Category", "Clause Text", "Risk Score", "Favorable"])

    for corpus in corpora:
        clauses = await engine.get_corpus_clauses(corpus.corpus_id)
        for clause in clauses:
            writer.writerow([
                corpus.name,
                corpus.industry.value if corpus.industry else "",
                corpus.geography.value if corpus.geography else "",
                clause.category.value if hasattr(clause.category, 'value') else str(clause.category),
                clause.clause_text[:500],
                clause.risk_score,
                clause.is_favorable,
            ])

    from fastapi.responses import StreamingResponse
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=benchmarks.csv"},
    )


# ── Job Orchestration ──────────────────────────────────────────────


@router.post("/jobs/recompute", response_model=BenchmarkJobCreateResponse)
async def trigger_recompute(
    corpus_id: Optional[uuid.UUID] = Query(None, description="Specific corpus to recompute"),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.BENCHMARK_ADMIN)),
):
    """Trigger a full benchmark recompute as a background Celery task."""
    from app.workers.benchmark import recompute_benchmarks

    recompute_benchmarks.delay(
        tenant_id=user.tenant_id,
        corpus_id=str(corpus_id) if corpus_id else None,
        user_id=user.id,
    )

    return BenchmarkJobCreateResponse(
        job_id=uuid.uuid4(),
        job_type="recompute_scores",
        status="pending",
        message="Benchmark recompute submitted. Check /benchmarks/jobs for status.",
    )


@router.post("/jobs/refresh-embeddings", response_model=BenchmarkJobCreateResponse)
async def trigger_embedding_refresh(
    corpus_id: Optional[uuid.UUID] = Query(None, description="Specific corpus to refresh"),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.BENCHMARK_ADMIN)),
):
    """Trigger a full embedding refresh as a background Celery task."""
    from app.workers.benchmark import refresh_embeddings

    refresh_embeddings.delay(
        tenant_id=user.tenant_id,
        corpus_id=str(corpus_id) if corpus_id else None,
        user_id=user.id,
    )

    return BenchmarkJobCreateResponse(
        job_id=uuid.uuid4(),
        job_type="refresh_embeddings",
        status="pending",
        message="Embedding refresh submitted. Check /benchmarks/jobs for status.",
    )


@router.get("/jobs", response_model=BenchmarkJobListResponse)
async def list_jobs(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.BENCHMARK_READ)),
):
    """List recent benchmark orchestration jobs."""
    from app.domains.benchmark.models import BenchmarkJob, BenchmarkJobStatus

    result = await db.execute(
        select(BenchmarkJob).where(
            BenchmarkJob.tenant_id == uuid.UUID(user.tenant_id),
        ).order_by(BenchmarkJob.created_at.desc()).limit(limit)
    )
    jobs = list(result.scalars().all())

    return BenchmarkJobListResponse(
        items=[_job_to_response(j) for j in jobs],
        total=len(jobs),
    )


@router.get("/jobs/{job_id}", response_model=BenchmarkJobResponse)
async def get_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.BENCHMARK_READ)),
):
    """Get the status of a specific benchmark orchestration job."""
    from app.domains.benchmark.models import BenchmarkJob

    result = await db.execute(
        select(BenchmarkJob).where(
            BenchmarkJob.job_id == job_id,
            BenchmarkJob.tenant_id == uuid.UUID(user.tenant_id),
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return _job_to_response(job)


# ── Governance: Versioning ─────────────────────────────────────────


def _get_governance(db: AsyncSession, user: UserContext) -> CorpusGovernanceService:
    return CorpusGovernanceService(db, user.tenant_id)


def _get_lineage(db: AsyncSession, user: UserContext) -> LineageService:
    return LineageService(db, user.tenant_id)


@router.get("/corpora/{corpus_id}/versions", response_model=BenchmarkCorpusVersionListResponse)
async def list_corpus_versions(
    corpus_id: uuid.UUID,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.BENCHMARK_READ)),
):
    """List all versions/snapshots of a benchmark corpus."""
    gov = _get_governance(db, user)
    versions = await gov.list_versions(corpus_id, limit=limit)
    return BenchmarkCorpusVersionListResponse(
        items=[_version_to_response(v) for v in versions],
        total=len(versions),
    )


# ── Governance: Approval Workflow ──────────────────────────────────


@router.get("/corpora/{corpus_id}/approval", response_model=BenchmarkCorpusApprovalResponse)
async def get_corpus_approval(
    corpus_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.BENCHMARK_READ)),
):
    """Get the current approval state of a benchmark corpus."""
    gov = _get_governance(db, user)
    approval = await gov.get_approval(corpus_id)
    if not approval:
        raise HTTPException(status_code=404, detail="No approval record found for this corpus")
    return _approval_to_response(approval)


@router.post("/corpora/{corpus_id}/approval", response_model=BenchmarkCorpusApprovalResponse)
async def update_corpus_approval(
    corpus_id: uuid.UUID,
    body: ApprovalAction,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.BENCHMARK_ADMIN)),
):
    """Update the approval state of a benchmark corpus.

    Actions:
    - ``submit``: DRAFT → PENDING_REVIEW
    - ``approve``: PENDING_REVIEW → APPROVED
    - ``reject``: PENDING_REVIEW → REJECTED
    - ``archive``: any → ARCHIVED
    """
    from app.domains.benchmark.models import BenchmarkCorpus

    gov = _get_governance(db, user)

    if body.action == "submit":
        approval = await gov.submit_for_review(corpus_id, user.id, body.notes)
    elif body.action == "approve":
        approval = await gov.approve(corpus_id, user.id, body.notes)
        # Mark corpus as active on approval
        await db.execute(
            sa_update(BenchmarkCorpus).where(
                BenchmarkCorpus.corpus_id == corpus_id,
            ).values(is_active="true")
        )
    elif body.action == "reject":
        approval = await gov.reject(corpus_id, user.id, body.notes or "No reason provided")
    elif body.action == "archive":
        approval = await gov.archive(corpus_id)
        # Mark corpus as inactive on archive
        await db.execute(
            sa_update(BenchmarkCorpus).where(
                BenchmarkCorpus.corpus_id == corpus_id,
            ).values(is_active="false")
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {body.action}")

    await db.commit()
    return _approval_to_response(approval)


# ── Governance: Deduplication ──────────────────────────────────────


@router.post("/corpora/{corpus_id}/dedupe", response_model=BenchmarkDedupeReportListResponse)
async def run_dedupe_analysis(
    corpus_id: uuid.UUID,
    threshold: float = Query(0.85, ge=0.5, le=1.0, description="Similarity threshold"),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.BENCHMARK_ADMIN)),
):
    """Run deduplication analysis on a benchmark corpus.

    Scans all clause embeddings for near-duplicate pairs above the
    given similarity threshold. Creates dedupe report records.
    """
    gov = _get_governance(db, user)
    reports = await gov.run_dedupe_analysis(corpus_id, similarity_threshold=threshold)
    await db.commit()

    exact = sum(1 for r in reports if r.severity.value == "exact")
    near = sum(1 for r in reports if r.severity.value == "near")
    similar = sum(1 for r in reports if r.severity.value == "similar")

    return BenchmarkDedupeReportListResponse(
        items=[_dedupe_to_response(r) for r in reports],
        total=len(reports),
        exact_duplicates=exact,
        near_duplicates=near,
        similar_duplicates=similar,
    )


@router.get("/corpora/{corpus_id}/dedupe", response_model=BenchmarkDedupeReportListResponse)
async def list_dedupe_reports(
    corpus_id: uuid.UUID,
    severity: Optional[str] = Query(None, description="Filter by severity: exact, near, similar"),
    resolved: Optional[str] = Query(None, description="Filter by resolved state: true, false"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.BENCHMARK_READ)),
):
    """List deduplication reports for a corpus."""
    gov = _get_governance(db, user)
    reports = await gov.list_dedupe_reports(
        corpus_id=corpus_id,
        severity=severity,
        resolved=resolved,
        limit=limit,
    )

    exact = sum(1 for r in reports if r.severity.value == "exact")
    near = sum(1 for r in reports if r.severity.value == "near")
    similar = sum(1 for r in reports if r.severity.value == "similar")

    return BenchmarkDedupeReportListResponse(
        items=[_dedupe_to_response(r) for r in reports],
        total=len(reports),
        exact_duplicates=exact,
        near_duplicates=near,
        similar_duplicates=similar,
    )


@router.post("/dedupe/{report_id}/resolve", response_model=BenchmarkDedupeReportResponse)
async def resolve_dedupe_report(
    report_id: uuid.UUID,
    body: DedupeResolveRequest,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.BENCHMARK_ADMIN)),
):
    """Resolve a deduplication report.

    Actions:
    - ``merge``: Keep clause A, remove clause B
    - ``remove``: Remove clause B (the duplicate)
    - ``keep``: Keep both (false positive)
    - ``dismiss``: Mark as reviewed without action
    """
    gov = _get_governance(db, user)
    report = await gov.resolve_dedupe(report_id, body.action, body.notes)
    if not report:
        raise HTTPException(status_code=404, detail="Dedupe report not found")
    await db.commit()
    return _dedupe_to_response(report)


# ── Governance: Lineage ────────────────────────────────────────────


@router.get("/corpora/{corpus_id}/lineage", response_model=BenchmarkLineageListResponse)
async def list_corpus_lineage(
    corpus_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.BENCHMARK_READ)),
):
    """List recompute provenance records for a corpus."""
    svc = _get_lineage(db, user)
    records = await svc.list_lineage(corpus_id=corpus_id, limit=limit)
    return BenchmarkLineageListResponse(
        items=[_lineage_to_response(r) for r in records],
        total=len(records),
    )


# ── Helpers ────────────────────────────────────────────────────────


def _corpus_to_response(corpus) -> BenchmarkCorpusResponse:
    return BenchmarkCorpusResponse(
        corpus_id=corpus.corpus_id,
        name=corpus.name,
        description=corpus.description,
        source=corpus.source.value if hasattr(corpus.source, 'value') else str(corpus.source),
        industry=corpus.industry.value if corpus.industry else None,
        geography=corpus.geography.value if corpus.geography else None,
        contract_type=corpus.contract_type.value if corpus.contract_type else None,
        document_count=corpus.document_count or 0,
        clause_count=corpus.clause_count or 0,
        is_active=corpus.is_active,
        created_at=corpus.created_at,
        updated_at=corpus.updated_at,
    )


def _clause_to_response(clause) -> BenchmarkClauseResponse:
    return BenchmarkClauseResponse(
        clause_id=clause.clause_id,
        corpus_id=clause.corpus_id,
        category=clause.category.value if hasattr(clause.category, 'value') else str(clause.category),
        clause_text=clause.clause_text,
        clause_text_snippet=clause.clause_text_snippet,
        source_document=clause.source_document,
        risk_score=clause.risk_score,
        is_favorable=clause.is_favorable,
        created_at=clause.created_at,
    )


def _classify_risk(percentile: Optional[float]) -> str:
    if percentile is None:
        return "unknown"
    if percentile >= 90:
        return "critical"
    if percentile >= 75:
        return "high"
    if percentile >= 50:
        return "medium"
    if percentile >= 25:
        return "low"
    return "info"


def _job_to_response(job) -> BenchmarkJobResponse:
    """Convert a BenchmarkJob ORM model to a response schema."""
    return BenchmarkJobResponse(
        job_id=job.job_id,
        job_type=job.job_type.value if hasattr(job.job_type, 'value') else str(job.job_type),
        status=job.status.value if hasattr(job.status, 'value') else str(job.status),
        progress_pct=job.progress_pct or 0,
        progress_message=job.progress_message,
        error_message=job.error_message,
        items_processed=job.items_processed or 0,
        items_failed=job.items_failed or 0,
        items_total=job.items_total or 0,
        result_summary=job.result_summary,
        started_at=job.started_at,
        completed_at=job.completed_at,
        created_at=job.created_at,
    )


# ── Governance Helpers ─────────────────────────────────────────────


def _version_to_response(version) -> BenchmarkCorpusVersionResponse:
    return BenchmarkCorpusVersionResponse(
        version_id=version.version_id,
        corpus_id=version.corpus_id,
        version_number=version.version_number,
        version_label=version.version_label,
        clause_count=version.clause_count,
        change_description=version.change_description,
        created_by=version.created_by,
        job_id=version.job_id,
        created_at=version.created_at,
    )


def _approval_to_response(approval) -> BenchmarkCorpusApprovalResponse:
    return BenchmarkCorpusApprovalResponse(
        approval_id=approval.approval_id,
        corpus_id=approval.corpus_id,
        state=approval.state.value if hasattr(approval.state, 'value') else str(approval.state),
        submitted_by=approval.submitted_by,
        submitted_at=approval.submitted_at,
        reviewed_by=approval.reviewed_by,
        reviewed_at=approval.reviewed_at,
        review_notes=approval.review_notes,
        created_at=approval.created_at,
        updated_at=approval.updated_at,
    )


def _dedupe_to_response(report) -> BenchmarkDedupeReportResponse:
    return BenchmarkDedupeReportResponse(
        report_id=report.report_id,
        corpus_id=report.corpus_id,
        severity=report.severity.value if hasattr(report.severity, 'value') else str(report.severity),
        clause_id_a=report.clause_id_a,
        clause_id_b=report.clause_id_b,
        similarity_score=report.similarity_score,
        clause_category=report.clause_category.value if hasattr(report.clause_category, 'value') else str(report.clause_category) if report.clause_category else None,
        detected_by=report.detected_by,
        resolved=report.resolved,
        resolution_action=report.resolution_action,
        created_at=report.created_at,
    )


def _lineage_to_response(record) -> BenchmarkLineageResponse:
    return BenchmarkLineageResponse(
        lineage_id=record.lineage_id,
        corpus_id=record.corpus_id,
        corpus_version_id=record.corpus_version_id,
        job_id=record.job_id,
        operation=record.operation,
        score_count_affected=record.score_count_affected,
        corpus_clause_count=record.corpus_clause_count,
        previous_lineage_id=record.previous_lineage_id,
        delta_summary=record.delta_summary,
        created_by=record.created_by,
        created_at=record.created_at,
    )
