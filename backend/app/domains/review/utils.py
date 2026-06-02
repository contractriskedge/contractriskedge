"""Shared helpers for the review domain."""

from typing import Optional

from app.domains.review.redline_ops import prepare_redline_display
from app.domains.review.schemas import (
    ConfidenceLabel, LocatorResponse, RedlineItem, RiskTraceabilityItem, WordDiffSegment,
)


def enum_value(v):
    """Safely extract value from a potentially mixed enum/str field."""
    if v is None:
        return None
    return v.value if hasattr(v, "value") else str(v)


def _build_confidence_label(confidence: Optional[float]) -> Optional[ConfidenceLabel]:
    """Convert a numeric confidence score to a human-readable semantic label.

    Tiers are calibrated to match our deterministic confidence scoring in service.py:
      Very High  0.90+   Exact modification or high-severity anchor with strong signals
      High       0.75–0.89  Known anchor text present
      Medium     0.55–0.74  Topology-guided insert or medium-severity modification
      Low        0.35–0.54  Fallback / heuristic placement
      Uncertain  <0.35   Could not determine reliable placement
    """
    if confidence is None:
        return None
    c = float(confidence)
    if c >= 0.90:
        return ConfidenceLabel(label="Very High", tier="very_high", numeric=c)
    if c >= 0.75:
        return ConfidenceLabel(label="High", tier="high", numeric=c)
    if c >= 0.55:
        return ConfidenceLabel(label="Medium", tier="medium", numeric=c)
    if c >= 0.35:
        return ConfidenceLabel(label="Low", tier="low", numeric=c)
    return ConfidenceLabel(label="Uncertain", tier="uncertain", numeric=c)


def _extract_traceability(redline) -> Optional[RiskTraceabilityItem]:
    """Pull risk traceability chain out of the redline's JSONB metadata.

    Supports both:
    - AI-generated findings (detected_risk, business_impact, mitigation_strategy)
    - Mitigation-generated redlines (+ mitigation_type, estimated_reduction_pct, etc.)
    """
    meta = getattr(redline, "redline_metadata", None)
    if not meta or not isinstance(meta, dict):
        return None
    trace = meta.get("traceability")
    if not trace or not isinstance(trace, dict):
        return None
    detected = trace.get("detected_risk", "").strip()
    impact = trace.get("business_impact", "").strip()
    mitigation = trace.get("mitigation_strategy", "").strip()
    if not any([detected, impact, mitigation]):
        return None
    return RiskTraceabilityItem(
        detected_risk=detected,
        business_impact=impact,
        mitigation_strategy=mitigation,
        mitigation_type=trace.get("mitigation_type"),
        estimated_reduction_pct=trace.get("mitigation_effectiveness_pct"),
        confidence=trace.get("mitigation_confidence"),
        source=trace.get("mitigation_source"),
        generated_from=trace.get("generated_from"),
    )


def redline_to_item(redline, *, chunk_ids: Optional[list[str]] = None,
                    locator_result: Optional[dict] = None) -> RedlineItem:
    """Build API redline DTO with operation-aware display fields, locator,
    calibrated confidence label, and risk traceability chain."""
    proposed = redline.reviewer_modified_text or redline.proposed_text
    display = prepare_redline_display(
        redline.original_text,
        proposed,
        clause_type=redline.clause_type,
        stored_operation=getattr(redline, "operation", None),
        anchor_text=getattr(redline, "anchor_text", None) or "",
        reviewer_modified_text=redline.reviewer_modified_text,
    )
    return RedlineItem(
        redline_id=str(redline.redline_id),
        clause_type=redline.clause_type,
        original_text=display["display_original"],
        proposed_text=proposed,
        ai_proposed_text=redline.proposed_text or None,
        finding_id=str(redline.finding_id) if getattr(redline, "finding_id", None) else None,
        operation=display["operation"],
        anchor_text=display["anchor_text"] or None,
        context_excerpt=display["context_excerpt"],
        chunk_ids=chunk_ids or [],
        word_diff=[WordDiffSegment(**seg) for seg in display["word_diff"]],
        rationale=redline.rationale,
        risk_level=redline.risk_level,
        confidence=redline.confidence,
        confidence_label=_build_confidence_label(redline.confidence),
        status=enum_value(redline.status),
        reviewer_modified_text=redline.reviewer_modified_text,
        reviewed_by=redline.reviewed_by,
        reviewed_at=redline.reviewed_at,
        created_at=redline.created_at,
        locator=LocatorResponse(**(locator_result or {})) if locator_result else None,
        traceability=_extract_traceability(redline),
    )
