"""AI Governance schemas — prompt registry, evaluation, regression, model audit."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Enums ───────────────────────────────────────────────────────────


class PromptState(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class EvaluationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TestOutcome(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    ERROR = "error"
    SKIPPED = "skipped"


class ConfidenceCalibrationLevel(str, Enum):
    VERY_HIGH = "very_high"       # >= 0.9
    HIGH = "high"                 # >= 0.7
    MEDIUM = "medium"             # >= 0.5
    LOW = "low"                   # >= 0.3
    VERY_LOW = "very_low"         # < 0.3


class ModelProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE = "azure"
    AWS = "aws"
    GCP = "gcp"
    LOCAL = "local"
    CUSTOM = "custom"


# ── Prompt Registry ─────────────────────────────────────────────────


class PromptTemplateCreate(BaseModel):
    """Create a new prompt template."""
    key: str = Field(..., min_length=1, max_length=200, pattern=r"^[a-z][a-z0-9_]+$")
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    template: str = Field(..., min_length=1)
    system_prompt: Optional[str] = None
    default_model: str = "gpt-4o"
    default_temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    default_max_tokens: int = Field(default=4096, ge=64, le=128000)
    response_schema: Optional[dict[str, Any]] = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PromptTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    template: Optional[str] = None
    system_prompt: Optional[str] = None
    default_model: Optional[str] = None
    default_temperature: Optional[float] = None
    default_max_tokens: Optional[int] = None
    response_schema: Optional[dict[str, Any]] = None
    tags: Optional[list[str]] = None
    state: Optional[PromptState] = None


class PromptVersionResponse(BaseModel):
    """A versioned prompt template."""
    version_id: str
    prompt_key: str
    version_number: int
    name: str
    description: Optional[str] = None
    template: str
    system_prompt: Optional[str] = None
    default_model: str
    default_temperature: float
    default_max_tokens: int
    response_schema: Optional[dict[str, Any]] = None
    tags: list[str] = Field(default_factory=list)
    state: PromptState = PromptState.DRAFT
    created_by: str = ""
    created_at: datetime
    # Diff from previous version
    diff_from_previous: Optional[str] = None
    previous_version_id: Optional[str] = None


class PromptSummary(BaseModel):
    """Summary of a prompt template and its versions."""
    prompt_key: str
    name: str
    description: Optional[str] = None
    active_version: Optional[int] = None
    total_versions: int = 0
    state: PromptState = PromptState.DRAFT
    tags: list[str] = Field(default_factory=list)
    last_used_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


# ── Evaluation Datasets ─────────────────────────────────────────────


class EvaluationDatasetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    prompt_key: str
    test_cases: list[TestCaseInput] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class TestCaseInput(BaseModel):
    """A single test case for evaluating a prompt."""
    input_variables: dict[str, Any] = Field(default_factory=dict)
    expected_output: Optional[str] = None
    expected_finding_count: Optional[int] = None
    expected_risk_score_range: Optional[tuple[float, float]] = None
    expected_clause_types: Optional[list[str]] = None
    expected_severity: Optional[str] = None
    tags: list[str] = Field(default_factory=list)


class TestCaseResult(BaseModel):
    """Result of running a single test case."""
    test_index: int
    outcome: TestOutcome
    actual_output: Optional[str] = None
    expected_output: Optional[str] = None
    score: Optional[float] = None
    latency_ms: Optional[int] = None
    token_count: Optional[int] = None
    error_message: Optional[str] = None
    details: dict[str, Any] = Field(default_factory=dict)


class EvaluationRunResponse(BaseModel):
    """Result of an evaluation run against a dataset."""
    run_id: str
    dataset_id: str
    dataset_name: str = ""
    prompt_key: str
    prompt_version: int
    model: str
    status: EvaluationStatus
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    warnings: int = 0
    pass_rate: float = 0.0
    avg_latency_ms: float = 0.0
    total_tokens: int = 0
    results: list[TestCaseResult] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime


class EvaluationDatasetResponse(BaseModel):
    """An evaluation dataset with test cases."""
    dataset_id: str
    name: str
    description: Optional[str] = None
    prompt_key: str
    test_case_count: int = 0
    tags: list[str] = Field(default_factory=list)
    last_run: Optional[EvaluationRunResponse] = None
    created_by: str = ""
    created_at: datetime
    updated_at: datetime


# ── Regression Testing ──────────────────────────────────────────────


class RegressionSuiteCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    dataset_ids: list[str] = Field(default_factory=list)
    prompt_keys: list[str] = Field(default_factory=list)
    schedule_cron: Optional[str] = None  # cron expression for scheduled runs
    notify_on_failure: bool = False
    notify_channels: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class RegressionRunResponse(BaseModel):
    """Result of a full regression test run."""
    run_id: str
    suite_id: str
    suite_name: str = ""
    status: EvaluationStatus
    evaluation_runs: list[EvaluationRunResponse] = Field(default_factory=list)
    total_tests: int = 0
    total_passed: int = 0
    total_failed: int = 0
    overall_pass_rate: float = 0.0
    regressions_found: int = 0  # tests that passed before but failed now
    improvements_found: int = 0  # tests that failed before but pass now
    score_delta: Optional[float] = None  # change from previous run
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime


class RegressionSuiteResponse(BaseModel):
    suite_id: str
    name: str
    description: Optional[str] = None
    dataset_ids: list[str] = Field(default_factory=list)
    prompt_keys: list[str] = Field(default_factory=list)
    schedule_cron: Optional[str] = None
    is_active: bool = True
    last_run: Optional[RegressionRunResponse] = None
    last_run_at: Optional[datetime] = None
    tags: list[str] = Field(default_factory=list)
    created_by: str = ""
    created_at: datetime
    updated_at: datetime


# ── Confidence Calibration ──────────────────────────────────────────


class ConfidenceCalibrationRecord(BaseModel):
    """A record of confidence calibration for a model/prompt combination."""
    calibration_id: str = ""
    prompt_key: str
    prompt_version: int
    model: str
    sample_size: int = 0
    calibration_curve: list[CalibrationPoint] = Field(default_factory=list)
    avg_confidence: float = 0.0
    avg_accuracy: float = 0.0
    calibration_error: float = 0.0  # lower is better
    last_calibrated_at: Optional[datetime] = None


class CalibrationPoint(BaseModel):
    """A point on the calibration curve."""
    confidence_bin: str  # e.g., '0.0-0.1', '0.9-1.0'
    bin_center: float
    sample_count: int
    accuracy: float  # actual accuracy in this bin
    confidence: float  # average confidence in this bin


class CalibrationRecommendation(BaseModel):
    """Recommendation for confidence calibration."""
    prompt_key: str
    model: str
    current_calibration_error: float = 0.0
    recommended_confidence_offset: float = 0.0
    overconfidence_bins: list[str] = Field(default_factory=list)
    underconfidence_bins: list[str] = Field(default_factory=list)
    recommendation: str = ""


# ── Model Audit Trail ───────────────────────────────────────────────


class ModelAuditEvent(BaseModel):
    """An audit event for AI model usage."""
    event_id: str = ""
    event_type: str  # 'inference', 'prompt_change', 'model_change', 'eval_run', 'error'
    prompt_key: str
    prompt_version: int
    model: str
    provider: str
    duration_ms: Optional[int] = None
    token_count: Optional[int] = None
    cost_usd: Optional[float] = None
    success: bool = True
    error_type: Optional[str] = None
    request_id: Optional[str] = None
    tenant_id: Optional[str] = None
    created_at: datetime


class ModelAuditLogResponse(BaseModel):
    """Paginated model audit log."""
    events: list[ModelAuditEvent] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50


# ── AI Quality Dashboard ────────────────────────────────────────────


class AIQualityDashboard(BaseModel):
    """Executive dashboard for AI quality governance."""
    total_prompts: int = 0
    active_prompts: int = 0
    total_evaluation_datasets: int = 0
    total_test_cases: int = 0
    last_regression_pass_rate: Optional[float] = None
    regressions_found_last_run: int = 0
    avg_calibration_error: Optional[float] = None
    total_inferences_24h: int = 0
    inference_success_rate_24h: float = 0.0
    avg_latency_ms_24h: float = 0.0
    total_cost_24h: float = 0.0
    model_usage: list[ModelUsageSummary] = Field(default_factory=list)
    recent_errors: list[ModelAuditEvent] = Field(default_factory=list)


class ModelUsageSummary(BaseModel):
    """Usage summary for a single model."""
    model: str
    provider: str
    inferences_24h: int = 0
    avg_latency_ms: float = 0.0
    total_tokens: int = 0
    cost_usd: float = 0.0
    error_rate: float = 0.0
