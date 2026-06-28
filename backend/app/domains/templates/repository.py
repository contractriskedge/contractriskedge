"""Template Library repository — tenant-scoped data access."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from .models import (
    ContractTemplate, TemplateVersion, TemplateVariable,
    TemplateCategory, TemplateFavorite, GeneratedContract,
    TemplateUsageHistory, TemplateClause, TemplateClauseRef,
    TemplatePackage, TemplatePackageItem,
)

logger = logging.getLogger(__name__)


class TemplateRepository:
    """Tenant-isolated data access for templates."""

    def __init__(self, session: AsyncSession, tenant_id: str):
        self.session = session
        self.tenant_id = tenant_id

    # ── Categories ────────────────────────────────────────────────

    async def list_categories(self) -> list[TemplateCategory]:
        stmt = (
            select(TemplateCategory)
            .where(
                TemplateCategory.tenant_id == self.tenant_id,
                TemplateCategory.is_active == True,
            )
            .order_by(TemplateCategory.display_order, TemplateCategory.name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_category(self, category_id: str) -> Optional[TemplateCategory]:
        stmt = select(TemplateCategory).where(
            TemplateCategory.id == category_id,
            TemplateCategory.tenant_id == self.tenant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_category(self, category: TemplateCategory) -> TemplateCategory:
        self.session.add(category)
        await self.session.flush()
        return category

    async def update_category(self, category: TemplateCategory) -> TemplateCategory:
        await self.session.flush()
        return category

    async def delete_category(self, category_id: str) -> bool:
        stmt = select(TemplateCategory).where(
            TemplateCategory.id == category_id,
            TemplateCategory.tenant_id == self.tenant_id,
        )
        result = await self.session.execute(stmt)
        cat = result.scalar_one_or_none()
        if not cat:
            return False
        cat.is_active = False
        await self.session.flush()
        return True

    async def get_category_template_count(self) -> dict[str, int]:
        stmt = sa_text("""
            SELECT c.id, COUNT(t.id)::int AS cnt
            FROM template_categories c
            LEFT JOIN contract_templates t ON t.category_id = c.id AND t.tenant_id = :tenant_id
            WHERE c.tenant_id = :tenant_id2
            GROUP BY c.id
        """)
        result = await self.session.execute(stmt, {
            "tenant_id": self.tenant_id, "tenant_id2": self.tenant_id,
        })
        return {str(row.id): row.cnt for row in result.fetchall()}

    # ── Templates ─────────────────────────────────────────────────

    async def list_templates(
        self,
        status: Optional[str] = None,
        category_id: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ContractTemplate], int]:
        query = select(ContractTemplate).where(
            ContractTemplate.tenant_id == self.tenant_id,
        )
        count_query = select(func.count(ContractTemplate.id)).where(
            ContractTemplate.tenant_id == self.tenant_id,
        )

        if status:
            query = query.where(ContractTemplate.status == status)
            count_query = count_query.where(ContractTemplate.status == status)
        if category_id:
            query = query.where(ContractTemplate.category_id == category_id)
            count_query = count_query.where(ContractTemplate.category_id == category_id)
        if search:
            pattern = f"%{search}%"
            query = query.where(
                ContractTemplate.name.ilike(pattern) |
                ContractTemplate.description.ilike(pattern) |
                ContractTemplate.tags.cast(sa_text).ilike(pattern)
            )
            count_query = count_query.where(
                ContractTemplate.name.ilike(pattern) |
                ContractTemplate.description.ilike(pattern) |
                ContractTemplate.tags.cast(sa_text).ilike(pattern)
            )

        # Get total count
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        # Fetch page
        offset = (page - 1) * page_size
        query = (
            query
            .options(joinedload(ContractTemplate.category))
            .order_by(ContractTemplate.updated_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self.session.execute(query)
        # Use unique() because of joinedload
        templates = list({row.id: row for row in result.scalars().unique().all()}.values())
        return templates, total

    async def get_template(self, template_id: str) -> Optional[ContractTemplate]:
        stmt = (
            select(ContractTemplate)
            .options(
                joinedload(ContractTemplate.category),
                joinedload(ContractTemplate.versions),
            )
            .where(
                ContractTemplate.id == template_id,
                ContractTemplate.tenant_id == self.tenant_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def create_template(self, template: ContractTemplate) -> ContractTemplate:
        self.session.add(template)
        await self.session.flush()
        return template

    async def update_template(self, template: ContractTemplate) -> ContractTemplate:
        template.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return template

    async def delete_template(self, template_id: str) -> bool:
        stmt = select(ContractTemplate).where(
            ContractTemplate.id == template_id,
            ContractTemplate.tenant_id == self.tenant_id,
        )
        result = await self.session.execute(stmt)
        tpl = result.scalar_one_or_none()
        if not tpl:
            return False
        await self.session.delete(tpl)
        await self.session.flush()
        return True

    async def increment_usage(self, template_id: str) -> None:
        await self.session.execute(
            sa_text("""
                UPDATE contract_templates
                SET usage_count = usage_count + 1
                WHERE id = :id AND tenant_id = :tenant_id
            """),
            {"id": template_id, "tenant_id": self.tenant_id},
        )
        await self.session.flush()

    # ── Versions ──────────────────────────────────────────────────

    async def get_version(self, version_id: str) -> Optional[TemplateVersion]:
        stmt = select(TemplateVersion).where(
            TemplateVersion.id == version_id,
            TemplateVersion.tenant_id == self.tenant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_version(self, version: TemplateVersion) -> TemplateVersion:
        self.session.add(version)
        await self.session.flush()
        return version

    async def get_latest_version_number(self, template_id: str) -> int:
        stmt = (
            select(func.coalesce(func.max(TemplateVersion.version_number), 0))
            .where(
                TemplateVersion.template_id == template_id,
                TemplateVersion.tenant_id == self.tenant_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def update_template_current_version(
        self, template_id: str, version_id: str,
    ) -> None:
        await self.session.execute(
            sa_text("""
                UPDATE contract_templates
                SET current_version_id = :version_id
                WHERE id = :id AND tenant_id = :tenant_id
            """),
            {"version_id": version_id, "id": template_id, "tenant_id": self.tenant_id},
        )
        await self.session.flush()

    # ── Variables ─────────────────────────────────────────────────

    async def save_variables(
        self, version_id: str, variables: list[TemplateVariable],
    ) -> None:
        for v in variables:
            v.tenant_id = self.tenant_id
            self.session.add(v)
        await self.session.flush()

    async def get_variables_by_version(self, version_id: str) -> list[TemplateVariable]:
        stmt = select(TemplateVariable).where(
            TemplateVariable.tenant_id == self.tenant_id,
        )
        # Variables are stored in the version's JSON, but we keep a
        # separate table for queryability. For now, return empty.
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ── Favorites ─────────────────────────────────────────────────

    async def toggle_favorite(
        self, template_id: str, user_id: str,
    ) -> bool:
        stmt = select(TemplateFavorite).where(
            TemplateFavorite.tenant_id == self.tenant_id,
            TemplateFavorite.template_id == template_id,
            TemplateFavorite.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        fav = result.scalar_one_or_none()
        if fav:
            await self.session.delete(fav)
            await self.session.flush()
            return False  # now not favorite
        fav = TemplateFavorite(
            tenant_id=self.tenant_id,
            template_id=template_id,
            user_id=user_id,
        )
        self.session.add(fav)
        await self.session.flush()
        return True  # now favorite

    async def get_favorite_ids(self, user_id: str) -> set[str]:
        stmt = select(TemplateFavorite.template_id).where(
            TemplateFavorite.tenant_id == self.tenant_id,
            TemplateFavorite.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        return {row[0] for row in result.fetchall()}

    # ── Generated Contracts ───────────────────────────────────────

    async def create_generated_contract(
        self, gc: GeneratedContract,
    ) -> GeneratedContract:
        self.session.add(gc)
        await self.session.flush()
        return gc

    async def get_generated_contract(
        self, contract_id: str,
    ) -> Optional[GeneratedContract]:
        stmt = select(GeneratedContract).where(
            GeneratedContract.id == contract_id,
            GeneratedContract.tenant_id == self.tenant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_generated_contract_by_idempotency(
        self, idempotency_key: str,
    ) -> Optional[GeneratedContract]:
        """Find an existing generated contract by idempotency key."""
        stmt = select(GeneratedContract).where(
            GeneratedContract.idempotency_key == idempotency_key,
            GeneratedContract.tenant_id == self.tenant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_drafts(
        self, user_id: str, limit: int = 20,
    ) -> list[GeneratedContract]:
        """List draft contracts for a user, ordered by most recent."""
        stmt = (
            select(GeneratedContract)
            .where(
                GeneratedContract.tenant_id == self.tenant_id,
                GeneratedContract.created_by == user_id,
                GeneratedContract.status == "draft",
                GeneratedContract.review_id.is_(None),
            )
            .order_by(GeneratedContract.updated_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ── Usage History ─────────────────────────────────────────────

    async def log_usage(
        self,
        template_id: str,
        action: str,
        actor_id: str,
        template_version_id: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> None:
        entry = TemplateUsageHistory(
            tenant_id=self.tenant_id,
            template_id=template_id,
            template_version_id=template_version_id,
            action=action,
            actor_id=actor_id,
            details=details or {},
        )
        self.session.add(entry)
        await self.session.flush()

    async def get_usage_history(
        self, template_id: str, limit: int = 50,
    ) -> list[TemplateUsageHistory]:
        stmt = (
            select(TemplateUsageHistory)
            .where(
                TemplateUsageHistory.tenant_id == self.tenant_id,
                TemplateUsageHistory.template_id == template_id,
            )
            .order_by(TemplateUsageHistory.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ── Dashboard Metrics ─────────────────────────────────────────

    async def get_metrics(self) -> dict:
        now = datetime.now(timezone.utc)
        first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Counts by status
        status_counts = {}
        stmt = sa_text("""
            SELECT status, COUNT(*)::int AS cnt
            FROM contract_templates
            WHERE tenant_id = :tenant_id
            GROUP BY status
        """)
        result = await self.session.execute(stmt, {"tenant_id": self.tenant_id})
        for row in result.fetchall():
            status_counts[str(row.status)] = row.cnt

        # Generated this month
        stmt = sa_text("""
            SELECT COUNT(*)::int
            FROM generated_contracts
            WHERE tenant_id = :tenant_id AND created_at >= :first_of_month
        """)
        result = await self.session.execute(stmt, {
            "tenant_id": self.tenant_id,
            "first_of_month": first_of_month,
        })
        generated_this_month = result.scalar() or 0

        # Most used templates
        stmt = (
            select(ContractTemplate)
            .where(
                ContractTemplate.tenant_id == self.tenant_id,
            )
            .order_by(ContractTemplate.usage_count.desc())
            .limit(5)
        )
        result = await self.session.execute(stmt)
        most_used = list(result.scalars().all())

        # Top categories by template count
        stmt = sa_text("""
            SELECT c.name, COUNT(t.id)::int AS cnt
            FROM template_categories c
            LEFT JOIN contract_templates t ON t.category_id = c.id AND t.tenant_id = :tenant_id
            WHERE c.tenant_id = :tenant_id2
            GROUP BY c.name
            ORDER BY cnt DESC
            LIMIT 5
        """)
        result = await self.session.execute(stmt, {
            "tenant_id": self.tenant_id, "tenant_id2": self.tenant_id,
        })
        top_categories = [{"name": row.name, "count": row.cnt} for row in result.fetchall()]

        return {
            "total_templates": sum(status_counts.values()),
            "approved_templates": status_counts.get("approved", 0),
            "draft_templates": status_counts.get("draft", 0),
            "generated_this_month": generated_this_month,
            "most_used_templates": most_used,
            "top_categories": top_categories,
        }

    # ── Clauses ───────────────────────────────────────────────────

    async def list_clauses(
        self,
        clause_type: Optional[str] = None,
        template_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[TemplateClause], int]:
        query = select(TemplateClause).where(
            TemplateClause.tenant_id == self.tenant_id,
        )
        count_query = select(func.count(TemplateClause.id)).where(
            TemplateClause.tenant_id == self.tenant_id,
        )
        if clause_type:
            query = query.where(TemplateClause.clause_type == clause_type)
            count_query = count_query.where(TemplateClause.clause_type == clause_type)
        if template_id:
            query = query.where(TemplateClause.template_id == template_id)
            count_query = count_query.where(TemplateClause.template_id == template_id)
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0
        offset = (page - 1) * page_size
        query = query.order_by(TemplateClause.display_order, TemplateClause.title).offset(offset).limit(page_size)
        result = await self.session.execute(query)
        return list(result.scalars().all()), total

    async def get_clause(self, clause_id: str) -> Optional[TemplateClause]:
        stmt = select(TemplateClause).where(
            TemplateClause.id == clause_id,
            TemplateClause.tenant_id == self.tenant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_clause(self, clause: TemplateClause) -> TemplateClause:
        self.session.add(clause)
        await self.session.flush()
        return clause

    async def update_clause(self, clause: TemplateClause) -> TemplateClause:
        clause.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return clause

    async def delete_clause(self, clause: TemplateClause) -> None:
        await self.session.delete(clause)
        await self.session.flush()

    # ── Clause Dependencies ───────────────────────────────────────

    async def get_clause_dependencies(self, clause_id: str) -> dict:
        """Count templates and contracts referencing a clause."""
        # Templates using this clause
        stmt = sa_text("""
            SELECT COUNT(DISTINCT tcr.template_id)::int AS template_count,
                   COUNT(DISTINCT gc.id)::int AS contract_count
            FROM template_clause_refs tcr
            LEFT JOIN generated_contracts gc ON gc.template_id = tcr.template_id
                AND gc.tenant_id = tcr.tenant_id
            WHERE tcr.clause_id = :clause_id AND tcr.tenant_id = :tenant_id
        """)
        result = await self.session.execute(stmt, {
            "clause_id": clause_id, "tenant_id": self.tenant_id,
        })
        row = result.fetchone()

        # Template names
        stmt2 = sa_text("""
            SELECT DISTINCT ct.id, ct.name
            FROM template_clause_refs tcr
            JOIN contract_templates ct ON ct.id = tcr.template_id
            WHERE tcr.clause_id = :clause_id AND tcr.tenant_id = :tenant_id
            LIMIT 50
        """)
        result2 = await self.session.execute(stmt2, {
            "clause_id": clause_id, "tenant_id": self.tenant_id,
        })
        templates = [{"id": r.id, "name": r.name} for r in result2.fetchall()]

        return {
            "template_count": row.template_count if row else 0,
            "contract_count": row.contract_count if row else 0,
            "templates": templates,
        }

    # ── Clause Analytics ──────────────────────────────────────────

    async def get_clause_analytics(self) -> dict:
        """Get clause library analytics."""
        now = datetime.now(timezone.utc)

        # Counts by status
        stmt = sa_text("""
            SELECT status, COUNT(*)::int AS cnt
            FROM template_clauses
            WHERE tenant_id = :tenant_id
            GROUP BY status
        """)
        result = await self.session.execute(stmt, {"tenant_id": self.tenant_id})
        status_counts = {str(row.status): row.cnt for row in result.fetchall()}

        # Most used clauses
        stmt = sa_text("""
            SELECT id, tenant_id, template_id, clause_type, title, content,
                   category, risk_level, ai_rewrite_allowed, fallback_clause_id,
                   is_required, is_conditional, condition_expression, display_order,
                   status, version, change_summary, approved_by, approved_at,
                   usage_count, contract_usage_count, created_by, updated_by,
                   created_at, updated_at
            FROM template_clauses
            WHERE tenant_id = :tenant_id
            ORDER BY usage_count DESC
            LIMIT 10
        """)
        result = await self.session.execute(stmt, {"tenant_id": self.tenant_id})
        most_used = [TemplateClause(**dict(row._mapping)) for row in result.fetchall()]

        # Highest risk clauses (critical + high)
        stmt = sa_text("""
            SELECT id, tenant_id, template_id, clause_type, title, content,
                   category, risk_level, ai_rewrite_allowed, fallback_clause_id,
                   is_required, is_conditional, condition_expression, display_order,
                   status, version, change_summary, approved_by, approved_at,
                   usage_count, contract_usage_count, created_by, updated_by,
                   created_at, updated_at
            FROM template_clauses
            WHERE tenant_id = :tenant_id AND risk_level IN ('critical', 'high')
            ORDER BY risk_level, usage_count DESC
            LIMIT 10
        """)
        result = await self.session.execute(stmt, {"tenant_id": self.tenant_id})
        highest_risk = [TemplateClause(**dict(row._mapping)) for row in result.fetchall()]

        # Deprecated clauses still in use
        stmt = sa_text("""
            SELECT tc.id, tc.tenant_id, tc.template_id, tc.clause_type, tc.title,
                   tc.content, tc.category, tc.risk_level, tc.ai_rewrite_allowed,
                   tc.fallback_clause_id, tc.is_required, tc.is_conditional,
                   tc.condition_expression, tc.display_order, tc.status, tc.version,
                   tc.change_summary, tc.approved_by, tc.approved_at,
                   tc.usage_count, tc.contract_usage_count, tc.created_by, tc.updated_by,
                   tc.created_at, tc.updated_at
            FROM template_clauses tc
            WHERE tc.tenant_id = :tenant_id AND tc.status = 'deprecated'
              AND tc.usage_count > 0
            ORDER BY tc.usage_count DESC
            LIMIT 10
        """)
        result = await self.session.execute(stmt, {"tenant_id": self.tenant_id})
        deprecated_still_used = [TemplateClause(**dict(row._mapping)) for row in result.fetchall()]

        # Average AI rewrite rate
        stmt = sa_text("""
            SELECT
                CASE WHEN COUNT(*) > 0
                    THEN (COUNT(*) FILTER (WHERE ai_rewrite_allowed = TRUE)::float / COUNT(*)::float) * 100
                    ELSE 0
                END AS rate
            FROM template_clauses
            WHERE tenant_id = :tenant_id
        """)
        result = await self.session.execute(stmt, {"tenant_id": self.tenant_id})
        row = result.fetchone()
        avg_ai_rewrite_rate = round(row.rate, 1) if row else 0

        # Clauses by type
        stmt = sa_text("""
            SELECT clause_type, COUNT(*)::int AS cnt
            FROM template_clauses
            WHERE tenant_id = :tenant_id
            GROUP BY clause_type
            ORDER BY cnt DESC
        """)
        result = await self.session.execute(stmt, {"tenant_id": self.tenant_id})
        clauses_by_type = [{"type": r.clause_type, "count": r.cnt} for r in result.fetchall()]

        # Clauses by risk level
        stmt = sa_text("""
            SELECT COALESCE(risk_level, 'unspecified') AS risk_level, COUNT(*)::int AS cnt
            FROM template_clauses
            WHERE tenant_id = :tenant_id
            GROUP BY risk_level
            ORDER BY cnt DESC
        """)
        result = await self.session.execute(stmt, {"tenant_id": self.tenant_id})
        clauses_by_risk = [{"level": r.risk_level, "count": r.cnt} for r in result.fetchall()]

        return {
            "total_clauses": sum(status_counts.values()),
            "published_clauses": status_counts.get("published", 0),
            "draft_clauses": status_counts.get("draft", 0),
            "most_used_clauses": most_used,
            "highest_risk_clauses": highest_risk,
            "deprecated_still_used": deprecated_still_used,
            "avg_ai_rewrite_rate": avg_ai_rewrite_rate,
            "clauses_by_type": clauses_by_type,
            "clauses_by_risk": clauses_by_risk,
        }

    # ── Clause Search (Global Search) ─────────────────────────────

    async def search_clauses(
        self,
        query: str,
        clause_type: Optional[str] = None,
        risk_level: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[TemplateClause], int]:
        """Search clauses by name, content, tags, risk, and category."""
        pattern = f"%{query}%"
        conditions = [
            TemplateClause.tenant_id == self.tenant_id,
            (
                TemplateClause.title.ilike(pattern) |
                TemplateClause.content.ilike(pattern) |
                TemplateClause.category.ilike(pattern) |
                TemplateClause.clause_type.ilike(pattern)
            ),
        ]
        if clause_type:
            conditions.append(TemplateClause.clause_type == clause_type)
        if risk_level:
            conditions.append(TemplateClause.risk_level == risk_level)

        count_query = select(func.count(TemplateClause.id)).where(*conditions)
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        offset = (page - 1) * page_size
        query_stmt = (
            select(TemplateClause)
            .where(*conditions)
            .order_by(TemplateClause.usage_count.desc(), TemplateClause.title)
            .offset(offset)
            .limit(page_size)
        )
        result = await self.session.execute(query_stmt)
        return list(result.scalars().all()), total

    # ── Clause Refs ───────────────────────────────────────────────

    async def set_clause_refs(
        self, template_version_id: str, refs: list[dict],
    ) -> list[dict]:
        """Replace all clause refs for a template version with new ones.

        Each ref must include clause_id and optionally clause_version, sort_order, etc.
        The clause_version is auto-resolved to the latest published version if not specified.
        """
        # Get the template_version to know tenant_id and template_id
        stmt = select(TemplateVersion).where(
            TemplateVersion.id == template_version_id,
        )
        result = await self.session.execute(stmt)
        ver = result.scalar_one_or_none()
        if not ver:
            raise ValueError("Template version not found")

        # Delete existing refs
        del_stmt = sa_text("""
            DELETE FROM template_clause_refs
            WHERE template_version_id = :tvid AND tenant_id = :tenant_id
        """)
        await self.session.execute(del_stmt, {
            "tvid": template_version_id,
            "tenant_id": self.tenant_id,
        })

        # Insert new refs
        now = datetime.now(timezone.utc)
        created_refs = []
        for i, ref in enumerate(refs):
            clause_id = ref.get("clause_id")
            clause_version = ref.get("clause_version", 1)

            # Auto-resolve to latest published version if not specified
            if not ref.get("clause_version"):
                cv_stmt = sa_text("""
                    SELECT version FROM template_clauses
                    WHERE id = :cid AND tenant_id = :tenant_id
                """)
                cv_result = await self.session.execute(cv_stmt, {
                    "cid": clause_id, "tenant_id": self.tenant_id,
                })
                cv_row = cv_result.fetchone()
                if cv_row:
                    clause_version = cv_row.version

            new_ref = TemplateClauseRef(
                tenant_id=self.tenant_id,
                template_id=ver.template_id,
                template_version_id=template_version_id,
                clause_id=clause_id,
                clause_version=clause_version,
                sort_order=ref.get("sort_order", i),
                is_required=ref.get("is_required", False),
                condition_expression=ref.get("condition_expression"),
                fallback_clause_id=ref.get("fallback_clause_id"),
                effective_from=ref.get("effective_from"),
                effective_to=ref.get("effective_to"),
                created_at=now,
            )
            self.session.add(new_ref)
            created_refs.append({
                "clause_id": clause_id,
                "clause_version": clause_version,
                "sort_order": ref.get("sort_order", i),
                "is_required": ref.get("is_required", False),
            })

        await self.session.flush()
        return created_refs

    async def get_clause_refs(self, template_version_id: str) -> list[dict]:
        """Get clause references with clause details for a template version."""
        stmt = sa_text("""
            SELECT
                tcr.id, tcr.template_id, tcr.template_version_id,
                tcr.clause_id, tcr.clause_version, tcr.sort_order,
                tcr.is_required, tcr.condition_expression,
                tcr.fallback_clause_id,
                tcr.effective_from, tcr.effective_to,
                tc.title AS clause_title,
                tc.clause_type,
                tc.risk_level,
                tc.content AS clause_content,
                tc.status AS clause_status
            FROM template_clause_refs tcr
            JOIN template_clauses tc ON tc.id = tcr.clause_id
            WHERE tcr.template_version_id = :tvid
            ORDER BY tcr.sort_order
        """)
        result = await self.session.execute(stmt, {
            "tvid": template_version_id,
        })
        return [dict(row._mapping) for row in result.fetchall()]

    # ── Template Packages ────────────────────────────────────────

    async def list_packages(
        self,
        industry: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[TemplatePackage], int]:
        query = select(TemplatePackage).where(
            TemplatePackage.tenant_id == self.tenant_id,
        )
        count_query = select(func.count(TemplatePackage.id)).where(
            TemplatePackage.tenant_id == self.tenant_id,
        )
        if industry:
            query = query.where(TemplatePackage.industry == industry)
            count_query = count_query.where(TemplatePackage.industry == industry)

        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        offset = (page - 1) * page_size
        query = (
            query
            .options(joinedload(TemplatePackage.items))
            .order_by(TemplatePackage.updated_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self.session.execute(query)
        packages = list({row.id: row for row in result.scalars().unique().all()}.values())
        return packages, total

    async def get_package(self, package_id: str) -> Optional[TemplatePackage]:
        stmt = (
            select(TemplatePackage)
            .options(joinedload(TemplatePackage.items))
            .where(
                TemplatePackage.id == package_id,
                TemplatePackage.tenant_id == self.tenant_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def create_package(self, package: TemplatePackage) -> TemplatePackage:
        self.session.add(package)
        await self.session.flush()
        return package

    async def update_package(self, package: TemplatePackage) -> TemplatePackage:
        package.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return package

    async def delete_package(self, package_id: str) -> bool:
        stmt = select(TemplatePackage).where(
            TemplatePackage.id == package_id,
            TemplatePackage.tenant_id == self.tenant_id,
        )
        result = await self.session.execute(stmt)
        pkg = result.scalar_one_or_none()
        if not pkg:
            return False
        await self.session.delete(pkg)
        await self.session.flush()
        return True

    async def set_package_items(
        self, package_id: str, items: list,
    ) -> list[dict]:
        """Replace all items in a package with new ones."""
        # Delete existing items
        del_stmt = sa_text("""
            DELETE FROM template_package_items
            WHERE package_id = :pid AND tenant_id = :tenant_id
        """)
        await self.session.execute(del_stmt, {
            "pid": package_id, "tenant_id": self.tenant_id,
        })

        # Insert new items
        result_items = []
        for i, item in enumerate(items):
            pi = TemplatePackageItem(
                tenant_id=self.tenant_id,
                package_id=package_id,
                template_id=item.template_id if hasattr(item, 'template_id') else item.get('template_id'),
                display_order=item.display_order if hasattr(item, 'display_order') else item.get('display_order', i),
                is_required=item.is_required if hasattr(item, 'is_required') else item.get('is_required', True),
            )
            self.session.add(pi)
            result_items.append({
                "template_id": pi.template_id,
                "display_order": pi.display_order,
            })

        await self.session.flush()
        return result_items
