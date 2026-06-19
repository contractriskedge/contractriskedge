"""AI analysis Celery worker — executes analysis pipeline asynchronously.

Review population (ContractReview + review_findings + review_redlines)
now happens inside ``AIService.analyze()`` to ensure it runs in the same
session/transaction as the AI analysis.

Concurrent analysis limiting:
- Uses Redis INCR/DECR with 300s TTL to track active analyses per tenant.
- Prevents double-decrement via ``acquired_slot`` boolean guard.
- Falls back gracefully if Redis is unavailable (allows analysis through).
"""

from __future__ import annotations

import logging
import random
from typing import Optional

from app.config import settings
from app.domains.ai.llm import OpenAIProvider, RateLimitError, QuotaExceededError, parse_openai_retry_after
from app.domains.ai.providers.registry import llm_registry
from app.domains.ai.repository import AIRepository
from app.domains.ai.service import AIService
from app.domains.vectors.repository import VectorRepository
from app.domains.ingestion.repository import IngestionRepository
from app.kernel.events.bus import EventBus
from app.kernel.database.session_utils import safe_session_rollback
from workers.worker_async import WorkerAsyncHelper
from workers.worker_loop import worker_loop

logger = logging.getLogger(__name__)

MAX_RETRIES = 8

# Redis key prefix for active analysis tracking
_ACTIVE_ANALYSIS_KEY = "ai_active:{}"
_CONCURRENCY_TTL = 300  # 5 minutes — safety release for crashed workers


class MaxConcurrentAnalysisError(Exception):
    """Raised when tenant has reached the maximum number of concurrent analyses."""


async def _acquire_concurrency_slot(tenant_id: str) -> bool:
    """Try to acquire a concurrency slot for this tenant.

    Uses Redis INCR + EXPIRE in a pipeline. Returns True if slot acquired,
    False if at capacity. Falls back to True if Redis is unavailable.
    """
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=2,
        )
        key = _ACTIVE_ANALYSIS_KEY.format(tenant_id)
        pipe = r.pipeline()
        pipe.incr(key)
        pipe.expire(key, _CONCURRENCY_TTL)
        results = await pipe.execute()
        count = results[0]
        max_concurrent = settings.effective_max_concurrent
        if count > max_concurrent:
            # Slot not available — decrement the counter we just incremented
            await r.decr(key)
            await r.close()
            logger.info(
                "Concurrency slot full for tenant %s: %d active (max=%d).",
                tenant_id, count - 1, max_concurrent,
            )
            return False

        logger.info(
            "Concurrency slot acquired for tenant %s: %d/%d active.",
            tenant_id, count, max_concurrent,
        )
        await r.close()
        return True
    except Exception as exc:
        logger.warning("Redis unavailable for concurrency tracking: %s — allowing analysis through", exc)
        return True  # Fail open: allow analysis if Redis is down


async def _release_concurrency_slot(tenant_id: str) -> None:
    """Release a concurrency slot. Safe to call even if slot was not acquired."""
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=2,
        )
        key = _ACTIVE_ANALYSIS_KEY.format(tenant_id)
        await r.decr(key)
        await r.close()
    except Exception:
        pass  # Non-critical: slot will expire via TTL


from app.kernel.database.orm_registry import register_orm_models
from workers.celery_app import celery_app

register_orm_models()


def dispatch_analyze_contract(
    upload_id: str,
    tenant_id: str,
    user_id: str | None = None,
    analysis_type: str = "full",
    *,
    stagger: bool = True,
) -> None:
    """Queue AI analysis, optionally staggering dispatch to reduce API rate-limit bursts."""
    countdown = random.randint(30, 180) if stagger else 0
    analyze_contract_task.apply_async(
        kwargs={
            "upload_id": upload_id,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "analysis_type": analysis_type,
        },
        countdown=countdown,
    )


@celery_app.task(
    bind=True,
    name="analyze_contract",
    max_retries=MAX_RETRIES,
    acks_late=True,
)
def analyze_contract_task(self, upload_id: str, tenant_id: str,
                           user_id: str = None, analysis_type: str = "full",
                           preserve_redline_ids: list = None,
                           preserve_finding_ids: list = None):
    """Execute AI analysis on a contract's chunks.

    Enforces per-tenant concurrent analysis limit using Redis INCR/DECR.
    If the limit is reached, the task retries after ``ai_concurrency_retry_seconds``.
    Uses ``acquired_slot`` boolean to prevent double-decrement on error paths.
    """
    helper = WorkerAsyncHelper()
    return helper.run(_analyze_contract(helper, self, upload_id, tenant_id, user_id, analysis_type,
                                         preserve_redline_ids, preserve_finding_ids))


async def _analyze_contract(helper: WorkerAsyncHelper, task, upload_id: str, tenant_id: str,
                             user_id: str = None, analysis_type: str = "full",
                             preserve_redline_ids: list = None,
                             preserve_finding_ids: list = None):
    acquired_slot = False
    session = await worker_loop.create_session(tenant_id, user_id or "system", "api")
    async with helper.session_scope(session):
        try:
            # ── Concurrent analysis limit ─────────────────────────
            acquired_slot = await _acquire_concurrency_slot(tenant_id)
            if not acquired_slot:
                logger.info(
                    "Concurrent analysis limit reached for tenant %s "
                    "(max=%d). Using exponential backoff.",
                    tenant_id,
                    settings.effective_max_concurrent,
                )
                raise MaxConcurrentAnalysisError(
                    f"Tenant {tenant_id} has reached max concurrent analyses "
                    f"({settings.effective_max_concurrent})."
                )

            provider = OpenAIProvider(api_key=settings.openai_api_key)
            llm_registry.register(provider)

            # Register DeepSeek as fallback if API key is configured
            if settings.deepseek_api_key:
                from app.domains.ai.llm import DeepSeekProvider
                deepseek = DeepSeekProvider(api_key=settings.deepseek_api_key)
                llm_registry.register(deepseek)
                logger.info(
                    "DeepSeek provider registered as fallback (order=%s)",
                    settings.ai_provider_fallback_order,
                )

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

        except MaxConcurrentAnalysisError:
            await safe_session_rollback(session)
            # Exponential backoff with jitter: 5s, 10s, 20s, capped at max
            # Jitter prevents thundering herd when many contracts retry simultaneously.
            retries = getattr(task, "request", None)
            attempt = retries.retries if retries else 0
            base = min(5 * (2 ** attempt), settings.ai_concurrency_retry_seconds)
            jitter = random.uniform(0, base * 0.3)  # Up to 30% jitter
            backoff = base + jitter
            logger.info(
                "Concurrency slot unavailable for tenant %s "
                "(attempt=%d, backoff=%.1fs, max=%d, active_slots=%s).",
                tenant_id, attempt + 1, backoff,
                settings.effective_max_concurrent,
                _ACTIVE_ANALYSIS_KEY.format(tenant_id),
            )
            raise task.retry(countdown=backoff)

        except RateLimitError as exc:
            await safe_session_rollback(session)
            retry_after = exc.retry_after_seconds or parse_openai_retry_after(str(exc)) or 20.0
            jitter = random.uniform(1, retry_after * 0.25)
            countdown = retry_after + jitter + 2
            retries = getattr(task, "request", None)
            attempt = retries.retries if retries else 0
            logger.warning(
                "OpenAI rate limit for upload %s — retry in %.1fs (attempt %d/%d): %s",
                upload_id, countdown, attempt + 1, MAX_RETRIES, exc,
            )
            raise task.retry(countdown=countdown, exc=exc)

        except QuotaExceededError as exc:
            await safe_session_rollback(session)
            logger.error(
                "OpenAI quota exceeded for upload %s — not retrying: %s",
                upload_id, exc,
            )
            try:
                fail_session = await worker_loop.create_session(tenant_id, user_id or "system", "api")
                from app.domains.ai.models import ExecutionStatus
                ai_repo = AIRepository(fail_session, tenant_id=tenant_id)
                run = await ai_repo.get_latest_run_for_upload(upload_id, tenant_id)
                if run and run.status in (ExecutionStatus.PROCESSING, ExecutionStatus.PENDING):
                    await ai_repo.fail_run(
                        run.run_id,
                        "OpenAI quota exceeded — check billing at platform.openai.com",
                    )
                    await fail_session.commit()
                await fail_session.close()
            except Exception as mark_err:
                logger.error("Failed to mark quota-exceeded run as FAILED: %s", mark_err)
            raise

        except Exception as exc:
            await safe_session_rollback(session)
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
                        await safe_session_rollback(fail_session)
                        await fail_session.close()
                    except Exception:
                        pass
            raise

        finally:
            # ── Release concurrency slot ──────────────────────────
            # Only DECR if we actually acquired the slot.
            # The acquired_slot boolean prevents double-decrement when
            # MaxConcurrentAnalysisError is caught and re-raised via retry().
            if acquired_slot:
                await _release_concurrency_slot(tenant_id)
