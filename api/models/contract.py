"""Pydantic models for contract entities.

Defines the data structures for contracts, contract versions,
and contract search operations.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class ContractStatus(str, Enum):
    """Status of a contract in the system."""

    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"
    ARCHIVED = "archived"


class ContractType(str, Enum):
    """Type of contract document."""

    NDA = "nda"
    SERVICE_AGREEMENT = "service_agreement"
    LICENSE = "license"
    EMPLOYMENT = "employment"
    LEASE = "lease"
    SOW = "statement_of_work"
    MSa = "master_service_agreement"
    OTHER = "other"


class ContractCreate(BaseModel):
    """Schema for creating a new contract record."""

    filename: str = Field(..., description="Original filename", max_length=500)
    content_type: str = Field(..., description="MIME type")
    tenant_id: str = Field(..., description="Tenant identifier")
    user_id: str = Field(..., description="Uploading user")
    contract_type: Optional[ContractType] = Field(None, description="Contract type")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    tags: List[str] = Field(default_factory=list, description="Contract tags")

    @field_validator("filename")
    @classmethod
    def filename_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Filename must not be empty")
        return v.strip()


class ContractVersion(BaseModel):
    """Schema for a contract version."""

    version_id: str = Field(..., description="Version identifier")
    contract_id: str = Field(..., description="Parent contract identifier")
    version_number: int = Field(..., ge=1, description="Sequential version number")
    filename: str = Field(..., description="Filename for this version")
    file_size: int = Field(..., ge=0, description="File size in bytes")
    checksum: str = Field(..., description="SHA-256 checksum of file")
    created_at: datetime = Field(..., description="Version creation time")
    created_by: str = Field(..., description="User who created this version")
    change_notes: Optional[str] = Field(None, description="Description of changes")


class Contract(BaseModel):
    """Full contract model with all metadata."""

    contract_id: str = Field(..., description="Unique contract identifier")
    tenant_id: str = Field(..., description="Tenant identifier")
    user_id: str = Field(..., description="Owner user ID")
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type")
    file_size: int = Field(default=0, ge=0, description="File size in bytes")
    status: ContractStatus = Field(
        default=ContractStatus.PENDING, description="Processing status"
    )
    contract_type: Optional[ContractType] = Field(None, description="Contract type")
    version: int = Field(default=1, ge=1, description="Current version number")
    total_pages: int = Field(default=0, ge=0, description="Number of pages")
    total_clauses: int = Field(default=0, ge=0, description="Number of clauses")
    total_chunks: int = Field(default=0, ge=0, description="Number of chunks")
    tags: List[str] = Field(default_factory=list, description="Tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    checksum: Optional[str] = Field(None, description="SHA-256 checksum")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    archived_at: Optional[datetime] = Field(None, description="Archival timestamp")


class ContractSearch(BaseModel):
    """Schema for contract search parameters."""

    query: Optional[str] = Field(None, description="Full-text search query")
    tenant_id: Optional[str] = Field(None, description="Filter by tenant")
    status: Optional[ContractStatus] = Field(None, description="Filter by status")
    contract_type: Optional[ContractType] = Field(None, description="Filter by type")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    date_from: Optional[datetime] = Field(None, description="Start date filter")
    date_to: Optional[datetime] = Field(None, description="End date filter")
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    sort_by: str = Field(default="created_at", description="Sort field")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")
