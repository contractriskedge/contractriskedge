"""Workflow Impact Analysis — shows what would be affected before publishing.

Analyzes templates, active contracts, departments, and regions that reference
a workflow pack version.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ── Dataclasses ────────────────────────────────────────────────────


@dataclass
class ImpactAnalysisResult:
    """Result of an impact analysis for a workflow pack version."""
    template_count: int = 0
    active_contract_count: int = 0
    departments: list[str] = field(default_factory=list)
    regions: list[str] = field(default_factory=list)
    templates: list[dict[str, Any]] = field(default_factory=list)
    contracts: list[dict[str, Any]] = field(default_factory=list)


# ── Impact Analyzer ────────────────────────────────────────────────


class ImpactAnalyzer:
    """Analyzes the impact of publishing a workflow pack version.

    Shows which templates, active contracts, departments, and regions
    would be affected by a version change.
    """

    def __init__(self, session: Any, tenant_id: str) -> None:
        """Initialize the impact analyzer.

        Args:
            session: Database session (AsyncSession or SyncSession).
            tenant_id: The tenant scope for the analysis.
        """
        self.session = session
        self.tenant_id = tenant_id

    async def analyze(
        self,
        pack_id: str,
        version_id: str,
    ) -> ImpactAnalysisResult:
        """Analyze the impact of publishing a workflow pack version.

        Queries templates, active contracts, departments, and regions
        that reference the given pack.

        Args:
            pack_id: The workflow pack ID to analyze.
            version_id: The specific version ID being published.

        Returns:
            ImpactAnalysisResult with counts and details.
        """
        result = ImpactAnalysisResult()

        # Analyze templates using this pack
        result.templates = await self._find_templates(pack_id)
        result.template_count = len(result.templates)

        # Analyze active contracts using this pack
        result.contracts = await self._find_active_contracts(pack_id)
        result.active_contract_count = len(result.contracts)

        # Extract unique departments and regions
        departments: set[str] = set()
        regions: set[str] = set()

        for template in result.templates:
            dept = template.get("department") or template.get("business_unit")
            if dept:
                departments.add(str(dept))
            region = template.get("region")
            if region:
                regions.add(str(region))

        for contract in result.contracts:
            dept = contract.get("department") or contract.get("business_unit")
            if dept:
                departments.add(str(dept))
            region = contract.get("region")
            if region:
                regions.add(str(region))

        result.departments = sorted(departments)
        result.regions = sorted(regions)

        logger.info(
            "Impact analysis: pack=%s version=%s templates=%d contracts=%d depts=%d regions=%d",
            pack_id, version_id,
            result.template_count, result.active_contract_count,
            len(result.departments), len(result.regions),
        )

        return result

    async def _find_templates(self, pack_id: str) -> list[dict[str, Any]]:
        """Find templates that reference the given workflow pack.

        Attempts to query the templates table if it exists, otherwise
        returns an empty list gracefully.
        """
        try:
            from sqlalchemy import select, text as sa_text

            # Try to query contract templates that reference this workflow pack
            stmt = sa_text("""
                SELECT template_id, name, department, region, business_unit
                FROM contract_templates
                WHERE tenant_id = :tid
                  AND (workflow_pack_id = :pack_id OR workflow_pack_id IS NULL)
                ORDER BY name
            """)
            result = await self.session.execute(stmt, {
                "tid": self.tenant_id,
                "pack_id": pack_id,
            })
            return [
                {
                    "template_id": str(row.template_id),
                    "name": row.name,
                    "department": row.department,
                    "region": row.region,
                    "business_unit": row.business_unit,
                }
                for row in result.fetchall()
            ]
        except Exception as exc:
            logger.debug("Could not query templates: %s", exc)
            return []

    async def _find_active_contracts(self, pack_id: str) -> list[dict[str, Any]]:
        """Find active contracts that reference the given workflow pack.

        Attempts to query the contracts table if it exists, otherwise
        returns an empty list gracefully.
        """
        try:
            from sqlalchemy import text as sa_text

            stmt = sa_text("""
                SELECT contract_id, title, department, region, business_unit, status
                FROM contracts
                WHERE tenant_id = :tid
                  AND workflow_pack_id = :pack_id
                  AND status IN ('active', 'executed', 'in_review')
                ORDER BY title
            """)
            result = await self.session.execute(stmt, {
                "tid": self.tenant_id,
                "pack_id": pack_id,
            })
            return [
                {
                    "contract_id": str(row.contract_id),
                    "title": row.title,
                    "department": row.department,
                    "region": row.region,
                    "business_unit": row.business_unit,
                    "status": row.status,
                }
                for row in result.fetchall()
            ]
        except Exception as exc:
            logger.debug("Could not query contracts: %s", exc)
            return []
