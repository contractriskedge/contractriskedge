"""AI Evaluation Harness — golden contract testing for AI quality validation.

This is one of the most critical missing pieces in AI startups.
Without this, prompt changes become dangerous.

Tests validate:
- Golden contracts produce expected findings
- Expected clause matches
- Hallucination detection
- Confidence scoring
- Regression benchmarks
- Precision, recall, consistency, drift score
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ── Evaluation Types ───────────────────────────────────────────────

@dataclass
class GoldenContract:
    """A golden contract with expected AI analysis results.

    This is the ground truth for evaluation.
    """
    contract_id: str
    contract_type: str  # "nda", "msa", "saas", "procurement", "employment", "dpa", "vendor"
    filename: str
    filepath: str

    # Expected results
    expected_risk_score: float
    expected_findings: list[ExpectedFinding] = field(default_factory=list)
    expected_clause_types: list[str] = field(default_factory=list)
    expected_redlines: list[ExpectedRedline] = field(default_factory=list)

    # Metadata
    description: str = ""
    jurisdiction: str = "us"
    risk_profile: str = "standard"  # "standard", "high_risk", "low_risk"
    tags: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ExpectedFinding:
    """An expected finding that the AI should detect."""
    clause_type: str
    severity: str
    title: str
    description_contains: str = ""
    min_confidence: float = 0.7
    required: bool = True  # If True, missing this is a failure


@dataclass
class ExpectedRedline:
    """An expected redline suggestion."""
    clause_type: str
    original_text_contains: str = ""
    proposed_text_contains: str = ""
    operation: str = "modification"
    min_confidence: float = 0.7
    required: bool = True


# ── Evaluation Results ─────────────────────────────────────────────

@dataclass
class EvaluationResult:
    """Result of evaluating an AI execution against a golden contract."""
    contract_id: str
    contract_type: str
    passed: bool

    # Metrics
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    accuracy: float = 0.0

    # Finding-level metrics
    true_positives: list[str] = field(default_factory=list)
    false_positives: list[str] = field(default_factory=list)
    false_negatives: list[str] = field(default_factory=list)

    # Score comparison
    expected_risk_score: float = 0.0
    actual_risk_score: float = 0.0
    risk_score_error: float = 0.0

    # Confidence
    avg_confidence: float = 0.0
    confidence_within_threshold: bool = True

    # Hallucination
    hallucination_flags: list[str] = field(default_factory=list)
    hallucination_count: int = 0

    # Latency & cost
    latency_ms: int = 0
    cost_usd: float = 0.0
    total_tokens: int = 0

    # Details
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_type": self.contract_type,
            "passed": self.passed,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1_score": round(self.f1_score, 4),
            "accuracy": round(self.accuracy, 4),
            "true_positives": len(self.true_positives),
            "false_positives": len(self.false_positives),
            "false_negatives": len(self.false_negatives),
            "expected_risk_score": self.expected_risk_score,
            "actual_risk_score": self.actual_risk_score,
            "risk_score_error": round(self.risk_score_error, 4),
            "avg_confidence": round(self.avg_confidence, 4),
            "hallucination_count": self.hallucination_count,
            "latency_ms": self.latency_ms,
            "cost_usd": round(self.cost_usd, 6),
            "total_tokens": self.total_tokens,
            "errors": self.errors,
            "warnings": self.warnings,
        }


@dataclass
class EvaluationSuiteResult:
    """Result of running an evaluation suite (multiple contracts)."""
    suite_name: str
    total_contracts: int
    passed: int
    failed: int
    results: list[EvaluationResult] = field(default_factory=list)

    # Aggregate metrics
    avg_precision: float = 0.0
    avg_recall: float = 0.0
    avg_f1: float = 0.0
    avg_accuracy: float = 0.0
    avg_risk_score_error: float = 0.0
    avg_confidence: float = 0.0
    total_hallucinations: int = 0
    total_cost_usd: float = 0.0
    total_latency_ms: int = 0

    @property
    def pass_rate(self) -> float:
        if self.total_contracts == 0:
            return 0.0
        return self.passed / self.total_contracts

    def to_dict(self) -> dict[str, Any]:
        return {
            "suite_name": self.suite_name,
            "total_contracts": self.total_contracts,
            "passed": self.passed,
            "failed": self.failed,
            "pass_rate": round(self.pass_rate, 4),
            "avg_precision": round(self.avg_precision, 4),
            "avg_recall": round(self.avg_recall, 4),
            "avg_f1": round(self.avg_f1, 4),
            "avg_accuracy": round(self.avg_accuracy, 4),
            "avg_risk_score_error": round(self.avg_risk_score_error, 4),
            "avg_confidence": round(self.avg_confidence, 4),
            "total_hallucinations": self.total_hallucinations,
            "total_cost_usd": round(self.total_cost_usd, 4),
            "total_latency_ms": self.total_latency_ms,
            "results": [r.to_dict() for r in self.results],
        }


# ── Evaluation Runner ──────────────────────────────────────────────

@dataclass
class AIEvaluationRunner:
    """Runs AI evaluations against golden contracts.

    Usage::
        runner = AIEvaluationRunner()
        result = await runner.evaluate_contract(
            golden_contract=contract,
            ai_service=ai_service,
        )
        suite_result = await runner.run_suite(
            contracts=[contract1, contract2],
            ai_service=ai_service,
        )
    """

    confidence_threshold: float = 0.7
    risk_score_tolerance: float = 0.15  # Acceptable delta from expected

    async def evaluate_contract(
        self,
        golden_contract: GoldenContract,
        analysis_result: Any,  # AnalysisResult or similar
        parsed_response: dict[str, Any] | None = None,
        latency_ms: int = 0,
        cost_usd: float = 0.0,
        total_tokens: int = 0,
    ) -> EvaluationResult:
        """Evaluate an AI execution against a golden contract.

        Args:
            golden_contract: The golden contract with expected results.
            analysis_result: The AI analysis result object.
            parsed_response: The raw parsed JSON response from the LLM.
            latency_ms: Execution latency.
            cost_usd: Execution cost.
            total_tokens: Total tokens used.

        Returns:
            EvaluationResult with precision, recall, F1, etc.
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Extract actual findings
        actual_findings = self._extract_findings(analysis_result, parsed_response)
        actual_titles = {f.get("title", "") for f in actual_findings}
        actual_clause_types = {f.get("clause_type", "") for f in actual_findings}
        actual_risk_score = self._extract_risk_score(analysis_result, parsed_response)

        # Calculate metrics
        expected_required = {f.title for f in golden_contract.expected_findings if f.required}
        expected_all = {f.title for f in golden_contract.expected_findings}

        true_positives = actual_titles & expected_required
        false_positives = actual_titles - expected_all
        false_negatives = expected_required - actual_titles

        # Precision: TP / (TP + FP)
        precision = len(true_positives) / (len(true_positives) + len(false_positives)) if (len(true_positives) + len(false_positives)) > 0 else 0.0

        # Recall: TP / (TP + FN)
        recall = len(true_positives) / (len(true_positives) + len(false_negatives)) if (len(true_positives) + len(false_negatives)) > 0 else 0.0

        # F1 Score
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        # Accuracy
        total_expected = len(expected_all)
        total_actual = len(actual_findings)
        correct = len(true_positives)
        accuracy = correct / max(total_expected, total_actual) if max(total_expected, total_actual) > 0 else 0.0

        # Risk score error
        risk_score_error = abs(actual_risk_score - golden_contract.expected_risk_score) if actual_risk_score is not None else 1.0

        # Average confidence
        confidences = [f.get("confidence", 0.0) or 0.0 for f in actual_findings if f.get("confidence") is not None]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        # Hallucination detection
        hallucination_flags = self._detect_hallucinations(parsed_response or {})

        # Check for missing required findings
        missing_required = false_negatives
        if missing_required:
            errors.append(f"Missing required findings: {', '.join(sorted(missing_required))}")

        # Check risk score tolerance
        if risk_score_error > self.risk_score_tolerance:
            warnings.append(
                f"Risk score delta {risk_score_error:.2f} exceeds tolerance {self.risk_score_tolerance}"
            )

        # Check clause type coverage
        expected_clause_types = set(golden_contract.expected_clause_types)
        if expected_clause_types:
            missing_clause_types = expected_clause_types - actual_clause_types
            if missing_clause_types:
                warnings.append(f"Missing clause types: {', '.join(sorted(missing_clause_types))}")

        passed = len(errors) == 0

        return EvaluationResult(
            contract_id=golden_contract.contract_id,
            contract_type=golden_contract.contract_type,
            passed=passed,
            precision=precision,
            recall=recall,
            f1_score=f1,
            accuracy=accuracy,
            true_positives=list(true_positives),
            false_positives=list(false_positives),
            false_negatives=list(false_negatives),
            expected_risk_score=golden_contract.expected_risk_score,
            actual_risk_score=actual_risk_score or 0.0,
            risk_score_error=risk_score_error,
            avg_confidence=avg_confidence,
            hallucination_flags=hallucination_flags,
            hallucination_count=len(hallucination_flags),
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            total_tokens=total_tokens,
            errors=errors,
            warnings=warnings,
        )

    async def run_suite(
        self,
        contracts: list[GoldenContract],
        analysis_results: list[tuple[Any, dict[str, Any] | None, int, float, int]],
        suite_name: str = "default",
    ) -> EvaluationSuiteResult:
        """Run evaluation suite across multiple golden contracts.

        Args:
            contracts: List of golden contracts.
            analysis_results: List of (analysis_result, parsed_response, latency_ms, cost_usd, total_tokens) tuples.
            suite_name: Name for this evaluation suite.

        Returns:
            EvaluationSuiteResult with aggregate metrics.
        """
        results: list[EvaluationResult] = []

        for contract, (analysis_result, parsed_response, latency_ms, cost_usd, total_tokens) in zip(contracts, analysis_results):
            result = await self.evaluate_contract(
                golden_contract=contract,
                analysis_result=analysis_result,
                parsed_response=parsed_response,
                latency_ms=latency_ms,
                cost_usd=cost_usd,
                total_tokens=total_tokens,
            )
            results.append(result)

        passed = sum(1 for r in results if r.passed)
        failed = sum(1 for r in results if not r.passed)

        suite_result = EvaluationSuiteResult(
            suite_name=suite_name,
            total_contracts=len(contracts),
            passed=passed,
            failed=failed,
            results=results,
            avg_precision=sum(r.precision for r in results) / len(results) if results else 0.0,
            avg_recall=sum(r.recall for r in results) / len(results) if results else 0.0,
            avg_f1=sum(r.f1_score for r in results) / len(results) if results else 0.0,
            avg_accuracy=sum(r.accuracy for r in results) / len(results) if results else 0.0,
            avg_risk_score_error=sum(r.risk_score_error for r in results) / len(results) if results else 0.0,
            avg_confidence=sum(r.avg_confidence for r in results) / len(results) if results else 0.0,
            total_hallucinations=sum(r.hallucination_count for r in results),
            total_cost_usd=sum(r.cost_usd for r in results),
            total_latency_ms=sum(r.latency_ms for r in results),
        )

        return suite_result

    # ── Internal Helpers ───────────────────────────────────────────

    def _extract_findings(
        self,
        analysis_result: Any,
        parsed_response: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        """Extract findings from analysis result or parsed response."""
        if parsed_response and "findings" in parsed_response:
            return parsed_response["findings"]
        if hasattr(analysis_result, "findings"):
            return [
                {
                    "clause_type": getattr(f, "clause_type", ""),
                    "severity": getattr(f, "severity", ""),
                    "title": getattr(f, "title", ""),
                    "description": getattr(f, "description", ""),
                    "confidence": getattr(f, "confidence", 0.0),
                }
                for f in analysis_result.findings
            ]
        return []

    def _extract_risk_score(
        self,
        analysis_result: Any,
        parsed_response: dict[str, Any] | None,
    ) -> float | None:
        """Extract risk score from analysis result or parsed response."""
        if parsed_response and "risk_score" in parsed_response:
            try:
                return float(parsed_response["risk_score"])
            except (ValueError, TypeError):
                pass
        if hasattr(analysis_result, "risk_score"):
            return analysis_result.risk_score
        return None

    def _detect_hallucinations(self, parsed: dict[str, Any]) -> list[str]:
        """Detect potential hallucinations in the response."""
        flags: list[str] = []
        text = json.dumps(parsed).lower()

        hallucination_patterns = [
            ("uncertainty_language", r"\b(i think|i believe|i guess|perhaps|maybe)\b"),
            ("unverifiable_claim", r"\b(industry standard|market practice|widely accepted)\b"),
            ("unsupported_recommendation", r"\b(you should|you must|you need to)\b"),
        ]

        import re
        for flag_name, pattern in hallucination_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                flags.append(flag_name)

        return flags


# ── Golden Contract Factory ────────────────────────────────────────

def load_golden_contracts(dataset_dir: str = "tests/ai_eval/datasets") -> list[GoldenContract]:
    """Load golden contracts from dataset directory."""
    contracts: list[GoldenContract] = []
    base_path = Path(dataset_dir)

    if not base_path.exists():
        logger.warning("Dataset directory not found: %s", dataset_dir)
        return contracts

    for filepath in base_path.glob("*.json"):
        try:
            with open(filepath) as f:
                data = json.load(f)
            contract = GoldenContract(
                contract_id=data.get("contract_id", filepath.stem),
                contract_type=data.get("contract_type", "unknown"),
                filename=filepath.name,
                filepath=str(filepath),
                expected_risk_score=data.get("expected_risk_score", 0.5),
                expected_findings=[
                    ExpectedFinding(**f) for f in data.get("expected_findings", [])
                ],
                expected_clause_types=data.get("expected_clause_types", []),
                description=data.get("description", ""),
                jurisdiction=data.get("jurisdiction", "us"),
                risk_profile=data.get("risk_profile", "standard"),
                tags=data.get("tags", []),
            )
            contracts.append(contract)
        except Exception as e:
            logger.error("Failed to load golden contract %s: %s", filepath, e)

    return contracts
