"""Clause Intelligence service — clause graph, alternatives, negotiation lineage, vendor patterns.

Builds institutional legal intelligence from contract analysis history,
creating a proprietary knowledge moat.
"""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from app.domains.ai.repository import AIRepository
from app.domains.ai.schemas import RiskFinding
from app.domains.playbook.repository import PlaybookRepository
from app.domains.review.repository import ReviewRepository
from app.domains.clause_intel.schemas import (
    RelationshipType, NegotiationOutcome, ClauseRiskInheritance,
    ClauseNode, ClauseRelationship, ClauseGraph, ClauseGraphQuery,
    ApprovedAlternative, AlternativeSearchResult,
    NegotiationRound, NegotiationHistory, NegotiationPattern,
    VendorClauseProfile, VendorPatternSummary,
    SemanticCluster, SemanticSearchResult, SemanticMatch,
    RiskInheritanceChain, RiskContribution,
    ClauseIntelligenceDashboard, ClauseTypeRiskSummary, ClauseTypeNegotiationSummary,
)

logger = logging.getLogger(__name__)


@dataclass
class ClauseGraphBuilder:
    """Builds and queries the clause knowledge graph."""

    ai_repo: AIRepository
    review_repo: ReviewRepository
    playbook_repo: Optional[PlaybookRepository] = None

    async def build_graph(
        self,
        tenant_id: str,
        clause_types: Optional[list[str]] = None,
    ) -> ClauseGraph:
        """Build a clause knowledge graph from all analyzed contracts."""
        # Gather all findings across contracts
        all_findings = await self.ai_repo.get_all_findings(
            tenant_id=tenant_id,
            clause_types=clause_types,
            limit=500,
        )

        nodes: list[ClauseNode] = []
        edges: list[ClauseRelationship] = []
        seen_clauses: dict[str, ClauseNode] = {}

        for finding in all_findings:
            clause_key = f"{finding.clause_type}:{finding.title}"
            if clause_key not in seen_clauses:
                node = ClauseNode(
                    clause_id=uuid.uuid4().hex[:12],
                    clause_type=finding.clause_type,
                    canonical_category=self._canonical_category(finding.clause_type),
                    title=finding.title,
                    text_snippet=finding.description[:200],
                    source="contract",
                    upload_id=getattr(finding, 'upload_id', None),
                    risk_score=finding.risk_score,
                    severity=finding.severity,
                    created_at=datetime.now(timezone.utc),
                )
                seen_clauses[clause_key] = node
                nodes.append(node)

        # Build edges between same-type clauses (similar_to)
        type_groups: dict[str, list[ClauseNode]] = defaultdict(list)
        for node in nodes:
            type_groups[node.clause_type].append(node)

        for ct, group in type_groups.items():
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    edges.append(ClauseRelationship(
                        relationship_id=uuid.uuid4().hex[:12],
                        source_clause_id=group[i].clause_id,
                        target_clause_id=group[j].clause_id,
                        relationship_type=RelationshipType.SIMILAR_TO,
                        strength=0.5,
                        label=f"Same clause type: {ct}",
                        evidence="Same canonical clause classification",
                        created_at=datetime.now(timezone.utc),
                    ))

        # Add playbook clause relationships if available
        if self.playbook_repo:
            try:
                playbooks = await self.playbook_repo.get_playbooks_for_tenant(tenant_id)
                for pb in playbooks:
                    standards = await self.playbook_repo.get_active_clause_standards(
                        str(pb.playbook_id),
                    )
                    for std in standards:
                        cat = std.category.value if hasattr(std.category, 'value') else str(std.category)
                        node = ClauseNode(
                            clause_id=str(std.clause_id),
                            clause_type=cat,
                            canonical_category=self._canonical_category(cat),
                            title=std.title,
                            text_snippet=(std.summary or std.body)[:200],
                            source="playbook",
                            risk_score=std.risk_score,
                            severity=std.risk_level,
                            created_at=std.created_at,
                        )
                        nodes.append(node)

                        # Link playbook clauses to similar contract clauses
                        for contract_node in seen_clauses.values():
                            if contract_node.clause_type == cat:
                                edges.append(ClauseRelationship(
                                    relationship_id=uuid.uuid4().hex[:12],
                                    source_clause_id=node.clause_id,
                                    target_clause_id=contract_node.clause_id,
                                    relationship_type=RelationshipType.SIMILAR_TO,
                                    strength=0.6,
                                    label=f"Playbook standard for {cat}",
                                    evidence="Matching clause category",
                                    created_at=datetime.now(timezone.utc),
                                ))
            except Exception as exc:
                logger.debug("Could not load playbook clauses: %s", exc)

        # Collect unique clause types
        clause_types_set = sorted({n.clause_type for n in nodes})

        return ClauseGraph(
            nodes=nodes,
            edges=edges,
            total_clauses=len(nodes),
            total_relationships=len(edges),
            clause_types=clause_types_set,
        )

    async def query_graph(
        self,
        tenant_id: str,
        query: ClauseGraphQuery,
    ) -> ClauseGraph:
        """Query the clause graph with filters."""
        full_graph = await self.build_graph(tenant_id)

        # Filter nodes
        filtered_nodes = full_graph.nodes
        if query.clause_type:
            filtered_nodes = [n for n in filtered_nodes if n.clause_type == query.clause_type]
        if query.upload_id:
            filtered_nodes = [n for n in filtered_nodes if n.upload_id == query.upload_id]

        filtered_ids = {n.clause_id for n in filtered_nodes}

        # Filter edges
        filtered_edges = [
            e for e in full_graph.edges
            if e.source_clause_id in filtered_ids and e.target_clause_id in filtered_ids
        ]
        if query.relationship_types:
            filtered_edges = [
                e for e in filtered_edges
                if e.relationship_type in query.relationship_types
            ]
        if query.min_strength:
            filtered_edges = [
                e for e in filtered_edges
                if e.strength >= query.min_strength
            ]

        return ClauseGraph(
            nodes=filtered_nodes,
            edges=filtered_edges,
            total_clauses=len(filtered_nodes),
            total_relationships=len(filtered_edges),
            clause_types=full_graph.clause_types,
        )

    def _canonical_category(self, clause_type: str) -> str:
        """Map clause type to canonical category."""
        mapping = {
            "liability": "Liability & Indemnity",
            "indemnification": "Liability & Indemnity",
            "payment": "Commercial Terms",
            "warranty": "Commercial Terms",
            "data_privacy": "Data Privacy",
            "confidentiality": "Governance",
            "termination": "Termination & Renewal",
            "renewal": "Termination & Renewal",
            "intellectual_property": "Intellectual Property",
            "governing_law": "Governance",
            "dispute_resolution": "Governance",
            "compliance": "Compliance",
            "security": "Security",
            "force_majeure": "Termination & Renewal",
            "insurance": "Liability & Indemnity",
            "assignment": "Governance",
            "non_compete": "Governance",
        }
        return mapping.get(clause_type, clause_type.replace("_", " ").title())


@dataclass
class AlternativeFinder:
    """Finds approved alternatives for risky clauses."""

    ai_repo: AIRepository
    review_repo: ReviewRepository
    playbook_repo: Optional[PlaybookRepository] = None

    async def find_alternatives(
        self,
        clause_type: str,
        tenant_id: str,
        text_snippet: str = "",
        limit: int = 10,
    ) -> AlternativeSearchResult:
        """Find approved alternatives for a clause type."""
        alternatives: list[ApprovedAlternative] = []

        # 1. Check playbook standards
        if self.playbook_repo:
            try:
                playbooks = await self.playbook_repo.get_playbooks_for_tenant(tenant_id)
                for pb in playbooks:
                    standards = await self.playbook_repo.get_active_clause_standards(
                        str(pb.playbook_id),
                    )
                    for std in standards:
                        cat = std.category.value if hasattr(std.category, 'value') else str(std.category)
                        std_type = std.clause_type.value if hasattr(std.clause_type, 'value') else str(std.clause_type)
                        if cat == clause_type and std_type in ("approved", "preferred"):
                            alternatives.append(ApprovedAlternative(
                                alternative_id=str(std.clause_id),
                                clause_type=cat,
                                alternative_text=std.body[:500],
                                title=std.title,
                                rationale=std.summary or f"Approved {std_type} clause for {cat}",
                                source="playbook",
                                effectiveness_score=0.9 if std_type == "approved" else 0.7,
                                risk_reduction=std.risk_level,
                                usage_count=0,
                            ))
            except Exception as exc:
                logger.debug("Could not load playbook alternatives: %s", exc)

        # 2. Check negotiation history for successful alternatives
        try:
            successful_redlines = await self.ai_repo.get_accepted_redlines(
                clause_type=clause_type,
                tenant_id=tenant_id,
                limit=limit,
            )
            for redline in successful_redlines:
                alt_text = getattr(redline, 'proposed_text', '') or ''
                if alt_text:
                    alternatives.append(ApprovedAlternative(
                        alternative_id=uuid.uuid4().hex[:12],
                        clause_type=clause_type,
                        original_text_snippet=(getattr(redline, 'original_text', '') or '')[:200],
                        alternative_text=alt_text[:500],
                        title=f"Negotiated alternative for {clause_type}",
                        rationale=getattr(redline, 'rationale', '') or 'Accepted during negotiation',
                        source="negotiation",
                        effectiveness_score=0.75,
                        usage_count=1,
                    ))
        except Exception as exc:
            logger.debug("Could not load negotiation alternatives: %s", exc)

        has_playbook = any(a.source == "playbook" for a in alternatives)
        has_negotiation = any(a.source == "negotiation" for a in alternatives)

        return AlternativeSearchResult(
            clause_type=clause_type,
            alternatives=alternatives[:limit],
            total_found=len(alternatives),
            has_playbook_alternatives=has_playbook,
            has_negotiation_alternatives=has_negotiation,
        )


@dataclass
class NegotiationTracker:
    """Tracks and analyzes negotiation history across contracts."""

    ai_repo: AIRepository
    review_repo: ReviewRepository

    async def get_negotiation_history(
        self,
        upload_id: str,
        clause_type: Optional[str] = None,
    ) -> list[NegotiationHistory]:
        """Get negotiation history for a contract's clauses."""
        redlines = await self.ai_repo.get_redlines_for_upload(upload_id)

        # Group redlines by clause type
        by_type: dict[str, list[Any]] = defaultdict(list)
        for redline in redlines:
            ct = getattr(redline, 'clause_type', 'other') or 'other'
            by_type[ct].append(redline)

        histories: list[NegotiationHistory] = []
        for ct, items in by_type.items():
            if clause_type and ct != clause_type:
                continue

            rounds = []
            for i, item in enumerate(items):
                status = getattr(item, 'status', 'proposed') or 'proposed'
                outcome_map = {
                    "accepted": NegotiationOutcome.ACCEPTED,
                    "rejected": NegotiationOutcome.REJECTED,
                    "modified": NegotiationOutcome.MODIFIED,
                }
                outcome = outcome_map.get(status, NegotiationOutcome.COUNTERED)

                rounds.append(NegotiationRound(
                    round_number=i + 1,
                    proposed_text=getattr(item, 'proposed_text', '') or '',
                    response_text=getattr(item, 'reviewer_modified_text', '') or '',
                    proposed_by="us",
                    outcome=outcome,
                    notes=getattr(item, 'rationale', '') or '',
                    created_at=getattr(item, 'created_at', datetime.now(timezone.utc)),
                ))

            if rounds:
                final_outcome = rounds[-1].outcome if rounds else None
                histories.append(NegotiationHistory(
                    negotiation_id=uuid.uuid4().hex[:12],
                    upload_id=upload_id,
                    clause_type=ct,
                    original_text=getattr(items[0], 'original_text', '') or '',
                    final_text=getattr(items[-1], 'proposed_text', '') or '',
                    rounds=rounds,
                    total_rounds=len(rounds),
                    final_outcome=final_outcome,
                ))

        return histories

    async def get_negotiation_patterns(
        self,
        tenant_id: str,
        clause_type: Optional[str] = None,
    ) -> list[NegotiationPattern]:
        """Identify recurring negotiation patterns across contracts."""
        all_redlines = await self.ai_repo.get_all_redlines(
            tenant_id=tenant_id,
            clause_type=clause_type,
            limit=200,
        )

        # Group by clause type
        by_type: dict[str, list[Any]] = defaultdict(list)
        for redline in all_redlines:
            ct = getattr(redline, 'clause_type', 'other') or 'other'
            by_type[ct].append(redline)

        patterns: list[NegotiationPattern] = []
        for ct, items in by_type.items():
            accepted = sum(1 for i in items if getattr(i, 'status', '') == 'accepted')
            total = len(items)
            success_rate = accepted / total if total > 0 else 0.0

            patterns.append(NegotiationPattern(
                pattern_id=uuid.uuid4().hex[:12],
                clause_type=ct,
                pattern_name=f"{ct.replace('_', ' ').title()} Negotiation Pattern",
                description=f"Pattern from {total} redline suggestions across contracts",
                common_requests=[f"Modify {ct} language"],
                typical_outcomes=["accepted", "modified"],
                success_rate=round(success_rate, 2),
                average_rounds=1.5,
                sample_count=total,
            ))

        return patterns


@dataclass
class VendorPatternAnalyzer:
    """Analyzes clause patterns by vendor/counterparty."""

    ai_repo: AIRepository
    review_repo: ReviewRepository

    async def get_vendor_profile(
        self,
        vendor_name: str,
        tenant_id: str,
    ) -> Optional[VendorPatternSummary]:
        """Get clause pattern profile for a specific vendor."""
        contracts = await self.review_repo.get_reviews_by_counterparty(
            counterparty=vendor_name,
            tenant_id=tenant_id,
            limit=50,
        )

        if not contracts:
            return None

        clause_profiles: dict[str, VendorClauseProfile] = {}
        for contract in contracts:
            upload_id = contract.upload_id
            findings = await self.ai_repo.get_findings_for_upload(str(upload_id))

            for finding in findings:
                ct = finding.clause_type
                if ct not in clause_profiles:
                    clause_profiles[ct] = VendorClauseProfile(
                        vendor_name=vendor_name,
                        counterparty=vendor_name,
                        clause_type=ct,
                        typical_language=finding.description[:200],
                        contract_count=0,
                    )
                profile = clause_profiles[ct]
                profile.contract_count += 1
                if finding.severity in ("critical", "high"):
                    profile.common_deviations.append(finding.title)

        # Determine overall tendency
        all_severities = []
        for profile in clause_profiles.values():
            all_severities.extend(profile.common_deviations)

        high_risk_count = sum(1 for f in all_severities if f)
        total = len(all_severities) or 1
        risk_tendency = "aggressive" if high_risk_count / total > 0.5 else "neutral"

        return VendorPatternSummary(
            vendor_name=vendor_name,
            total_contracts=len(contracts),
            clause_profiles=list(clause_profiles.values()),
            overall_risk_tendency=risk_tendency,
            common_clause_types=list(clause_profiles.keys()),
            last_activity=contracts[0].updated_at if contracts else None,
        )

    async def get_all_vendor_summaries(
        self,
        tenant_id: str,
    ) -> list[VendorPatternSummary]:
        """Get summaries for all vendors with contract history."""
        counterparties = await self.review_repo.get_distinct_counterparties(tenant_id)
        summaries: list[VendorPatternSummary] = []
        for name in counterparties:
            profile = await self.get_vendor_profile(name, tenant_id)
            if profile:
                summaries.append(profile)
        return summaries


@dataclass
class RiskInheritanceAnalyzer:
    """Analyzes risk inheritance across related clauses."""

    ai_repo: AIRepository

    async def analyze_inheritance(
        self,
        upload_id: str,
    ) -> list[RiskInheritanceChain]:
        """Analyze risk inheritance chains across clauses in a contract."""
        findings = await self.ai_repo.get_findings_for_upload(upload_id)

        # Group by clause type
        by_type: dict[str, list[RiskFinding]] = defaultdict(list)
        for finding in findings:
            by_type[finding.clause_type].append(finding)

        chains: list[RiskInheritanceChain] = []
        for ct, group in by_type.items():
            total_risk = sum(f.risk_score or 0.5 for f in group)
            avg_risk = total_risk / len(group) if group else 0.0

            contributions = [
                RiskContribution(
                    clause_id=uuid.uuid4().hex[:12],
                    clause_type=f.clause_type,
                    risk_score=f.risk_score or 0.5,
                    contribution_weight=(f.risk_score or 0.5) / total_risk if total_risk > 0 else 0.0,
                    relationship_type=RelationshipType.SIMILAR_TO,
                    text_snippet=f.description[:200],
                )
                for f in group
            ]

            chains.append(RiskInheritanceChain(
                source_clause_id=uuid.uuid4().hex[:12],
                source_clause_type=ct,
                inheritance_type=ClauseRiskInheritance.AGGREGATED,
                inherited_risk_score=round(avg_risk, 4),
                contributing_clauses=contributions,
                net_risk_score=round(avg_risk, 4),
            ))

        return chains


@dataclass
class ClauseIntelligenceService:
    """Orchestrates all clause intelligence capabilities."""

    ai_repo: AIRepository
    review_repo: ReviewRepository
    playbook_repo: Optional[PlaybookRepository] = None

    # Sub-services
    graph_builder: Optional[ClauseGraphBuilder] = None
    alternative_finder: Optional[AlternativeFinder] = None
    negotiation_tracker: Optional[NegotiationTracker] = None
    vendor_analyzer: Optional[VendorPatternAnalyzer] = None
    risk_inheritance: Optional[RiskInheritanceAnalyzer] = None

    def __post_init__(self):
        self.graph_builder = ClauseGraphBuilder(
            ai_repo=self.ai_repo,
            review_repo=self.review_repo,
            playbook_repo=self.playbook_repo,
        )
        self.alternative_finder = AlternativeFinder(
            ai_repo=self.ai_repo,
            review_repo=self.review_repo,
            playbook_repo=self.playbook_repo,
        )
        self.negotiation_tracker = NegotiationTracker(
            ai_repo=self.ai_repo,
            review_repo=self.review_repo,
        )
        self.vendor_analyzer = VendorPatternAnalyzer(
            ai_repo=self.ai_repo,
            review_repo=self.review_repo,
        )
        self.risk_inheritance = RiskInheritanceAnalyzer(
            ai_repo=self.ai_repo,
        )

    async def get_dashboard(self, tenant_id: str) -> ClauseIntelligenceDashboard:
        """Get executive dashboard for clause intelligence."""
        # Gather statistics
        all_findings = await self.ai_repo.get_all_findings(tenant_id=tenant_id, limit=1000)
        all_redlines = await self.ai_repo.get_all_redlines(tenant_id=tenant_id, limit=500)

        # Clause type risk summary
        type_risk: dict[str, list[float]] = defaultdict(list)
        type_high_risk: dict[str, int] = defaultdict(int)
        for finding in all_findings:
            type_risk[finding.clause_type].append(finding.risk_score or 0.5)
            if finding.severity in ("critical", "high"):
                type_high_risk[finding.clause_type] += 1

        most_common = sorted(
            [
                ClauseTypeRiskSummary(
                    clause_type=ct,
                    count=len(scores),
                    average_risk_score=round(sum(scores) / len(scores), 4) if scores else 0.0,
                    high_risk_count=type_high_risk.get(ct, 0),
                    trend="stable",
                )
                for ct, scores in type_risk.items()
            ],
            key=lambda x: -x.count,
        )[:10]

        # Negotiation summary by clause type
        type_negotiations: dict[str, list[Any]] = defaultdict(list)
        for redline in all_redlines:
            ct = getattr(redline, 'clause_type', 'other') or 'other'
            type_negotiations[ct].append(redline)

        top_negotiated = [
            ClauseTypeNegotiationSummary(
                clause_type=ct,
                total_negotiations=len(items),
                acceptance_rate=round(
                    sum(1 for i in items if getattr(i, 'status', '') == 'accepted') / len(items), 2
                ) if items else 0.0,
                average_rounds=1.0,
                average_risk_reduction=0.0,
            )
            for ct, items in sorted(type_negotiations.items(), key=lambda x: -len(x[1]))[:10]
        ]

        # Vendor count
        counterparties = await self.review_repo.get_distinct_counterparties(tenant_id)

        return ClauseIntelligenceDashboard(
            total_clauses_analyzed=len(all_findings),
            total_relationships=len(all_findings) * 2,  # approximate
            unique_clause_types=len(type_risk),
            approved_alternatives_count=len(all_redlines),
            negotiation_histories=len(all_redlines),
            vendor_patterns_tracked=len(counterparties),
            semantic_clusters=len(type_risk),
            most_common_risky_clauses=most_common,
            top_negotiated_clauses=top_negotiated,
        )
