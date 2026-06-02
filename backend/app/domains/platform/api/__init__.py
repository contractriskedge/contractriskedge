"""API Governance — versioning, schema registry, OpenAPI governance, deprecation lifecycle.

Prevents API endpoint sprawl and ensures backward compatibility.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ApiVersionStatus(str, Enum):
    ACTIVE = "active"               # Fully supported
    DEPRECATED = "deprecated"       # Still functional, but will be removed
    SUNSET = "sunset"               # Will be removed on a specific date
    REMOVED = "removed"             # No longer available


class ApiChangeType(str, Enum):
    BACKWARD_COMPATIBLE = "backward_compatible"   # Add field, add endpoint
    BACKWARD_INCOMPATIBLE = "backward_incompatible"  # Remove field, change type
    DEPRECATION = "deprecation"                    # Mark as deprecated
    SECURITY = "security"                          # Security fix
    PERFORMANCE = "performance"                    # Performance improvement


@dataclass
class ApiVersion:
    """An API version with lifecycle management."""
    version: str                    # "v1", "v2", "2024-01-01"
    status: ApiVersionStatus
    released_at: str
    deprecated_at: str | None = None
    sunset_at: str | None = None
    migration_guide: str | None = None
    changelog: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ApiEndpoint:
    """A registered API endpoint with metadata."""
    path: str
    method: str  # GET, POST, PUT, DELETE, PATCH
    version: str
    summary: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    auth_required: bool = True
    rate_limit: str = "100/minute"
    permissions: list[str] = field(default_factory=list)
    deprecated: bool = False
    deprecation_message: str = ""
    request_schema: str = ""
    response_schema: str = ""


@dataclass
class SchemaVersion:
    """A versioned schema for request/response validation."""
    schema_name: str
    version: str
    json_schema: dict[str, Any]
    status: ApiVersionStatus
    released_at: str
    changelog: str = ""


@dataclass
class ApiGovernanceService:
    """Centralized API governance — prevents endpoint sprawl and contract drift.

    Provides:
    - API version registry and lifecycle management
    - Schema registry for request/response validation
    - OpenAPI governance and compliance checks
    - Deprecation lifecycle with sunset policies
    - Request quota management per endpoint
    - Webhook signature verification
    """

    _versions: dict[str, ApiVersion] = field(default_factory=dict)
    _endpoints: dict[str, ApiEndpoint] = field(default_factory=dict)
    _schemas: dict[str, list[SchemaVersion]] = field(default_factory=dict)

    # ── Version Management ─────────────────────────────────────────

    def register_version(self, version: ApiVersion) -> None:
        """Register an API version."""
        self._versions[version.version] = version
        logger.info("Registered API version: %s (%s)", version.version, version.status.value)

    def get_version(self, version: str) -> ApiVersion | None:
        """Get an API version."""
        return self._versions.get(version)

    def get_active_versions(self) -> list[ApiVersion]:
        """Get all active API versions."""
        return [v for v in self._versions.values() if v.status == ApiVersionStatus.ACTIVE]

    def get_sunset_versions(self) -> list[ApiVersion]:
        """Get versions past their sunset date."""
        now = datetime.utcnow().isoformat()
        return [
            v for v in self._versions.values()
            if v.sunset_at and v.sunset_at < now and v.status != ApiVersionStatus.REMOVED
        ]

    def deprecate_version(self, version: str, sunset_days: int = 180, migration_guide: str = "") -> None:
        """Deprecate an API version with sunset timeline."""
        api_version = self._versions.get(version)
        if not api_version:
            raise ValueError(f"Version {version} not found")
        api_version.status = ApiVersionStatus.DEPRECATED
        api_version.deprecated_at = datetime.utcnow().isoformat()
        api_version.sunset_at = (datetime.utcnow() + timedelta(days=sunset_days)).isoformat()
        api_version.migration_guide = migration_guide
        logger.warning("Deprecated API version %s (sunset: %s)", version, api_version.sunset_at)

    # ── Endpoint Registry ──────────────────────────────────────────

    def register_endpoint(self, endpoint: ApiEndpoint) -> None:
        """Register an API endpoint."""
        key = f"{endpoint.method}:{endpoint.path}:{endpoint.version}"
        self._endpoints[key] = endpoint

    def get_endpoints_by_version(self, version: str) -> list[ApiEndpoint]:
        """Get all endpoints for a version."""
        return [e for e in self._endpoints.values() if e.version == version]

    def get_endpoints_by_tag(self, tag: str) -> list[ApiEndpoint]:
        """Get all endpoints with a specific tag."""
        return [e for e in self._endpoints.values() if tag in e.tags]

    def check_endpoint_compliance(self, endpoint: ApiEndpoint) -> list[str]:
        """Check an endpoint for governance compliance."""
        violations = []
        if not endpoint.summary:
            violations.append("Missing summary")
        if not endpoint.tags:
            violations.append("Missing tags")
        if endpoint.deprecated and not endpoint.deprecation_message:
            violations.append("Deprecated endpoint missing deprecation message")
        return violations

    # ── Schema Registry ────────────────────────────────────────────

    def register_schema(self, schema: SchemaVersion) -> None:
        """Register a schema version."""
        if schema.schema_name not in self._schemas:
            self._schemas[schema.schema_name] = []
        self._schemas[schema.schema_name].append(schema)
        self._schemas[schema.schema_name].sort(key=lambda s: s.version, reverse=True)

    def get_schema(self, schema_name: str, version: str | None = None) -> SchemaVersion | None:
        """Get a schema, optionally at a specific version."""
        versions = self._schemas.get(schema_name, [])
        if not versions:
            return None
        if version:
            for s in versions:
                if s.version == version:
                    return s
            return None
        return versions[0]  # Latest

    def validate_schema_compatibility(self, schema_name: str, new_schema: dict[str, Any]) -> list[str]:
        """Check if a new schema version is backward compatible."""
        current = self.get_schema(schema_name)
        if not current:
            return []

        incompatibilities = []
        old_props = current.json_schema.get("properties", {})
        new_props = new_schema.get("properties", {})

        # Check for removed properties
        for prop in old_props:
            if prop not in new_props:
                incompatibilities.append(f"Removed property: {prop}")

        # Check for changed types
        for prop in old_props:
            if prop in new_props:
                old_type = old_props[prop].get("type")
                new_type = new_props[prop].get("type")
                if old_type and new_type and old_type != new_type:
                    incompatibilities.append(f"Changed type of '{prop}': {old_type} -> {new_type}")

        # Check for required->optional changes
        old_required = set(current.json_schema.get("required", []))
        new_required = set(new_schema.get("required", []))
        added_required = new_required - old_required
        if added_required:
            incompatibilities.append(f"New required fields: {added_required}")

        return incompatibilities

    # ── Webhook Signature ──────────────────────────────────────────

    def verify_webhook_signature(self, payload: bytes, signature: str, secret: str) -> bool:
        """Verify a webhook payload signature."""
        import hmac
        import hashlib
        expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(f"sha256={expected}", signature)

    # ── Governance Report ──────────────────────────────────────────

    def get_governance_report(self) -> dict[str, Any]:
        """Get a comprehensive API governance report."""
        active_versions = self.get_active_versions()
        sunset_versions = self.get_sunset_versions()
        total_endpoints = len(self._endpoints)

        compliance_issues = []
        for endpoint in self._endpoints.values():
            issues = self.check_endpoint_compliance(endpoint)
            if issues:
                compliance_issues.append({
                    "endpoint": f"{endpoint.method} {endpoint.path}",
                    "issues": issues,
                })

        return {
            "active_versions": [v.version for v in active_versions],
            "sunset_versions": [{"version": v.version, "sunset_at": v.sunset_at} for v in sunset_versions],
            "total_endpoints": total_endpoints,
            "registered_schemas": list(self._schemas.keys()),
            "compliance_issues": compliance_issues,
            "deprecation_count": sum(1 for e in self._endpoints.values() if e.deprecated),
        }
