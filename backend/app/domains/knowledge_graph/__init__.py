"""Knowledge Graph Foundation — relationship intelligence for contract data.

Tracks:
- Vendors and counterparties
- Clauses and their relationships
- Obligations and dependencies
- Renewals and lifecycle events
- Legal entities and corporate structure
- Risk propagation across related agreements
- Related agreements and contract hierarchy
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# ── Entity Types ───────────────────────────────────────────────────

class GraphEntityType(str, Enum):
    CONTRACT = "contract"
    CLAUSE = "clause"
    OBLIGATION = "obligation"
    VENDOR = "vendor"
    LEGAL_ENTITY = "legal_entity"
    PERSON = "person"
    RENEWAL = "renewal"
    RISK = "risk"
    FINDING = "finding"
    PLAYBOOK = "playbook"


class RelationshipType(str, Enum):
    CONTAINS = "contains"               # Contract -> Clause
    REFERENCES = "references"            # Clause -> Clause
    AMENDS = "amends"                    # Contract -> Contract
    SUPERSEDES = "supersedes"            # Contract -> Contract
    RELATED_TO = "related_to"            # Contract -> Contract
    GOVERNS = "governs"                  # LegalEntity -> Contract
    OBLIGATES = "obligates"              # Clause -> Obligation
    ASSIGNED_TO = "assigned_to"          # Obligation -> Person
    PROPAGATES_RISK = "propagates_risk"  # Clause -> Risk
    MITIGATES = "mitigates"              # Playbook -> Risk
    RENEWS = "renews"                    # Contract -> Renewal
    SAME_AS = "same_as"                  # Entity -> Entity (dedup)
    PARENT_OF = "parent_of"              # LegalEntity -> LegalEntity


@dataclass
class GraphEntity:
    """A node in the knowledge graph."""
    entity_id: str
    entity_type: GraphEntityType
    tenant_id: str
    name: str
    properties: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class GraphRelationship:
    """An edge in the knowledge graph."""
    source_id: str
    target_id: str
    relationship_type: RelationshipType
    tenant_id: str
    weight: float = 1.0
    properties: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class GraphPath:
    """A path between two entities in the graph."""
    entities: list[GraphEntity] = field(default_factory=list)
    relationships: list[GraphRelationship] = field(default_factory=list)
    total_weight: float = 0.0


# ── Knowledge Graph Database ───────────────────────────────────────

@dataclass
class KnowledgeGraphDB:
    """PostgreSQL-backed knowledge graph storage.

    Uses adjacency list pattern with JSONB properties.
    For production scale, migrate to dedicated graph DB (Neo4j/ArangoDB).
    """

    session: AsyncSession
    tenant_id: str

    async def upsert_entity(self, entity: GraphEntity) -> None:
        """Insert or update a graph entity."""
        sql = sa_text("""
            INSERT INTO knowledge_graph_entities (entity_id, entity_type, tenant_id, name, properties)
            VALUES (:eid, :etype, :tid, :name, :props)
            ON CONFLICT (entity_id, tenant_id)
            DO UPDATE SET name = :name, properties = :props, updated_at = NOW()
        """)
        await self.session.execute(sql, {
            "eid": entity.entity_id,
            "etype": entity.entity_type.value,
            "tid": entity.tenant_id,
            "name": entity.name,
            "props": entity.properties,
        })

    async def upsert_relationship(self, rel: GraphRelationship) -> None:
        """Insert or update a graph relationship."""
        sql = sa_text("""
            INSERT INTO knowledge_graph_relationships (source_id, target_id, relationship_type, tenant_id, weight, properties)
            VALUES (:sid, :tid, :rtype, :tenant, :weight, :props)
            ON CONFLICT (source_id, target_id, relationship_type, tenant_id)
            DO UPDATE SET weight = :weight, properties = :props, updated_at = NOW()
        """)
        await self.session.execute(sql, {
            "sid": rel.source_id,
            "tid": rel.target_id,
            "rtype": rel.relationship_type.value,
            "tenant": rel.tenant_id,
            "weight": rel.weight,
            "props": rel.properties,
        })

    async def get_entity(self, entity_id: str) -> GraphEntity | None:
        """Get an entity by ID."""
        sql = sa_text("""
            SELECT entity_id, entity_type, tenant_id, name, properties, created_at
            FROM knowledge_graph_entities
            WHERE entity_id = :eid AND tenant_id = :tid
        """)
        result = await self.session.execute(sql, {"eid": entity_id, "tid": self.tenant_id})
        row = result.fetchone()
        if not row:
            return None
        return GraphEntity(
            entity_id=str(row.entity_id),
            entity_type=GraphEntityType(row.entity_type),
            tenant_id=str(row.tenant_id),
            name=row.name,
            properties=row.properties or {},
            created_at=str(row.created_at),
        )

    async def get_relationships(
        self,
        entity_id: str,
        relationship_type: RelationshipType | None = None,
        direction: str = "outgoing",
    ) -> list[GraphRelationship]:
        """Get relationships for an entity."""
        if direction == "outgoing":
            if relationship_type:
                sql = sa_text("""
                    SELECT source_id, target_id, relationship_type, tenant_id, weight, properties, created_at
                    FROM knowledge_graph_relationships
                    WHERE source_id = :eid AND relationship_type = :rtype AND tenant_id = :tid
                    ORDER BY weight DESC
                """)
                result = await self.session.execute(sql, {"eid": entity_id, "rtype": relationship_type.value, "tid": self.tenant_id})
            else:
                sql = sa_text("""
                    SELECT source_id, target_id, relationship_type, tenant_id, weight, properties, created_at
                    FROM knowledge_graph_relationships
                    WHERE source_id = :eid AND tenant_id = :tid
                    ORDER BY weight DESC
                """)
                result = await self.session.execute(sql, {"eid": entity_id, "tid": self.tenant_id})
        else:
            if relationship_type:
                sql = sa_text("""
                    SELECT source_id, target_id, relationship_type, tenant_id, weight, properties, created_at
                    FROM knowledge_graph_relationships
                    WHERE target_id = :eid AND relationship_type = :rtype AND tenant_id = :tid
                    ORDER BY weight DESC
                """)
                result = await self.session.execute(sql, {"eid": entity_id, "rtype": relationship_type.value, "tid": self.tenant_id})
            else:
                sql = sa_text("""
                    SELECT source_id, target_id, relationship_type, tenant_id, weight, properties, created_at
                    FROM knowledge_graph_relationships
                    WHERE target_id = :eid AND tenant_id = :tid
                    ORDER BY weight DESC
                """)
                result = await self.session.execute(sql, {"eid": entity_id, "tid": self.tenant_id})

        return [
            GraphRelationship(
                source_id=str(row.source_id),
                target_id=str(row.target_id),
                relationship_type=RelationshipType(row.relationship_type),
                tenant_id=str(row.tenant_id),
                weight=row.weight or 1.0,
                properties=row.properties or {},
                created_at=str(row.created_at),
            )
            for row in result.fetchall()
        ]

    async def find_path(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 3,
    ) -> GraphPath | None:
        """Find a path between two entities (BFS)."""
        if max_depth < 1:
            return None

        visited = {source_id}
        queue: list[tuple[str, list[GraphRelationship]]] = [(source_id, [])]

        while queue:
            current, path = queue.pop(0)
            if current == target_id and path:
                # Build full path result
                entities = []
                seen_ids = set()
                for rel in path:
                    for eid in (rel.source_id, rel.target_id):
                        if eid not in seen_ids:
                            entity = await self.get_entity(eid)
                            if entity:
                                entities.append(entity)
                                seen_ids.add(eid)
                return GraphPath(
                    entities=entities,
                    relationships=path,
                    total_weight=sum(r.weight for r in path),
                )

            if len(path) >= max_depth:
                continue

            rels = await self.get_relationships(current)
            for rel in rels:
                next_id = rel.target_id
                if next_id not in visited:
                    visited.add(next_id)
                    queue.append((next_id, path + [rel]))

        return None

    async def get_risk_propagation(self, contract_id: str) -> list[dict[str, Any]]:
        """Get risk propagation from a contract through the graph."""
        sql = sa_text("""
            WITH RECURSIVE risk_propagation AS (
                -- Base: risks directly in this contract
                SELECT e.entity_id, e.name, e.entity_type, 0 as depth, e.properties
                FROM knowledge_graph_entities e
                WHERE e.properties->>'contract_id' = :cid AND e.tenant_id = :tid

                UNION ALL

                -- Recursive: follow relationships
                SELECT e.entity_id, e.name, e.entity_type, rp.depth + 1, e.properties
                FROM risk_propagation rp
                JOIN knowledge_graph_relationships r ON r.source_id = rp.entity_id
                JOIN knowledge_graph_entities e ON e.entity_id = r.target_id
                WHERE rp.depth < 3 AND e.tenant_id = :tid
            )
            SELECT DISTINCT entity_id, name, entity_type, depth, properties
            FROM risk_propagation
            ORDER BY depth, name
        """)
        result = await self.session.execute(sql, {"cid": contract_id, "tid": self.tenant_id})
        return [
            {
                "entity_id": str(row.entity_id),
                "name": row.name,
                "entity_type": row.entity_type,
                "depth": row.depth,
                "properties": row.properties or {},
            }
            for row in result.fetchall()
        ]

    async def search_entities(
        self,
        query: str,
        entity_type: GraphEntityType | None = None,
        limit: int = 20,
    ) -> list[GraphEntity]:
        """Search entities by name or properties."""
        if entity_type:
            sql = sa_text("""
                SELECT entity_id, entity_type, tenant_id, name, properties, created_at
                FROM knowledge_graph_entities
                WHERE tenant_id = :tid AND entity_type = :etype
                  AND (name ILIKE :q OR properties::text ILIKE :q)
                LIMIT :lim
            """)
            result = await self.session.execute(sql, {
                "tid": self.tenant_id,
                "etype": entity_type.value,
                "q": f"%{query}%",
                "lim": limit,
            })
        else:
            sql = sa_text("""
                SELECT entity_id, entity_type, tenant_id, name, properties, created_at
                FROM knowledge_graph_entities
                WHERE tenant_id = :tid
                  AND (name ILIKE :q OR properties::text ILIKE :q)
                LIMIT :lim
            """)
            result = await self.session.execute(sql, {
                "tid": self.tenant_id,
                "q": f"%{query}%",
                "lim": limit,
            })

        return [
            GraphEntity(
                entity_id=str(row.entity_id),
                entity_type=GraphEntityType(row.entity_type),
                tenant_id=str(row.tenant_id),
                name=row.name,
                properties=row.properties or {},
                created_at=str(row.created_at),
            )
            for row in result.fetchall()
        ]

    async def get_contract_neighborhood(self, contract_id: str, depth: int = 1) -> dict[str, list]:
        """Get the full neighborhood of a contract in the graph."""
        entities = []
        relationships = []

        # Get the contract entity
        contract = await self.get_entity(contract_id)
        if contract:
            entities.append(contract)

        # Get direct relationships
        rels = await self.get_relationships(contract_id)
        for rel in rels:
            relationships.append(rel)
            target = await self.get_entity(rel.target_id)
            if target and target not in entities:
                entities.append(target)

        # Get incoming relationships
        incoming = await self.get_relationships(contract_id, direction="incoming")
        for rel in incoming:
            relationships.append(rel)
            source = await self.get_entity(rel.source_id)
            if source and source not in entities:
                entities.append(source)

        return {
            "entities": [{"id": e.entity_id, "type": e.entity_type.value, "name": e.name} for e in entities],
            "relationships": [
                {"source": r.source_id, "target": r.target_id, "type": r.relationship_type.value, "weight": r.weight}
                for r in relationships
            ],
            "entity_count": len(entities),
            "relationship_count": len(relationships),
        }

    async def get_graph_stats(self) -> dict[str, Any]:
        """Get statistics about the knowledge graph."""
        sql = sa_text("""
            SELECT entity_type, COUNT(*) as count
            FROM knowledge_graph_entities
            WHERE tenant_id = :tid
            GROUP BY entity_type
            ORDER BY count DESC
        """)
        result = await self.session.execute(sql, {"tid": self.tenant_id})
        entity_counts = {row.entity_type: row.count for row in result.fetchall()}

        sql = sa_text("""
            SELECT relationship_type, COUNT(*) as count
            FROM knowledge_graph_relationships
            WHERE tenant_id = :tid
            GROUP BY relationship_type
            ORDER BY count DESC
        """)
        result = await self.session.execute(sql, {"tid": self.tenant_id})
        rel_counts = {row.relationship_type: row.count for row in result.fetchall()}

        return {
            "total_entities": sum(entity_counts.values()),
            "total_relationships": sum(rel_counts.values()),
            "entities_by_type": entity_counts,
            "relationships_by_type": rel_counts,
        }
