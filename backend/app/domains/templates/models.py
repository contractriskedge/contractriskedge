"""Template Library ORM models — tenant-isolated, versioned, auditable."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, Enum, ForeignKey, Index, Integer, String, Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.kernel.database.session import Base


class TemplateCategory(Base):
    """Template categories — NDA, MSA, SOW, etc."""

    __tablename__ = "template_categories"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_template_categories_tenant_slug", "tenant_id", "slug", unique=True),
    )


class ContractTemplate(Base):
    """Master contract template record — each template has many versions."""

    __tablename__ = "contract_templates"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    category_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("template_categories.id"), nullable=True,
    )
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[dict] = mapped_column(JSONB, default=list)
    owner: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    business_unit: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default="draft", index=True,
    )  # draft, under_review, approved, deprecated, archived
    current_version_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True,
    )
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    default_workflow: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    """Workflow identifier for future Workflow Engine — e.g. 'standard', 'nda', 'procurement', 'high_value'."""
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )
    updated_by: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    category: Mapped[Optional["TemplateCategory"]] = relationship(
        "TemplateCategory", lazy="joined",
    )
    versions: Mapped[list["TemplateVersion"]] = relationship(
        "TemplateVersion", back_populates="template",
        lazy="selectin", order_by="TemplateVersion.version_number.desc()",
    )

    __table_args__ = (
        Index("ix_contract_templates_tenant_status", "tenant_id", "status"),
        Index("ix_contract_templates_tenant_category", "tenant_id", "category_id"),
    )


class TemplateVersion(Base):
    """A specific version of a template — stores the document content."""

    __tablename__ = "template_versions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    template_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("contract_templates.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    change_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    # Document content stored as DOCX binary in S3, reference here
    storage_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    storage_bucket: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    file_name: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str] = mapped_column(String(100), default="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    # Template variables stored as structured JSON
    variables: Mapped[dict] = mapped_column(JSONB, default=list)
    # Clause references — list of {clause_id, is_required, condition, display_order}
    clause_refs: Mapped[dict] = mapped_column(JSONB, default=list)
    # Full rendered text for preview (with placeholders visible)
    placeholder_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    updated_by: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    template: Mapped["ContractTemplate"] = relationship(
        "ContractTemplate", back_populates="versions",
    )

    __table_args__ = (
        Index("ix_template_versions_template_number", "template_id", "version_number", unique=True),
    )


class TemplateVariable(Base):
    """Known variables/placeholders across templates — reusable definitions."""

    __tablename__ = "template_variables"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(200), nullable=False)
    label: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    field_type: Mapped[str] = mapped_column(
        String(50), default="text",
    )  # text, currency, number, date, boolean, dropdown, multi_select, address, email, phone, url
    default_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    options: Mapped[dict] = mapped_column(JSONB, default=list)  # for dropdown/multi_select
    validation_rules: Mapped[dict] = mapped_column(JSONB, default=dict)  # {required, min, max, regex, etc.}
    help_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_template_variables_tenant_key", "tenant_id", "key"),
    )


class TemplateFavorite(Base):
    """User favorites for templates."""

    __tablename__ = "template_favorites"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    template_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("contract_templates.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_template_favorites_tenant_user_template", "tenant_id", "user_id", "template_id", unique=True),
    )


class GeneratedContract(Base):
    """A contract generated from a template — links to the review lifecycle."""

    __tablename__ = "generated_contracts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    template_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("contract_templates.id"), nullable=False,
    )
    template_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("template_versions.id"), nullable=False,
    )
    review_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    variable_values: Mapped[dict] = mapped_column(JSONB, default=dict)
    clause_selections: Mapped[dict] = mapped_column(JSONB, default=list)
    """List of {clause_id, clause_version, included, reason_removed, notes}."""
    idempotency_key: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, index=True,
    )
    """Unique key to prevent duplicate generation on retry."""
    generated_docx_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    generated_pdf_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    generated_content: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
    )
    """Rendered document text with variables substituted."""
    status: Mapped[str] = mapped_column(String(50), default="draft")
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_generated_contracts_tenant_template", "tenant_id", "template_id"),
    )


class TemplateClauseRef(Base):
    """Join table linking template versions to specific clause versions.

    This prevents silent updates to historical templates when a clause changes.
    Each reference pins the exact clause version used at template creation time.
    """

    __tablename__ = "template_clause_refs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    template_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("contract_templates.id", ondelete="CASCADE"),
        nullable=False,
    )
    template_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("template_versions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    clause_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("template_clauses.id", ondelete="RESTRICT"),
        nullable=False,
    )
    clause_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    """Pinned clause version — prevents silent updates to historical templates."""
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    condition_expression: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fallback_clause_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    effective_from: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_clause_refs_version_clause", "template_version_id", "clause_id", unique=True),
        Index("ix_clause_refs_tenant_template", "tenant_id", "template_id"),
    )


class TemplateClause(Base):
    """Reusable clause library with versioning and approval workflow.

    Each clause has its own version history and lifecycle:
        draft → legal_review → approved → published

    Templates reference specific clause versions via TemplateClauseRef,
    ensuring historical templates are never silently updated.
    """

    __tablename__ = "template_clauses"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    template_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("contract_templates.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    clause_type: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True,
    )  # payment, confidentiality, liability, governing_law, termination, etc.
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    risk_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # low, medium, high, critical
    ai_rewrite_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    fallback_clause_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True,
    )
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    is_conditional: Mapped[bool] = mapped_column(Boolean, default=False)
    condition_expression: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    """e.g. 'Country == \"Germany\"' or 'AutoRenewal == true'"""
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    # Approval workflow: draft → legal_review → approved → published
    status: Mapped[str] = mapped_column(String(50), default="draft", index=True)
    """draft, legal_review, approved, published, deprecated, archived"""
    version: Mapped[int] = mapped_column(Integer, default=1)
    change_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    """Description of what changed in this version."""
    approved_by: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    # Usage tracking
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    """Number of templates referencing this clause."""
    contract_usage_count: Mapped[int] = mapped_column(Integer, default=0)
    """Number of generated contracts using this clause."""
    tags: Mapped[dict] = mapped_column(JSONB, default=list)
    """Searchable tags for clause discovery."""
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    updated_by: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_template_clauses_tenant_type", "tenant_id", "clause_type"),
        Index("ix_template_clauses_tenant_template", "tenant_id", "template_id"),
    )


class TemplateUsageHistory(Base):
    """Audit trail for template usage — who generated what when."""

    __tablename__ = "template_usage_history"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    template_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("contract_templates.id"), nullable=False,
    )
    template_version_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("template_versions.id"), nullable=True,
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    # created, updated, published, archived, deleted, generated, version_created, approved, deprecated
    actor_id: Mapped[str] = mapped_column(String(200), nullable=False)
    details: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_template_usage_tenant_template", "tenant_id", "template_id"),
        Index("ix_template_usage_tenant_action", "tenant_id", "action"),
    )


class TemplatePackage(Base):
    """A curated collection of templates — industry starter packs, tenant onboarding, etc.

    Packages enable one-click import of complete template sets:
        Procurement → MSA, NDA, SOW, Supplier Code of Conduct, DPA
        Healthcare → BAA, MSA, DPA, Business Associate Agreement
        Banking → ISDA, MSA, NDA, Credit Agreement, Security Agreement

    This becomes especially valuable if ContractRiskEdge is commercialized
    with industry-specific starter packs.
    """

    __tablename__ = "template_packages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    """e.g. procurement, healthcare, banking, saas, manufacturing"""
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    tags: Mapped[dict] = mapped_column(JSONB, default=list)
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    updated_by: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    items: Mapped[list["TemplatePackageItem"]] = relationship(
        "TemplatePackageItem", back_populates="package",
        lazy="selectin", order_by="TemplatePackageItem.display_order",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_template_packages_tenant_industry", "tenant_id", "industry"),
    )


class TemplatePackageItem(Base):
    """A template within a package — preserves ordering and allows future metadata."""

    __tablename__ = "template_package_items"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    package_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("template_packages.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    template_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("contract_templates.id", ondelete="RESTRICT"),
        nullable=False,
    )
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    """Whether this template is mandatory when importing the package."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    package: Mapped["TemplatePackage"] = relationship(
        "TemplatePackage", back_populates="items",
    )

    __table_args__ = (
        Index("ix_package_items_package_template", "package_id", "template_id", unique=True),
    )
