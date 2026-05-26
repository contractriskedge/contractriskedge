"""RAG (Retrieval-Augmented Generation) module for contract risk analysis.

Provides Pinecone vector store integration, LlamaIndex RAG pipeline,
embedding generation, semantic retrieval, cross-encoder re-ranking,
RAG 2.0 hierarchical retrieval pipeline, and retrieval grounding validation.
"""

from __future__ import annotations

from .vector_store import PineconeVectorStore
from .embedding import EmbeddingPipeline
from .retriever import RAGRetriever
from .re_ranker import CrossEncoderReRanker
from .query_builder import QueryBuilder
from .models import RAGResult, RetrievedChunk, SearchQuery
from .pipeline_v2 import RAGPipelineV2, PipelineResult, StageResult
from .grounding import RetrievalGroundingValidator, GroundingValidationResult, EvidenceLink

__all__ = [
    "PineconeVectorStore",
    "EmbeddingPipeline",
    "RAGRetriever",
    "CrossEncoderReRanker",
    "QueryBuilder",
    "RAGResult",
    "RetrievedChunk",
    "SearchQuery",
    "RAGPipelineV2",
    "PipelineResult",
    "StageResult",
    "RetrievalGroundingValidator",
    "GroundingValidationResult",
    "EvidenceLink",
]
