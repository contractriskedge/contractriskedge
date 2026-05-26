"""Playbook Context Provider — fetches approved/preferred/fallback clause standards for AI prompt injection."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.playbook.models import ClauseStandard, ClauseType

logger = logging.getLogger(__name__)


@dataclass
class PlaybookContext:
    """Approved/preferred/fallback language context for a clause category."""
    clause_category: str
    approved: list[ClauseStandard]  # Approved standards
    preferred: list[ClauseStandard]  # Preferred standards
    fallbacks: list[ClauseStandard]  # Fallback alternatives
    forbidden: list[ClauseStandard]  # Forbidden language

    def has_context(self) -> bool:
        return bool(self.approved or self.preferred or self.fallbacks)

    def to_prompt_context(self) -> str:
        """Render playbook context as a string for AI prompt injection."""
        if not self.has_context():
            return ""

        lines = ["APPROVED CLAUSE LANGUAGE FROM COMPANY PLAYBOOK:"]
        lines.append("")

        if self.approved:
            lines.append("APPROVED STANDARDS (must-use language):")
            for i, std in enumerate(self.approved, 1):
                lines.append(f"  {i}. {std.title}")
                lines.append(f"     {std.body[:500]}")
                if std.summary:
                    lines.append(f"     Note: {std.summary}")
            lines.append("")

        if self.preferred:
            lines.append("PREFERRED ALTERNATIVES (recommended when approved language cannot be used):")
            for i, std in enumerate(self.preferred, 1):
                lines.append(f"  {i}. {std.title}")
                lines.append(f"     {std.body[:500]}")
                if std.summary:
                    lines.append(f"     Note: {std.summary}")
            lines.append("")

        if self.fallbacks:
            lines.append("FALLBACK CLAUSES (acceptable compromise language):")
            for i, std in enumerate(self.fallbacks, 1):
                lines.append(f"  {i}. {std.title}")
                lines.append(f"     {std.body[:500]}")
                if std.summary:
                    lines.append(f"     Note: {std.summary}")
            lines.append("")

        if self.forbidden:
            lines.append("FORBIDDEN LANGUAGE (must be removed or modified):")
            for i, std in enumerate(self.forbidden, 1):
                lines.append(f"  {i}. {std.title}")
                if std.summary:
                    lines.append(f"     Note: {std.summary}")
            lines.append("")

        lines.append("INSTRUCTIONS:")
        lines.append("- If the contract language deviates from an APPROVED standard, recommend the approved language.")
        lines.append("- If the contract language deviates from a PREFERRED alternative, recommend the preferred language.")
        lines.append("- If the clause is MISSING entirely, recommend the approved standard or preferred alternative.")
        lines.append("- If the clause matches FORBIDDEN language, flag it for removal or modification.")
        lines.append("- Use the playbook language as the PRIMARY basis for your proposed_text.")
        lines.append("- Adapt the playbook language to fit the specific contract context, but preserve the core protections.")
        lines.append("")

        return "\n".join(lines)


class PlaybookContextProvider:
    """Fetches relevant clause standards from the playbook for AI prompt injection."""

    def __init__(self, session: AsyncSession, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id

    async def get_context(
        self,
        clause_category: str,
        playbook_id: Optional[str] = None,
    ) -> PlaybookContext:
        """Fetch all relevant clause standards for a given clause category."""
        from sqlalchemy import select

        query = select(ClauseStandard).where(
            ClauseStandard.tenant_id == self.tenant_id,
            ClauseStandard.is_active == True,
        )

        # Map common clause_type values to playbook categories
        category = _map_clause_type_to_category(clause_category)
        if category:
            query = query.where(ClauseStandard.category == category)

        if playbook_id:
            query = query.where(ClauseStandard.playbook_id == playbook_id)

        result = await self.session.execute(query)
        standards = result.scalars().all()

        approved = []
        preferred = []
        fallbacks = []
        forbidden = []

        for std in standards:
            ct = std.clause_type.value if hasattr(std.clause_type, "value") else str(std.clause_type)
            if ct == "approved":
                approved.append(std)
            elif ct == "preferred":
                preferred.append(std)
            elif ct == "fallback":
                fallbacks.append(std)
            elif ct == "forbidden":
                forbidden.append(std)

        return PlaybookContext(
            clause_category=clause_category,
            approved=approved,
            preferred=preferred,
            fallbacks=fallbacks,
            forbidden=forbidden,
        )


_CLAUSE_TYPE_TO_CATEGORY = {
    "indemnification": "indemnification",
    "indemnity": "indemnification",
    "limitation_of_liability": "limitation_of_liability",
    "liability": "limitation_of_liability",
    "confidentiality": "confidentiality",
    "data_privacy": "data_privacy",
    "privacy": "data_privacy",
    "intellectual_property": "intellectual_property",
    "ip": "intellectual_property",
    "termination": "termination",
    "governing_law": "governing_law",
    "law": "governing_law",
    "dispute_resolution": "dispute_resolution",
    "arbitration": "dispute_resolution",
    "force_majeure": "force_majeure",
    "payment_terms": "payment_terms",
    "payment": "payment_terms",
    "warranty": "warranty",
    "insurance": "insurance",
    "compliance": "compliance",
    "audit_rights": "audit_rights",
    "audit": "audit_rights",
    "assignment": "assignment",
    "non_compete": "non_compete",
    "non_solicit": "non_solicit",
    "sla": "sla",
    "escrow": "escrow",
    "general": "general",
}


def _map_clause_type_to_category(clause_type: str) -> Optional[str]:
    """Map a clause_type string to a playbook ClauseCategory enum value."""
    normalized = clause_type.strip().lower().replace(" ", "_").replace("-", "_")
    return _CLAUSE_TYPE_TO_CATEGORY.get(normalized)
