"""RAG (Retrieval-Augmented Generation) API endpoints.

Provides semantic search over contract clauses using Pinecone vector
store with tenant isolation, metadata filtering, and MMR diversity.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from middleware.auth import TokenPayload, get_current_user, require_permission, Permissions
from rag.models import RAGResult, RetrievedChunk, SearchQuery

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["RAG"])


class RAGSearchRequest(BaseModel):
    """Request model for RAG search."""

    query_text: str = Field(..., min_length=1, max_length=5000, description="Search query text")
    top_k: int = Field(5, ge=1, le=50, description="Number of results to return")
    diversity: float = Field(0.3, ge=0.0, le=1.0, description="MMR diversity factor (0=relevance, 1=diverse)")
    min_score: float = Field(0.0, ge=0.0, le=1.0, description="Minimum similarity score filter")
    metadata_filter: Optional[Dict[str, Any]] = Field(None, description="Metadata filter dict")
    category: Optional[str] = Field(None, description="Risk category filter")


class RAGSearchResponse(BaseModel):
    """Response model for RAG search."""

    query: str
    results: List[Dict[str, Any]]
    total_found: int
    retrieval_time_ms: float
    embedding_time_ms: float


# Lazy initialization of RAG components
_retriever = None


def _get_retriever():
    """Get the RAG retriever singleton.

    Returns:
        RAGRetriever instance or None if not configured.
    """
    global _retriever
    if _retriever is not None:
        return _retriever

    pinecone_api_key = os.getenv("PINECONE_API_KEY", "")
    pinecone_env = os.getenv("PINECONE_ENVIRONMENT", "us-east-1-aws")
    pinecone_index = os.getenv("PINECONE_INDEX", "contract-chunks")
    openai_api_key = os.getenv("OPENAI_API_KEY", "")

    if not pinecone_api_key or not openai_api_key:
        logger.warning(
            "RAG not configured: set PINECONE_API_KEY and OPENAI_API_KEY"
        )
        return None

    try:
        from rag.vector_store import PineconeVectorStore
        from rag.embedding import EmbeddingPipeline
        from rag.retriever import RAGRetriever

        vector_store = PineconeVectorStore(
            api_key=pinecone_api_key,
            environment=pinecone_env,
            index_name=pinecone_index,
        )
        embedding = EmbeddingPipeline(api_key=openai_api_key)
        _retriever = RAGRetriever(
            vector_store=vector_store,
            embedding_pipeline=embedding,
        )
        logger.info("RAG retriever initialized")
        return _retriever
    except Exception as exc:
        logger.error("Failed to initialize RAG retriever: %s", exc)
        return None


@router.post("/search")
async def search_clauses(
    request: RAGSearchRequest,
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> RAGSearchResponse:
    """Search contract clauses using semantic RAG retrieval.

    Args:
        request: Search query parameters.
        user: Authenticated user.

    Returns:
        Ranked search results with similarity scores.

    Raises:
        HTTPException: If RAG is not configured or search fails.
    """
    retriever = _get_retriever()
    if retriever is None:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="RAG search is not configured. Set PINECONE_API_KEY and OPENAI_API_KEY.",
        )

    try:
        # Build metadata filter
        metadata_filter = dict(request.metadata_filter or {})
        if request.category:
            metadata_filter["risk_category"] = request.category

        query = SearchQuery(
            query_text=request.query_text,
            top_k=request.top_k,
            tenant_id=user.tenant_id,
            diversity_factor=request.diversity,
            min_score=request.min_score,
            metadata_filter=metadata_filter if metadata_filter else {},
        )

        result = await retriever.retrieve(query)

        return RAGSearchResponse(
            query=request.query_text,
            results=[
                {
                    "chunk_id": r.chunk_id,
                    "text": r.text[:2000],
                    "score": r.score,
                    "document_id": r.document_id,
                    "page_number": r.page_number,
                    "clause_type": r.clause_type,
                    "metadata": r.metadata,
                }
                for r in result.results
            ],
            total_found=result.total_found,
            retrieval_time_ms=result.retrieval_time_ms,
            embedding_time_ms=result.embedding_time_ms,
        )

    except RuntimeError as exc:
        if "Pinecone SDK" in str(exc):
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Pinecone SDK not installed. Run: pip install pinecone",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG search failed: {exc}",
        )
    except Exception as exc:
        logger.error("RAG search failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="RAG search failed",
        )


@router.get("/health")
async def rag_health_check(
    user: TokenPayload = Depends(get_current_user),
    _: None = Depends(require_permission(Permissions.READ_CONTRACTS)),
) -> Dict[str, Any]:
    """Check if RAG system is configured and healthy.

    Args:
        user: Authenticated user.

    Returns:
        Dict with RAG configuration status.
    """
    retriever = _get_retriever()
    pinecone_key = bool(os.getenv("PINECONE_API_KEY", ""))
    openai_key = bool(os.getenv("OPENAI_API_KEY", ""))

    return {
        "configured": retriever is not None,
        "pinecone_configured": pinecone_key,
        "openai_configured": openai_key,
        "index": os.getenv("PINECONE_INDEX", "contract-chunks"),
        "environment": os.getenv("PINECONE_ENVIRONMENT", "us-east-1-aws"),
    }
