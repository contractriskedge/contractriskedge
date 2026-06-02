"""Legal Playbook + Policy Engine services.

Services:
- PlaybookService: CRUD, versioning, publishing, rollback
- ClauseStandardService: clause management, categorization, fallback chain
- PolicyOverrideService: override request/review lifecycle
- GovernanceAuditService: immutable audit trail
- AIPolicyInjectionService: policy context for AI prompts
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from app.domains.playbook.models import (
    LegalPlaybook, PlaybookVersion, ClauseStandard,
    PolicyRule, PolicyEvaluation, ApprovalThreshold,
    ClauseRecommendation, PolicyOverride, GovernanceAuditEvent,
    PlaybookStatus, OverrideStatus, EvaluationStatus,
    DeviationSeverity,
)
from app.domains.playbook.repository import PlaybookRepository
from app.domains.playbook.schemas import (
    PlaybookCreate, PlaybookUpdate, PlaybookVersionCreate,
    ClauseStandardCreate, ClauseStandardUpdate,
    PolicyRuleCreate, PolicyRuleUpdate,
    ApprovalThresholdCreate, ApprovalThresholdUpdate,
    OverrideRequest, OverrideReview,
    PlaybookFilterParams, ClauseFilterParams, RuleFilterParams,
    EvaluationFilterParams, OverrideFilterParams, AuditFilterParams,
)
from app.domains.playbook.engine import (
    PolicyEngine, EvaluationContext, ExtractedClause,
    EvaluationResult, RuleEvaluator, DeviationDetector,
    ClauseRecommender, RiskScorer, ApprovalThresholdEvaluator,
)
from app.kernel.events.bus import EventBus, DomainEvent
from app.kernel.security.auth import UserContext

logger = logging.getLogger(__name__)


# ── Domain Events ───────────────────────────────────────────────────


class PlaybookCreated(DomainEvent):
    event_type = "playbook.created"


class PlaybookPublished(DomainEvent):
    event_type = "playbook.published"


class PlaybookArchived(DomainEvent):
    event_type = "playbook.archived"


class PlaybookRolledBack(DomainEvent):
    event_type = "playbook.rolled_back"


class ClauseCreated(DomainEvent):
    event_type = "clause.created"


class ClauseUpdated(DomainEvent):
    event_type = "clause.updated"


class RuleCreated(DomainEvent):
    event_type = "rule.created"


class RuleUpdated(DomainEvent):
    event_type = "rule.updated"


class EvaluationCompleted(DomainEvent):
    event_type = "evaluation.completed"


class DeviationDetected(DomainEvent):
    event_type = "deviation.detected"


class OverrideRequested(DomainEvent):
    event_type = "override.requested"


class OverrideReviewed(DomainEvent):
    event_type = "override.reviewed"


class ThresholdCreated(DomainEvent):
    event_type = "threshold.created"


# ── Playbook Service ────────────────────────────────────────────────


@dataclass
class PlaybookService:
    """Manages legal playbook lifecycle — creation, versioning, publishing, rollback."""

    repo: PlaybookRepository
    event_bus: EventBus
    user: UserContext
    tenant_id: str

    async def create_playbook(self, data: PlaybookCreate) -> dict:
        """Create a new playbook with initial draft version."""
        playbook = await self.repo.create_playbook(
            tenant_id=self.tenant_id, name=data.name,
            description=data.description, jurisdiction=data.jurisdiction,
            practice_area=data.practice_area, tags=data.tags,
            metadata=data.metadata, created_by=self.user.id,
        )
        await self._audit("playbook.created", "playbook", str(playbook.playbook_id),
                          change_summary=f"Created playbook '{data.name}'")
        await self.event_bus.emit(PlaybookCreated(
            tenant_id=self.tenant_id, actor_id=self.user.id,
            data={"playbook_id": str(playbook.playbook_id), "name": data.name},
        ))
        return self._playbook_to_dict(playbook)

    async def get_playbook(self, playbook_id: str) -> Optional[dict]:
        playbook = await self.repo.get_playbook(playbook_id, self.tenant_id)
        return self._playbook_to_dict(playbook) if playbook else None

    async def list_playbooks(self, filters: PlaybookFilterParams) -> tuple[list, int]:
        items, total = await self.repo.list_playbooks(self.tenant_id, filters)
        return [self._playbook_to_dict(p) for p in items], total

    async def update_playbook(self, playbook_id: str, data: PlaybookUpdate) -> Optional[dict]:
        playbook = await self.repo.update_playbook(
            playbook_id, self.tenant_id, **data.model_dump(exclude_none=True),
        )
        if playbook:
            await self._audit("playbook.updated", "playbook", playbook_id,
                              change_summary=f"Updated playbook '{playbook.name}'")
        return self._playbook_to_dict(playbook) if playbook else None

    async def publish_playbook(self, playbook_id: str, data: PlaybookVersionCreate) -> Optional[dict]:
        version = await self.repo.publish_playbook(
            playbook_id, self.tenant_id, self.user.id,
            version_label=data.version_label, change_notes=data.change_notes,
        )
        if version:
            await self._audit("playbook.published", "playbook", playbook_id,
                              change_summary=f"Published version {version.version_number}")
            await self.event_bus.emit(PlaybookPublished(
                tenant_id=self.tenant_id, actor_id=self.user.id,
                data={"playbook_id": playbook_id, "version": version.version_number},
            ))
        return self._version_to_dict(version) if version else None

    async def create_draft_version(self, playbook_id: str) -> Optional[dict]:
        version = await self.repo.create_draft_version(playbook_id, self.tenant_id, self.user.id)
        return self._version_to_dict(version) if version else None

    async def rollback_playbook(self, playbook_id: str, target_version_id: str) -> Optional[dict]:
        version = await self.repo.rollback_to_version(playbook_id, self.tenant_id, target_version_id)
        if version:
            await self._audit("playbook.rolled_back", "playbook", playbook_id,
                              change_summary=f"Rolled back to version {version.version_number}")
            await self.event_bus.emit(PlaybookRolledBack(
                tenant_id=self.tenant_id, actor_id=self.user.id,
                data={"playbook_id": playbook_id, "version": version.version_number},
            ))
        return self._version_to_dict(version) if version else None

    async def archive_playbook(self, playbook_id: str) -> Optional[dict]:
        playbook = await self.repo.update_playbook(
            playbook_id, self.tenant_id,
            status=PlaybookStatus.ARCHIVED, archived_at=datetime.utcnow(),
        )
        if playbook:
            await self._audit("playbook.archived", "playbook", playbook_id,
                              change_summary=f"Archived playbook '{playbook.name}'")
            await self.event_bus.emit(PlaybookArchived(
                tenant_id=self.tenant_id, actor_id=self.user.id,
                data={"playbook_id": playbook_id},
            ))
        return self._playbook_to_dict(playbook) if playbook else None

    async def list_versions(self, playbook_id: str) -> tuple[list, int]:
        items, total = await self.repo.list_versions(playbook_id, self.tenant_id)
        return [self._version_to_dict(v) for v in items], total

    # ── Clause Standards ───────────────────────────────────────────

    async def create_clause(self, playbook_id: str, data: ClauseStandardCreate) -> Optional[dict]:
        playbook = await self.repo.get_playbook(playbook_id, self.tenant_id)
        if not playbook:
            return None
        clause = await self.repo.create_clause(
            playbook_id=playbook_id, tenant_id=self.tenant_id,
            created_by=self.user.id, **data.model_dump(),
        )
        await self._audit("clause.created", "clause", str(clause.clause_id),
                          change_summary=f"Created clause '{data.title}' in playbook '{playbook.name}'")
        await self.event_bus.emit(ClauseCreated(
            tenant_id=self.tenant_id, actor_id=self.user.id,
            data={"clause_id": str(clause.clause_id), "title": data.title},
        ))
        return self._clause_to_dict(clause)

    async def get_clause(self, clause_id: str) -> Optional[dict]:
        clause = await self.repo.get_clause(clause_id, self.tenant_id)
        return self._clause_to_dict(clause) if clause else None

    async def list_clauses(self, playbook_id: str, filters: ClauseFilterParams) -> tuple[list, int]:
        items, total = await self.repo.list_clauses(self.tenant_id, playbook_id, filters)
        return [self._clause_to_dict(c) for c in items], total

    async def update_clause(self, clause_id: str, data: ClauseStandardUpdate) -> Optional[dict]:
        clause = await self.repo.update_clause(
            clause_id, self.tenant_id, **data.model_dump(exclude_none=True),
        )
        if clause:
            await self._audit("clause.updated", "clause", clause_id,
                              change_summary=f"Updated clause '{clause.title}'")
        return self._clause_to_dict(clause) if clause else None

    async def deactivate_clause(self, clause_id: str) -> Optional[dict]:
        clause = await self.repo.update_clause(clause_id, self.tenant_id, is_active=False)
        if clause:
            await self._audit("clause.deactivated", "clause", clause_id,
                              change_summary=f"Deactivated clause '{clause.title}'")
        return self._clause_to_dict(clause) if clause else None

    # ── Policy Rules ───────────────────────────────────────────────

    async def create_rule(self, playbook_id: str, data: PolicyRuleCreate) -> Optional[dict]:
        playbook = await self.repo.get_playbook(playbook_id, self.tenant_id)
        if not playbook:
            return None
        rule = await self.repo.create_rule(
            playbook_id=playbook_id, tenant_id=self.tenant_id,
            created_by=self.user.id,
            name=data.name, description=data.description,
            rule_type=data.rule_type, priority=data.priority,
            is_mandatory=data.is_mandatory,
            conditions=data.conditions.model_dump() if data.conditions else {},
            effect=data.effect, effect_config=data.effect_config,
            target_clause_id=data.target_clause_id,
            target_category=data.target_category,
            applicable_jurisdictions=data.applicable_jurisdictions,
            applicable_industries=data.applicable_industries,
            min_contract_value=data.min_contract_value,
            max_contract_value=data.max_contract_value,
            effective_date=data.effective_date,
            expiration_date=data.expiration_date,
            tags=data.tags, metadata=data.metadata,
        )
        await self._audit("rule.created", "rule", str(rule.rule_id),
                          change_summary=f"Created rule '{data.name}' in playbook '{playbook.name}'")
        await self.event_bus.emit(RuleCreated(
            tenant_id=self.tenant_id, actor_id=self.user.id,
            data={"rule_id": str(rule.rule_id), "name": data.name},
        ))
        return self._rule_to_dict(rule)

    async def get_rule(self, rule_id: str) -> Optional[dict]:
        rule = await self.repo.get_rule(rule_id, self.tenant_id)
        return self._rule_to_dict(rule) if rule else None

    async def list_rules(self, playbook_id: str, filters: RuleFilterParams) -> tuple[list, int]:
        items, total = await self.repo.list_rules(self.tenant_id, playbook_id, filters)
        return [self._rule_to_dict(r) for r in items], total

    async def update_rule(self, rule_id: str, data: PolicyRuleUpdate) -> Optional[dict]:
        update_kwargs = data.model_dump(exclude_none=True)
        if "conditions" in update_kwargs and update_kwargs["conditions"] is not None:
            update_kwargs["conditions"] = update_kwargs["conditions"].model_dump()
        rule = await self.repo.update_rule(rule_id, self.tenant_id, **update_kwargs)
        if rule:
            await self._audit("rule.updated", "rule", rule_id,
                              change_summary=f"Updated rule '{rule.name}'")
        return self._rule_to_dict(rule) if rule else None

    # ── Approval Thresholds ────────────────────────────────────────

    async def create_threshold(self, playbook_id: str, data: ApprovalThresholdCreate) -> Optional[dict]:
        playbook = await self.repo.get_playbook(playbook_id, self.tenant_id)
        if not playbook:
            return None
        threshold = await self.repo.create_threshold(
            playbook_id=playbook_id, tenant_id=self.tenant_id,
            created_by=self.user.id, **data.model_dump(),
        )
        await self._audit("threshold.created", "threshold", str(threshold.threshold_id),
                          change_summary=f"Created threshold '{data.name}'")
        await self.event_bus.emit(ThresholdCreated(
            tenant_id=self.tenant_id, actor_id=self.user.id,
            data={"threshold_id": str(threshold.threshold_id), "name": data.name},
        ))
        return self._threshold_to_dict(threshold)

    async def list_thresholds(self, playbook_id: str,
                               threshold_type: Optional[str] = None) -> tuple[list, int]:
        items, total = await self.repo.list_thresholds(
            self.tenant_id, playbook_id, threshold_type,
        )
        return [self._threshold_to_dict(t) for t in items], total

    async def update_threshold(self, threshold_id: str, data: ApprovalThresholdUpdate) -> Optional[dict]:
        threshold = await self.repo.update_threshold(
            threshold_id, self.tenant_id, **data.model_dump(exclude_none=True),
        )
        if threshold:
            await self._audit("threshold.updated", "threshold", threshold_id,
                              change_summary=f"Updated threshold '{threshold.name}'")
        return self._threshold_to_dict(threshold) if threshold else None

    # ── Policy Evaluation ──────────────────────────────────────────

    async def evaluate_contract(self, upload_id: str, playbook_id: str,
                                 review_id: Optional[str] = None,
                                 clauses: Optional[list[ExtractedClause]] = None,
                                 contract_value: Optional[float] = None,
                                 jurisdiction: Optional[str] = None,
                                 industry: Optional[str] = None,
                                 risk_score: Optional[float] = None,
                                 findings: Optional[list[dict]] = None,
                                 correlation_id: Optional[str] = None,
                                 simulation_mode: bool = False) -> Optional[dict]:
        """Run full policy evaluation for a contract against a playbook.

        Args:
            simulation_mode: If True, runs evaluation without persisting results
                             (true dry-run). Returns result dict without saving.
        """
        playbook = await self.repo.get_playbook(playbook_id, self.tenant_id)
        if not playbook:
            return None

        # In simulation mode, skip persistence and return results directly
        if simulation_mode:
            return await self._run_simulation(
                upload_id=upload_id, playbook_id=playbook_id,
                playbook=playbook, review_id=review_id,
                clauses=clauses, contract_value=contract_value,
                jurisdiction=jurisdiction, industry=industry,
                risk_score=risk_score, findings=findings,
                correlation_id=correlation_id,
            )

        # Check for existing evaluation
        existing = await self.repo.get_evaluation_by_upload(upload_id, self.tenant_id)
        if existing and existing.status == EvaluationStatus.COMPLETED:
            return self._evaluation_to_dict(existing)

        # Create evaluation record
        evaluation = await self.repo.create_evaluation(
            tenant_id=self.tenant_id, upload_id=upload_id,
            review_id=review_id, playbook_id=playbook_id,
            playbook_version_id=playbook.active_version_id,
            status=EvaluationStatus.PROCESSING,
            started_at=datetime.utcnow(),
            correlation_id=correlation_id,
        )

        try:
            # Load active rules, standards, and thresholds
            rules = await self.repo.get_active_rules_by_playbook(playbook_id, self.tenant_id)
            standards = await self.repo.get_active_clauses_by_playbook(playbook_id, self.tenant_id)
            thresholds = await self.repo.get_active_thresholds_by_playbook(playbook_id, self.tenant_id)

            # Build evaluation context
            ctx = EvaluationContext(
                upload_id=upload_id,
                tenant_id=self.tenant_id,
                review_id=review_id,
                contract_value=contract_value,
                jurisdiction=jurisdiction,
                industry=industry,
                clauses=clauses or [],
                risk_score=risk_score,
                findings=findings or [],
                correlation_id=correlation_id,
            )

            # Run policy engine
            result: EvaluationResult = PolicyEngine.evaluate(rules, standards, thresholds, ctx)

            # Store clause recommendations
            if result.recommendations:
                rec_dicts = []
                for rec in result.recommendations:
                    rec_dicts.append({
                        "tenant_id": self.tenant_id,
                        "evaluation_id": str(evaluation.evaluation_id),
                        "upload_id": upload_id,
                        "review_id": review_id,
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
                await self.repo.bulk_create_recommendations(rec_dicts)

            # Serialize results
            results_json = [
                {
                    "rule_id": r.rule_id,
                    "rule_name": r.rule_name,
                    "rule_type": r.rule_type,
                    "effect": r.effect,
                    "violation_triggered": r.violation_triggered,
                    "priority": r.priority,
                    "details": r.details,
                    "deviation_severity": r.deviation_severity,
                }
                for r in result.rule_results
            ]

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
                for d in result.deviations
            ]

            recs_json = [
                {
                    "clause_category": r.clause_category,
                    "clause_type": r.clause_type,
                    "title": r.title,
                    "rationale": r.rationale,
                    "confidence_score": r.confidence_score,
                    "priority": r.priority,
                }
                for r in result.recommendations
            ]

            # Update evaluation with results
            evaluation = await self.repo.update_evaluation(
                str(evaluation.evaluation_id), self.tenant_id,
                status=EvaluationStatus.COMPLETED,
                total_rules_evaluated=result.total_rules,
                rules_passed=result.rules_passed,
                rules_failed=result.rules_failed,
                deviations_found=result.deviations_found,
                mandatory_blocks=result.mandatory_blocks,
                approval_required=result.approval_required,
                risk_score=result.risk_score,
                risk_level=result.risk_level,
                results=results_json,
                deviations=deviations_json,
                recommendations=recs_json,
                completed_at=datetime.utcnow(),
            )

            # Audit
            await self._audit("evaluation.completed", "evaluation", str(evaluation.evaluation_id),
                              change_summary=f"Evaluation completed: {result.rules_failed} rules failed, "
                                             f"{result.deviations_found} deviations, "
                                             f"risk level {result.risk_level}")

            if result.deviations:
                await self._audit("deviation.detected", "evaluation", str(evaluation.evaluation_id),
                                  change_summary=f"{len(result.deviations)} deviations detected",
                                  metadata={"deviation_count": len(result.deviations),
                                            "severities": list(set(d.severity for d in result.deviations))})

            await self.event_bus.emit(EvaluationCompleted(
                tenant_id=self.tenant_id, actor_id=self.user.id,
                data={
                    "evaluation_id": str(evaluation.evaluation_id),
                    "upload_id": upload_id,
                    "playbook_id": playbook_id,
                    "risk_level": result.risk_level,
                    "deviations": result.deviations_found,
                },
            ))

            return self._evaluation_to_dict(evaluation)

        except Exception as exc:
            logger.error("Policy evaluation failed: %s", exc, exc_info=True)
            await self.repo.update_evaluation(
                str(evaluation.evaluation_id), self.tenant_id,
                status=EvaluationStatus.FAILED,
                error_message=str(exc),
                completed_at=datetime.utcnow(),
            )
            raise

    async def _run_simulation(self, upload_id: str, playbook_id: str,
                               playbook: Any,
                               review_id: Optional[str] = None,
                               clauses: Optional[list[ExtractedClause]] = None,
                               contract_value: Optional[float] = None,
                               jurisdiction: Optional[str] = None,
                               industry: Optional[str] = None,
                               risk_score: Optional[float] = None,
                               findings: Optional[list[dict]] = None,
                               correlation_id: Optional[str] = None) -> dict:
        """Run policy engine in simulation mode without persisting results."""
        rules = await self.repo.get_active_rules_by_playbook(playbook_id, self.tenant_id)
        standards = await self.repo.get_active_clauses_by_playbook(playbook_id, self.tenant_id)
        thresholds = await self.repo.get_active_thresholds_by_playbook(playbook_id, self.tenant_id)

        ctx = EvaluationContext(
            upload_id=upload_id,
            tenant_id=self.tenant_id,
            review_id=review_id,
            contract_value=contract_value,
            jurisdiction=jurisdiction,
            industry=industry,
            clauses=clauses or [],
            risk_score=risk_score,
            findings=findings or [],
            correlation_id=correlation_id,
        )

        result: EvaluationResult = PolicyEngine.evaluate(rules, standards, thresholds, ctx)

        now = datetime.utcnow()
        return {
            "simulation": True,
            "evaluation_id": f"sim_{uuid.uuid4().hex[:12]}",
            "status": "completed",
            "playbook_id": playbook_id,
            "playbook_name": playbook.name if hasattr(playbook, 'name') else "",
            "upload_id": upload_id,
            "total_rules_evaluated": result.total_rules,
            "rules_passed": result.rules_passed,
            "rules_failed": result.rules_failed,
            "deviations_found": result.deviations_found,
            "mandatory_blocks": result.mandatory_blocks,
            "approval_required": result.approval_required,
            "risk_score": result.risk_score,
            "risk_level": result.risk_level,
            "started_at": now,
            "completed_at": now,
            "created_at": now,
            "results": [
                {
                    "rule_id": r.rule_id,
                    "rule_name": r.rule_name,
                    "rule_type": r.rule_type,
                    "effect": r.effect,
                    "violation_triggered": r.violation_triggered,
                    "priority": r.priority,
                    "details": r.details,
                    "deviation_severity": r.deviation_severity,
                }
                for r in result.rule_results
            ],
            "deviations": [
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
                for d in result.deviations
            ],
            "recommendations": [
                {
                    "clause_category": r.clause_category,
                    "clause_type": r.clause_type,
                    "title": r.title,
                    "rationale": r.rationale,
                    "confidence_score": r.confidence_score,
                    "priority": r.priority,
                }
                for r in result.recommendations
            ],
        }

    async def get_evaluation(self, evaluation_id: str) -> Optional[dict]:
        evaluation = await self.repo.get_evaluation(evaluation_id, self.tenant_id)
        return self._evaluation_to_dict(evaluation) if evaluation else None

    async def get_evaluation_by_upload(self, upload_id: str) -> Optional[dict]:
        evaluation = await self.repo.get_evaluation_by_upload(upload_id, self.tenant_id)
        return self._evaluation_to_dict(evaluation) if evaluation else None

    async def list_evaluations(self, filters: EvaluationFilterParams) -> tuple[list, int]:
        items, total = await self.repo.list_evaluations(self.tenant_id, filters)
        return [self._evaluation_to_dict(e) for e in items], total

    # ── Policy Overrides ───────────────────────────────────────────

    async def request_override(self, data: OverrideRequest) -> Optional[dict]:
        """Request a policy override with justification."""
        evaluation = await self.repo.get_evaluation(data.evaluation_id, self.tenant_id)
        if not evaluation:
            return None

        override = await self.repo.create_override(
            tenant_id=self.tenant_id, requested_by=self.user.id,
            evaluation_id=data.evaluation_id, rule_id=data.rule_id,
            upload_id=data.upload_id, review_id=data.review_id,
            override_type=data.override_type, justification=data.justification,
            risk_assessment=data.risk_assessment,
            proposed_alternative=data.proposed_alternative,
            effective_date=data.effective_date,
            expiration_date=data.expiration_date,
            correlation_id=data.correlation_id,
            metadata=data.metadata,
        )
        await self._audit("override.requested", "override", str(override.override_id),
                          change_summary=f"Override requested: {data.override_type}")
        await self.event_bus.emit(OverrideRequested(
            tenant_id=self.tenant_id, actor_id=self.user.id,
            data={
                "override_id": str(override.override_id),
                "evaluation_id": data.evaluation_id,
                "override_type": data.override_type,
            },
        ))
        return self._override_to_dict(override)

    async def review_override(self, override_id: str, data: OverrideReview) -> Optional[dict]:
        """Approve or reject a policy override."""
        override = await self.repo.get_override(override_id, self.tenant_id)
        if not override:
            return None
        if override.status != OverrideStatus.PENDING:
            raise ValueError(f"Override is already {override.status.value}")

        new_status = OverrideStatus.APPROVED if data.decision == "approved" else OverrideStatus.REJECTED
        override = await self.repo.update_override_status(
            override_id, self.tenant_id, new_status,
            reviewed_by=self.user.id, review_notes=data.review_notes,
        )
        await self._audit(f"override.{data.decision}", "override", override_id,
                          change_summary=f"Override {data.decision}")
        await self.event_bus.emit(OverrideReviewed(
            tenant_id=self.tenant_id, actor_id=self.user.id,
            data={"override_id": override_id, "decision": data.decision},
        ))
        return self._override_to_dict(override) if override else None

    async def list_overrides(self, filters: OverrideFilterParams) -> tuple[list, int]:
        items, total = await self.repo.list_overrides(self.tenant_id, filters)
        return [self._override_to_dict(o) for o in items], total

    async def get_override(self, override_id: str) -> Optional[dict]:
        override = await self.repo.get_override(override_id, self.tenant_id)
        return self._override_to_dict(override) if override else None

    # ── Governance Audit ───────────────────────────────────────────

    async def list_audit_events(self, filters: AuditFilterParams) -> tuple[list, int]:
        items, total = await self.repo.list_audit_events(self.tenant_id, filters)
        return [self._audit_event_to_dict(e) for e in items], total

    async def _audit(self, event_type: str, entity_type: str, entity_id: str,
                      change_summary: Optional[str] = None,
                      previous_state: Optional[dict] = None,
                      new_state: Optional[dict] = None,
                      metadata: Optional[dict] = None) -> None:
        """Create a governance audit event."""
        try:
            await self.repo.create_audit_event(
                tenant_id=self.tenant_id, event_type=event_type,
                entity_type=entity_type, entity_id=entity_id,
                actor_id=self.user.id, actor_role=self.user.role,
                previous_state=previous_state, new_state=new_state,
                change_summary=change_summary, metadata=metadata,
            )
        except Exception as exc:
            logger.warning("Failed to create audit event: %s", exc)

    # ── Serialization Helpers ──────────────────────────────────────

    def _playbook_to_dict(self, p: LegalPlaybook) -> dict:
        return {
            "playbook_id": str(p.playbook_id),
            "name": p.name,
            "description": p.description,
            "jurisdiction": p.jurisdiction,
            "practice_area": p.practice_area,
            "status": p.status.value if hasattr(p.status, 'value') else str(p.status),
            "active_version_id": str(p.active_version_id) if p.active_version_id else None,
            "version_count": p.version_count,
            "tags": list(p.tags) if p.tags else [],
            "metadata": p.metadata if p.metadata else {},
            "created_by": p.created_by,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
            "archived_at": p.archived_at,
        }

    def _version_to_dict(self, v: PlaybookVersion) -> dict:
        return {
            "version_id": str(v.version_id),
            "playbook_id": str(v.playbook_id),
            "version_number": v.version_number,
            "version_label": v.version_label,
            "change_notes": v.change_notes,
            "is_draft": v.is_draft,
            "is_active": v.is_active,
            "published_by": v.published_by,
            "published_at": v.published_at,
            "created_by": v.created_by,
            "created_at": v.created_at,
        }

    def _clause_to_dict(self, c: ClauseStandard) -> dict:
        return {
            "clause_id": str(c.clause_id),
            "playbook_id": str(c.playbook_id),
            "category": c.category.value if hasattr(c.category, 'value') else str(c.category),
            "clause_type": c.clause_type.value if hasattr(c.clause_type, 'value') else str(c.clause_type),
            "title": c.title,
            "body": c.body,
            "summary": c.summary,
            "fallback_clause_ids": [str(fid) for fid in (c.fallback_clause_ids or [])],
            "min_contract_value": c.min_contract_value,
            "max_contract_value": c.max_contract_value,
            "applicable_jurisdictions": list(c.applicable_jurisdictions or []),
            "applicable_industries": list(c.applicable_industries or []),
            "risk_level": c.risk_level,
            "risk_score": c.risk_score,
            "tags": list(c.tags or []),
            "is_active": c.is_active,
            "effective_date": c.effective_date,
            "expiration_date": c.expiration_date,
            "created_by": c.created_by,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
        }

    def _rule_to_dict(self, r: PolicyRule) -> dict:
        return {
            "rule_id": str(r.rule_id),
            "playbook_id": str(r.playbook_id),
            "name": r.name,
            "description": r.description,
            "rule_type": r.rule_type,
            "priority": r.priority,
            "is_active": r.is_active,
            "is_mandatory": r.is_mandatory,
            "conditions": dict(r.conditions) if r.conditions else {},
            "effect": r.effect.value if hasattr(r.effect, 'value') else str(r.effect),
            "effect_config": dict(r.effect_config) if r.effect_config else {},
            "target_clause_id": str(r.target_clause_id) if r.target_clause_id else None,
            "target_category": r.target_category,
            "applicable_jurisdictions": list(r.applicable_jurisdictions or []),
            "applicable_industries": list(r.applicable_industries or []),
            "min_contract_value": r.min_contract_value,
            "max_contract_value": r.max_contract_value,
            "effective_date": r.effective_date,
            "expiration_date": r.expiration_date,
            "tags": list(r.tags or []),
            "created_by": r.created_by,
            "created_at": r.created_at,
            "updated_at": r.updated_at,
        }

    def _threshold_to_dict(self, t: ApprovalThreshold) -> dict:
        return {
            "threshold_id": str(t.threshold_id),
            "playbook_id": str(t.playbook_id),
            "name": t.name,
            "description": t.description,
            "threshold_type": t.threshold_type,
            "operator": t.operator,
            "min_value": t.min_value,
            "max_value": t.max_value,
            "target_category": t.target_category,
            "approval_role": t.approval_role,
            "approval_level": t.approval_level,
            "fallback_approval_role": t.fallback_approval_role,
            "auto_approve": t.auto_approve,
            "sla_hours": t.sla_hours,
            "is_active": t.is_active,
            "priority": t.priority,
            "created_by": t.created_by,
            "created_at": t.created_at,
            "updated_at": t.updated_at,
        }

    def _evaluation_to_dict(self, e: PolicyEvaluation) -> dict:
        return {
            "evaluation_id": str(e.evaluation_id),
            "upload_id": str(e.upload_id),
            "review_id": str(e.review_id) if e.review_id else None,
            "playbook_id": str(e.playbook_id) if e.playbook_id else None,
            "playbook_version_id": str(e.playbook_version_id) if e.playbook_version_id else None,
            "status": e.status.value if hasattr(e.status, 'value') else str(e.status),
            "total_rules_evaluated": e.total_rules_evaluated,
            "rules_passed": e.rules_passed,
            "rules_failed": e.rules_failed,
            "deviations_found": e.deviations_found,
            "mandatory_blocks": e.mandatory_blocks,
            "approval_required": e.approval_required,
            "risk_score": e.risk_score,
            "risk_level": e.risk_level,
            "results": list(e.results) if e.results else [],
            "deviations": list(e.deviations) if e.deviations else [],
            "recommendations": list(e.recommendations) if e.recommendations else [],
            "correlation_id": e.correlation_id,
            "error_message": e.error_message,
            "started_at": e.started_at,
            "completed_at": e.completed_at,
            "created_at": e.created_at,
        }

    def _override_to_dict(self, o: PolicyOverride) -> dict:
        return {
            "override_id": str(o.override_id),
            "evaluation_id": str(o.evaluation_id),
            "rule_id": str(o.rule_id) if o.rule_id else None,
            "upload_id": str(o.upload_id),
            "review_id": str(o.review_id) if o.review_id else None,
            "override_type": o.override_type,
            "justification": o.justification,
            "risk_assessment": o.risk_assessment,
            "proposed_alternative": o.proposed_alternative,
            "status": o.status.value if hasattr(o.status, 'value') else str(o.status),
            "requested_by": o.requested_by,
            "requested_at": o.requested_at,
            "reviewed_by": o.reviewed_by,
            "reviewed_at": o.reviewed_at,
            "review_notes": o.review_notes,
            "effective_date": o.effective_date,
            "expiration_date": o.expiration_date,
            "correlation_id": o.correlation_id,
            "created_at": o.created_at,
            "updated_at": o.updated_at,
        }

    def _audit_event_to_dict(self, e: GovernanceAuditEvent) -> dict:
        return {
            "event_id": str(e.event_id),
            "event_type": e.event_type,
            "entity_type": e.entity_type,
            "entity_id": str(e.entity_id),
            "actor_id": e.actor_id,
            "actor_role": e.actor_role,
            "previous_state": e.previous_state,
            "new_state": e.new_state,
            "change_summary": e.change_summary,
            "correlation_id": e.correlation_id,
            "request_id": e.request_id,
            "source": e.source,
            "created_at": e.created_at,
        }


# ── AI Policy Injection Service ─────────────────────────────────────


@dataclass
class AIPolicyInjectionService:
    """Builds policy context for injection into AI analysis prompts.

    This service constructs the policy-aware context that gets injected
    into LLM prompts so the AI can make policy-compliant recommendations.
    """

    repo: PlaybookRepository
    tenant_id: str

    async def build_policy_context(
        self,
        playbook_id: str,
        upload_id: str,
        clause_categories: Optional[list[str]] = None,
        include_rules: bool = True,
        include_clauses: bool = True,
        include_thresholds: bool = False,
    ) -> dict:
        """Build structured policy context for AI prompt injection."""
        playbook = await self.repo.get_playbook(playbook_id, self.tenant_id)
        if not playbook:
            return {"playbook_name": "", "context_prompt": "", "applicable_clauses": [], "applicable_rules": []}

        context = {
            "playbook_name": playbook.name,
            "playbook_version": str(playbook.active_version_id) if playbook.active_version_id else None,
            "applicable_clauses": [],
            "applicable_rules": [],
            "applicable_thresholds": [],
            "context_prompt": "",
        }

        prompt_parts = [f"You are analyzing this contract against the '{playbook.name}' legal playbook."]

        if include_clauses:
            standards = await self.repo.get_active_clauses_by_playbook(
                playbook_id, self.tenant_id, category=None,
            )
            if clause_categories:
                standards = [s for s in standards if
                             (s.category.value if hasattr(s.category, 'value') else str(s.category)) in clause_categories]

            context["applicable_clauses"] = [self._clause_to_prompt_dict(s) for s in standards]

            # Group by type for prompt
            approved = [s for s in standards if s.clause_type in ("approved", "preferred")]
            forbidden = [s for s in standards if s.clause_type == "forbidden"]

            if approved:
                prompt_parts.append(f"\nAPPROVED CLAUSES ({len(approved)}):")
                for s in approved[:10]:  # Limit to top 10 to avoid token overflow
                    cat = s.category.value if hasattr(s.category, 'value') else str(s.category)
                    prompt_parts.append(f"- {cat}/{s.title}: {s.summary or s.body[:200]}...")

            if forbidden:
                prompt_parts.append(f"\nFORBIDDEN CLAUSES ({len(forbidden)}):")
                for s in forbidden[:5]:
                    cat = s.category.value if hasattr(s.category, 'value') else str(s.category)
                    prompt_parts.append(f"- {cat}/{s.title}: {s.summary or s.body[:200]}...")

        if include_rules:
            rules = await self.repo.get_active_rules_by_playbook(playbook_id, self.tenant_id)
            context["applicable_rules"] = [self._rule_to_prompt_dict(r) for r in rules]

            mandatory = [r for r in rules if r.is_mandatory]
            blocking = [r for r in rules if r.effect.value in ("block", "require_approval")]

            if mandatory:
                prompt_parts.append(f"\nMANDATORY RULES ({len(mandatory)}):")
                for r in mandatory[:10]:
                    prompt_parts.append(f"- [{r.rule_type}] {r.name}: {r.description or ''}")

            if blocking:
                prompt_parts.append(f"\nAPPROVAL/BLOCKING RULES ({len(blocking)}):")
                for r in blocking[:5]:
                    prompt_parts.append(f"- {r.name}: requires {r.effect.value}")

        if include_thresholds:
            thresholds = await self.repo.get_active_thresholds_by_playbook(playbook_id, self.tenant_id)
            context["applicable_thresholds"] = [self._threshold_to_prompt_dict(t) for t in thresholds]

            if thresholds:
                prompt_parts.append(f"\nAPPROVAL THRESHOLDS ({len(thresholds)}):")
                for t in thresholds[:5]:
                    prompt_parts.append(f"- {t.name}: {t.threshold_type} > {t.min_value} → {t.approval_role}")

        prompt_parts.append("\n\nEvaluate each clause against these standards. Flag any deviations.")
        prompt_parts.append("For each deviation, recommend the appropriate standard clause.")
        prompt_parts.append("If a clause is forbidden, flag it as CRITICAL.")
        prompt_parts.append("If a mandatory clause is missing, flag it as REQUIRED.")

        context["context_prompt"] = "\n".join(prompt_parts)
        return context

    async def inject_into_prompt(self, playbook_id: str, upload_id: str,
                                   base_prompt: str,
                                   clause_categories: Optional[list[str]] = None) -> str:
        """Inject playbook policy context into an AI prompt."""
        context = await self.build_policy_context(
            playbook_id=playbook_id, upload_id=upload_id,
            clause_categories=clause_categories,
            include_rules=True, include_clauses=True, include_thresholds=False,
        )
        if context["context_prompt"]:
            return f"{base_prompt}\n\n---\nPOLICY CONTEXT:\n{context['context_prompt']}"
        return base_prompt

    def _clause_to_prompt_dict(self, s: ClauseStandard) -> dict:
        return {
            "clause_id": str(s.clause_id),
            "category": s.category.value if hasattr(s.category, 'value') else str(s.category),
            "clause_type": s.clause_type.value if hasattr(s.clause_type, 'value') else str(s.clause_type),
            "title": s.title,
            "summary": s.summary or s.body[:300],
            "risk_level": s.risk_level,
        }

    def _rule_to_prompt_dict(self, r: PolicyRule) -> dict:
        return {
            "rule_id": str(r.rule_id),
            "name": r.name,
            "rule_type": r.rule_type,
            "effect": r.effect.value if hasattr(r.effect, 'value') else str(r.effect),
            "is_mandatory": r.is_mandatory,
            "description": r.description,
        }

    def _threshold_to_prompt_dict(self, t: ApprovalThreshold) -> dict:
        return {
            "threshold_id": str(t.threshold_id),
            "name": t.name,
            "threshold_type": t.threshold_type,
            "approval_role": t.approval_role,
            "auto_approve": t.auto_approve,
        }
