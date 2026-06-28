"""Dynamic Metadata Provider — extensible context providers for the rule engine.

Each provider exposes a set of fields that can be referenced in JSON Logic rules.
Adding a new integration means adding a new provider — no rule engine changes.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ── Abstract Metadata Provider ─────────────────────────────────────


class MetadataProvider(ABC):
    """Abstract base class for metadata providers.

    Each provider exposes fields and evaluates them against a context.
    New integrations are added by implementing this interface.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (e.g., 'contract', 'supplier', 'risk')."""
        ...

    @abstractmethod
    def get_fields(self) -> list[str]:
        """Return the list of field paths this provider exposes.

        These are the keys that can be referenced in JSON Logic rules
        using the 'var' operator (e.g., 'contract.risk_score').
        """
        ...

    @abstractmethod
    def evaluate(self, context: dict[str, Any]) -> dict[str, Any]:
        """Evaluate the provider's fields against the given context.

        Args:
            context: The full evaluation context (contract data, etc.).

        Returns:
            A dict of field values keyed by field name.
        """
        ...


# ── Contract Provider ──────────────────────────────────────────────


class ContractProvider(MetadataProvider):
    """Exposes contract-related fields for rule evaluation.

    Fields:
        contract.risk_score — numeric risk score (0-100)
        contract.value — contract monetary value
        contract.jurisdiction — legal jurisdiction
        contract.type — contract type (e.g., procurement, sales)
        contract.department — owning department
        contract.business_unit — business unit
        contract.region — geographic region
        contract.is_international — whether cross-border
        contract.has_data_privacy — whether data privacy clauses exist
        contract.clause_count — number of clauses
    """

    @property
    def provider_name(self) -> str:
        return "contract"

    def get_fields(self) -> list[str]:
        return [
            "contract.risk_score",
            "contract.value",
            "contract.jurisdiction",
            "contract.type",
            "contract.department",
            "contract.business_unit",
            "contract.region",
            "contract.is_international",
            "contract.has_data_privacy",
            "contract.clause_count",
        ]

    def evaluate(self, context: dict[str, Any]) -> dict[str, Any]:
        contract = context.get("contract", {})
        if not isinstance(contract, dict):
            contract = {}
        return {
            "contract.risk_score": contract.get("risk_score", 0),
            "contract.value": contract.get("value", 0.0),
            "contract.jurisdiction": contract.get("jurisdiction", ""),
            "contract.type": contract.get("type", ""),
            "contract.department": contract.get("department", ""),
            "contract.business_unit": contract.get("business_unit", ""),
            "contract.region": contract.get("region", ""),
            "contract.is_international": contract.get("is_international", False),
            "contract.has_data_privacy": contract.get("has_data_privacy", False),
            "contract.clause_count": contract.get("clause_count", 0),
        }


# ── Supplier Provider ──────────────────────────────────────────────


class SupplierProvider(MetadataProvider):
    """Exposes supplier-related fields for rule evaluation.

    Fields:
        supplier.region — supplier's geographic region
        supplier.tier — supplier tier (1, 2, 3)
        supplier.is_critical — whether critical supplier
        supplier.risk_level — supplier risk level
        supplier.relationship_length_years — years of relationship
    """

    @property
    def provider_name(self) -> str:
        return "supplier"

    def get_fields(self) -> list[str]:
        return [
            "supplier.region",
            "supplier.tier",
            "supplier.is_critical",
            "supplier.risk_level",
            "supplier.relationship_length_years",
        ]

    def evaluate(self, context: dict[str, Any]) -> dict[str, Any]:
        supplier = context.get("supplier", {})
        if not isinstance(supplier, dict):
            supplier = {}
        return {
            "supplier.region": supplier.get("region", ""),
            "supplier.tier": supplier.get("tier", 3),
            "supplier.is_critical": supplier.get("is_critical", False),
            "supplier.risk_level": supplier.get("risk_level", "low"),
            "supplier.relationship_length_years": supplier.get("relationship_length_years", 0),
        }


# ── Risk Provider ──────────────────────────────────────────────────


class RiskProvider(MetadataProvider):
    """Exposes risk-related fields for rule evaluation.

    Fields:
        risk.score — composite risk score (0-100)
        risk.category — risk category (low, medium, high, critical)
        risk.auto_score — AI-generated risk score
        risk.manual_score — human-assigned risk score
        risk.has_high_risk_clauses — whether high-risk clauses detected
        risk.compliance_flags — list of compliance flags
    """

    @property
    def provider_name(self) -> str:
        return "risk"

    def get_fields(self) -> list[str]:
        return [
            "risk.score",
            "risk.category",
            "risk.auto_score",
            "risk.manual_score",
            "risk.has_high_risk_clauses",
            "risk.compliance_flags",
        ]

    def evaluate(self, context: dict[str, Any]) -> dict[str, Any]:
        risk = context.get("risk", {})
        if not isinstance(risk, dict):
            risk = {}
        return {
            "risk.score": risk.get("score", 0),
            "risk.category": risk.get("category", "low"),
            "risk.auto_score": risk.get("auto_score", 0),
            "risk.manual_score": risk.get("manual_score", 0),
            "risk.has_high_risk_clauses": risk.get("has_high_risk_clauses", False),
            "risk.compliance_flags": risk.get("compliance_flags", []),
        }


# ── AI Provider ────────────────────────────────────────────────────


class AIProvider(MetadataProvider):
    """Exposes AI analysis fields for rule evaluation.

    Fields:
        ai.findings_count — number of AI findings
        ai.top_risk — top risk identified by AI
        ai.summary — AI analysis summary
        ai.sentiment — document sentiment score
        ai.language — detected document language
        ai.key_entities — key entities found by AI
    """

    @property
    def provider_name(self) -> str:
        return "ai"

    def get_fields(self) -> list[str]:
        return [
            "ai.findings_count",
            "ai.top_risk",
            "ai.summary",
            "ai.sentiment",
            "ai.language",
            "ai.key_entities",
        ]

    def evaluate(self, context: dict[str, Any]) -> dict[str, Any]:
        ai = context.get("ai", {})
        if not isinstance(ai, dict):
            ai = {}
        return {
            "ai.findings_count": ai.get("findings_count", 0),
            "ai.top_risk": ai.get("top_risk", ""),
            "ai.summary": ai.get("summary", ""),
            "ai.sentiment": ai.get("sentiment", 0.0),
            "ai.language": ai.get("language", "en"),
            "ai.key_entities": ai.get("key_entities", []),
        }


# ── User Provider ──────────────────────────────────────────────────


class UserProvider(MetadataProvider):
    """Exposes user/actor fields for rule evaluation.

    Fields:
        user.role — user's role
        user.department — user's department
        user.region — user's region
        user.is_manager — whether user is a manager
        user.approval_limit — user's monetary approval limit
    """

    @property
    def provider_name(self) -> str:
        return "user"

    def get_fields(self) -> list[str]:
        return [
            "user.role",
            "user.department",
            "user.region",
            "user.is_manager",
            "user.approval_limit",
        ]

    def evaluate(self, context: dict[str, Any]) -> dict[str, Any]:
        user = context.get("user", {})
        if not isinstance(user, dict):
            user = {}
        return {
            "user.role": user.get("role", ""),
            "user.department": user.get("department", ""),
            "user.region": user.get("region", ""),
            "user.is_manager": user.get("is_manager", False),
            "user.approval_limit": user.get("approval_limit", 0.0),
        }


# ── Provider Registry ──────────────────────────────────────────────


class ProviderRegistry:
    """Registry of all metadata providers.

    Maps provider names to provider instances for dynamic field resolution.
    """

    def __init__(self) -> None:
        self._providers: dict[str, MetadataProvider] = {}

    def register(self, provider: MetadataProvider) -> None:
        """Register a metadata provider.

        Args:
            provider: The provider instance to register.
        """
        name = provider.provider_name
        if name in self._providers:
            logger.warning("Overwriting existing provider: %s", name)
        self._providers[name] = provider
        logger.debug("Registered metadata provider: %s", name)

    def get_provider(self, name: str) -> Optional[MetadataProvider]:
        """Get a provider by name.

        Args:
            name: The provider name.

        Returns:
            The provider instance, or None if not found.
        """
        return self._providers.get(name)

    def list_providers(self) -> list[str]:
        """List all registered provider names."""
        return list(self._providers.keys())

    def get_all_fields(self) -> dict[str, list[str]]:
        """Get all fields from all registered providers.

        Returns:
            Dict mapping provider name to list of field paths.
        """
        return {
            name: provider.get_fields()
            for name, provider in self._providers.items()
        }


# ── Composite Context Builder ──────────────────────────────────────


class CompositeContextBuilder:
    """Builds a composite evaluation context from all registered providers.

    Calls all providers and merges their results into a single context dict
    that can be used by the JSON Logic rule engine.
    """

    def __init__(self, registry: Optional[ProviderRegistry] = None) -> None:
        self.registry = registry or self._default_registry()

    def build(self, base_context: dict[str, Any]) -> dict[str, Any]:
        """Build a composite context from all providers.

        Args:
            base_context: The base context with contract, supplier, etc. data.

        Returns:
            A merged context dict with all provider fields.
        """
        merged: dict[str, Any] = dict(base_context)

        for provider_name in self.registry.list_providers():
            provider = self.registry.get_provider(provider_name)
            if provider is None:
                continue
            try:
                fields = provider.evaluate(base_context)
                merged.update(fields)
            except Exception as exc:
                logger.warning(
                    "Provider '%s' evaluation failed: %s", provider_name, exc,
                )

        return merged

    def _default_registry(self) -> ProviderRegistry:
        """Create a registry with all default providers."""
        registry = ProviderRegistry()
        registry.register(ContractProvider())
        registry.register(SupplierProvider())
        registry.register(RiskProvider())
        registry.register(AIProvider())
        registry.register(UserProvider())
        return registry
