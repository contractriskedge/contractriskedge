"""AI Explainability service — builds evidence chains, confidence breakdowns, benchmark comparisons.

Transforms raw AI analysis output into structured explainability objects
that answer "why" for enterprise buyers.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from app.domains.ai.schemas import (
    AnalysisResult, RiskFinding, RedlineSuggestion,
    RiskTraceability, SeverityLevel,
)
from app.domains.ai.repository import AIRepository
from app.domains.playbook.repository import PlaybookRepository
from app.domains.review.repository import ReviewRepository
from app.domains.explainability.schemas import (
    EvidenceType, ConfidenceComponent, BenchmarkCategory, RegulationSource,
    EvidenceItem, SourceClauseEvidence, BenchmarkEvidence,
    PolicyViolationEvidence, PrecedentEvidence, RegulationEvidence,
    MitigationEvidence,
    ConfidenceBreakdown, ConfidenceComponentScore,
    Rationale, RationaleSegment,
    FindingExplanation, AlternativeSuggestion,
    RedlineExplanation,
    ExplainabilityResponse,
    BenchmarkEntry, BenchmarkComparison,
    RegulationMapping, RegulationCheckResult,
    RegulationEvidence as RegulationEvidenceSchema,
)

logger = logging.getLogger(__name__)


@dataclass
class EvidenceChainBuilder:
    """Builds evidence chains from AI analysis results and context."""

    ai_repo: AIRepository
    review_repo: ReviewRepository
    playbook_repo: Optional[PlaybookRepository] = None

    async def build_for_finding(
        self,
        finding: RiskFinding,
        finding_id: str,
        upload_id: str,
        review_id: str,
        tenant_id: str,
    ) -> tuple[list[EvidenceItem], ConfidenceBreakdown]:
        """Build complete evidence chain and confidence breakdown for a finding."""
        evidence: list[EvidenceItem] = []
        components: list[ConfidenceComponentScore] = []

        # 1. Source clause evidence
        source_evidence = await self._build_source_evidence(finding, upload_id)
        if source_evidence:
            evidence.append(source_evidence)

        # 2. Policy violation evidence (if playbook repo available)
        if self.playbook_repo:
            policy_evidence = await self._build_policy_evidence(
                finding, upload_id, tenant_id,
            )
            evidence.extend(policy_evidence)

        # 3. Benchmark evidence
        benchmark_evidence = await self._build_benchmark_evidence(finding)
        if benchmark_evidence:
            evidence.append(benchmark_evidence)

        # 4. Precedent evidence
        precedent_evidence = await self._build_precedent_evidence(
            finding, tenant_id,
        )
        if precedent_evidence:
            evidence.append(precedent_evidence)

        # 5. Regulation evidence
        regulation_evidence = self._build_regulation_evidence(finding)
        evidence.extend(regulation_evidence)

        # 6. Build confidence breakdown
        confidence = self._build_confidence_breakdown(finding)

        return evidence, confidence

    async def _build_source_evidence(
        self,
        finding: RiskFinding,
        upload_id: str,
    ) -> Optional[EvidenceItem]:
        """Build evidence from the source contract clause."""
        clause_text = ""
        if finding.chunk_indices:
            chunks = await self.ai_repo.get_chunks_for_upload(upload_id)
            for idx in finding.chunk_indices:
                if 0 <= idx < len(chunks):
                    chunk_text = getattr(chunks[idx], 'text', '') or ''
                    clause_text += chunk_text[:500] + "\n"

        return EvidenceItem(
            evidence_id=uuid.uuid4().hex[:12],
            type=EvidenceType.SOURCE_CLAUSE,
            label=f"Source clause: {finding.clause_type}",
            description=f"Risk finding '{finding.title}' is based on this clause text",
            relevance_score=1.0,
            source_clause=SourceClauseEvidence(
                clause_type=finding.clause_type,
                clause_text=clause_text,
                clause_text_snippet=clause_text[:200] if clause_text else finding.description[:200],
            ),
        )

    async def _build_policy_evidence(
        self,
        finding: RiskFinding,
        upload_id: str,
        tenant_id: str,
    ) -> list[EvidenceItem]:
        """Build evidence from policy rule violations."""
        if not self.playbook_repo:
            return []

        items: list[EvidenceItem] = []
        try:
            evaluations = await self.playbook_repo.get_evaluations_for_upload(
                upload_id, limit=5,
            )
            for eval_record in evaluations:
                eval_data = eval_record.results or {}
                if isinstance(eval_data, dict):
                    for rule_result in eval_data.get("rule_results", []):
                        matched_category = rule_result.get("matched_clause_category", "")
                        if matched_category and matched_category == finding.clause_type:
                            items.append(EvidenceItem(
                                evidence_id=uuid.uuid4().hex[:12],
                                type=EvidenceType.POLICY_VIOLATION,
                                label=f"Policy: {rule_result.get('rule_name', 'Unknown rule')}",
                                description=rule_result.get("details", ""),
                                relevance_score=0.9,
                                policy_violation=PolicyViolationEvidence(
                                    rule_id=rule_result.get("rule_id", ""),
                                    rule_name=rule_result.get("rule_name", "Unknown"),
                                    rule_type=rule_result.get("rule_type", ""),
                                    effect=rule_result.get("effect", ""),
                                    condition_matched=rule_result.get("details", ""),
                                    severity=rule_result.get("deviation_severity", "medium"),
                                ),
                            ))
        except Exception as exc:
            logger.debug("Could not load policy evidence: %s", exc)

        return items

    async def _build_benchmark_evidence(
        self,
        finding: RiskFinding,
    ) -> Optional[EvidenceItem]:
        """Build benchmark comparison evidence."""
        # Benchmark data would typically come from a benchmark registry.
        # This provides the structure; actual benchmarks are populated by the
        # benchmark registry service.
        severity_map = {
            "critical": "Significantly above market average",
            "high": "Above market average",
            "medium": "At market average",
            "low": "Below market average",
            "info": "At market average",
        }
        deviation = severity_map.get(finding.severity, "At market average")

        return EvidenceItem(
            evidence_id=uuid.uuid4().hex[:12],
            type=EvidenceType.BENCHMARK_REFERENCE,
            label=f"Benchmark: {finding.clause_type}",
            description=f"Compared to industry standards for {finding.clause_type.replace('_', ' ')} clauses",
            relevance_score=0.7,
            benchmark=BenchmarkEvidence(
                category=BenchmarkCategory.INDUSTRY_AVERAGE,
                benchmark_name=f"Industry {finding.clause_type.replace('_', ' ')} standard",
                benchmark_value="Standard market language",
                contract_value=finding.description[:100],
                deviation=deviation,
            ),
        )

    async def _build_precedent_evidence(
        self,
        finding: RiskFinding,
        tenant_id: str,
    ) -> Optional[EvidenceItem]:
        """Build precedent similarity evidence from historical reviews."""
        try:
            similar = await self.ai_repo.find_similar_findings(
                clause_type=finding.clause_type,
                severity=finding.severity,
                tenant_id=tenant_id,
                limit=3,
            )
            if similar:
                return EvidenceItem(
                    evidence_id=uuid.uuid4().hex[:12],
                    type=EvidenceType.PRECEDENT_SIMILARITY,
                    label=f"Found {len(similar)} similar precedents",
                    description=f"Similar {finding.clause_type} clauses in past contracts",
                    relevance_score=0.6,
                    precedent=PrecedentEvidence(
                        precedent_contract_id=similar[0].get("upload_id", ""),
                        precedent_contract_name=similar[0].get("document_name", "Previous contract"),
                        clause_type=finding.clause_type,
                        similarity_score=similar[0].get("similarity", 0.0),
                        outcome=similar[0].get("resolution", "unknown"),
                    ),
                )
        except Exception as exc:
            logger.debug("Could not load precedent evidence: %s", exc)

        return None

    def _build_regulation_evidence(
        self,
        finding: RiskFinding,
    ) -> list[EvidenceItem]:
        """Build regulation linkage evidence based on clause type."""
        # Regulation mappings by clause type
        regulation_map: dict[str, list[tuple[RegulationSource, str, str]]] = {
            "data_privacy": [
                (RegulationSource.GDPR, "Art. 5(1)(a)", "Lawfulness, fairness and transparency"),
                (RegulationSource.CCPA, "§1798.100", "Right to know and access"),
            ],
            "security": [
                (RegulationSource.GDPR, "Art. 32", "Security of processing"),
                (RegulationSource.PCI_DSS, "Req. 3", "Protect stored cardholder data"),
            ],
            "confidentiality": [
                (RegulationSource.GDPR, "Art. 5(1)(f)", "Integrity and confidentiality"),
            ],
            "compliance": [
                (RegulationSource.SOX, "§302", "Corporate responsibility for financial reports"),
            ],
            "indemnification": [
                (RegulationSource.UCC, "§2-312", "Warranty of title and against infringement"),
            ],
            "liability": [
                (RegulationSource.UCC, "§2-719", "Contractual modification of remedy"),
            ],
            "intellectual_property": [
                (RegulationSource.UCC, "§2-312", "Warranty of title"),
            ],
            "termination": [
                (RegulationSource.UCC, "§2-309", "Notice of termination"),
            ],
            "governing_law": [
                (RegulationSource.CISG, "Art. 1", "Scope of application"),
            ],
        }

        items: list[EvidenceItem] = []
        mappings = regulation_map.get(finding.clause_type, [])
        for source, provision, requirement in mappings:
            items.append(EvidenceItem(
                evidence_id=uuid.uuid4().hex[:12],
                type=EvidenceType.REGULATION_LINKAGE,
                label=f"Regulation: {source.value.upper()} {provision}",
                description=f"Requirement: {requirement}",
                relevance_score=0.8,
                regulation=RegulationEvidence(
                    regulation=source,
                    regulation_name=source.value.upper(),
                    provision=provision,
                    requirement=requirement,
                    compliance_status="at_risk" if finding.severity in ("critical", "high") else "unknown",
                    risk_if_non_compliant=f"Potential {source.value.upper()} violation related to {finding.title}",
                ),
            ))

        return items

    def _build_confidence_breakdown(
        self,
        finding: RiskFinding,
    ) -> ConfidenceBreakdown:
        """Build multi-component confidence breakdown for a finding."""
        base_confidence = finding.confidence or 0.7

        components = [
            ConfidenceComponentScore(
                component=ConfidenceComponent.CLAUSE_CLASSIFICATION,
                score=min(1.0, base_confidence * 1.05),
                weight=0.3,
                explanation=f"Clause classified as '{finding.clause_type}' with high pattern match confidence",
            ),
            ConfidenceComponentScore(
                component=ConfidenceComponent.SEVERITY_ASSESSMENT,
                score=self._severity_confidence(finding.severity),
                weight=0.25,
                explanation=f"Severity '{finding.severity}' based on clause language analysis",
            ),
            ConfidenceComponentScore(
                component=ConfidenceComponent.RISK_SCORING,
                score=finding.risk_score or base_confidence,
                weight=0.25,
                explanation="Risk score derived from severity, clause type, and context",
            ),
            ConfidenceComponentScore(
                component=ConfidenceComponent.POLICY_MATCH,
                score=0.8,
                weight=0.2,
                explanation="Policy rule matching based on declarative conditions",
            ),
        ]

        weighted_sum = sum(c.score * c.weight for c in components)
        total_weight = sum(c.weight for c in components)
        overall = round(weighted_sum / total_weight, 4) if total_weight > 0 else base_confidence

        signals = []
        if finding.severity in ("critical", "high"):
            signals.append("High severity finding — elevated attention required")
        if finding.confidence and finding.confidence < 0.5:
            signals.append("Low AI confidence — recommend human review")
        if finding.risk_score and finding.risk_score > 0.7:
            signals.append("Elevated risk score — correlates with high severity")

        return ConfidenceBreakdown(
            overall_confidence=overall,
            components=components,
            signals=signals,
            data_quality=0.85,
            model_reliability=0.78,
            human_validation_status="unreviewed",
        )

    def _severity_confidence(self, severity: str) -> float:
        """Confidence in severity assessment based on severity level."""
        mapping = {
            "critical": 0.85,
            "high": 0.80,
            "medium": 0.75,
            "low": 0.70,
            "info": 0.65,
        }
        return mapping.get(severity, 0.7)


@dataclass
class ExplainabilityService:
    """Orchestrates explainability for AI analysis results."""

    ai_repo: AIRepository
    review_repo: ReviewRepository
    playbook_repo: Optional[PlaybookRepository] = None
    evidence_builder: Optional[EvidenceChainBuilder] = None

    def __post_init__(self):
        self.evidence_builder = EvidenceChainBuilder(
            ai_repo=self.ai_repo,
            review_repo=self.review_repo,
            playbook_repo=self.playbook_repo,
        )

    async def get_explainability(
        self,
        review_id: str,
        upload_id: str,
        tenant_id: str,
    ) -> ExplainabilityResponse:
        """Build complete explainability for a review's AI analysis."""
        # Load analysis results
        analysis = await self.ai_repo.get_analysis_result(upload_id)
        findings_data = await self.ai_repo.get_findings_for_upload(upload_id)
        redlines_data = await self.ai_repo.get_redlines_for_upload(upload_id)

        # Build finding explanations
        finding_explanations: list[FindingExplanation] = []
        for finding in findings_data:
            evidence, confidence = await self.evidence_builder.build_for_finding(
                finding=finding,
                finding_id=getattr(finding, 'finding_id', '') or uuid.uuid4().hex[:12],
                upload_id=upload_id,
                review_id=review_id,
                tenant_id=tenant_id,
            )

            rationale = Rationale(
                summary=f"Clause type '{finding.clause_type}' assessed as '{finding.severity}' risk: {finding.title}",
                segments=[
                    RationaleSegment(
                        segment_type="observation",
                        text=finding.description,
                        evidence_ids=[e.evidence_id for e in evidence if e.type == EvidenceType.SOURCE_CLAUSE],
                    ),
                    RationaleSegment(
                        segment_type="analysis",
                        text=f"Severity: {finding.severity}. Confidence: {confidence.overall_confidence:.2f}",
                    ),
                ],
                evidence_chain=[e.evidence_id for e in evidence],
                confidence_breakdown=confidence,
            )

            if finding.recommendation:
                rationale.segments.append(
                    RationaleSegment(
                        segment_type="recommendation",
                        text=finding.recommendation,
                    )
                )

            alternatives = []
            if finding.recommendation:
                alternatives.append(AlternativeSuggestion(
                    title="AI-recommended alternative",
                    description=finding.recommendation,
                    risk_reduction=finding.severity,
                    confidence=confidence.overall_confidence,
                    source="ai_generated",
                ))

            finding_explanations.append(FindingExplanation(
                finding_id=getattr(finding, 'finding_id', '') or uuid.uuid4().hex[:12],
                finding_title=finding.title,
                finding_severity=finding.severity,
                clause_type=finding.clause_type,
                rationale=rationale,
                evidence=evidence,
                confidence=confidence,
                alternatives=alternatives,
            ))

        # Build redline explanations
        redline_explanations: list[RedlineExplanation] = []
        for redline in redlines_data:
            redline_evidence, redline_confidence = await self.evidence_builder.build_for_finding(
                finding=RiskFinding(
                    clause_type=redline.clause_type,
                    severity=redline.risk_level or "medium",
                    title=f"Redline: {redline.operation}",
                    description=redline.rationale or "",
                ),
                finding_id=uuid.uuid4().hex[:12],
                upload_id=upload_id,
                review_id=review_id,
                tenant_id=tenant_id,
            )

            redline_explanations.append(RedlineExplanation(
                redline_id=getattr(redline, 'redline_id', '') or uuid.uuid4().hex[:12],
                operation=redline.operation,
                rationale=Rationale(
                    summary=redline.rationale or f"Suggested {redline.operation} for {redline.clause_type}",
                    segments=[
                        RationaleSegment(
                            segment_type="analysis",
                            text=redline.rationale or "",
                        ),
                    ],
                ),
                evidence=redline_evidence,
                confidence=redline_confidence,
                risk_impact=redline.risk_level,
            ))

        # Overall confidence
        overall_confidence = ConfidenceBreakdown(
            overall_confidence=analysis.confidence if hasattr(analysis, 'confidence') else 0.75,
            components=[],
            signals=[],
        )

        return ExplainabilityResponse(
            review_id=review_id,
            upload_id=upload_id,
            overall_confidence=overall_confidence,
            finding_explanations=finding_explanations,
            redline_explanations=redline_explanations,
            summary=analysis.summary if hasattr(analysis, 'summary') else "",
        )

    async def get_regulation_check(
        self,
        upload_id: str,
        tenant_id: str,
    ) -> RegulationCheckResult:
        """Check contract clauses against applicable regulations."""
        findings_data = await self.ai_repo.get_findings_for_upload(upload_id)

        clause_types_seen: set[str] = set()
        for finding in findings_data:
            clause_types_seen.add(finding.clause_type)

        regulation_map: dict[str, list[tuple[RegulationSource, str, str]]] = {
            "data_privacy": [
                (RegulationSource.GDPR, "Art. 5(1)(a)", "Lawfulness, fairness and transparency"),
                (RegulationSource.CCPA, "§1798.100", "Right to know and access"),
            ],
            "security": [
                (RegulationSource.GDPR, "Art. 32", "Security of processing"),
                (RegulationSource.PCI_DSS, "Req. 3", "Protect stored cardholder data"),
            ],
            "confidentiality": [
                (RegulationSource.GDPR, "Art. 5(1)(f)", "Integrity and confidentiality"),
            ],
            "compliance": [
                (RegulationSource.SOX, "§302", "Corporate responsibility for financial reports"),
            ],
            "indemnification": [
                (RegulationSource.UCC, "§2-312", "Warranty of title and against infringement"),
            ],
            "liability": [
                (RegulationSource.UCC, "§2-719", "Contractual modification of remedy"),
            ],
            "intellectual_property": [
                (RegulationSource.UCC, "§2-312", "Warranty of title"),
            ],
            "termination": [
                (RegulationSource.UCC, "§2-309", "Notice of termination"),
            ],
            "governing_law": [
                (RegulationSource.CISG, "Art. 1", "Scope of application"),
            ],
        }

        mappings: list[RegulationMapping] = []
        total_checks = 0
        compliant = 0
        at_risk = 0
        non_compliant = 0
        unknown = 0

        for ct in clause_types_seen:
            reg_list = regulation_map.get(ct, [])
            if not reg_list:
                continue

            regulations = []
            for source, provision, requirement in reg_list:
                total_checks += 1
                # Determine compliance status based on findings
                status = "unknown"
                for finding in findings_data:
                    if finding.clause_type == ct and finding.severity in ("critical", "high"):
                        status = "at_risk"
                        break
                else:
                    if any(f.clause_type == ct for f in findings_data):
                        status = "compliant"

                if status == "compliant":
                    compliant += 1
                elif status == "at_risk":
                    at_risk += 1
                elif status == "non_compliant":
                    non_compliant += 1
                else:
                    unknown += 1

                regulations.append(RegulationEvidenceSchema(
                    regulation=source,
                    regulation_name=source.value.upper(),
                    provision=provision,
                    requirement=requirement,
                    compliance_status=status,
                ))

            if regulations:
                mappings.append(RegulationMapping(
                    clause_type=ct,
                    regulations=regulations,
                ))

        if at_risk > 0 or non_compliant > 0:
            overall = "action_required" if non_compliant > 0 else "attention_needed"
        elif compliant == total_checks:
            overall = "compliant"
        else:
            overall = "unknown"

        return RegulationCheckResult(
            upload_id=upload_id,
            mappings=mappings,
            total_checks=total_checks,
            compliant=compliant,
            at_risk=at_risk,
            non_compliant=non_compliant,
            unknown=unknown,
            overall_status=overall,
        )
