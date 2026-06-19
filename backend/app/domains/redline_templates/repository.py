"""Repository for RedlineTemplate data access."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func, update, delete as sa_delete, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.redline_templates.models import RedlineTemplate


class RedlineTemplateRepository:
    """Data access for redline templates."""

    def __init__(self, session: AsyncSession, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id

    async def create(self, data: dict) -> RedlineTemplate:
        template = RedlineTemplate(
            tenant_id=self.tenant_id,
            **data,
        )
        self.session.add(template)
        await self.session.flush()
        return template

    async def get(self, template_id: str) -> Optional[RedlineTemplate]:
        stmt = select(RedlineTemplate).where(
            RedlineTemplate.template_id == template_id,
            RedlineTemplate.tenant_id == self.tenant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        clause_type: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[RedlineTemplate]:
        query = select(RedlineTemplate).where(RedlineTemplate.tenant_id == self.tenant_id)
        if clause_type:
            query = query.where(RedlineTemplate.clause_type == clause_type)
        if category:
            query = query.where(RedlineTemplate.category == category)
        if status:
            query = query.where(RedlineTemplate.status == status)
        query = query.order_by(RedlineTemplate.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(self, template_id: str, data: dict) -> Optional[RedlineTemplate]:
        data["updated_at"] = datetime.now(timezone.utc)
        stmt = (
            update(RedlineTemplate)
            .where(
                RedlineTemplate.template_id == template_id,
                RedlineTemplate.tenant_id == self.tenant_id,
            )
            .values(**data)
        )
        await self.session.execute(stmt)
        await self.session.flush()
        return await self.get(template_id)

    async def delete(self, template_id: str) -> bool:
        stmt = sa_delete(RedlineTemplate).where(
            RedlineTemplate.template_id == template_id,
            RedlineTemplate.tenant_id == self.tenant_id,
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0

    async def record_usage(self, template_id: str, accepted: bool = True) -> None:
        """Increment usage count and update accept_rate."""
        template = await self.get(template_id)
        if not template:
            return
        new_count = template.usage_count + 1
        new_rate = ((template.accept_rate * template.usage_count) + (1.0 if accepted else 0.0)) / new_count
        stmt = (
            update(RedlineTemplate)
            .where(RedlineTemplate.template_id == template_id)
            .values(
                usage_count=new_count,
                accept_rate=new_rate,
                last_used=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def get_coverage(self) -> dict:
        """Get template coverage analytics grouped by clause_type.

        Returns counts of findings and templates per clause_type.
        """
        from sqlalchemy import text as sa_text

        # Get template counts per clause_type
        template_sql = sa_text("""
            SELECT clause_type, COUNT(*) as templates,
                   COUNT(*) FILTER (WHERE status = 'active') as active_templates
            FROM redline_templates
            WHERE tenant_id = :tenant_id
            GROUP BY clause_type
        """)
        t_result = await self.session.execute(template_sql, {"tenant_id": self.tenant_id})
        template_counts = {r.clause_type: {"templates": r.templates, "active": r.active_templates} for r in t_result.fetchall()}

        # Get finding counts per clause_type from review_findings
        finding_sql = sa_text("""
            SELECT rf.clause_type, COUNT(*) as findings
            FROM review_findings rf
            JOIN contract_reviews cr ON rf.review_id = cr.review_id
            WHERE rf.tenant_id = :tenant_id
              AND cr.is_deleted = FALSE
            GROUP BY rf.clause_type
            ORDER BY findings DESC
        """)
        f_result = await self.session.execute(finding_sql, {"tenant_id": self.tenant_id})
        finding_counts = {r.clause_type: r.findings for r in f_result.fetchall()}

        # Merge
        all_types = set(list(template_counts.keys()) + list(finding_counts.keys()))
        by_clause = []
        total_findings = 0
        total_templates = 0
        covered_findings = 0

        for ct in sorted(all_types):
            findings = finding_counts.get(ct, 0)
            templates = template_counts.get(ct, {}).get("templates", 0)
            active = template_counts.get(ct, {}).get("active", 0)
            total_findings += findings
            total_templates += templates
            if templates > 0:
                covered_findings += findings

            if templates > 0 and findings > 0:
                status = "covered"
            elif templates > 0 and findings == 0:
                status = "partial"
            else:
                status = "missing"

            by_clause.append({
                "clause_type": ct,
                "total_findings": findings,
                "templates_available": templates,
                "active_templates": active,
                "coverage_pct": round((templates / max(findings, 1)) * 100, 1) if findings > 0 else 0.0,
                "status": status,
            })

        return {
            "total_findings": total_findings,
            "total_templates": total_templates,
            "templates_used": covered_findings,
            "templates_missing": total_findings - covered_findings,
            "coverage_pct": round((covered_findings / max(total_findings, 1)) * 100, 1),
            "by_clause_type": by_clause,
        }

    async def get_missing_templates(self, limit: int = 20) -> list[dict]:
        """Find clause types with findings but no templates, ranked by frequency."""
        sql = sa_text("""
            SELECT rf.clause_type, COUNT(*) as findings,
                   MIN(cr.created_at) as first_seen,
                   MAX(cr.created_at) as last_seen
            FROM review_findings rf
            JOIN contract_reviews cr ON rf.review_id = cr.review_id
            WHERE rf.tenant_id = :tenant_id
              AND cr.is_deleted = FALSE
              AND NOT EXISTS (
                  SELECT 1 FROM redline_templates rt
                  WHERE rt.tenant_id = rf.tenant_id
                    AND rt.clause_type = rf.clause_type
                    AND rt.status = 'active'
              )
            GROUP BY rf.clause_type
            ORDER BY findings DESC
            LIMIT :limit
        """)
        result = await self.session.execute(sql, {"tenant_id": self.tenant_id, "limit": limit})
        return [dict(r._mapping) for r in result.fetchall()]
