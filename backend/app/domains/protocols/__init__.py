"""Enterprise Protocol Layer — interoperable protocols for workflow exchange, audit exchange, explainability, replay portability, policy interoperability, obligation interchange, federated event contracts.

Enterprise interoperability infrastructure — the foundation for an industry operating standard.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ProtocolVersion(str, Enum):
    V1_0_0 = "1.0.0"


@dataclass
class ProtocolSchema:
    """A protocol schema defining an interoperability standard."""
    protocol: str
    version: ProtocolVersion
    description: str
    schema_def: dict[str, Any] = field(default_factory=dict)
    required_fields: list[str] = field(default_factory=list)


@dataclass
class WorkflowExchangeProtocol:
    """Protocol for exchanging workflow definitions between systems.

    Enables:
    - Import/export workflow definitions
    - Cross-system workflow migration
    - Workflow marketplace distribution
    """

    @staticmethod
    def get_schema() -> ProtocolSchema:
        return ProtocolSchema(
            protocol="workflow_exchange",
            version=ProtocolVersion.V1_0_0,
            description="Standard format for exchanging workflow definitions between ContractEdge instances",
            schema_def={
                "type": "object",
                "properties": {
                    "protocol_version": {"type": "string", "enum": ["1.0.0"]},
                    "workflow": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "version": {"type": "string"},
                            "nodes": {"type": "array"},
                            "edges": {"type": "array"},
                            "sla_seconds": {"type": "integer"},
                            "tags": {"type": "array"},
                        },
                        "required": ["name", "nodes", "edges"],
                    },
                    "metadata": {
                        "type": "object",
                        "properties": {
                            "exported_at": {"type": "string"},
                            "source_version": {"type": "string"},
                            "checksum": {"type": "string"},
                        },
                    },
                },
                "required": ["protocol_version", "workflow"],
            },
            required_fields=["protocol_version", "workflow.name", "workflow.nodes"],
        )

    @staticmethod
    def export_workflow(workflow_data: dict) -> dict[str, Any]:
        """Export a workflow in the standard exchange format."""
        payload = json.dumps(workflow_data, sort_keys=True)
        checksum = hashlib.sha256(payload.encode()).hexdigest()
        return {
            "protocol_version": "1.0.0",
            "workflow": workflow_data,
            "metadata": {
                "exported_at": datetime.utcnow().isoformat(),
                "source_version": "1.0.0",
                "checksum": checksum,
            },
        }

    @staticmethod
    def validate_export(package: dict) -> list[str]:
        """Validate a workflow exchange package."""
        errors = []
        if package.get("protocol_version") != "1.0.0":
            errors.append("Unsupported protocol version")
        workflow = package.get("workflow", {})
        if not workflow.get("name"):
            errors.append("Workflow name is required")
        if not workflow.get("nodes"):
            errors.append("Workflow must have at least one node")
        return errors


@dataclass
class AuditExchangeProtocol:
    """Protocol for exchanging audit trail entries between systems."""

    @staticmethod
    def get_schema() -> ProtocolSchema:
        return ProtocolSchema(
            protocol="audit_exchange",
            version=ProtocolVersion.V1_0_0,
            description="Standard format for verifiable audit trail exchange",
            schema_def={
                "type": "object",
                "properties": {
                    "protocol_version": {"type": "string"},
                    "entries": {"type": "array"},
                    "chain_proof": {"type": "object"},
                },
                "required": ["protocol_version", "entries"],
            },
            required_fields=["protocol_version", "entries"],
        )

    @staticmethod
    def create_exchange_package(entries: list[dict]) -> dict[str, Any]:
        """Create a verifiable audit exchange package."""
        chain_hashes = []
        previous = "GENESIS"
        for entry in entries:
            content = f"{previous}|{json.dumps(entry, sort_keys=True)}"
            current = hashlib.sha256(content.encode()).hexdigest()
            chain_hashes.append(current)
            previous = current

        return {
            "protocol_version": "1.0.0",
            "entries": entries,
            "chain_proof": {
                "first_hash": chain_hashes[0] if chain_hashes else "",
                "last_hash": chain_hashes[-1] if chain_hashes else "",
                "chain_length": len(chain_hashes),
                "algorithm": "sha256",
            },
        }


@dataclass
class ExplainabilityExchangeSchema:
    """Schema for exchanging AI explainability data."""

    @staticmethod
    def get_schema() -> ProtocolSchema:
        return ProtocolSchema(
            protocol="explainability_exchange",
            version=ProtocolVersion.V1_0_0,
            description="Standard format for AI explainability data exchange",
            schema_def={
                "type": "object",
                "properties": {
                    "execution_id": {"type": "string"},
                    "model": {"type": "string"},
                    "provider": {"type": "string"},
                    "prompt_version": {"type": "string"},
                    "trace_events": {"type": "array"},
                    "retrieval_chunks": {"type": "array"},
                    "guardrail_decisions": {"type": "array"},
                    "confidence": {"type": "number"},
                },
                "required": ["execution_id", "model", "provider"],
            },
            required_fields=["execution_id", "model", "provider"],
        )


@dataclass
class ReplayPortabilitySchema:
    """Schema for portable replay data."""

    @staticmethod
    def get_schema() -> ProtocolSchema:
        return ProtocolSchema(
            protocol="replay_portability",
            version=ProtocolVersion.V1_0_0,
            description="Standard format for portable AI execution replay",
            schema_def={
                "type": "object",
                "properties": {
                    "original_execution_id": {"type": "string"},
                    "snapshot": {"type": "object"},
                    "prompt_template": {"type": "string"},
                    "model_config": {"type": "object"},
                    "retrieval_context": {"type": "object"},
                    "replay_results": {"type": "object"},
                },
                "required": ["original_execution_id", "snapshot"],
            },
            required_fields=["original_execution_id", "snapshot"],
        )


@dataclass
class PolicyInteroperabilityFormat:
    """Standard format for policy exchange between systems."""

    @staticmethod
    def get_schema() -> ProtocolSchema:
        return ProtocolSchema(
            protocol="policy_interoperability",
            version=ProtocolVersion.V1_0_0,
            description="Standard format for governance policy exchange",
            schema_def={
                "type": "object",
                "properties": {
                    "policy_id": {"type": "string"},
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "rules": {"type": "array"},
                    "severity": {"type": "string"},
                    "scope": {"type": "string"},
                    "effective_date": {"type": "string"},
                },
                "required": ["policy_id", "name", "rules"],
            },
            required_fields=["policy_id", "name", "rules"],
        )


@dataclass
class ObligationInterchangeStandard:
    """Standard format for obligation data interchange."""

    @staticmethod
    def get_schema() -> ProtocolSchema:
        return ProtocolSchema(
            protocol="obligation_interchange",
            version=ProtocolVersion.V1_0_0,
            description="Standard format for obligation data exchange between systems",
            schema_def={
                "type": "object",
                "properties": {
                    "obligation_id": {"type": "string"},
                    "description": {"type": "string"},
                    "type": {"type": "string"},
                    "party": {"type": "string"},
                    "status": {"type": "string"},
                    "due_date": {"type": "string"},
                    "contract_reference": {"type": "string"},
                    "evidence": {"type": "array"},
                },
                "required": ["obligation_id", "description", "type", "party"],
            },
            required_fields=["obligation_id", "description", "type", "party"],
        )


@dataclass
class FederatedEventContract:
    """Contract for federated event exchange between platforms."""

    @staticmethod
    def get_schema() -> ProtocolSchema:
        return ProtocolSchema(
            protocol="federated_event_contract",
            version=ProtocolVersion.V1_0_0,
            description="Standard contract for federated event exchange between platforms",
            schema_def={
                "type": "object",
                "properties": {
                    "event_id": {"type": "string"},
                    "event_type": {"type": "string"},
                    "source_platform": {"type": "string"},
                    "target_platform": {"type": "string"},
                    "payload": {"type": "object"},
                    "signature": {"type": "string"},
                    "timestamp": {"type": "string"},
                },
                "required": ["event_id", "event_type", "source_platform", "payload"],
            },
            required_fields=["event_id", "event_type", "source_platform", "payload"],
        )


@dataclass
class ProtocolRegistry:
    """Registry of all enterprise protocols."""

    _protocols: dict[str, ProtocolSchema] = field(default_factory=dict)

    def __post_init__(self):
        self.register(WorkflowExchangeProtocol.get_schema())
        self.register(AuditExchangeProtocol.get_schema())
        self.register(ExplainabilityExchangeSchema.get_schema())
        self.register(ReplayPortabilitySchema.get_schema())
        self.register(PolicyInteroperabilityFormat.get_schema())
        self.register(ObligationInterchangeStandard.get_schema())
        self.register(FederatedEventContract.get_schema())

    def register(self, schema: ProtocolSchema) -> None:
        """Register a protocol schema."""
        self._protocols[schema.protocol] = schema

    def get_protocol(self, name: str) -> ProtocolSchema | None:
        """Get a protocol schema by name."""
        return self._protocols.get(name)

    def list_protocols(self) -> list[dict[str, Any]]:
        """List all registered protocols."""
        return [
            {"protocol": p.protocol, "version": p.version.value, "description": p.description}
            for p in self._protocols.values()
        ]

    def validate_against_protocol(self, protocol: str, data: dict) -> list[str]:
        """Validate data against a protocol schema."""
        schema = self._protocols.get(protocol)
        if not schema:
            return [f"Protocol '{protocol}' not found"]

        errors = []
        for field in schema.required_fields:
            parts = field.split(".")
            current = data
            for part in parts:
                if isinstance(current, dict):
                    current = current.get(part)
                else:
                    current = None
                    break
            if current is None:
                errors.append(f"Missing required field: {field}")

        return errors


# ── Global singleton ───────────────────────────────────────────────

protocol_registry = ProtocolRegistry()
