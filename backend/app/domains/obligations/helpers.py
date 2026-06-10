"""Obligation creation helpers — contract numbering, clause search, user search.

Provides endpoints used by the Create Obligation modal for searchable dropdowns.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_tenant_id
from app.kernel.security.rbac import require_permission
from app.kernel.security.permissions import Permissions

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/obligation-helpers", tags=["Obligation Helpers"])


@router.get("/clause-references", response_model=None)
async def search_clause_references(
    q: str = Query("", max_length=200),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Search clause references from the clause library.

    Returns matching clause names/types that can be used as clause_reference
    in obligation creation. Maintains a "recently used" concept based on
    the obligation_audit_log.
    """
    results = []

    # Check which tables exist using information_schema (safe, won't poison transaction)
    tables_exist = {}
    for t in ["clause_catalog", "review_findings", "obligations"]:
        try:
            r = await db.execute(
                text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = :t)"),
                {"t": t},
            )
            tables_exist[t] = r.scalar() or False
        except Exception:
            tables_exist[t] = False

    # 1. Try clause_catalog if it exists
    if q and tables_exist.get("clause_catalog"):
        try:
            stmt = text("""
                SELECT cc.clause_id, cc.clause_type, cc.title, cc.content
                FROM clause_catalog cc
                WHERE cc.tenant_id = :tenant_id
                  AND (cc.title ILIKE :query OR cc.clause_type ILIKE :query OR cc.content ILIKE :query)
                ORDER BY
                    CASE WHEN cc.title ILIKE :query THEN 0 ELSE 1 END,
                    cc.usage_count DESC
                LIMIT :limit
            """)
            rows = await db.execute(stmt, {"tenant_id": tenant_id, "query": f"%{q}%", "limit": limit})
            for row in rows.fetchall():
                results.append({
                    "id": str(row.clause_id),
                    "type": "clause_library",
                    "label": row.title or row.clause_type,
                    "detail": row.clause_type,
                    "value": row.title or row.clause_type,
                })
        except Exception:
            pass

    # 2. Search from review_findings clause_type as fallback
    if not results and q and tables_exist.get("review_findings"):
        try:
            stmt = text("""
                SELECT DISTINCT clause_type, COUNT(*) as cnt
                FROM review_findings
                WHERE tenant_id = :tenant_id
                  AND clause_type ILIKE :query
                GROUP BY clause_type
                ORDER BY cnt DESC
                LIMIT :limit
            """)
            rows = await db.execute(stmt, {"tenant_id": tenant_id, "query": f"%{q}%", "limit": limit})
            for row in rows.fetchall():
                results.append({
                    "id": row.clause_type,
                    "type": "finding",
                    "label": row.clause_type.replace("_", " ").title(),
                    "detail": f"Found in {row.cnt} findings",
                    "value": row.clause_type,
                })
        except Exception:
            pass

    # 3. No query: return recently used clause references from obligations
    if not q and tables_exist.get("obligations"):
        try:
            stmt = text("""
                SELECT DISTINCT o.clause_reference, COUNT(*) as usage_count
                FROM obligations o
                WHERE o.tenant_id = :tenant_id
                  AND o.clause_reference IS NOT NULL
                  AND o.clause_reference != ''
                GROUP BY o.clause_reference
                ORDER BY usage_count DESC, MAX(o.updated_at) DESC
                LIMIT :limit
            """)
            rows = await db.execute(stmt, {"tenant_id": tenant_id, "limit": limit})
            for row in rows.fetchall():
                results.append({
                    "id": row.clause_reference,
                    "type": "recent",
                    "label": row.clause_reference,
                    "detail": f"Used {row.usage_count} times",
                    "value": row.clause_reference,
                })
        except Exception:
            pass

    return {"data": results, "total": len(results)}


@router.get("/users", response_model=None)
async def search_users(
    q: str = Query("", max_length=200),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Search admin users for Owner / Assignee fields.

    Returns user name, email, role, and department.
    """
    query = select(
        text("user_id, name, email, role, business_unit")
    ).select_from(text("admin_users")).where(
        text("tenant_id = :tenant_id")
    )
    bind = {"tenant_id": tenant_id}

    if q:
        query = query.where(
            text("(name ILIKE :query OR email ILIKE :query)")
        )
        bind["query"] = f"%{q}%"

    query = query.order_by(text("is_active DESC, name ASC")).limit(limit)
    rows = await db.execute(query, bind)

    results = []
    for row in rows.fetchall():
        results.append({
            "id": str(row.user_id),
            "name": row.name,
            "email": row.email,
            "role": row.role,
            "department": row.business_unit,
            "business_unit": row.business_unit,
        })

    return {"data": results, "total": len(results)}


@router.get("/departments", response_model=None)
async def search_departments(
    q: str = Query("", max_length=200),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Search distinct department values from admin_users and obligations."""
    results = []
    seen = set()

    # From admin_users (business_unit is the closest concept to department)
    stmt = text("""
        SELECT DISTINCT business_unit FROM admin_users
        WHERE tenant_id = :tenant_id
          AND business_unit IS NOT NULL
          AND business_unit != ''
          AND (:q = '' OR business_unit ILIKE :q_pattern)
        ORDER BY business_unit
        LIMIT :limit
    """)
    rows = await db.execute(stmt, {"tenant_id": tenant_id, "q": q, "q_pattern": f"%{q}%", "limit": limit})
    for row in rows.fetchall():
        dept = row.business_unit
        if dept and dept not in seen:
            seen.add(dept)
            results.append({"value": dept, "label": dept, "source": "users"})

    # From obligations (if we haven't hit limit)
    if len(results) < limit:
        remaining = limit - len(results)
        stmt2 = text("""
            SELECT DISTINCT department FROM obligations
            WHERE tenant_id = :tenant_id
              AND department IS NOT NULL
              AND department != ''
              AND (:q = '' OR department ILIKE :q_pattern)
            ORDER BY department
            LIMIT :remaining
        """)
        rows2 = await db.execute(stmt2, {"tenant_id": tenant_id, "q": q, "q_pattern": f"%{q}%", "remaining": remaining})
        for row in rows2.fetchall():
            dept = row.department
            if dept and dept not in seen:
                seen.add(dept)
                results.append({"value": dept, "label": dept, "source": "obligations"})

    return {"data": results, "total": len(results)}


@router.get("/business-units", response_model=None)
async def search_business_units(
    q: str = Query("", max_length=200),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_tenant_id),
    _: None = Depends(require_permission(Permissions.CONTRACTS_READ)),
):
    """Search distinct business_unit values from admin_users and obligations."""
    results = []
    seen = set()

    stmt = text("""
        SELECT DISTINCT business_unit FROM admin_users
        WHERE tenant_id = :tenant_id
          AND business_unit IS NOT NULL
          AND business_unit != ''
          AND (:q = '' OR business_unit ILIKE :q_pattern)
        ORDER BY business_unit
        LIMIT :limit
    """)
    rows = await db.execute(stmt, {"tenant_id": tenant_id, "q": q, "q_pattern": f"%{q}%", "limit": limit})
    for row in rows.fetchall():
        bu = row.business_unit
        if bu and bu not in seen:
            seen.add(bu)
            results.append({"value": bu, "label": bu, "source": "users"})

    if len(results) < limit:
        remaining = limit - len(results)
        stmt2 = text("""
            SELECT DISTINCT business_unit FROM obligations
            WHERE tenant_id = :tenant_id
              AND business_unit IS NOT NULL
              AND business_unit != ''
              AND (:q = '' OR business_unit ILIKE :q_pattern)
            ORDER BY business_unit
            LIMIT :remaining
        """)
        rows2 = await db.execute(stmt2, {"tenant_id": tenant_id, "q": q, "q_pattern": f"%{q}%", "remaining": remaining})
        for row in rows2.fetchall():
            bu = row.business_unit
            if bu and bu not in seen:
                seen.add(bu)
                results.append({"value": bu, "label": bu, "source": "obligations"})

    return {"data": results, "total": len(results)}
