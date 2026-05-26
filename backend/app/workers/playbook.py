"""Celery tasks for Legal Playbook + Policy Engine.

Tasks:
- evaluate_contract_policies_task: Full policy evaluation for a contract
- detect_clause_deviations_task: Re-detect deviations after playbook changes
- generate_clause_recommendations_task: Generate clause recommendations for a review
- reevaluate_playbook_changes_task: Re-evaluate all contracts affected by playbook changes
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from app.domains.playbook.engine import PolicyEngine, EvaluationContext, ExtractedClause
from app.domains.playbook.repository import PlaybookRepository
from app.domains.playbook.service import PlaybookService, AIPolicyInjectionService
from app.kernel.events.bus import EventBus

logger = logging.getLogger(__name__)

# Celery app will be imported at runtime
try:
    from app.workers.celery_app import celery_app
except ImportError:
    # Fallback for when celery is not configured
    celery_app = None


def _get_task_id() -> str:
    """Get current task ID from Celery context."""
    try:
        from celery import current_task
        return current_task.request.id or "unknown"
    except (ImportError, AttributeError, RuntimeError):
        return "unknown"


if celery_app:

    @celery_app.task(
        name="playbook.evaluate_contract_policies",
        bind=True,
        max_retries=3,
        default_retry_delay=30,
        acks_late=True,
        reject_on_worker_lost=True,
        queue="playbook",
    )
    def evaluate_contract_policies_task(
        self,
        upload_id: str,
        playbook_id: str,
        tenant_id: str,
        review_id: Optional[str] = None,
        contract_value: Optional[float] = None,
        jurisdiction: Optional[str] = None,
        industry: Optional[str] = None,
        risk_score: Optional[float] = None,
        clauses: Optional[list[dict]] = None,
        findings: Optional[list[dict]] = None,
        correlation_id: Optional[str] = None,
        user_id: str = "system",
    ):
        """Evaluate a contract against a playbook's policy rules asynchronously."""
        task_id = _get_task_id()
        correlation_id = correlation_id or task_id
        logger.info(
            "Evaluating contract policies",
            extra={"upload_id": upload_id, "playbook_id": playbook_id,
                   "tenant_id": tenant_id, "correlation_id": correlation_id,
                   "task_id": task_id},
        )

        try:
            # This is a sync Celery task — we use an async wrapper
            import asyncio

            async def _run_evaluation():
                from app.kernel.database.session import TenantAwareSessionFactory
                from app.config import settings

                factory = TenantAwareSessionFactory(
                    database_url=settings.database_url,
                    pool_size=2, max_overflow=2,
                )
                session = await factory.create_session(
                    tenant_id=tenant_id, user_id=user_id, user_role="admin",
                )

                try:
                    repo = PlaybookRepository(session, tenant_id=tenant_id)
                    event_bus = EventBus()

                    # Build user context
                    from dataclasses import dataclass
                    from app.kernel.security.auth import UserContext

                    user = UserContext(id=user_id, role="admin", tenant_id=tenant_id)

                    service = PlaybookService(
                        repo=repo, event_bus=event_bus, user=user, tenant_id=tenant_id,
                    )

                    # Parse extracted clauses
                    extracted_clauses = []
                    if clauses:
                        for c in clauses:
                            extracted_clauses.append(ExtractedClause(
                                category=c.get("category", "general"),
                                text=c.get("text", ""),
                                text_snippet=c.get("text_snippet", c.get("text", "")[:200]),
                                confidence=c.get("confidence", 1.0),
                                page_numbers=c.get("page_numbers", []),
                                metadata=c.get("metadata", {}),
                            ))

                    result = await service.evaluate_contract(
                        upload_id=upload_id, playbook_id=playbook_id,
                        review_id=review_id, contract_value=contract_value,
                        jurisdiction=jurisdiction, industry=industry,
                        risk_score=risk_score, findings=findings,
                        clauses=extracted_clauses, correlation_id=correlation_id,
                    )

                    await session.commit()
                    return result

                except Exception:
                    await session.rollback()
                    raise
                finally:
                    await session.close()
                    await factory.close()

            result = asyncio.run(_run_evaluation())
            logger.info(
                "Policy evaluation completed",
                extra={"upload_id": upload_id, "risk_level": result.get("risk_level") if result else None,
                       "deviations": result.get("deviations_found") if result else None,
                       "correlation_id": correlation_id},
            )
            return result

        except Exception as exc:
            logger.error(
                "Policy evaluation failed",
                extra={"upload_id": upload_id, "playbook_id": playbook_id,
                       "error": str(exc), "correlation_id": correlation_id},
                exc_info=True,
            )
            try:
                self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))
            except Exception:
                logger.critical("Policy evaluation exhausted retries",
                                extra={"upload_id": upload_id, "correlation_id": correlation_id})
                raise

    @celery_app.task(
        name="playbook.detect_clause_deviations",
        bind=True,
        max_retries=3,
        default_retry_delay=30,
        acks_late=True,
        queue="playbook",
    )
    def detect_clause_deviations_task(
        self,
        evaluation_id: str,
        upload_id: str,
        playbook_id: str,
        tenant_id: str,
        clauses: list[dict],
        correlation_id: Optional[str] = None,
    ):
        """Detect clause deviations for an existing evaluation."""
        task_id = _get_task_id()
        correlation_id = correlation_id or task_id
        logger.info(
            "Detecting clause deviations",
            extra={"evaluation_id": evaluation_id, "upload_id": upload_id,
                   "playbook_id": playbook_id, "tenant_id": tenant_id,
                   "correlation_id": correlation_id},
        )

        try:
            import asyncio

            async def _run_detection():
                from app.kernel.database.session import TenantAwareSessionFactory
                from app.config import settings

                factory = TenantAwareSessionFactory(
                    database_url=settings.database_url,
                    pool_size=2, max_overflow=2,
                )
                session = await factory.create_session(
                    tenant_id=tenant_id, user_id="system", user_role="admin",
                )

                try:
                    repo = PlaybookRepository(session, tenant_id=tenant_id)

                    # Load playbook data
                    standards = await repo.get_active_clauses_by_playbook(playbook_id, tenant_id)
                    rules = await repo.get_active_rules_by_playbook(playbook_id, tenant_id)

                    # Parse clauses
                    extracted = []
                    for c in clauses:
                        extracted.append(ExtractedClause(
                            category=c.get("category", "general"),
                            text=c.get("text", ""),
                            text_snippet=c.get("text_snippet", c.get("text", "")[:200]),
                            confidence=c.get("confidence", 1.0),
                        ))

                    # Run detection
                    from app.domains.playbook.engine import DeviationDetector, RuleEvaluator
                    ctx = EvaluationContext(
                        upload_id=upload_id, tenant_id=tenant_id, clauses=extracted,
                        correlation_id=correlation_id,
                    )

                    rule_results = []
                    for rule in rules:
                        if rule.is_active:
                            rule_results.append(RuleEvaluator.evaluate_rule(rule, ctx))

                    deviations = DeviationDetector.detect_deviations(extracted, standards, rule_results)

                    # Store results
                    deviations_json = [
                        {
                            "clause_category": d.clause_category,
                            "clause_text_snippet": d.clause_text_snippet,
                            "expected": d.expected,
                            "actual": d.actual,
                            "severity": d.severity,
                            "score": d.score,
                            "rule_id": d.rule_id,
                            "recommendation": d.recommendation,
                            "fallback_clause_id": d.fallback_clause_id,
                        }
                        for d in deviations
                    ]

                    await repo.update_evaluation(
                        evaluation_id, tenant_id,
                        deviations=deviations_json,
                        deviations_found=len(deviations),
                    )

                    await session.commit()
                    return {"deviations_found": len(deviations), "deviations": deviations_json}

                except Exception:
                    await session.rollback()
                    raise
                finally:
                    await session.close()
                    await factory.close()

            result = asyncio.run(_run_detection())
            logger.info("Deviation detection completed",
                        extra={"evaluation_id": evaluation_id,
                               "deviations": result["deviations_found"],
                               "correlation_id": correlation_id})
            return result

        except Exception as exc:
            logger.error("Deviation detection failed",
                         extra={"evaluation_id": evaluation_id, "error": str(exc),
                                "correlation_id": correlation_id},
                         exc_info=True)
            try:
                self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))
            except Exception:
                raise

    @celery_app.task(
        name="playbook.generate_clause_recommendations",
        bind=True,
        max_retries=2,
        default_retry_delay=30,
        acks_late=True,
        queue="playbook",
    )
    def generate_clause_recommendations_task(
        self,
        evaluation_id: str,
        upload_id: str,
        playbook_id: str,
        tenant_id: str,
        correlation_id: Optional[str] = None,
    ):
        """Generate clause recommendations for a completed evaluation."""
        task_id = _get_task_id()
        correlation_id = correlation_id or task_id
        logger.info("Generating clause recommendations",
                    extra={"evaluation_id": evaluation_id, "playbook_id": playbook_id,
                           "tenant_id": tenant_id, "correlation_id": correlation_id})

        try:
            import asyncio

            async def _run():
                from app.kernel.database.session import TenantAwareSessionFactory
                from app.config import settings

                factory = TenantAwareSessionFactory(
                    database_url=settings.database_url,
                    pool_size=2, max_overflow=2,
                )
                session = await factory.create_session(
                    tenant_id=tenant_id, user_id="system", user_role="admin",
                )

                try:
                    repo = PlaybookRepository(session, tenant_id=tenant_id)

                    # Get evaluation and standards
                    evaluation = await repo.get_evaluation(evaluation_id, tenant_id)
                    if not evaluation:
                        raise ValueError(f"Evaluation {evaluation_id} not found")

                    standards = await repo.get_active_clauses_by_playbook(playbook_id, tenant_id)

                    # Parse deviations from stored results
                    deviations_data = list(evaluation.deviations) if evaluation.deviations else []

                    from app.domains.playbook.engine import ClauseRecommender, DeviationResult

                    deviations = []
                    for d in deviations_data:
                        deviations.append(DeviationResult(
                            clause_category=d.get("clause_category", ""),
                            clause_text_snippet=d.get("clause_text_snippet", ""),
                            expected=d.get("expected", ""),
                            actual=d.get("actual", ""),
                            severity=d.get("severity", "medium"),
                            score=d.get("score", 0.5),
                            rule_id=d.get("rule_id"),
                            recommendation=d.get("recommendation"),
                            fallback_clause_id=d.get("fallback_clause_id"),
                        ))

                    recommendations = ClauseRecommender.recommend(deviations, standards)

                    # Store recommendations
                    rec_dicts = []
                    for rec in recommendations:
                        rec_dicts.append({
                            "tenant_id": tenant_id,
                            "evaluation_id": evaluation_id,
                            "upload_id": upload_id,
                            "review_id": str(evaluation.review_id) if evaluation.review_id else None,
                            "clause_id": rec.clause_id,
                            "clause_category": rec.clause_category,
                            "clause_type": rec.clause_type,
                            "title": rec.title,
                            "body": rec.body,
                            "rationale": rec.rationale,
                            "confidence_score": rec.confidence_score,
                            "risk_reduction": rec.risk_reduction,
                            "priority": rec.priority,
                            "replaces_clause_text": rec.replaces_clause_text,
                        })

                    if rec_dicts:
                        await repo.bulk_create_recommendations(rec_dicts)

                    # Update evaluation with recommendations summary
                    recs_summary = [
                        {"clause_category": r["clause_category"], "clause_type": r["clause_type"],
                         "title": r["title"], "rationale": r["rationale"],
                         "confidence_score": r["confidence_score"], "priority": r["priority"]}
                        for r in rec_dicts
                    ]
                    await repo.update_evaluation(
                        evaluation_id, tenant_id, recommendations=recs_summary,
                    )

                    await session.commit()
                    return {"recommendations_count": len(rec_dicts)}

                except Exception:
                    await session.rollback()
                    raise
                finally:
                    await session.close()
                    await factory.close()

            result = asyncio.run(_run())
            logger.info("Recommendations generated",
                        extra={"evaluation_id": evaluation_id,
                               "count": result["recommendations_count"],
                               "correlation_id": correlation_id})
            return result

        except Exception as exc:
            logger.error("Recommendation generation failed",
                         extra={"evaluation_id": evaluation_id, "error": str(exc),
                                "correlation_id": correlation_id},
                         exc_info=True)
            try:
                self.retry(exc=exc, countdown=30)
            except Exception:
                raise

    @celery_app.task(
        name="playbook.reevaluate_playbook_changes",
        bind=True,
        max_retries=2,
        default_retry_delay=60,
        acks_late=True,
        queue="playbook",
    )
    def reevaluate_playbook_changes_task(
        self,
        playbook_id: str,
        tenant_id: str,
        correlation_id: Optional[str] = None,
    ):
        """Re-evaluate all contracts affected by playbook changes."""
        task_id = _get_task_id()
        correlation_id = correlation_id or task_id
        logger.info("Re-evaluating playbook changes",
                    extra={"playbook_id": playbook_id, "tenant_id": tenant_id,
                           "correlation_id": correlation_id})

        try:
            import asyncio

            async def _run():
                from app.kernel.database.session import TenantAwareSessionFactory
                from app.config import settings

                factory = TenantAwareSessionFactory(
                    database_url=settings.database_url,
                    pool_size=2, max_overflow=2,
                )
                session = await factory.create_session(
                    tenant_id=tenant_id, user_id="system", user_role="admin",
                )

                try:
                    repo = PlaybookRepository(session, tenant_id=tenant_id)

                    # Find all evaluations for this playbook
                    from app.domains.playbook.models import PolicyEvaluation
                    from sqlalchemy import select

                    stmt = select(PolicyEvaluation).where(
                        PolicyEvaluation.playbook_id == playbook_id,
                        PolicyEvaluation.tenant_id == tenant_id,
                        PolicyEvaluation.status == "completed",
                    ).order_by(PolicyEvaluation.created_at.desc()).limit(50)

                    result = await session.execute(stmt)
                    evaluations = list(result.scalars().all())

                    # Mark for re-evaluation
                    from app.domains.playbook.models import EvaluationStatus
                    re_eval_count = 0
                    for eval_record in evaluations:
                        eval_record.status = EvaluationStatus.PENDING
                        re_eval_count += 1

                    await session.flush()
                    await session.commit()

                    return {
                        "playbook_id": playbook_id,
                        "affected_evaluations": re_eval_count,
                        "correlation_id": correlation_id,
                    }

                except Exception:
                    await session.rollback()
                    raise
                finally:
                    await session.close()
                    await factory.close()

            result = asyncio.run(_run())
            logger.info("Playbook re-evaluation queued",
                        extra={"playbook_id": playbook_id,
                               "affected": result["affected_evaluations"],
                               "correlation_id": correlation_id})
            return result

        except Exception as exc:
            logger.error("Playbook re-evaluation failed",
                         extra={"playbook_id": playbook_id, "error": str(exc),
                                "correlation_id": correlation_id},
                         exc_info=True)
            try:
                self.retry(exc=exc, countdown=60)
            except Exception:
                raise

else:
    # Stub tasks when Celery is not configured
    async def evaluate_contract_policies_task_stub(*args, **kwargs):
        logger.warning("Celery not configured — policy evaluation task skipped")
        return None

    async def detect_clause_deviations_task_stub(*args, **kwargs):
        logger.warning("Celery not configured — deviation detection task skipped")
        return None

    async def generate_clause_recommendations_task_stub(*args, **kwargs):
        logger.warning("Celery not configured — recommendation generation task skipped")
        return None

    async def reevaluate_playbook_changes_task_stub(*args, **kwargs):
        logger.warning("Celery not configured — re-evaluation task skipped")
        return None
