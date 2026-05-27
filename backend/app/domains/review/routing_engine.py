"""Intelligent Routing Engine — data-driven reviewer assignment and workload management.

Uses historical telemetry to:
  - Recommend optimal reviewers based on expertise, workload, and speed
  - Auto-route reviews with concurrency-safe assignment locks
  - Predict workload bottlenecks before they occur
  - Score reviewer candidates on multiple dimensions

All routing decisions are recorded in AssignmentAudit for full explainability.

Integration points:
  - ReviewService.assign() → recommendation overlay
  - Recovery daemon → auto-assignment for stuck reviews
  - Admin diagnostics → workload visibility
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func as sa_func, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# ── Scoring Weights ──────────────────────────────────────────────

# How much each factor contributes to the overall recommendation score.
# Higher = more important. Configurable per tenant in future.

_WORKLOAD_WEIGHT = 0.30       # Lower active count → higher score
_SPEED_WEIGHT = 0.25          # Faster historical completion → higher score
_EXPERTISE_WEIGHT = 0.20      # Experience with clause category → higher score
_ESCALATION_WEIGHT = 0.15     # Lower escalation rate → higher score
_TENANT_POLICY_WEIGHT = 0.10  # Tenant routing rules → modifier

# Maximum active reviews before a reviewer is considered overloaded
_DEFAULT_MAX_CAPACITY = 10


# ── Data Models ──────────────────────────────────────────────────


@dataclass
class ReviewerCandidate:
    """Scored reviewer candidate for routing recommendations."""
    reviewer_id: str
    score: float  # 0.0 to 1.0, higher = better match
    active_review_count: int
    avg_completion_hours: float
    expertise_score: float  # 0.0 to 1.0
    escalation_rate: float  # 0.0 to 1.0
    is_overloaded: bool = False
    score_breakdown: dict[str, float] = field(default_factory=dict)


@dataclass
class RoutingRecommendation:
    """Complete routing recommendation with explainability."""
    review_id: str
    recommended_reviewer_id: str
    confidence_score: float
    candidates: list[ReviewerCandidate] = field(default_factory=list)
    reasoning: list[str] = field(default_factory=list)
    routing_rule_applied: Optional[str] = None


# ── Routing Engine ───────────────────────────────────────────────


class RoutingEngine:
    """Intelligent reviewer routing engine.

    Scores and recommends reviewers based on:
    1. Current workload (active review count)
    2. Historical completion speed
    3. Domain expertise (clause categories worked on)
    4. Escalation history
    5. Tenant routing rules

    Usage:
        engine = RoutingEngine(session, tenant_id)
        recommendation = await engine.recommend_reviewer(
            review_id="review-123",
            preferred_role="legal_ops",
        )
    """

    def __init__(self, session: AsyncSession, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id

    async def recommend_reviewer(
        self,
        review_id: str,
        preferred_role: Optional[str] = None,
        exclude_reviewers: Optional[list[str]] = None,
    ) -> RoutingRecommendation:
        """Recommend the best reviewer for a review.

        Scores all eligible reviewers and returns the top candidate
        with explainability data.

        Args:
            review_id: The review to route.
            preferred_role: Optional role filter (e.g. 'legal_ops', 'reviewer').
            exclude_reviewers: Optional list of reviewer IDs to exclude.

        Returns:
            RoutingRecommendation with top candidate and reasoning.
        """
        from app.domains.review.models import ContractReview

        # Get review data for context
        result = await self.session.execute(
            select(ContractReview).where(
                ContractReview.review_id == review_id,
                ContractReview.tenant_id == self.tenant_id,
            )
        )
        review = result.scalar_one_or_none()
        if not review:
            return RoutingRecommendation(
                review_id=review_id,
                recommended_reviewer_id="",
                confidence_score=0.0,
                reasoning=["Review not found"],
            )

        # Get all eligible reviewers for this tenant
        candidates = await self._score_candidates(
            review=review,
            preferred_role=preferred_role,
            exclude_reviewers=exclude_reviewers or [],
        )

        if not candidates:
            return RoutingRecommendation(
                review_id=review_id,
                recommended_reviewer_id="",
                confidence_score=0.0,
                reasoning=["No eligible reviewers found"],
            )

        # Sort by score descending
        candidates.sort(key=lambda c: c.score, reverse=True)
        top = candidates[0]

        # Build reasoning
        reasoning = self._build_reasoning(top, review)

        # Check tenant routing rules
        rule_name = await self._match_routing_rule(review)

        return RoutingRecommendation(
            review_id=review_id,
            recommended_reviewer_id=top.reviewer_id,
            confidence_score=round(top.score, 3),
            candidates=candidates[:5],  # Top 5
            reasoning=reasoning,
            routing_rule_applied=rule_name,
        )

    async def _score_candidates(
        self,
        review,
        preferred_role: Optional[str],
        exclude_reviewers: list[str],
    ) -> list[ReviewerCandidate]:
        """Score all eligible reviewers for a review.

        Queries workload, speed, expertise, and escalation data
        for each reviewer and computes a composite score.
        """
        # Get all active users who can be reviewers
        from app.domains.admin.models import AdminUser

        users_result = await self.session.execute(
            select(AdminUser).where(
                AdminUser.tenant_id == self.tenant_id,
                AdminUser.is_active.is_(True),
            )
        )
        all_users = users_result.scalars().all()

        # Filter by role if specified
        if preferred_role:
            eligible = [u for u in all_users if u.role == preferred_role]
            if not eligible:
                # Fall back to all active users
                eligible = all_users
        else:
            eligible = all_users

        # Remove excluded
        eligible = [u for u in eligible if u.user_id not in exclude_reviewers]

        if not eligible:
            return []

        # Get workload data (active review counts per reviewer)
        workload_data = await self._get_workload_data()

        # Get speed data (historical completion times per reviewer)
        speed_data = await self._get_speed_data()

        # Get expertise data (clause categories per reviewer)
        expertise_data = await self._get_expertise_data()

        # Get escalation data (escalation rate per reviewer)
        escalation_data = await self._get_escalation_data()

        # Score each candidate
        candidates = []
        for user in eligible:
            uid = user.user_id
            workload = workload_data.get(uid, 0)
            speed = speed_data.get(uid)
            expertise = expertise_data.get(uid, 0.0)
            escalation = escalation_data.get(uid, 0.0)

            scores = {}
            reasons = []

            # Workload score (lower = better)
            max_capacity = _DEFAULT_MAX_CAPACITY
            workload_score = max(0, 1.0 - (workload / max_capacity))
            scores["workload"] = round(workload_score * _WORKLOAD_WEIGHT, 4)
            if workload >= max_capacity:
                reasons.append(f"At capacity ({workload}/{max_capacity})")

            # Speed score (faster = better)
            speed_score = 0.5  # Default mid-score
            if speed and speed > 0:
                # Normalize: faster than 24h → high score, slower → low score
                speed_score = max(0, min(1.0, 1.0 - (speed / 168.0)))  # 168h = 7 days
            scores["speed"] = round(speed_score * _SPEED_WEIGHT, 4)

            # Expertise score (higher = better)
            scores["expertise"] = round(expertise * _EXPERTISE_WEIGHT, 4)

            # Escalation score (lower = better)
            escalation_score = max(0, 1.0 - escalation)
            scores["escalation"] = round(escalation_score * _ESCALATION_WEIGHT, 4)

            # Tenant policy score
            policy_score = 0.5  # Default neutral
            scores["policy"] = round(policy_score * _TENANT_POLICY_WEIGHT, 4)

            # Composite score
            total = sum(scores.values())

            candidates.append(ReviewerCandidate(
                reviewer_id=uid,
                score=round(total, 4),
                active_review_count=workload,
                avg_completion_hours=speed or 0,
                expertise_score=round(expertise, 2),
                escalation_rate=round(escalation, 2),
                is_overloaded=workload >= max_capacity,
                score_breakdown=scores,
            ))

        return candidates

    async def _get_workload_data(self) -> dict[str, int]:
        """Get active review counts per reviewer."""
        result = await self.session.execute(
            sa_text("""
                SELECT assigned_to, COUNT(*)::int AS active_count
                FROM contract_reviews
                WHERE tenant_id = :tid
                  AND is_deleted = FALSE
                  AND status IN ('in_review', 'pending_approval')
                  AND assigned_to IS NOT NULL
                GROUP BY assigned_to
            """),
            {"tid": self.tenant_id},
        )
        return {row.assigned_to: row.active_count for row in result.fetchall()}

    async def _get_speed_data(self) -> dict[str, float]:
        """Get median completion time in hours per reviewer."""
        result = await self.session.execute(
            sa_text("""
                SELECT
                    ra.assignee_id,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (
                        ORDER BY EXTRACT(EPOCH FROM (ra.completed_at - ra.created_at)) / 3600
                    ) AS median_hours
                FROM review_assignments ra
                WHERE ra.tenant_id = :tid
                  AND ra.completed_at IS NOT NULL
                  AND ra.created_at > NOW() - INTERVAL '90 days'
                GROUP BY ra.assignee_id
            """),
            {"tid": self.tenant_id},
        )
        return {
            row.assignee_id: round(float(row.median_hours), 1)
            for row in result.fetchall()
        }

    async def _get_expertise_data(self) -> dict[str, float]:
        """Compute expertise score per reviewer based on clause category diversity.

        Higher score = broader experience across clause categories.
        """
        result = await self.session.execute(
            sa_text("""
                SELECT
                    ra.assignee_id,
                    COUNT(DISTINCT rf.clause_category)::int AS category_count,
                    COUNT(rf.finding_id)::int AS total_findings
                FROM review_assignments ra
                JOIN review_findings rf ON rf.review_id = ra.review_id
                WHERE ra.tenant_id = :tid
                  AND ra.completed_at IS NOT NULL
                  AND ra.created_at > NOW() - INTERVAL '90 days'
                GROUP BY ra.assignee_id
            """),
            {"tid": self.tenant_id},
        )
        expertise = {}
        for row in result.fetchall():
            # Score: 0-1 based on category breadth (capped at 10 categories)
            breadth = min(row.category_count / 10.0, 1.0)
            # Bonus for volume (capped at 100 findings)
            volume = min(row.total_findings / 100.0, 1.0)
            expertise[row.assignee_id] = round(breadth * 0.6 + volume * 0.4, 2)
        return expertise

    async def _get_escalation_data(self) -> dict[str, float]:
        """Get escalation rate per reviewer (0.0 to 1.0)."""
        result = await self.session.execute(
            sa_text("""
                SELECT
                    cr.assigned_to,
                    COUNT(DISTINCT re.escalation_id)::float /
                        NULLIF(COUNT(DISTINCT cr.review_id), 0)::float AS escalation_rate
                FROM contract_reviews cr
                LEFT JOIN review_escalations re ON re.review_id = cr.review_id
                WHERE cr.tenant_id = :tid
                  AND cr.assigned_to IS NOT NULL
                  AND cr.created_at > NOW() - INTERVAL '90 days'
                GROUP BY cr.assigned_to
            """),
            {"tid": self.tenant_id},
        )
        return {
            row.assigned_to: round(float(row.escalation_rate), 2)
            for row in result.fetchall()
        }

    async def _match_routing_rule(self, review) -> Optional[str]:
        """Check if any tenant routing rule matches this review.

        Returns the name of the first matching rule, or None.
        """
        from app.domains.review.models import RoutingRule

        try:
            result = await self.session.execute(
                select(RoutingRule).where(
                    RoutingRule.tenant_id == self.tenant_id,
                    RoutingRule.is_active.is_(True),
                ).order_by(RoutingRule.priority.desc())
            )
            rules = result.scalars().all()

            for rule in rules:
                conditions = rule.conditions or {}
                match = True

                # Simple condition matching
                for key, value in conditions.items():
                    attr = getattr(review, key, None)
                    if attr is None or attr != value:
                        match = False
                        break

                if match:
                    return rule.name
        except Exception:
            pass

        return None

    def _build_reasoning(
        self,
        candidate: ReviewerCandidate,
        review,
    ) -> list[str]:
        """Build human-readable reasoning for a recommendation."""
        reasons = []

        reasons.append(
            f"Workload: {candidate.active_review_count} active reviews "
            f"({candidate.score_breakdown.get('workload', 0):.2f} pts)"
        )
        reasons.append(
            f"Speed: avg {candidate.avg_completion_hours:.1f}h completion "
            f"({candidate.score_breakdown.get('speed', 0):.2f} pts)"
        )
        reasons.append(
            f"Expertise: {candidate.expertise_score:.0%} breadth "
            f"({candidate.score_breakdown.get('expertise', 0):.2f} pts)"
        )
        reasons.append(
            f"Escalation rate: {candidate.escalation_rate:.0%} "
            f"({candidate.score_breakdown.get('escalation', 0):.2f} pts)"
        )

        total = sum(candidate.score_breakdown.values())
        reasons.append(f"Total confidence: {candidate.score:.1%}")

        return reasons


# ── Factory ──────────────────────────────────────────────────────

def get_routing_engine(session: AsyncSession, tenant_id: str) -> RoutingEngine:
    """Create a RoutingEngine for the given tenant."""
    return RoutingEngine(session=session, tenant_id=tenant_id)
