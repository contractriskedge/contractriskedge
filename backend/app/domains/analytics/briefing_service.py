"""Executive Briefing Generator — LLM-powered operational intelligence briefings.

Generates natural-language executive briefings by composing data from:
- ExecutiveAnalyticsService (dashboard metrics, anomalies, trends)
- DigestGenerator (portfolio snapshot)
- NarrativeGenerator (trend narratives)
- OpenAI provider (narrative synthesis)

Supports:
- Daily executive briefing
- Risk escalation summary
- KPI change explanation
- Anomaly spike analysis
- Root cause identification
- Operational recommendations
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.domains.analytics.executive_service import ExecutiveAnalyticsService
from app.domains.analytics.reporting_service import DigestGenerator, NarrativeGenerator, AnomalyDetector
from app.domains.analytics.reporting_schemas import (
    DigestStyle,
    ExecutiveDigest,
    AnomalyDetectionResult,
    TrendNarrativeSet,
)
from app.domains.analytics.executive_schemas import ExecutiveDashboard
from app.domains.ai.llm import OpenAIProvider, LLMRequest, LLMResponse, llm_registry
from app.domains.ai.prompts import prompt_registry, PromptTemplate

logger = logging.getLogger(__name__)

BRIEFING_SYSTEM_PROMPT = """You are an executive intelligence analyst for an enterprise contract risk platform.

You generate concise, insight-dense operational briefings for C-level executives.

Your briefings must be:
1. FACTUAL — only reference data provided in the context
2. SPECIFIC — use actual numbers, percentages, and trends
3. ACTIONABLE — include clear recommendations
4. CONCISE — executives need the key insight in under 30 seconds
5. CONFIDENCE-AWARE — indicate when data is uncertain or anomalous

Focus on:
- What changed since the last period
- What requires immediate attention
- What trends are emerging
- What actions are recommended
- What risks are escalating

Format structure:
- Executive Summary (2-3 sentences)
- Key Metrics (table-style with changes)
- Critical Alerts (what needs attention now)
- Trend Analysis (what's changing)
- Recommendations (specific actions)
- Risk Escalations (what to watch)"""


@dataclass
class ExecutiveBriefingGenerator:
    """Generates LLM-powered executive briefings from operational data."""

    session: AsyncSession
    tenant_id: str

    async def generate_briefing(
        self,
        style: DigestStyle = DigestStyle.STANDARD,
        lookback_days: int = 7,
        include_recommendations: bool = True,
    ) -> ExecutiveBriefing:
        """Generate a complete executive briefing with LLM narrative synthesis."""
        executive_service = ExecutiveAnalyticsService(session=self.session, tenant_id=self.tenant_id)
        digest_generator = DigestGenerator(session=self.session, tenant_id=self.tenant_id)
        narrative_generator = NarrativeGenerator(session=self.session, tenant_id=self.tenant_id)
        anomaly_detector = AnomalyDetector(session=self.session, tenant_id=self.tenant_id)

        # 1. Gather all operational data in parallel
        dashboard = await executive_service.get_dashboard(lookback_days=lookback_days)
        digest = await digest_generator.generate_digest(
            style=style,
            lookback_days=lookback_days,
        )
        narratives = await narrative_generator.generate_narratives(lookback_days=lookback_days)
        anomalies = await anomaly_detector.detect_anomalies(lookback_hours=lookback_days * 24)

        # 2. Build structured context for the LLM
        context = self._build_briefing_context(
            dashboard=dashboard,
            digest=digest,
            narratives=narratives,
            anomalies=anomalies,
            lookback_days=lookback_days,
        )

        # 3. Generate LLM narrative
        llm_result = await self._generate_llm_narrative(context, style, include_recommendations)

        # 4. Compose final briefing
        return ExecutiveBriefing(
            tenant_id=self.tenant_id,
            generated_at=datetime.utcnow(),
            period_days=lookback_days,
            style=style,
            portfolio_snapshot=digest.portfolio_snapshot,
            key_metrics=digest.key_metrics,
            anomalies=anomalies,
            narratives=narratives,
            executive_summary=llm_result.executive_summary,
            key_findings=llm_result.key_findings,
            recommendations=llm_result.recommendations if include_recommendations else [],
            risk_escalations=llm_result.risk_escalations,
            model=llm_result.model,
            prompt_version=llm_result.prompt_version,
            total_tokens=llm_result.total_tokens,
            cost_usd=llm_result.cost_usd,
            latency_ms=llm_result.latency_ms,
        )

    async def generate_risk_escalation(
        self,
        anomaly: Optional[AnomalyDetectionResult] = None,
        lookback_days: int = 1,
    ) -> RiskEscalationBriefing:
        """Generate a focused risk escalation briefing for urgent situations."""
        executive_service = ExecutiveAnalyticsService(session=self.session, tenant_id=self.tenant_id)

        dashboard = await executive_service.get_dashboard(lookback_days=lookback_days)

        if not anomaly:
            anomaly_detector = AnomalyDetector(session=self.session, tenant_id=self.tenant_id)
            anomaly = await anomaly_detector.detect_anomalies(lookback_hours=lookback_days * 24)

        context = self._build_escalation_context(dashboard, anomaly)
        llm_result = await self._generate_escalation_narrative(context)

        return RiskEscalationBriefing(
            tenant_id=self.tenant_id,
            generated_at=datetime.utcnow(),
            period_hours=lookback_days * 24,
            anomaly_summary=anomaly,
            executive_summary=llm_result.executive_summary,
            root_causes=llm_result.root_causes,
            recommended_actions=llm_result.recommendations,
            impact_assessment=llm_result.impact_assessment,
            model=llm_result.model,
            prompt_version=llm_result.prompt_version,
        )

    def _build_briefing_context(
        self,
        dashboard: ExecutiveDashboard,
        digest: ExecutiveDigest,
        narratives: TrendNarrativeSet,
        anomalies: AnomalyDetectionResult,
        lookback_days: int,
    ) -> dict:
        """Build structured context dict for LLM briefing generation."""
        ps = dashboard.portfolio_summary
        sla = dashboard.sla_risk_overview
        bottlenecks = dashboard.throughput_bottlenecks
        exposure = dashboard.contract_exposure

        return {
            "period": f"Last {lookback_days} days",
            "portfolio": {
                "total_contracts": ps.total_contracts,
                "active_reviews": ps.active_reviews,
                "avg_risk_score": round(ps.avg_risk_score, 2),
                "critical_contracts": ps.critical_contracts,
                "high_risk_vendors": ps.high_risk_vendors,
                "risk_distribution": ps.risk_distribution.model_dump() if hasattr(ps.risk_distribution, "model_dump") else {},
                "total_exposure": round(ps.total_exposure, 2),
            },
            "sla_risk": {
                "total_active": sla.total_active_reviews,
                "at_risk": sla.at_risk,
                "critical": sla.critical,
                "breached": sla.breached,
                "predicted_breaches_7d": sla.breach_prediction.predicted_breaches_next_7d,
                "predicted_breaches_30d": sla.breach_prediction.predicted_breaches_next_30d,
            },
            "bottlenecks": {
                "queue_depth": bottlenecks.queue_depth,
                "avg_wait_hours": round(bottlenecks.avg_wait_time_hours, 1),
                "throughput": round(bottlenecks.overall_throughput, 2),
                "bottleneck_count": len(bottlenecks.bottlenecks),
                "critical_bottlenecks": sum(1 for b in bottlenecks.bottlenecks if b.severity == "critical"),
            },
            "exposure": {
                "total_score": round(exposure.total_exposure_score, 2),
                "concentration_risk": exposure.concentration_risk,
                "top_drivers": [{"clause": d.clause_type, "contribution": round(d.contribution_pct, 1)} for d in exposure.top_risk_drivers[:3]],
            },
            "anomalies": {
                "total": anomalies.total_anomalies if hasattr(anomalies, "total_anomalies") else len(getattr(anomalies, "anomalies", [])),
                "critical": anomalies.critical_count if hasattr(anomalies, "critical_count") else 0,
                "types": list(set(getattr(a, "type", "unknown") for a in getattr(anomalies, "anomalies", []))),
            },
            "narratives": narratives.model_dump() if hasattr(narratives, "model_dump") else {},
        }

    def _build_escalation_context(self, dashboard: ExecutiveDashboard, anomaly: AnomalyDetectionResult) -> dict:
        """Build focused context for risk escalation briefings."""
        sla = dashboard.sla_risk_overview
        bottlenecks = dashboard.throughput_bottlenecks
        exposure = dashboard.contract_exposure

        return {
            "sla_critical": sla.critical,
            "sla_breached": sla.breached,
            "bottleneck_critical": sum(1 for b in bottlenecks.bottlenecks if b.severity == "critical"),
            "queue_depth": bottlenecks.queue_depth,
            "exposure_score": round(exposure.total_exposure_score, 2),
            "concentration_risk": exposure.concentration_risk,
            "anomalies": [{"type": getattr(a, "type", "unknown"), "severity": getattr(a, "severity", "medium"), "title": getattr(a, "title", "")} for a in getattr(anomaly, "anomalies", [])[:5]],
        }

    async def _generate_llm_narrative(
        self,
        context: dict,
        style: DigestStyle,
        include_recommendations: bool,
    ) -> LLMBriefingResult:
        """Generate narrative content via OpenAI."""
        import time
        start = time.monotonic()

        provider = llm_registry.get("openai")
        if not provider:
            provider = OpenAIProvider(api_key=settings.openai_api_key)
            llm_registry.register(provider)

        style_instruction = {
            DigestStyle.BRIEF: "Provide a very concise briefing (2-3 sentences per section).",
            DigestStyle.STANDARD: "Provide a standard briefing with moderate detail.",
            DigestStyle.DETAILED: "Provide a comprehensive briefing with full analysis.",
        }.get(style, "Provide a standard briefing.")

        user_prompt = f"""Generate an executive briefing for the following operational data.

{style_instruction}

Context:
{json.dumps(context, indent=2, default=str)}

{"Include specific, actionable recommendations based on the data." if include_recommendations else "Focus on analysis only, not recommendations."}

Respond in JSON format with these fields:
- executive_summary: string (2-3 sentence overview)
- key_findings: array of {findings: string, severity: string, impact: string} objects
- recommendations: array of {action: string, priority: string, expected_impact: string} objects
- risk_escalations: array of {risk: string, severity: string, timeframe: string, mitigation: string} objects"""

        request = LLMRequest(
            system_prompt=BRIEFING_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            model="gpt-4o",
            temperature=0.3,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )

        try:
            response: LLMResponse = await provider.generate(request)
            parsed = self._parse_llm_response(response.text)
            elapsed_ms = int((time.monotonic() - start) * 1000)

            return LLMBriefingResult(
                executive_summary=parsed.get("executive_summary", "Briefing generated."),
                key_findings=parsed.get("key_findings", []),
                recommendations=parsed.get("recommendations", []),
                risk_escalations=parsed.get("risk_escalations", []),
                impact_assessment="",
                root_causes=[],
                model=response.model or "gpt-4o",
                prompt_version=2,
                total_tokens=response.total_tokens or 0,
                cost_usd=response.cost_usd or 0.0,
                latency_ms=elapsed_ms,
            )
        except Exception as exc:
            logger.error("LLM briefing generation failed: %s", exc)
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return self._fallback_briefing(context, str(exc), elapsed_ms)

    async def _generate_escalation_narrative(self, context: dict) -> LLMBriefingResult:
        """Generate focused escalation narrative."""
        import time
        start = time.monotonic()

        provider = llm_registry.get("openai")
        if not provider:
            provider = OpenAIProvider(api_key=settings.openai_api_key)
            llm_registry.register(provider)

        user_prompt = f"""URGENT: Generate a risk escalation briefing for the following operational situation.

Context:
{json.dumps(context, indent=2, default=str)}

Respond in JSON format with these fields:
- executive_summary: string (urgent overview, 2-3 sentences)
- root_causes: array of {cause: string, confidence: string, evidence: string} objects
- recommendations: array of {action: string, priority: string, owner: string} objects
- impact_assessment: string (business impact description)"""

        request = LLMRequest(
            system_prompt=BRIEFING_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            model="gpt-4o",
            temperature=0.2,
            max_tokens=1500,
            response_format={"type": "json_object"},
        )

        try:
            response: LLMResponse = await provider.generate(request)
            parsed = self._parse_llm_response(response.text)
            elapsed_ms = int((time.monotonic() - start) * 1000)

            return LLMBriefingResult(
                executive_summary=parsed.get("executive_summary", "Risk escalation briefing."),
                key_findings=parsed.get("key_findings", []),
                recommendations=parsed.get("recommendations", []),
                risk_escalations=[],
                impact_assessment=parsed.get("impact_assessment", ""),
                root_causes=parsed.get("root_causes", []),
                model=response.model or "gpt-4o",
                prompt_version=2,
                total_tokens=response.total_tokens or 0,
                cost_usd=response.cost_usd or 0.0,
                latency_ms=elapsed_ms,
            )
        except Exception as exc:
            logger.error("LLM escalation briefing failed: %s", exc)
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return self._fallback_escalation(str(exc), elapsed_ms)

    def _parse_llm_response(self, text: str) -> dict:
        """Parse JSON from LLM response with fallback."""
        import re
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass
            return {}

    def _fallback_briefing(self, context: dict, error: str, elapsed_ms: int) -> LLMBriefingResult:
        """Return a data-driven fallback when LLM is unavailable."""
        portfolio = context.get("portfolio", {})
        sla = context.get("sla_risk", {})
        bottlenecks = context.get("bottlenecks", {})

        summary_parts = []
        if portfolio.get("total_contracts"):
            summary_parts.append(f"Portfolio contains {portfolio['total_contracts']} contracts with {portfolio['active_reviews']} active reviews.")
        if sla.get("at_risk"):
            summary_parts.append(f"{sla['at_risk']} reviews at SLA risk, {sla['breached']} breached.")
        if bottlenecks.get("critical_bottlenecks"):
            summary_parts.append(f"{bottlenecks['critical_bottlenecks']} critical bottlenecks detected.")

        return LLMBriefingResult(
            executive_summary=" ".join(summary_parts) or "Operational data available. AI briefing unavailable.",
            key_findings=[{"finding": f"AI briefing unavailable: {error}", "severity": "info", "impact": "Briefing generated from structured data only"}],
            recommendations=[],
            risk_escalations=[],
            impact_assessment="",
            root_causes=[],
            model="fallback-rule-based",
            prompt_version=1,
            total_tokens=0,
            cost_usd=0.0,
            latency_ms=elapsed_ms,
        )

    def _fallback_escalation(self, error: str, elapsed_ms: int) -> LLMBriefingResult:
        return LLMBriefingResult(
            executive_summary=f"Risk escalation briefing unavailable. {error}",
            key_findings=[],
            recommendations=[],
            risk_escalations=[],
            impact_assessment="Unable to generate impact assessment.",
            root_causes=[],
            model="fallback-rule-based",
            prompt_version=1,
            total_tokens=0,
            cost_usd=0.0,
            latency_ms=elapsed_ms,
        )


# ── Data Types ────────────────────────────────────────────────────


class ExecutiveBriefing:
    """Complete executive briefing with LLM narrative synthesis."""
    def __init__(
        self,
        tenant_id: str,
        generated_at: datetime,
        period_days: int,
        style: DigestStyle,
        portfolio_snapshot: any,
        key_metrics: any,
        anomalies: AnomalyDetectionResult,
        narratives: TrendNarrativeSet,
        executive_summary: str,
        key_findings: list,
        recommendations: list,
        risk_escalations: list,
        model: str,
        prompt_version: int,
        total_tokens: int,
        cost_usd: float,
        latency_ms: int,
    ):
        self.tenant_id = tenant_id
        self.generated_at = generated_at
        self.period_days = period_days
        self.style = style
        self.portfolio_snapshot = portfolio_snapshot
        self.key_metrics = key_metrics
        self.anomalies = anomalies
        self.narratives = narratives
        self.executive_summary = executive_summary
        self.key_findings = key_findings
        self.recommendations = recommendations
        self.risk_escalations = risk_escalations
        self.model = model
        self.prompt_version = prompt_version
        self.total_tokens = total_tokens
        self.cost_usd = cost_usd
        self.latency_ms = latency_ms

    def to_dict(self) -> dict:
        return {
            "tenant_id": self.tenant_id,
            "generated_at": self.generated_at.isoformat(),
            "period_days": self.period_days,
            "style": self.style.value if hasattr(self.style, "value") else str(self.style),
            "portfolio_snapshot": self.portfolio_snapshot,
            "key_metrics": self.key_metrics,
            "anomalies": self.anomalies,
            "narratives": self.narratives,
            "executive_summary": self.executive_summary,
            "key_findings": self.key_findings,
            "recommendations": self.recommendations,
            "risk_escalations": self.risk_escalations,
            "model": self.model,
            "prompt_version": self.prompt_version,
            "total_tokens": self.total_tokens,
            "cost_usd": self.cost_usd,
            "latency_ms": self.latency_ms,
        }


class RiskEscalationBriefing:
    """Focused risk escalation briefing for urgent situations."""
    def __init__(
        self,
        tenant_id: str,
        generated_at: datetime,
        period_hours: int,
        anomaly_summary: AnomalyDetectionResult,
        executive_summary: str,
        root_causes: list,
        recommended_actions: list,
        impact_assessment: str,
        model: str,
        prompt_version: int,
    ):
        self.tenant_id = tenant_id
        self.generated_at = generated_at
        self.period_hours = period_hours
        self.anomaly_summary = anomaly_summary
        self.executive_summary = executive_summary
        self.root_causes = root_causes
        self.recommended_actions = recommended_actions
        self.impact_assessment = impact_assessment
        self.model = model
        self.prompt_version = prompt_version

    def to_dict(self) -> dict:
        return {
            "tenant_id": self.tenant_id,
            "generated_at": self.generated_at.isoformat(),
            "period_hours": self.period_hours,
            "anomaly_summary": self.anomaly_summary,
            "executive_summary": self.executive_summary,
            "root_causes": self.root_causes,
            "recommended_actions": self.recommended_actions,
            "impact_assessment": self.impact_assessment,
            "model": self.model,
            "prompt_version": self.prompt_version,
        }


@dataclass
class LLMBriefingResult:
    """Structured result from LLM briefing generation."""
    executive_summary: str
    key_findings: list
    recommendations: list
    risk_escalations: list
    impact_assessment: str
    root_causes: list
    model: str
    prompt_version: int
    total_tokens: int
    cost_usd: float
    latency_ms: int
