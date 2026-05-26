"""Confidence calibration engine with self-consistency scoring and drift alerting.

Provides self-consistency scoring across multiple LLM sampling passes,
confidence calibration against verified scores, and drift detection
when confidence drops below configurable thresholds. Integrates with
existing severity scoring.
"""

from __future__ import annotations

import json
import logging
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from llm.client import LLMClient
from llm.models import LLMRequest, LLMResponse, Message, RoleType

logger = logging.getLogger(__name__)


@dataclass
class SelfConsistencyResult:
    """Result of self-consistency scoring across multiple passes."""

    mean_score: float
    std_dev: float
    pairwise_agreement: float
    num_passes: int
    all_scores: List[float]
    consistent: bool
    consensus_label: str  # high, medium, low


@dataclass
class CalibrationSample:
    """A single calibration data point for drift tracking."""

    clause_text: str
    category_id: str
    confidence_score: float
    severity_score: int
    timestamp: datetime = field(default_factory=datetime.utcnow)
    verified: bool = False
    verified_score: Optional[float] = None


@dataclass
class DriftAlert:
    """Alert raised when confidence drift is detected."""

    alert_id: str
    metric: str
    current_value: float
    threshold: float
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    acknowledged: bool = False


class ConfidenceCalibrationEngine:
    """Confidence calibration with self-consistency scoring and drift alerting.

    Provides:
    1. Self-consistency scoring: Runs multiple LLM passes and measures agreement.
    2. Confidence calibration: Maps raw scores to calibrated confidence levels.
    3. Drift detection: Alerts when confidence drops below threshold.
    4. Integration with severity scoring for unified risk assessment.

    Usage:
        llm_client = LLMClient(...)
        engine = ConfidenceCalibrationEngine(llm_client)
        result = await engine.compute_self_consistency(clause_text, category_id)
        calibrated = engine.calibrate_confidence(result.mean_score)
        alerts = engine.check_drift()
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        num_sampling_passes: int = 3,
        consistency_threshold: float = 0.15,
        drift_window_size: int = 50,
        drift_alert_threshold: float = 0.4,
        calibration_history_size: int = 1000,
    ) -> None:
        """Initialize the confidence calibration engine.

        Args:
            llm_client: LLM client for sampling passes.
            num_sampling_passes: Number of passes for self-consistency.
            consistency_threshold: Max std dev for consistent results.
            drift_window_size: Window size for drift detection.
            drift_alert_threshold: Confidence threshold for alerts.
            calibration_history_size: Max calibration samples to retain.
        """
        self._llm_client = llm_client
        self._num_sampling_passes = max(1, num_sampling_passes)
        self._consistency_threshold = consistency_threshold
        self._drift_window_size = drift_window_size
        self._drift_alert_threshold = drift_alert_threshold
        self._calibration_history_size = calibration_history_size

        self._samples: List[CalibrationSample] = []
        self._alerts: List[DriftAlert] = []
        self._alert_counter: int = 0

    async def compute_self_consistency(
        self,
        clause_text: str,
        category_id: str,
        tenant_id: Optional[str] = None,
    ) -> SelfConsistencyResult:
        """Compute self-consistency across multiple LLM sampling passes.

        Runs the same clause through the LLM multiple times with slightly
        different temperatures and measures agreement between outputs.

        Args:
            clause_text: The clause text to analyze.
            category_id: Risk category for context.
            tenant_id: Optional tenant identifier.

        Returns:
            SelfConsistencyResult with mean score, std dev, and agreement.
        """
        if self._llm_client is None:
            # Fallback: return a default result
            return SelfConsistencyResult(
                mean_score=0.7,
                std_dev=0.0,
                pairwise_agreement=1.0,
                num_passes=1,
                all_scores=[0.7],
                consistent=True,
                consensus_label="medium",
            )

        scores: List[float] = []
        temperatures = [0.05, 0.15, 0.25]

        for i in range(min(self._num_sampling_passes, len(temperatures))):
            try:
                prompt = (
                    "Rate the severity of this contract clause on a scale of 0.0 to 1.0, "
                    "where 0.0 = no risk and 1.0 = critical risk.\n\n"
                    f"Category: {category_id}\n\n"
                    f"Clause:\n```\n{clause_text}\n```\n\n"
                    "Respond with ONLY a JSON object:\n"
                    '{"severity_score": float, "confidence": float (0.0-1.0), '
                    '"reasoning": "string"}'
                )

                request = LLMRequest(
                    messages=[Message(role=RoleType.USER, content=prompt)],
                    temperature=temperatures[i],
                    max_tokens=512,
                    tenant_id=tenant_id,
                    request_id=f"confidence_{category_id}_{i}",
                )

                response: LLMResponse = await self._llm_client.complete(request)

                # Parse the response
                try:
                    data = json.loads(response.content.strip())
                    score = float(data.get("confidence", data.get("severity_score", 0.5)))
                    scores.append(max(0.0, min(1.0, score)))
                except (json.JSONDecodeError, ValueError):
                    logger.warning(
                        "Failed to parse confidence pass %d for %s", i, category_id
                    )
                    scores.append(0.5)

            except Exception as exc:
                logger.warning("Confidence pass %d failed: %s", i, exc)
                scores.append(0.5)

        if not scores:
            scores = [0.5]

        mean_score = statistics.mean(scores)
        std_dev = statistics.stdev(scores) if len(scores) > 1 else 0.0
        consistent = std_dev <= self._consistency_threshold

        # Compute pairwise agreement
        pairwise_agreement = 1.0
        if len(scores) > 1:
            agreements = []
            for i in range(len(scores)):
                for j in range(i + 1, len(scores)):
                    diff = abs(scores[i] - scores[j])
                    agreements.append(1.0 - diff)
            pairwise_agreement = statistics.mean(agreements) if agreements else 1.0

        # Determine consensus label
        if mean_score >= 0.7 and consistent:
            consensus_label = "high"
        elif mean_score >= 0.4 and consistent:
            consensus_label = "medium"
        else:
            consensus_label = "low"

        return SelfConsistencyResult(
            mean_score=round(mean_score, 3),
            std_dev=round(std_dev, 3),
            pairwise_agreement=round(pairwise_agreement, 3),
            num_passes=len(scores),
            all_scores=[round(s, 3) for s in scores],
            consistent=consistent,
            consensus_label=consensus_label,
        )

    def calibrate_confidence(
        self,
        raw_confidence: float,
    ) -> Tuple[float, str]:
        """Calibrate a raw confidence score to a calibrated value and label.

        Applies calibration correction based on historical verification data.

        Args:
            raw_confidence: Raw confidence score (0.0-1.0).

        Returns:
            Tuple of (calibrated_score, label) where label is high/medium/low.
        """
        # Apply calibration correction based on historical bias
        calibrated = raw_confidence

        if len(self._samples) >= 10:
            verified_samples = [s for s in self._samples if s.verified]
            if verified_samples:
                # Compute calibration error
                errors = [
                    abs(s.confidence_score - (s.verified_score or s.confidence_score))
                    for s in verified_samples
                ]
                mean_error = statistics.mean(errors)
                # Apply inverse correction
                calibrated = raw_confidence - mean_error * 0.3
                calibrated = max(0.0, min(1.0, calibrated))

        # Determine label
        if calibrated >= 0.7:
            label = "high"
        elif calibrated >= 0.4:
            label = "medium"
        else:
            label = "low"

        return round(calibrated, 3), label

    def add_sample(
        self,
        clause_text: str,
        category_id: str,
        confidence_score: float,
        severity_score: int,
    ) -> None:
        """Record a calibration sample for drift tracking.

        Args:
            clause_text: The clause text.
            category_id: Risk category.
            confidence_score: The confidence score.
            severity_score: The severity score.
        """
        sample = CalibrationSample(
            clause_text=clause_text[:300],
            category_id=category_id,
            confidence_score=confidence_score,
            severity_score=severity_score,
        )
        self._samples.append(sample)

        # Trim history
        if len(self._samples) > self._calibration_history_size:
            self._samples = self._samples[-self._calibration_history_size:]

    def verify_sample(
        self,
        clause_text: str,
        verified_score: float,
    ) -> bool:
        """Mark a sample as verified (e.g., by human review).

        Args:
            clause_text: The clause text to match.
            verified_score: The verified confidence score.

        Returns:
            True if sample was found and verified.
        """
        for sample in self._samples:
            if sample.clause_text == clause_text[:300] and not sample.verified:
                sample.verified = True
                sample.verified_score = verified_score
                logger.info(
                    "Verified calibration sample: score=%.3f", verified_score
                )
                return True
        return False

    def check_drift(self) -> List[DriftAlert]:
        """Check for confidence drift and generate alerts.

        Analyzes recent samples to detect if confidence scores have
        drifted below acceptable thresholds.

        Returns:
            List of active drift alerts.
        """
        new_alerts: List[DriftAlert] = []

        if len(self._samples) < self._drift_window_size:
            return new_alerts

        # Analyze recent window
        recent = self._samples[-self._drift_window_size:]
        recent_confidences = [s.confidence_score for s in recent]
        mean_confidence = statistics.mean(recent_confidences)

        # Check against threshold
        if mean_confidence < self._drift_alert_threshold:
            self._alert_counter += 1
            alert = DriftAlert(
                alert_id=f"drift_{self._alert_counter}",
                metric="mean_confidence",
                current_value=round(mean_confidence, 3),
                threshold=self._drift_alert_threshold,
                message=(
                    f"Confidence drift detected: mean confidence {mean_confidence:.3f} "
                    f"dropped below threshold {self._drift_alert_threshold} "
                    f"in last {self._drift_window_size} samples"
                ),
            )
            self._alerts.append(alert)
            new_alerts.append(alert)
            logger.warning("Confidence drift alert: %s", alert.message)

        # Check for rapid degradation
        if len(recent) >= 20:
            first_half = statistics.mean(recent_confidences[: len(recent) // 2])
            second_half = statistics.mean(recent_confidences[len(recent) // 2:])
            if second_half < first_half - 0.2:
                self._alert_counter += 1
                alert = DriftAlert(
                    alert_id=f"drift_rapid_{self._alert_counter}",
                    metric="rapid_degradation",
                    current_value=round(second_half, 3),
                    threshold=round(first_half - 0.2, 3),
                    message=(
                        f"Rapid confidence degradation detected: "
                        f"{first_half:.3f} -> {second_half:.3f}"
                    ),
                )
                self._alerts.append(alert)
                new_alerts.append(alert)

        # Trim old alerts
        max_alerts = 100
        if len(self._alerts) > max_alerts:
            self._alerts = self._alerts[-max_alerts:]

        return new_alerts

    def get_active_alerts(self) -> List[DriftAlert]:
        """Get all unacknowledged drift alerts.

        Returns:
            List of active (unacknowledged) alerts.
        """
        return [a for a in self._alerts if not a.acknowledged]

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge a drift alert.

        Args:
            alert_id: The alert identifier.

        Returns:
            True if alert was found and acknowledged.
        """
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                return True
        return False

    def get_calibration_summary(self) -> Dict[str, Any]:
        """Get a summary of calibration state.

        Returns:
            Dict with calibration metrics and active alerts.
        """
        total = len(self._samples)
        verified = sum(1 for s in self._samples if s.verified)
        recent = self._samples[-self._drift_window_size:] if total > 0 else []

        recent_confidences = [s.confidence_score for s in recent]
        mean_confidence = statistics.mean(recent_confidences) if recent_confidences else 0.0

        return {
            "total_samples": total,
            "verified_samples": verified,
            "window_size": self._drift_window_size,
            "recent_mean_confidence": round(mean_confidence, 3),
            "alert_threshold": self._drift_alert_threshold,
            "active_alerts": len(self.get_active_alerts()),
            "total_alerts": len(self._alerts),
            "consistency_threshold": self._consistency_threshold,
        }
