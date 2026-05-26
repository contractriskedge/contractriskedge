"""Contract redlining and version comparison API endpoints.

Provides endpoints for comparing contract versions, generating
redline diffs, AI-powered redline suggestions, and tracking
contract changes over time.
"""

from __future__ import annotations

import difflib
import json
import logging
import os
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from middleware.auth import TokenPayload, get_current_user, require_permission, Permissions
from redline.models import (
    RedlineRequest,
    RedlineResponse,
    RedlineSuggestion,
    ClauseType,
    PartyRole,
    DealSizeTier,
    Industry,
    CounterpartyAggressiveness,
)
from redline.prompts import RedlinePromptTemplates
from redline.formatter import RedlineFormatter
from redline.quality_constraints import QualityConstraintEngine, QualityConstraintViolation
from redline.status_tracker import StatusTracker, RedlineStatus
from redline.diff_engine import DiffEngine
from llm.client import LLMClient
from llm.models import LLMRequest, Message, RoleType

load_dotenv()

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/redlines", tags=["Redlines"])


# In-memory store for development
_redline_results: Dict[str, Dict[str, Any]] = {}
_redline_suggestions: Dict[str, RedlineSuggestion] = {}

# Service instances
_prompt_templates = RedlinePromptTemplates()
_formatter = RedlineFormatter()
_quality_engine = QualityConstraintEngine()
_status_tracker = StatusTracker()
_diff_engine = DiffEngine()

# LLM client instance (lazy-initialized)
_llm_client: Optional[LLMClient] = None


def _get_llm_client() -> LLMClient:
    """Get or create the LLM client singleton.

    Uses DeepSeek as primary with OpenAI as fallback.
    Falls back to template-based generation if no keys configured.

    Returns:
        Configured LLM client instance.
    """
    global _llm_client
    if _llm_client is None:
        deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")
        openai_key = os.getenv("OPENAI_API_KEY", "")
        if deepseek_key or openai_key:
            _llm_client = LLMClient(
                deepseek_key=deepseek_key,
                openai_key=openai_key,
            )
            logger.info(
                "LLM client initialized: primary=DeepSeek, fallback=%s",
                "OpenAI" if openai_key else "None",
            )
        else:
            logger.warning("No LLM API keys configured; using template-based generation")
            _llm_client = None  # Sentinel for template-based fallback
    return _llm_client


def seed_sample_suggestions() -> int:
    """Seed sample redline suggestions for development/demo.

    Creates a set of predefined redline suggestions so the Legal Review
    page has data to display without requiring LLM calls.

    Returns:
        Number of suggestions seeded.
    """
    global _redline_suggestions
    if _redline_suggestions:
        return 0  # Already seeded

    from datetime import datetime, timedelta

    samples = [
        {
            "contract_id": "c0000001-0000-0000-0000-000000000001",
            "clause_type": "indemnification",
            "original_text": "The Supplier shall indemnify, defend, and hold harmless the Customer from and against any and all claims, damages, losses, liabilities, and expenses arising out of or related to any breach of this Agreement by the Supplier.",
            "proposed_text": "The Supplier shall indemnify, defend, and hold harmless the Customer, its affiliates, and their respective officers, directors, and employees from and against any and all claims, damages, losses, liabilities, and expenses arising out of or relating to any breach of this Agreement by the Supplier or its subcontractors.",
            "change_type": "modification",
            "rationale": "Broadened indemnification scope to cover affiliates and subcontractors, providing comprehensive protection for the Customer. Added explicit coverage for officers, directors, and employees to align with industry standards.",
            "confidence": 0.88,
            "risk_impact": "high",
        },
        {
            "contract_id": "c0000001-0000-0000-0000-000000000001",
            "clause_type": "liability_caps",
            "original_text": "In no event shall either party be liable for any indirect, incidental, special, consequential, or punitive damages, regardless of the theory of liability.",
            "proposed_text": "In no event shall either party be liable for any indirect, incidental, special, consequential, or punitive damages, regardless of the theory of liability; provided, however, that this limitation shall not apply to (a) either party's indemnification obligations, (b) either party's breach of confidentiality obligations, or (c) the Customer's non-payment of fees.",
            "change_type": "modification",
            "rationale": "Added standard exceptions to the exclusion of damages for indemnification, confidentiality breaches, and payment obligations. This prevents the limitation from applying to the most critical liability areas.",
            "confidence": 0.92,
            "risk_impact": "high",
        },
        {
            "contract_id": "c0000001-0000-0000-0000-000000000001",
            "clause_type": "termination_rights",
            "original_text": "This Agreement may be terminated by either party upon 30 days written notice to the other party.",
            "proposed_text": "This Agreement may be terminated by either party: (a) upon 30 days written notice to the other party; (b) immediately by the Customer if the Supplier materially breaches this Agreement and fails to cure within 15 days; or (c) immediately by either party if the other party becomes insolvent or files for bankruptcy.",
            "change_type": "modification",
            "rationale": "Added termination for cause with cure period and immediate termination for insolvency. These provisions protect the Customer's interests in case of Supplier default while providing a fair cure period.",
            "confidence": 0.85,
            "risk_impact": "medium",
        },
        {
            "contract_id": "c0000001-0000-0000-0000-000000000001",
            "clause_type": "confidentiality",
            "original_text": "The Receiving Party shall maintain strict confidentiality of all Confidential Information disclosed by the Disclosing Party.",
            "proposed_text": "The Receiving Party shall maintain strict confidentiality of all Confidential Information disclosed by the Disclosing Party and shall not use or disclose such information except as expressly permitted herein. Confidential Information shall include, without limitation, trade secrets, business plans, customer data, financial information, and technical data. This obligation shall survive termination of this Agreement for a period of five (5) years.",
            "change_type": "modification",
            "rationale": "Expanded confidentiality definition to include specific categories of protected information. Added explicit survival period of 5 years post-termination to ensure ongoing protection of sensitive information.",
            "confidence": 0.90,
            "risk_impact": "medium",
        },
        {
            "contract_id": "c0000001-0000-0000-0000-000000000001",
            "clause_type": "payment_terms",
            "original_text": "The Customer shall pay the Supplier the agreed upon fees within 30 days of receipt of invoice.",
            "proposed_text": "The Customer shall pay the Supplier the agreed upon fees within 45 days of receipt of invoice. All invoices shall include detailed supporting documentation. The Supplier may not increase fees by more than 3% annually without the Customer's prior written consent.",
            "change_type": "modification",
            "rationale": "Extended payment terms from 30 to 45 days to improve Customer cash flow. Added requirement for supporting documentation and a 3% annual fee increase cap to provide cost predictability.",
            "confidence": 0.82,
            "risk_impact": "low",
        },
    ]

    count = 0
    for s in samples:
        suggestion = RedlineSuggestion(
            contract_id=s["contract_id"],
            clause_type=s["clause_type"],
            original_text=s["original_text"],
            proposed_text=s["proposed_text"],
            change_type=s["change_type"],
            rationale=s["rationale"],
            confidence=s["confidence"],
            risk_impact=s["risk_impact"],
        )
        _redline_suggestions[suggestion.suggestion_id] = suggestion
        _status_tracker.add_suggestion(suggestion)
        count += 1

    logger.info("Seeded %d sample redline suggestions for development", count)
    return count


@router.post("/compare", status_code=status.HTTP_201_CREATED)
async def compare_contract_versions(
    request: Request,
    source_contract_id: str = Query(..., description="Original contract version"),
    target_contract_id: str = Query(..., description="New contract version"),
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_REDLINES)),
) -> Dict[str, Any]:
    """Compare two versions of a contract and generate a redline diff.

    Args:
        request: FastAPI request (used to access app state).
        source_contract_id: The original/base contract version.
        target_contract_id: The new/modified contract version.
        user: Authenticated user.

    Returns:
        Dict with comparison_id and diff results.

    Raises:
        HTTPException: If contracts not found or inaccessible.
    """
    repo = request.app.state.db_repo
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not available",
        )

    source = await repo.get_contract(source_contract_id)
    target = await repo.get_contract(target_contract_id)

    if source is None or target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both contracts not found",
        )

    tenant_id = user.tenant_id or "default"
    if source.get("tenant_id") != tenant_id or target.get("tenant_id") != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to one or both contracts",
        )

    source_text = source.get("text") or source.get("clause_text", "")
    target_text = target.get("text") or target.get("clause_text", "")

    # Generate unified diff
    diff_lines = list(
        difflib.unified_diff(
            source_text.splitlines(keepends=True),
            target_text.splitlines(keepends=True),
            fromfile=f"v{source.get('version', '0')}: {source.get('filename', 'source')}",
            tofile=f"v{target.get('version', '0')}: {target.get('filename', 'target')}",
            n=3,
        )
    )

    # Generate structured changes
    changes = _compute_structured_changes(source_text, target_text)

    comparison_id = str(uuid.uuid4())
    result: Dict[str, Any] = {
        "comparison_id": comparison_id,
        "source_contract_id": source_contract_id,
        "target_contract_id": target_contract_id,
        "tenant_id": tenant_id,
        "user_id": user.sub,
        "created_at": datetime.utcnow().isoformat(),
        "summary": {
            "total_additions": sum(1 for c in changes if c["type"] == "addition"),
            "total_deletions": sum(1 for c in changes if c["type"] == "deletion"),
            "total_modifications": sum(1 for c in changes if c["type"] == "modification"),
            "net_change": len(target_text) - len(source_text),
        },
        "diff": "".join(diff_lines),
        "changes": changes,
    }

    _redline_results[comparison_id] = result

    logger.info(
        "Redline comparison created: %s between %s and %s",
        comparison_id,
        source_contract_id,
        target_contract_id,
    )

    return result


@router.get("/suggest/")
@router.get("/suggest")
async def list_suggestions(
    contract_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_REDLINES)),
) -> Dict[str, Any]:
    """List redline suggestions.

    Args:
        contract_id: Optional filter by contract ID.
        status_filter: Optional filter by status.
        page: Page number.
        page_size: Items per page.
        user: Authenticated user.

    Returns:
        Dict with suggestions list and pagination.
    """
    suggestions = list(_redline_suggestions.values())

    if contract_id:
        suggestions = [s for s in suggestions if s.contract_id == contract_id]
    if status_filter:
        suggestions = [s for s in suggestions if s.status == status_filter]

    suggestions.sort(key=lambda s: s.created_at, reverse=True)
    total = len(suggestions)
    start = (page - 1) * page_size
    end = start + page_size

    return {
        "suggestions": [s.model_dump() for s in suggestions[start:end]],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/suggest/{suggestion_id}")
async def get_suggestion(
    suggestion_id: str,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_REDLINES)),
) -> RedlineSuggestion:
    """Get a specific redline suggestion.

    Args:
        suggestion_id: The suggestion identifier.
        user: Authenticated user.

    Returns:
        The redline suggestion.

    Raises:
        HTTPException: If suggestion not found.
    """
    suggestion = _redline_suggestions.get(suggestion_id)
    if suggestion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Suggestion {suggestion_id} not found",
        )
    return suggestion


@router.get("/{comparison_id}")
async def get_redline_comparison(
    comparison_id: str,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_REDLINES)),
) -> Dict[str, Any]:
    """Get a redline comparison result.

    Args:
        comparison_id: The comparison identifier.
        user: Authenticated user.

    Returns:
        Redline comparison with diff and changes.
    """
    result = _redline_results.get(comparison_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Redline comparison {comparison_id} not found",
        )

    if result.get("tenant_id") != (user.tenant_id or "default"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return result


@router.get("")
@router.get("/")
async def list_redline_comparisons(
    contract_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_REDLINES)),
) -> Dict[str, Any]:
    """List redline comparisons.

    Args:
        contract_id: Optional filter by contract ID.
        page: Page number.
        page_size: Items per page.
        user: Authenticated user.

    Returns:
        Dict with comparisons list.
    """
    tenant_id = user.tenant_id or "default"

    results = [
        r
        for r in _redline_results.values()
        if r.get("tenant_id") == tenant_id
    ]

    if contract_id:
        results = [
            r
            for r in results
            if r.get("source_contract_id") == contract_id
            or r.get("target_contract_id") == contract_id
        ]

    results.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    total = len(results)
    start = (page - 1) * page_size
    end = start + page_size

    return {
        "comparisons": results[start:end],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/suggest", status_code=status.HTTP_201_CREATED)
async def generate_redline_suggestion(
    request: RedlineRequest,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.WRITE_REDLINES)),
) -> RedlineResponse:
    """Generate an AI redline suggestion for a contract clause.

    Uses the specialized prompt templates and quality constraints to
    generate attorney-quality redline suggestions.

    Args:
        request: The redline suggestion request.
        user: Authenticated user.

    Returns:
        RedlineResponse with the suggestion and quality checks.

    Raises:
        HTTPException: If quality constraints are violated or generation fails.
    """
    start_time = time.monotonic()
    model_version = "redline-v1.0.0"

    try:
        # Build prompt messages
        messages = _prompt_templates.build_messages(
            clause_type=request.clause_type,
            original_clause_text=request.original_clause_text,
            party_role=request.party_role,
            deal_size_tier=request.deal_size_tier,
            industry=request.industry,
            counterparty_aggressiveness=request.counterparty_aggressiveness,
            jurisdiction=request.jurisdiction,
        )

        # Try LLM-based generation first
        llm_client = _get_llm_client()
        if llm_client is not None:
            try:
                # Convert OpenAI-format messages to our Message model
                raw_messages = _prompt_templates.build_messages(
                    clause_type=request.clause_type,
                    original_clause_text=request.original_clause_text,
                    party_role=request.party_role,
                    deal_size_tier=request.deal_size_tier,
                    industry=request.industry,
                    counterparty_aggressiveness=request.counterparty_aggressiveness,
                    jurisdiction=request.jurisdiction,
                )
                llm_messages = []
                for msg in raw_messages:
                    role = RoleType.SYSTEM if msg["role"] == "system" else RoleType.USER
                    llm_messages.append(Message(role=role, content=msg["content"]))

                llm_request = LLMRequest(
                    messages=llm_messages,
                    max_tokens=2048,
                    temperature=0.3,
                )
                llm_response = await llm_client.complete(llm_request)

                # Parse the JSON response from the LLM
                try:
                    content = llm_response.content.strip()
                    # Handle markdown code block wrapping
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0].strip()
                    elif "```" in content:
                        content = content.split("```")[1].split("```")[0].strip()
                    llm_output = json.loads(content)
                    proposed_text = llm_output.get("proposed_text", "")
                    if not proposed_text:
                        logger.warning("LLM response missing proposed_text; falling back to template")
                        proposed_text = _generate_proposed_text(
                            request.original_clause_text,
                            request.clause_type,
                            request.party_role,
                        )
                except (json.JSONDecodeError, KeyError) as parse_err:
                    logger.warning("Failed to parse LLM JSON response: %s; using template fallback", parse_err)
                    proposed_text = _generate_proposed_text(
                        request.original_clause_text,
                        request.clause_type,
                        request.party_role,
                    )
            except Exception as llm_err:
                logger.warning("LLM request failed: %s; using template fallback", llm_err)
                proposed_text = _generate_proposed_text(
                    request.original_clause_text,
                    request.clause_type,
                    request.party_role,
                )
        else:
            # No LLM configured, use template-based generation
            proposed_text = _generate_proposed_text(
                request.original_clause_text,
                request.clause_type,
                request.party_role,
            )

        # Run quality checks
        quality_results = _quality_engine.check_all(
            proposed_text, request.clause_type
        )

        if not _quality_engine.all_hard_passed(quality_results):
            errors = _quality_engine.get_errors(quality_results)
            error_details = [
                {"constraint": e.constraint_name, "message": e.message}
                for e in errors
            ]
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": "quality_constraint_violation",
                    "constraints": error_details,
                },
            )

        # Compute word diff
        word_diff = _diff_engine.get_word_diff_summary(
            request.original_clause_text, proposed_text
        )

        # Determine change type
        change_type = _diff_engine.compute_change_type(
            request.original_clause_text, proposed_text
        )

        # Build suggestion
        suggestion = RedlineSuggestion(
            contract_id=request.contract_id,
            clause_type=request.clause_type,
            original_text=request.original_clause_text,
            proposed_text=proposed_text,
            change_type=change_type,
            word_diff=word_diff,
            rationale=(
                f"Based on analysis of the {request.clause_type.value} clause "
                f"in the context of a {request.deal_size_tier.value} deal in the "
                f"{request.industry.value} industry, with a "
                f"{request.counterparty_aggressiveness.value} counterparty stance. "
                f"The suggested changes aim to better protect your interests as the "
                f"{request.party_role.value} under {request.jurisdiction} law."
            ),
            confidence=0.85,
            attorney_review_required=True,
            risk_impact="medium",
            metadata={
                "party_role": request.party_role.value,
                "deal_size_tier": request.deal_size_tier.value,
                "industry": request.industry.value,
                "counterparty_aggressiveness": request.counterparty_aggressiveness.value,
                "jurisdiction": request.jurisdiction,
                "quality_checks": [
                    {
                        "constraint": r.constraint_name,
                        "passed": r.passed,
                        "severity": r.severity,
                        "message": r.message,
                    }
                    for r in quality_results
                ],
            },
        )

        # Store and track
        _redline_suggestions[suggestion.suggestion_id] = suggestion
        _status_tracker.add_suggestion(suggestion)

        processing_time = int((time.monotonic() - start_time) * 1000)

        logger.info(
            "Redline suggestion %s generated for contract %s in %dms",
            suggestion.suggestion_id,
            request.contract_id,
            processing_time,
        )

        return RedlineResponse(
            suggestion=suggestion,
            quality_checks=[
                {
                    "constraint": r.constraint_name,
                    "passed": r.passed,
                    "severity": r.severity,
                    "message": r.message,
                }
                for r in quality_results
            ],
            processing_time_ms=processing_time,
            model_version=model_version,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Redline suggestion failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Redline suggestion generation failed: {exc}",
        )


@router.post("/suggest/{suggestion_id}/accept")
async def accept_suggestion(
    suggestion_id: str,
    comment: str = "",
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.ACCEPT_REDLINES)),
) -> Dict[str, Any]:
    """Accept a redline suggestion.

    Args:
        suggestion_id: The suggestion to accept.
        comment: Optional acceptance comment.
        user: Authenticated user.

    Returns:
        Dict with updated suggestion status.
    """
    try:
        suggestion = _status_tracker.accept(
            suggestion_id=suggestion_id,
            changed_by=user.sub,
            comment=comment,
        )
        return {
            "suggestion_id": suggestion_id,
            "status": suggestion.status,
            "changed_by": user.sub,
            "changed_at": suggestion.status_changed_at.isoformat(),
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.post("/suggest/{suggestion_id}/reject")
async def reject_suggestion(
    suggestion_id: str,
    comment: str = "",
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.ACCEPT_REDLINES)),
) -> Dict[str, Any]:
    """Reject a redline suggestion.

    Args:
        suggestion_id: The suggestion to reject.
        comment: Optional rejection reason.
        user: Authenticated user.

    Returns:
        Dict with updated suggestion status.
    """
    try:
        suggestion = _status_tracker.reject(
            suggestion_id=suggestion_id,
            changed_by=user.sub,
            comment=comment,
        )
        return {
            "suggestion_id": suggestion_id,
            "status": suggestion.status,
            "changed_by": user.sub,
            "changed_at": suggestion.status_changed_at.isoformat(),
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


def _generate_proposed_text(
    original_text: str,
    clause_type: ClauseType,
    party_role: PartyRole,
) -> str:
    """Generate proposed replacement text for a clause (LLM-only fallback).

    This function is only called when the LLM is unavailable. It returns
    a clear error message instead of fake template text.

    Args:
        original_text: The original clause text.
        clause_type: The type of clause.
        party_role: The party's role.

    Returns:
        Error message indicating LLM is required.
    """
    logger.warning(
        "LLM unavailable for redline generation. "
        "Clause type: %s, Party role: %s.",
        clause_type, party_role,
    )
    return (
        f"[AI REDLINE UNAVAILABLE]\n\n"
        f"The AI redline suggestion could not be generated because "
        f"the LLM service is currently unavailable. "
        f"Please configure DEEPSEEK_API_KEY or OPENAI_API_KEY "
        f"in your environment variables and try again.\n\n"
        f"Original clause type: {clause_type.value}\n"
        f"Party role: {party_role.value}"
    )


def _compute_structured_changes(
    source_text: str,
    target_text: str,
) -> List[Dict[str, Any]]:
    """Compute structured changes between two text versions.

    Args:
        source_text: Original text.
        target_text: Modified text.

    Returns:
        List of change dicts with type, position, and content.
    """
    changes: List[Dict[str, Any]] = []
    matcher = difflib.SequenceMatcher(None, source_text, target_text)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue

        change: Dict[str, Any] = {
            "type": tag,  # 'replace', 'delete', 'insert'
            "source_start": i1,
            "source_end": i2,
            "target_start": j1,
            "target_end": j2,
        }

        if tag == "replace":
            change["source_text"] = source_text[i1:i2]
            change["target_text"] = target_text[j1:j2]
            change["type"] = "modification"
        elif tag == "delete":
            change["source_text"] = source_text[i1:i2]
            change["type"] = "deletion"
        elif tag == "insert":
            change["target_text"] = target_text[j1:j2]
            change["type"] = "addition"

        # Truncate long content for display
        for key in ("source_text", "target_text"):
            if key in change and len(change[key]) > 500:
                change[key + "_truncated"] = True
                change[key] = change[key][:500] + "..."

        changes.append(change)

    return changes
