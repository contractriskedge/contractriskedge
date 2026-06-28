"""Workflow Foundation — Sprint 33.1 Workflow Engine components.

Validation engine, JSON Logic rule engine, workflow simulator,
business calendar, domain events, action catalog, metadata providers,
impact analysis, and built-in marketplace packs.
"""

from __future__ import annotations

from app.domains.workflow.validation import (
    IssueCode,
    IssueSeverity,
    ValidationIssue,
    ValidationResult,
    WorkflowValidator,
)
from app.domains.workflow.json_logic import (
    BusinessRuleCatalog,
    ExplanationNode,
    json_logic,
    RuleEvaluator,
    RuleReference,
)
from app.domains.workflow.simulator import (
    DryRunResult,
    RuleMatch,
    RuleSkip,
    SimulatedStage,
    SimulationInput,
    SimulationLog,
    SimulationResult,
    WorkflowSimulator,
)
from app.domains.workflow.calendar import (
    BusinessCalendar,
    BusinessHoursCalculator,
    default_calendar,
)
from app.domains.workflow.events import (
    ApprovalGranted,
    ApprovalRejected,
    ObligationCreated,
    RuleMatched,
    RuleSkipped,
    SignatureCompleted,
    SignatureSent,
    StageCompleted,
    StageEntered,
    WorkflowBreached,
    WorkflowCancelled,
    WorkflowCompleted,
    WorkflowEscalated,
    WorkflowStarted,
    WORKFLOW_EVENT_TYPES,
)
from app.domains.workflow.actions import (
    ActionContext,
    ActionFactory,
    ActionProvider,
    ActionRegistry,
    ActionResult,
    ApproveAction,
    DelayAction,
    DevAutoAction,
    EmailAction,
    NotifyAction,
    RejectAction,
)
from app.domains.workflow.providers import (
    AIProvider,
    CompositeContextBuilder,
    ContractProvider,
    MetadataProvider,
    ProviderRegistry,
    RiskProvider,
    SupplierProvider,
    UserProvider,
)
from app.domains.workflow.impact import (
    ImpactAnalysisResult,
    ImpactAnalyzer,
)
from app.domains.workflow.templates import (
    BUILT_IN_PACKS,
    get_built_in_pack,
    list_built_in_packs,
    seed_built_in_packs,
)

__all__ = [
    # Validation
    "IssueCode",
    "IssueSeverity",
    "ValidationIssue",
    "ValidationResult",
    "WorkflowValidator",
    # JSON Logic
    "BusinessRuleCatalog",
    "ExplanationNode",
    "json_logic",
    "RuleEvaluator",
    "RuleReference",
    # Simulator
    "DryRunResult",
    "RuleMatch",
    "RuleSkip",
    "SimulatedStage",
    "SimulationInput",
    "SimulationLog",
    "SimulationResult",
    "WorkflowSimulator",
    # Calendar
    "BusinessCalendar",
    "BusinessHoursCalculator",
    "default_calendar",
    # Events
    "ApprovalGranted",
    "ApprovalRejected",
    "ObligationCreated",
    "RuleMatched",
    "RuleSkipped",
    "SignatureCompleted",
    "SignatureSent",
    "StageCompleted",
    "StageEntered",
    "WorkflowBreached",
    "WorkflowCancelled",
    "WorkflowCompleted",
    "WorkflowEscalated",
    "WorkflowStarted",
    "WORKFLOW_EVENT_TYPES",
    # Actions
    "ActionContext",
    "ActionFactory",
    "ActionProvider",
    "ActionRegistry",
    "ActionResult",
    "ApproveAction",
    "DelayAction",
    "DevAutoAction",
    "EmailAction",
    "NotifyAction",
    "RejectAction",
    # Providers
    "AIProvider",
    "CompositeContextBuilder",
    "ContractProvider",
    "MetadataProvider",
    "ProviderRegistry",
    "RiskProvider",
    "SupplierProvider",
    "UserProvider",
    # Impact
    "ImpactAnalysisResult",
    "ImpactAnalyzer",
    # Templates
    "BUILT_IN_PACKS",
    "get_built_in_pack",
    "list_built_in_packs",
    "seed_built_in_packs",
]
