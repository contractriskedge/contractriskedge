"""Cost & Resource Governance schemas — budgets, quotas, accounting, model routing, throttling."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Enums ───────────────────────────────────────────────────────────


class BudgetPeriod(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class BudgetAlertLevel(str, Enum):
    DISABLED = "disabled"
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    HARD_BLOCK = "hard_block"


class ModelTier(str, Enum):
    ECONOMY = "economy"       # gpt-4o-mini, cheapest
    STANDARD = "standard"     # gpt-4o, balanced
    PREMIUM = "premium"       # claude-3.5-sonnet, best quality
    CUSTOM = "custom"         # tenant-specified


class RoutingStrategy(str, Enum):
    QUALITY_FIRST = "quality_first"       # Always best model
    COST_FIRST = "cost_first"             # Always cheapest adequate model
    BALANCED = "balanced"                 # Quality/cost weighted
    TENANT_PREFERRED = "tenant_preferred" # Tenant's explicit model choice


class ResourceType(str, Enum):
    AI_INFERENCE = "ai_inference"
    AI_TOKEN = "ai_token"
    STORAGE_BYTES = "storage_bytes"
    API_REQUEST = "api_request"
    EXPORT = "export"
    WEBHOOK = "webhook"


# ── Token Budgets ───────────────────────────────────────────────────


class TokenBudgetConfig(BaseModel):
    """Per-tenant token budget configuration."""
    budget_id: str = ""
    tenant_id: str
    period: BudgetPeriod = BudgetPeriod.DAILY
    token_limit: int = Field(default=1_000_000, ge=0)
    cost_limit_usd: float = Field(default=10.0, ge=0.0)
    alert_level: BudgetAlertLevel = BudgetAlertLevel.WARNING
    alert_threshold_pct: float = Field(default=80.0, ge=0.0, le=100.0)
    hard_block: bool = False  # if True, reject requests over limit
    notification_channels: list[str] = Field(default_factory=list)
    is_active: bool = True
    created_at: datetime


class TokenBudgetUsage(BaseModel):
    """Current usage against a token budget."""
    budget_id: str
    tenant_id: str
    period: BudgetPeriod
    token_limit: int
    cost_limit_usd: float
    tokens_used: int = 0
    cost_usd: float = 0.0
    usage_pct: float = 0.0
    remaining_tokens: int = 0
    remaining_cost_usd: float = 0.0
    alert_level: BudgetAlertLevel = BudgetAlertLevel.INFO
    is_exceeded: bool = False
    reset_at: datetime


class BudgetAlert(BaseModel):
    """Alert generated when a budget threshold is crossed."""
    alert_id: str = ""
    tenant_id: str
    budget_id: str
    alert_level: BudgetAlertLevel
    metric: str  # 'tokens' or 'cost'
    current_value: float
    threshold_value: float
    message: str = ""
    created_at: datetime
    acknowledged: bool = False


class BudgetConfigCreate(BaseModel):
    period: BudgetPeriod = BudgetPeriod.DAILY
    token_limit: int = Field(default=1_000_000, ge=0)
    cost_limit_usd: float = Field(default=10.0, ge=0.0)
    alert_level: BudgetAlertLevel = BudgetAlertLevel.WARNING
    alert_threshold_pct: float = Field(default=80.0, ge=0.0, le=100.0)
    hard_block: bool = False
    notification_channels: list[str] = Field(default_factory=list)


class BudgetConfigUpdate(BaseModel):
    token_limit: Optional[int] = None
    cost_limit_usd: Optional[float] = None
    alert_level: Optional[BudgetAlertLevel] = None
    alert_threshold_pct: Optional[float] = None
    hard_block: Optional[bool] = None
    notification_channels: Optional[list[str]] = None
    is_active: Optional[bool] = None


# ── Tenant Quotas ───────────────────────────────────────────────────


class TenantQuota(BaseModel):
    """Resource quotas for a tenant."""
    tenant_id: str
    max_users: int = Field(default=10, ge=1)
    max_documents: int = Field(default=1000, ge=1)
    max_daily_inferences: int = Field(default=500, ge=0)
    max_monthly_inferences: int = Field(default=15000, ge=0)
    max_storage_bytes: int = Field(default=1_000_000_000, ge=0)  # 1GB
    max_api_requests_per_min: int = Field(default=100, ge=1)
    max_concurrent_analyses: int = Field(default=5, ge=1)
    max_exports_per_day: int = Field(default=50, ge=0)
    allowed_model_tiers: list[ModelTier] = Field(default_factory=lambda: [ModelTier.ECONOMY, ModelTier.STANDARD])
    allowed_features: list[str] = Field(default_factory=list)


class QuotaUsage(BaseModel):
    """Current usage against tenant quotas."""
    tenant_id: str
    current_users: int = 0
    current_documents: int = 0
    inferences_today: int = 0
    inferences_this_month: int = 0
    storage_bytes: int = 0
    exports_today: int = 0
    concurrent_analyses: int = 0
    quotas: TenantQuota
    any_exceeded: bool = False
    exceeded_quotas: list[str] = Field(default_factory=list)


class QuotaCheckResult(BaseModel):
    """Result of checking a specific operation against quotas."""
    allowed: bool = True
    reason: str = ""
    resource: ResourceType
    current_usage: float = 0.0
    limit: float = 0.0
    remaining: float = 0.0


# ── Inference Accounting ───────────────────────────────────────────


class InferenceRecord(BaseModel):
    """A single inference accounting record."""
    record_id: str = ""
    tenant_id: str
    model: str
    provider: str
    prompt_key: str = ""
    prompt_version: int = 0
    tokens_prompt: int = 0
    tokens_completion: int = 0
    tokens_total: int = 0
    cost_usd: float = 0.0
    duration_ms: int = 0
    cached: bool = False
    routed_by: str = ""  # 'manual', 'auto_economy', 'auto_balanced', 'auto_premium'
    request_id: Optional[str] = None
    created_at: datetime


class InferenceSummary(BaseModel):
    """Summary of inference usage for a period."""
    tenant_id: str
    period_start: datetime
    period_end: datetime
    total_inferences: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    by_model: dict[str, ModelInferenceSummary] = Field(default_factory=dict)
    by_prompt: dict[str, PromptInferenceSummary] = Field(default_factory=dict)
    avg_latency_ms: float = 0.0
    cache_hit_rate: float = 0.0


class ModelInferenceSummary(BaseModel):
    """Inference summary for a single model."""
    model: str
    inferences: int = 0
    tokens: int = 0
    cost_usd: float = 0.0
    avg_latency_ms: float = 0.0


class PromptInferenceSummary(BaseModel):
    """Inference summary for a single prompt."""
    prompt_key: str
    prompt_version: int = 0
    inferences: int = 0
    tokens: int = 0
    cost_usd: float = 0.0
    avg_latency_ms: float = 0.0


# ── Model Routing ───────────────────────────────────────────────────


class ModelCapability(BaseModel):
    """Capabilities of an AI model."""
    supports_json_mode: bool = True
    supports_vision: bool = False
    supports_function_calling: bool = True
    max_context_window: int = 128000
    max_output_tokens: int = 4096
    quality_score: float = Field(default=7.0, ge=0.0, le=10.0)


class ModelRoute(BaseModel):
    """A registered model with routing metadata."""
    model_name: str
    provider: str
    tier: ModelTier
    capabilities: ModelCapability
    cost_per_input_token: float
    cost_per_output_token: float
    is_active: bool = True
    weight: float = Field(default=1.0, ge=0.0, le=1.0)  # for weighted routing


class RoutingDecision(BaseModel):
    """Result of a model routing decision."""
    selected_model: str
    selected_provider: str
    tier: ModelTier
    estimated_cost: float = 0.0
    strategy_used: RoutingStrategy
    alternatives: list[str] = Field(default_factory=list)
    reason: str = ""


class RoutingRule(BaseModel):
    """A rule that determines which model to use for a task."""
    rule_id: str = ""
    prompt_key_pattern: str = "*"  # glob pattern matching prompt keys
    min_quality: float = Field(default=0.0, ge=0.0, le=10.0)
    max_cost_per_request: Optional[float] = None
    preferred_tier: Optional[ModelTier] = None
    preferred_model: Optional[str] = None
    strategy: RoutingStrategy = RoutingStrategy.BALANCED
    priority: int = Field(default=100, ge=1)
    is_active: bool = True


# ── Cache ROI ───────────────────────────────────────────────────────


class CacheROIMetrics(BaseModel):
    """ROI metrics for AI response caching."""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    hit_rate: float = 0.0
    tokens_saved: int = 0
    cost_saved_usd: float = 0.0
    latency_saved_ms: float = 0.0
    period_hours: int = 24


# ── Throttling ──────────────────────────────────────────────────────


class ThrottleRule(BaseModel):
    """A throttling rule for expensive operations."""
    rule_id: str = ""
    resource: ResourceType
    max_count: int
    window_seconds: int
    cost_threshold_usd: Optional[float] = None  # throttle if cost exceeds this
    token_threshold: Optional[int] = None       # throttle if tokens exceed this
    is_active: bool = True


class ThrottleDecision(BaseModel):
    """Decision about whether to allow or throttle an operation."""
    allowed: bool = True
    reason: str = ""
    retry_after_seconds: Optional[int] = None
    current_count: int = 0
    limit: int = 0


# ── Cost Dashboard ──────────────────────────────────────────────────


class CostGovernanceDashboard(BaseModel):
    """Executive dashboard for cost and resource governance."""
    tenant_id: str
    budget_usage: list[TokenBudgetUsage] = Field(default_factory=list)
    quota_usage: Optional[QuotaUsage] = None
    active_alerts: list[BudgetAlert] = Field(default_factory=list)
    inference_summary: Optional[InferenceSummary] = None
    cache_roi: Optional[CacheROIMetrics] = None
    top_cost_drivers: list[CostDriver] = Field(default_factory=list)
    savings_opportunities: list[str] = Field(default_factory=list)


class CostDriver(BaseModel):
    """A cost driver with impact analysis."""
    resource: str  # 'model:gpt-4o', 'prompt:risk_analysis', etc.
    cost_usd: float = 0.0
    percentage: float = 0.0
    trend: str = "stable"  # 'increasing', 'decreasing', 'stable'
    recommendation: str = ""
