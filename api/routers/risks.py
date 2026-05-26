"""Risk analysis API endpoints — enhanced 8-field explainability model.

Provides endpoints for running AI-powered risk analysis on contracts,
retrieving risk reports, managing risk assessment configurations,
validating claims, and managing escalation workflows.
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from middleware.auth import TokenPayload, get_current_user, require_permission, Permissions

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/risks", tags=["Risk Analysis"])


# In-memory stores for development
_risk_reports: Dict[str, Dict[str, Any]] = {}
_escalation_items: Dict[str, Dict[str, Any]] = {}

# Risk categories for contract analysis
RISK_CATEGORIES = [
    "indemnification",
    "liability_limitation",
    "termination",
    "confidentiality",
    "data_privacy",
    "compliance",
    "payment_terms",
    "force_majeure",
    "assignment",
    "governing_law",
    "non_compete",
    "intellectual_property",
]

# Global escalation workflow instance
_escalation_workflow: Any = None


def _get_escalation_workflow():
    """Get or create the escalation workflow singleton."""
    global _escalation_workflow
    if _escalation_workflow is None:
        from risk_engine.escalation import EscalationWorkflow
        _escalation_workflow = EscalationWorkflow()
    return _escalation_workflow


async def _run_risk_analysis(
    report_id: str,
    contract_id: str,
    clause_texts: List[str],
    categories: List[str],
    tenant_id: str,
) -> Dict[str, Any]:
    """Run the AI-powered risk analysis pipeline with 8-field explainability.

    Uses the PromptChainOrchestrator to analyze each clause through
    the 4-step chain, producing the enhanced 8-field enterprise
    explainability output.

    Args:
        report_id: The report to update.
        contract_id: The contract being analyzed.
        clause_texts: List of clause texts to analyze.
        categories: Risk categories to check.
        tenant_id: Tenant for tracking.

    Returns:
        Dict with analysis results including 8-field explainability.
    """
    results = []
    total = len(clause_texts)

    try:
        from risk_engine.taxonomy import RiskTaxonomy
        from risk_engine.chain import PromptChainOrchestrator
        from risk_engine.confidence import ConfidenceCalibrationEngine
        from risk_engine.jurisdiction import JurisdictionalRiskLayer
        from risk_engine.escalation import EscalationReason

        taxonomy = RiskTaxonomy()
        llm_client = _get_llm_client()
        orchestrator = PromptChainOrchestrator(taxonomy=taxonomy, llm_client=llm_client)
        confidence_engine = ConfidenceCalibrationEngine(llm_client=llm_client)
        jurisdiction_layer = JurisdictionalRiskLayer()
        escalation_workflow = _get_escalation_workflow()

        for i, clause_text in enumerate(clause_texts):
            try:
                chain_result = await orchestrator.run_chain(
                    clause_text=clause_text,
                    tenant_id=tenant_id,
                )

                if chain_result.success:
                    # Compute self-consistency confidence
                    category_id = "indemnification"
                    if chain_result.classification and chain_result.classification.data:
                        classifications = chain_result.classification.data.get("classifications", [])
                        if classifications:
                            category_id = classifications[0].get("category_id", "indemnification")

                    consistency = await confidence_engine.compute_self_consistency(
                        clause_text=clause_text,
                        category_id=category_id,
                        tenant_id=tenant_id,
                    )

                    # Get confidence score (from chain or self-consistency)
                    raw_confidence = chain_result.confidence_score or consistency.mean_score
                    calibrated_confidence, confidence_label = confidence_engine.calibrate_confidence(raw_confidence)

                    # Record calibration sample
                    severity_score = 5
                    if chain_result.severity and chain_result.severity.data:
                        severity_score = chain_result.severity.data.get("severity_score", 5)
                    confidence_engine.add_sample(
                        clause_text=clause_text,
                        category_id=category_id,
                        confidence_score=calibrated_confidence,
                        severity_score=severity_score,
                    )

                    # Evaluate jurisdictional context
                    jurisdictional_considerations = jurisdiction_layer.evaluate_clause(
                        clause_text=clause_text,
                        category_id=category_id,
                        jurisdictions=["US", "EU", "UK", "APAC"],
                    )

                    # Check if escalation needed
                    escalation_reason = escalation_workflow.should_escalate(
                        confidence_score=calibrated_confidence,
                        severity_score=severity_score,
                    )
                    escalation = None
                    if escalation_reason:
                        ai_rationale = ""
                        if chain_result.rationale and chain_result.rationale.data:
                            ai_rationale = json.dumps(chain_result.rationale.data)
                        escalation = escalation_workflow.create_escalation(
                            contract_id=contract_id,
                            clause_text=clause_text,
                            risk_category=category_id,
                            severity_score=severity_score,
                            confidence_score=calibrated_confidence,
                            escalation_reason=escalation_reason,
                            ai_rationale=ai_rationale,
                            tenant_id=tenant_id,
                        )

                    result_entry = {
                        "clause_text": clause_text[:500],
                        # 8-field explainability
                        "why_flagged": chain_result.why_flagged or "",
                        "potential_business_impact": chain_result.potential_business_impact or "",
                        "market_benchmark_comparison": chain_result.market_benchmark_comparison or "",
                        "confidence_score": calibrated_confidence,
                        "confidence_label": confidence_label,
                        "suggested_remediation": chain_result.suggested_remediation or "",
                        "linked_evidence": chain_result.linked_evidence,
                        "jurisdictional_considerations": [
                            j.model_dump() if hasattr(j, "model_dump") else j
                            for j in jurisdictional_considerations
                        ],
                        # Legacy fields for backward compatibility
                        "classification": chain_result.classification.data if chain_result.classification else None,
                        "assessment": chain_result.assessment.data if chain_result.assessment else None,
                        "severity": chain_result.severity.data if chain_result.severity else None,
                        "rationale": chain_result.rationale.data if chain_result.rationale else None,
                        "hallucination_check": chain_result.hallucination_check,
                        "citations": chain_result.citations,
                        "self_consistency": {
                            "mean_score": consistency.mean_score,
                            "std_dev": consistency.std_dev,
                            "pairwise_agreement": consistency.pairwise_agreement,
                            "consistent": consistency.consistent,
                            "consensus_label": consistency.consensus_label,
                        },
                        "escalation": {
                            "escalated": escalation is not None,
                            "escalation_id": escalation.escalation_id if escalation else None,
                            "reason": escalation_reason.value if escalation_reason else None,
                        } if escalation else {"escalated": False},
                    }
                else:
                    result_entry = {
                        "clause_text": clause_text[:500],
                        "error": chain_result.error or "Analysis failed",
                    }

                results.append(result_entry)

                # Update progress
                report = _risk_reports.get(report_id)
                if report:
                    report["progress"] = round((i + 1) / total * 100, 1)
                    report["results"] = results

            except Exception as exc:
                logger.error("Clause analysis failed: %s", exc)
                results.append({
                    "clause_text": clause_text[:500],
                    "error": str(exc),
                })

        # Compute aggregate scores
        severity_scores = [
            r.get("severity", {}).get("severity_score", 0)
            for r in results if r.get("severity")
        ]
        avg_severity = sum(severity_scores) / len(severity_scores) if severity_scores else 0
        high_risk = sum(1 for s in severity_scores if s >= 7)
        medium_risk = sum(1 for s in severity_scores if 4 <= s < 7)

        summary = {
            "total_clauses": total,
            "analyzed": len(results),
            "avg_severity": round(avg_severity, 1),
            "high_risk_count": high_risk,
            "medium_risk_count": medium_risk,
            "categories_checked": categories,
            "avg_confidence": round(
                sum(r.get("confidence_score", 0) for r in results if "confidence_score" in r)
                / max(len([r for r in results if "confidence_score" in r]), 1), 3
            ),
        }

        final_result = {
            "results": results,
            "summary": summary,
        }

        # Update report
        report = _risk_reports.get(report_id)
        if report:
            report["status"] = "completed"
            report["progress"] = 100
            report["results"] = final_result
            report["completed_at"] = datetime.utcnow().isoformat()

        logger.info(
            "Risk analysis completed: report=%s, %d clauses analyzed, avg severity=%.1f",
            report_id,
            total,
            avg_severity,
        )

        return final_result

    except Exception as exc:
        logger.error("Risk analysis failed: %s", exc, exc_info=True)
        report = _risk_reports.get(report_id)
        if report:
            report["status"] = "failed"
            report["error"] = str(exc)
        return {"error": str(exc)}


def _get_llm_client():
    """Get or create the LLM client.

    Returns:
        LLMClient instance.
    """
    from llm.client import LLMClient

    return LLMClient(
        deepseek_key=os.getenv("DEEPSEEK_API_KEY", ""),
        anthropic_key=os.getenv("ANTHROPIC_API_KEY", ""),
        openai_key=os.getenv("OPENAI_API_KEY", ""),
    )


@router.post("/analyze", status_code=status.HTTP_201_CREATED)
async def analyze_contract_risks(
    contract_id: str = Query(..., description="Contract to analyze"),
    categories: Optional[List[str]] = Query(
        None, description="Risk categories to analyze"
    ),
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.WRITE_CONTRACTS)),
) -> Dict[str, Any]:
    """Start an AI-powered risk analysis on a contract with 8-field explainability.

    Analyzes contract clauses through the enhanced prompt chain producing
    the 8-field enterprise explainability model:
    1. clause_text          2. risk_category          3. why_flagged
    4. potential_business_impact  5. market_benchmark_comparison
    6. confidence_score     7. suggested_remediation  8. linked_evidence
    9. jurisdictional_considerations

    Args:
        contract_id: The contract to analyze.
        categories: Specific risk categories to evaluate.
        user: Authenticated user.

    Returns:
        Dict with report_id and status for tracking.
    """
    if categories:
        invalid = [c for c in categories if c not in RISK_CATEGORIES]
        if invalid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid risk categories: {invalid}. "
                f"Valid: {RISK_CATEGORIES}",
            )

    report_id = str(uuid.uuid4())
    report: Dict[str, Any] = {
        "report_id": report_id,
        "contract_id": contract_id,
        "tenant_id": user.tenant_id or "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "user_id": user.sub,
        "status": "analyzing",
        "progress": 0,
        "categories": categories or RISK_CATEGORIES,
        "created_at": datetime.utcnow().isoformat(),
        "results": None,
    }

    _risk_reports[report_id] = report

    logger.info(
        "Risk analysis started: report=%s, contract=%s, user=%s",
        report_id,
        contract_id,
        user.sub,
    )

    # Fetch contract clauses from the database or use sample clauses
    clause_texts = await _get_contract_clauses(contract_id)

    if not clause_texts:
        # Use sample clauses for demo
        clause_texts = [
            "The Supplier shall indemnify, defend, and hold harmless the Customer from and against any and all claims, damages, losses, liabilities, and expenses arising out of or related to any breach of this Agreement by the Supplier.",
            "In no event shall either party be liable for any indirect, incidental, special, consequential, or punitive damages, regardless of the theory of liability.",
            "This Agreement may be terminated by either party upon 30 days written notice to the other party.",
            "The Receiving Party shall maintain strict confidentiality of all Confidential Information disclosed by the Disclosing Party.",
        ]

    # Run analysis in background
    asyncio.create_task(
        _run_risk_analysis(
            report_id=report_id,
            contract_id=contract_id,
            clause_texts=clause_texts,
            categories=categories or RISK_CATEGORIES,
            tenant_id=user.tenant_id or "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        )
    )

    return {
        "report_id": report_id,
        "status": "analyzing",
        "status_url": f"/api/v1/risks/{report_id}",
        "total_clauses": len(clause_texts),
    }


async def _get_contract_clauses(contract_id: str) -> List[str]:
    """Fetch clause texts for a contract from the database.

    Args:
        contract_id: The contract identifier.

    Returns:
        List of clause text strings.
    """
    try:
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine

        database_url = os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://dev_user:dev_password@localhost:5432/contract_risk_dev",
        )
        engine = create_async_engine(database_url)
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT text FROM chunks WHERE contract_id = :contract_id ORDER BY chunk_index LIMIT 50"),
                {"contract_id": contract_id},
            )
            rows = result.fetchall()
            await engine.dispose()
            return [row.text for row in rows if row.text]
    except Exception as exc:
        logger.warning("Failed to fetch clauses for contract %s: %s", contract_id, exc)
        return []


# ── V2-003: Unsupported Claim Detection ──


@router.post("/validate", status_code=status.HTTP_200_OK)
async def validate_risk_claims(
    clause_text: str = Query(..., description="Source contract clause text"),
    ai_output: str = Query(..., description="AI-generated analysis to validate"),
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """Validate that AI-generated claims are grounded in source contract text.

    Uses the GroundingValidator to verify each claim in the AI output
    has supporting evidence in the source clause text. Detects unsupported
    claims and potential hallucinations.

    Args:
        clause_text: The original source contract clause text.
        ai_output: The AI-generated analysis to validate.

    Returns:
        Dict with per-claim verification results and grounding score.
    """
    try:
        from llm.hallucination.detector import GroundingValidator

        validator = GroundingValidator()
        result = validator.validate(clause_text=clause_text, ai_output_text=ai_output)

        return {
            "passed": result.passed,
            "grounding_score": result.grounding_score,
            "claims_verified": result.claims_verified,
            "claims_supported": result.claims_supported,
            "claims_unsupported": result.claims_unsupported,
            "unsupported_claims": result.unsupported_claims,
            "verifications": [
                {
                    "claim": v.claim_text,
                    "supported": v.supported,
                    "confidence": v.confidence,
                    "evidence_excerpt": v.evidence_excerpt,
                }
                for v in result.verifications
            ],
            "details": result.details,
        }
    except Exception as exc:
        logger.error("Claim validation failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Claim validation failed: {str(exc)}",
        )


# ── V2-004: Escalation Workflow ──


@router.get("/escalations", status_code=status.HTTP_200_OK)
async def list_escalations(
    status_filter: Optional[str] = Query(None, description="Filter by status: pending, in_review, reviewed, overridden, dismissed"),
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """List escalation items requiring attorney review.

    Returns items that have been escalated due to low confidence,
    high severity, or other configurable thresholds.

    Args:
        status_filter: Optional filter by escalation status.

    Returns:
        Dict with escalations list and statistics.
    """
    try:
        workflow = _get_escalation_workflow()
        tenant_id = user.tenant_id or "default"

        if status_filter:
            from risk_engine.escalation import EscalationStatus
            valid_statuses = [s.value for s in EscalationStatus]
            if status_filter not in valid_statuses:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {status_filter}. Valid: {valid_statuses}",
                )

        items = workflow.get_pending_escalations(tenant_id=tenant_id)

        # Filter by status if specified
        if status_filter:
            items = [e for e in items if e.status.value == status_filter]

        return {
            "escalations": [
                {
                    "escalation_id": e.escalation_id,
                    "contract_id": e.contract_id,
                    "clause_text": e.clause_text[:300],
                    "risk_category": e.risk_category,
                    "severity_score": e.severity_score,
                    "confidence_score": e.confidence_score,
                    "escalation_reason": e.escalation_reason.value,
                    "status": e.status.value,
                    "created_at": e.created_at.isoformat(),
                    "reviewed_by": e.reviewed_by,
                    "reviewed_at": e.reviewed_at.isoformat() if e.reviewed_at else None,
                }
                for e in items
            ],
            "statistics": workflow.get_statistics(tenant_id=tenant_id),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to list escalations: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list escalations: {str(exc)}",
        )


@router.post("/escalations/{escalation_id}/review", status_code=status.HTTP_200_OK)
async def review_escalation(
    escalation_id: str,
    status: str = Query(..., description="Review status: reviewed, overridden, dismissed"),
    comment: Optional[str] = Query(None, description="Review comment"),
    override_score: Optional[int] = Query(None, ge=1, le=10, description="Override severity score"),
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.WRITE_CONTRACTS)),
) -> Dict[str, Any]:
    """Submit a review for an escalation item.

    Allows attorneys to review, override, or dismiss escalated risk flags.
    Updates the escalation status and optionally overrides the severity score.

    Args:
        escalation_id: The escalation to review.
        status: New status (reviewed, overridden, dismissed).
        comment: Optional review comment.
        override_score: Optional severity score override (1-10).

    Returns:
        Dict with updated escalation item.
    """
    try:
        from risk_engine.escalation import EscalationStatus

        workflow = _get_escalation_workflow()

        valid_statuses = ["reviewed", "overridden", "dismissed"]
        if status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}. Valid: {valid_statuses}",
            )

        item = workflow.review_escalation(
            escalation_id=escalation_id,
            reviewed_by=user.sub or "attorney@lawfirm.com",
            status=EscalationStatus(status),
            comment=comment,
            override_score=override_score,
        )

        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Escalation {escalation_id} not found",
            )

        return {
            "escalation_id": item.escalation_id,
            "status": item.status.value,
            "reviewed_by": item.reviewed_by,
            "reviewed_at": item.reviewed_at.isoformat() if item.reviewed_at else None,
            "comment": item.review_comment,
            "override_score": item.override_score,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to review escalation: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to review escalation: {str(exc)}",
        )


@router.get("/{report_id}")
async def get_risk_report(
    report_id: str,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """Get a risk analysis report.

    Args:
        report_id: The risk report identifier.
        user: Authenticated user.

    Returns:
        Risk report with findings and scores.

    Raises:
        HTTPException: If report not found or access denied.
    """
    report = _risk_reports.get(report_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Risk report {report_id} not found",
        )

    tenant_id = user.tenant_id or "default"
    if report.get("tenant_id") != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this report",
        )

    return report


@router.get("")
@router.get("/")
async def list_risk_reports(
    contract_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """List risk analysis reports.

    Args:
        contract_id: Optional filter by contract.
        page: Page number.
        page_size: Items per page.
        user: Authenticated user.

    Returns:
        Dict with reports list and pagination.
    """
    tenant_id = user.tenant_id or "default"

    results = [
        r
        for r in _risk_reports.values()
        if r.get("tenant_id") == tenant_id
    ]

    if contract_id:
        results = [r for r in results if r.get("contract_id") == contract_id]

    results.sort(key=lambda r: r.get("created_at", ""), reverse=True)

    total = len(results)
    start = (page - 1) * page_size
    end = start + page_size

    return {
        "reports": results[start:end],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_risk_report(
    report_id: str,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.DELETE_CONTRACTS)),
) -> None:
    """Delete a risk analysis report.

    Args:
        report_id: The report to delete.
        user: Authenticated user.
    """
    report = _risk_reports.get(report_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Risk report {report_id} not found",
        )

    if report.get("tenant_id") != (user.tenant_id or "default"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    del _risk_reports[report_id]
