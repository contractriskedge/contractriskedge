"""Calibration validation and drift detection for severity scoring.

Monitors severity score calibration over time, detects drift in
scoring patterns, and provides validation against known benchmarks.
"""

from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from .severity import SeverityResult

logger = logging.getLogger(__name__)


@dataclass
class CalibrationSample:
    """A single calibration data point."""

    clause_text: str
    category_id: str
    predicted_score: int
    predicted_confidence: str
    actual_score: Optional[int]  # None if unverified
    timestamp: datetime = field(default_factory=datetime.utcnow)
    verified_by: Optional[str] = None  # Human reviewer if verified


@dataclass
class CalibrationReport:
    """Report on severity score calibration."""

    total_samples: int
    verified_samples: int
    mean_error: float
    mean_absolute_error: float
    root_mean_squared_error: float
    accuracy_within_1: float  # % of predictions within 1 point
    accuracy_within_2: float  # % of predictions within 2 points
    confidence_distribution: Dict[str, float]
    drift_detected: bool
    drift_severity: str  # none, minor, moderate, severe
    recommendations: List[str]


class CalibrationValidator:
    """Validates severity score calibration and detects drift.

    Tracks severity score predictions against verified scores,
    computes calibration metrics, and alerts when scoring patterns
    drift beyond acceptable thresholds.

    Usage:
        validator = CalibrationValidator()
        validator.add_sample(clause_text, "indemnification", 7, "high")
        validator.verify_sample(clause_text, actual_score=6)
        report = validator.generate_report()
    """

    def __init__(
        self,
        max_samples: int = 10_000,
        drift_window_days: int = 7,
        mae_threshold: float = 1.5,
    ) -> None:
        """Initialize the calibration validator.

        Args:
            max_samples: Maximum number of samples to retain.
            drift_window_days: Window for drift detection.
            mae_threshold: MAE threshold for drift alert.
        """
        self._samples: List[CalibrationSample] = []
        self._max_samples = max_samples
        self._drift_window_days = drift_window_days
        self._mae_threshold = mae_threshold
        self._category_stats: Dict[str, List[float]] = {}

    def add_sample(
        self,
        clause_text: str,
        category_id: str,
        predicted_score: int,
        predicted_confidence: str,
    ) -> None:
        """Record a severity prediction sample.

        Args:
            clause_text: The clause that was scored.
            category_id: Risk category.
            predicted_score: The predicted severity score (1-10).
            predicted_confidence: Confidence level (high/medium/low).
        """
        sample = CalibrationSample(
            clause_text=clause_text[:500],  # Truncate for storage
            category_id=category_id,
            predicted_score=predicted_score,
            predicted_confidence=predicted_confidence,
        )
        self._samples.append(sample)

        # Track category stats
        if category_id not in self._category_stats:
            self._category_stats[category_id] = []
        self._category_stats[category_id].append(float(predicted_score))

        # Prune if over limit
        if len(self._samples) > self._max_samples:
            self._samples = self._samples[-self._max_samples:]

        logger.debug(
            "Calibration sample added: %s score=%d confidence=%s",
            category_id,
            predicted_score,
            predicted_confidence,
        )

    def verify_sample(
        self,
        clause_text: str,
        actual_score: int,
        verified_by: Optional[str] = None,
    ) -> bool:
        """Verify a prediction with an actual score.

        Args:
            clause_text: The clause text to match.
            actual_score: The verified actual score.
            verified_by: Optional identifier of the verifier.

        Returns:
            True if a matching sample was found and updated.
        """
        for sample in self._samples:
            if sample.clause_text == clause_text[:500] and sample.actual_score is None:
                sample.actual_score = actual_score
                sample.verified_by = verified_by
                logger.info(
                    "Sample verified: score=%d (was %d) by %s",
                    actual_score,
                    sample.predicted_score,
                    verified_by or "unknown",
                )
                return True

        logger.warning("No unverified sample found matching clause text")
        return False

    def generate_report(self) -> CalibrationReport:
        """Generate a calibration report.

        Computes accuracy metrics and drift detection.

        Returns:
            CalibrationReport with all metrics.
        """
        verified = [s for s in self._samples if s.actual_score is not None]

        if not verified:
            return CalibrationReport(
                total_samples=len(self._samples),
                verified_samples=0,
                mean_error=0.0,
                mean_absolute_error=0.0,
                root_mean_squared_error=0.0,
                accuracy_within_1=0.0,
                accuracy_within_2=0.0,
                confidence_distribution=self._get_confidence_distribution(),
                drift_detected=False,
                drift_severity="none",
                recommendations=["Collect verified samples to enable calibration analysis"],
            )

        errors = [s.predicted_score - s.actual_score for s in verified]
        abs_errors = [abs(e) for e in errors]

        mae = statistics.mean(abs_errors)
        rmse = statistics.sqrt(statistics.mean(e ** 2 for e in errors))
        within_1 = sum(1 for e in abs_errors if e <= 1) / len(abs_errors)
        within_2 = sum(1 for e in abs_errors if e <= 2) / len(abs_errors)

        # Drift detection
        drift_detected, drift_severity = self._detect_drift(verified)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            mae, within_1, drift_detected, drift_severity
        )

        return CalibrationReport(
            total_samples=len(self._samples),
            verified_samples=len(verified),
            mean_error=statistics.mean(errors),
            mean_absolute_error=mae,
            root_mean_squared_error=rmse,
            accuracy_within_1=within_1,
            accuracy_within_2=within_2,
            confidence_distribution=self._get_confidence_distribution(),
            drift_detected=drift_detected,
            drift_severity=drift_severity,
            recommendations=recommendations,
        )

    def _detect_drift(
        self, verified: List[CalibrationSample]
    ) -> Tuple[bool, str]:
        """Detect scoring drift over time.

        Compares recent MAE against historical MAE.

        Args:
            verified: List of verified samples.

        Returns:
            Tuple of (drift_detected, severity).
        """
        cutoff = datetime.utcnow() - timedelta(days=self._drift_window_days)

        recent = [s for s in verified if s.timestamp >= cutoff]
        historical = [s for s in verified if s.timestamp < cutoff]

        if len(recent) < 10 or len(historical) < 10:
            return False, "none"  # Insufficient data

        recent_mae = statistics.mean(
            abs(s.predicted_score - s.actual_score) for s in recent
        )
        historical_mae = statistics.mean(
            abs(s.predicted_score - s.actual_score) for s in historical
        )

        if recent_mae <= historical_mae:
            return False, "none"

        drift_ratio = recent_mae / historical_mae if historical_mae > 0 else 1.0

        if drift_ratio > 1.5:
            return True, "severe"
        elif drift_ratio > 1.25:
            return True, "moderate"
        elif drift_ratio > 1.1:
            return True, "minor"

        return False, "none"

    def _get_confidence_distribution(self) -> Dict[str, float]:
        """Get the distribution of confidence levels.

        Returns:
            Dict mapping confidence level to proportion.
        """
        if not self._samples:
            return {"high": 0.0, "medium": 0.0, "low": 0.0}

        counts: Dict[str, int] = {"high": 0, "medium": 0, "low": 0}
        for s in self._samples:
            conf = s.predicted_confidence.lower()
            if conf in counts:
                counts[conf] += 1

        total = sum(counts.values())
        return {
            k: round(v / total, 3) if total > 0 else 0.0
            for k, v in counts.items()
        }

    def _generate_recommendations(
        self,
        mae: float,
        accuracy_within_1: float,
        drift_detected: bool,
        drift_severity: str,
    ) -> List[str]:
        """Generate calibration improvement recommendations.

        Args:
            mae: Mean absolute error.
            accuracy_within_1: Proportion within 1 point.
            drift_detected: Whether drift was detected.
            drift_severity: Severity of drift.

        Returns:
            List of recommendation strings.
        """
        recommendations: list[str] = []

        if mae > self._mae_threshold:
            recommendations.append(
                f"MAE of {mae:.2f} exceeds threshold of {self._mae_threshold}. "
                "Review scoring guidelines and consider recalibration."
            )

        if accuracy_within_1 < 0.6:
            recommendations.append(
                f"Only {accuracy_within_1:.1%} of predictions within 1 point. "
                "Target is 70%+. Review scoring consistency."
            )

        if drift_detected:
            recommendations.append(
                f"Scoring drift detected ({drift_severity}). "
                "Investigate recent changes in scoring patterns."
            )

        if self._get_confidence_distribution().get("high", 0) > 0.8:
            recommendations.append(
                "Over 80% of predictions are high confidence. Consider whether "
                "confidence calibration is accurate."
            )

        verified_count = sum(1 for s in self._samples if s.actual_score is not None)
        if verified_count < 50:
            recommendations.append(
                f"Only {verified_count} verified samples. Target 100+ for "
                "reliable calibration metrics."
            )

        # Category-specific recommendations
        for cat_id, scores in self._category_stats.items():
            if len(scores) >= 10:
                cat_std = statistics.stdev(scores) if len(scores) > 1 else 0
                if cat_std < 0.5:
                    recommendations.append(
                        f"Category '{cat_id}' shows very low score variance "
                        f"(std={cat_std:.2f}). Scores may not be discriminating."
                    )

        if not recommendations:
            recommendations.append("Calibration is within acceptable parameters.")

        return recommendations

    def get_category_calibration(
        self, category_id: str
    ) -> Dict[str, Any]:
        """Get calibration metrics for a specific category.

        Args:
            category_id: The risk category.

        Returns:
            Dict with category-specific calibration data.
        """
        category_samples = [
            s for s in self._samples
            if s.category_id == category_id and s.actual_score is not None
        ]

        if not category_samples:
            return {
                "category_id": category_id,
                "sample_count": 0,
                "message": "No verified samples for this category",
            }

        errors = [
            s.predicted_score - s.actual_score for s in category_samples
        ]
        abs_errors = [abs(e) for e in errors]

        return {
            "category_id": category_id,
            "sample_count": len(category_samples),
            "mean_error": round(statistics.mean(errors), 3),
            "mae": round(statistics.mean(abs_errors), 3),
            "accuracy_within_1": round(
                sum(1 for e in abs_errors if e <= 1) / len(abs_errors), 3
            ),
            "avg_predicted": round(
                statistics.mean(s.predicted_score for s in category_samples), 2
            ),
            "avg_actual": round(
                statistics.mean(s.actual_score for s in category_samples), 2
            ),
        }

    @property
    def total_samples(self) -> int:
        """Get total number of calibration samples.

        Returns:
            Sample count.
        """
        return len(self._samples)

    @property
    def verified_count(self) -> int:
        """Get number of verified samples.

        Returns:
            Verified sample count.
        """
        return sum(1 for s in self._samples if s.actual_score is not None)
