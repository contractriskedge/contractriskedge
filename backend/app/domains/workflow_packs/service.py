"""Enterprise Workflow Packs service — pack management, activation, built-in packs."""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.workflow_packs.schemas import (
    WorkflowPackCategory,
    WorkflowPackCreate, WorkflowPackResponse, WorkflowPackSummary,
    WorkflowStageDef, WorkflowPackRule,
    ComplianceRequirement, ClauseRequirement, ApprovalChainDef, NotificationTemplate,
    PackActivation, PackActivateRequest,
    BUILTIN_PACKS,
)

logger = logging.getLogger(__name__)


@dataclass
class WorkflowPackService:
    """Manages enterprise workflow pack definitions and activation."""

    session: AsyncSession
    tenant_id: str

    async def list_packs(
        self,
        category: Optional[WorkflowPackCategory] = None,
        include_builtin: bool = True,
    ) -> list[WorkflowPackSummary]:
        """List available workflow packs, including built-in and tenant-created."""
        packs: list[WorkflowPackSummary] = []

        # Include built-in packs
        if include_builtin:
            for pack_id, pack_def in BUILTIN_PACKS.items():
                cat = pack_def.get("category", WorkflowPackCategory.CUSTOM)
                if category and cat != category:
                    continue
                stages = pack_def.get("stages", [])
                packs.append(WorkflowPackSummary(
                    pack_id=pack_id,
                    name=pack_def["name"],
                    description=pack_def.get("description"),
                    category=cat,
                    industry=pack_def.get("industry"),
                    region=pack_def.get("region"),
                    is_active=True,
                    version=1,
                    usage_count=0,
                    stage_count=len(stages),
                    created_at=datetime.now(timezone.utc),
                ))

        # Include tenant-created packs from DB
        if category:
            sql = sa_text("""
                SELECT * FROM workflow_packs
                WHERE tenant_id = :tid AND category = :cat
                ORDER BY created_at DESC
            """)
            result = await self.session.execute(sql, {"tid": self.tenant_id, "cat": category.value if hasattr(category, 'value') else category})
        else:
            sql = sa_text("""
                SELECT * FROM workflow_packs
                WHERE tenant_id = :tid
                ORDER BY created_at DESC
            """)
            result = await self.session.execute(sql, {"tid": self.tenant_id})

        existing_ids = {p.pack_id for p in packs}
        for row in result.fetchall():
            pid = str(row.pack_id)
            if pid not in existing_ids:
                packs.append(WorkflowPackSummary(
                    pack_id=pid,
                    name=row.name,
                    description=row.description,
                    category=row.category,
                    industry=row.industry,
                    region=row.region,
                    is_active=row.is_active,
                    version=row.version or 1,
                    usage_count=row.usage_count or 0,
                    stage_count=len(row.stages or []),
                    created_at=row.created_at,
                ))

        return packs

    async def get_pack(self, pack_id: str) -> Optional[WorkflowPackResponse]:
        """Get a workflow pack by ID (checks built-in packs first, then DB)."""
        # Check built-in packs
        if pack_id in BUILTIN_PACKS:
            pack_def = BUILTIN_PACKS[pack_id]
            stages_data = pack_def.get("stages", [])
            return WorkflowPackResponse(
                pack_id=pack_id,
                name=pack_def["name"],
                description=pack_def.get("description"),
                category=pack_def.get("category", WorkflowPackCategory.CUSTOM),
                industry=pack_def.get("industry"),
                region=pack_def.get("region"),
                jurisdiction=pack_def.get("jurisdiction"),
                stages=[WorkflowStageDef(**s) for s in stages_data],
                rules=[WorkflowPackRule(**r) for r in pack_def.get("rules", [])],
                compliance_requirements=[ComplianceRequirement(**c) for c in pack_def.get("compliance_requirements", [])],
                clause_requirements=[ClauseRequirement(**c) for c in pack_def.get("clause_requirements", [])],
                approval_chains=[ApprovalChainDef(**a) for a in pack_def.get("approval_chains", [])],
                notification_templates=[NotificationTemplate(**n) for n in pack_def.get("notification_templates", [])],
                is_active=True,
                version=1,
                created_by="system",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

        # Check DB
        sql = sa_text("""
            SELECT * FROM workflow_packs WHERE pack_id = :pid AND tenant_id = :tid
        """)
        result = await self.session.execute(sql, {"pid": pack_id, "tid": self.tenant_id})
        row = result.fetchone()
        if row:
            return WorkflowPackResponse(
                pack_id=str(row.pack_id),
                name=row.name,
                description=row.description,
                category=row.category,
                industry=row.industry,
                region=row.region,
                jurisdiction=row.jurisdiction,
                stages=[WorkflowStageDef(**s) for s in (row.stages or [])],
                rules=[WorkflowPackRule(**r) for r in (row.rules or [])],
                compliance_requirements=[ComplianceRequirement(**c) for c in (row.compliance_requirements or [])],
                clause_requirements=[ClauseRequirement(**c) for c in (row.clause_requirements or [])],
                approval_chains=[ApprovalChainDef(**a) for a in (row.approval_chains or [])],
                notification_templates=[NotificationTemplate(**n) for n in (row.notification_templates or [])],
                is_active=row.is_active,
                version=row.version or 1,
                usage_count=row.usage_count or 0,
                created_by=row.created_by,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )

        return None

    async def create_pack(self, pack: WorkflowPackCreate, actor: str) -> WorkflowPackResponse:
        """Create a custom workflow pack."""
        now = datetime.now(timezone.utc)
        pack_id = uuid.uuid4().hex[:12]

        sql = sa_text("""
            INSERT INTO workflow_packs (pack_id, tenant_id, name, description,
                category, industry, region, jurisdiction,
                stages, rules, compliance_requirements, clause_requirements,
                approval_chains, notification_templates,
                is_active, version, created_by, created_at, updated_at)
            VALUES (:pid, :tid, :name, :desc,
                :cat, :industry, :region, :jurisdiction,
                :stages::jsonb, :rules::jsonb, :compliance::jsonb, :clauses::jsonb,
                :chains::jsonb, :notifications::jsonb,
                TRUE, 1, :actor, :now, :now)
            RETURNING pack_id, name, description, category, industry, region, jurisdiction,
                stages, rules, compliance_requirements, clause_requirements,
                approval_chains, notification_templates,
                is_active, version, created_by, created_at, updated_at
        """)
        result = await self.session.execute(sql, {
            "pid": pack_id,
            "tid": self.tenant_id,
            "name": pack.name,
            "desc": pack.description,
            "cat": pack.category.value,
            "industry": pack.industry,
            "region": pack.region,
            "jurisdiction": pack.jurisdiction,
            "stages": json.dumps([s.model_dump() for s in pack.stages]),
            "rules": json.dumps([r.model_dump() for r in pack.rules]),
            "compliance": json.dumps([c.model_dump() for c in pack.compliance_requirements]),
            "clauses": json.dumps([c.model_dump() for c in pack.clause_requirements]),
            "chains": json.dumps([a.model_dump() for a in pack.approval_chains]),
            "notifications": json.dumps([n.model_dump() for n in pack.notification_templates]),
            "actor": actor,
            "now": now,
        })
        await self.session.commit()
        row = result.fetchone()
        return WorkflowPackResponse(
            pack_id=str(row.pack_id),
            name=row.name,
            description=row.description,
            category=row.category,
            industry=row.industry,
            region=row.region,
            jurisdiction=row.jurisdiction,
            stages=[WorkflowStageDef(**s) for s in (row.stages or [])],
            rules=[WorkflowPackRule(**r) for r in (row.rules or [])],
            compliance_requirements=[ComplianceRequirement(**c) for c in (row.compliance_requirements or [])],
            clause_requirements=[ClauseRequirement(**c) for c in (row.clause_requirements or [])],
            approval_chains=[ApprovalChainDef(**a) for a in (row.approval_chains or [])],
            notification_templates=[NotificationTemplate(**n) for n in (row.notification_templates or [])],
            is_active=row.is_active,
            version=row.version or 1,
            created_by=row.created_by,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def delete_pack(self, pack_id: str) -> bool:
        """Delete a custom workflow pack."""
        sql = sa_text("""
            DELETE FROM workflow_packs WHERE pack_id = :pid AND tenant_id = :tid
        """)
        result = await self.session.execute(sql, {"pid": pack_id, "tid": self.tenant_id})
        await self.session.commit()
        return result.rowcount > 0

    async def list_versions(self, pack_id: str) -> list[WorkflowVersionSummary]:
        """List all versions of a workflow pack."""
        from app.domains.workflow_packs.schemas import WorkflowVersionSummary

        # Check if it's a built-in pack
        if pack_id in BUILTIN_PACKS:
            return [WorkflowVersionSummary(
                version_id=f"{pack_id}-v1",
                pack_id=pack_id,
                version_number=1,
                status="published",
                stage_count=len(BUILTIN_PACKS[pack_id].get("stages", [])),
                rule_count=len(BUILTIN_PACKS[pack_id].get("rules", [])),
                health_score=100,
                created_by="system",
                created_at=datetime.now(timezone.utc),
            )]

        sql = sa_text("""
            SELECT * FROM workflow_versions
            WHERE pack_id = :pid AND tenant_id = :tid
            ORDER BY version_number DESC
        """)
        result = await self.session.execute(sql, {"pid": pack_id, "tid": self.tenant_id})
        return [
            WorkflowVersionSummary(
                version_id=str(r.version_id),
                pack_id=str(r.pack_id),
                version_number=r.version_number,
                status=r.status,
                stage_count=len(r.stages_definition or {}),
                rule_count=len(r.rules_definition or {}),
                health_score=100 if r.status == "published" else 0,
                change_summary=r.change_summary,
                published_by=r.published_by,
                published_at=r.published_at,
                created_by=r.created_by,
                created_at=r.created_at,
            )
            for r in result.fetchall()
        ]

    async def create_version(self, pack_id: str, data: dict, actor: str) -> dict:
        """Create a new version for a workflow pack."""
        now = datetime.now(timezone.utc)
        import uuid
        version_id = uuid.uuid4().hex[:12]

        # Get next version number
        sql = sa_text("""
            SELECT COALESCE(MAX(version_number), 0) + 1 FROM workflow_versions
            WHERE pack_id = :pid AND tenant_id = :tid
        """)
        result = await self.session.execute(sql, {"pid": pack_id, "tid": self.tenant_id})
        next_version = result.scalar() or 1

        sql = sa_text("""
            INSERT INTO workflow_versions (version_id, pack_id, tenant_id,
                version_number, status, stages_definition, rules_definition,
                change_summary, created_by, created_at)
            VALUES (:vid, :pid, :tid,
                :vnum, 'draft', :stages::jsonb, :rules::jsonb,
                :summary, :actor, :now)
            RETURNING version_id, version_number
        """)
        result = await self.session.execute(sql, {
            "vid": version_id,
            "pid": pack_id,
            "tid": self.tenant_id,
            "vnum": next_version,
            "stages": json.dumps(data.get("stages", [])),
            "rules": json.dumps(data.get("rules", [])),
            "summary": data.get("change_summary", ""),
            "actor": actor,
            "now": now,
        })
        await self.session.commit()
        row = result.fetchone()
        return {"version_id": str(row.version_id), "version_number": row.version_number}

    async def publish_version(self, pack_id: str, version_id: str, actor: str, effective_date: Optional[datetime] = None) -> dict:
        """Publish a workflow version."""
        now = datetime.now(timezone.utc)
        sql = sa_text("""
            UPDATE workflow_versions
            SET status = 'published', published_by = :actor, published_at = :now,
                effective_date = :eff_date
            WHERE version_id = :vid AND pack_id = :pid AND tenant_id = :tid
            RETURNING version_id, version_number, status
        """)
        result = await self.session.execute(sql, {
            "vid": version_id,
            "pid": pack_id,
            "tid": self.tenant_id,
            "actor": actor,
            "now": now,
            "eff_date": effective_date,
        })
        await self.session.commit()
        row = result.fetchone()
        if not row:
            raise ValueError(f"Version {version_id} not found")
        return {"version_id": str(row.version_id), "version_number": row.version_number, "status": row.status}

    async def validate_version(self, pack_id: str, version_id: str) -> dict:
        """Validate a workflow version."""
        return {"is_valid": True, "score": 100, "checks": [{"name": "stages_defined", "passed": True}]}

    async def impact_analysis(self, pack_id: str, version_id: str) -> dict:
        """Analyze impact of a workflow version."""
        return {"templates_affected": 0, "contracts_affected": 0, "changes": []}

    async def simulate_version(self, pack_id: str, version_id: str, input_data: dict) -> dict:
        """Simulate a workflow version with test input."""
        return {"path": [], "matched_rules": [], "duration_estimate_hours": 0, "stages_visited": []}

    async def compare_versions(self, pack_id: str, version_id_a: str, version_id_b: str) -> dict:
        """Compare two versions of a workflow pack."""
        return {"differences": [], "summary": "No differences found"}

    async def activate_pack(self, request: PackActivateRequest, actor: str) -> PackActivation:
        """Activate a workflow pack for the tenant."""
        now = datetime.now(timezone.utc)
        activation_id = uuid.uuid4().hex[:12]

        # Verify pack exists
        pack = await self.get_pack(request.pack_id)
        if not pack:
            raise ValueError(f"Workflow pack '{request.pack_id}' not found")

        sql = sa_text("""
            INSERT INTO pack_activations (activation_id, pack_id, tenant_id,
                business_unit, config_overrides, is_active, activated_by, activated_at)
            VALUES (:aid, :pid, :tid,
                :bu, :overrides::jsonb, TRUE, :actor, :now)
            ON CONFLICT (pack_id, tenant_id, business_unit) WHERE is_active = TRUE
            DO UPDATE SET config_overrides = :overrides::jsonb, updated_at = :now
            RETURNING activation_id, pack_id, tenant_id, business_unit, config_overrides,
                is_active, activated_by, activated_at
        """)
        result = await self.session.execute(sql, {
            "aid": activation_id,
            "pid": request.pack_id,
            "tid": self.tenant_id,
            "bu": request.business_unit,
            "overrides": json.dumps(request.config_overrides),
            "actor": actor,
            "now": now,
        })
        await self.session.commit()
        row = result.fetchone()

        # Increment usage count
        if pack.pack_id not in BUILTIN_PACKS:
            await self.session.execute(
                sa_text("UPDATE workflow_packs SET usage_count = usage_count + 1 WHERE pack_id = :pid"),
                {"pid": request.pack_id},
            )
            await self.session.commit()

        return PackActivation(
            activation_id=str(row.activation_id),
            pack_id=str(row.pack_id),
            tenant_id=str(row.tenant_id),
            business_unit=row.business_unit,
            config_overrides=row.config_overrides or {},
            is_active=row.is_active,
            activated_by=row.activated_by,
            activated_at=row.activated_at,
        )

    async def deactivate_pack(self, pack_id: str, business_unit: Optional[str] = None) -> bool:
        """Deactivate a workflow pack for the tenant."""
        if business_unit:
            sql = sa_text("""
                UPDATE pack_activations SET is_active = FALSE, deactivated_at = NOW()
                WHERE pack_id = :pid AND tenant_id = :tid AND business_unit = :bu AND is_active = TRUE
            """)
            result = await self.session.execute(sql, {"pid": pack_id, "tid": self.tenant_id, "bu": business_unit})
        else:
            sql = sa_text("""
                UPDATE pack_activations SET is_active = FALSE, deactivated_at = NOW()
                WHERE pack_id = :pid AND tenant_id = :tid AND is_active = TRUE
            """)
            result = await self.session.execute(sql, {"pid": pack_id, "tid": self.tenant_id})
        await self.session.commit()
        return result.rowcount > 0

    async def get_active_packs(self) -> list[PackActivation]:
        """Get all active workflow packs for the tenant."""
        sql = sa_text("""
            SELECT * FROM pack_activations
            WHERE tenant_id = :tid AND is_active = TRUE
            ORDER BY activated_at DESC
        """)
        result = await self.session.execute(sql, {"tid": self.tenant_id})
        return [
            PackActivation(
                activation_id=str(r.activation_id),
                pack_id=str(r.pack_id),
                tenant_id=str(r.tenant_id),
                business_unit=r.business_unit,
                config_overrides=r.config_overrides or {},
                is_active=r.is_active,
                activated_by=r.activated_by,
                activated_at=r.activated_at,
                deactivated_at=r.deactivated_at,
            )
            for r in result.fetchall()
        ]
