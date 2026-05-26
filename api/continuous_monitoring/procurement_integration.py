"""SAP Ariba / Coupa procurement integration (V2-034).

Provides PO-level risk linkage and metadata sync with SAP Ariba
and Coupa procurement platforms. Enables bidirectional data flow
for contract risk intelligence in procurement workflows.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ProcurementPlatform(str, Enum):
    """Supported procurement platforms."""

    SAP_ARIBA = "sap_ariba"
    COUPA = "coupa"


class SyncDirection(str, Enum):
    """Direction of data synchronization."""

    IMPORT = "import"           # Procurement -> Platform
    EXPORT = "export"           # Platform -> Procurement
    BIDIRECTIONAL = "bidirectional"


@dataclass
class PurchaseOrder:
    """A purchase order from a procurement platform."""

    po_id: str
    platform: ProcurementPlatform
    po_number: str
    supplier_name: str
    supplier_id: str
    contract_id: Optional[str] = None
    amount: float = 0.0
    currency: str = "USD"
    status: str = "pending"  # pending, approved, fulfilled, cancelled
    created_date: Optional[str] = None
    expected_delivery_date: Optional[str] = None
    description: str = ""
    line_items: List[Dict[str, Any]] = field(default_factory=list)
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    synced_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "po_id": self.po_id,
            "platform": self.platform.value if isinstance(self.platform, ProcurementPlatform) else self.platform,
            "po_number": self.po_number,
            "supplier_name": self.supplier_name,
            "supplier_id": self.supplier_id,
            "contract_id": self.contract_id,
            "amount": self.amount,
            "currency": self.currency,
            "status": self.status,
            "created_date": self.created_date,
            "expected_delivery_date": self.expected_delivery_date,
            "description": self.description,
            "line_items": self.line_items,
            "risk_score": round(self.risk_score, 2) if self.risk_score is not None else None,
            "risk_level": self.risk_level,
            "synced_at": self.synced_at,
        }


@dataclass
class ProcurementConfig:
    """Configuration for a procurement platform connection."""

    config_id: str
    tenant_id: str
    platform: ProcurementPlatform
    api_endpoint: str
    api_key_identifier: str  # Reference to stored API key
    sync_direction: SyncDirection
    sync_interval_minutes: int = 60
    last_sync_at: Optional[str] = None
    enabled: bool = True
    metadata_mapping: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_id": self.config_id,
            "tenant_id": self.tenant_id,
            "platform": self.platform.value if isinstance(self.platform, ProcurementPlatform) else self.platform,
            "api_endpoint": self.api_endpoint,
            "sync_direction": self.sync_direction.value if isinstance(self.sync_direction, SyncDirection) else self.sync_direction,
            "sync_interval_minutes": self.sync_interval_minutes,
            "last_sync_at": self.last_sync_at,
            "enabled": self.enabled,
        }


class ProcurementIntegration:
    """SAP Ariba / Coupa procurement integration.

    Manages connections to procurement platforms, syncs purchase orders,
    and links PO-level risk data to contracts.

    Usage:
        integration = ProcurementIntegration()
        await integration.configure_connection(config)
        pos = await integration.import_purchase_orders(tenant_id, "sap_ariba")
    """

    def __init__(self, db_pool: Optional[Any] = None) -> None:
        """Initialize the procurement integration.

        Args:
            db_pool: Optional database pool.
        """
        self._db_pool = db_pool
        self._configs: Dict[str, ProcurementConfig] = {}
        self._purchase_orders: Dict[str, PurchaseOrder] = {}
        self._risk_linkage: Dict[str, str] = {}  # po_id -> contract_id

    async def configure_connection(
        self,
        tenant_id: str,
        platform: ProcurementPlatform,
        api_endpoint: str,
        api_key: str,
        sync_direction: SyncDirection = SyncDirection.BIDIRECTIONAL,
        sync_interval_minutes: int = 60,
        metadata_mapping: Optional[Dict[str, str]] = None,
    ) -> ProcurementConfig:
        """Configure a connection to a procurement platform.

        Args:
            tenant_id: The tenant identifier.
            platform: The procurement platform.
            api_endpoint: API endpoint URL.
            api_key: API key for authentication.
            sync_direction: Sync direction.
            sync_interval_minutes: Sync interval.
            metadata_mapping: Field mapping from platform to platform.

        Returns:
            The created ProcurementConfig.
        """
        config = ProcurementConfig(
            config_id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            platform=platform,
            api_endpoint=api_endpoint,
            api_key_identifier=f"procurement_{platform.value}_{tenant_id}",
            sync_direction=sync_direction,
            sync_interval_minutes=sync_interval_minutes,
            metadata_mapping=metadata_mapping or {},
        )
        self._configs[config.config_id] = config

        # Store API key reference (in production, use secure vault)
        logger.info(
            "Configured %s connection for tenant %s (endpoint: %s, direction: %s)",
            platform.value if isinstance(platform, ProcurementPlatform) else platform,
            tenant_id, api_endpoint,
            sync_direction.value if isinstance(sync_direction, SyncDirection) else sync_direction,
        )

        return config

    async def import_purchase_orders(
        self,
        tenant_id: str,
        platform: ProcurementPlatform,
    ) -> List[Dict[str, Any]]:
        """Import purchase orders from a procurement platform.

        Args:
            tenant_id: The tenant identifier.
            platform: The procurement platform.

        Returns:
            List of imported purchase order dicts.
        """
        # Find matching config
        config = next(
            (c for c in self._configs.values()
             if c.tenant_id == tenant_id and c.platform == platform and c.enabled),
            None
        )
        if not config:
            logger.warning("No active config found for tenant %s / %s", tenant_id, platform)
            return []

        # Simulate API call to procurement platform
        imported_pos = await self._fetch_from_platform(config)

        # Store purchase orders
        for po_data in imported_pos:
            po = PurchaseOrder(
                po_id=str(uuid.uuid4()),
                platform=platform,
                po_number=po_data.get("po_number", f"PO-{len(self._purchase_orders)}"),
                supplier_name=po_data.get("supplier_name", "Unknown"),
                supplier_id=po_data.get("supplier_id", ""),
                amount=po_data.get("amount", 0.0),
                currency=po_data.get("currency", "USD"),
                status=po_data.get("status", "pending"),
                created_date=po_data.get("created_date"),
                expected_delivery_date=po_data.get("expected_delivery_date"),
                description=po_data.get("description", ""),
                line_items=po_data.get("line_items", []),
                synced_at=datetime.utcnow().isoformat(),
            )
            self._purchase_orders[po.po_id] = po

        # Update last sync
        config.last_sync_at = datetime.utcnow().isoformat()

        logger.info(
            "Imported %d purchase orders from %s for tenant %s",
            len(imported_pos),
            platform.value if isinstance(platform, ProcurementPlatform) else platform,
            tenant_id,
        )

        return [po.to_dict() for po in self._purchase_orders.values()
                if po.platform == platform]

    async def _fetch_from_platform(
        self,
        config: ProcurementConfig,
    ) -> List[Dict[str, Any]]:
        """Fetch purchase orders from a procurement platform API.

        In production, this would make actual HTTP calls to the platform API.
        This implementation returns simulated data.

        Args:
            config: The procurement configuration.

        Returns:
            List of purchase order dicts.
        """
        platform_name = config.platform.value if isinstance(config.platform, ProcurementPlatform) else config.platform

        if platform_name == "sap_ariba":
            return self._simulate_ariba_pos()
        elif platform_name == "coupa":
            return self._simulate_coupa_pos()
        return []

    def _simulate_ariba_pos(self) -> List[Dict[str, Any]]:
        """Simulate SAP Ariba purchase order data.

        Returns:
            List of simulated PO dicts.
        """
        return [
            {
                "po_number": "ARB-2024-001",
                "supplier_name": "TechCorp Solutions",
                "supplier_id": "SUP-001",
                "amount": 150000.0,
                "currency": "USD",
                "status": "approved",
                "created_date": "2024-01-15",
                "expected_delivery_date": "2024-03-15",
                "description": "Enterprise software license renewal",
                "line_items": [
                    {"description": "Software License", "quantity": 1, "unit_price": 120000.0},
                    {"description": "Maintenance & Support", "quantity": 1, "unit_price": 30000.0},
                ],
            },
            {
                "po_number": "ARB-2024-002",
                "supplier_name": "DataGuard Security",
                "supplier_id": "SUP-002",
                "amount": 75000.0,
                "currency": "USD",
                "status": "pending",
                "created_date": "2024-02-01",
                "expected_delivery_date": "2024-04-01",
                "description": "Security audit services",
                "line_items": [
                    {"description": "Penetration Testing", "quantity": 1, "unit_price": 45000.0},
                    {"description": "Compliance Audit", "quantity": 1, "unit_price": 30000.0},
                ],
            },
        ]

    def _simulate_coupa_pos(self) -> List[Dict[str, Any]]:
        """Simulate Coupa purchase order data.

        Returns:
            List of simulated PO dicts.
        """
        return [
            {
                "po_number": "COU-2024-001",
                "supplier_name": "CloudHost Inc.",
                "supplier_id": "SUP-003",
                "amount": 240000.0,
                "currency": "USD",
                "status": "approved",
                "created_date": "2024-01-20",
                "expected_delivery_date": "2024-02-20",
                "description": "Cloud infrastructure services Q1",
                "line_items": [
                    {"description": "Compute Resources", "quantity": 12, "unit_price": 10000.0},
                    {"description": "Storage Services", "quantity": 12, "unit_price": 8000.0},
                    {"description": "Network Services", "quantity": 12, "unit_price": 2000.0},
                ],
            },
        ]

    async def link_po_to_contract(
        self,
        po_id: str,
        contract_id: str,
    ) -> bool:
        """Link a purchase order to a contract for risk linkage.

        Args:
            po_id: Purchase order identifier.
            contract_id: Contract identifier.

        Returns:
            True if linked.
        """
        if po_id not in self._purchase_orders:
            return False

        self._purchase_orders[po_id].contract_id = contract_id
        self._risk_linkage[po_id] = contract_id
        logger.info("Linked PO %s to contract %s", po_id, contract_id)
        return True

    async def get_contract_pos(
        self,
        contract_id: str,
    ) -> List[Dict[str, Any]]:
        """Get all purchase orders linked to a contract.

        Args:
            contract_id: The contract identifier.

        Returns:
            List of purchase order dicts.
        """
        return [
            po.to_dict() for po in self._purchase_orders.values()
            if po.contract_id == contract_id
        ]

    async def get_po_risk_summary(
        self,
        tenant_id: str,
    ) -> Dict[str, Any]:
        """Get risk summary across all purchase orders.

        Args:
            tenant_id: The tenant identifier.

        Returns:
            Dict with PO risk summary.
        """
        tenant_pos = [
            po for po in self._purchase_orders.values()
            # In production, filter by tenant via linked contracts
        ]

        total_amount = sum(po.amount for po in tenant_pos)
        high_risk_amount = sum(
            po.amount for po in tenant_pos
            if po.risk_level in ("high", "critical")
        )

        return {
            "total_pos": len(tenant_pos),
            "total_amount": total_amount,
            "high_risk_amount": high_risk_amount,
            "high_risk_percent": round(
                high_risk_amount / max(total_amount, 1) * 100, 1
            ),
            "by_status": {
                status: sum(1 for po in tenant_pos if po.status == status)
                for status in set(po.status for po in tenant_pos)
            },
            "linked_to_contracts": sum(
                1 for po in tenant_pos if po.contract_id is not None
            ),
        }
