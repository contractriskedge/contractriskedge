"""AI analysis Celery worker — executes analysis pipeline asynchronously.

Review population (ContractReview + review_findings + review_redlines)
now happens inside ``AIService.analyze()`` to ensure it runs in the same
session/transaction as the AI analysis.
"""

from __future__ import annotations

import logging

from app.config import settings
from app.domains.ai.llm import OpenAIProvider
from app.domains.ai.providers.registry import llm_registry
from app.domains.ai.repository import AIRepository
from app.domains.ai.service import AIService
from app.domains.vectors.repository import VectorRepository
from app.domains.ingestion.repository import IngestionRepository
from app.kernel.events.bus import EventBus
from workers.worker_async import WorkerAsyncHelper
from workers.worker_loop import worker_loop

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


from app.kernel.database.orm_registry import register_orm_models
from workers.celery_app import celery_app

register_orm_models()


@celery_app.task(
    bind=True,
    name="analyze_contract",
    max_retries=MAX_RETRIES,
    acks_late=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
)
def analyze_contract_task(self, upload_id: str, tenant_id: str,
                           user_id: str = None, analysis_type: str = "full",
                           preserve_redline_ids: list = None,
                           preserve_finding_ids: list = None):
    """Execute AI analysis on a contract's chunks.

    Triggered after EMBEDDING_PENDING → ANALYSIS_PENDING state.
    Transitions to REVIEW_READY or FAILED.
    After successful analysis, auto-creates/updates the ContractReview
    and populates review_findings / review_redlines.
    """
    helper = WorkerAsyncHelper()
    return helper.run(_analyze_contract(helper, self, upload_id, tenant_id, user_id, analysis_type,
                                         preserve_redline_ids, preserve_finding_ids))


async def _analyze_contract(helper: WorkerAsyncHelper, task, upload_id: str, tenant_id: str,
                             user_id: str = None, analysis_type: str = "full",
                             preserve_redline_ids: list = None,
                             preserve_finding_ids: list = None):
    session = await worker_loop.create_session(tenant_id, user_id or "system", "api")
    async with helper.session_scope(session):
        try:
            provider = OpenAIProvider(api_key=settings.openai_api_key)
            llm_registry.register(provider)

            service = AIService(
                ai_repo=AIRepository(session, tenant_id=tenant_id),
                vector_repo=VectorRepository(session, tenant_id=tenant_id),
                ingest_repo=IngestionRepository(session, tenant_id=tenant_id),
                event_bus=EventBus(),
                user=None,
                tenant_id=tenant_id,
            )

            result = await service.analyze(
                upload_id, analysis_type, force=True,
                preserve_redline_ids=preserve_redline_ids,
                preserve_finding_ids=preserve_finding_ids,
            )
            # Review population happens inside service.analyze() in the same transaction

            await session.commit()

            logger.info("AI analysis complete: upload=%s risk=%.4f findings=%d redlines=%d",
                         upload_id, result.risk_score, len(result.findings), len(result.redlines))

        except Exception as exc:
            await session.rollback()
            logger.error("AI analysis failed for %s: %s", upload_id, exc)

            # Mark the AI run as FAILED in DB after retries exhausted
            # so the recovery daemon doesn't need to wait 30 min to detect it.
            retries = getattr(task, "request", None)
            retry_count = retries.retries if retries else 0
            if retry_count >= MAX_RETRIES - 1:
                try:
                    # Create a fresh session for failure marking to avoid
                    # reusing an aborted transaction from the failed analysis.
                    fail_session = await worker_loop.create_session(tenant_id, user_id or "system", "api")
                    from app.domains.ai.models import ExecutionStatus
                    ai_repo = AIRepository(fail_session, tenant_id=tenant_id)
                    run = await ai_repo.get_latest_run_for_upload(upload_id, tenant_id)
                    if run and run.status in (ExecutionStatus.PROCESSING, ExecutionStatus.PENDING):
                        await ai_repo.fail_run(run.run_id, f"Max retries exhausted: {exc}")
                        await fail_session.commit()
                        logger.warning("Marked AI run %s as FAILED after retry exhaustion", run.run_id)
                    await fail_session.close()
                except Exception as mark_err:
                    logger.error("Failed to mark AI run as FAILED: %s", mark_err)
                    try:
                        await fail_session.rollback()
                        await fail_session.close()
                    except Exception:
                        pass
            raise
