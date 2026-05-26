"""Legal Playbook + Policy Engine SQLAlchemy models.

Covers:
- legal_playbooks / playbook_versions: versioned playbook management
- clause_standards: approved/forbidden/preferred clause language
- policy_rules: conditional rule engine for clause evaluation
- policy_evaluations: per-contract evaluation results
- approval_thresholds: risk/value-based approval routing
- clause_recommendations: AI-generated clause suggestions
- policy_overrides: override requests with audit lineage
- governance_audit_events: immutable audit trail
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

from app.kernel.database.base import Base


# ── Enums ────────────────────────────────────────────────────────────


class PlaybookStatus(str, PyEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    SUPERSEDED = "superseded"


class ClauseCategory(str, PyEnum):
    INDEMNIFICATION = "indemnification"
    LIMITATION_OF_LIABILITY = "limitation_of_liability"
    CONFIDENTIALITY = "confidentiality"
    DATA_PRIVACY = "data_privacy"
    INTELLECTUAL_PROPERTY = "intellectual_property"
    TERMINATION = "termination"
    GOVERNING_LAW = "governing_law"
    DISPUTE_RESOLUTION = "dispute_resolution"
    FORCE_MAJEURE = "force_majeure"
    PAYMENT_TERMS = "payment_terms"
    WARRANTY = "warranty"
    INSURANCE = "insurance"
    COMPLIANCE = "compliance"
    AUDIT_RIGHTS = "audit_rights"
    ASSIGNMENT = "assignment"
    NON_COMPETE = "non_compete"
    NON_SOLICIT = "non_solicit"
    SLA = "sla"
    ESCROW = "escrow"
    GENERAL = "general"


class ClauseType(str, PyEnum):
    APPROVED = "approved"
    PREFERRED = "preferred"
    FALLBACK = "fallback"
    FORBIDDEN = "forbidden"
    CONDITIONAL = "conditional"


class RuleOperator(str, PyEnum):
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    IN = "in"
    NOT_IN = "not_in"
    MATCHES_REGEX = "matches_regex"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"
    MEETS_THRESHOLD = "meets_threshold"


class RuleEffect(str, PyEnum):
    ALLOW = "allow"
    BLOCK = "block"
    FLAG_FOR_REVIEW = "flag_for_review"
    REQUIRE_APPROVAL = "require_approval"
    REQUIRE_MANDATORY_CLAUSE = "require_mandatory_clause"
    RECOMMEND_FALLBACK = "recommend_fallback"
    ESCALATE = "escalate"


class DeviationSeverity(str, PyEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class OverrideStatus(str, PyEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class EvaluationStatus(str, PyEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ── Legal Playbooks ──────────────────────────────────────────────────


class LegalPlaybook(Base):
    """A versioned legal playbook containing clause standards and policy rules."""
    __tablename__ = "legal_playbooks"

    playbook_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    jurisdiction = Column(Text, nullable=True)  # e.g., 'US', 'UK', 'EU', 'APAC'
    practice_area = Column(Text, nullable=True)  # e.g., 'commercial', 'employment', 'real_estate'
    status = Column(SAEnum("draft", "published", "archived", "superseded", name="playbook_status", create_type=True), nullable=False, default=PlaybookStatus.DRAFT)

    active_version_id = Column(UUID, nullable=True)
    version_count = Column(Integer, nullable=False, default=1)

    tags = Column(ARRAY(Text), nullable=False, default=list)
    document_metadata = Column("metadata", JSONB, nullable=False, default=dict)

    created_by = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    archived_at = Column(DateTime(timezone=True), nullable=True)


class PlaybookVersion(Base):
    """Immutable version snapshot of a playbook at publish time."""
    __tablename__ = "playbook_versions"

    version_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    playbook_id = Column(UUID, ForeignKey("legal_playbooks.playbook_id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)

    version_number = Column(Integer, nullable=False)
    version_label = Column(Text, nullable=True)  # e.g., 'v2.1', '2024-Q3-release'
    change_notes = Column(Text, nullable=True)

    # Snapshot of playbook metadata at version creation
    snapshot = Column(JSONB, nullable=False, default=dict)

    # Version lineage
    parent_version_id = Column(UUID, nullable=True)
    is_draft = Column(Boolean, nullable=False, default=True)
    is_active = Column(Boolean, nullable=False, default=False)

    published_by = Column(Text, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# ── Clause Standards ────────────────────────────────────────────────


class ClauseStandard(Base):
    """Standardized clause language — approved, preferred, fallback, and forbidden clauses."""
    __tablename__ = "clause_standards"

    clause_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    playbook_id = Column(UUID, ForeignKey("legal_playbooks.playbook_id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)

    category = Column(SAEnum("indemnification", "limitation_of_liability", "confidentiality", "data_privacy", "intellectual_property", "termination", "governing_law", "dispute_resolution", "force_majeure", "payment_terms", "warranty", "insurance", "compliance", "audit_rights", "assignment", "non_compete", "non_solicit", "sla", "escrow", "general", name="clause_category", create_type=True), nullable=False)
    clause_type = Column(SAEnum("approved", "preferred", "fallback", "forbidden", "conditional", name="clause_type", create_type=True), nullable=False)

    title = Column(Text, nullable=False)
    body = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)

    # Fallback chain — if this clause is rejected, recommend these fallback IDs
    fallback_clause_ids = Column(ARRAY(UUID), nullable=False, default=list)

    # Applicability
    min_contract_value = Column(Float, nullable=True)
    max_contract_value = Column(Float, nullable=True)
    applicable_jurisdictions = Column(ARRAY(Text), nullable=False, default=list)
    applicable_industries = Column(ARRAY(Text), nullable=False, default=list)

    # Risk metadata
    risk_level = Column(Text, nullable=False, default="medium")  # 'critical', 'high', 'medium', 'low'
    risk_score = Column(Float, nullable=True)

    # Tags and metadata
    tags = Column(ARRAY(Text), nullable=False, default=list)
    document_metadata = Column("metadata", JSONB, nullable=False, default=dict)

    # Versioning — which playbook version this clause belongs to
    playbook_version_id = Column(UUID, ForeignKey("playbook_versions.version_id", ondelete="SET NULL"), nullable=True)

    is_active = Column(Boolean, nullable=False, default=True)
    effective_date = Column(DateTime(timezone=True), nullable=True)
    expiration_date = Column(DateTime(timezone=True), nullable=True)

    created_by = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


# ── Policy Rules ────────────────────────────────────────────────────


class PolicyRule(Base):
    """Conditional policy rule for clause evaluation, deviation detection, and approval routing."""
    __tablename__ = "policy_rules"

    rule_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    playbook_id = Column(UUID, ForeignKey("legal_playbooks.playbook_id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    rule_type = Column(Text, nullable=False)  # 'clause_required', 'clause_forbidden', 'deviation', 'approval', 'risk_threshold', 'value_threshold'

    priority = Column(Integer, nullable=False, default=100)  # lower = evaluated first
    is_active = Column(Boolean, nullable=False, default=True)
    is_mandatory = Column(Boolean, nullable=False, default=False)

    # Conditional logic (JSON structure)
    # {
    #   "operator": "equals|contains|greater_than|...",
    #   "field": "clause.category|contract.value|...",
    #   "value": "...",
    #   "conditions": [...]  # nested for AND/OR
    # }
    conditions = Column(JSONB, nullable=False, default=dict)

    # Rule effect when conditions match
    effect = Column(SAEnum("allow", "block", "flag_for_review", "require_approval", "require_mandatory_clause", "recommend_fallback", "escalate", name="rule_effect", create_type=True), nullable=False)
    effect_config = Column(JSONB, nullable=False, default=dict)  # e.g., {"approval_role": "legal_director", "fallback_clause_id": "..."}

    # Clause references
    target_clause_id = Column(UUID, ForeignKey("clause_standards.clause_id", ondelete="SET NULL"), nullable=True)
    target_category = Column(Text, nullable=True)

    # Applicability
    applicable_jurisdictions = Column(ARRAY(Text), nullable=False, default=list)
    applicable_industries = Column(ARRAY(Text), nullable=False, default=list)
    min_contract_value = Column(Float, nullable=True)
    max_contract_value = Column(Float, nullable=True)

    effective_date = Column(DateTime(timezone=True), nullable=True)
    expiration_date = Column(DateTime(timezone=True), nullable=True)

    # Rule metadata
    tags = Column(ARRAY(Text), nullable=False, default=list)
    document_metadata = Column("metadata", JSONB, nullable=False, default=dict)

    created_by = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


# ── Policy Evaluations ──────────────────────────────────────────────


class PolicyEvaluation(Base):
    """Per-contract evaluation result — stores which rules matched and what deviations were found."""
    __tablename__ = "policy_evaluations"

    evaluation_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)

    # Entity being evaluated
    upload_id = Column(UUID, ForeignKey("upload_sessions.upload_id", ondelete="CASCADE"), nullable=False, index=True)
    review_id = Column(UUID, ForeignKey("contract_reviews.review_id", ondelete="SET NULL"), nullable=True)
    playbook_id = Column(UUID, ForeignKey("legal_playbooks.playbook_id", ondelete="SET NULL"), nullable=True)
    playbook_version_id = Column(UUID, ForeignKey("playbook_versions.version_id", ondelete="SET NULL"), nullable=True)

    status = Column(SAEnum("pending", "processing", "completed", "failed", name="eval_status", create_type=True), nullable=False, default=EvaluationStatus.PENDING)

    # Results summary
    total_rules_evaluated = Column(Integer, nullable=False, default=0)
    rules_passed = Column(Integer, nullable=False, default=0)
    rules_failed = Column(Integer, nullable=False, default=0)
    deviations_found = Column(Integer, nullable=False, default=0)
    mandatory_blocks = Column(Integer, nullable=False, default=0)
    approval_required = Column(Integer, nullable=False, default=0)

    # Overall risk score from evaluation
    risk_score = Column(Float, nullable=True)
    risk_level = Column(Text, nullable=True)  # 'critical', 'high', 'medium', 'low'

    # Full evaluation results
    results = Column(JSONB, nullable=False, default=list)  # list of per-rule evaluation results
    deviations = Column(JSONB, nullable=False, default=list)  # list of detected deviations
    recommendations = Column(JSONB, nullable=False, default=list)  # list of clause recommendations

    correlation_id = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# ── Approval Thresholds ─────────────────────────────────────────────


class ApprovalThreshold(Base):
    """Risk-based and value-based approval routing thresholds."""
    __tablename__ = "approval_thresholds"

    threshold_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)
    playbook_id = Column(UUID, ForeignKey("legal_playbooks.playbook_id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)

    # Threshold type
    threshold_type = Column(Text, nullable=False)  # 'risk_score', 'contract_value', 'clause_category', 'deviation_severity', 'override'

    # Comparison
    operator = Column(Text, nullable=False, default="greater_than")  # 'greater_than', 'less_than', 'equals', 'in_range'
    min_value = Column(Float, nullable=True)
    max_value = Column(Float, nullable=True)

    # Target clause category (for clause_category type)
    target_category = Column(Text, nullable=True)

    # Approval routing
    approval_role = Column(Text, nullable=False)  # 'legal_manager', 'legal_director', 'general_counsel', 'cfo', 'ceo'
    approval_level = Column(Integer, nullable=False, default=1)  # escalation level
    fallback_approval_role = Column(Text, nullable=True)

    # Auto-approval
    auto_approve = Column(Boolean, nullable=False, default=False)
    auto_approve_conditions = Column(JSONB, nullable=True)

    # SLA for approval
    sla_hours = Column(Integer, nullable=True)

    is_active = Column(Boolean, nullable=False, default=True)
    priority = Column(Integer, nullable=False, default=100)

    created_by = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


# ── Clause Recommendations ─────────────────────────────────────────


class ClauseRecommendation(Base):
    """AI-generated clause recommendations for a specific contract review."""
    __tablename__ = "clause_recommendations"

    recommendation_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)

    evaluation_id = Column(UUID, ForeignKey("policy_evaluations.evaluation_id", ondelete="CASCADE"), nullable=False, index=True)
    upload_id = Column(UUID, ForeignKey("upload_sessions.upload_id", ondelete="CASCADE"), nullable=False)
    review_id = Column(UUID, ForeignKey("contract_reviews.review_id", ondelete="SET NULL"), nullable=True)

    # Source clause standard (if recommending from playbook)
    clause_id = Column(UUID, ForeignKey("clause_standards.clause_id", ondelete="SET NULL"), nullable=True)
    clause_category = Column(Text, nullable=False)
    clause_type = Column(Text, nullable=False)

    title = Column(Text, nullable=False)
    body = Column(Text, nullable=False)
    rationale = Column(Text, nullable=True)

    # Recommendation metadata
    confidence_score = Column(Float, nullable=True)
    risk_reduction = Column(Text, nullable=True)  # 'critical', 'high', 'medium', 'low'
    priority = Column(Integer, nullable=False, default=50)

    # Status
    is_applied = Column(Boolean, nullable=False, default=False)
    applied_at = Column(DateTime(timezone=True), nullable=True)
    applied_by = Column(Text, nullable=True)

    # Deviation context
    deviation_id = Column(UUID, nullable=True)
    replaces_clause_text = Column(Text, nullable=True)

    document_metadata = Column("metadata", JSONB, nullable=False, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# ── Policy Overrides ────────────────────────────────────────────────


class PolicyOverride(Base):
    """Request to override a policy rule or deviation — with approval workflow and audit lineage."""
    __tablename__ = "policy_overrides"

    override_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)

    evaluation_id = Column(UUID, ForeignKey("policy_evaluations.evaluation_id", ondelete="CASCADE"), nullable=False, index=True)
    rule_id = Column(UUID, ForeignKey("policy_rules.rule_id", ondelete="SET NULL"), nullable=True)
    upload_id = Column(UUID, ForeignKey("upload_sessions.upload_id", ondelete="CASCADE"), nullable=False)
    review_id = Column(UUID, ForeignKey("contract_reviews.review_id", ondelete="SET NULL"), nullable=True)

    # Override details
    override_type = Column(Text, nullable=False)  # 'rule_exception', 'deviation_waiver', 'clause_substitution', 'threshold_override'
    justification = Column(Text, nullable=False)
    risk_assessment = Column(Text, nullable=True)
    proposed_alternative = Column(Text, nullable=True)

    # Status
    status = Column(SAEnum("pending", "approved", "rejected", "expired", "cancelled", name="override_status", create_type=True), nullable=False, default=OverrideStatus.PENDING)

    # Approval chain
    requested_by = Column(Text, nullable=False)
    requested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reviewed_by = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)

    # Expiration
    effective_date = Column(DateTime(timezone=True), nullable=True)
    expiration_date = Column(DateTime(timezone=True), nullable=True)

    # Audit lineage
    previous_override_id = Column(UUID, nullable=True)  # chain of overrides for same clause
    correlation_id = Column(Text, nullable=True)

    document_metadata = Column("metadata", JSONB, nullable=False, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


# ── Governance Audit Events ─────────────────────────────────────────


class GovernanceAuditEvent(Base):
    """Immutable audit trail for all playbook and policy governance actions."""
    __tablename__ = "governance_audit_events"

    event_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID, ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False, index=True)

    event_type = Column(Text, nullable=False, index=True)
    # 'playbook.created', 'playbook.published', 'playbook.archived', 'playbook.rolled_back',
    # 'clause.created', 'clause.updated', 'clause.deactivated',
    # 'rule.created', 'rule.updated', 'rule.activated', 'rule.deactivated',
    # 'evaluation.completed', 'deviation.detected',
    # 'override.requested', 'override.approved', 'override.rejected', 'override.expired',
    # 'threshold.created', 'threshold.updated',
    # 'recommendation.applied', 'policy.context_injected'

    entity_type = Column(Text, nullable=False)  # 'playbook', 'clause', 'rule', 'evaluation', 'override', 'threshold'
    entity_id = Column(UUID, nullable=False)

    # Actor
    actor_id = Column(Text, nullable=False)
    actor_role = Column(Text, nullable=True)

    # Change details
    previous_state = Column(JSONB, nullable=True)
    new_state = Column(JSONB, nullable=True)
    change_summary = Column(Text, nullable=True)

    # Correlation
    correlation_id = Column(Text, nullable=True)
    request_id = Column(Text, nullable=True)

    # Source
    source = Column(Text, nullable=False, default="api")  # 'api', 'worker', 'system', 'ai'

    document_metadata = Column("metadata", JSONB, nullable=False, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
