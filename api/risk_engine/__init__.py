"""Risk engine module for AI Contract Risk Analyzer.

Provides comprehensive risk analysis including taxonomy definition,
prompt chain orchestration, severity scoring, output validation,
confidence calibration, escalation workflows, and jurisdictional
risk context.
"""

from __future__ import annotations

from .taxonomy import RiskTaxonomy, RiskCategoryDef, RiskSubType
from .schema import TaxonomySchema
from .validator import TaxonomyValidator
from .prompts import RiskPromptChain
from .chain import PromptChainOrchestrator
from .few_shot import FewShotExamples
from .severity import SeverityScorer
from .calibrator import CalibrationValidator
from .output_schema import (
    RiskFlagOutput,
    RiskFlagSet,
    LinkedEvidence,
    JurisdictionalConsideration,
    BenchmarkComparison,
    SuggestedAction,
)
from .schema_validator import OutputSchemaValidator
from .confidence import ConfidenceCalibrationEngine
from .escalation import EscalationWorkflow
from .jurisdiction import JurisdictionalRiskLayer

__all__ = [
    "RiskTaxonomy",
    "RiskCategoryDef",
    "RiskSubType",
    "TaxonomySchema",
    "TaxonomyValidator",
    "RiskPromptChain",
    "PromptChainOrchestrator",
    "FewShotExamples",
    "SeverityScorer",
    "CalibrationValidator",
    "RiskFlagOutput",
    "RiskFlagSet",
    "LinkedEvidence",
    "JurisdictionalConsideration",
    "BenchmarkComparison",
    "SuggestedAction",
    "OutputSchemaValidator",
    "ConfidenceCalibrationEngine",
    "EscalationWorkflow",
    "JurisdictionalRiskLayer",
]
