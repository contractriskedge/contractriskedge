"""Structured Error Taxonomy — centralized error codes for the entire application.

Provides a canonical registry of domain-specific error codes with:
  - Machine-readable error_code strings for programmatic handling
  - Human-readable default messages
  - Retry classification (retryable vs non-retryable)
  - HTTP status code mapping
  - Domain ownership attribution

Usage:
    from app.kernel.web.error_codes import ErrorCode, ErrorCategory

    raise AppError(error_code=ErrorCode.OCR_FAILURE)
    # Returns: {"error_code": "OCR_FAILURE", "message": "...", "status_code": 502}
"""

from __future__ import annotations

from enum import Enum
from typing import Optional


class ErrorCategory(str, Enum):
    """High-level category for grouping errors."""
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    INGESTION = "ingestion"
    EXTRACTION = "extraction"
    AI_ANALYSIS = "ai_analysis"
    PERSISTENCE = "persistence"
    INFRASTRUCTURE = "infrastructure"
    INTEGRATION = "integration"
    RATE_LIMITING = "rate_limiting"
    BUSINESS_LOGIC = "business_logic"
    UNKNOWN = "unknown"


class RetryAction(str, Enum):
    """Recommended action for handling the error."""
    RETRY_IMMEDIATELY = "retry_immediately"  # Safe to retry right away
    RETRY_WITH_BACKOFF = "retry_with_backoff"  # Retry with exponential backoff
    RETRY_LATER = "retry_later"  # Don't retry automatically; manual retry
    DO_NOT_RETRY = "do_not_retry"  # Fatal error; do not retry
    ESCALATE = "escalate"  # Requires human intervention


class ErrorCode(str, Enum):
    """Canonical, domain-specific error codes.

    Format: DOMAIN_SPECIFIC_ERROR
    Each code maps to a category, HTTP status, default message, and retry action.
    """

    # ── Validation Errors ─────────────────────────────────────────
    VALIDATION_FAILURE = "VALIDATION_FAILURE"
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_FILE_TYPE = "INVALID_FILE_TYPE"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    CHECKSUM_MISMATCH = "CHECKSUM_MISMATCH"
    MALWARE_DETECTED = "MALWARE_DETECTED"

    # ── Authentication / Authorization ────────────────────────────
    UNAUTHENTICATED = "UNAUTHENTICATED"
    UNAUTHORIZED = "UNAUTHORIZED"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    TENANT_MISMATCH = "TENANT_MISMATCH"

    # ── Ingestion Errors ──────────────────────────────────────────
    UPLOAD_FAILURE = "UPLOAD_FAILURE"
    UPLOAD_NOT_FOUND = "UPLOAD_NOT_FOUND"
    DUPLICATE_UPLOAD = "DUPLICATE_UPLOAD"
    STORAGE_UPLOAD_FAILURE = "STORAGE_UPLOAD_FAILURE"
    STORAGE_DOWNLOAD_FAILURE = "STORAGE_DOWNLOAD_FAILURE"
    INGESTION_STATE_INVALID = "INGESTION_STATE_INVALID"
    INGESTION_TIMEOUT = "INGESTION_TIMEOUT"
    INGESTION_RETRY_EXCEEDED = "INGESTION_RETRY_EXCEEDED"

    # ── Extraction / OCR Errors ───────────────────────────────────
    OCR_FAILURE = "OCR_FAILURE"
    OCR_TIMEOUT = "OCR_TIMEOUT"
    OCR_QUALITY_TOO_LOW = "OCR_QUALITY_TOO_LOW"
    EXTRACTION_FAILURE = "EXTRACTION_FAILURE"
    PARSER_FAILURE = "PARSER_FAILURE"
    UNSUPPORTED_DOCUMENT_FORMAT = "UNSUPPORTED_DOCUMENT_FORMAT"

    # ── Chunking / Embedding Errors ───────────────────────────────
    CHUNKING_FAILURE = "CHUNKING_FAILURE"
    EMBEDDING_FAILURE = "EMBEDDING_FAILURE"
    EMBEDDING_TIMEOUT = "EMBEDDING_TIMEOUT"
    VECTOR_WRITE_FAILURE = "VECTOR_WRITE_FAILURE"
    VECTOR_SEARCH_FAILURE = "VECTOR_SEARCH_FAILURE"

    # ── AI Analysis Errors ────────────────────────────────────────
    ANALYSIS_FAILURE = "ANALYSIS_FAILURE"
    ANALYSIS_TIMEOUT = "ANALYSIS_TIMEOUT"
    ANALYSIS_RATE_LIMITED = "ANALYSIS_RATE_LIMITED"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    INVALID_MODEL_RESPONSE = "INVALID_MODEL_RESPONSE"
    PROMPT_TOO_LONG = "PROMPT_TOO_LONG"
    AI_COST_LIMIT_EXCEEDED = "AI_COST_LIMIT_EXCEEDED"
    AI_RUN_NOT_FOUND = "AI_RUN_NOT_FOUND"

    # ── Persistence Errors ────────────────────────────────────────
    PERSISTENCE_FAILURE = "PERSISTENCE_FAILURE"
    DB_CONNECTION_FAILURE = "DB_CONNECTION_FAILURE"
    DB_SESSION_FAILURE = "DB_SESSION_FAILURE"
    ENTITY_NOT_FOUND = "ENTITY_NOT_FOUND"
    DUPLICATE_ENTITY = "DUPLICATE_ENTITY"
    CONSTRAINT_VIOLATION = "CONSTRAINT_VIOLATION"
    OPTIMISTIC_LOCK_FAILURE = "OPTIMISTIC_LOCK_FAILURE"

    # ── Review Errors ─────────────────────────────────────────────
    REVIEW_NOT_FOUND = "REVIEW_NOT_FOUND"
    REVIEW_STATE_INVALID = "REVIEW_STATE_INVALID"
    REVIEW_ALREADY_EXISTS = "REVIEW_ALREADY_EXISTS"
    REVIEW_NOT_EDITABLE = "REVIEW_NOT_EDITABLE"
    FINDING_NOT_FOUND = "FINDING_NOT_FOUND"
    REDLINE_NOT_FOUND = "REDLINE_NOT_FOUND"
    INVALID_REVIEW_TRANSITION = "INVALID_REVIEW_TRANSITION"

    # ── Integration Errors ────────────────────────────────────────
    INTEGRATION_FAILURE = "INTEGRATION_FAILURE"
    OAUTH_FAILURE = "OAUTH_FAILURE"
    WEBHOOK_DELIVERY_FAILURE = "WEBHOOK_DELIVERY_FAILURE"
    CONNECTOR_TIMEOUT = "CONNECTOR_TIMEOUT"
    SYNC_FAILURE = "SYNC_FAILURE"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    THIRD_PARTY_UNAVAILABLE = "THIRD_PARTY_UNAVAILABLE"

    # ── Infrastructure Errors ─────────────────────────────────────
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    DEPENDENCY_FAILURE = "DEPENDENCY_FAILURE"
    TIMEOUT = "TIMEOUT"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"

    # ── Business Logic Errors ─────────────────────────────────────
    BUSINESS_RULE_VIOLATION = "BUSINESS_RULE_VIOLATION"
    SLA_BREACHED = "SLA_BREACHED"
    ESCALATION_REQUIRED = "ESCALATION_REQUIRED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    CONFLICTING_STATE = "CONFLICTING_STATE"


# ── Error Code Registry ────────────────────────────────────────────

_ERROR_CODE_REGISTRY: dict[ErrorCode, dict] = {}


def _register(
    code: ErrorCode,
    status_code: int,
    default_message: str,
    category: ErrorCategory,
    retry_action: RetryAction,
    domain: str,
    description: str = "",
) -> None:
    _ERROR_CODE_REGISTRY[code] = {
        "error_code": code.value,
        "status_code": status_code,
        "message": default_message,
        "category": category.value,
        "retry_action": retry_action.value,
        "domain": domain,
        "description": description,
    }


# ── Validation ──
_register(ErrorCode.VALIDATION_FAILURE, 422, "Validation failed", ErrorCategory.VALIDATION, RetryAction.DO_NOT_RETRY, "shared", "Generic validation error")
_register(ErrorCode.INVALID_INPUT, 422, "Invalid input provided", ErrorCategory.VALIDATION, RetryAction.DO_NOT_RETRY, "shared", "Input data failed validation")
_register(ErrorCode.MISSING_REQUIRED_FIELD, 422, "Missing required field", ErrorCategory.VALIDATION, RetryAction.DO_NOT_RETRY, "shared", "A required field was not provided")
_register(ErrorCode.INVALID_FILE_TYPE, 422, "File type not supported", ErrorCategory.VALIDATION, RetryAction.DO_NOT_RETRY, "ingestion", "File extension or MIME type not in allowed list")
_register(ErrorCode.FILE_TOO_LARGE, 422, "File exceeds maximum size", ErrorCategory.VALIDATION, RetryAction.DO_NOT_RETRY, "ingestion", "File exceeds 100MB limit")
_register(ErrorCode.CHECKSUM_MISMATCH, 422, "Checksum verification failed", ErrorCategory.VALIDATION, RetryAction.RETRY_IMMEDIATELY, "ingestion", "Client and server checksums do not match")
_register(ErrorCode.MALWARE_DETECTED, 422, "Malware detected in file", ErrorCategory.VALIDATION, RetryAction.DO_NOT_RETRY, "security", "File failed malware scan")

# ── Auth ──
_register(ErrorCode.UNAUTHENTICATED, 401, "Authentication required", ErrorCategory.AUTHENTICATION, RetryAction.DO_NOT_RETRY, "auth", "No valid authentication credentials")
_register(ErrorCode.UNAUTHORIZED, 403, "Access denied", ErrorCategory.AUTHORIZATION, RetryAction.DO_NOT_RETRY, "auth", "Insufficient permissions for this resource")
_register(ErrorCode.TOKEN_EXPIRED, 401, "Token has expired", ErrorCategory.AUTHENTICATION, RetryAction.RETRY_IMMEDIATELY, "auth", "Auth token needs refresh")
_register(ErrorCode.INSUFFICIENT_PERMISSIONS, 403, "Insufficient permissions", ErrorCategory.AUTHORIZATION, RetryAction.DO_NOT_RETRY, "auth", "User lacks required role/permission")
_register(ErrorCode.TENANT_MISMATCH, 403, "Tenant access denied", ErrorCategory.AUTHORIZATION, RetryAction.DO_NOT_RETRY, "auth", "Cross-tenant access attempt detected")

# ── Ingestion ──
_register(ErrorCode.UPLOAD_FAILURE, 500, "File upload failed", ErrorCategory.INGESTION, RetryAction.RETRY_WITH_BACKOFF, "ingestion", "Upload pipeline encountered an error")
_register(ErrorCode.UPLOAD_NOT_FOUND, 404, "Upload not found", ErrorCategory.INGESTION, RetryAction.DO_NOT_RETRY, "ingestion", "Upload session does not exist")
_register(ErrorCode.DUPLICATE_UPLOAD, 409, "Duplicate upload detected", ErrorCategory.INGESTION, RetryAction.DO_NOT_RETRY, "ingestion", "File with identical checksum already exists")
_register(ErrorCode.STORAGE_UPLOAD_FAILURE, 502, "Failed to store file", ErrorCategory.INGESTION, RetryAction.RETRY_WITH_BACKOFF, "ingestion", "Object storage upload failed")
_register(ErrorCode.STORAGE_DOWNLOAD_FAILURE, 502, "Failed to retrieve file", ErrorCategory.INGESTION, RetryAction.RETRY_WITH_BACKOFF, "ingestion", "Object storage download failed")
_register(ErrorCode.INGESTION_STATE_INVALID, 409, "Invalid ingestion state transition", ErrorCategory.INGESTION, RetryAction.DO_NOT_RETRY, "ingestion", "State machine transition not allowed")
_register(ErrorCode.INGESTION_TIMEOUT, 504, "Ingestion pipeline timed out", ErrorCategory.INGESTION, RetryAction.RETRY_WITH_BACKOFF, "ingestion", "Ingestion exceeded time limit")
_register(ErrorCode.INGESTION_RETRY_EXCEEDED, 429, "Ingestion retry limit exceeded", ErrorCategory.INGESTION, RetryAction.ESCALATE, "ingestion", "Max retry attempts reached")

# ── OCR / Extraction ──
_register(ErrorCode.OCR_FAILURE, 502, "OCR processing failed", ErrorCategory.EXTRACTION, RetryAction.RETRY_WITH_BACKOFF, "extraction", "OCR engine returned an error")
_register(ErrorCode.OCR_TIMEOUT, 504, "OCR processing timed out", ErrorCategory.EXTRACTION, RetryAction.RETRY_WITH_BACKOFF, "extraction", "OCR took too long to complete")
_register(ErrorCode.OCR_QUALITY_TOO_LOW, 422, "OCR quality below threshold", ErrorCategory.EXTRACTION, RetryAction.DO_NOT_RETRY, "extraction", "Extracted text quality insufficient for analysis")
_register(ErrorCode.EXTRACTION_FAILURE, 502, "Text extraction failed", ErrorCategory.EXTRACTION, RetryAction.RETRY_WITH_BACKOFF, "extraction", "Document text extraction failed")
_register(ErrorCode.PARSER_FAILURE, 502, "Document parser failed", ErrorCategory.EXTRACTION, RetryAction.RETRY_WITH_BACKOFF, "extraction", "Document format parser error")
_register(ErrorCode.UNSUPPORTED_DOCUMENT_FORMAT, 422, "Unsupported document format", ErrorCategory.EXTRACTION, RetryAction.DO_NOT_RETRY, "extraction", "Document format cannot be processed")

# ── Embedding ──
_register(ErrorCode.CHUNKING_FAILURE, 502, "Document chunking failed", ErrorCategory.AI_ANALYSIS, RetryAction.RETRY_WITH_BACKOFF, "vectors", "Text chunking pipeline failed")
_register(ErrorCode.EMBEDDING_FAILURE, 502, "Embedding generation failed", ErrorCategory.AI_ANALYSIS, RetryAction.RETRY_WITH_BACKOFF, "vectors", "OpenAI embedding API returned error")
_register(ErrorCode.EMBEDDING_TIMEOUT, 504, "Embedding generation timed out", ErrorCategory.AI_ANALYSIS, RetryAction.RETRY_WITH_BACKOFF, "vectors", "Embedding API took too long")
_register(ErrorCode.VECTOR_WRITE_FAILURE, 502, "Vector storage write failed", ErrorCategory.PERSISTENCE, RetryAction.RETRY_WITH_BACKOFF, "vectors", "pgvector insert failed")
_register(ErrorCode.VECTOR_SEARCH_FAILURE, 502, "Vector search failed", ErrorCategory.AI_ANALYSIS, RetryAction.RETRY_WITH_BACKOFF, "search", "Semantic search query failed")

# ── AI Analysis ──
_register(ErrorCode.ANALYSIS_FAILURE, 502, "AI analysis failed", ErrorCategory.AI_ANALYSIS, RetryAction.RETRY_WITH_BACKOFF, "ai", "AI analysis pipeline error")
_register(ErrorCode.ANALYSIS_TIMEOUT, 504, "AI analysis timed out", ErrorCategory.AI_ANALYSIS, RetryAction.RETRY_WITH_BACKOFF, "ai", "AI model took too long to respond")
_register(ErrorCode.ANALYSIS_RATE_LIMITED, 429, "AI analysis rate limited", ErrorCategory.RATE_LIMITING, RetryAction.RETRY_WITH_BACKOFF, "ai", "OpenAI rate limit hit")
_register(ErrorCode.MODEL_UNAVAILABLE, 503, "AI model unavailable", ErrorCategory.AI_ANALYSIS, RetryAction.RETRY_LATER, "ai", "OpenAI model is currently unavailable")
_register(ErrorCode.INVALID_MODEL_RESPONSE, 502, "Invalid AI model response", ErrorCategory.AI_ANALYSIS, RetryAction.RETRY_IMMEDIATELY, "ai", "Model returned unparseable output")
_register(ErrorCode.PROMPT_TOO_LONG, 422, "Prompt exceeds token limit", ErrorCategory.AI_ANALYSIS, RetryAction.DO_NOT_RETRY, "ai", "Input context exceeds model maximum")
_register(ErrorCode.AI_COST_LIMIT_EXCEEDED, 429, "AI cost limit exceeded", ErrorCategory.RATE_LIMITING, RetryAction.ESCALATE, "ai", "Tenant AI budget exhausted")
_register(ErrorCode.AI_RUN_NOT_FOUND, 404, "AI analysis run not found", ErrorCategory.AI_ANALYSIS, RetryAction.DO_NOT_RETRY, "ai", "No analysis run with given ID")

# ── Persistence ──
_register(ErrorCode.PERSISTENCE_FAILURE, 500, "Data persistence failed", ErrorCategory.PERSISTENCE, RetryAction.RETRY_WITH_BACKOFF, "shared", "Database write failed")
_register(ErrorCode.DB_CONNECTION_FAILURE, 503, "Database connection failed", ErrorCategory.INFRASTRUCTURE, RetryAction.RETRY_WITH_BACKOFF, "shared", "Cannot connect to database")
_register(ErrorCode.DB_SESSION_FAILURE, 500, "Database session error", ErrorCategory.PERSISTENCE, RetryAction.RETRY_IMMEDIATELY, "shared", "Session management error")
_register(ErrorCode.ENTITY_NOT_FOUND, 404, "Resource not found", ErrorCategory.PERSISTENCE, RetryAction.DO_NOT_RETRY, "shared", "Requested entity does not exist")
_register(ErrorCode.DUPLICATE_ENTITY, 409, "Resource already exists", ErrorCategory.PERSISTENCE, RetryAction.DO_NOT_RETRY, "shared", "Entity with same key exists")
_register(ErrorCode.CONSTRAINT_VIOLATION, 409, "Constraint violation", ErrorCategory.PERSISTENCE, RetryAction.DO_NOT_RETRY, "shared", "Database constraint violation")
_register(ErrorCode.OPTIMISTIC_LOCK_FAILURE, 409, "Concurrent modification detected", ErrorCategory.PERSISTENCE, RetryAction.RETRY_IMMEDIATELY, "shared", "Entity was modified by another request")

# ── Review ──
_register(ErrorCode.REVIEW_NOT_FOUND, 404, "Review not found", ErrorCategory.BUSINESS_LOGIC, RetryAction.DO_NOT_RETRY, "review", "Contract review does not exist")
_register(ErrorCode.REVIEW_STATE_INVALID, 409, "Invalid review state", ErrorCategory.BUSINESS_LOGIC, RetryAction.DO_NOT_RETRY, "review", "Review is in an unexpected state")
_register(ErrorCode.REVIEW_ALREADY_EXISTS, 409, "Review already exists", ErrorCategory.BUSINESS_LOGIC, RetryAction.DO_NOT_RETRY, "review", "Upload already has a review")
_register(ErrorCode.REVIEW_NOT_EDITABLE, 409, "Review is not editable", ErrorCategory.BUSINESS_LOGIC, RetryAction.DO_NOT_RETRY, "review", "Review cannot be modified in current state")
_register(ErrorCode.FINDING_NOT_FOUND, 404, "Finding not found", ErrorCategory.BUSINESS_LOGIC, RetryAction.DO_NOT_RETRY, "review", "AI finding does not exist")
_register(ErrorCode.REDLINE_NOT_FOUND, 404, "Redline not found", ErrorCategory.BUSINESS_LOGIC, RetryAction.DO_NOT_RETRY, "review", "Redline suggestion does not exist")
_register(ErrorCode.INVALID_REVIEW_TRANSITION, 409, "Invalid review status transition", ErrorCategory.BUSINESS_LOGIC, RetryAction.DO_NOT_RETRY, "review", "Status change not allowed")

# ── Integration ──
_register(ErrorCode.INTEGRATION_FAILURE, 502, "Integration failed", ErrorCategory.INTEGRATION, RetryAction.RETRY_WITH_BACKOFF, "integrations", "Third-party integration error")
_register(ErrorCode.OAUTH_FAILURE, 502, "OAuth authentication failed", ErrorCategory.INTEGRATION, RetryAction.RETRY_LATER, "integrations", "OAuth token refresh/acquire failed")
_register(ErrorCode.WEBHOOK_DELIVERY_FAILURE, 502, "Webhook delivery failed", ErrorCategory.INTEGRATION, RetryAction.RETRY_WITH_BACKOFF, "integrations", "Webhook endpoint unreachable")
_register(ErrorCode.CONNECTOR_TIMEOUT, 504, "Connector timed out", ErrorCategory.INTEGRATION, RetryAction.RETRY_WITH_BACKOFF, "integrations", "Third-party connector timeout")
_register(ErrorCode.SYNC_FAILURE, 502, "Data sync failed", ErrorCategory.INTEGRATION, RetryAction.RETRY_WITH_BACKOFF, "integrations", "Integration sync pipeline error")
_register(ErrorCode.RATE_LIMIT_EXCEEDED, 429, "Rate limit exceeded", ErrorCategory.RATE_LIMITING, RetryAction.RETRY_WITH_BACKOFF, "shared", "API rate limit hit")
_register(ErrorCode.THIRD_PARTY_UNAVAILABLE, 503, "Third-party service unavailable", ErrorCategory.INTEGRATION, RetryAction.RETRY_LATER, "integrations", "External service is down")

# ── Infrastructure ──
_register(ErrorCode.SERVICE_UNAVAILABLE, 503, "Service unavailable", ErrorCategory.INFRASTRUCTURE, RetryAction.RETRY_LATER, "shared", "Service is temporarily unavailable")
_register(ErrorCode.INTERNAL_ERROR, 500, "Internal server error", ErrorCategory.UNKNOWN, RetryAction.ESCALATE, "shared", "Unexpected internal error")
_register(ErrorCode.DEPENDENCY_FAILURE, 502, "Dependency failure", ErrorCategory.INFRASTRUCTURE, RetryAction.RETRY_WITH_BACKOFF, "shared", "Upstream dependency failed")
_register(ErrorCode.TIMEOUT, 504, "Request timed out", ErrorCategory.INFRASTRUCTURE, RetryAction.RETRY_WITH_BACKOFF, "shared", "Operation exceeded time limit")
_register(ErrorCode.NOT_IMPLEMENTED, 501, "Not implemented", ErrorCategory.UNKNOWN, RetryAction.DO_NOT_RETRY, "shared", "Feature not yet implemented")

# ── Business Logic ──
_register(ErrorCode.BUSINESS_RULE_VIOLATION, 422, "Business rule violation", ErrorCategory.BUSINESS_LOGIC, RetryAction.DO_NOT_RETRY, "shared", "Operation violates business rules")
_register(ErrorCode.SLA_BREACHED, 409, "SLA deadline breached", ErrorCategory.BUSINESS_LOGIC, RetryAction.ESCALATE, "review", "Review SLA deadline has passed")
_register(ErrorCode.ESCALATION_REQUIRED, 409, "Escalation required", ErrorCategory.BUSINESS_LOGIC, RetryAction.ESCALATE, "review", "Review requires escalation")
_register(ErrorCode.APPROVAL_REQUIRED, 403, "Approval required", ErrorCategory.BUSINESS_LOGIC, RetryAction.DO_NOT_RETRY, "review", "Operation requires approval")
_register(ErrorCode.CONFLICTING_STATE, 409, "Conflicting state", ErrorCategory.BUSINESS_LOGIC, RetryAction.DO_NOT_RETRY, "shared", "Operation conflicts with current state")


# ── Public API ─────────────────────────────────────────────────────


def get_error_info(error_code: ErrorCode) -> dict:
    """Get the full error info for a given error code.

    Returns a dict with keys: error_code, status_code, message, category,
    retry_action, domain, description.
    """
    return _ERROR_CODE_REGISTRY.get(error_code, {
        "error_code": "UNKNOWN_ERROR",
        "status_code": 500,
        "message": "An unknown error occurred",
        "category": ErrorCategory.UNKNOWN.value,
        "retry_action": RetryAction.ESCALATE.value,
        "domain": "unknown",
        "description": "Unrecognized error code",
    })


def is_retryable(error_code: ErrorCode) -> bool:
    """Check if an error is safe to retry."""
    info = get_error_info(error_code)
    return info["retry_action"] in (
        RetryAction.RETRY_IMMEDIATELY.value,
        RetryAction.RETRY_WITH_BACKOFF.value,
    )


def get_http_status(error_code: ErrorCode) -> int:
    """Get the HTTP status code for an error code."""
    return get_error_info(error_code)["status_code"]


def get_error_message(error_code: ErrorCode) -> str:
    """Get the default human-readable message for an error code."""
    return get_error_info(error_code)["message"]


def make_error_response(error_code: ErrorCode, message: Optional[str] = None,
                         details: Optional[dict] = None) -> dict:
    """Create a standardized error response dict.

    Returns:
        {
            "error_code": "OCR_FAILURE",
            "message": "OCR processing failed",
            "status_code": 502,
            "category": "extraction",
            "retryable": True,
            "details": {...}
        }
    """
    info = get_error_info(error_code)
    return {
        "error_code": info["error_code"],
        "message": message or info["message"],
        "status_code": info["status_code"],
        "category": info["category"],
        "retryable": is_retryable(error_code),
        "details": details,
    }
