"""Benchmark orchestration Celery tasks — recompute, refresh, stale detection, export, and governance.

Provides the operational lifecycle for the benchmark subsystem:

- ``recompute_benchmarks`` — Recompute all percentile scores for a corpus
- ``refresh_embeddings`` — Regenerate embeddings for all clauses in a corpus
- ``detect_stale_scores`` — Find and flag scores based on stale corpus data
- ``export_benchmarks_async`` — Generate a CSV export as a background job

Each task creates a ``BenchmarkJob`` record for tracking and observability.
Tasks that modify corpus data also create version snapshots and lineage records.
"""

from __future__ import annotations

import csv
import io
import logging
import uuid
from datetime import datetime, timedelta, timezone

from celery import shared_task
from sqlalchemy import select, func, delete, text as sa_text

from app.config import settings
from app.domains.benchmark.models import (
    BenchmarkCorpus,
    BenchmarkClause,
    BenchmarkScore,
    BenchmarkJob,
    BenchmarkJobType,
    BenchmarkJobStatus,
    BenchmarkLineage,
)
from app.domains.benchmark.engine import BenchmarkEngine
from app.domains.vectors.services.embedding_service import EmbeddingService
from workers.worker_loop import worker_loop

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
STALE_AFTER_DAYS = 7  # Scores older than this are considered stale


# ── Helpers ────────────────────────────────────────────────────────


async def _create_job(
    tenant_id: str,
    job_type: BenchmarkJobType,
    corpus_id: uuid.UUID | None = None,
    upload_id: uuid.UUID | None = None,
) -> BenchmarkJob | None:
    """Create a new BenchmarkJob record and return it.

    Returns ``None`` if the benchmark_jobs table does not exist
    (graceful degradation for un-migrated databases).
    """
    session = await worker_loop.create_session(tenant_id, "system", "worker")
    try:
        job = BenchmarkJob(
            job_id=uuid.uuid4(),
            tenant_id=uuid.UUID(tenant_id),
            job_type=job_type,
            status=BenchmarkJobStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
            corpus_id=corpus_id,
            upload_id=upload_id,
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return job
    except Exception as exc:
        await session.rollback()
        # Graceful degradation: if the table doesn't exist, log and return None
        if "does not exist" in str(exc) or "UndefinedTable" in str(exc):
            logger.warning(
                "[Benchmark] benchmark_jobs table not found — skipping job tracking "
                "(run 'alembic upgrade head' to create it): %s",
                exc,
            )
            return None
        raise
    finally:
        await session.close()


async def _complete_job(job: BenchmarkJob, session) -> None:
    """Mark a job as completed with timing."""
    job.status = BenchmarkJobStatus.COMPLETED
    job.completed_at = datetime.now(timezone.utc)
    job.progress_pct = 100


async def _fail_job(job: BenchmarkJob, session, error: str, details: dict | None = None) -> None:
    """Mark a job as failed with error context."""
    job.status = BenchmarkJobStatus.FAILED
    job.completed_at = datetime.now(timezone.utc)
    job.error_message = str(error)[:2000]
    if details:
        job.error_details = details


async def _update_progress(job: BenchmarkJob, session, pct: int, message: str) -> None:
    """Update job progress."""
    job.progress_pct = min(100, max(0, pct))
    job.progress_message = message


def _run_for_all_active_tenants(runner, *, label: str) -> dict:
    """Run a per-tenant benchmark job for every active tenant (Celery Beat entry)."""
    from app.kernel.database.sync_session import get_sync_factory

    factory = get_sync_factory()
    session = factory.create_session(tenant_id="system", user_id="system", user_role="admin")
    try:
        rows = session.execute(
            sa_text("SELECT tenant_id FROM tenants WHERE is_active = TRUE")
        ).fetchall()
    finally:
        session.close()

    results: dict[str, object] = {}
    for (tenant_id,) in rows:
        tenant_id_str = str(tenant_id)
        try:
            results[tenant_id_str] = runner(tenant_id_str)
        except Exception as exc:
            logger.exception("[Benchmark] %s failed for tenant %s", label, tenant_id_str)
            results[tenant_id_str] = {"status": "failed", "error": str(exc)}

    return {"status": "completed", "tenants": len(results), "results": results}


# ── Task: Recompute Benchmarks ─────────────────────────────────────


@shared_task(
    name="benchmark.recompute",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=MAX_RETRIES,
    acks_late=True,
)
def recompute_benchmarks(
    tenant_id: str | None = None,
    corpus_id: str | None = None,
    user_id: str = "system",
):
    """Recompute all benchmark percentile scores for a tenant's corpus.

    If ``corpus_id`` is provided, only that corpus is recomputed.
    Otherwise, all active corpora for the tenant are processed.

    When ``tenant_id`` is omitted (Celery Beat), runs for all active tenants.

    This is the primary score-freshness mechanism.  Should be scheduled
    nightly via Celery Beat.
    """
    if tenant_id is not None:
        return worker_loop.run(_recompute_async(tenant_id, corpus_id, user_id))
    return _run_for_all_active_tenants(
        lambda tid: worker_loop.run(_recompute_async(tid, corpus_id, user_id)),
        label="Recompute",
    )


async def _recompute_async(
    tenant_id: str,
    corpus_id: str | None,
    user_id: str,
) -> dict:
    """Async implementation of recompute_benchmarks."""
    from app.domains.benchmark.governance import CorpusGovernanceService, LineageService

    job = await _create_job(tenant_id, BenchmarkJobType.RECOMPUTE_SCORES)
    session = await worker_loop.create_session(tenant_id, user_id, "worker")
    engine = BenchmarkEngine(session, tenant_id)
    gov = CorpusGovernanceService(session, tenant_id)
    lineage_svc = LineageService(session, tenant_id)

    try:
        # Gather target corpora
        if corpus_id:
            corpora = [await engine.get_corpus(uuid.UUID(corpus_id))]
            corpora = [c for c in corpora if c]
        else:
            corpora = await engine.list_corpora()

        if not corpora:
            if job is not None:
                await _update_progress(job, session, 100, "No corpora to recompute")
                await _complete_job(job, session)
                await session.commit()
            return {"status": "skipped", "reason": "no corpora"}

        # Load all scores grouped by (corpus_id, category)
        total_categories = 0
        processed = 0

        for corpus in corpora:
            # Get distinct categories that have scores for this corpus
            score_categories = await session.execute(
                select(BenchmarkScore.category).where(
                    BenchmarkScore.corpus_id == corpus.corpus_id,
                    BenchmarkScore.tenant_id == uuid.UUID(tenant_id),
                ).distinct()
            )
            categories = [row[0] for row in score_categories.fetchall()]
            total_categories += len(categories)

        if job is not None:
            job.items_total = total_categories
            await session.flush()

        # Create version snapshot and lineage before recompute
        for corpus in corpora:
            version = await gov.create_version_snapshot(
                corpus_id=corpus.corpus_id,
                change_description="Pre-recompute snapshot",
                created_by=f"job:{job.job_id}" if job else "system",
                job_id=job.job_id if job else None,
            )

            # Count total clauses in corpus
            clause_count_result = await session.execute(
                select(func.count(BenchmarkClause.clause_id)).where(
                    BenchmarkClause.corpus_id == corpus.corpus_id,
                    BenchmarkClause.tenant_id == uuid.UUID(tenant_id),
                )
            )
            corpus_clause_count = clause_count_result.scalar() or 0

            # Record lineage
            await lineage_svc.record_recompute(
                corpus_id=corpus.corpus_id,
                corpus_version_id=version.version_id,
                job_id=job.job_id if job else None,
                operation="recompute",
                score_count_affected=0,  # Updated after processing
                corpus_clause_count=corpus_clause_count,
                created_by=f"job:{job.job_id}" if job else "system",
            )

        # Recompute scores per corpus
        for corpus in corpora:
            # Get all distinct upload_ids that have scores for this corpus
            upload_ids_result = await session.execute(
                select(BenchmarkScore.upload_id).where(
                    BenchmarkScore.corpus_id == corpus.corpus_id,
                    BenchmarkScore.tenant_id == uuid.UUID(tenant_id),
                ).distinct()
            )
            upload_ids = [row[0] for row in upload_ids_result.fetchall()]

            for upload_id in upload_ids:
                # Get existing scores for this upload + corpus
                existing_scores = await session.execute(
                    select(BenchmarkScore).where(
                        BenchmarkScore.upload_id == upload_id,
                        BenchmarkScore.corpus_id == corpus.corpus_id,
                        BenchmarkScore.tenant_id == uuid.UUID(tenant_id),
                    )
                )
                score_records = list(existing_scores.scalars().all())

                if not score_records:
                    continue

                # Build clause_score tuples from persisted scores
                clause_scores = [
                    (s.category.value if hasattr(s.category, 'value') else str(s.category), s.your_score)
                    for s in score_records
                ]

                # Recompute percentiles (returns updated score_data dicts)
                results = await engine.compute_percentile(
                    upload_id=upload_id,
                    corpus_id=corpus.corpus_id,
                    clause_scores=clause_scores,
                )

                # Update persisted scores with new percentile values
                for result in results:
                    category_str = result["category"]
                    for score_record in score_records:
                        rec_cat = score_record.category.value if hasattr(score_record.category, 'value') else str(score_record.category)
                        if rec_cat == category_str:
                            score_record.percentile = result["percentile"]
                            score_record.market_median = result["market_median"]
                            score_record.market_p25 = result.get("market_p25")
                            score_record.market_p75 = result.get("market_p75")
                            score_record.market_mean = result.get("market_mean")
                            score_record.market_stddev = result.get("market_stddev")
                            score_record.deviation = result.get("deviation")
                            score_record.deviation_percent = result.get("deviation_percent")
                            score_record.direction = result.get("direction")
                            score_record.sample_size = result["sample_size"]
                            score_record.confidence = result.get("confidence")
                            break

                processed += len(results)
                if job is not None:
                    pct = int((processed / max(total_categories, 1)) * 100)
                    await _update_progress(
                        job, session, pct,
                        f"Recomputed {processed}/{total_categories} score groups",
                    )

        if job is not None:
            job.items_processed = processed

            # Update lineage with actual score count
            for corpus in corpora:
                latest_lineage = await session.execute(
                    select(BenchmarkLineage).where(
                        BenchmarkLineage.corpus_id == corpus.corpus_id,
                        BenchmarkLineage.job_id == job.job_id,
                    ).order_by(BenchmarkLineage.created_at.desc()).limit(1)
                )
                lineage_record = latest_lineage.scalar_one_or_none()
                if lineage_record:
                    lineage_record.score_count_affected = processed

            await _complete_job(job, session)
            await session.commit()

        logger.info(
            "[Benchmark] Recomputed %d score groups across %d corpora for tenant %s",
            processed, len(corpora), tenant_id,
        )
        return {"status": "completed", "corpora": len(corpora), "scores_recomputed": processed}

    except Exception as exc:
        await session.rollback()
        if job is not None:
            try:
                await _fail_job(job, session, str(exc))
                await session.commit()
            except Exception:
                logger.exception("[Benchmark] Failed to persist job failure for tenant %s", tenant_id)
        logger.exception("[Benchmark] Recompute failed for tenant %s", tenant_id)
        raise


# ── Task: Refresh Embeddings ───────────────────────────────────────


@shared_task(
    name="benchmark.refresh_embeddings",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=MAX_RETRIES,
    acks_late=True,
)
def refresh_embeddings(
    tenant_id: str | None = None,
    corpus_id: str | None = None,
    user_id: str = "system",
):
    """Regenerate embeddings for all clauses in a benchmark corpus.

    If ``corpus_id`` is provided, only that corpus is refreshed.
    Otherwise, all active corpora for the tenant are processed.

    When ``tenant_id`` is omitted (Celery Beat), runs for all active tenants.

    Should be scheduled weekly or triggered after an embedding model upgrade.
    """
    if tenant_id is not None:
        return worker_loop.run(_refresh_embeddings_async(tenant_id, corpus_id, user_id))
    return _run_for_all_active_tenants(
        lambda tid: worker_loop.run(_refresh_embeddings_async(tid, corpus_id, user_id)),
        label="Embedding refresh",
    )


async def _refresh_embeddings_async(
    tenant_id: str,
    corpus_id: str | None,
    user_id: str,
) -> dict:
    """Async implementation of refresh_embeddings."""
    job = await _create_job(tenant_id, BenchmarkJobType.REFRESH_EMBEDDINGS)
    session = await worker_loop.create_session(tenant_id, user_id, "worker")
    embedding_service = EmbeddingService(
        api_key=settings.openai_api_key,
        model=settings.default_embedding_model,
    )

    try:
        # Gather target clauses
        query = select(BenchmarkClause).where(
            BenchmarkClause.tenant_id == uuid.UUID(tenant_id),
        )
        if corpus_id:
            query = query.where(BenchmarkClause.corpus_id == uuid.UUID(corpus_id))
        result = await session.execute(query)
        clauses = list(result.scalars().all())

        if not clauses:
            if job is not None:
                await _update_progress(job, session, 100, "No clauses to refresh")
                await _complete_job(job, session)
                await session.commit()
            return {"status": "skipped", "reason": "no clauses"}

        if job is not None:
            job.items_total = len(clauses)
            await session.flush()

        processed = 0
        failed = 0

        for clause in clauses:
            try:
                embedding = await embedding_service.embed_text(clause.clause_text)
                if embedding:
                    clause.embedding = embedding
                    processed += 1
                else:
                    failed += 1
            except Exception as exc:
                logger.warning(
                    "[Benchmark] Embedding refresh failed for clause %s: %s",
                    clause.clause_id, exc,
                )
                failed += 1

            if job is not None:
                pct = int(((processed + failed) / len(clauses)) * 100)
                await _update_progress(
                    job, session, pct,
                    f"Refreshed {processed}/{len(clauses)} embeddings ({failed} failed)",
                )

        if job is not None:
            job.items_processed = processed
            job.items_failed = failed
            await _complete_job(job, session)
            await session.commit()

        logger.info(
            "[Benchmark] Refreshed %d embeddings for tenant %s (%d failed)",
            processed, tenant_id, failed,
        )
        return {"status": "completed", "refreshed": processed, "failed": failed}

    except Exception as exc:
        await session.rollback()
        if job is not None:
            try:
                await _fail_job(job, session, str(exc))
                await session.commit()
            except Exception:
                logger.exception("[Benchmark] Failed to persist job failure for tenant %s", tenant_id)
        logger.exception("[Benchmark] Embedding refresh failed for tenant %s", tenant_id)
        raise


# ── Task: Detect Stale Scores ──────────────────────────────────────


@shared_task(
    name="benchmark.detect_stale",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=MAX_RETRIES,
    acks_late=True,
)
def detect_stale_scores(
    tenant_id: str | None = None,
    stale_after_days: int = STALE_AFTER_DAYS,
):
    """Detect and flag benchmark scores that are based on stale corpus data.

    A score is considered stale if:
    1. The score record is older than ``stale_after_days``
    2. The corpus has been updated (new clauses added) since the score was computed
    3. The embedding model version has changed (future: checked via metadata)

    When ``tenant_id`` is omitted (Celery Beat), runs for all active tenants.

    This task does NOT modify scores — it returns a report of stale entries
    for review.  Use ``recompute_benchmarks`` to refresh stale scores.
    """
    if tenant_id is not None:
        return worker_loop.run(_detect_stale_async(tenant_id, stale_after_days))
    return _run_for_all_active_tenants(
        lambda tid: worker_loop.run(_detect_stale_async(tid, stale_after_days)),
        label="Stale detection",
    )


async def _detect_stale_async(
    tenant_id: str,
    stale_after_days: int,
) -> dict:
    """Async implementation of detect_stale_scores."""
    job = await _create_job(tenant_id, BenchmarkJobType.STALE_DETECTION)
    session = await worker_loop.create_session(tenant_id, "system", "worker")

    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=stale_after_days)

        # Find scores older than the cutoff
        stale_scores = await session.execute(
            select(BenchmarkScore).where(
                BenchmarkScore.tenant_id == uuid.UUID(tenant_id),
                BenchmarkScore.created_at < cutoff,
            ).order_by(BenchmarkScore.created_at)
        )
        scores = list(stale_scores.scalars().all())

        # Also find scores where the corpus has newer clauses than the score
        corpus_stale = []
        for score in scores:
            corpus = await session.execute(
                select(BenchmarkCorpus).where(
                    BenchmarkCorpus.corpus_id == score.corpus_id,
                )
            )
            corpus_row = corpus.scalar_one_or_none()
            if corpus_row and corpus_row.updated_at and score.created_at:
                if corpus_row.updated_at > score.created_at:
                    corpus_stale.append(str(score.score_id))

        if job is not None:
            job.items_processed = len(scores)
            job.items_failed = len(corpus_stale)
            job.result_summary = {
                "total_stale": len(scores),
                "corpus_updated_since_score": len(corpus_stale),
                "stale_score_ids": [str(s.score_id) for s in scores[:100]],  # First 100
                "stale_after_days": stale_after_days,
                "cutoff_date": cutoff.isoformat(),
            }
            await _complete_job(job, session)
            await session.commit()

        logger.info(
            "[Benchmark] Detected %d stale scores for tenant %s (%d corpus-updated)",
            len(scores), tenant_id, len(corpus_stale),
        )
        return {
            "status": "completed",
            "stale_scores": len(scores),
            "corpus_updated_since_score": len(corpus_stale),
        }

    except Exception as exc:
        await session.rollback()
        if job is not None:
            try:
                await _fail_job(job, session, str(exc))
                await session.commit()
            except Exception:
                logger.exception("[Benchmark] Failed to persist job failure for tenant %s", tenant_id)
        logger.exception("[Benchmark] Stale detection failed for tenant %s", tenant_id)
        raise


# ── Task: Async CSV Export ─────────────────────────────────────────


@shared_task(
    name="benchmark.export_csv",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=MAX_RETRIES,
    acks_late=True,
)
def export_benchmarks_async(
    tenant_id: str,
    corpus_id: str | None = None,
    user_id: str = "system",
):
    """Generate a CSV export of benchmark data as a background job.

    The resulting CSV content is stored in the job's ``result_summary``.
    A separate endpoint can retrieve the completed export.
    """
    return worker_loop.run(_export_csv_async(tenant_id, corpus_id, user_id))


async def _export_csv_async(
    tenant_id: str,
    corpus_id: str | None,
    user_id: str,
) -> dict:
    """Async implementation of export_benchmarks_async."""
    job = await _create_job(tenant_id, BenchmarkJobType.EXPORT_CSV)
    session = await worker_loop.create_session(tenant_id, user_id, "worker")
    engine = BenchmarkEngine(session, tenant_id)

    try:
        # Gather corpora
        if corpus_id:
            corpora = [await engine.get_corpus(uuid.UUID(corpus_id))]
            corpora = [c for c in corpora if c]
        else:
            corpora = await engine.list_corpora()

        if not corpora:
            if job is not None:
                await _update_progress(job, session, 100, "No corpora to export")
                await _complete_job(job, session)
                await session.commit()
            return {"status": "skipped", "reason": "no corpora"}

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Corpus Name", "Industry", "Geography", "Contract Type",
            "Clause Category", "Clause Text", "Risk Score",
            "Favorable", "Document Source",
        ])

        total_clauses = 0
        for corpus in corpora:
            clauses = await engine.get_corpus_clauses(corpus.corpus_id)
            for clause in clauses:
                writer.writerow([
                    corpus.name,
                    corpus.industry.value if corpus.industry else "",
                    corpus.geography.value if corpus.geography else "",
                    corpus.contract_type.value if corpus.contract_type else "",
                    clause.category.value if hasattr(clause.category, 'value') else str(clause.category),
                    clause.clause_text[:500],
                    clause.risk_score,
                    clause.is_favorable,
                    clause.source_document or "",
                ])
                total_clauses += 1

        csv_content = output.getvalue()
        output.close()

        if job is not None:
            job.items_processed = total_clauses
            job.result_summary = {
                "csv_size_bytes": len(csv_content),
                "row_count": total_clauses + 1,  # +1 for header
                "corpus_count": len(corpora),
                "csv_content": csv_content,  # Stored for retrieval — large exports should use S3
            }
            await _complete_job(job, session)
            await session.commit()

        logger.info(
            "[Benchmark] Exported %d rows for tenant %s",
            total_clauses + 1, tenant_id,
        )
        return {
            "status": "completed",
            "rows": total_clauses + 1,
            "corpora": len(corpora),
        }

    except Exception as exc:
        await session.rollback()
        if job is not None:
            try:
                await _fail_job(job, session, str(exc))
                await session.commit()
            except Exception:
                logger.exception("[Benchmark] Failed to persist job failure for tenant %s", tenant_id)
        logger.exception("[Benchmark] CSV export failed for tenant %s", tenant_id)
        raise
