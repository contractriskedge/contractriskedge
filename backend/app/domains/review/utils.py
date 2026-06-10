"""Shared helpers for the review domain."""

from typing import Optional

from app.domains.review.redline_ops import prepare_redline_display
from app.domains.review.mapping_validation import MappingValidationResult
from app.domains.review.schemas import (
    ConfidenceLabel,
    LocatorResponse,
    RedlineItem,
    RedlineMappingDetails,
    RiskTraceabilityItem,
    SourceLocation,
    WordDiffSegment,
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


def build_source_location(finding, *, chunk=None) -> Optional[SourceLocation]:
    """Create reviewer-facing source traceability from stored finding data."""
    chunk_id = None
    chunk_ids = list(getattr(finding, "chunk_ids", None) or [])
    if chunk_ids:
        chunk_id = str(chunk_ids[0])
    if chunk is not None and getattr(chunk, "chunk_id", None):
        chunk_id = str(chunk.chunk_id)

    source_text = getattr(finding, "source_text", None) or getattr(finding, "clause_text", None)
    if not source_text and chunk is not None:
        source_text = getattr(chunk, "text", None)

    page_number = getattr(finding, "page_number", None)
    if page_number is None:
        page_numbers = list(getattr(finding, "page_numbers", None) or [])
        if page_numbers:
            page_number = page_numbers[0]
        elif chunk is not None:
            chunk_pages = list(getattr(chunk, "page_numbers", None) or [])
            if chunk_pages:
                page_number = chunk_pages[0]

    section_heading = getattr(finding, "section_heading", None)
    if not section_heading and chunk is not None:
        section_heading = getattr(chunk, "section_heading", None)

    paragraph_index = getattr(finding, "paragraph_index", None)
    if paragraph_index is None and chunk is not None and getattr(chunk, "chunk_index", None) is not None:
        paragraph_index = int(chunk.chunk_index) + 1

    start = getattr(finding, "source_start_offset", None)
    end = getattr(finding, "source_end_offset", None)
    if source_text and start is None:
        start = 0
    if source_text and end is None:
        end = len(source_text)

    confidence_score = getattr(finding, "confidence_score", None)
    if confidence_score is None:
        confidence_score = getattr(finding, "confidence", None)

    if not any([page_number, section_heading, paragraph_index, source_text, chunk_id]):
        return None

    return SourceLocation(
        page_number=page_number,
        section_heading=section_heading,
        paragraph_index=paragraph_index,
        source_text=source_text,
        source_start_offset=start,
        source_end_offset=end,
        confidence_score=confidence_score,
        chunk_id=chunk_id,
    )


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
                    locator_result: Optional[dict] = None,
                    source_location: Optional[SourceLocation] = None,
                    finding_clause_type: Optional[str] = None,
                    finding_title: Optional[str] = None,
                    finding_recommendation: Optional[str] = None,
                    mapping: Optional[MappingValidationResult] = None) -> RedlineItem:
    """Build API redline DTO with operation-aware display fields, locator,
    calibrated confidence label, and risk traceability chain.

    When a linked finding exists, finding_clause_type, finding_title, and
    finding_recommendation are passed to enable client-side category validation.
    """
    proposed = redline.reviewer_modified_text or redline.proposed_text
    display = prepare_redline_display(
        redline.original_text,
        proposed,
        clause_type=redline.clause_type,
        stored_operation=getattr(redline, "operation", None),
        anchor_text=getattr(redline, "anchor_text", None) or "",
        reviewer_modified_text=redline.reviewer_modified_text,
    )
    mapping = mapping or MappingValidationResult(
        valid=True,
        mapping_status="valid",
        warning=None,
        finding_id=str(redline.finding_id) if getattr(redline, "finding_id", None) else None,
        finding_title=finding_title,
        finding_category=None,
        redline_title=redline.clause_type or "Redline",
        redline_category=redline.clause_type,
        category=finding_clause_type or redline.clause_type,
    )
    display_status = enum_value(redline.status)
    if not mapping.valid and display_status in ("proposed", "invalid_mapping"):
        display_status = "invalid_mapping"

    return RedlineItem(
        redline_id=str(redline.redline_id),
        clause_type=redline.clause_type,
        original_text=display["display_original"],
        proposed_text=proposed,
        ai_proposed_text=redline.proposed_text or None,
        finding_id=mapping.finding_id,
        finding_category=mapping.finding_category or finding_clause_type,
        finding_title=mapping.finding_title or finding_title,
        finding_recommendation=finding_recommendation,
        redline_title=mapping.redline_title,
        redline_category=mapping.redline_category,
        mapping_valid=mapping.valid,
        mapping_status=mapping.mapping_status,
        mapping_warning=mapping.warning,
        mapping_details=RedlineMappingDetails(
            finding_title=mapping.finding_title,
            redline_title=mapping.redline_title,
            category=mapping.category,
            finding_category=mapping.finding_category,
            redline_category=mapping.redline_category,
        ),
        operation=display["operation"],
        anchor_text=display["anchor_text"] or None,
        context_excerpt=display["context_excerpt"],
        chunk_ids=chunk_ids or [],
        word_diff=[WordDiffSegment(**seg) for seg in display["word_diff"]],
        rationale=redline.rationale,
        risk_level=redline.risk_level,
        confidence=redline.confidence,
        confidence_label=_build_confidence_label(redline.confidence),
        status=display_status,
        reviewer_modified_text=redline.reviewer_modified_text,
        reviewed_by=redline.reviewed_by,
        reviewed_at=redline.reviewed_at,
        created_at=redline.created_at,
        locator=LocatorResponse(**(locator_result or {})) if locator_result else None,
        source_location=source_location,
        traceability=_extract_traceability(redline),
    )
