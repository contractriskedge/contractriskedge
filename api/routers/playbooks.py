"""Playbook configuration API endpoints.

Provides CRUD operations for playbook rules, version management,
and rule evaluation. Playbooks define company-specific risk policies
for contract clause evaluation.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from middleware.auth import TokenPayload, get_current_user, require_permission, Permissions
from playbook.engine import (
    PlaybookEngine,
    Playbook,
    PlaybookRule,
    PlaybookVersion,
    RuleCondition,
    RuleAction,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/playbooks", tags=["Playbooks"])

# Singleton engine instance (will be replaced with DB-backed version)
_engine: Optional[PlaybookEngine] = None


def _get_engine() -> PlaybookEngine:
    """Get the playbook engine singleton.

    Returns:
        The PlaybookEngine instance.
    """
    global _engine
    if _engine is None:
        _engine = PlaybookEngine()
    return _engine


# ── Request/Response Models ──────────────────────────────────────────────


class PlaybookCreate(BaseModel):
    """Request model for creating a playbook."""

    name: str = Field(..., min_length=1, max_length=200, description="Playbook name")
    description: str = Field("", max_length=2000, description="Playbook description")
    contract_types: List[str] = Field(default_factory=list, description="Applicable contract types")


class PlaybookUpdate(BaseModel):
    """Request model for updating a playbook."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    contract_types: Optional[List[str]] = None
    is_active: Optional[bool] = None


class RuleCreate(BaseModel):
    """Request model for creating a playbook rule."""

    clause_type: str = Field(..., min_length=1, description="Clause type this rule applies to")
    condition: RuleCondition = Field(..., description="Rule condition type")
    value: str = Field(..., min_length=1, max_length=1000, description="Value to compare against")
    action: RuleAction = Field(..., description="Action to take when matched")
    action_value: str = Field(..., max_length=1000, description="Action parameter")
    priority: int = Field(0, ge=0, le=1000, description="Rule priority (higher = evaluated first)")


class RuleUpdate(BaseModel):
    """Request model for updating a playbook rule."""

    clause_type: Optional[str] = None
    condition: Optional[RuleCondition] = None
    value: Optional[str] = None
    action: Optional[RuleAction] = None
    action_value: Optional[str] = None
    priority: Optional[int] = None
    enabled: Optional[bool] = None


class VersionApprove(BaseModel):
    """Request model for approving a playbook version."""

    approved_by: str = Field(..., min_length=1, description="Name/ID of approver")
    change_summary: str = Field("", max_length=2000, description="Summary of changes")


class EvaluateRequest(BaseModel):
    """Request model for evaluating a clause against a playbook."""

    clause_text: str = Field(..., min_length=1, description="The clause text to evaluate")
    clause_type: str = Field(..., min_length=1, description="Type of clause")


class EvaluateResponse(BaseModel):
    """Response model for clause evaluation."""

    matched_rules: List[Dict[str, Any]] = Field(default_factory=list)
    total_rules: int = 0
    matched_count: int = 0


# ── Playbook CRUD Endpoints ──────────────────────────────────────────────


@router.get("", response_model=List[Dict[str, Any]])
async def list_playbooks(
    include_inactive: bool = Query(False, description="Include inactive playbooks"),
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> List[Dict[str, Any]]:
    """List all playbooks for the current tenant.

    Args:
        include_inactive: Whether to include inactive playbooks.
        user: Authenticated user.

    Returns:
        List of playbook summaries.
    """
    engine = _get_engine()
    playbooks = engine.list_playbooks(tenant_id=user.tenant_id or "default")

    if not include_inactive:
        playbooks = [p for p in playbooks if p.is_active]

    return [
        {
            "playbook_id": p.playbook_id,
            "name": p.name,
            "description": p.description,
            "contract_types": p.contract_types,
            "is_active": p.is_active,
            "version_count": len(p.versions),
            "created_at": p.created_at,
            "updated_at": p.updated_at,
        }
        for p in playbooks
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_playbook(
    playbook: PlaybookCreate,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.WRITE_PLAYBOOKS)),
) -> Dict[str, Any]:
    """Create a new playbook.

    Args:
        playbook: Playbook configuration.
        user: Authenticated user.

    Returns:
        The created playbook.
    """
    engine = _get_engine()
    result = engine.create_playbook(
        name=playbook.name,
        description=playbook.description,
        contract_types=playbook.contract_types,
        tenant_id=user.tenant_id or "default",
    )
    return {
        "playbook_id": result.playbook_id,
        "name": result.name,
        "description": result.description,
        "contract_types": result.contract_types,
        "is_active": result.is_active,
        "tenant_id": result.tenant_id,
        "created_at": result.created_at,
        "updated_at": result.updated_at,
    }


@router.get("/{playbook_id}")
async def get_playbook(
    playbook_id: str,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """Get a playbook by ID with full details including versions.

    Args:
        playbook_id: Playbook identifier.
        user: Authenticated user.

    Returns:
        Full playbook details.

    Raises:
        HTTPException: If playbook not found.
    """
    engine = _get_engine()
    playbook = engine.get_playbook(playbook_id)
    if playbook is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Playbook {playbook_id} not found",
        )

    return {
        "playbook_id": playbook.playbook_id,
        "name": playbook.name,
        "description": playbook.description,
        "contract_types": playbook.contract_types,
        "tenant_id": playbook.tenant_id,
        "is_active": playbook.is_active,
        "created_at": playbook.created_at,
        "updated_at": playbook.updated_at,
        "versions": [
            {
                "version_id": v.version_id,
                "version_number": v.version_number,
                "status": v.status,
                "created_by": v.created_by,
                "created_at": v.created_at,
                "change_summary": v.change_summary,
                "rule_count": len(v.rules),
            }
            for v in playbook.versions
        ],
    }


@router.put("/{playbook_id}")
async def update_playbook(
    playbook_id: str,
    update: PlaybookUpdate,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.WRITE_PLAYBOOKS)),
) -> Dict[str, Any]:
    """Update a playbook's metadata.

    Args:
        playbook_id: Playbook identifier.
        update: Fields to update.
        user: Authenticated user.

    Returns:
        Updated playbook.

    Raises:
        HTTPException: If playbook not found.
    """
    engine = _get_engine()
    playbook = engine.get_playbook(playbook_id)
    if playbook is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Playbook {playbook_id} not found",
        )

    if update.name is not None:
        playbook.name = update.name
    if update.description is not None:
        playbook.description = update.description
    if update.contract_types is not None:
        playbook.contract_types = update.contract_types
    if update.is_active is not None:
        playbook.is_active = update.is_active

    playbook.updated_at = datetime.utcnow().isoformat() + "Z"

    return {
        "playbook_id": playbook.playbook_id,
        "name": playbook.name,
        "description": playbook.description,
        "contract_types": playbook.contract_types,
        "is_active": playbook.is_active,
        "updated_at": playbook.updated_at,
    }


@router.delete("/{playbook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_playbook(
    playbook_id: str,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.WRITE_PLAYBOOKS)),
) -> None:
    """Delete a playbook.

    Args:
        playbook_id: Playbook identifier.
        user: Authenticated user.

    Raises:
        HTTPException: If playbook not found.
    """
    engine = _get_engine()
    playbook = engine.get_playbook(playbook_id)
    if playbook is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Playbook {playbook_id} not found",
        )

    engine._playbooks.pop(playbook_id, None)


# ── Rule Management Endpoints ────────────────────────────────────────────


@router.post("/{playbook_id}/rules", status_code=status.HTTP_201_CREATED)
async def add_rule(
    playbook_id: str,
    rule: RuleCreate,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.WRITE_PLAYBOOKS)),
) -> Dict[str, Any]:
    """Add a rule to a playbook.

    Args:
        playbook_id: Target playbook.
        rule: Rule configuration.
        user: Authenticated user.

    Returns:
        The created rule.

    Raises:
        HTTPException: If playbook not found.
    """
    engine = _get_engine()
    result = engine.add_rule(
        playbook_id=playbook_id,
        clause_type=rule.clause_type,
        condition=rule.condition,
        value=rule.value,
        action=rule.action,
        action_value=rule.action_value,
        priority=rule.priority,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Playbook {playbook_id} not found",
        )

    return {
        "rule_id": result.rule_id,
        "clause_type": result.clause_type,
        "condition": result.condition.value,
        "value": result.value,
        "action": result.action.value,
        "action_value": result.action_value,
        "priority": result.priority,
        "enabled": result.enabled,
    }


@router.get("/{playbook_id}/rules")
async def list_rules(
    playbook_id: str,
    clause_type: Optional[str] = Query(None, description="Filter by clause type"),
    enabled_only: bool = Query(True, description="Only return enabled rules"),
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> List[Dict[str, Any]]:
    """List rules in a playbook.

    Args:
        playbook_id: Playbook identifier.
        clause_type: Optional clause type filter.
        enabled_only: Only return enabled rules.
        user: Authenticated user.

    Returns:
        List of rules.

    Raises:
        HTTPException: If playbook not found.
    """
    engine = _get_engine()
    playbook = engine.get_playbook(playbook_id)
    if playbook is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Playbook {playbook_id} not found",
        )

    if not playbook.versions:
        return []

    active_version = playbook.versions[-1]
    rules = active_version.rules

    if clause_type:
        rules = [r for r in rules if r.clause_type == clause_type]
    if enabled_only:
        rules = [r for r in rules if r.enabled]

    return [
        {
            "rule_id": r.rule_id,
            "clause_type": r.clause_type,
            "condition": r.condition.value,
            "value": r.value,
            "action": r.action.value,
            "action_value": r.action_value,
            "priority": r.priority,
            "enabled": r.enabled,
        }
        for r in rules
    ]


@router.put("/{playbook_id}/rules/{rule_id}")
async def update_rule(
    playbook_id: str,
    rule_id: str,
    update: RuleUpdate,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.WRITE_PLAYBOOKS)),
) -> Dict[str, Any]:
    """Update a specific rule in a playbook.

    Args:
        playbook_id: Playbook identifier.
        rule_id: Rule identifier.
        update: Fields to update.
        user: Authenticated user.

    Returns:
        Updated rule.

    Raises:
        HTTPException: If playbook or rule not found.
    """
    engine = _get_engine()
    playbook = engine.get_playbook(playbook_id)
    if playbook is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Playbook {playbook_id} not found",
        )

    if not playbook.versions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playbook has no versions",
        )

    active_version = playbook.versions[-1]
    target_rule = next((r for r in active_version.rules if r.rule_id == rule_id), None)
    if target_rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule {rule_id} not found in playbook {playbook_id}",
        )

    if update.clause_type is not None:
        target_rule.clause_type = update.clause_type
    if update.condition is not None:
        target_rule.condition = update.condition
    if update.value is not None:
        target_rule.value = update.value
    if update.action is not None:
        target_rule.action = update.action
    if update.action_value is not None:
        target_rule.action_value = update.action_value
    if update.priority is not None:
        target_rule.priority = update.priority
    if update.enabled is not None:
        target_rule.enabled = update.enabled

    return {
        "rule_id": target_rule.rule_id,
        "clause_type": target_rule.clause_type,
        "condition": target_rule.condition.value,
        "value": target_rule.value,
        "action": target_rule.action.value,
        "action_value": target_rule.action_value,
        "priority": target_rule.priority,
        "enabled": target_rule.enabled,
    }


@router.delete("/{playbook_id}/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    playbook_id: str,
    rule_id: str,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.WRITE_PLAYBOOKS)),
) -> None:
    """Delete a rule from a playbook.

    Args:
        playbook_id: Playbook identifier.
        rule_id: Rule identifier.
        user: Authenticated user.

    Raises:
        HTTPException: If playbook or rule not found.
    """
    engine = _get_engine()
    playbook = engine.get_playbook(playbook_id)
    if playbook is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Playbook {playbook_id} not found",
        )

    if not playbook.versions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playbook has no versions",
        )

    active_version = playbook.versions[-1]
    original_count = len(active_version.rules)
    active_version.rules = [r for r in active_version.rules if r.rule_id != rule_id]

    if len(active_version.rules) == original_count:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule {rule_id} not found in playbook {playbook_id}",
        )


# ── Version Management Endpoints ─────────────────────────────────────────


@router.post("/{playbook_id}/versions/{version_number}/approve")
async def approve_version(
    playbook_id: str,
    version_number: int,
    approval: VersionApprove,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.WRITE_PLAYBOOKS)),
) -> Dict[str, Any]:
    """Approve a playbook version.

    Args:
        playbook_id: Playbook identifier.
        version_number: Version number to approve.
        approval: Approval details.
        user: Authenticated user.

    Returns:
        Updated version info.

    Raises:
        HTTPException: If playbook or version not found.
    """
    engine = _get_engine()
    playbook = engine.get_playbook(playbook_id)
    if playbook is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Playbook {playbook_id} not found",
        )

    version = next(
        (v for v in playbook.versions if v.version_number == version_number),
        None,
    )
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {version_number} not found",
        )

    version.status = "active"
    version.approved_by = approval.approved_by
    version.approved_at = datetime.utcnow().isoformat() + "Z"
    version.change_summary = approval.change_summary
    playbook.is_active = True
    playbook.updated_at = datetime.utcnow().isoformat() + "Z"

    return {
        "version_id": version.version_id,
        "version_number": version.version_number,
        "status": version.status,
        "approved_by": version.approved_by,
        "approved_at": version.approved_at,
        "change_summary": version.change_summary,
    }


# ── Evaluation Endpoint ──────────────────────────────────────────────────


@router.post("/{playbook_id}/evaluate")
async def evaluate_clause(
    playbook_id: str,
    request: EvaluateRequest,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> EvaluateResponse:
    """Evaluate a clause against a playbook's rules.

    Args:
        playbook_id: Playbook to evaluate against.
        request: Clause text and type.
        user: Authenticated user.

    Returns:
        Evaluation results with matched rules.

    Raises:
        HTTPException: If playbook not found.
    """
    engine = _get_engine()
    playbook = engine.get_playbook(playbook_id)
    if playbook is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Playbook {playbook_id} not found",
        )

    results = engine.evaluate(
        playbook_id=playbook_id,
        clause_text=request.clause_text,
        clause_type=request.clause_type,
    )

    return EvaluateResponse(
        matched_rules=results,
        total_rules=len(playbook.versions[-1].rules) if playbook.versions else 0,
        matched_count=len(results),
    )
