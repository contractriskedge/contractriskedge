"""Legal Playbook + Policy Engine repository — data access for all playbook entities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update, func, or_, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.kernel.repository.base import BaseRepository
from app.domains.playbook.models import (
    LegalPlaybook, PlaybookVersion, ClauseStandard,
    PolicyRule, PolicyEvaluation, ApprovalThreshold,
    ClauseRecommendation, PolicyOverride, GovernanceAuditEvent,
    PlaybookStatus, OverrideStatus, EvaluationStatus,
)


@dataclass
class PlaybookRepository(BaseRepository):
    """Data access for legal playbooks and versions."""

    # ── Playbooks ──────────────────────────────────────────────────

    async def create_playbook(self, tenant_id: str, name: str, created_by: str,
                               description: Optional[str] = None, jurisdiction: Optional[str] = None,
                               practice_area: Optional[str] = None, tags: Optional[list[str]] = None,
                               metadata: Optional[dict] = None) -> LegalPlaybook:
        playbook = LegalPlaybook(
            tenant_id=tenant_id, name=name, description=description,
            jurisdiction=jurisdiction, practice_area=practice_area,
            tags=tags or [], metadata=metadata or {}, created_by=created_by,
        )
        self.session.add(playbook)
        await self.session.flush()

        # Create initial draft version
        version = PlaybookVersion(
            playbook_id=playbook.playbook_id, tenant_id=tenant_id,
            version_number=1, is_draft=True, is_active=False,
            created_by=created_by,
        )
        self.session.add(version)
        await self.session.flush()

        playbook.active_version_id = version.version_id
        return playbook

    async def get_playbook(self, playbook_id: str, tenant_id: str) -> Optional[LegalPlaybook]:
        stmt = select(LegalPlaybook).where(
            LegalPlaybook.playbook_id == playbook_id,
            LegalPlaybook.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_playbooks(self, tenant_id: str, filters) -> tuple[list, int]:
        query = select(LegalPlaybook).where(LegalPlaybook.tenant_id == tenant_id)
        if filters.status:
            query = query.where(LegalPlaybook.status == filters.status)
        if filters.jurisdiction:
            query = query.where(LegalPlaybook.jurisdiction == filters.jurisdiction)
        if filters.practice_area:
            query = query.where(LegalPlaybook.practice_area == filters.practice_area)
        if filters.search:
            search = f"%{filters.search}%"
            query = query.where(
                or_(LegalPlaybook.name.ilike(search), LegalPlaybook.description.ilike(search))
            )
        sort_col = getattr(LegalPlaybook, filters.sort_by, LegalPlaybook.created_at)
        order = sort_col.desc() if filters.sort_order == "desc" else sort_col.asc()
        query = query.order_by(order)
        return await self.paginate(query, filters.page, filters.page_size)

    async def update_playbook(self, playbook_id: str, tenant_id: str, **kwargs) -> Optional[LegalPlaybook]:
        playbook = await self.get_playbook(playbook_id, tenant_id)
        if not playbook:
            return None
        allowed = {"name", "description", "jurisdiction", "practice_area", "status", "tags", "metadata"}
        updates = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        if updates:
            stmt = update(LegalPlaybook).where(
                LegalPlaybook.playbook_id == playbook_id,
                LegalPlaybook.tenant_id == tenant_id,
            ).values(**updates)
            await self.session.execute(stmt)
            await self.session.flush()
        return await self.get_playbook(playbook_id, tenant_id)

    async def publish_playbook(self, playbook_id: str, tenant_id: str,
                                published_by: str, version_label: Optional[str] = None,
                                change_notes: Optional[str] = None) -> Optional[PlaybookVersion]:
        """Publish the current draft version as active."""
        playbook = await self.get_playbook(playbook_id, tenant_id)
        if not playbook:
            return None

        # Get current draft version
        stmt = select(PlaybookVersion).where(
            PlaybookVersion.playbook_id == playbook_id,
            PlaybookVersion.tenant_id == tenant_id,
            PlaybookVersion.is_draft == True,
        ).order_by(PlaybookVersion.version_number.desc()).limit(1)
        result = await self.session.execute(stmt)
        version = result.scalar_one_or_none()

        if not version:
            return None

        # Mark version as published
        now = datetime.utcnow()
        version.is_draft = False
        version.is_active = True
        version.published_by = published_by
        version.published_at = now
        version.version_label = version_label
        version.change_notes = change_notes

        # Snapshot current state
        version.snapshot = {
            "name": playbook.name,
            "description": playbook.description,
            "jurisdiction": playbook.jurisdiction,
            "practice_area": playbook.practice_area,
            "tags": playbook.tags,
            "metadata": playbook.metadata,
            "published_at": now.isoformat(),
        }

        # Update playbook status
        playbook.status = PlaybookStatus.PUBLISHED
        playbook.active_version_id = version.version_id
        playbook.version_count += 1

        await self.session.flush()
        return version

    async def create_draft_version(self, playbook_id: str, tenant_id: str,
                                    created_by: str) -> Optional[PlaybookVersion]:
        """Create a new draft version based on the current active version."""
        playbook = await self.get_playbook(playbook_id, tenant_id)
        if not playbook:
            return None

        # Find current max version number
        stmt = select(func.max(PlaybookVersion.version_number)).where(
            PlaybookVersion.playbook_id == playbook_id,
            PlaybookVersion.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        max_version = result.scalar() or 0

        # Find active version for lineage
        active_version = None
        if playbook.active_version_id:
            av_stmt = select(PlaybookVersion).where(
                PlaybookVersion.version_id == playbook.active_version_id,
            )
            av_result = await self.session.execute(av_stmt)
            active_version = av_result.scalar_one_or_none()

        version = PlaybookVersion(
            playbook_id=playbook_id, tenant_id=tenant_id,
            version_number=max_version + 1,
            is_draft=True, is_active=False,
            parent_version_id=active_version.version_id if active_version else None,
            created_by=created_by,
        )
        self.session.add(version)
        await self.session.flush()

        playbook.status = PlaybookStatus.DRAFT
        playbook.active_version_id = version.version_id
        return version

    async def rollback_to_version(self, playbook_id: str, tenant_id: str,
                                   target_version_id: str) -> Optional[PlaybookVersion]:
        """Rollback playbook to a specific version."""
        playbook = await self.get_playbook(playbook_id, tenant_id)
        if not playbook:
            return None

        stmt = select(PlaybookVersion).where(
            PlaybookVersion.version_id == target_version_id,
            PlaybookVersion.playbook_id == playbook_id,
            PlaybookVersion.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        target = result.scalar_one_or_none()
        if not target:
            return None

        # Deactivate current active
        if playbook.active_version_id:
            deact = update(PlaybookVersion).where(
                PlaybookVersion.version_id == playbook.active_version_id,
            ).values(is_active=False)
            await self.session.execute(deact)

        # Reactivate target
        target.is_active = True
        target.is_draft = False
        playbook.active_version_id = target.version_id
        playbook.status = PlaybookStatus.PUBLISHED
        await self.session.flush()
        return target

    async def list_versions(self, playbook_id: str, tenant_id: str) -> tuple[list[PlaybookVersion], int]:
        stmt = select(PlaybookVersion).where(
            PlaybookVersion.playbook_id == playbook_id,
            PlaybookVersion.tenant_id == tenant_id,
        ).order_by(PlaybookVersion.version_number.desc())
        result = await self.session.execute(stmt)
        items = result.scalars().all()
        return items, len(items)

    # ── Clause Standards ───────────────────────────────────────────

    async def create_clause(self, playbook_id: str, tenant_id: str, created_by: str,
                             **kwargs) -> ClauseStandard:
        clause = ClauseStandard(
            playbook_id=playbook_id, tenant_id=tenant_id,
            created_by=created_by, **kwargs,
        )
        self.session.add(clause)
        await self.session.flush()
        return clause

    async def get_clause(self, clause_id: str, tenant_id: str) -> Optional[ClauseStandard]:
        stmt = select(ClauseStandard).where(
            ClauseStandard.clause_id == clause_id,
            ClauseStandard.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_clauses(self, tenant_id: str, playbook_id: str, filters) -> tuple[list, int]:
        query = select(ClauseStandard).where(
            ClauseStandard.tenant_id == tenant_id,
            ClauseStandard.playbook_id == playbook_id,
        )
        if filters.category:
            query = query.where(ClauseStandard.category == filters.category)
        if filters.clause_type:
            query = query.where(ClauseStandard.clause_type == filters.clause_type)
        if filters.risk_level:
            query = query.where(ClauseStandard.risk_level == filters.risk_level)
        if filters.is_active is not None:
            query = query.where(ClauseStandard.is_active == filters.is_active)
        if filters.search:
            search = f"%{filters.search}%"
            query = query.where(
                or_(ClauseStandard.title.ilike(search), ClauseStandard.body.ilike(search))
            )
        sort_col = getattr(ClauseStandard, filters.sort_by, ClauseStandard.created_at)
        order = sort_col.desc() if filters.sort_order == "desc" else sort_col.asc()
        query = query.order_by(order)
        return await self.paginate(query, filters.page, filters.page_size)

    async def update_clause(self, clause_id: str, tenant_id: str, **kwargs) -> Optional[ClauseStandard]:
        clause = await self.get_clause(clause_id, tenant_id)
        if not clause:
            return None
        allowed = {"title", "body", "summary", "fallback_clause_ids", "min_contract_value",
                    "max_contract_value", "applicable_jurisdictions", "applicable_industries",
                    "risk_level", "risk_score", "tags", "metadata", "is_active",
                    "effective_date", "expiration_date"}
        updates = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        if updates:
            stmt = update(ClauseStandard).where(
                ClauseStandard.clause_id == clause_id,
                ClauseStandard.tenant_id == tenant_id,
            ).values(**updates)
            await self.session.execute(stmt)
            await self.session.flush()
        return await self.get_clause(clause_id, tenant_id)

    async def get_active_clauses_by_playbook(self, playbook_id: str, tenant_id: str,
                                              category: Optional[str] = None) -> list[ClauseStandard]:
        stmt = select(ClauseStandard).where(
            ClauseStandard.playbook_id == playbook_id,
            ClauseStandard.tenant_id == tenant_id,
            ClauseStandard.is_active == True,
        )
        if category:
            stmt = stmt.where(ClauseStandard.category == category)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ── Policy Rules ───────────────────────────────────────────────

    async def create_rule(self, playbook_id: str, tenant_id: str, created_by: str,
                           **kwargs) -> PolicyRule:
        rule = PolicyRule(
            playbook_id=playbook_id, tenant_id=tenant_id,
            created_by=created_by, **kwargs,
        )
        self.session.add(rule)
        await self.session.flush()
        return rule

    async def get_rule(self, rule_id: str, tenant_id: str) -> Optional[PolicyRule]:
        stmt = select(PolicyRule).where(
            PolicyRule.rule_id == rule_id,
            PolicyRule.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_rules(self, tenant_id: str, playbook_id: str, filters) -> tuple[list, int]:
        query = select(PolicyRule).where(
            PolicyRule.tenant_id == tenant_id,
            PolicyRule.playbook_id == playbook_id,
        )
        if filters.rule_type:
            query = query.where(PolicyRule.rule_type == filters.rule_type)
        if filters.effect:
            query = query.where(PolicyRule.effect == filters.effect)
        if filters.is_active is not None:
            query = query.where(PolicyRule.is_active == filters.is_active)
        if filters.is_mandatory is not None:
            query = query.where(PolicyRule.is_mandatory == filters.is_mandatory)
        if filters.search:
            search = f"%{filters.search}%"
            query = query.where(PolicyRule.name.ilike(search))
        sort_col = getattr(PolicyRule, filters.sort_by, PolicyRule.priority)
        order = sort_col.asc() if filters.sort_order == "asc" else sort_col.desc()
        query = query.order_by(order)
        return await self.paginate(query, filters.page, filters.page_size)

    async def update_rule(self, rule_id: str, tenant_id: str, **kwargs) -> Optional[PolicyRule]:
        rule = await self.get_rule(rule_id, tenant_id)
        if not rule:
            return None
        allowed = {"name", "description", "priority", "is_active", "is_mandatory",
                    "conditions", "effect", "effect_config", "target_clause_id",
                    "target_category", "applicable_jurisdictions", "applicable_industries",
                    "min_contract_value", "max_contract_value", "effective_date",
                    "expiration_date", "tags", "metadata"}
        updates = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        if updates:
            stmt = update(PolicyRule).where(
                PolicyRule.rule_id == rule_id,
                PolicyRule.tenant_id == tenant_id,
            ).values(**updates)
            await self.session.execute(stmt)
            await self.session.flush()
        return await self.get_rule(rule_id, tenant_id)

    async def get_active_rules_by_playbook(self, playbook_id: str, tenant_id: str) -> list[PolicyRule]:
        stmt = select(PolicyRule).where(
            PolicyRule.playbook_id == playbook_id,
            PolicyRule.tenant_id == tenant_id,
            PolicyRule.is_active == True,
        ).order_by(PolicyRule.priority.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ── Policy Evaluations ─────────────────────────────────────────

    async def create_evaluation(self, tenant_id: str, upload_id: str, **kwargs) -> PolicyEvaluation:
        eval_record = PolicyEvaluation(
            tenant_id=tenant_id, upload_id=upload_id, **kwargs,
        )
        self.session.add(eval_record)
        await self.session.flush()
        return eval_record

    async def get_evaluation(self, evaluation_id: str, tenant_id: str) -> Optional[PolicyEvaluation]:
        stmt = select(PolicyEvaluation).where(
            PolicyEvaluation.evaluation_id == evaluation_id,
            PolicyEvaluation.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_evaluation_by_upload(self, upload_id: str, tenant_id: str) -> Optional[PolicyEvaluation]:
        stmt = select(PolicyEvaluation).where(
            PolicyEvaluation.upload_id == upload_id,
            PolicyEvaluation.tenant_id == tenant_id,
        ).order_by(PolicyEvaluation.created_at.desc()).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_evaluations(self, tenant_id: str, filters) -> tuple[list, int]:
        query = select(PolicyEvaluation).where(PolicyEvaluation.tenant_id == tenant_id)
        if filters.status:
            query = query.where(PolicyEvaluation.status == filters.status)
        if filters.upload_id:
            query = query.where(PolicyEvaluation.upload_id == filters.upload_id)
        if filters.risk_level:
            query = query.where(PolicyEvaluation.risk_level == filters.risk_level)
        sort_col = getattr(PolicyEvaluation, filters.sort_by, PolicyEvaluation.created_at)
        order = sort_col.desc() if filters.sort_order == "desc" else sort_col.asc()
        query = query.order_by(order)
        return await self.paginate(query, filters.page, filters.page_size)

    async def update_evaluation(self, evaluation_id: str, tenant_id: str, **kwargs) -> Optional[PolicyEvaluation]:
        eval_record = await self.get_evaluation(evaluation_id, tenant_id)
        if not eval_record:
            return None
        allowed = {"status", "total_rules_evaluated", "rules_passed", "rules_failed",
                    "deviations_found", "mandatory_blocks", "approval_required",
                    "risk_score", "risk_level", "results", "deviations", "recommendations",
                    "correlation_id", "error_message", "started_at", "completed_at"}
        updates = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        if updates:
            stmt = update(PolicyEvaluation).where(
                PolicyEvaluation.evaluation_id == evaluation_id,
                PolicyEvaluation.tenant_id == tenant_id,
            ).values(**updates)
            await self.session.execute(stmt)
            await self.session.flush()
        return await self.get_evaluation(evaluation_id, tenant_id)

    # ── Approval Thresholds ────────────────────────────────────────

    async def create_threshold(self, playbook_id: str, tenant_id: str, created_by: str,
                                **kwargs) -> ApprovalThreshold:
        threshold = ApprovalThreshold(
            playbook_id=playbook_id, tenant_id=tenant_id,
            created_by=created_by, **kwargs,
        )
        self.session.add(threshold)
        await self.session.flush()
        return threshold

    async def get_threshold(self, threshold_id: str, tenant_id: str) -> Optional[ApprovalThreshold]:
        stmt = select(ApprovalThreshold).where(
            ApprovalThreshold.threshold_id == threshold_id,
            ApprovalThreshold.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_thresholds(self, tenant_id: str, playbook_id: str,
                               threshold_type: Optional[str] = None) -> tuple[list[ApprovalThreshold], int]:
        stmt = select(ApprovalThreshold).where(
            ApprovalThreshold.tenant_id == tenant_id,
            ApprovalThreshold.playbook_id == playbook_id,
        )
        if threshold_type:
            stmt = stmt.where(ApprovalThreshold.threshold_type == threshold_type)
        stmt = stmt.order_by(ApprovalThreshold.priority.asc())
        result = await self.session.execute(stmt)
        items = list(result.scalars().all())
        return items, len(items)

    async def update_threshold(self, threshold_id: str, tenant_id: str, **kwargs) -> Optional[ApprovalThreshold]:
        threshold = await self.get_threshold(threshold_id, tenant_id)
        if not threshold:
            return None
        allowed = {"name", "description", "operator", "min_value", "max_value",
                    "target_category", "approval_role", "approval_level",
                    "fallback_approval_role", "auto_approve", "auto_approve_conditions",
                    "sla_hours", "is_active", "priority"}
        updates = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
        if updates:
            stmt = update(ApprovalThreshold).where(
                ApprovalThreshold.threshold_id == threshold_id,
                ApprovalThreshold.tenant_id == tenant_id,
            ).values(**updates)
            await self.session.execute(stmt)
            await self.session.flush()
        return await self.get_threshold(threshold_id, tenant_id)

    async def get_active_thresholds_by_playbook(self, playbook_id: str, tenant_id: str) -> list[ApprovalThreshold]:
        stmt = select(ApprovalThreshold).where(
            ApprovalThreshold.playbook_id == playbook_id,
            ApprovalThreshold.tenant_id == tenant_id,
            ApprovalThreshold.is_active == True,
        ).order_by(ApprovalThreshold.priority.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ── Clause Recommendations ─────────────────────────────────────

    async def create_recommendation(self, **kwargs) -> ClauseRecommendation:
        rec = ClauseRecommendation(**kwargs)
        self.session.add(rec)
        await self.session.flush()
        return rec

    async def bulk_create_recommendations(self, recommendations: list[dict]) -> list[ClauseRecommendation]:
        recs = [ClauseRecommendation(**r) for r in recommendations]
        for r in recs:
            self.session.add(r)
        await self.session.flush()
        return recs

    async def get_recommendations_by_evaluation(self, evaluation_id: str, tenant_id: str) -> list[ClauseRecommendation]:
        stmt = select(ClauseRecommendation).where(
            ClauseRecommendation.evaluation_id == evaluation_id,
            ClauseRecommendation.tenant_id == tenant_id,
        ).order_by(ClauseRecommendation.priority.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def mark_recommendation_applied(self, recommendation_id: str, tenant_id: str,
                                           applied_by: str) -> Optional[ClauseRecommendation]:
        stmt = update(ClauseRecommendation).where(
            ClauseRecommendation.recommendation_id == recommendation_id,
            ClauseRecommendation.tenant_id == tenant_id,
        ).values(is_applied=True, applied_at=datetime.utcnow(), applied_by=applied_by)
        await self.session.execute(stmt)
        await self.session.flush()
        return await self.session.execute(
            select(ClauseRecommendation).where(
                ClauseRecommendation.recommendation_id == recommendation_id,
                ClauseRecommendation.tenant_id == tenant_id,
            )
        ).then(lambda r: r.scalar_one_or_none())

    # ── Policy Overrides ───────────────────────────────────────────

    async def create_override(self, tenant_id: str, requested_by: str, **kwargs) -> PolicyOverride:
        override = PolicyOverride(
            tenant_id=tenant_id, requested_by=requested_by, **kwargs,
        )
        self.session.add(override)
        await self.session.flush()
        return override

    async def get_override(self, override_id: str, tenant_id: str) -> Optional[PolicyOverride]:
        stmt = select(PolicyOverride).where(
            PolicyOverride.override_id == override_id,
            PolicyOverride.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_overrides(self, tenant_id: str, filters) -> tuple[list, int]:
        query = select(PolicyOverride).where(PolicyOverride.tenant_id == tenant_id)
        if filters.status:
            query = query.where(PolicyOverride.status == filters.status)
        if filters.override_type:
            query = query.where(PolicyOverride.override_type == filters.override_type)
        if filters.upload_id:
            query = query.where(PolicyOverride.upload_id == filters.upload_id)
        sort_col = getattr(PolicyOverride, filters.sort_by, PolicyOverride.created_at)
        order = sort_col.desc() if filters.sort_order == "desc" else sort_col.asc()
        query = query.order_by(order)
        return await self.paginate(query, filters.page, filters.page_size)

    async def update_override_status(self, override_id: str, tenant_id: str,
                                      status: OverrideStatus, reviewed_by: str,
                                      review_notes: Optional[str] = None) -> Optional[PolicyOverride]:
        stmt = update(PolicyOverride).where(
            PolicyOverride.override_id == override_id,
            PolicyOverride.tenant_id == tenant_id,
        ).values(
            status=status, reviewed_by=reviewed_by,
            reviewed_at=datetime.utcnow(), review_notes=review_notes,
        )
        await self.session.execute(stmt)
        await self.session.flush()
        return await self.get_override(override_id, tenant_id)

    # ── Governance Audit Events ────────────────────────────────────

    async def create_audit_event(self, tenant_id: str, event_type: str, entity_type: str,
                                  entity_id: str, actor_id: str, actor_role: Optional[str] = None,
                                  previous_state: Optional[dict] = None,
                                  new_state: Optional[dict] = None,
                                  change_summary: Optional[str] = None,
                                  correlation_id: Optional[str] = None,
                                  request_id: Optional[str] = None,
                                  source: str = "api",
                                  metadata: Optional[dict] = None) -> GovernanceAuditEvent:
        event = GovernanceAuditEvent(
            tenant_id=tenant_id, event_type=event_type,
            entity_type=entity_type, entity_id=entity_id,
            actor_id=actor_id, actor_role=actor_role,
            previous_state=previous_state, new_state=new_state,
            change_summary=change_summary, correlation_id=correlation_id,
            request_id=request_id, source=source,
            metadata=metadata or {},
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def list_audit_events(self, tenant_id: str, filters) -> tuple[list, int]:
        query = select(GovernanceAuditEvent).where(GovernanceAuditEvent.tenant_id == tenant_id)
        if filters.event_type:
            query = query.where(GovernanceAuditEvent.event_type == filters.event_type)
        if filters.entity_type:
            query = query.where(GovernanceAuditEvent.entity_type == filters.entity_type)
        if filters.entity_id:
            query = query.where(GovernanceAuditEvent.entity_id == filters.entity_id)
        if filters.actor_id:
            query = query.where(GovernanceAuditEvent.actor_id == filters.actor_id)
        if filters.date_from:
            query = query.where(GovernanceAuditEvent.created_at >= filters.date_from)
        if filters.date_to:
            query = query.where(GovernanceAuditEvent.created_at <= filters.date_to)
        sort_col = getattr(GovernanceAuditEvent, filters.sort_by, GovernanceAuditEvent.created_at)
        order = sort_col.desc() if filters.sort_order == "desc" else sort_col.asc()
        query = query.order_by(order)
        return await self.paginate(query, filters.page, filters.page_size)
