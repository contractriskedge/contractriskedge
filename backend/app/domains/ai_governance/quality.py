"""AI Quality Governance V2 — hallucination detection, semantic regression, explanation quality, benchmark gates.

Extends the Sprint 8 AI Governance layer with production-grade quality controls.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.ai_governance.schemas import (
    TestOutcome, TestCaseResult, EvaluationRunResponse,
)

logger = logging.getLogger(__name__)


# ── Hallucination Detection ─────────────────────────────────────────


@dataclass
class HallucinationDetector:
    """Detects hallucinations in AI outputs by verifying claims against source text.

    Uses a multi-strategy approach:
    1. Claim extraction — split AI output into verifiable claims
    2. Source grounding — check each claim against source clause text
    3. Consistency scoring — measure agreement across multiple dimensions
    """

    @staticmethod
    def extract_claims(text: str) -> list[str]:
        """Extract verifiable claims from AI output text."""
        import re
        claims: list[str] = []

        # Split by sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Filter out non-claim sentences (questions, greetings, etc.)
            if sentence.endswith('?') or len(sentence) < 20:
                continue

            # Extract claim-worthy patterns
            if any(keyword in sentence.lower() for keyword in [
                'this clause', 'the contract', 'this provision', 'section',
                'the agreement', 'the party', 'the obligation', 'the risk',
                'the liability', 'the indemnity', 'the warranty',
            ]):
                claims.append(sentence)

        return claims[:20]  # Limit to prevent explosion

    @staticmethod
    def verify_claim(claim: str, source_text: str) -> tuple[bool, float]:
        """Verify a claim against source text. Returns (supported, confidence)."""
        if not source_text:
            return False, 0.0

        # Normalize
        claim_lower = claim.lower()
        source_lower = source_text.lower()

        # Extract key terms from claim (skip common words)
        import re
        claim_words = set(re.findall(r'\b[a-z]{4,}\b', claim_lower))
        source_words = set(re.findall(r'\b[a-z]{4,}\b', source_lower))

        if not claim_words:
            return False, 0.0

        # Check term overlap
        overlap = claim_words & source_words
        overlap_ratio = len(overlap) / len(claim_words) if claim_words else 0

        # Check for direct phrase matches
        phrases = re.findall(r'([a-z]+\s+[a-z]+\s+[a-z]+)', claim_lower)
        phrase_matches = sum(1 for p in phrases if p in source_lower)
        phrase_ratio = phrase_matches / len(phrases) if phrases else 0

        # Combined score
        confidence = (overlap_ratio * 0.6 + phrase_ratio * 0.4)
        supported = confidence >= 0.35

        return supported, round(confidence, 4)

    @staticmethod
    def detect_hallucinations(
        ai_output: str,
        source_text: str,
    ) -> dict[str, Any]:
        """Run full hallucination detection pipeline."""
        claims = HallucinationDetector.extract_claims(ai_output)
        if not claims:
            return {
                "total_claims": 0,
                "supported_claims": 0,
                "unsupported_claims": 0,
                "grounding_score": 1.0,
                "claims": [],
                "has_hallucinations": False,
            }

        results: list[dict] = []
        supported_count = 0

        for claim in claims:
            is_supported, confidence = HallucinationDetector.verify_claim(claim, source_text)
            results.append({
                "claim": claim,
                "supported": is_supported,
                "confidence": confidence,
            })
            if is_supported:
                supported_count += 1

        grounding_score = supported_count / len(claims) if claims else 1.0

        return {
            "total_claims": len(claims),
            "supported_claims": supported_count,
            "unsupported_claims": len(claims) - supported_count,
            "grounding_score": round(grounding_score, 4),
            "claims": results,
            "has_hallucinations": grounding_score < 0.7,
        }


# ── Semantic Regression Testing ─────────────────────────────────────


@dataclass
class SemanticRegressionTester:
    """Compares old vs new AI outputs to detect regressions."""

    @staticmethod
    def compare_outputs(
        old_output: str,
        new_output: str,
        expected_output: Optional[str] = None,
    ) -> dict[str, Any]:
        """Compare two AI outputs and detect semantic regressions."""
        import re

        def extract_key_findings(text: str) -> set[str]:
            """Extract key findings/claims as normalized phrases."""
            findings = set()
            for line in text.split('\n'):
                line = line.strip().lower()
                # Extract finding-like patterns
                if any(kw in line for kw in ['risk', 'clause', 'severity', 'missing', 'recommend']):
                    # Normalize: remove punctuation, collapse whitespace
                    normalized = re.sub(r'[^\w\s]', '', line)
                    normalized = re.sub(r'\s+', ' ', normalized).strip()
                    if len(normalized) > 20:
                        findings.add(normalized[:200])
            return findings

        old_findings = extract_key_findings(old_output)
        new_findings = extract_key_findings(new_output)

        # Findings added
        added = new_findings - old_findings
        # Findings removed
        removed = old_findings - new_findings
        # Findings retained
        retained = old_findings & new_findings

        # Semantic similarity score
        total = len(old_findings | new_findings)
        similarity = len(retained) / total if total > 0 else 1.0

        # Regression detection
        regressions: list[str] = []
        improvements: list[str] = []

        for r in removed:
            regressions.append(f"Previously reported finding no longer present: {r[:100]}...")
        for a in added:
            improvements.append(f"New finding detected: {a[:100]}...")

        # If expected output is provided, check against it
        expected_match = None
        if expected_output:
            expected_findings = extract_key_findings(expected_output)
            missing_expected = expected_findings - new_findings
            expected_match = {
                "matched": len(missing_expected) == 0,
                "missing_count": len(missing_expected),
                "missing": list(missing_expected)[:5],
            }

        has_regression = similarity < 0.6 or len(regressions) > 2

        return {
            "similarity_score": round(similarity, 4),
            "old_finding_count": len(old_findings),
            "new_finding_count": len(new_findings),
            "findings_added": len(added),
            "findings_removed": len(removed),
            "findings_retained": len(retained),
            "regressions": regressions[:10],
            "improvements": improvements[:10],
            "has_regression": has_regression,
            "expected_match": expected_match,
        }


# ── Explanation Quality Scoring ─────────────────────────────────────


@dataclass
class ExplanationQualityScorer:
    """Scores the quality of AI-generated explanations and rationales."""

    @staticmethod
    def score_explanation(
        explanation: str,
        context: Optional[str] = None,
    ) -> dict[str, Any]:
        """Score the quality of an AI explanation."""
        import re

        if not explanation:
            return {
                "score": 0.0,
                "has_explanation": False,
                "dimensions": {},
                "issues": ["No explanation provided"],
            }

        # Dimension 1: Completeness — does it explain WHY?
        has_causal_language = any(word in explanation.lower() for word in [
            'because', 'therefore', 'since', 'due to', 'as a result',
            'leads to', 'causes', 'results in', 'consequently',
        ])

        # Dimension 2: Specificity — does it reference specific clauses/terms?
        specific_terms = re.findall(r'\b(?:section|clause|paragraph|article|term|provision)\s+\d+', explanation.lower())
        has_specific_refs = len(specific_terms) > 0

        # Dimension 3: Actionability — does it recommend action?
        has_recommendation = any(word in explanation.lower() for word in [
            'recommend', 'suggest', 'should', 'consider', 'propose',
            'mitigate', 'address', 'review', 'modify',
        ])

        # Dimension 4: Evidence grounding — does it reference source?
        has_evidence = any(word in explanation.lower() for word in [
            'according to', 'based on', 'as stated in', 'per the',
            'references', 'cites', 'from the contract',
        ])

        # Dimension 5: Conciseness — reasonable length
        word_count = len(explanation.split())
        is_concise = 20 <= word_count <= 200

        # Compute scores
        completeness = 1.0 if has_causal_language else 0.3
        specificity = 1.0 if has_specific_refs else 0.2
        actionability = 1.0 if has_recommendation else 0.3
        evidence = 1.0 if has_evidence else 0.2
        conciseness = 1.0 if is_concise else (0.5 if word_count < 300 else 0.3)

        dimensions = {
            "completeness": round(completeness, 2),
            "specificity": round(specificity, 2),
            "actionability": round(actionability, 2),
            "evidence_grounding": round(evidence, 2),
            "conciseness": round(conciseness, 2),
        }

        # Overall score (weighted)
        weights = {"completeness": 0.3, "specificity": 0.25, "actionability": 0.2, "evidence_grounding": 0.15, "conciseness": 0.1}
        overall = sum(dimensions[k] * weights[k] for k in weights)

        issues = []
        if not has_causal_language:
            issues.append("Missing causal reasoning — does not explain WHY")
        if not has_specific_refs:
            issues.append("Missing specific clause/section references")
        if not has_recommendation:
            issues.append("Missing actionable recommendation")
        if not has_evidence:
            issues.append("Missing source evidence grounding")
        if not is_concise:
            issues.append(f"Explanation length ({word_count} words) could be optimized")

        return {
            "score": round(overall, 4),
            "has_explanation": True,
            "dimensions": dimensions,
            "issues": issues,
            "word_count": word_count,
        }


# ── Benchmark Regression Gates ──────────────────────────────────────


@dataclass
class BenchmarkGateService:
    """Evaluates quality metrics against thresholds to block or allow deployments."""

    session: AsyncSession
    tenant_id: str

    # Default quality thresholds
    MIN_PASS_RATE: float = 0.80          # 80% of tests must pass
    MAX_HALLUCINATION_RATE: float = 0.15  # Max 15% hallucination rate
    MIN_EXPLANATION_QUALITY: float = 0.50  # Min 0.5 explanation quality score
    MAX_REGRESSION_COUNT: int = 3         # Max 3 regressions allowed

    async def evaluate_gate(
        self,
        prompt_key: str,
        new_version: int,
        evaluation_run_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Evaluate whether a prompt version passes quality gates."""
        results: dict[str, Any] = {
            "prompt_key": prompt_key,
            "new_version": new_version,
            "overall_passed": False,
            "gates": [],
            "summary": "",
        }

        gate_results: list[dict] = []
        all_passed = True

        # Gate 1: Evaluation pass rate
        if evaluation_run_id:
            gate1 = await self._check_pass_rate_gate(evaluation_run_id)
            gate_results.append(gate1)
            if not gate1["passed"]:
                all_passed = False

        # Gate 2: Compare with previous version
        if new_version > 1:
            gate2 = await self._check_regression_gate(prompt_key, new_version)
            gate_results.append(gate2)
            if not gate2["passed"]:
                all_passed = False

        # Gate 3: Check for critical failures in recent runs
        gate3 = await self._check_critical_failures_gate(prompt_key)
        gate_results.append(gate3)
        if not gate3["passed"]:
            all_passed = False

        results["gates"] = gate_results
        results["overall_passed"] = all_passed
        results["summary"] = "All quality gates passed" if all_passed else f"{sum(1 for g in gate_results if not g['passed'])} gate(s) failed"

        return results

    async def _check_pass_rate_gate(self, run_id: str) -> dict[str, Any]:
        """Check if evaluation pass rate meets minimum threshold."""
        sql = sa_text("""
            SELECT total_tests, passed, failed, pass_rate
            FROM eval_runs WHERE run_id = :rid
        """)
        result = await self.session.execute(sql, {"rid": run_id})
        row = result.fetchone()

        if not row:
            return {"gate": "pass_rate", "passed": False, "reason": "Evaluation run not found"}

        pass_rate = row.pass_rate or 0.0
        passed = pass_rate >= self.MIN_PASS_RATE

        return {
            "gate": "pass_rate",
            "passed": passed,
            "pass_rate": pass_rate,
            "threshold": self.MIN_PASS_RATE,
            "reason": f"Pass rate {pass_rate:.1%} meets threshold {self.MIN_PASS_RATE:.0%}" if passed else f"Pass rate {pass_rate:.1%} below threshold {self.MIN_PASS_RATE:.0%}",
        }

    async def _check_regression_gate(self, prompt_key: str, new_version: int) -> dict[str, Any]:
        """Check if new version introduces regressions compared to previous."""
        # Get previous version's evaluation
        sql = sa_text("""
            SELECT pass_rate, total_tests, passed
            FROM eval_runs
            WHERE prompt_key = :key AND prompt_version = :ver
            ORDER BY created_at DESC LIMIT 1
        """)
        prev = await self.session.execute(sql, {"key": prompt_key, "ver": new_version - 1})
        prev_row = prev.fetchone()

        current = await self.session.execute(sql, {"key": prompt_key, "ver": new_version})
        current_row = current.fetchone()

        if not prev_row or not current_row:
            return {"gate": "regression", "passed": True, "reason": "Insufficient data for regression comparison"}

        delta = (current_row.pass_rate or 0.0) - (prev_row.pass_rate or 0.0)
        passed = delta >= -0.05  # Allow 5% degradation

        return {
            "gate": "regression",
            "passed": passed,
            "previous_pass_rate": prev_row.pass_rate,
            "current_pass_rate": current_row.pass_rate,
            "delta": round(delta, 4),
            "reason": f"Pass rate stable/improved (Δ={delta:+.1%})" if passed else f"Pass rate degraded (Δ={delta:+.1%})",
        }

    async def _check_critical_failures_gate(self, prompt_key: str) -> dict[str, Any]:
        """Check for critical failures in recent evaluation runs."""
        sql = sa_text("""
            SELECT COUNT(*)::int AS failures
            FROM model_audit_log
            WHERE prompt_key = :key
              AND success = FALSE
              AND created_at > NOW() - INTERVAL '24 hours'
        """)
        result = await self.session.execute(sql, {"key": prompt_key})
        row = result.fetchone()
        failures = row.failures if row else 0

        passed = failures < 5  # Less than 5 failures in 24h

        return {
            "gate": "critical_failures",
            "passed": passed,
            "failures_24h": failures,
            "threshold": 5,
            "reason": f"{failures} failures in 24h within acceptable range" if passed else f"{failures} failures in 24h exceeds threshold",
        }
