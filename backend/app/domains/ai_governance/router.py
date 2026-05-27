"""AI Governance API router — prompt registry, evaluation, regression, model audit."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user, get_tenant_id
from app.kernel.security.auth import UserContext
from app.kernel.security.rbac import require_permission
from app.kernel.security.permissions import Permissions
from app.domains.ai_governance.schemas import (
    PromptState,
    PromptTemplateCreate, PromptTemplateUpdate, PromptVersionResponse, PromptSummary,
    EvaluationDatasetCreate, EvaluationDatasetResponse,
    EvaluationRunResponse,
    RegressionSuiteCreate, RegressionSuiteResponse, RegressionRunResponse,
    ModelAuditEvent, ModelAuditLogResponse,
    AIQualityDashboard,
)
from app.domains.ai_governance.service import (
    PromptRegistryService,
    EvaluationHarness,
    ModelAuditService,
)
from app.domains.ai_governance.quality import (
    HallucinationDetector,
    SemanticRegressionTester,
    ExplanationQualityScorer,
    BenchmarkGateService,
)

router = APIRouter(prefix="/ai-governance", tags=["AI Governance"])


# ── Dependencies ────────────────────────────────────────────────────


async def get_prompt_service(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> PromptRegistryService:
    return PromptRegistryService(session=db, tenant_id=tenant_id)


async def get_eval_service(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> EvaluationHarness:
    return EvaluationHarness(session=db, tenant_id=tenant_id)


async def get_audit_service(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> ModelAuditService:
    return ModelAuditService(session=db, tenant_id=tenant_id)


# ── Prompt Registry ─────────────────────────────────────────────────


@router.post("/prompts", response_model=PromptVersionResponse, status_code=201)
async def create_prompt(
    prompt: PromptTemplateCreate,
    service: PromptRegistryService = Depends(get_prompt_service),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """Create a new prompt template with initial version."""
    return await service.create_prompt(prompt, actor=user.id)


@router.post("/prompts/{prompt_key}/versions", response_model=PromptVersionResponse)
async def create_prompt_version(
    prompt_key: str,
    prompt: PromptTemplateUpdate,
    service: PromptRegistryService = Depends(get_prompt_service),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """Create a new version of an existing prompt template."""
    try:
        return await service.create_version(prompt_key, prompt, actor=user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/prompts", response_model=list[PromptSummary])
async def list_prompts(
    service: PromptRegistryService = Depends(get_prompt_service),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """List all prompt templates with their latest version info."""
    return await service.list_prompts()


@router.get("/prompts/{prompt_key}", response_model=PromptVersionResponse)
async def get_prompt(
    prompt_key: str,
    version: Optional[int] = Query(None, description="Specific version number"),
    service: PromptRegistryService = Depends(get_prompt_service),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """Get a specific version of a prompt template."""
    result = await service.get_prompt(prompt_key, version=version)
    if not result:
        raise HTTPException(status_code=404, detail=f"Prompt '{prompt_key}' not found")
    return result


@router.post("/prompts/{prompt_key}/versions/{version_number}/activate", response_model=PromptVersionResponse)
async def activate_prompt_version(
    prompt_key: str,
    version_number: int,
    service: PromptRegistryService = Depends(get_prompt_service),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """Activate a specific version of a prompt template."""
    try:
        return await service.activate_version(prompt_key, version_number, actor=user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Evaluation Datasets ─────────────────────────────────────────────


@router.post("/datasets", response_model=EvaluationDatasetResponse, status_code=201)
async def create_evaluation_dataset(
    dataset: EvaluationDatasetCreate,
    service: EvaluationHarness = Depends(get_eval_service),
    user: UserContext = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """Create an evaluation dataset with test cases."""
    return await service.create_dataset(dataset, actor=user.id)


@router.get("/datasets", response_model=list[EvaluationDatasetResponse])
async def list_evaluation_datasets(
    prompt_key: Optional[str] = Query(None),
    service: EvaluationHarness = Depends(get_eval_service),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """List evaluation datasets, optionally filtered by prompt key."""
    return await service.list_datasets(prompt_key=prompt_key)


@router.post("/datasets/{dataset_id}/run", response_model=EvaluationRunResponse)
async def run_evaluation(
    dataset_id: str,
    prompt_key: str = Query(...),
    prompt_version: int = Query(...),
    model: str = Query("gpt-4o"),
    service: EvaluationHarness = Depends(get_eval_service),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """Run an evaluation against a dataset."""
    try:
        return await service.run_evaluation(
            dataset_id=dataset_id,
            prompt_key=prompt_key,
            prompt_version=prompt_version,
            model=model,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Model Audit ─────────────────────────────────────────────────────


@router.post("/audit/events", status_code=201)
async def record_audit_event(
    event: ModelAuditEvent,
    service: ModelAuditService = Depends(get_audit_service),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """Record a model audit event (internal)."""
    event_id = await service.record_event(event)
    return {"event_id": event_id}


@router.get("/audit/log", response_model=ModelAuditLogResponse)
async def get_audit_log(
    prompt_key: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    success: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    service: ModelAuditService = Depends(get_audit_service),
    _: None = Depends(require_permission(Permissions.AUDIT_READ)),
):
    """Get the model audit log with optional filters."""
    return await service.get_audit_log(
        prompt_key=prompt_key,
        event_type=event_type,
        success=success,
        page=page,
        page_size=page_size,
    )


# ── Quality Dashboard ───────────────────────────────────────────────


@router.get("/quality-dashboard", response_model=AIQualityDashboard)
async def get_ai_quality_dashboard(
    service: ModelAuditService = Depends(get_audit_service),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """Get the AI quality governance dashboard."""
    return await service.get_quality_dashboard()


# ── Hallucination Detection ─────────────────────────────────────


@router.post("/detect-hallucinations")
async def detect_hallucinations(
    ai_output: str = Query(..., min_length=1, description="AI-generated text to check"),
    source_text: str = Query("", description="Source contract text for grounding"),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """Detect potential hallucinations in AI output by verifying claims against source text."""
    return HallucinationDetector.detect_hallucinations(ai_output, source_text)


# ── Semantic Regression ────────────────────────────────────────


@router.post("/semantic-regression")
async def check_semantic_regression(
    old_output: str = Query(..., min_length=1, description="Previous AI output"),
    new_output: str = Query(..., min_length=1, description="New AI output"),
    expected_output: Optional[str] = Query(None, description="Expected/correct output"),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """Compare old vs new AI outputs to detect semantic regressions."""
    return SemanticRegressionTester.compare_outputs(old_output, new_output, expected_output)


# ── Explanation Quality ────────────────────────────────────────


@router.post("/explanation-quality")
async def score_explanation_quality(
    explanation: str = Query(..., min_length=1, description="AI explanation to score"),
    context: Optional[str] = Query(None, description="Optional context"),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """Score the quality of an AI-generated explanation across multiple dimensions."""
    return ExplanationQualityScorer.score_explanation(explanation, context)


# ── Benchmark Gates ────────────────────────────────────────────


@router.post("/gates/evaluate")
async def evaluate_quality_gates(
    prompt_key: str = Query(...),
    new_version: int = Query(..., ge=1),
    evaluation_run_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.ADMIN_TENANT)),
):
    """Evaluate whether a prompt version passes all quality gates before deployment."""
    gate_service = BenchmarkGateService(session=db, tenant_id=tenant_id)
    return await gate_service.evaluate_gate(
        prompt_key=prompt_key,
        new_version=new_version,
        evaluation_run_id=evaluation_run_id,
    )
