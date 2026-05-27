"""Policy Engine API router — simulation, dry-run, rule graph, impact analysis, health."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user, get_tenant_id
from app.kernel.security.auth import UserContext
from app.kernel.security.rbac import require_permission
from app.kernel.security.permissions import Permissions
from app.kernel.web.pagination import PaginatedResponse
from app.domains.playbook.repository import PlaybookRepository
from app.domains.policy.schemas import (
    RuleGraph, RuleGraphNode, RuleGraphEdge,
    SimulationRequest, SimulationResult, SimulationSummary,
    DryRunRequest, DryRunResult,
    PolicyChange, PolicyImpactAnalysis,
    PolicyAuditEvent, PolicyAuditLogResponse,
    PolicyHealthCheck,
)
from app.domains.policy.service import (
    PolicySimulationEngine,
    PolicyRuleGraphBuilder,
    PolicyImpactAnalyzer,
    PolicyHealthChecker,
)

router = APIRouter(prefix="/policy", tags=["Policy Engine"])


# ── Dependencies ────────────────────────────────────────────────────


async def get_repo(
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
) -> PlaybookRepository:
    return PlaybookRepository(db, tenant_id=tenant_id)


async def get_simulation_engine(
    repo: PlaybookRepository = Depends(get_repo),
    tenant_id: str = Depends(get_tenant_id),
) -> PolicySimulationEngine:
    return PolicySimulationEngine(repo=repo, tenant_id=tenant_id)


async def get_graph_builder(
    repo: PlaybookRepository = Depends(get_repo),
) -> PolicyRuleGraphBuilder:
    return PolicyRuleGraphBuilder(repo=repo)


async def get_impact_analyzer(
    repo: PlaybookRepository = Depends(get_repo),
    tenant_id: str = Depends(get_tenant_id),
) -> PolicyImpactAnalyzer:
    return PolicyImpactAnalyzer(repo=repo, tenant_id=tenant_id)


async def get_health_checker(
    repo: PlaybookRepository = Depends(get_repo),
) -> PolicyHealthChecker:
    return PolicyHealthChecker(repo=repo)


# ── Rule Graph ──────────────────────────────────────────────────────


@router.get("/playbooks/{playbook_id}/graph", response_model=RuleGraph)
async def get_policy_rule_graph(
    playbook_id: str,
    builder: PolicyRuleGraphBuilder = Depends(get_graph_builder),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Get the dependency graph of all policy rules in a playbook."""
    return await builder.build_graph(playbook_id)


# ── Simulation ──────────────────────────────────────────────────────


@router.post("/simulate", response_model=SimulationResult)
async def run_policy_simulation(
    request: SimulationRequest,
    engine: PolicySimulationEngine = Depends(get_simulation_engine),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Run a what-if policy simulation against a hypothetical contract profile."""
    return await engine.simulate(request)


@router.post("/dry-run", response_model=DryRunResult)
async def run_policy_dry_run(
    request: DryRunRequest,
    engine: PolicySimulationEngine = Depends(get_simulation_engine),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Dry-run policy evaluation against a real contract without persisting results."""
    return await engine.dry_run(request)


# ── Impact Analysis ─────────────────────────────────────────────────


@router.post("/playbooks/{playbook_id}/impact-analysis", response_model=PolicyImpactAnalysis)
async def analyze_policy_impact(
    playbook_id: str,
    changes: list[PolicyChange],
    description: str = Query("", description="Description of the proposed changes"),
    analyzer: PolicyImpactAnalyzer = Depends(get_impact_analyzer),
    _: None = Depends(require_permission(Permissions.CONTRACTS_WRITE)),
):
    """Analyze how proposed policy changes would affect existing contract evaluations."""
    return await analyzer.analyze_impact(playbook_id, changes, description=description)


# ── Policy Health ───────────────────────────────────────────────────


@router.get("/playbooks/{playbook_id}/health", response_model=PolicyHealthCheck)
async def check_policy_health(
    playbook_id: str,
    checker: PolicyHealthChecker = Depends(get_health_checker),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Run a health check on a playbook's policy configuration."""
    return await checker.check_health(playbook_id)
