"""Database session management and CRUD operations for PostgreSQL.

Provides async database sessions and repository classes for all
entity types. Replaces all in-memory stores with proper PostgreSQL
persistence.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncConnection

logger = logging.getLogger(__name__)


class DatabaseRepository:
    """Base repository for PostgreSQL CRUD operations.

    Provides async methods for common database operations
    across all entity types.
    """

    def __init__(self, engine: AsyncEngine) -> None:
        """Initialize the repository.

        Args:
            engine: SQLAlchemy async engine.
        """
        self._engine = engine

    def get_connection(self):
        """Get a database connection from the pool.

        Returns:
            An async context manager for a database connection.
        """
        return self._engine.connect()

    # ── Contracts ────────────────────────────────────────────────────────────

    async def create_contract(self, contract_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new contract record.

        Args:
            contract_data: Contract data dict.

        Returns:
            Created contract with ID.
        """
        contract_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        async with self.get_connection() as conn:
            await conn.execute(
                text("""
                    INSERT INTO contracts (contract_id, tenant_id, user_id, filename,
                        content_type, file_size, file_path, status, contract_type,
                        version, total_pages, tags, metadata, created_at, updated_at)
                    VALUES (:contract_id, :tenant_id, :user_id, :filename,
                        :content_type, :file_size, :file_path, :status, :contract_type,
                        :version, :total_pages, :tags, :metadata, :created_at, :updated_at)
                """),
                {
                    "contract_id": contract_id,
                    "tenant_id": contract_data.get("tenant_id", "default"),
                    "user_id": contract_data.get("user_id", "unknown"),
                    "filename": contract_data.get("filename", ""),
                    "content_type": contract_data.get("content_type", ""),
                    "file_size": contract_data.get("file_size", 0),
                    "file_path": contract_data.get("file_path", ""),
                    "status": contract_data.get("status", "pending"),
                    "contract_type": contract_data.get("contract_type", "other"),
                    "version": contract_data.get("version", 1),
                    "total_pages": contract_data.get("total_pages", 0),
                    "tags": contract_data.get("tags", []),
                    "metadata": json.dumps(contract_data.get("metadata", {})),
                    "created_at": now,
                    "updated_at": now,
                },
            )
            await conn.commit()

        return {**contract_data, "contract_id": contract_id, "created_at": now}

    def _parse_contract(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Parse contract row, converting JSON string fields to lists/dicts."""
        if row.get("tags") and isinstance(row["tags"], str):
            try:
                row["tags"] = json.loads(row["tags"])
            except (json.JSONDecodeError, TypeError):
                pass
        if row.get("metadata") and isinstance(row["metadata"], str):
            try:
                row["metadata"] = json.loads(row["metadata"])
            except (json.JSONDecodeError, TypeError):
                pass
        return row

    async def get_contract(self, contract_id: str) -> Optional[Dict[str, Any]]:
        """Get a contract by ID.

        Args:
            contract_id: Contract identifier.

        Returns:
            Contract dict or None.
        """
        async with self.get_connection() as conn:
            result = await conn.execute(
                text("SELECT * FROM contracts WHERE contract_id = :contract_id"),
                {"contract_id": contract_id},
            )
            row = result.fetchone()
            if row is None:
                return None
            return self._parse_contract(dict(row._mapping))

    async def list_contracts(
        self, tenant_id: str, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List contracts for a tenant.

        Args:
            tenant_id: Tenant identifier.
            limit: Max results.
            offset: Pagination offset.

        Returns:
            List of contract dicts.
        """
        async with self.get_connection() as conn:
            result = await conn.execute(
                text("""
                    SELECT * FROM contracts
                    WHERE tenant_id = :tenant_id
                    ORDER BY created_at DESC
                    LIMIT :limit OFFSET :offset
                """),
                {"tenant_id": tenant_id, "limit": limit, "offset": offset},
            )
            return [self._parse_contract(dict(row._mapping)) for row in result.fetchall()]

    async def delete_contract(self, contract_id: str) -> bool:
        """Delete a contract.

        Args:
            contract_id: Contract identifier.

        Returns:
            True if deleted.
        """
        async with self.get_connection() as conn:
            result = await conn.execute(
                text("DELETE FROM contracts WHERE contract_id = :contract_id"),
                {"contract_id": contract_id},
            )
            await conn.commit()
            return result.rowcount > 0

    # ── Redline Suggestions ──────────────────────────────────────────────────

    async def save_redline_suggestion(self, data: Dict[str, Any]) -> str:
        """Save a redline suggestion.

        Args:
            data: Suggestion data.

        Returns:
            Suggestion ID.
        """
        suggestion_id = data.get("suggestion_id", str(uuid.uuid4()))
        now = datetime.utcnow().isoformat()

        async with self.get_connection() as conn:
            await conn.execute(
                text("""
                    INSERT INTO redline_comparisons (comparison_id, source_contract_id,
                        target_contract_id, tenant_id, user_id, diff_text, summary,
                        changes, created_at)
                    VALUES (:comparison_id, :source_contract_id, :target_contract_id,
                        :tenant_id, :user_id, :diff_text, :summary, :changes, :created_at)
                """),
                {
                    "comparison_id": suggestion_id,
                    "source_contract_id": data.get("source_contract_id", ""),
                    "target_contract_id": data.get("target_contract_id", ""),
                    "tenant_id": data.get("tenant_id", "default"),
                    "user_id": data.get("user_id", "unknown"),
                    "diff_text": data.get("diff", ""),
                    "summary": json.dumps(data.get("summary", {})),
                    "changes": json.dumps(data.get("changes", [])),
                    "created_at": now,
                },
            )
            await conn.commit()

        return suggestion_id

    # ── Audit Log ────────────────────────────────────────────────────────────

    async def append_audit_log(self, entry: Dict[str, Any]) -> str:
        """Append an entry to the audit log.

        Args:
            entry: Audit entry data.

        Returns:
            Entry ID.
        """
        entry_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        async with self.get_connection() as conn:
            await conn.execute(
                text("""
                    INSERT INTO audit_logs (audit_id, tenant_id, user_id, action,
                        resource_type, resource_id, details, created_at)
                    VALUES (:audit_id, :tenant_id, :user_id, :action,
                        :resource_type, :resource_id, :details, :created_at)
                """),
                {
                    "audit_id": entry_id,
                    "tenant_id": entry.get("tenant_id", "default"),
                    "user_id": entry.get("actor_id", entry.get("user_id", "unknown")),
                    "action": entry.get("action", ""),
                    "resource_type": entry.get("resource_type", ""),
                    "resource_id": entry.get("resource_id", ""),
                    "details": json.dumps(entry.get("details", {})),
                    "created_at": now,
                },
            )
            await conn.commit()

        return entry_id

    async def query_audit_logs(
        self,
        tenant_id: str,
        limit: int = 100,
        offset: int = 0,
        action: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Query audit logs.

        Args:
            tenant_id: Tenant filter.
            limit: Max results.
            offset: Pagination offset.
            action: Optional action filter.

        Returns:
            List of audit entries.
        """
        query = """
            SELECT * FROM audit_logs
            WHERE tenant_id = :tenant_id
        """
        params: Dict[str, Any] = {"tenant_id": tenant_id, "limit": limit, "offset": offset}

        if action:
            query += " AND action = :action"
            params["action"] = action

        query += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"

        async with self.get_connection() as conn:
            result = await conn.execute(text(query), params)
            return [dict(row._mapping) for row in result.fetchall()]

    # ── Webhooks ─────────────────────────────────────────────────────────────

    async def save_webhook(self, data: Dict[str, Any]) -> str:
        """Save a webhook registration.

        Args:
            data: Webhook data.

        Returns:
            Webhook ID.
        """
        webhook_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        async with self.get_connection() as conn:
            await conn.execute(
                text("""
                    INSERT INTO webhook_registrations (webhook_id, tenant_id, user_id,
                        url, events, is_active, description, created_at, updated_at)
                    VALUES (:webhook_id, :tenant_id, :user_id,
                        :url, :events, :is_active, :description, :created_at, :updated_at)
                """),
                {
                    "webhook_id": webhook_id,
                    "tenant_id": data.get("tenant_id", "default"),
                    "user_id": data.get("user_id", "unknown"),
                    "url": data.get("url", ""),
                    "events": data.get("events", []),
                    "is_active": data.get("is_active", True),
                    "description": data.get("description", ""),
                    "created_at": now,
                    "updated_at": now,
                },
            )
            await conn.commit()

        return webhook_id

    async def list_webhooks(self, tenant_id: str) -> List[Dict[str, Any]]:
        """List webhooks for a tenant.

        Args:
            tenant_id: Tenant identifier.

        Returns:
            List of webhook dicts.
        """
        async with self.get_connection() as conn:
            result = await conn.execute(
                text("""
                    SELECT * FROM webhook_registrations
                    WHERE tenant_id = :tenant_id
                    ORDER BY created_at DESC
                """),
                {"tenant_id": tenant_id},
            )
            return [dict(row._mapping) for row in result.fetchall()]

    # ── Benchmark Corpus ────────────────────────────────────────────────────

    async def save_benchmark_clause(self, data: Dict[str, Any]) -> str:
        """Save a benchmark clause to the corpus.

        Args:
            data: Benchmark clause data.

        Returns:
            Clause ID.
        """
        clause_id = str(uuid.uuid4())

        async with self.get_connection() as conn:
            await conn.execute(
                text("""
                    INSERT INTO chunks (chunk_id, contract_id, tenant_id, chunk_index,
                        text, token_count, metadata, created_at)
                    VALUES (:chunk_id, :contract_id, :tenant_id, :chunk_index,
                        :text, :token_count, :metadata, :created_at)
                """),
                {
                    "chunk_id": clause_id,
                    "contract_id": data.get("source_document_id", "benchmark"),
                    "tenant_id": data.get("tenant_id", "default"),
                    "chunk_index": data.get("chunk_index", 0),
                    "text": data.get("clause_text", ""),
                    "token_count": data.get("token_count", len(data.get("clause_text", "").split())),
                    "metadata": json.dumps(data.get("metadata", {})),
                    "created_at": datetime.utcnow().isoformat(),
                },
            )
            await conn.commit()

        return clause_id

    # ── Health Check ─────────────────────────────────────────────────────────

    async def health_check(self) -> bool:
        """Check database connectivity.

        Returns:
            True if database is reachable.
        """
        try:
            conn = await self._engine.connect()
            await conn.execute(text("SELECT 1"))
            await conn.close()
            return True
        except Exception as exc:
            logger.warning("Database health check failed: %s", exc)
            return False

    # ── Users ────────────────────────────────────────────────────────────────

    async def list_users(self, tenant_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """List users for a tenant.

        Args:
            tenant_id: Tenant to filter by.
            limit: Maximum number of users.
            offset: Pagination offset.

        Returns:
            List of user dicts.
        """
        async with self.get_connection() as conn:
            result = await conn.execute(
                text("""
                    SELECT user_id, email, name, tenant_id, role, is_active,
                           permissions, metadata, last_login, created_at, updated_at
                    FROM users
                    WHERE tenant_id = :tenant_id
                    ORDER BY created_at DESC
                    LIMIT :limit OFFSET :offset
                """),
                {"tenant_id": tenant_id, "limit": limit, "offset": offset},
            )
            rows = result.fetchall()
            return [dict(row._mapping) for row in rows]

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a user by ID.

        Args:
            user_id: The user's Auth0 sub or internal ID.

        Returns:
            User dict or None.
        """
        async with self.get_connection() as conn:
            result = await conn.execute(
                text("""
                    SELECT user_id, email, name, tenant_id, role, is_active,
                           permissions, metadata, last_login, created_at, updated_at
                    FROM users
                    WHERE user_id = :user_id
                """),
                {"user_id": user_id},
            )
            row = result.fetchone()
            return dict(row._mapping) if row else None

    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user.

        Args:
            user_data: User data dict with keys: user_id, email, name, tenant_id,
                      role, is_active, permissions, metadata.

        Returns:
            Created user dict.
        """
        now = datetime.utcnow().isoformat()
        async with self.get_connection() as conn:
            await conn.execute(
                text("""
                    INSERT INTO users (user_id, email, name, tenant_id, role,
                        is_active, permissions, metadata, created_at, updated_at)
                    VALUES (:user_id, :email, :name, :tenant_id, :role,
                        :is_active, :permissions, :metadata, :created_at, :updated_at)
                """),
                {
                    "user_id": user_data["user_id"],
                    "email": user_data.get("email", ""),
                    "name": user_data.get("name", ""),
                    "tenant_id": user_data.get("tenant_id", "default"),
                    "role": user_data.get("role", "viewer"),
                    "is_active": user_data.get("is_active", True),
                    "permissions": json.dumps(user_data.get("permissions", [])),
                    "metadata": json.dumps(user_data.get("metadata", {})),
                    "created_at": now,
                    "updated_at": now,
                },
            )
            await conn.commit()
        return await self.get_user(user_data["user_id"])

    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a user.

        Args:
            user_id: The user to update.
            updates: Dict of fields to update.

        Returns:
            Updated user dict or None if not found.
        """
        allowed_fields = {"email", "name", "role", "is_active", "permissions", "metadata"}
        set_clauses = []
        params = {"user_id": user_id}

        for field in allowed_fields:
            if field in updates:
                if field == "metadata":
                    set_clauses.append(f"{field} = :{field}::jsonb")
                    params[field] = json.dumps(updates[field])
                elif field == "permissions":
                    set_clauses.append(f"{field} = :{field}")
                    params[field] = updates[field]
                else:
                    set_clauses.append(f"{field} = :{field}")
                    params[field] = updates[field]

        if not set_clauses:
            return await self.get_user(user_id)

        set_clauses.append("updated_at = :updated_at")
        params["updated_at"] = datetime.utcnow().isoformat()

        async with self.get_connection() as conn:
            await conn.execute(
                text(f"""
                    UPDATE users
                    SET {', '.join(set_clauses)}
                    WHERE user_id = :user_id
                """),
                params,
            )
            await conn.commit()
        return await self.get_user(user_id)

    async def delete_user(self, user_id: str) -> bool:
        """Delete a user.

        Args:
            user_id: The user to delete.

        Returns:
            True if deleted, False if not found.
        """
        async with self.get_connection() as conn:
            result = await conn.execute(
                text("DELETE FROM users WHERE user_id = :user_id"),
                {"user_id": user_id},
            )
            await conn.commit()
            return result.rowcount > 0

    # ── Contract Relationships ──────────────────────────────────────────────

    async def create_relationship(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a relationship between two contracts.

        Args:
            data: Dict with parent_contract_id, child_contract_id,
                  relationship_type, effective_date (optional), notes (optional).

        Returns:
            Created relationship dict.
        """
        import uuid
        relationship_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        async with self.get_connection() as conn:
            await conn.execute(
                text("""
                    INSERT INTO contract_relationships (relationship_id,
                        parent_contract_id, child_contract_id, relationship_type,
                        effective_date, notes, created_at)
                    VALUES (:relationship_id, :parent_contract_id, :child_contract_id,
                        :relationship_type, :effective_date, :notes, :created_at)
                """),
                {
                    "relationship_id": relationship_id,
                    "parent_contract_id": data["parent_contract_id"],
                    "child_contract_id": data["child_contract_id"],
                    "relationship_type": data["relationship_type"],
                    "effective_date": data.get("effective_date"),
                    "notes": data.get("notes"),
                    "created_at": now,
                },
            )
            await conn.commit()

        return {
            "relationship_id": relationship_id,
            "parent_contract_id": data["parent_contract_id"],
            "child_contract_id": data["child_contract_id"],
            "relationship_type": data["relationship_type"],
            "effective_date": data.get("effective_date"),
            "notes": data.get("notes"),
            "created_at": now,
        }

    async def get_relationship(self, relationship_id: str) -> Optional[Dict[str, Any]]:
        """Get a relationship by ID.

        Args:
            relationship_id: Relationship identifier.

        Returns:
            Relationship dict or None.
        """
        async with self.get_connection() as conn:
            result = await conn.execute(
                text("""
                    SELECT * FROM contract_relationships
                    WHERE relationship_id = :relationship_id
                """),
                {"relationship_id": relationship_id},
            )
            row = result.fetchone()
            return dict(row._mapping) if row else None

    async def list_relationships(
        self, contract_id: str
    ) -> List[Dict[str, Any]]:
        """List all relationships involving a contract (as parent or child).

        Args:
            contract_id: The contract to find relationships for.

        Returns:
            List of relationship dicts.
        """
        async with self.get_connection() as conn:
            result = await conn.execute(
                text("""
                    SELECT * FROM contract_relationships
                    WHERE parent_contract_id = :contract_id
                        OR child_contract_id = :contract_id
                    ORDER BY created_at DESC
                """),
                {"contract_id": contract_id},
            )
            return [dict(row._mapping) for row in result.fetchall()]

    async def list_all_relationships(self) -> List[Dict[str, Any]]:
        """List all contract relationships.

        Returns:
            List of all relationship dicts.
        """
        async with self.get_connection() as conn:
            result = await conn.execute(
                text("""
                    SELECT * FROM contract_relationships
                    ORDER BY created_at DESC
                """),
            )
            return [dict(row._mapping) for row in result.fetchall()]

    async def delete_relationship(self, relationship_id: str) -> bool:
        """Delete a relationship.

        Args:
            relationship_id: Relationship identifier.

        Returns:
            True if deleted.
        """
        async with self.get_connection() as conn:
            result = await conn.execute(
                text("""
                    DELETE FROM contract_relationships
                    WHERE relationship_id = :relationship_id
                """),
                {"relationship_id": relationship_id},
            )
            await conn.commit()
            return result.rowcount > 0

    async def update_contract_risk_score(
        self, contract_id: str, risk_score: float
    ) -> bool:
        """Update a contract's risk score.

        Args:
            contract_id: Contract identifier.
            risk_score: New risk score (0.0 to 1.0).

        Returns:
            True if updated.
        """
        now = datetime.utcnow().isoformat()
        async with self.get_connection() as conn:
            result = await conn.execute(
                text("""
                    UPDATE contracts
                    SET risk_score = :risk_score, updated_at = :updated_at
                    WHERE contract_id = :contract_id
                """),
                {
                    "contract_id": contract_id,
                    "risk_score": risk_score,
                    "updated_at": now,
                },
            )
            await conn.commit()
            return result.rowcount > 0
