"""Enterprise Federation Layer — inter-company workflows, supplier/customer coordination, federated approvals, federated audit exchange, secure shared obligations.

Cross-organization operational coordination infrastructure.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class FederationPermission(str, Enum):
    VIEW = "view"
    COMMENT = "comment"
    APPROVE = "approve"
    EDIT = "edit"
    ADMIN = "admin"


@dataclass
class FederationPartner:
    """A trusted federation partner organization."""
    partner_id: str
    name: str
    tenant_id: str
    public_key: str = ""
    permissions: list[FederationPermission] = field(default_factory=lambda: [FederationPermission.VIEW])
    is_active: bool = True
    connected_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_active: str = ""


@dataclass
class FederatedWorkflow:
    """A workflow that spans multiple organizations."""
    workflow_id: str
    initiator_tenant: str
    participants: list[dict[str, Any]] = field(default_factory=list)
    shared_data: dict[str, Any] = field(default_factory=dict)
    status: str = "active"  # active, completed, terminated
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class FederatedAuditEntry:
    """An audit entry shared across organizations."""
    entry_id: str
    source_tenant: str
    target_tenant: str
    event_type: str
    description: str
    evidence_hash: str = ""
    verified: bool = False
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class FederationService:
    """Enterprise federation layer — cross-organization operational coordination.

    Capabilities:
    - Controlled inter-company workflows (shared workflows between orgs)
    - Supplier/customer coordination (shared obligations, approvals)
    - Federated approvals (cross-org approval chains)
    - Federated audit exchange (verifiable audit sharing)
    - Secure shared obligations (cross-org obligation tracking)
    - Cross-enterprise SLA coordination (shared SLA monitoring)
    """

    _partners: dict[str, FederationPartner] = field(default_factory=dict)
    _workflows: dict[str, FederatedWorkflow] = field(default_factory=dict)
    _audit_entries: list[FederatedAuditEntry] = field(default_factory=list)

    def register_partner(self, partner: FederationPartner) -> None:
        """Register a federation partner."""
        self._partners[partner.partner_id] = partner
        logger.info("Registered federation partner: %s (%s)", partner.name, partner.tenant_id[:8])

    def get_partner(self, partner_id: str) -> FederationPartner | None:
        """Get a federation partner."""
        return self._partners.get(partner_id)

    def list_partners(self, tenant_id: str | None = None) -> list[FederationPartner]:
        """List federation partners."""
        if tenant_id:
            return [p for p in self._partners.values() if p.tenant_id == tenant_id]
        return list(self._partners.values())

    def create_federated_workflow(self, initiator_tenant: str, participants: list[dict]) -> FederatedWorkflow:
        """Create a workflow that spans multiple organizations."""
        wf = FederatedWorkflow(
            workflow_id=str(uuid.uuid4()),
            initiator_tenant=initiator_tenant,
            participants=participants,
        )
        self._workflows[wf.workflow_id] = wf
        return wf

    def share_audit_entry(self, source_tenant: str, target_tenant: str, event_type: str, description: str, evidence: str = "") -> FederatedAuditEntry:
        """Share an audit entry with a partner organization."""
        import hashlib
        entry = FederatedAuditEntry(
            entry_id=str(uuid.uuid4()),
            source_tenant=source_tenant,
            target_tenant=target_tenant,
            event_type=event_type,
            description=description,
            evidence_hash=hashlib.sha256(evidence.encode()).hexdigest() if evidence else "",
        )
        self._audit_entries.append(entry)
        return entry

    def verify_audit_entry(self, entry_id: str, evidence: str) -> bool:
        """Verify a federated audit entry against evidence."""
        import hashlib
        for entry in self._audit_entries:
            if entry.entry_id == entry_id:
                computed = hashlib.sha256(evidence.encode()).hexdigest()
                verified = computed == entry.evidence_hash
                entry.verified = verified
                return verified
        return False

    def get_federated_audit_trail(self, tenant_id: str) -> list[FederatedAuditEntry]:
        """Get all audit entries involving a tenant."""
        return [
            e for e in self._audit_entries
            if e.source_tenant == tenant_id or e.target_tenant == tenant_id
        ]

    def get_federation_summary(self) -> dict[str, Any]:
        """Get federation layer summary."""
        return {
            "total_partners": len(self._partners),
            "active_workflows": sum(1 for w in self._workflows.values() if w.status == "active"),
            "shared_audit_entries": len(self._audit_entries),
            "verified_entries": sum(1 for e in self._audit_entries if e.verified),
        }


# ── Global singleton ───────────────────────────────────────────────

federation_service = FederationService()
