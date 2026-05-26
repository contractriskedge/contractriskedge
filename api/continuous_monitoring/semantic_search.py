"""Cross-contract semantic search engine (V2-024).

Provides natural language querying across all contracts in a tenant's
portfolio. Uses embeddings-based retrieval with hybrid search (semantic
+ keyword), faceted filtering, and clause-level result ranking.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SearchQuery:
    """A semantic search query with filters."""

    query_id: str
    natural_language_query: str
    tenant_id: str
    contract_type_filter: Optional[List[str]] = None
    risk_category_filter: Optional[List[str]] = None
    jurisdiction_filter: Optional[List[str]] = None
    date_range_start: Optional[str] = None
    date_range_end: Optional[str] = None
    counterparty_filter: Optional[List[str]] = None
    max_results: int = 20
    min_relevance_score: float = 0.5
    include_clause_text: bool = True
    include_metadata: bool = True
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "query_id": self.query_id,
            "natural_language_query": self.natural_language_query,
            "tenant_id": self.tenant_id,
            "contract_type_filter": self.contract_type_filter,
            "risk_category_filter": self.risk_category_filter,
            "jurisdiction_filter": self.jurisdiction_filter,
            "date_range_start": self.date_range_start,
            "date_range_end": self.date_range_end,
            "counterparty_filter": self.counterparty_filter,
            "max_results": self.max_results,
            "min_relevance_score": self.min_relevance_score,
            "created_at": self.created_at,
        }


@dataclass
class SearchResult:
    """A single semantic search result."""

    clause_id: str
    contract_id: str
    contract_name: str
    clause_text: str
    relevance_score: float
    semantic_score: float
    keyword_score: float
    section: Optional[str] = None
    page_number: Optional[int] = None
    risk_category: Optional[str] = None
    risk_score: Optional[float] = None
    contract_type: Optional[str] = None
    counterparty: Optional[str] = None
    jurisdiction: Optional[str] = None
    highlighted_text: Optional[str] = None
    matched_terms: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "clause_id": self.clause_id,
            "contract_id": self.contract_id,
            "contract_name": self.contract_name,
            "clause_text": self.clause_text[:500] + "..." if len(self.clause_text) > 500 else self.clause_text,
            "section": self.section,
            "page_number": self.page_number,
            "relevance_score": round(self.relevance_score, 4),
            "semantic_score": round(self.semantic_score, 4),
            "keyword_score": round(self.keyword_score, 4),
            "risk_category": self.risk_category,
            "risk_score": self.risk_score,
            "contract_type": self.contract_type,
            "counterparty": self.counterparty,
            "jurisdiction": self.jurisdiction,
            "highlighted_text": self.highlighted_text,
            "matched_terms": self.matched_terms,
        }


class SemanticSearchEngine:
    """Cross-contract semantic search engine.

    Supports natural language queries across the contract corpus with
    hybrid search (embeddings + keyword), faceted filtering, and
    clause-level result ranking.

    Usage:
        engine = SemanticSearchEngine()
        results = await engine.search("Find all uncapped indemnity clauses", tenant_id)
    """

    def __init__(
        self,
        embedding_model: str = "text-embedding-3-large",
        pinecone_index: Optional[Any] = None,
        db_repo: Optional[Any] = None,
    ) -> None:
        """Initialize the semantic search engine.

        Args:
            embedding_model: The embedding model to use.
            pinecone_index: Optional Pinecone index for vector search.
            db_repo: Optional database repository for metadata queries.
        """
        self._embedding_model = embedding_model
        self._pinecone_index = pinecone_index
        self._db_repo = db_repo
        self._search_history: List[SearchQuery] = []
        self._max_history: int = 1000

        # Query intent patterns for better search understanding
        self._intent_patterns = {
            "indemnity": ["uncapped indemnity", "indemnification", "indemnify", "hold harmless"],
            "liability": ["unlimited liability", "liability cap", "limitation of liability", "liable"],
            "confidentiality": ["confidentiality", "non-disclosure", "nda", "confidential information"],
            "termination": ["termination", "terminate", "termination for cause", "termination for convenience"],
            "renewal": ["renewal", "auto-renew", "renew", "evergreen"],
            "payment": ["payment terms", "payment", "invoice", "late payment", "interest"],
            "gdpr": ["gdpr", "data protection", "personal data", "data processing"],
            "insurance": ["insurance", "coverage", "certificate of insurance", "liability insurance"],
            "jurisdiction": ["governing law", "jurisdiction", "venue", "choice of law"],
            "non_compete": ["non-compete", "non compete", "restrictive covenant"],
            "audit": ["audit", "inspection", "records", "compliance audit"],
            "force_majeure": ["force majeure", "act of god", "unforeseen"],
            "assignment": ["assignment", "assign", "delegate", "subcontract"],
            "warranty": ["warranty", "warranties", "as-is", "as is"],
        }

    async def search(
        self,
        query: str,
        tenant_id: str,
        filters: Optional[Dict[str, Any]] = None,
        max_results: int = 20,
    ) -> Dict[str, Any]:
        """Execute a semantic search across all contracts.

        Args:
            query: Natural language search query.
            tenant_id: The tenant to search within.
            filters: Optional search filters (contract_type, risk_category, etc.).
            max_results: Maximum number of results.

        Returns:
            Dict with search results and metadata.
        """
        filters = filters or {}
        search_query = SearchQuery(
            query_id=str(uuid.uuid4()),
            natural_language_query=query,
            tenant_id=tenant_id,
            contract_type_filter=filters.get("contract_types"),
            risk_category_filter=filters.get("risk_categories"),
            jurisdiction_filter=filters.get("jurisdictions"),
            date_range_start=filters.get("date_start"),
            date_range_end=filters.get("date_end"),
            counterparty_filter=filters.get("counterparties"),
            max_results=max_results,
            min_relevance_score=filters.get("min_relevance", 0.5),
        )

        # Detect query intent
        detected_intents = self._detect_intent(query)
        search_query.metadata = {"detected_intents": detected_intents}

        # Execute hybrid search
        results = await self._execute_hybrid_search(search_query)

        # Store in history
        self._search_history.append(search_query)
        if len(self._search_history) > self._max_history:
            self._search_history = self._search_history[-self._max_history:]

        return {
            "query": search_query.to_dict(),
            "total_results": len(results),
            "results": [r.to_dict() for r in results[:max_results]],
            "detected_intents": detected_intents,
            "suggested_filters": self._suggest_filters(results),
        }

    def _detect_intent(self, query: str) -> Dict[str, float]:
        """Detect search intents in the query.

        Args:
            query: The natural language query.

        Returns:
            Dict of intent -> confidence score.
        """
        query_lower = query.lower()
        intents: Dict[str, float] = {}

        for intent, patterns in self._intent_patterns.items():
            for pattern in patterns:
                if pattern in query_lower:
                    intents[intent] = intents.get(intent, 0) + 1.0

        # Normalize scores
        if intents:
            max_score = max(intents.values())
            intents = {k: round(v / max_score, 2) for k, v in intents.items()}

        return intents

    async def _execute_hybrid_search(
        self,
        search_query: SearchQuery,
    ) -> List[SearchResult]:
        """Execute hybrid search combining semantic and keyword matching.

        Args:
            search_query: The search query with filters.

        Returns:
            Ranked list of search results.
        """
        results: List[SearchResult] = []

        if self._pinecone_index:
            # Use vector search via Pinecone
            results = await self._vector_search(search_query)
        else:
            # Fallback to keyword-based search
            results = await self._keyword_search(search_query)

        # Apply filters
        results = self._apply_filters(results, search_query)

        # Sort by relevance score
        results.sort(key=lambda r: r.relevance_score, reverse=True)

        return results

    async def _vector_search(
        self,
        search_query: SearchQuery,
    ) -> List[SearchResult]:
        """Execute vector similarity search via Pinecone.

        Args:
            search_query: The search query.

        Returns:
            List of search results.
        """
        if not self._pinecone_index:
            return await self._keyword_search(search_query)

        try:
            # Generate embedding for the query
            embedding = await self._generate_embedding(search_query.natural_language_query)

            # Query Pinecone with namespace isolation
            namespace = f"tenant_{search_query.tenant_id}"
            response = self._pinecone_index.query(
                vector=embedding,
                top_k=search_query.max_results * 2,
                namespace=namespace,
                include_metadata=True,
            )

            results = []
            for match in response.get("matches", []):
                metadata = match.get("metadata", {})
                result = SearchResult(
                    clause_id=match.get("id", "unknown"),
                    contract_id=metadata.get("contract_id", "unknown"),
                    contract_name=metadata.get("contract_name", "Unknown"),
                    clause_text=metadata.get("clause_text", ""),
                    section=metadata.get("section"),
                    page_number=metadata.get("page_number"),
                    relevance_score=match.get("score", 0.0),
                    semantic_score=match.get("score", 0.0),
                    keyword_score=0.0,
                    risk_category=metadata.get("risk_category"),
                    risk_score=metadata.get("risk_score"),
                    contract_type=metadata.get("contract_type"),
                    counterparty=metadata.get("counterparty"),
                    jurisdiction=metadata.get("jurisdiction"),
                    matched_terms=[],
                )
                results.append(result)

            return results

        except Exception as exc:
            logger.warning("Vector search failed, falling back to keyword: %s", exc)
            return await self._keyword_search(search_query)

    async def _keyword_search(
        self,
        search_query: SearchQuery,
    ) -> List[SearchResult]:
        """Execute keyword-based search as fallback.

        Args:
            search_query: The search query.

        Returns:
            List of search results.
        """
        query_terms = search_query.natural_language_query.lower().split()
        # Remove common stop words
        stop_words = {"the", "a", "an", "in", "on", "at", "to", "for", "of", "and", "or", "is", "are", "was", "were"}
        query_terms = [t for t in query_terms if t not in stop_words and len(t) > 2]

        if not self._db_repo:
            logger.warning("No database repository available for keyword search")
            return []

        try:
            # Use database full-text search
            async with self._db_repo.get_connection() as conn:
                from sqlalchemy import text

                # Build full-text search query
                tsquery = " & ".join(f"{term}:*" for term in query_terms)
                sql = text("""
                    SELECT c.contract_id, c.filename, cl.clause_id, cl.clause_text,
                           cl.section, cl.page_number, cl.risk_category, cl.risk_score,
                           c.contract_type, c.metadata,
                           ts_rank(to_tsvector('english', cl.clause_text),
                                   to_tsquery('english', :tsquery)) AS rank
                    FROM clauses cl
                    JOIN contracts c ON cl.contract_id = c.contract_id
                    WHERE c.tenant_id = :tenant_id
                      AND to_tsvector('english', cl.clause_text) @@ to_tsquery('english', :tsquery)
                    ORDER BY rank DESC
                    LIMIT :limit
                """)
                rows = await conn.execute(sql, {
                    "tsquery": tsquery,
                    "tenant_id": search_query.tenant_id,
                    "limit": search_query.max_results * 2,
                })
                rows = rows.fetchall() if hasattr(rows, 'fetchall') else rows

                results = []
                for row in rows:
                    result = SearchResult(
                        clause_id=row.clause_id,
                        contract_id=row.contract_id,
                        contract_name=row.filename,
                        clause_text=row.clause_text,
                        section=row.section,
                        page_number=row.page_number,
                        relevance_score=float(row.rank) if row.rank else 0.5,
                        semantic_score=0.0,
                        keyword_score=float(row.rank) if row.rank else 0.5,
                        risk_category=row.risk_category,
                        risk_score=float(row.risk_score) if row.risk_score else None,
                        contract_type=row.contract_type,
                        matched_terms=[t for t in query_terms if t in row.clause_text.lower()],
                    )
                    results.append(result)

                return results

        except Exception as exc:
            logger.error("Keyword search failed: %s", exc)
            return []

    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate an embedding vector for the query text.

        Args:
            text: The text to embed.

        Returns:
            Embedding vector.
        """
        try:
            import openai
            response = openai.embeddings.create(
                model=self._embedding_model,
                input=text,
            )
            return response.data[0].embedding
        except Exception as exc:
            logger.warning("Embedding generation failed: %s", exc)
            # Return a zero vector as fallback (will match nothing)
            return [0.0] * 1536  # text-embedding-3-large dimension

    def _apply_filters(
        self,
        results: List[SearchResult],
        query: SearchQuery,
    ) -> List[SearchResult]:
        """Apply post-search filters.

        Args:
            results: Initial search results.
            query: Search query with filters.

        Returns:
            Filtered results.
        """
        filtered = results

        if query.contract_type_filter:
            filtered = [r for r in filtered if r.contract_type in query.contract_type_filter]

        if query.risk_category_filter:
            filtered = [r for r in filtered if r.risk_category in query.risk_category_filter]

        if query.jurisdiction_filter:
            filtered = [r for r in filtered if r.jurisdiction in query.jurisdiction_filter]

        if query.counterparty_filter:
            filtered = [r for r in filtered if r.counterparty in query.counterparty_filter]

        if query.min_relevance_score > 0:
            filtered = [r for r in filtered if r.relevance_score >= query.min_relevance_score]

        return filtered

    def _suggest_filters(
        self,
        results: List[SearchResult],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Suggest facet filters based on results.

        Args:
            results: Search results.

        Returns:
            Dict of suggested filter categories and values.
        """
        contract_types: Dict[str, int] = {}
        risk_categories: Dict[str, int] = {}
        jurisdictions: Dict[str, int] = {}

        for r in results:
            if r.contract_type:
                contract_types[r.contract_type] = contract_types.get(r.contract_type, 0) + 1
            if r.risk_category:
                risk_categories[r.risk_category] = risk_categories.get(r.risk_category, 0) + 1
            if r.jurisdiction:
                jurisdictions[r.jurisdiction] = jurisdictions.get(r.jurisdiction, 0) + 1

        return {
            "contract_types": [{"value": k, "count": v} for k, v in
                                sorted(contract_types.items(), key=lambda x: -x[1])][:10],
            "risk_categories": [{"value": k, "count": v} for k, v in
                                 sorted(risk_categories.items(), key=lambda x: -x[1])][:10],
            "jurisdictions": [{"value": k, "count": v} for k, v in
                               sorted(jurisdictions.items(), key=lambda x: -x[1])][:5],
        }

    async def get_search_history(
        self,
        tenant_id: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get recent search history for a tenant.

        Args:
            tenant_id: The tenant identifier.
            limit: Maximum number of history entries.

        Returns:
            List of recent search query dicts.
        """
        tenant_history = [
            q for q in self._search_history
            if q.tenant_id == tenant_id
        ]
        return [q.to_dict() for q in tenant_history[-limit:]]

    async def get_popular_searches(
        self,
        tenant_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get popular searches for a tenant.

        Args:
            tenant_id: The tenant identifier.
            limit: Maximum number of entries.

        Returns:
            List of popular search terms with counts.
        """
        from collections import Counter

        tenant_history = [
            q for q in self._search_history
            if q.tenant_id == tenant_id
        ]

        query_counts = Counter(q.natural_language_query.lower() for q in tenant_history)
        return [
            {"query": query, "count": count}
            for query, count in query_counts.most_common(limit)
        ]
