# ContractRiskEdge — Production Hardening Blueprint

## Pre-Implementation Production Readiness Review & Operational Safeguards

**Classification:** Internal Production Readiness Engineering Document  
**Version:** 1.0  
**Status:** Pre-Implementation Hardening Review  
**Target:** Production Pilot Q3 2026

---

## Table of Contents

1. [Reduce Custom Infrastructure](#1-reduce-custom-infrastructure)
2. [Celery Evolution Strategy](#2-celery-evolution-strategy)
3. [Multi-LLM Provider Abstraction](#3-multi-llm-provider-abstraction)
4. [OCR Quality Governance Pipeline](#4-ocr-quality-governance-pipeline)
5. [Search Evolution Preparation](#5-search-evolution-preparation)
6. [pgvector Scale Threshold Governance](#6-pgvector-scale-threshold-governance)
7. [Enterprise UX Hardening Standards](#7-enterprise-ux-hardening-standards)
8. [AI Cost Governance](#8-ai-cost-governance)
9. [Product Validation Governance](#9-product-validation-governance)
10. [Production Hardening Summary](#10-production-hardening-summary)

---

## 1. Reduce Custom Infrastructure

### 1.1 Build vs Buy Decision Matrix

| Capability | Recommendation | Recommended Tool | Build Cost | Buy Cost | Lock-in Risk | Migration Complexity |
|-----------|---------------|-----------------|------------|----------|--------------|---------------------|
| **Auth/OIDC** | BUY | Auth0 | Very High | Low-Medium | Medium | Low (standard OIDC) |
| **Workflow Orchestration** | BUY (V2+) | Temporal | Very High | Medium | Medium | Medium (abstraction layer) |
| **Prompt Management** | BUY | LangSmith/Braintrust | High | Low | Medium | Low (standard API) |
| **Feature Flags** | BUY | Flagsmith/LaunchDarkly | Medium | Low | Low | Low (API-driven) |
| **Notifications** | BUY | Novu/Courier | High | Low | Low | Low (API-driven) |
| **Observability** | BUY | Grafana Cloud | High | Medium | Low | Low (OTel standard) |
| **Error Tracking** | BUY | Sentry | Medium | Low | Low | Low (SDK) |
| **Analytics/Product** | BUY | PostHog | High | Low | Medium | Low (SDK) |
| **AI Tracing** | BUY | LangSmith/Helicone | High | Low | Medium | Low (SDK wrapper) |
| **Rate Limiting** | BUILD | Redis-based | Low | N/A | None | N/A |
| **Audit Logging** | BUILD | PostgreSQL | Low | N/A | None | N/A |

### 1.2 MUST Build Internally

```
1. Domain business logic (contracts, clauses, workflows, compliance)
   └── Core IP, cannot outsource

2. AI analysis pipeline orchestration
   └── Tightly coupled to domain models

3. Search + retrieval engine
   └── pgvector integration, domain-specific ranking

4. Audit logging
   └── Compliance requirements, immutable storage

5. Multi-tenant data isolation
   └── RLS, tenant context, data segregation

6. API Gateway + middleware
   └── Rate limiting, auth enforcement, request routing
```

### 1.3 SHOULD Buy (V1)

```
1. Auth0
   └── OIDC, MFA, SSO, user management, social login
   └── Cost: ~$2/user/month (enterprise tier)
   └── Migration path: standard OIDC — any OIDC provider works
   └── Fallback: self-hosted Ory Hydra or Keycloak

2. Sentry
   └── Error tracking, performance monitoring, release tracking
   └── Cost: ~$26/month (team tier)
   └── Self-hosted option available

3. Grafana Cloud (or self-hosted)
   └── Metrics (Prometheus), logs (Loki), traces (Tempo)
   └── Cost: free tier up to 10k series / 50GB logs
   └── Self-hosted: docker compose (free)

4. PostHog (self-hosted or cloud)
   └── Product analytics, feature flags, session recording
   └── Cost: free self-hosted, ~$0.003/event cloud
   └── Self-hosted: single docker compose service
```

### 1.4 SHOULD Buy (V2+)

```
1. Temporal (cloud or self-hosted)
   └── Replaces Celery for complex orchestration
   └── When: workflow complexity exceeds Celery's reliability guarantees
   └── Migration: abstraction layer (see Section 2)

2. LangSmith or Braintrust
   └── Prompt versioning, evaluation, tracing
   └── When: > 5 prompts in production, A/B testing needed
   └── Cost: ~$0.10/trace

3. Novu
   └── Notification infrastructure (in-app, email, SMS, push)
   └── When: notification volume exceeds simple in-app pattern
   └── Cost: free tier up to 30k events/month
```

### 1.5 Implementation Guidance

```python
# ── Auth0 Integration (V1) ────────────────────────────────────────

# app/kernel/security/auth.py
from authlib.integrations.starlette_client import OAuth

oauth = OAuth()
oauth.register(
    name='auth0',
    server_metadata_url=f'https://{settings.AUTH0_DOMAIN}/.well-known/openid-configuration',
    client_id=settings.AUTH0_CLIENT_ID,
    client_secret=settings.AUTH0_CLIENT_SECRET,
    client_kwargs={'scope': 'openid profile email'},
)

async def verify_token(token: str) -> UserContext:
    """Verify JWT from Auth0."""
    jwks = await get_jwks(settings.AUTH0_DOMAIN)
    payload = jwt.decode(
        token, jwks, algorithms=['RS256'],
        audience=settings.AUTH0_AUDIENCE,
        issuer=f'https://{settings.AUTH0_DOMAIN}/',
    )
    return UserContext(
        id=payload['sub'],
        email=payload.get('email'),
        tenant_id=payload.get(f'{settings.AUTH0_AUDIENCE}/tenant_id'),
        role=payload.get(f'{settings.AUTH0_AUDIENCE}/role', 'viewer'),
    )

# ── Sentry Integration ─────────────────────────────────────────────

# app/main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    environment=settings.ENVIRONMENT,
    traces_sample_rate=0.25,  # Sample 25% of transactions
    profiles_sample_rate=0.10,
    integrations=[
        FastApiIntegration(),
        SqlalchemyIntegration(),
    ],
)

# ── PostHog Feature Flags ──────────────────────────────────────────

# app/kernel/features.py
import posthog

posthog.project_api_key = settings.POSTHOG_API_KEY
posthog.host = settings.POSTHOG_HOST

async def is_feature_enabled(
    flag_key: str, user_id: str, tenant_id: str,
    default: bool = False,
) -> bool:
    """Evaluate feature flag with tenant context."""
    return posthog.feature_enabled(
        flag_key,
        user_id,
        groups={'tenant': tenant_id},
        person_properties={'tenant_id': tenant_id},
    )
```

---

## 2. Celery Evolution Strategy

### 2.1 Problem

Celery is reliable for simple task queues but becomes problematic for:
- Complex multi-step workflows (state management)
- Long-running AI tasks (heartbeat, cancellation)
- SLA-guaranteed execution (retry visibility)
- Workflow observability (step-level tracing)

### 2.2 Strategy: Keep Celery for V1, Abstract for Migration

```
V1 (Months 1-6): Celery
  └── Simple task queue pattern
  └── Single queue per workload type
  └── Retry with exponential backoff
  └── Basic task monitoring (Flower)

V2 (Months 6-12): Temporal (or Hatchet/Prefect)
  └── Complex workflow orchestration
  └── Long-running AI workflows
  └── SLA-guaranteed execution
  └── Workflow-level observability
  └── Saga pattern support

Migration: Abstraction layer prevents framework lock-in
```

### 2.3 Worker Abstraction Interface

```python
# app/kernel/workers/interface.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Awaitable

@dataclass
class TaskDefinition:
    """Abstract task definition — framework agnostic."""
    name: str
    fn: Callable
    queue: str
    max_retries: int = 3
    retry_delay_seconds: int = 60
    timeout_seconds: int = 300
    sla_seconds: int | None = None

class TaskExecutor(ABC):
    """Abstract task execution interface.
    
    Implementations:
    - CeleryTaskExecutor (V1)
    - TemporalTaskExecutor (V2+)
    """

    @abstractmethod
    async def execute_async(self, task: TaskDefinition, **kwargs) -> str:
        """Submit task for async execution. Returns task ID."""
        ...

    @abstractmethod
    async def get_status(self, task_id: str) -> str:
        ...

    @abstractmethod
    async def cancel(self, task_id: str) -> bool:
        ...

    @abstractmethod
    async def get_result(self, task_id: str, timeout: int = 30) -> Any:
        ...

# ── Celery Implementation (V1) ─────────────────────────────────────

# app/kernel/workers/celery_executor.py
from celery import Celery

celery_app = Celery('contractrisk', broker=settings.CELERY_BROKER_URL)

class CeleryTaskExecutor(TaskExecutor):
    def __init__(self):
        self.app = celery_app

    def execute_async(self, task: TaskDefinition, **kwargs) -> str:
        # Register task dynamically
        celery_task = self.app.task(
            bind=True,
            name=task.name,
            max_retries=task.max_retries,
            acks_late=True,
        )(task.fn)
        result = celery_task.delay(**kwargs)
        return result.id

    def get_status(self, task_id: str) -> str:
        result = self.app.AsyncResult(task_id)
        return result.status

# ── Usage in domain services ───────────────────────────────────────

# domains/contracts/service.py
from app.kernel.workers.interface import TaskDefinition, TaskExecutor

class ContractService:
    def __init__(self, executor: TaskExecutor):
        self.executor = executor

    async def create(self, data: ContractCreate) -> Contract:
        contract = await self.repository.create(...)
        
        # Submit ingestion task — framework agnostic
        task_id = await self.executor.execute_async(
            TaskDefinition(
                name='ingestion.process_document',
                fn=process_document,
                queue='ingestion',
                max_retries=3,
                timeout_seconds=300,
            ),
            contract_id=contract.id,
            tenant_id=self.tenant_id,
        )
        
        return contract
```

### 2.4 Migration Path: Celery → Temporal

```
Phase 1 (V1): Celery
  └── All background tasks use TaskExecutor interface
  └── Business logic is PURE — no Celery imports in service layer
  └── Celery only in kernel/workers/celery_executor.py

Phase 2 (V2): Dual Run
  └── New workflows use Temporal
  └── Existing Celery tasks continue running
  └── TemporalTaskExecutor implements TaskExecutor interface
  └── Gradual migration per workflow type

Phase 3 (V2+): Temporal Primary
  └── All workflows migrated to Temporal
  └── Celery decommissioned
  └── Simple tasks remain as Temporal Activities
```

### 2.5 Anti-Coupling Rules

```
1. Service layer NEVER imports Celery directly
2. Service layer NEVER uses @celery_app.task decorator
3. All task definitions go through TaskExecutor interface
4. Business logic is in PURE functions (no framework dependencies)
5. Worker files only contain: task definition + executor wiring
6. Retry logic is configured in TaskDefinition, not in business code
7. Task routing (queue names) is configured in TaskDefinition
```

---

## 3. Multi-LLM Provider Abstraction

### 3.1 Provider Abstraction Interface

```python
# app/kernel/llm/interface.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

@dataclass
class LLMRequest:
    prompt: str
    system_prompt: str | None = None
    model: str | None = None
    temperature: float = 0.1
    max_tokens: int = 4096
    response_format: dict | None = None  # {"type": "json_object"}
    timeout_seconds: int = 60

@dataclass
class LLMResponse:
    content: str
    model: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: int
    cost_usd: float

class LLMProvider(ABC):
    """Abstract LLM provider interface.
    
    Implementations:
    - OpenAIProvider
    - AnthropicProvider
    - AzureOpenAIProvider
    - LocalProvider (vLLM/Ollama)
    """

    @abstractmethod
    async def complete(self, request: LLMRequest) -> LLMResponse:
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @property
    @abstractmethod
    def supported_models(self) -> list[str]:
        ...

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Health check for this provider."""
        ...

# ── OpenAI Implementation ──────────────────────────────────────────

# app/kernel/llm/providers/openai.py
import openai

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, organization: str | None = None):
        self.client = openai.AsyncOpenAI(api_key=api_key, organization=organization)
        self._models = ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo']

    @property
    def provider_name(self) -> str: return 'openai'

    @property
    def supported_models(self) -> list[str]: return self._models

    @property
    def is_available(self) -> bool:
        try:
            self.client.models.list()
            return True
        except Exception:
            return False

    async def complete(self, request: LLMRequest) -> LLMResponse:
        import time
        start = time.time()
        
        messages = []
        if request.system_prompt:
            messages.append({'role': 'system', 'content': request.system_prompt})
        messages.append({'role': 'user', 'content': request.prompt})
        
        kwargs = {
            'model': request.model or 'gpt-4o',
            'messages': messages,
            'temperature': request.temperature,
            'max_tokens': request.max_tokens,
        }
        if request.response_format:
            kwargs['response_format'] = request.response_format
        
        response = await self.client.chat.completions.create(**kwargs)
        latency_ms = int((time.time() - start) * 1000)
        usage = response.usage
        
        return LLMResponse(
            content=response.choices[0].message.content,
            model=response.model,
            provider=self.provider_name,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
            latency_ms=latency_ms,
            cost_usd=self._estimate_cost(request.model, usage.prompt_tokens, usage.completion_tokens),
        )

    def _estimate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        rates = {
            'gpt-4o':          {'input': 0.0000025, 'output': 0.00001},
            'gpt-4o-mini':     {'input': 0.00000015, 'output': 0.0000006},
            'gpt-4-turbo':     {'input': 0.00001, 'output': 0.00003},
        }
        rate = rates.get(model, rates['gpt-4o'])
        return (prompt_tokens * rate['input']) + (completion_tokens * rate['output'])

# ── Anthropic Implementation ───────────────────────────────────────

# app/kernel/llm/providers/anthropic.py
import anthropic

class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self._models = ['claude-3-opus-20240229', 'claude-3-sonnet-20240229', 'claude-3-haiku-20240307']

    @property
    def provider_name(self) -> str: return 'anthropic'

    async def complete(self, request: LLMRequest) -> LLMResponse:
        import time
        start = time.time()
        
        response = await self.client.messages.create(
            model=request.model or 'claude-3-sonnet-20240229',
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            system=request.system_prompt or '',
            messages=[{'role': 'user', 'content': request.prompt}],
        )
        latency_ms = int((time.time() - start) * 1000)
        
        return LLMResponse(
            content=response.content[0].text,
            model=response.model,
            provider=self.provider_name,
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            latency_ms=latency_ms,
            cost_usd=self._estimate_cost(request.model, response.usage.input_tokens, response.usage.output_tokens),
        )
```

### 3.2 Model Router with Fallback

```python
# app/kernel/llm/router.py

import random
from dataclasses import dataclass

@dataclass
class RoutingStrategy:
    """Defines how to route requests across providers."""
    primary_provider: str
    fallback_providers: list[str]  # Ordered by preference
    cost_optimized: bool = False
    latency_optimized: bool = False

class ModelRouter:
    """Routes LLM requests across providers with fallback and cost awareness."""

    def __init__(self):
        self._providers: dict[str, LLMProvider] = {}
        self._strategies: dict[str, RoutingStrategy] = {
            'risk_analysis': RoutingStrategy(
                primary_provider='openai',
                fallback_providers=['anthropic'],
                cost_optimized=False,
            ),
            'clause_classification': RoutingStrategy(
                primary_provider='openai',
                fallback_providers=['anthropic'],
                cost_optimized=True,
            ),
            'embedding': RoutingStrategy(
                primary_provider='openai',
                fallback_providers=[],
                cost_optimized=True,
            ),
        }

    def register_provider(self, provider: LLMProvider):
        self._providers[provider.provider_name] = provider

    async def complete(
        self, request: LLMRequest, workflow_type: str = 'risk_analysis',
    ) -> LLMResponse:
        strategy = self._strategies.get(workflow_type, self._strategies['risk_analysis'])
        
        # Try providers in order
        providers_to_try = [strategy.primary_provider] + strategy.fallback_providers
        
        last_error = None
        for provider_name in providers_to_try:
            provider = self._providers.get(provider_name)
            if not provider or not provider.is_available:
                continue
            
            try:
                return await provider.complete(request)
            except Exception as exc:
                last_error = exc
                logger.warning(f"Provider {provider_name} failed: {exc}")
                continue
        
        raise AllProvidersFailedError(f"All providers failed. Last error: {last_error}")

    async def get_cheapest_completion(
        self, request: LLMRequest, min_quality: float = 0.8,
    ) -> LLMResponse:
        """Cost-optimized: try cheapest model first, fall back to better models."""
        model_tiers = [
            ('gpt-4o-mini', 0.7),    # Cheap, lower quality
            ('gpt-4o', 0.9),          # Medium cost, high quality
            ('claude-3-opus', 0.95),  # Expensive, highest quality
        ]
        
        for model, quality in model_tiers:
            if quality < min_quality:
                continue
            request.model = model
            try:
                return await self.complete(request)
            except Exception:
                continue
        
        raise AllProvidersFailedError("All cost-optimized models failed")
```

### 3.3 Provider Health Scoring

```sql
-- ── Provider Health Tracking ──────────────────────────────────────

CREATE TABLE llm_provider_health (
    health_id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider            TEXT NOT NULL,
    model               TEXT NOT NULL,
    period_start        TIMESTAMPTZ NOT NULL,
    period_end          TIMESTAMPTZ NOT NULL,
    total_requests      INTEGER NOT NULL DEFAULT 0,
    success_count       INTEGER NOT NULL DEFAULT 0,
    error_count         INTEGER NOT NULL DEFAULT 0,
    p50_latency_ms      INTEGER,
    p95_latency_ms      INTEGER,
    p99_latency_ms      INTEGER,
    avg_tokens_per_request INTEGER,
    error_rate          REAL GENERATED ALWAYS AS (
        CASE WHEN total_requests > 0 
        THEN error_count::REAL / total_requests 
        ELSE 0 END
    ) STORED,
    availability_score  REAL GENERATED ALWAYS AS (
        CASE WHEN total_requests > 0 
        THEN success_count::REAL / total_requests 
        ELSE 0 END
    ) STORED,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_provider_health_lookup
    ON llm_provider_health(provider, model, period_start DESC);
```

---

## 4. OCR Quality Governance Pipeline

### 4.1 OCR Quality Scoring

```python
# domains/ingestion/ocr/quality.py

@dataclass
class OCRQualityScore:
    overall_score: float       # 0-1
    text_confidence: float     # Average character confidence
    skew_detected: float       # Degrees of skew (0 = perfect)
    blank_page_ratio: float    # % of page that is blank
    garbage_text_ratio: float  # % of text that is unreadable
    table_detection_score: float  # 0-1
    has_scanned_signature: bool

class OCRQualityGate:
    """Quality gate for OCR output. Determines if extraction is acceptable."""

    MIN_CONFIDENCE = 0.7
    MAX_SKEW_DEGREES = 5.0
    MAX_BLANK_RATIO = 0.3
    MAX_GARBAGE_RATIO = 0.15

    async def evaluate(self, page_text: str, page_image: bytes, ocr_metadata: dict) -> OCRQualityScore:
        score = OCRQualityScore(
            text_confidence=self._calculate_text_confidence(ocr_metadata),
            skew_detected=self._detect_skew(page_image),
            blank_page_ratio=self._calculate_blank_ratio(page_text),
            garbage_text_ratio=self._calculate_garbage_ratio(page_text),
            table_detection_score=self._detect_tables(page_image),
            has_scanned_signature=self._detect_signature(page_image),
            overall_score=0.0,
        )
        
        # Composite score
        score.overall_score = (
            score.text_confidence * 0.4 +
            (1 - score.blank_page_ratio) * 0.2 +
            (1 - score.garbage_text_ratio) * 0.2 +
            score.table_detection_score * 0.1 +
            (1 - min(score.skew_detected / 10, 1)) * 0.1
        )
        
        return score

    async def is_passable(self, score: OCRQualityScore) -> tuple[bool, str | None]:
        """Determine if OCR quality is acceptable or needs remediation."""
        if score.text_confidence < self.MIN_CONFIDENCE:
            return False, f"Low text confidence: {score.text_confidence:.2f}"
        if score.skew_detected > self.MAX_SKEW_DEGREES:
            return False, f"Excessive skew: {score.skew_detected:.1f} degrees"
        if score.blank_page_ratio > self.MAX_BLANK_RATIO:
            return False, f"High blank ratio: {score.blank_page_ratio:.2f}"
        if score.garbage_text_ratio > self.MAX_GARBAGE_RATIO:
            return False, f"High garbage text: {score.garbage_text_ratio:.2f}"
        return True, None

    def _calculate_text_confidence(self, metadata: dict) -> float:
        """Average confidence from OCR engine."""
        confidences = metadata.get('char_confidences', [])
        if not confidences:
            return 0.8  # Default for digital PDFs (no OCR needed)
        return sum(confidences) / len(confidences)

    def _calculate_blank_ratio(self, text: str) -> float:
        """Ratio of whitespace/empty to total content."""
        if not text:
            return 1.0
        non_blank = len([c for c in text if not c.isspace()])
        return 1 - (non_blank / len(text))

    def _calculate_garbage_ratio(self, text: str) -> float:
        """Detect OCR garbage: repeated special chars, random Unicode."""
        import re
        garbage_patterns = [
            r'[^\w\s\.\,\;\:\!\?\(\)\[\]\{\}\-\'\"]',  # Unusual characters
            r'(.)\1{10,}',  # Repeated characters
            r'\w{50,}',     # Overly long "words"
        ]
        garbage_chars = 0
        for pattern in garbage_patterns:
            matches = re.findall(pattern, text)
            garbage_chars += sum(len(m) for m in matches)
        return garbage_chars / max(len(text), 1)
```

### 4.2 OCR Decision Tree

```
                    ┌──────────────────┐
                    │   PDF Uploaded   │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  Extract text    │
                    │  (PyMuPDF)       │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  Quality check   │
                    │  score > 0.7?    │
                    └────────┬─────────┘
                         YES │    NO
                    ┌────────┴──────────┐
                    │                   │
                    ▼                   ▼
            ┌──────────────┐   ┌──────────────┐
            │  Use directly │   │  Run OCR     │
            │  (digital)    │   │  (Tesseract) │
            └──────┬───────┘   └──────┬───────┘
                   │                  │
                   │           ┌──────▼───────┐
                   │           │  Quality     │
                   │           │  check > 0.7?│
                   │           └──────┬───────┘
                   │              YES │    NO
                   │         ┌────────┴──────────┐
                   │         │                   │
                   │         ▼                   ▼
                   │  ┌──────────────┐  ┌──────────────────┐
                   │  │ Use OCR text │  │ Run OCRmyPDF     │
                   │  │              │  │ (deskew + enhance)│
                   │  └──────┬───────┘  └──────┬───────────┘
                   │         │                 │
                   │         │          ┌──────▼───────────┐
                   │         │          │  Quality check   │
                   │         │          │  score > 0.7?    │
                   │         │          └──────┬───────────┘
                   │         │             YES │    NO
                   │         │        ┌────────┴──────────┐
                   │         │        │                   │
                   │         │        ▼                   ▼
                   │         │  ┌──────────────┐  ┌──────────────────┐
                   │         │  │ Use enhanced │  │ Flag for human   │
                   │         │  │ OCR text     │  │ review (low qual)│
                   │         │  └──────────────┘  └──────────────────┘
                   │         │
                   └─────────┘
```

### 4.3 OCR Telemetry

```sql
-- ── OCR Quality Metrics ───────────────────────────────────────────

CREATE TABLE ocr_quality_metrics (
    metric_id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contract_id         UUID NOT NULL,
    tenant_id           UUID NOT NULL,
    extraction_method   TEXT NOT NULL,   -- 'pymupdf', 'tesseract', 'ocrmypdf'
    overall_score       REAL NOT NULL,
    text_confidence     REAL,
    blank_ratio         REAL,
    garbage_ratio       REAL,
    page_count          INTEGER NOT NULL,
    pages_below_threshold INTEGER NOT NULL DEFAULT 0,
    processing_time_ms  INTEGER NOT NULL,
    retry_count         INTEGER NOT NULL DEFAULT 0,
    had_fallback        BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ocr_quality_tenant
    ON ocr_quality_metrics(tenant_id, created_at DESC);
```

---

## 5. Search Evolution Preparation

### 5.1 Retrieval Abstraction Layer

```python
# domains/search/engine/interface.py

from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class RetrievalRequest:
    query: str
    tenant_id: str
    filters: dict | None = None
    top_k: int = 20
    page: int = 1
    page_size: int = 20

@dataclass
class RetrievedChunk:
    chunk_id: str
    contract_id: str
    text: str
    score: float
    metadata: dict

class RetrievalEngine(ABC):
    """Abstract retrieval interface.
    
    V1: HybridSearchEngine (BM25 + pgvector)
    V2: + Reranker
    V3: + Query Rewriter + Graph Enhancement
    """

    @abstractmethod
    async def search(self, request: RetrievalRequest) -> tuple[list[RetrievedChunk], int]:
        ...

# ── Future Reranker Integration Point ──────────────────────────────

class Reranker(ABC):
    """Abstract reranker interface.
    
    V1: No-op (identity)
    V2: Cross-encoder reranker
    """

    @abstractmethod
    async def rerank(self, query: str, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        ...

# ── Future Query Rewriter Integration Point ────────────────────────

class QueryRewriter(ABC):
    """Abstract query rewriting interface.
    
    V1: No-op (identity)
    V2: LLM-based query expansion
    """

    @abstractmethod
    async def rewrite(self, query: str, context: dict) -> str:
        ...
```

### 5.2 Search Quality Evaluation

```python
# domains/search/evaluation/quality.py

@dataclass
class SearchQualityMetrics:
    ndcg_at_10: float       # Normalized Discounted Cumulative Gain
    mrr: float              # Mean Reciprocal Rank
    precision_at_10: float
    recall_at_10: float
    average_click_rank: float  # Average rank of clicked results
    zero_result_rate: float    # % of queries with 0 results

class SearchEvaluator:
    """Evaluate search quality against human-judged relevance datasets."""

    def __init__(self):
        self.datasets: dict[str, list[SearchExample]] = {}

    def load_dataset(self, name: str, examples: list[SearchExample]):
        self.datasets[name] = examples

    async def evaluate(self, engine: RetrievalEngine, dataset_name: str) -> SearchQualityMetrics:
        examples = self.datasets.get(dataset_name, [])
        ndcg_scores = []
        rr_scores = []
        precision_scores = []
        recall_scores = []
        zero_result_count = 0

        for example in examples:
            results, total = await engine.search(RetrievalRequest(
                query=example.query,
                tenant_id='eval_tenant',
            ))

            if total == 0:
                zero_result_count += 1
                continue

            # Calculate metrics
            relevant = set(example.relevant_chunk_ids)
            retrieved = [r.chunk_id for r in results[:10]]

            ndcg_scores.append(self._ndcg(retrieved, relevant, 10))
            rr_scores.append(self._reciprocal_rank(retrieved, relevant))
            precision_scores.append(self._precision(retrieved, relevant))
            recall_scores.append(self._recall(retrieved, relevant, example.all_relevant_ids))

        return SearchQualityMetrics(
            ndcg_at_10=sum(ndcg_scores) / max(len(ndcg_scores), 1),
            mrr=sum(rr_scores) / max(len(rr_scores), 1),
            precision_at_10=sum(precision_scores) / max(len(precision_scores), 1),
            recall_at_10=sum(recall_scores) / max(len(recall_scores), 1),
            average_click_rank=0.0,  # Requires production click data
            zero_result_rate=zero_result_count / max(len(examples), 1),
        )
```

---

## 6. pgvector Scale Threshold Governance

### 6.1 Scaling Thresholds

| Threshold | Chunks | Storage (1536d) | Index Build | Query p50 | Query p95 | Action |
|-----------|--------|-----------------|-------------|-----------|-----------|--------|
| **Green** | < 10M | < 60 GB | < 1 hour | < 50ms | < 200ms | No action needed |
| **Yellow** | 10-50M | 60-300 GB | 1-4 hours | 50-100ms | 200-500ms | Monitor, optimize ivfflat lists |
| **Orange** | 50-100M | 300-600 GB | 4-8 hours | 100-200ms | 500-1000ms | Plan migration, test external vector DB |
| **Red** | 100-250M | 600 GB-1.5 TB | 8-24 hours | 200-500ms | 1-3s | Migrate to dedicated vector DB |
| **Critical** | > 250M | > 1.5 TB | > 24 hours | > 500ms | > 3s | External vector DB required |

### 6.2 Operational Warning Signals

```sql
-- ── Vector Index Health Monitoring ────────────────────────────────

CREATE MATERIALIZED VIEW vector_index_health AS
SELECT
    schemaname,
    tablename,
    indexname,
    pg_relation_size(indexrelid) AS index_size_bytes,
    pg_stat_get_numscans(indexrelid) AS scans_count,
    pg_stat_get_tuples_fetched(indexrelid) AS tuples_fetched,
    pg_stat_get_tuples_returned(indexrelid) AS tuples_returned,
    NOW() AS measured_at
FROM pg_stat_user_indexes
WHERE indexname LIKE '%embedding%';

-- ── Alert when: ───────────────────────────────────────────────────
-- 1. Index size > 100 GB (per partition)
-- 2. Query latency p95 > 500ms
-- 3. Index build time > 4 hours
-- 4. Scan count dropping (queries using seq scan instead of index)
-- 5. Tuple fetch ratio < 0.1 (index not selective enough)
```

### 6.3 ivfflat Tuning Guide

```python
def calculate_ivfflat_lists(n_rows: int) -> int:
    """Optimal ivfflat lists parameter based on table size."""
    if n_rows < 100_000:
        return 100
    elif n_rows < 1_000_000:
        return max(100, int(n_rows ** 0.5))
    else:
        return min(4000, int(n_rows ** 0.5))

def calculate_probes(lists: int, target_recall: float = 0.99) -> int:
    """Optimal probes parameter for target recall."""
    # More probes = better recall, slower queries
    if target_recall >= 0.99:
        return min(lists // 10, 100)
    elif target_recall >= 0.95:
        return min(lists // 20, 50)
    else:
        return min(lists // 40, 10)
```

### 6.4 Migration Readiness: pgvector → External Vector DB

```
TRIGGER CONDITIONS (any 2 of 3):
  1. Chunks > 100M
  2. Index build time > 8 hours
  3. Query p95 > 1s

MIGRATION PLAN:
  Phase 1: Dual-write (2 weeks)
    └── Write to both pgvector and Qdrant/Milvus
    └── Compare query results (recall@10 parity)
    └── Monitor latency and cost

  Phase 2: Gradual read migration (2 weeks)
    └── Route 10% of queries to new vector DB
    └── Increase by 10% daily
    └── Monitor recall and latency

  Phase 3: Full cutover (1 week)
    └── All queries use new vector DB
    └── pgvector kept as warm standby
    └── Remove pgvector index after confirmation

  ROLLBACK:
    └── Revert DNS/routing to pgvector
    └── Dual-write still active during migration
    └── Full rollback in < 1 hour
```

---

## 7. Enterprise UX Hardening Standards

### 7.1 Skeleton Loading Standards

```typescript
// components/ui/skeleton.tsx — Standardized loading states

// Rule: EVERY data-fetching component has 3 states:
//   1. Loading (skeleton)
//   2. Error (error boundary + retry)
//   3. Empty (empty state with CTA)

// ── Table Skeleton ────────────────────────────────────────────────
export function TableSkeleton({ rows = 5, columns = 4 }: { rows?: number; columns?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-4">
          {Array.from({ length: columns }).map((_, j) => (
            <div key={j} className="h-4 bg-gray-200 rounded animate-pulse flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
}

// ── KPI Card Skeleton ─────────────────────────────────────────────
export function KpiCardSkeleton() {
  return (
    <div className="rounded-xl border p-4 space-y-3">
      <div className="h-3 w-24 bg-gray-200 rounded animate-pulse" />
      <div className="h-8 w-16 bg-gray-200 rounded animate-pulse" />
      <div className="h-2 w-32 bg-gray-200 rounded animate-pulse" />
    </div>
  );
}

// ── Detail Panel Skeleton ─────────────────────────────────────────
export function DetailPanelSkeleton() {
  return (
    <div className="space-y-4 p-6">
      <div className="h-6 w-48 bg-gray-200 rounded animate-pulse" />
      <div className="space-y-2">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="flex justify-between">
            <div className="h-4 w-24 bg-gray-200 rounded animate-pulse" />
            <div className="h-4 w-32 bg-gray-200 rounded animate-pulse" />
          </div>
        ))}
      </div>
    </div>
  );
}
```

### 7.2 Virtualized Tables

```typescript
// Rule: ANY table with > 100 rows MUST use virtualization

import { useVirtualizer } from '@tanstack/react-virtual';

export function VirtualizedTable({ data, columns, onSelect }: TableProps) {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: data.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 48,  // 48px per row
    overscan: 10,            // Render 10 extra rows above/below
  });

  return (
    <div ref={parentRef} className="overflow-auto" style={{ height: '600px' }}>
      <div style={{ height: `${virtualizer.getTotalSize()}px` }}>
        <table className="w-full">
          <thead className="sticky top-0 bg-white z-10">
            <tr>
              {columns.map(col => <th key={col.key}>{col.label}</th>)}
            </tr>
          </thead>
          <tbody>
            {virtualizer.getVirtualItems().map((virtualRow) => {
              const item = data[virtualRow.index];
              return (
                <tr
                  key={item.id}
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: `${virtualRow.size}px`,
                    transform: `translateY(${virtualRow.start}px)`,
                  }}
                >
                  {columns.map(col => <td key={col.key}>{item[col.key]}</td>)}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

### 7.3 Role-Aware Rendering

```typescript
// lib/hooks/use-permissions.ts

import { useAuthStore } from '@/stores/auth-store';

type Permission = 'contract:read' | 'contract:write' | 'contract:delete'
  | 'workflow:approve' | 'admin:users' | 'audit:view';

const ROLE_PERMISSIONS: Record<string, Permission[]> = {
  admin: ['contract:read', 'contract:write', 'contract:delete', 'workflow:approve', 'admin:users', 'audit:view'],
  analyst: ['contract:read', 'contract:write', 'workflow:approve'],
  viewer: ['contract:read'],
};

export function usePermission() {
  const user = useAuthStore(s => s.user);

  const can = (permission: Permission): boolean => {
    if (!user) return false;
    const permissions = ROLE_PERMISSIONS[user.role] || [];
    return permissions.includes(permission);
  };

  const require = (permission: Permission): void => {
    if (!can(permission)) {
      throw new Error(`Permission denied: ${permission}`);
    }
  };

  return { can, require };
}

// ── Usage in components ───────────────────────────────────────────

function DeleteContractButton({ contractId }: { contractId: string }) {
  const { can } = usePermission();

  if (!can('contract:delete')) {
    return null;  // Don't render at all
  }

  return <Button variant="danger">Delete Contract</Button>;
}
```

### 7.4 Cache Invalidation Governance

```typescript
// lib/hooks/use-contracts.ts — Cache invalidation rules

export function useCreateContract() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: FormData) => apiClient.post('/contracts', data),

    // Rule 1: Invalidate list queries on mutation
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contracts'] });
    },

    // Rule 2: Show toast on success/error
    onError: (error) => {
      toast.error('Failed to create contract');
    },
  });
}

// Rule 3: Stale time governance
//   Dashboard data:    30s stale time
//   Detail data:       2min stale time
//   Reference data:    5min stale time (users, roles)
//   AI results:        Until new analysis completes
//   Search results:    30s stale time
```

### 7.5 UX Performance Budgets

```
Interaction response:    < 100ms  (button clicks, navigation)
Page load (initial):     < 2s     (first contentful paint)
Page load (subsequent):  < 500ms  (cached/SPA navigation)
Table render (100 rows): < 200ms  (virtualized)
Table render (10k rows): < 1s     (virtualized)
Search autocomplete:     < 200ms  (debounced 300ms)
AI streaming TTFF:       < 1s     (time to first fragment)
Modal/drawer open:       < 100ms  (animation)
```

---

## 8. AI Cost Governance

### 8.1 Cost Ledger Schema

```sql
-- ── AI Cost Ledger ────────────────────────────────────────────────

CREATE TABLE ai_cost_ledger (
    ledger_id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL,
    analysis_id         UUID REFERENCES ai_analyses(analysis_id),
    workflow_id         UUID,
    contract_id         UUID,
    
    -- Provider
    provider            TEXT NOT NULL,       -- 'openai', 'anthropic'
    model               TEXT NOT NULL,       -- 'gpt-4o', 'claude-3-sonnet'
    workflow_type       TEXT NOT NULL,       -- 'risk_analysis', 'clause_classify'
    
    -- Usage
    prompt_tokens       INTEGER NOT NULL,
    completion_tokens   INTEGER NOT NULL,
    total_tokens        INTEGER NOT NULL,
    estimated_cost_usd  NUMERIC(12,8) NOT NULL,
    actual_cost_usd     NUMERIC(12,8),       -- From provider billing API
    
    -- Performance
    latency_ms          INTEGER NOT NULL,
    was_cached          BOOLEAN NOT NULL DEFAULT FALSE,
    had_retry           BOOLEAN NOT NULL DEFAULT FALSE,
    retry_count         INTEGER NOT NULL DEFAULT 0,
    
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (created_at);

CREATE INDEX idx_cost_ledger_tenant
    ON ai_cost_ledger(tenant_id, created_at DESC);
CREATE INDEX idx_cost_ledger_model
    ON ai_cost_ledger(model, created_at DESC);

-- ── Daily Cost Aggregation ────────────────────────────────────────

CREATE MATERIALIZED VIEW ai_cost_daily AS
SELECT
    tenant_id,
    date_trunc('day', created_at) AS day,
    provider,
    model,
    workflow_type,
    COUNT(*) AS total_calls,
    SUM(total_tokens) AS total_tokens,
    SUM(estimated_cost_usd) AS total_cost,
    AVG(latency_ms) AS avg_latency_ms,
    SUM(CASE WHEN was_cached THEN 1 ELSE 0 END) AS cached_calls,
    SUM(CASE WHEN had_retry THEN 1 ELSE 0 END) AS retried_calls
FROM ai_cost_ledger
GROUP BY tenant_id, date_trunc('day', created_at), provider, model, workflow_type;

REFRESH MATERIALIZED VIEW CONCURRENTLY ai_cost_daily;
```

### 8.2 Budget Enforcement

```python
# app/kernel/llm/cost_governor.py

class AICostGovernor:
    """Enforces AI budget limits per tenant."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_and_record(
        self, tenant_id: str, workflow_type: str,
        estimated_cost: float, request: LLMRequest,
    ) -> tuple[bool, str | None]:
        """Check budget before execution. Returns (allowed, reason)."""
        
        # 1. Check daily budget
        daily_usage = await self._get_daily_usage(tenant_id)
        daily_budget = await self._get_daily_budget(tenant_id)
        
        if daily_budget and (daily_usage + estimated_cost) > daily_budget:
            return False, f"Daily AI budget exceeded (${daily_usage:.2f} / ${daily_budget:.2f})"
        
        # 2. Check monthly budget
        monthly_usage = await self._get_monthly_usage(tenant_id)
        monthly_budget = await self._get_monthly_budget(tenant_id)
        
        if monthly_budget and (monthly_usage + estimated_cost) > monthly_budget:
            return False, f"Monthly AI budget exceeded (${monthly_usage:.2f} / ${monthly_budget:.2f})"
        
        # 3. Check per-workflow rate limit
        hourly_count = await self._get_hourly_count(tenant_id, workflow_type)
        if hourly_count > 100:  # Configurable per workflow
            return False, f"Hourly rate limit reached for {workflow_type}"
        
        return True, None

    async def record_usage(self, response: LLMResponse, tenant_id: str, workflow_type: str, analysis_id: str):
        """Record AI usage in cost ledger."""
        await self.db.execute(
            text("""
                INSERT INTO ai_cost_ledger
                    (tenant_id, analysis_id, provider, model, workflow_type,
                     prompt_tokens, completion_tokens, total_tokens,
                     estimated_cost_usd, latency_ms)
                VALUES
                    (:tenant_id, :analysis_id, :provider, :model, :workflow_type,
                     :prompt_tokens, :completion_tokens, :total_tokens,
                     :cost, :latency_ms)
            """),
            {
                'tenant_id': tenant_id,
                'analysis_id': analysis_id,
                'provider': response.provider,
                'model': response.model,
                'workflow_type': workflow_type,
                'prompt_tokens': response.prompt_tokens,
                'completion_tokens': response.completion_tokens,
                'total_tokens': response.total_tokens,
                'cost': response.cost_usd,
                'latency_ms': response.latency_ms,
            },
        )
        await self.db.commit()
```

### 8.3 Cost Dashboard Metrics

```
AI Cost Dashboard (Grafana):

1. Cost by Tenant (bar chart)
   └── Daily/weekly/monthly cost per tenant
   └── Budget utilization %

2. Cost by Model (pie chart)
   └── gpt-4o vs gpt-4o-mini vs claude-3

3. Cost by Workflow (bar chart)
   └── risk_analysis vs clause_classify vs obligations

4. Cache Hit Rate (gauge)
   └── % of AI calls served from cache

5. Cost per Analysis (heatmap)
   └── Average cost by workflow type and contract size

6. Efficiency Score (time series)
   └── tokens per dollar over time

7. Anomaly Detection (alert)
   └── Daily cost > 2x standard deviation from 7-day average
```

---

## 9. Product Validation Governance

### 9.1 MVP Validation Gates

```
GATE 1: Auth + Tenant (Week 4)
  [ ] User can sign up via Auth0
  [ ] User can create tenant
  [ ] User can invite team members
  [ ] RBAC enforced (admin/analyst/viewer)
  └── FAILURE: Blocked — cannot proceed without multi-tenant auth

GATE 2: Contract Upload + OCR (Week 8)
  [ ] User can upload PDF
  [ ] OCR extracts text from digital PDF (> 95% accuracy)
  [ ] OCR extracts text from scanned PDF (> 80% accuracy)
  [ ] Text is chunked and embedded
  └── FAILURE: Pause — OCR quality must meet minimum threshold

GATE 3: AI Analysis (Week 12)
  [ ] AI generates risk analysis for uploaded contract
  [ ] AI classifies clauses with > 80% accuracy
  [ ] AI findings are displayed in UI
  [ ] Analysis completes within 30 seconds
  └── FAILURE: Pause — AI quality must meet threshold before workflow integration

GATE 4: Search (Week 14)
  [ ] Semantic search returns relevant results
  [ ] Recall@10 > 0.80 on test dataset
  [ ] Search latency p95 < 1s
  └── FAILURE: Pause — search quality below enterprise threshold

GATE 5: Workflow + Review UI (Week 20)
  [ ] User can review contract in UI
  [ ] User can approve/reject workflow
  [ ] Audit log captures all actions
  [ ] 3 pilot users can complete end-to-end flow
  └── FAILURE: Pause — UX must be validated with real users

GATE 6: Pilot Ready (Week 24)
  [ ] All 5 gates passed
  [ ] Load test: 100 concurrent users, 1s p95 latency
  [ ] Security audit: no critical findings
  [ ] Backup/restore tested
  [ ] Runbook documented
  └── FAILURE: Blocked — cannot launch pilot without passing all gates
```

### 9.2 Infrastructure Stop Rules

```
STOP BUILDING INFRASTRUCTURE WHEN:
  1. < 100 active users — use single PostgreSQL, no read replicas
  2. < 10k contracts — no archival jobs needed
  3. < 1M chunks — pgvector is sufficient, no external vector DB
  4. < 10 AI analyses/day — no AI caching needed
  5. < 5 team members — no deployment automation beyond basic CI/CD
  6. < 3 months since first pilot — no multi-region planning
  7. < 50% AI budget utilization — no cost optimization needed
  8. < 1 search quality complaint — no reranker needed

PRIORITIZE UX WHEN:
  1. 3+ pilot users report confusion
  2. Task completion rate < 80%
  3. Time-to-complete > 2x estimated
  4. Support tickets > 5/week for same issue

PRIORITIZE RELIABILITY WHEN:
  1. Error rate > 1%
  2. P99 latency > 5s
  3. Any data loss incident
  4. Any security incident
```

### 9.3 Product Maturity Scorecard

| Dimension | Crawl (V1) | Walk (V2) | Run (V3) | Current Score |
|-----------|-----------|-----------|----------|---------------|
| **Auth** | Auth0 basic | SSO, SCIM | MFA, device trust | Crawl |
| **OCR** | PyMuPDF + Tesseract | OCRmyPDF + deskew | Cloud OCR fallback | Crawl |
| **AI** | Single model (GPT-4o) | Multi-provider + cache | Fine-tuned models | Crawl |
| **Search** | pgvector hybrid | Reranker + query rewrite | Graph-enhanced | Crawl |
| **Workflows** | Single approval | Multi-step | Conditional routing | Crawl |
| **Infrastructure** | Single region | Read replicas | Multi-region | Crawl |
| **Security** | RLS + JWT | Field encryption | Zero trust | Crawl |
| **Observability** | Sentry + logs | Grafana dashboards | Anomaly detection | Crawl |
| **Cost Governance** | Manual tracking | Budget alerts | Auto-optimization | Crawl |
| **Testing** | Unit + integration | E2E + load | Chaos engineering | Crawl |

**Target for Pilot:** All dimensions at Crawl, 3 dimensions at Walk (Auth, AI, Search)

---

## 10. Production Hardening Summary

### 10.1 Priority Action Items

| Priority | Action | Section | Effort | Impact | Timeline |
|----------|--------|---------|--------|--------|----------|
| **P0** | Implement LLM provider abstraction | §3 | 2 days | Prevents lock-in, enables fallback | Week 1 |
| **P0** | Implement worker abstraction layer | §2 | 1 day | Prevents Celery lock-in | Week 1 |
| **P0** | Add OCR quality scoring + fallback | §4 | 3 days | Prevents silent data quality issues | Week 2-3 |
| **P0** | Add Auth0 integration | §1 | 2 days | Production auth | Week 1 |
| **P0** | Add Sentry error tracking | §1 | 0.5 day | Crash visibility | Week 1 |
| **P1** | Implement AI cost ledger | §8 | 2 days | Cost visibility | Week 3-4 |
| **P1** | Add skeleton loading to all components | §7 | 3 days | UX quality | Week 4-6 |
| **P1** | Add search evaluation dataset | §5 | 2 days | Search quality measurement | Week 6-8 |
| **P1** | Set up Grafana dashboards | §1 | 2 days | Operational visibility | Week 4-6 |
| **P2** | Implement budget enforcement | §8 | 3 days | Cost control | Month 3 |
| **P2** | Virtualize large tables | §7 | 2 days | UI performance | Month 3 |
| **P2** | Add cache invalidation rules | §7 | 1 day | Data freshness | Month 2 |

### 10.2 Technical Debt Prevention Rules

```
1. Every LLM call goes through LLMProvider abstraction — NO direct OpenAI calls
2. Every background task goes through TaskExecutor abstraction — NO direct Celery decorators
3. Every search query goes through RetrievalEngine abstraction — NO direct pgvector queries
4. Every component has loading/error/empty states — NO missing states
5. Every data-fetching hook has staleTime configured — NO infinite refetching
6. Every AI call is logged in ai_cost_ledger — NO untracked AI usage
7. Every table with > 100 rows uses virtualization — NO unoptimized large tables
8. Every route checks permissions server-side — NO client-only auth
9. Every migration has a downgrade script — NO irreversible migrations
10. Every external dependency has a fallback — NO single points of failure
```

### 10.3 Operational Runbooks Needed Before Pilot

```
1. Incident Response Runbook
   └── How to detect, respond, and recover from:
       - API outage
       - Database connection exhaustion
       - OpenAI API outage
       - Worker queue backlog
       - Redis failure
       - S3 upload failure

2. Database Runbook
   └── How to:
       - Run migration (normal + emergency)
       - Rollback migration
       - Check replication lag
       - Force reindex
       - Archive old partitions
       - Restore from backup

3. AI Runbook
   └── How to:
       - Switch LLM provider
       - Clear AI cache
       - Re-run failed analyses
       - Update prompt templates
       - Investigate high costs

4. Deployment Runbook
   └── How to:
       - Deploy new version (normal)
       - Rollback deployment
       - Scale services up/down
       - Update secrets
       - Verify deployment health
```

### 10.4 Final Pre-Implementation Checklist

```
Pre-Flight Checklist (before writing first line of production code):

[ ] Auth0 tenant configured
[ ] Sentry project created
[ ] Grafana Cloud account set up (or self-hosted planned)
[ ] PostgreSQL 16 with pgvector extension available
[ ] Redis 7 available
[ ] S3-compatible storage available
[ ] OpenAI API key provisioned (with spending limit)
[ ] CI/CD pipeline configured
[ ] Docker Compose dev environment working
[ ] Migration scripts initialized (Alembic)
[ ] Test database available
[ ] Team has access to all above
[ ] Runbooks drafted (incident response, database, AI, deployment)
[ ] On-call rotation defined
[ ] Monitoring alerts configured (error rate, latency, queue depth)
[ ] Backup strategy implemented
[ ] Security review completed
[ ] Product validation gates defined
[ ] Pilot customer identified
[ ] Success metrics defined
```
