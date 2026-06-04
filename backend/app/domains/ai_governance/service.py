"""AI Governance service — prompt registry, evaluation harness, regression testing, model audit."""

from __future__ import annotations

import difflib
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.ai_governance.schemas import (
    PromptState, EvaluationStatus, TestOutcome, ModelProvider,
    PromptTemplateCreate, PromptTemplateUpdate, PromptVersionResponse, PromptSummary,
    EvaluationDatasetCreate, EvaluationDatasetResponse,
    TestCaseInput, TestCaseResult, EvaluationRunResponse,
    RegressionSuiteCreate, RegressionSuiteResponse, RegressionRunResponse,
    ConfidenceCalibrationRecord, CalibrationPoint, CalibrationRecommendation,
    ModelAuditEvent, ModelAuditLogResponse,
    AIQualityDashboard, ModelUsageSummary,
    CostSummaryResponse, ModelCostBreakdown, ModelRequestBreakdown,
    ModelLatencyBreakdown, SafetySummaryResponse, ApprovalTypeBreakdown,
)

logger = logging.getLogger(__name__)


@dataclass
class PromptRegistryService:
    """Persistent prompt template registry with versioning and diff tracking."""

    session: AsyncSession
    tenant_id: str

    async def create_prompt(self, prompt: PromptTemplateCreate, actor: str) -> PromptVersionResponse:
        """Create a new prompt template with initial version."""
        now = datetime.now(timezone.utc)
        version_id = uuid.uuid4().hex[:12]

        sql = sa_text("""
            INSERT INTO prompt_templates (version_id, prompt_key, version_number, name,
                description, template, system_prompt, default_model, default_temperature,
                default_max_tokens, response_schema, tags, state, created_by, created_at)
            VALUES (:vid, :key, 1, :name,
                :desc, :template, :system_prompt, :model, :temp,
                :max_tokens, :schema::jsonb, :tags, 'active', :actor, :now)
            RETURNING version_id, prompt_key, version_number, name, description,
                template, system_prompt, default_model, default_temperature,
                default_max_tokens, response_schema, tags, state, created_by, created_at
        """)
        result = await self.session.execute(sql, {
            "vid": version_id,
            "key": prompt.key,
            "name": prompt.name,
            "desc": prompt.description,
            "template": prompt.template,
            "system_prompt": prompt.system_prompt,
            "model": prompt.default_model,
            "temp": prompt.default_temperature,
            "max_tokens": prompt.default_max_tokens,
            "schema": json.dumps(prompt.response_schema) if prompt.response_schema else None,
            "tags": prompt.tags,
            "actor": actor,
            "now": now,
        })
        await self.session.commit()
        row = result.fetchone()
        return self._row_to_version_response(row)

    async def create_version(self, prompt_key: str, prompt: PromptTemplateUpdate, actor: str) -> PromptVersionResponse:
        """Create a new version of an existing prompt template."""
        # Get current active version
        current = await self._get_active_version(prompt_key)
        if not current:
            raise ValueError(f"No active prompt found for key '{prompt_key}'")

        now = datetime.now(timezone.utc)
        version_id = uuid.uuid4().hex[:12]
        new_version_number = current.version_number + 1

        # Compute diff
        old_template = current.template
        new_template = prompt.template if prompt.template is not None else old_template
        diff = self._compute_diff(old_template, new_template)

        sql = sa_text("""
            INSERT INTO prompt_templates (version_id, prompt_key, version_number, name,
                description, template, system_prompt, default_model, default_temperature,
                default_max_tokens, response_schema, tags, state, diff_from_previous,
                previous_version_id, created_by, created_at)
            VALUES (:vid, :key, :vnum, :name,
                :desc, :template, :system_prompt, :model, :temp,
                :max_tokens, :schema::jsonb, :tags, 'draft', :diff,
                :prev_vid, :actor, :now)
            RETURNING version_id, prompt_key, version_number, name, description,
                template, system_prompt, default_model, default_temperature,
                default_max_tokens, response_schema, tags, state,
                diff_from_previous, previous_version_id, created_by, created_at
        """)
        result = await self.session.execute(sql, {
            "vid": version_id,
            "key": prompt_key,
            "vnum": new_version_number,
            "name": prompt.name or current.name,
            "desc": prompt.description if prompt.description is not None else current.description,
            "template": new_template,
            "system_prompt": prompt.system_prompt if prompt.system_prompt is not None else current.system_prompt,
            "model": prompt.default_model or current.default_model,
            "temp": prompt.default_temperature if prompt.default_temperature is not None else current.default_temperature,
            "max_tokens": prompt.default_max_tokens or current.default_max_tokens,
            "schema": json.dumps(prompt.response_schema) if prompt.response_schema else current.response_schema,
            "tags": prompt.tags or current.tags,
            "diff": diff,
            "prev_vid": current.version_id,
            "actor": actor,
            "now": now,
        })
        await self.session.commit()
        row = result.fetchone()
        return self._row_to_version_response(row)

    async def list_prompts(self) -> list[PromptSummary]:
        """List all prompt templates with their latest version info."""
        sql = sa_text("""
            SELECT DISTINCT ON (pt.prompt_key)
                pt.prompt_key, pt.name, pt.description, pt.version_number,
                pt.state, pt.tags, pt.created_at, pt.created_at as updated_at
            FROM prompt_templates pt
            ORDER BY pt.prompt_key, pt.version_number DESC
        """)
        result = await self.session.execute(sql)
        return [
            PromptSummary(
                prompt_key=r.prompt_key,
                name=r.name,
                description=r.description,
                active_version=r.version_number,
                state=r.state,
                tags=r.tags or [],
                created_at=r.created_at,
                updated_at=r.created_at,
            )
            for r in result.fetchall()
        ]

    async def get_prompt(self, prompt_key: str, version: Optional[int] = None) -> Optional[PromptVersionResponse]:
        """Get a specific version of a prompt template."""
        if version:
            sql = sa_text("""
                SELECT * FROM prompt_templates
                WHERE prompt_key = :key AND version_number = :vnum
                ORDER BY version_number DESC LIMIT 1
            """)
            result = await self.session.execute(sql, {"key": prompt_key, "vnum": version})
        else:
            sql = sa_text("""
                SELECT * FROM prompt_templates
                WHERE prompt_key = :key AND state = 'active'
                ORDER BY version_number DESC LIMIT 1
            """)
            result = await self.session.execute(sql, {"key": prompt_key})
        row = result.fetchone()
        return self._row_to_version_response(row) if row else None

    async def activate_version(self, prompt_key: str, version_number: int, actor: str) -> PromptVersionResponse:
        """Activate a specific version of a prompt template."""
        now = datetime.now(timezone.utc)

        # Deactivate all versions
        await self.session.execute(
            sa_text("""
                UPDATE prompt_templates SET state = 'deprecated', updated_at = :now
                WHERE prompt_key = :key AND state = 'active'
            """),
            {"key": prompt_key, "now": now},
        )

        # Activate the specified version
        sql = sa_text("""
            UPDATE prompt_templates SET state = 'active', updated_at = :now
            WHERE prompt_key = :key AND version_number = :vnum
            RETURNING version_id, prompt_key, version_number, name, description,
                template, system_prompt, default_model, default_temperature,
                default_max_tokens, response_schema, tags, state,
                diff_from_previous, previous_version_id, created_by, created_at
        """)
        result = await self.session.execute(sql, {
            "key": prompt_key, "vnum": version_number, "now": now,
        })
        await self.session.commit()
        row = result.fetchone()
        if not row:
            raise ValueError(f"Version {version_number} not found for prompt '{prompt_key}'")
        return self._row_to_version_response(row)

    async def _get_active_version(self, prompt_key: str) -> Optional[PromptVersionResponse]:
        """Get the currently active version of a prompt."""
        sql = sa_text("""
            SELECT * FROM prompt_templates
            WHERE prompt_key = :key AND state = 'active'
            ORDER BY version_number DESC LIMIT 1
        """)
        result = await self.session.execute(sql, {"key": prompt_key})
        row = result.fetchone()
        return self._row_to_version_response(row) if row else None

    def _compute_diff(self, old_text: str, new_text: str) -> str:
        """Compute a unified diff between two template versions."""
        diff = difflib.unified_diff(
            old_text.splitlines(keepends=True),
            new_text.splitlines(keepends=True),
            fromfile="previous",
            tofile="current",
        )
        return "".join(diff)

    def _row_to_version_response(self, row) -> PromptVersionResponse:
        return PromptVersionResponse(
            version_id=str(row.version_id),
            prompt_key=row.prompt_key,
            version_number=row.version_number,
            name=row.name,
            description=row.description,
            template=row.template,
            system_prompt=row.system_prompt,
            default_model=row.default_model,
            default_temperature=row.default_temperature or 0.1,
            default_max_tokens=row.default_max_tokens or 4096,
            response_schema=row.response_schema,
            tags=row.tags or [],
            state=row.state,
            created_by=row.created_by,
            created_at=row.created_at,
            diff_from_previous=row.diff_from_previous,
            previous_version_id=str(row.previous_version_id) if row.previous_version_id else None,
        )


@dataclass
class EvaluationHarness:
    """Evaluation harness for running test cases against prompts."""

    session: AsyncSession
    tenant_id: str

    async def create_dataset(self, dataset: EvaluationDatasetCreate, actor: str) -> EvaluationDatasetResponse:
        """Create an evaluation dataset with test cases."""
        now = datetime.now(timezone.utc)
        dataset_id = uuid.uuid4().hex[:12]

        sql = sa_text("""
            INSERT INTO eval_datasets (dataset_id, tenant_id, name, description,
                prompt_key, test_cases, tags, created_by, created_at, updated_at)
            VALUES (:did, :tid, :name, :desc,
                :prompt_key, :test_cases::jsonb, :tags, :actor, :now, :now)
            RETURNING dataset_id, name, description, prompt_key, test_cases, tags,
                created_by, created_at, updated_at
        """)
        result = await self.session.execute(sql, {
            "did": dataset_id,
            "tid": self.tenant_id,
            "name": dataset.name,
            "desc": dataset.description,
            "prompt_key": dataset.prompt_key,
            "test_cases": json.dumps([tc.model_dump() for tc in dataset.test_cases]),
            "tags": dataset.tags,
            "actor": actor,
            "now": now,
        })
        await self.session.commit()
        row = result.fetchone()
        return EvaluationDatasetResponse(
            dataset_id=str(row.dataset_id),
            name=row.name,
            description=row.description,
            prompt_key=row.prompt_key,
            test_case_count=len(row.test_cases or []),
            tags=row.tags or [],
            created_by=row.created_by,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def list_datasets(self, prompt_key: Optional[str] = None) -> list[EvaluationDatasetResponse]:
        """List evaluation datasets."""
        if prompt_key:
            sql = sa_text("""
                SELECT * FROM eval_datasets
                WHERE tenant_id = :tid AND prompt_key = :key
                ORDER BY created_at DESC
            """)
            result = await self.session.execute(sql, {"tid": self.tenant_id, "key": prompt_key})
        else:
            sql = sa_text("""
                SELECT * FROM eval_datasets
                WHERE tenant_id = :tid
                ORDER BY created_at DESC
            """)
            result = await self.session.execute(sql, {"tid": self.tenant_id})
        return [
            EvaluationDatasetResponse(
                dataset_id=str(r.dataset_id),
                name=r.name,
                description=r.description,
                prompt_key=r.prompt_key,
                test_case_count=len(r.test_cases or []),
                tags=r.tags or [],
                created_by=r.created_by,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in result.fetchall()
        ]

    async def run_evaluation(
        self,
        dataset_id: str,
        prompt_key: str,
        prompt_version: int,
        model: str = "gpt-4o",
    ) -> EvaluationRunResponse:
        """Run an evaluation against a dataset.

        Note: Actual LLM inference is delegated to the AI service.
        This records the run and results structure.
        """
        now = datetime.now(timezone.utc)
        run_id = uuid.uuid4().hex[:12]

        # Get dataset
        ds_sql = sa_text("""
            SELECT * FROM eval_datasets WHERE dataset_id = :did AND tenant_id = :tid
        """)
        ds_result = await self.session.execute(ds_sql, {"did": dataset_id, "tid": self.tenant_id})
        ds_row = ds_result.fetchone()
        if not ds_row:
            raise ValueError(f"Dataset '{dataset_id}' not found")

        test_cases = ds_row.test_cases or []
        total = len(test_cases)

        # Create run record
        run_sql = sa_text("""
            INSERT INTO eval_runs (run_id, dataset_id, tenant_id, prompt_key,
                prompt_version, model, status, total_tests, started_at, created_at)
            VALUES (:rid, :did, :tid, :pkey,
                :pver, :model, 'running', :total, :now, :now)
            RETURNING run_id, dataset_id, prompt_key, prompt_version, model,
                status, total_tests, passed, failed, warnings, pass_rate,
                avg_latency_ms, total_tokens, started_at, completed_at, created_at
        """)
        await self.session.execute(run_sql, {
            "rid": run_id,
            "did": dataset_id,
            "tid": self.tenant_id,
            "pkey": prompt_key,
            "pver": prompt_version,
            "model": model,
            "total": total,
            "now": now,
        })
        await self.session.commit()

        # In a real implementation, this would call the LLM for each test case.
        # For now, return the structure — actual execution is async and would
        # be handled by a background worker.
        return EvaluationRunResponse(
            run_id=run_id,
            dataset_id=dataset_id,
            dataset_name=ds_row.name,
            prompt_key=prompt_key,
            prompt_version=prompt_version,
            model=model,
            status=EvaluationStatus.RUNNING,
            total_tests=total,
            started_at=now,
            created_at=now,
        )


@dataclass
class ModelAuditService:
    """Records and queries the model audit trail."""

    session: AsyncSession
    tenant_id: str

    async def record_event(self, event: ModelAuditEvent) -> str:
        """Record a model audit event."""
        event_id = uuid.uuid4().hex[:12]
        now = datetime.now(timezone.utc)

        sql = sa_text("""
            INSERT INTO model_audit_log (event_id, event_type, prompt_key, prompt_version,
                model, provider, duration_ms, token_count, cost_usd, success,
                error_type, request_id, tenant_id, created_at)
            VALUES (:eid, :etype, :pkey, :pver,
                :model, :provider, :dur, :tokens, :cost, :success,
                :err, :req_id, :tid, :now)
        """)
        await self.session.execute(sql, {
            "eid": event_id,
            "etype": event.event_type,
            "pkey": event.prompt_key,
            "pver": event.prompt_version,
            "model": event.model,
            "provider": event.provider,
            "dur": event.duration_ms,
            "tokens": event.token_count,
            "cost": event.cost_usd,
            "success": event.success,
            "err": event.error_type,
            "req_id": event.request_id,
            "tid": self.tenant_id,
            "now": now,
        })
        await self.session.commit()
        return event_id

    async def get_audit_log(
        self,
        prompt_key: Optional[str] = None,
        event_type: Optional[str] = None,
        success: Optional[bool] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> ModelAuditLogResponse:
        """Get the model audit log with filters."""
        conditions = ["tenant_id = :tid"]
        params: dict = {"tid": self.tenant_id}

        if prompt_key:
            conditions.append("prompt_key = :pkey")
            params["pkey"] = prompt_key
        if event_type:
            conditions.append("event_type = :etype")
            params["etype"] = event_type
        if success is not None:
            conditions.append("success = :success")
            params["success"] = success

        where = " AND ".join(conditions)
        offset = (page - 1) * page_size

        count_sql = sa_text(f"SELECT COUNT(*)::int FROM model_audit_log WHERE {where}")
        count_result = await self.session.execute(count_sql, params)
        total = count_result.scalar() or 0

        sql = sa_text(f"""
            SELECT * FROM model_audit_log
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """)
        params["limit"] = page_size
        params["offset"] = offset
        result = await self.session.execute(sql, params)

        events = [
            ModelAuditEvent(
                event_id=str(r.event_id),
                event_type=r.event_type,
                prompt_key=r.prompt_key,
                prompt_version=r.prompt_version,
                model=r.model,
                provider=r.provider,
                duration_ms=r.duration_ms,
                token_count=r.token_count,
                cost_usd=r.cost_usd,
                success=r.success,
                error_type=r.error_type,
                request_id=r.request_id,
                tenant_id=str(r.tenant_id) if r.tenant_id else None,
                created_at=r.created_at,
            )
            for r in result.fetchall()
        ]

        return ModelAuditLogResponse(events=events, total=total, page=page, page_size=page_size)

    async def get_quality_dashboard(self) -> AIQualityDashboard:
        """Get the AI quality dashboard."""
        # Prompt counts
        prompt_count = await self.session.execute(
            sa_text("""
                SELECT COUNT(DISTINCT prompt_key)::int FROM prompt_templates
            """)
        )
        total_prompts = prompt_count.scalar() or 0

        active_prompt_count = await self.session.execute(
            sa_text("""
                SELECT COUNT(DISTINCT prompt_key)::int FROM prompt_templates WHERE state = 'active'
            """)
        )
        active_prompts = active_prompt_count.scalar() or 0

        # Dataset counts
        ds_count = await self.session.execute(
            sa_text("SELECT COUNT(*)::int FROM eval_datasets WHERE tenant_id = :tid"),
            {"tid": self.tenant_id},
        )
        total_datasets = ds_count.scalar() or 0

        tc_count = await self.session.execute(
            sa_text("""
                SELECT COALESCE(SUM(jsonb_array_length(test_cases)), 0)::int
                FROM eval_datasets WHERE tenant_id = :tid
            """),
            {"tid": self.tenant_id},
        )
        total_test_cases = tc_count.scalar() or 0

        # 24h stats
        stats = await self.session.execute(
            sa_text("""
                SELECT
                    COUNT(*)::int AS total,
                    COUNT(*) FILTER (WHERE success = TRUE)::int AS successful,
                    COALESCE(AVG(duration_ms), 0)::float AS avg_latency,
                    COALESCE(SUM(cost_usd), 0)::float AS total_cost
                FROM model_audit_log
                WHERE tenant_id = :tid AND created_at > NOW() - INTERVAL '24 hours'
            """),
            {"tid": self.tenant_id},
        )
        row = stats.fetchone()
        total_24h = row.total if row else 0
        successful_24h = row.successful if row else 0
        success_rate = (successful_24h / total_24h * 100) if total_24h > 0 else 100.0

        # Model usage
        model_stats = await self.session.execute(
            sa_text("""
                SELECT model, provider,
                    COUNT(*)::int AS inferences,
                    COALESCE(AVG(duration_ms), 0)::float AS avg_latency,
                    COALESCE(SUM(token_count), 0)::int AS tokens,
                    COALESCE(SUM(cost_usd), 0)::float AS cost,
                    COUNT(*) FILTER (WHERE success = FALSE)::int AS errors
                FROM model_audit_log
                WHERE tenant_id = :tid AND created_at > NOW() - INTERVAL '24 hours'
                GROUP BY model, provider
            """),
            {"tid": self.tenant_id},
        )
        model_usage = [
            ModelUsageSummary(
                model=r.model,
                provider=r.provider,
                inferences_24h=r.inferences,
                avg_latency_ms=round(r.avg_latency, 1),
                total_tokens=r.tokens,
                cost_usd=round(r.cost, 4),
                error_rate=round(r.errors / r.inferences * 100, 2) if r.inferences > 0 else 0.0,
            )
            for r in model_stats.fetchall()
        ]

        return AIQualityDashboard(
            total_prompts=total_prompts,
            active_prompts=active_prompts,
            total_evaluation_datasets=total_datasets,
            total_test_cases=total_test_cases,
            total_inferences_24h=total_24h,
            inference_success_rate_24h=round(success_rate, 1),
            avg_latency_ms_24h=round(row.avg_latency, 1) if row else 0.0,
            total_cost_24h=round(row.total_cost, 4) if row else 0.0,
            model_usage=model_usage,
        )

    # ── Cost Summary (from ai_execution_runs) ───────────────────

    async def get_cost_summary(self) -> CostSummaryResponse:
        """Get aggregated AI cost and usage summary from execution runs."""
        # Overall stats
        total = await self.session.execute(
            sa_text("""
                SELECT
                    COALESCE(SUM(cost_usd), 0)::float AS total_cost,
                    COALESCE(SUM(total_tokens), 0)::int AS total_tokens,
                    COUNT(*)::int AS total_requests,
                    COALESCE(AVG(latency_ms), 0)::float AS avg_latency
                FROM ai_execution_runs
                WHERE tenant_id = :tid
            """),
            {"tid": self.tenant_id},
        )
        row = total.fetchone()
        total_cost = row.total_cost if row else 0.0
        total_tokens = row.total_tokens if row else 0
        total_requests = row.total_requests if row else 0
        avg_latency = row.avg_latency if row else 0.0

        avg_cost_per_request = round(total_cost / total_requests, 6) if total_requests > 0 else 0.0
        avg_cost_per_token = round(total_cost / total_tokens, 10) if total_tokens > 0 else 0.0

        # Cost by model
        by_model = await self.session.execute(
            sa_text("""
                SELECT model, provider,
                    COALESCE(SUM(cost_usd), 0)::float AS cost,
                    COUNT(*)::int AS requests,
                    COALESCE(AVG(latency_ms), 0)::float AS avg_lat,
                    COALESCE(MIN(latency_ms), 0)::float AS min_lat,
                    COALESCE(MAX(latency_ms), 0)::float AS max_lat
                FROM ai_execution_runs
                WHERE tenant_id = :tid
                GROUP BY model, provider
                ORDER BY cost DESC
            """),
            {"tid": self.tenant_id},
        )
        rows = by_model.fetchall()

        cost_by_model = []
        requests_by_model = []
        latency_by_model = []

        for r in rows:
            pct = round(r.cost / total_cost * 100, 1) if total_cost > 0 else 0.0
            req_pct = round(r.requests / total_requests * 100, 1) if total_requests > 0 else 0.0
            cost_by_model.append(ModelCostBreakdown(
                model=r.model, provider=r.provider,
                cost=round(r.cost, 4), percentage=pct,
            ))
            requests_by_model.append(ModelRequestBreakdown(
                model=r.model, requests=r.requests, percentage=req_pct,
            ))
            latency_by_model.append(ModelLatencyBreakdown(
                model=r.model,
                avg_latency_ms=round(r.avg_lat, 1),
                min_latency_ms=round(r.min_lat, 1),
                max_latency_ms=round(r.max_lat, 1),
            ))

        return CostSummaryResponse(
            total_cost=round(total_cost, 4),
            total_tokens=total_tokens,
            total_requests=total_requests,
            avg_cost_per_request=avg_cost_per_request,
            avg_cost_per_token=avg_cost_per_token,
            avg_latency_ms=round(avg_latency, 1),
            cost_by_model=cost_by_model,
            requests_by_model=requests_by_model,
            latency_by_model=latency_by_model,
        )

    # ── Safety Summary (from ai_approvals + ai_execution_runs) ──

    async def get_safety_summary(self) -> SafetySummaryResponse:
        """Get aggregated AI safety and approval summary."""
        # Approval stats
        apr = await self.session.execute(
            sa_text("""
                SELECT
                    COUNT(*)::int AS total,
                    COUNT(*) FILTER (WHERE status = 'approved')::int AS approved,
                    COUNT(*) FILTER (WHERE status = 'rejected')::int AS rejected,
                    COUNT(*) FILTER (WHERE status = 'pending')::int AS pending,
                    COALESCE(AVG(confidence), 0)::float AS avg_conf
                FROM ai_approvals
                WHERE tenant_id = :tid
            """),
            {"tid": self.tenant_id},
        )
        arow = apr.fetchone()
        total_approvals = arow.total if arow else 0
        approved_count = arow.approved if arow else 0
        rejected_count = arow.rejected if arow else 0
        pending_count = arow.pending if arow else 0
        avg_confidence = arow.avg_conf if arow else 0.0
        approval_rate = round(approved_count / total_approvals * 100, 1) if total_approvals > 0 else 0.0

        # Execution stats
        exec_stats = await self.session.execute(
            sa_text("""
                SELECT
                    COUNT(*)::int AS total,
                    COUNT(*) FILTER (WHERE status = 'completed')::int AS completed,
                    COUNT(*) FILTER (WHERE status = 'failed')::int AS failed
                FROM ai_execution_runs
                WHERE tenant_id = :tid
            """),
            {"tid": self.tenant_id},
        )
        erow = exec_stats.fetchone()
        total_execs = (erow.total if erow else 0)
        completed_execs = (erow.completed if erow else 0)
        exec_success_rate = round(completed_execs / total_execs * 100, 1) if total_execs > 0 else 0.0

        # Approvals by type
        by_type = await self.session.execute(
            sa_text("""
                SELECT approval_type,
                    COUNT(*)::int AS total,
                    COUNT(*) FILTER (WHERE status = 'approved')::int AS approved,
                    COUNT(*) FILTER (WHERE status = 'rejected')::int AS rejected
                FROM ai_approvals
                WHERE tenant_id = :tid
                GROUP BY approval_type
            """),
            {"tid": self.tenant_id},
        )
        approvals_by_type = [
            ApprovalTypeBreakdown(
                approval_type=r.approval_type,
                count=r.total,
                approved=r.approved,
                rejected=r.rejected,
            )
            for r in by_type.fetchall()
        ]

        return SafetySummaryResponse(
            total_approvals=total_approvals,
            approved_count=approved_count,
            rejected_count=rejected_count,
            pending_count=pending_count,
            approval_rate=approval_rate,
            avg_confidence=round(avg_confidence, 2),
            total_executions=total_execs,
            execution_success_rate=exec_success_rate,
            cost_impact_pct=0.0,
            approvals_by_type=approvals_by_type,
        )
