"""AI Evaluation Harness — pytest integration for golden contract testing.

Run with::
    pytest tests/ai_eval/ -v
    pytest tests/ai_eval/ --eval-suite=full
    pytest tests/ai_eval/ --eval-report=report.json
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import pytest

from tests.ai_eval import (
    AIEvaluationRunner,
    EvaluationSuiteResult,
    GoldenContract,
    load_golden_contracts,
)

logger = logging.getLogger(__name__)


# ── Pytest Configuration ───────────────────────────────────────────

# Options and markers are defined in conftest.py


# ── Fixtures ───────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def eval_runner() -> AIEvaluationRunner:
    """Create an AI evaluation runner."""
    return AIEvaluationRunner(
        confidence_threshold=0.7,
        risk_score_tolerance=0.15,
    )


@pytest.fixture(scope="session")
def golden_contracts(request: pytest.FixtureRequest) -> list[GoldenContract]:
    """Load golden contracts from the datasets directory."""
    dataset_dir = Path(__file__).parent / "datasets"
    contracts = load_golden_contracts(str(dataset_dir))

    # Filter by contract type if specified
    try:
        contract_types = request.config.getoption("--eval-contract-types")
    except (ValueError, AttributeError):
        contract_types = None
    if contract_types:
        types = set(t.strip() for t in contract_types.split(","))
        contracts = [c for c in contracts if c.contract_type in types]

    return contracts


@pytest.fixture(scope="session")
def eval_suite(request: pytest.FixtureRequest) -> str:
    """Get the evaluation suite name."""
    return request.config.getoption("--eval-suite")


# ── Smoke Tests ────────────────────────────────────────────────────

@pytest.mark.ai_eval
@pytest.mark.ai_smoke
class TestAISmokeEvaluation:
    """Quick smoke tests to validate basic AI functionality."""

    def test_evaluation_runner_initialization(self, eval_runner: AIEvaluationRunner) -> None:
        """Verify the evaluation runner initializes correctly."""
        assert eval_runner is not None
        assert eval_runner.confidence_threshold == 0.7
        assert eval_runner.risk_score_tolerance == 0.15

    def test_golden_contracts_loaded(self, golden_contracts: list[GoldenContract]) -> None:
        """Verify golden contracts are loaded from datasets."""
        assert len(golden_contracts) > 0, "No golden contracts loaded"
        contract_types = {c.contract_type for c in golden_contracts}
        assert "nda" in contract_types, "NDA contract should be in datasets"
        assert "msa" in contract_types, "MSA contract should be in datasets"

    def test_golden_contract_structure(self, golden_contracts: list[GoldenContract]) -> None:
        """Verify all golden contracts have required fields."""
        for contract in golden_contracts:
            assert contract.contract_id, f"Contract missing ID: {contract.filename}"
            assert contract.contract_type, f"Contract missing type: {contract.contract_id}"
            assert 0.0 <= contract.expected_risk_score <= 1.0, \
                f"Invalid risk score for {contract.contract_id}: {contract.expected_risk_score}"
            assert len(contract.expected_findings) > 0, \
                f"No expected findings for {contract.contract_id}"

    def test_evaluation_runner_compute_metrics(self, eval_runner: AIEvaluationRunner) -> None:
        """Test that the evaluation runner correctly computes precision/recall/F1."""
        # Create a mock golden contract
        from tests.ai_eval import ExpectedFinding, GoldenContract

        contract = GoldenContract(
            contract_id="test_001",
            contract_type="test",
            filename="test.json",
            filepath="/dev/null/test.json",
            expected_risk_score=0.5,
            expected_findings=[
                ExpectedFinding(clause_type="liability", severity="high", title="Finding A", required=True),
                ExpectedFinding(clause_type="payment", severity="medium", title="Finding B", required=True),
                ExpectedFinding(clause_type="termination", severity="low", title="Finding C", required=False),
            ],
        )

        # Mock a perfect response
        class MockAnalysisResult:
            risk_score = 0.5
            findings = []

        parsed_response = {
            "risk_score": 0.5,
            "summary": "Test summary",
            "findings": [
                {"clause_type": "liability", "severity": "high", "title": "Finding A", "description": "Liability finding", "confidence": 0.9},
                {"clause_type": "payment", "severity": "medium", "title": "Finding B", "description": "Payment finding", "confidence": 0.85},
                {"clause_type": "termination", "severity": "low", "title": "Finding C", "description": "Termination finding", "confidence": 0.8},
            ],
        }

        import asyncio
        result = asyncio.run(eval_runner.evaluate_contract(
            golden_contract=contract,
            analysis_result=MockAnalysisResult(),
            parsed_response=parsed_response,
        ))

        assert result.passed, f"Perfect response should pass: {result.errors}"
        assert result.precision == 1.0, f"Expected precision 1.0, got {result.precision}"
        assert result.recall == 1.0, f"Expected recall 1.0, got {result.recall}"
        assert result.f1_score == 1.0, f"Expected F1 1.0, got {result.f1_score}"


# ── Full Evaluation Suite ──────────────────────────────────────────

@pytest.mark.ai_eval
@pytest.mark.ai_regression
class TestAIEvaluationSuite:
    """Full evaluation suite — runs against all golden contracts."""

    @pytest.fixture(scope="class")
    def suite_results(
        self,
        eval_runner: AIEvaluationRunner,
        golden_contracts: list[GoldenContract],
        eval_suite: str,
    ) -> EvaluationSuiteResult | None:
        """Run the evaluation suite and return results."""
        # In smoke mode, only test first contract
        if eval_suite == "smoke" and len(golden_contracts) > 1:
            contracts = [golden_contracts[0]]
        else:
            contracts = golden_contracts

        # Build mock analysis results for each contract
        # In real usage, this would call the actual AI service
        analysis_results = []
        for contract in contracts:
            analysis_results.append((
                self._create_mock_result(contract),
                self._create_mock_parsed(contract),
                500,  # latency_ms
                0.002,  # cost_usd
                1500,  # total_tokens
            ))

        import asyncio
        result = asyncio.run(eval_runner.run_suite(
            contracts=contracts,
            analysis_results=analysis_results,
            suite_name=eval_suite,
        ))
        return result

    def _create_mock_result(self, contract: GoldenContract) -> Any:
        """Create a mock analysis result for testing."""
        class MockAnalysisResult:
            risk_score = contract.expected_risk_score
            findings = []

        return MockAnalysisResult()

    def _create_mock_parsed(self, contract: GoldenContract) -> dict[str, Any]:
        """Create a mock parsed response that matches expected findings."""
        findings = []
        for ef in contract.expected_findings:
            findings.append({
                "clause_type": ef.clause_type,
                "severity": ef.severity,
                "title": ef.title,
                "description": f"{ef.description_contains} - detected in contract analysis",
                "confidence": ef.min_confidence + 0.1,
                "chunk_indices": [0],
            })
        return {
            "risk_score": contract.expected_risk_score,
            "summary": f"Analysis of {contract.contract_type} contract",
            "findings": findings,
        }

    def test_suite_completes(self, suite_results: EvaluationSuiteResult | None) -> None:
        """Verify the evaluation suite completes."""
        assert suite_results is not None, "Suite results should not be None"
        assert suite_results.total_contracts > 0, "Should have evaluated at least one contract"

    def test_suite_metrics_computed(self, suite_results: EvaluationSuiteResult | None) -> None:
        """Verify aggregate metrics are computed."""
        assert suite_results is not None
        assert 0.0 <= suite_results.avg_precision <= 1.0
        assert 0.0 <= suite_results.avg_recall <= 1.0
        assert 0.0 <= suite_results.avg_f1 <= 1.0
        assert suite_results.total_contracts == len(suite_results.results)

    def test_suite_report_generation(
        self,
        suite_results: EvaluationSuiteResult | None,
        request: pytest.FixtureRequest,
    ) -> None:
        """Verify report can be generated (if --eval-report is provided)."""
        report_path = request.config.getoption("--eval-report")
        if report_path and suite_results:
            import json
            with open(report_path, "w") as f:
                json.dump(suite_results.to_dict(), f, indent=2)
            assert Path(report_path).exists(), f"Report not written to {report_path}"


# ── Hallucination Detection Tests ──────────────────────────────────

@pytest.mark.ai_eval
@pytest.mark.ai_hallucination
class TestAIHallucinationDetection:
    """Tests for hallucination detection in AI responses."""

    @pytest.fixture
    def runner(self) -> AIEvaluationRunner:
        return AIEvaluationRunner()

    def test_detect_uncertainty_language(self, runner: AIEvaluationRunner) -> None:
        """Detect 'I think' or 'perhaps' in responses."""
        flags = runner._detect_hallucinations({
            "risk_score": 0.5,
            "summary": "I think this contract has some risks perhaps.",
            "findings": [],
        })
        assert len(flags) > 0, "Should flag uncertainty language"

    def test_detect_unverifiable_claims(self, runner: AIEvaluationRunner) -> None:
        """Detect 'industry standard' claims."""
        flags = runner._detect_hallucinations({
            "risk_score": 0.5,
            "summary": "This is industry standard practice.",
            "findings": [],
        })
        assert len(flags) > 0, "Should flag unverifiable claims"

    def test_clean_response_no_flags(self, runner: AIEvaluationRunner) -> None:
        """Clean response should not trigger hallucination flags."""
        flags = runner._detect_hallucinations({
            "risk_score": 0.5,
            "summary": "The contract contains standard liability and indemnification clauses.",
            "findings": [
                {"clause_type": "liability", "title": "Test", "description": "Standard clause"},
            ],
        })
        assert len(flags) == 0, f"Clean response should not have flags: {flags}"


# ── Response Validation Tests ──────────────────────────────────────

@pytest.mark.ai_eval
class TestAIResponseValidation:
    """Tests for LLM response validation."""

    @pytest.fixture
    def validator(self):
        from app.domains.ai.validation import LLMResponseValidator
        return LLMResponseValidator()

    def test_valid_json_passes(self, validator) -> None:
        """Valid JSON response should pass validation."""
        result = validator.validate(
            json.dumps({
                "risk_score": 0.5,
                "summary": "Test summary",
                "findings": [{"clause_type": "liability", "severity": "high", "title": "Test", "description": "Test finding"}],
            })
        )
        assert result.passed, f"Valid response should pass: {result.issues}"

    def test_invalid_json_fails(self, validator) -> None:
        """Invalid JSON should fail validation."""
        result = validator.validate("not valid json{{{")
        assert not result.passed, "Invalid JSON should fail"

    def test_missing_required_fields(self, validator) -> None:
        """Missing required fields should fail validation."""
        result = validator.validate(json.dumps({"risk_score": 0.5}))
        assert not result.passed, "Missing fields should fail"

    def test_risk_score_out_of_range(self, validator) -> None:
        """Risk score outside 0.0-1.0 should fail."""
        result = validator.validate(json.dumps({
            "risk_score": 1.5,
            "summary": "Test",
            "findings": [],
        }))
        assert not result.passed, "Risk score > 1.0 should fail"

    def test_hallucination_detection(self, validator) -> None:
        """Response with uncertainty language should get warnings."""
        result = validator.validate(json.dumps({
            "risk_score": 0.5,
            "summary": "I think this might be a risk, perhaps.",
            "findings": [{"clause_type": "liability", "severity": "high", "title": "Test", "description": "Test"}],
        }))
        warnings = [i for i in result.issues if i.code == "hallucination_language"]
        assert len(warnings) > 0, "Should detect hallucination language"


# ── Replay Engine Tests ────────────────────────────────────────────

@pytest.mark.ai_eval
class TestAIReplayEngine:
    """Tests for the deterministic replay engine."""

    def test_drift_classification(self) -> None:
        """Test drift severity classification."""
        from app.domains.ai.replay import ReplayAIExecutionService, DriftSeverity

        service = object.__new__(ReplayAIExecutionService)

        from app.domains.ai.replay import ReplayComparison

        comparison = ReplayComparison(
            execution_id="test",
            original_run_id="orig",
            replay_run_id="replay",
        )
        # drift_score defaults to 0.0, severity should be NONE
        assert comparison.drift_severity == DriftSeverity.NONE

        # Manually set drift_score and re-classify
        comparison.drift_score = 0.1
        comparison.drift_severity = service._classify_drift(0.1)
        assert comparison.drift_severity == DriftSeverity.LOW

        comparison.drift_score = 0.2
        comparison.drift_severity = service._classify_drift(0.2)
        assert comparison.drift_severity == DriftSeverity.MEDIUM

        comparison.drift_score = 0.35
        comparison.drift_severity = service._classify_drift(0.35)
        assert comparison.drift_severity == DriftSeverity.HIGH

        comparison.drift_score = 0.55
        comparison.drift_severity = service._classify_drift(0.55)
        assert comparison.drift_severity == DriftSeverity.CRITICAL

    def test_replay_comparison_to_dict(self) -> None:
        """Test ReplayComparison serialization."""
        from app.domains.ai.replay import ReplayComparison, DriftSeverity

        comparison = ReplayComparison(
            execution_id="exec-1",
            original_run_id="orig-1",
            replay_run_id="replay-1",
            drift_detected=True,
            drift_score=0.25,
            drift_severity=DriftSeverity.MEDIUM,
            original_findings_count=5,
            replay_findings_count=7,
            findings_overlap=0.6,
            original_risk_score=0.5,
            replay_risk_score=0.65,
        )
        d = comparison.to_dict()
        assert d["execution_id"] == "exec-1"
        assert d["drift_detected"] == True
        assert d["drift_score"] == 0.25
        assert d["original_findings_count"] == 5
        assert d["replay_findings_count"] == 7


# ── Queue Reliability Tests ────────────────────────────────────────

@pytest.mark.ai_eval
class TestQueueReliability:
    """Tests for the reliable queue framework."""

    @pytest.fixture
    def queue_manager(self):
        from app.domains.queue import ReliableQueueManager, RetryPolicy, BackoffStrategy
        return ReliableQueueManager(
            retry_policy=RetryPolicy(
                max_retries=3,
                backoff_strategy=BackoffStrategy.FIXED,
                base_delay_seconds=0.01,
                jitter=False,
            ),
        )

    def test_enqueue_job(self, queue_manager) -> None:
        """Test basic job enqueueing."""
        import asyncio
        job = asyncio.run(queue_manager.enqueue(
            job_type="test_job",
            payload={"key": "value"},
            queue_name="test_queue",
        ))
        assert job.job_id is not None
        assert job.job_type == "test_job"
        assert job.payload == {"key": "value"}
        assert job.status.value == "pending"

    def test_idempotency(self, queue_manager) -> None:
        """Test idempotency key deduplication."""
        import asyncio
        job1 = asyncio.run(queue_manager.enqueue(
            job_type="test_job",
            payload={"key": "value"},
        ))
        is_dup = queue_manager.is_duplicate(job1.idempotency_key)
        assert is_dup, "Should detect duplicate"

    def test_retry_policy_delays(self) -> None:
        """Test retry backoff calculation."""
        from app.domains.queue import RetryPolicy, BackoffStrategy

        # Exponential backoff
        policy = RetryPolicy(
            backoff_strategy=BackoffStrategy.EXPONENTIAL,
            base_delay_seconds=1.0,
            max_delay_seconds=60.0,
            jitter=False,
        )
        assert policy.get_delay(1) == 1.0
        assert policy.get_delay(2) == 2.0
        assert policy.get_delay(3) == 4.0
        assert policy.get_delay(4) == 8.0

        # Linear backoff
        linear = RetryPolicy(
            backoff_strategy=BackoffStrategy.LINEAR,
            base_delay_seconds=1.0,
            jitter=False,
        )
        assert linear.get_delay(1) == 1.0
        assert linear.get_delay(2) == 2.0
        assert linear.get_delay(3) == 3.0

    def test_dead_letter_queue(self, queue_manager) -> None:
        """Test dead-letter queue after max retries."""
        import asyncio

        async def failing_handler(job):
            raise ValueError("Intentional failure")

        queue_manager.register_handler("failing_job", failing_handler)

        job = asyncio.run(queue_manager.enqueue(
            job_type="failing_job",
            payload={},
            max_retries=1,
        ))

        # Process twice (should fail and go to DLQ)
        asyncio.run(queue_manager.process_next("default"))
        asyncio.run(queue_manager.process_next("default"))

        dlq = queue_manager.get_dead_letter_queue()
        assert len(dlq) > 0, "Job should be in dead-letter queue"

    def test_stuck_job_detection(self, queue_manager) -> None:
        """Test stuck job recovery."""
        import asyncio

        # Simulate a stuck job
        job = QueueJob(
            job_type="stuck_job",
            payload={},
            started_at=time.time() - 120,  # Started 2 minutes ago
        )
        queue_manager._processing[job.job_id] = job

        stuck = asyncio.run(queue_manager.scan_stuck_jobs(timeout_seconds=60))
        assert len(stuck) > 0, "Should detect stuck job"
        assert stuck[0].job_id == job.job_id


# ── Prompt Registry Tests ──────────────────────────────────────────

@pytest.mark.ai_eval
class TestPromptRegistry:
    """Tests for the prompt registry with versioning."""

    @pytest.fixture
    def registry(self):
        from app.domains.ai.prompts import PromptRegistry, PromptTemplate, PromptStatus
        return PromptRegistry()

    def test_register_and_get(self, registry) -> None:
        """Test registering and retrieving prompt templates."""
        from app.domains.ai.prompts import PromptTemplate

        template = PromptTemplate(
            key="test_prompt",
            version="1.0.0",
            system_prompt="You are a test assistant.",
            template="Analyze: {{ text }}",
        )
        registry.register(template)

        retrieved = registry.get("test_prompt")
        assert retrieved is not None
        assert retrieved.version == "1.0.0"
        assert retrieved.system_prompt == "You are a test assistant."

    def test_version_sorting(self, registry) -> None:
        """Test that versions are sorted correctly (newest first)."""
        from app.domains.ai.prompts import PromptTemplate

        v1 = PromptTemplate(key="test", version="1.0.0", system_prompt="v1")
        v2 = PromptTemplate(key="test", version="2.0.0", system_prompt="v2")
        v3 = PromptTemplate(key="test", version="1.5.0", system_prompt="v1.5")

        registry.register(v1)
        registry.register(v2)
        registry.register(v3)

        versions = registry.list_versions("test")
        assert versions[0].version == "2.0.0"
        assert versions[1].version == "1.5.0"
        assert versions[2].version == "1.0.0"

    def test_activate_version(self, registry) -> None:
        """Test activating a specific version."""
        from app.domains.ai.prompts import PromptTemplate

        v1 = PromptTemplate(key="test", version="1.0.0", system_prompt="v1")
        v2 = PromptTemplate(key="test", version="2.0.0", system_prompt="v2")

        registry.register(v1)
        registry.register(v2)

        registry.activate("test", "1.0.0")
        active = registry.get_active("test")
        assert active is not None
        assert active.version == "1.0.0"

    def test_tenant_override(self, registry) -> None:
        """Test tenant-specific prompt overrides."""
        from app.domains.ai.prompts import PromptTemplate, TenantPromptOverride

        base = PromptTemplate(key="test", version="1.0.0", system_prompt="Default prompt")
        registry.register(base)

        override = TenantPromptOverride(
            tenant_id="tenant_123",
            prompt_key="test",
            version="1.0.0",
            overridden_system_prompt="Tenant-specific prompt",
        )
        registry.set_tenant_override(override)

        # Without tenant, should get default
        default = registry.get("test")
        assert default is not None
        assert default.system_prompt == "Default prompt"

        # With tenant, should get override
        tenant_version = registry.get("test", tenant_id="tenant_123")
        assert tenant_version is not None
        assert tenant_version.system_prompt == "Tenant-specific prompt"


# ── Telemetry Tests ────────────────────────────────────────────────

@pytest.mark.ai_eval
class TestAITelemetry:
    """Tests for structured AI telemetry."""

    @pytest.fixture
    def metrics(self):
        from app.domains.ai.telemetry import AIExecutionMetrics
        return AIExecutionMetrics()

    def test_record_execution(self, metrics) -> None:
        """Test recording an execution."""
        from app.domains.ai.telemetry import ExecutionMetrics

        m = ExecutionMetrics(
            execution_id="exec-1",
            tenant_id="tenant-1",
            operation_type="risk_analysis",
            provider="openai",
            model="gpt-4o",
            total_latency_ms=500,
            provider_latency_ms=450,
            total_tokens=1000,
            cost_usd=0.002,
            confidence=0.85,
            findings_count=5,
        )
        metrics.record_execution(m)

        agg = metrics.get_aggregates()
        assert agg["total_executions"] == 1
        assert agg["total_cost_usd"] == 0.002
        assert agg["total_tokens"] == 1000

    def test_aggregates_multiple_executions(self, metrics) -> None:
        """Test aggregate calculations with multiple executions."""
        from app.domains.ai.telemetry import ExecutionMetrics

        for i in range(5):
            metrics.record_execution(ExecutionMetrics(
                execution_id=f"exec-{i}",
                tenant_id="tenant-1",
                operation_type="risk_analysis",
                provider="openai",
                model="gpt-4o",
                total_latency_ms=500,
                total_tokens=1000,
                cost_usd=0.002,
            ))

        agg = metrics.get_aggregates()
        assert agg["total_executions"] == 5
        assert agg["total_cost_usd"] == 0.01
        assert agg["avg_latency_ms"] == 500

    def test_error_rate(self, metrics) -> None:
        """Test error rate calculation."""
        from app.domains.ai.telemetry import ExecutionMetrics

        for i in range(8):
            metrics.record_execution(ExecutionMetrics(
                execution_id=f"ok-{i}", tenant_id="t1", operation_type="test",
                provider="openai", model="gpt-4o",
            ))
        for i in range(2):
            metrics.record_execution(ExecutionMetrics(
                execution_id=f"fail-{i}", tenant_id="t1", operation_type="test",
                provider="openai", model="gpt-4o",
                error_message="Timeout",
            ))

        assert metrics.get_error_rate() == 0.2

    def test_reset(self, metrics) -> None:
        """Test resetting metrics."""
        from app.domains.ai.telemetry import ExecutionMetrics

        metrics.record_execution(ExecutionMetrics(
            execution_id="exec-1", tenant_id="t1", operation_type="test",
            provider="openai", model="gpt-4o",
        ))
        metrics.reset()
        assert metrics.get_aggregates()["total_executions"] == 0


# ── Tracing Tests ──────────────────────────────────────────────────

@pytest.mark.ai_eval
class TestAITracing:
    """Tests for OpenTelemetry tracing integration."""

    @pytest.fixture
    def tracer(self):
        from app.domains.ai.telemetry.tracing import AIExecutionTracer
        # Create a tracer with no OTEL to use the in-memory recorder
        import app.domains.ai.telemetry.tracing as tracing_mod
        orig = tracing_mod._OTEL_AVAILABLE
        tracing_mod._OTEL_AVAILABLE = False
        t = AIExecutionTracer()
        tracing_mod._OTEL_AVAILABLE = orig
        return t

    def test_execution_span(self, tracer) -> None:
        """Test creating an execution span."""
        with tracer.execution_span("exec-1", "tenant-1", "risk_analysis") as span:
            assert span is not None
            tracer.set_span_attribute(span, "test_attr", "test_value")

        spans = tracer.get_recorder_spans()
        assert len(spans) == 1
        assert spans[0]["name"] == "ai.execution"

    def test_nested_spans(self, tracer) -> None:
        """Test nested span hierarchy."""
        with tracer.execution_span("exec-1", "tenant-1", "risk_analysis"):
            with tracer.retrieval_span():
                pass
            with tracer.provider_span("openai", "gpt-4o"):
                pass
            with tracer.validation_span():
                pass

        spans = tracer.get_recorder_spans()
        span_names = [s["name"] for s in spans]
        assert "ai.execution" in span_names
        assert "ai.retrieval" in span_names
        assert "ai.provider" in span_names
        assert "ai.validation" in span_names

    def test_span_attributes(self, tracer) -> None:
        """Test span attributes are recorded."""
        with tracer.execution_span("exec-1", "tenant-1", "risk_analysis") as span:
            tracer.set_span_attribute(span, "ai.execution_id", "exec-1")
            tracer.set_span_attribute(span, "ai.tenant_id", "tenant-1")

        spans = tracer.get_recorder_spans()
        attrs = spans[0]["attributes"]
        assert attrs.get("ai.execution_id") == "exec-1"
        assert attrs.get("ai.tenant_id") == "tenant-1"

    def test_exception_recording(self, tracer) -> None:
        """Test recording exceptions on spans."""
        span = tracer.start_span("test.span", {"test": "value"})
        tracer.record_exception(span, ValueError("Test error"))
        tracer.end_span(span, "error")

        spans = tracer.get_recorder_spans()
        assert spans[0]["status"] == "error"


# Import for stuck job test
import time
from app.domains.queue import QueueJob
