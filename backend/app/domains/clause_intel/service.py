"""Clause Intelligence service — CRUD, AI analysis, benchmarking, and analytics."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, delete, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.clause_intel.models import (
    Clause, ClauseVersion, ClauseEmbedding, ClauseBenchmark,
    NegotiationHistory, ClauseUsage, FallbackClause,
)
from app.domains.clause_intel.schemas import (
    ClauseCreate, ClauseUpdate, ClauseResponse, ClauseKpiResponse,
    BenchmarkResponse, FallbackVariantResponse, NegotiationHistoryResponse,
    SimilarityResult, DeviationResponse,
)
from app.domains.playbook.models import LegalPlaybook

logger = logging.getLogger(__name__)


class ClauseService:
    """Service layer for clause intelligence operations."""

    def __init__(self, session: AsyncSession, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id

    async def list_clauses(self, page=1, page_size=20, category=None, search=None,
                           approval_status=None, risk_level=None, sort_by="updated_at", sort_order="desc"):
        query = select(Clause).where(Clause.tenant_id == uuid.UUID(self.tenant_id))
        if category:
            query = query.where(Clause.category == category)
        if search:
            q = f"%{search}%"
            query = query.where(or_(Clause.name.ilike(q), Clause.text.ilike(q)))
        if approval_status:
            query = query.where(Clause.approval_status == approval_status)
        if risk_level:
            query = query.where(Clause.risk_level == risk_level)
        count_q = select(func.count()).select_from(query.subquery())
        total = await self.session.scalar(count_q) or 0
        sort_col = getattr(Clause, sort_by, Clause.updated_at)
        order = sort_col.desc() if sort_order == "desc" else sort_col.asc()
        query = query.order_by(order).offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(query)
        clauses = result.scalars().all()
        return [self._to_response(c) for c in clauses], total

    async def get_clause(self, clause_id: str) -> Optional[ClauseResponse]:
        c = await self.session.get(Clause, uuid.UUID(clause_id))
        return self._to_response(c) if c else None

    async def create_clause(self, data: ClauseCreate) -> ClauseResponse:
        c = Clause(
            clause_id=uuid.uuid4(), tenant_id=uuid.UUID(self.tenant_id),
            name=data.name, category=data.category, clause_type=data.clause_type,
            text=data.text, jurisdiction=data.jurisdiction,
            contract_types=data.contract_types or [],
            risk_score=data.risk_score, owner=data.owner,
            tags=data.tags or [], governance_notes=data.governance_notes,
        )
        self.session.add(c)
        await self.session.commit()
        await self.session.refresh(c)
        return self._to_response(c)

    async def update_clause(self, clause_id: str, data: ClauseUpdate) -> Optional[ClauseResponse]:
        c = await self.session.get(Clause, uuid.UUID(clause_id))
        if not c:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for key, val in update_data.items():
            setattr(c, key, val)
        c.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(c)
        return self._to_response(c)

    async def delete_clause(self, clause_id: str) -> bool:
        c = await self.session.get(Clause, uuid.UUID(clause_id))
        if not c:
            return False
        await self.session.delete(c)
        await self.session.commit()
        return True

    async def get_kpis(self) -> ClauseKpiResponse:
        base = select(Clause).where(Clause.tenant_id == uuid.UUID(self.tenant_id))
        total = await self.session.scalar(select(func.count()).select_from(base.subquery())) or 0
        approved = await self.session.scalar(select(func.count()).select_from(base.where(Clause.approval_status == "approved").subquery())) or 0
        pending = await self.session.scalar(select(func.count()).select_from(base.where(Clause.approval_status == "pending_review").subquery())) or 0
        deprecated = await self.session.scalar(select(func.count()).select_from(base.where(Clause.approval_status == "deprecated").subquery())) or 0
        scores = await self.session.execute(select(Clause.risk_score).where(Clause.tenant_id == uuid.UUID(self.tenant_id), Clause.risk_score.isnot(None)))
        all_scores = [r[0] for r in scores if r[0] is not None]
        avg_risk = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0
        confs = await self.session.execute(select(Clause.ai_confidence).where(Clause.tenant_id == uuid.UUID(self.tenant_id), Clause.ai_confidence.isnot(None)))
        all_conf = [r[0] for r in confs if r[0] is not None]
        avg_conf = round(sum(all_conf) / len(all_conf), 1) if all_conf else 0
        fb_count = await self.session.scalar(select(func.count()).select_from(select(FallbackClause).where(FallbackClause.tenant_id == uuid.UUID(self.tenant_id)).subquery())) or 0
        pb_count = await self.session.scalar(select(func.count()).select_from(select(LegalPlaybook).where(LegalPlaybook.tenant_id == uuid.UUID(self.tenant_id)).subquery())) or 0
        return ClauseKpiResponse(total_clauses=total, approved_count=approved, pending_review=pending, deprecated_count=deprecated, avg_risk_score=avg_risk, avg_ai_confidence=avg_conf, total_fallbacks=fb_count, total_playbooks=pb_count)

    async def get_benchmarks(self) -> list[BenchmarkResponse]:
        result = await self.session.execute(select(ClauseBenchmark).where(ClauseBenchmark.tenant_id == uuid.UUID(self.tenant_id)).order_by(ClauseBenchmark.category))
        return [BenchmarkResponse(category=b.category, market_median=b.market_median, market_p25=b.market_p25, market_p75=b.market_p75, sample_size=b.sample_size, avg_risk_score=b.avg_risk_score, acceptance_rate=b.acceptance_rate, deviation_rate=b.deviation_rate) for b in result.scalars().all()]

    async def get_fallback_variants(self, clause_id: str) -> list[FallbackVariantResponse]:
        c = await self.session.get(Clause, uuid.UUID(clause_id))
        if not c:
            return []
        result = await self.session.execute(select(FallbackClause).where(FallbackClause.tenant_id == uuid.UUID(self.tenant_id), FallbackClause.category == c.category).order_by(FallbackClause.is_preferred.desc(), FallbackClause.usage_rate.desc().nullslast()))
        return [FallbackVariantResponse(id=str(v.fallback_id), label=v.label, text=v.text, risk_score=v.risk_score, negotiation_strength=v.negotiation_strength, usage_rate=v.usage_rate, is_preferred=v.is_preferred, jurisdiction=v.jurisdiction) for v in result.scalars().all()]

    async def get_negotiation_history(self, clause_id: str) -> list[NegotiationHistoryResponse]:
        result = await self.session.execute(select(NegotiationHistory).where(NegotiationHistory.tenant_id == uuid.UUID(self.tenant_id), NegotiationHistory.clause_id == uuid.UUID(clause_id)).order_by(NegotiationHistory.created_at.desc()))
        return [NegotiationHistoryResponse(id=str(h.history_id), clause_id=str(h.clause_id), counterparty=h.counterparty, original_text=h.original_text, negotiated_text=h.negotiated_text, outcome=h.outcome, risk_delta=h.risk_delta, strategy_used=h.strategy_used, success=h.success, created_by=h.created_by, created_at=h.created_at.isoformat() if h.created_at else None) for h in result.scalars().all()]

    async def ai_review(self, text: str, category: str) -> dict:
        risk_score = self._score_clause_risk(text, category)
        risk_level = "critical" if risk_score >= 8 else "high" if risk_score >= 6 else "medium" if risk_score >= 4 else "low"
        return {"risk_score": risk_score, "risk_level": risk_level, "confidence": min(95, 50 + risk_score * 5), "explanation": self._generate_explanation(category, risk_score), "negotiation_strength": round(max(1, 10 - risk_score), 1), "negotiation_guidance": self._generate_guidance(category, risk_score), "compliance_warnings": self._check_compliance(category, text), "suggested_fallback": None, "escalation_triggers": self._escalation_triggers(risk_score)}

    def _score_clause_risk(self, text: str, category: str) -> float:
        high_risk = ["indemnify", "unlimited", "irrevocable", "sole discretion", "perpetual", "exclusive", "binding arbitration", "no liability"]
        medium_risk = ["reasonable", "material adverse", "best efforts", "time is of the essence", "represent and warrant"]
        text_lower = text.lower()
        score = 3.0
        for kw in high_risk:
            if kw in text_lower:
                score += 1.5
        for kw in medium_risk:
            if kw in text_lower:
                score += 0.8
        if category in {"indemnification", "limitation_of_liability", "confidentiality", "data_privacy"}:
            score += 1.0
        return round(min(10, max(1, score)), 1)

    def _generate_explanation(self, category: str, score: float) -> str:
        cat = category.replace("_", " ")
        if score >= 7:
            return f"High-risk {cat} clause detected. Contains aggressive language that may create significant liability exposure."
        if score >= 4:
            return f"Medium-risk {cat} clause. Contains some protective language that should be reviewed."
        return f"Low-risk {cat} clause. Generally aligns with market standards."

    def _generate_guidance(self, category: str, score: float) -> str:
        cat = category.replace("_", " ")
        if score >= 7:
            return f"Strongly recommend replacing this {cat} clause with approved fallback language."
        if score >= 4:
            return f"Review {cat} clause against playbook standards."
        return f"No action required. Clause aligns with standard {cat} language."

    def _check_compliance(self, category: str, text: str) -> list[str]:
        warnings = []
        checks = {"data_privacy": "GDPR/CCPA", "confidentiality": "data protection", "compliance": "regulatory", "indemnification": "liability caps"}
        if category in checks:
            warnings.append(f"Verify {checks[category]} compliance requirements")
        if "unlimited" in text.lower():
            warnings.append("Unlimited liability clause may violate policy limits")
        return warnings

    def _escalation_triggers(self, score: float) -> list[str]:
        if score >= 8:
            return ["Risk score exceeds threshold", "Requires legal review", "Playbook deviation detected"]
        if score >= 6:
            return ["Risk score exceeds warning threshold"]
        return []

    async def find_similar(self, text: str, category: Optional[str] = None, limit: int = 10) -> list[SimilarityResult]:
        query = select(Clause).where(Clause.tenant_id == uuid.UUID(self.tenant_id))
        if category:
            query = query.where(Clause.category == category)
        result = await self.session.execute(query.limit(50))
        clauses = result.scalars().all()
        scored = []
        text_lower = text.lower()
        for c in clauses:
            c_text_lower = (c.text or "").lower()
            common = len(set(text_lower.split()) & set(c_text_lower.split()))
            total = len(set(text_lower.split()) | set(c_text_lower.split()))
            similarity = round(common / total, 3) if total > 0 else 0
            scored.append((similarity, c))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [SimilarityResult(clause_id=str(c.clause_id), name=c.name, similarity=s, text=c.text[:200], category=c.category, risk_score=c.risk_score) for s, c in scored[:limit]]

    async def get_deviations(self) -> list[DeviationResponse]:
        result = await self.session.execute(select(Clause, ClauseBenchmark).join(ClauseBenchmark, and_(ClauseBenchmark.tenant_id == Clause.tenant_id, ClauseBenchmark.category == Clause.category)).where(Clause.tenant_id == uuid.UUID(self.tenant_id)))
        deviations = []
        for c, b in result.all():
            deviation = abs((c.risk_score or 0) - b.market_median)
            if deviation > 2:
                deviations.append(DeviationResponse(clause_id=str(c.clause_id), name=c.name, category=c.category, deviation_score=round(deviation, 1), market_median=b.market_median, your_score=c.risk_score or 0, risk_impact="higher risk than market" if (c.risk_score or 0) > b.market_median else "lower risk than market", recommendation=f"Review {c.category} clause for market alignment"))
        return deviations

    def _to_response(self, c: Clause) -> ClauseResponse:
        return ClauseResponse(id=str(c.clause_id), name=c.name, category=c.category, clause_type=c.clause_type, text=c.text, jurisdiction=c.jurisdiction, contract_types=c.contract_types or [], risk_score=c.risk_score, risk_level=c.risk_level, ai_confidence=c.ai_confidence, ai_explanation=c.ai_explanation, negotiation_strength=c.negotiation_strength, negotiation_guidance=c.negotiation_guidance, benchmark_percentile=c.benchmark_percentile, usage_frequency=c.usage_frequency or 0, approval_status=c.approval_status or "draft", owner=c.owner, version=c.version or 1, is_favorite=c.is_favorite or False, tags=c.tags or [], deviation_frequency=c.deviation_frequency or 0, market_percentile=c.market_percentile, playbook_linkage=c.playbook_linkage, governance_notes=c.governance_notes, created_at=c.created_at.isoformat() if c.created_at else None, updated_at=c.updated_at.isoformat() if c.updated_at else None)
