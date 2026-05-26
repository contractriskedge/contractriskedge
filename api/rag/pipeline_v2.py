"""RAG 2.0 hierarchical retrieval pipeline — 5-stage grounded generation.

Implements a 5-stage hierarchical retrieval pipeline:
1. Contract type identification
2. Applicable legal playbook retrieval
3. Market benchmark retrieval
4. Jurisdiction-specific retrieval
5. Grounded recommendation generation

Integrates with existing LlamaIndex/Pinecone infrastructure.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .models import RAGResult, RetrievedChunk, SearchQuery
from .retriever import RAGRetriever
from .embedding import EmbeddingPipeline
from .vector_store import PineconeVectorStore
from .re_ranker import CrossEncoderReRanker
from .query_builder import QueryBuilder
from llm.models import LLMRequest, LLMResponse, Message, RoleType
from llm.client import LLMClient

logger = logging.getLogger(__name__)


@dataclass
class StageResult:
    """Result from a single stage of the retrieval pipeline."""

    stage_name: str
    success: bool
    chunks: List[RetrievedChunk] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    retrieval_time_ms: float = 0.0
    error: Optional[str] = None


@dataclass
class PipelineResult:
    """Complete result from the 5-stage retrieval pipeline."""

    success: bool
    contract_type: Optional[str] = None
    playbook_rules: List[Dict[str, Any]] = field(default_factory=list)
    market_benchmarks: List[Dict[str, Any]] = field(default_factory=list)
    jurisdiction_context: List[Dict[str, Any]] = field(default_factory=list)
    grounded_recommendation: Optional[str] = None
    all_evidence: List[Dict[str, Any]] = field(default_factory=list)
    total_retrieval_time_ms: float = 0.0
    stages: Dict[str, StageResult] = field(default_factory=dict)
    pipeline_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    error: Optional[str] = None


class RAGPipelineV2:
    """5-stage hierarchical retrieval pipeline for grounded risk analysis.

    Stages:
    1. Contract type identification — classifies the contract type
    2. Legal playbook retrieval — fetches applicable legal rules
    3. Market benchmark retrieval — compares against market standards
    4. Jurisdiction-specific retrieval — fetches jurisdiction context
    5. Grounded recommendation generation — produces final output

    Usage:
        pipeline = RAGPipelineV2(retriever, llm_client)
        result = await pipeline.run(clause_text, contract_type="SaaS Agreement")
    """

    def __init__(
        self,
        retriever: RAGRetriever,
        llm_client: Optional[LLMClient] = None,
        query_builder: Optional[QueryBuilder] = None,
        re_ranker: Optional[CrossEncoderReRanker] = None,
    ) -> None:
        """Initialize the RAG 2.0 pipeline.

        Args:
            retriever: The RAG retriever for vector search.
            llm_client: Optional LLM client for generation.
            query_builder: Optional query builder for search optimization.
            re_ranker: Optional cross-encoder re-ranker.
        """
        self._retriever = retriever
        self._llm_client = llm_client
        self._query_builder = query_builder or QueryBuilder()
        self._re_ranker = re_ranker

    async def run(
        self,
        clause_text: str,
        contract_type: Optional[str] = None,
        jurisdiction: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> PipelineResult:
        """Run the complete 5-stage retrieval pipeline.

        Args:
            clause_text: The clause text to analyze.
            contract_type: Optional contract type hint.
            jurisdiction: Optional jurisdiction hint.
            tenant_id: Optional tenant identifier.

        Returns:
            PipelineResult with all stage outputs.
        """
        pipeline_id = str(uuid.uuid4())
        start_time = time.monotonic()
        result = PipelineResult(pipeline_id=pipeline_id)

        try:
            # ── Stage 1: Contract Type Identification ──
            stage1 = await self._stage_contract_type(clause_text, contract_type, tenant_id)
            result.stages["contract_type"] = stage1
            contract_type = stage1.context.get("contract_type", contract_type or "unknown")
            result.contract_type = contract_type

            if not stage1.success:
                logger.warning("Stage 1 (contract type) failed, continuing: %s", stage1.error)

            # ── Stage 2: Legal Playbook Retrieval ──
            stage2 = await self._stage_playbook_retrieval(
                clause_text, contract_type, tenant_id
            )
            result.stages["playbook"] = stage2
            result.playbook_rules = stage2.context.get("rules", [])

            # ── Stage 3: Market Benchmark Retrieval ──
            stage3 = await self._stage_market_benchmarks(
                clause_text, contract_type, tenant_id
            )
            result.stages["market_benchmarks"] = stage3
            result.market_benchmarks = stage3.context.get("benchmarks", [])

            # ── Stage 4: Jurisdiction-Specific Retrieval ──
            stage4 = await self._stage_jurisdiction(
                clause_text, jurisdiction, tenant_id
            )
            result.stages["jurisdiction"] = stage4
            result.jurisdiction_context = stage4.context.get("jurisdiction_rules", [])

            # ── Stage 5: Grounded Recommendation Generation ──
            stage5 = await self._stage_grounded_generation(
                clause_text=clause_text,
                contract_type=contract_type,
                playbook_rules=result.playbook_rules,
                market_benchmarks=result.market_benchmarks,
                jurisdiction_context=result.jurisdiction_context,
                tenant_id=tenant_id,
            )
            result.stages["generation"] = stage5
            result.grounded_recommendation = stage5.context.get("recommendation")

            # Collect all evidence
            all_evidence = []
            for stage in [stage2, stage3, stage4]:
                for chunk in stage.chunks:
                    all_evidence.append({
                        "source": chunk.metadata.get("source", "unknown"),
                        "text": chunk.text[:500],
                        "score": chunk.score,
                        "stage": stage.stage_name,
                    })
            result.all_evidence = all_evidence

            result.success = all(
                s.success for s in result.stages.values()
            )
            result.total_retrieval_time_ms = (time.monotonic() - start_time) * 1000

            logger.info(
                "RAG pipeline %s completed in %.0fms: %d stages, %d evidence items",
                pipeline_id,
                result.total_retrieval_time_ms,
                len(result.stages),
                len(all_evidence),
            )

        except Exception as exc:
            logger.error("RAG pipeline %s failed: %s", pipeline_id, exc, exc_info=True)
            result.success = False
            result.error = str(exc)

        return result

    async def _stage_contract_type(
        self,
        clause_text: str,
        hint: Optional[str],
        tenant_id: Optional[str],
    ) -> StageResult:
        """Stage 1: Identify the contract type from the clause text.

        Args:
            clause_text: The clause text.
            hint: Optional contract type hint.
            tenant_id: Optional tenant identifier.

        Returns:
            StageResult with identified contract type.
        """
        stage = StageResult(stage_name="contract_type")
        start = time.monotonic()

        try:
            if hint:
                stage.context["contract_type"] = hint
                stage.success = True
            elif self._llm_client:
                prompt = (
                    "Identify the type of contract this clause is from. "
                    "Choose from: SaaS Agreement, Software License, Services Agreement, "
                    "NDA, Employment Contract, Supply Agreement, Distribution Agreement, "
                    "Partnership Agreement, Loan Agreement, Insurance Policy, Other.\n\n"
                    f"Clause:\n```\n{clause_text}\n```\n\n"
                    'Respond with JSON: {"contract_type": "string", "confidence": float, "reasoning": "string"}'
                )
                request = LLMRequest(
                    messages=[Message(role=RoleType.USER, content=prompt)],
                    temperature=0.1,
                    max_tokens=256,
                    tenant_id=tenant_id,
                    request_id=f"rag_stage1_{uuid.uuid4().hex[:8]}",
                )
                response = await self._llm_client.complete(request)
                try:
                    data = json.loads(response.content.strip())
                    stage.context["contract_type"] = data.get("contract_type", "Other")
                    stage.context["confidence"] = data.get("confidence", 0.5)
                except json.JSONDecodeError:
                    stage.context["contract_type"] = "Other"
            else:
                stage.context["contract_type"] = "Other"

            stage.success = True
        except Exception as exc:
            stage.error = str(exc)
            stage.context["contract_type"] = hint or "Other"

        stage.retrieval_time_ms = (time.monotonic() - start) * 1000
        return stage

    async def _stage_playbook_retrieval(
        self,
        clause_text: str,
        contract_type: str,
        tenant_id: Optional[str],
    ) -> StageResult:
        """Stage 2: Retrieve applicable legal playbook rules.

        Args:
            clause_text: The clause text.
            contract_type: Identified contract type.
            tenant_id: Optional tenant identifier.

        Returns:
            StageResult with playbook rules.
        """
        stage = StageResult(stage_name="playbook")
        start = time.monotonic()

        try:
            query_text = (
                f"Legal playbook rules for {contract_type}: {clause_text[:300]}"
            )
            search_query = SearchQuery(
                query_text=query_text,
                top_k=5,
                category_filter="playbook",
                tenant_id=tenant_id,
                metadata_filter={"contract_type": contract_type} if contract_type != "Other" else {},
            )
            rag_result = await self._retriever.retrieve(search_query)
            stage.chunks = rag_result.results

            # Extract rules from chunks
            rules = []
            for chunk in rag_result.results:
                rules.append({
                    "text": chunk.text[:500],
                    "score": chunk.score,
                    "source": chunk.metadata.get("source", "playbook"),
                    "rule_id": chunk.metadata.get("rule_id", ""),
                })
            stage.context["rules"] = rules
            stage.success = True
        except Exception as exc:
            stage.error = str(exc)
            logger.warning("Playbook retrieval failed: %s", exc)

        stage.retrieval_time_ms = (time.monotonic() - start) * 1000
        return stage

    async def _stage_market_benchmarks(
        self,
        clause_text: str,
        contract_type: str,
        tenant_id: Optional[str],
    ) -> StageResult:
        """Stage 3: Retrieve market benchmark comparisons.

        Args:
            clause_text: The clause text.
            contract_type: Identified contract type.
            tenant_id: Optional tenant identifier.

        Returns:
            StageResult with market benchmarks.
        """
        stage = StageResult(stage_name="market_benchmarks")
        start = time.monotonic()

        try:
            query_text = (
                f"Market benchmark for {contract_type} clauses: {clause_text[:300]}"
            )
            search_query = SearchQuery(
                query_text=query_text,
                top_k=5,
                category_filter="benchmark",
                tenant_id=tenant_id,
            )
            rag_result = await self._retriever.retrieve(search_query)
            stage.chunks = rag_result.results

            benchmarks = []
            for chunk in rag_result.results:
                benchmarks.append({
                    "text": chunk.text[:500],
                    "score": chunk.score,
                    "source": chunk.metadata.get("source", "benchmark"),
                    "percentile": chunk.metadata.get("percentile", 50),
                    "industry": chunk.metadata.get("industry", "general"),
                })
            stage.context["benchmarks"] = benchmarks
            stage.success = True
        except Exception as exc:
            stage.error = str(exc)
            logger.warning("Market benchmark retrieval failed: %s", exc)

        stage.retrieval_time_ms = (time.monotonic() - start) * 1000
        return stage

    async def _stage_jurisdiction(
        self,
        clause_text: str,
        jurisdiction: Optional[str],
        tenant_id: Optional[str],
    ) -> StageResult:
        """Stage 4: Retrieve jurisdiction-specific context.

        Args:
            clause_text: The clause text.
            jurisdiction: Optional jurisdiction hint.
            tenant_id: Optional tenant identifier.

        Returns:
            StageResult with jurisdiction rules.
        """
        stage = StageResult(stage_name="jurisdiction")
        start = time.monotonic()

        try:
            jur = jurisdiction or "US"
            query_text = (
                f"Jurisdiction-specific legal context for {jur}: {clause_text[:300]}"
            )
            search_query = SearchQuery(
                query_text=query_text,
                top_k=3,
                category_filter="jurisdiction",
                tenant_id=tenant_id,
                metadata_filter={"jurisdiction": jur},
            )
            rag_result = await self._retriever.retrieve(search_query)
            stage.chunks = rag_result.results

            jur_rules = []
            for chunk in rag_result.results:
                jur_rules.append({
                    "text": chunk.text[:500],
                    "score": chunk.score,
                    "jurisdiction": chunk.metadata.get("jurisdiction", jur),
                    "regulation": chunk.metadata.get("regulation", ""),
                })
            stage.context["jurisdiction_rules"] = jur_rules
            stage.success = True
        except Exception as exc:
            stage.error = str(exc)
            logger.warning("Jurisdiction retrieval failed: %s", exc)

        stage.retrieval_time_ms = (time.monotonic() - start) * 1000
        return stage

    async def _stage_grounded_generation(
        self,
        clause_text: str,
        contract_type: str,
        playbook_rules: List[Dict[str, Any]],
        market_benchmarks: List[Dict[str, Any]],
        jurisdiction_context: List[Dict[str, Any]],
        tenant_id: Optional[str],
    ) -> StageResult:
        """Stage 5: Generate grounded recommendations.

        Args:
            clause_text: The clause text.
            contract_type: Identified contract type.
            playbook_rules: Retrieved playbook rules.
            market_benchmarks: Retrieved market benchmarks.
            jurisdiction_context: Retrieved jurisdiction context.
            tenant_id: Optional tenant identifier.

        Returns:
            StageResult with grounded recommendation.
        """
        stage = StageResult(stage_name="generation")
        start = time.monotonic()

        try:
            if not self._llm_client:
                stage.context["recommendation"] = (
                    "LLM client not available. Recommendation generation skipped."
                )
                stage.success = True
                return stage

            # Build context from previous stages
            playbook_text = "\n".join(
                f"- {r['text'][:300]}" for r in playbook_rules[:3]
            ) if playbook_rules else "No specific playbook rules found."

            benchmark_text = "\n".join(
                f"- {b['text'][:300]}" for b in market_benchmarks[:3]
            ) if market_benchmarks else "No market benchmarks available."

            jurisdiction_text = "\n".join(
                f"- {j['text'][:300]}" for j in jurisdiction_context[:3]
            ) if jurisdiction_context else "No jurisdiction-specific context available."

            prompt = (
                "You are a senior contract attorney AI. Generate a grounded "
                "risk assessment and recommendation based on the following context.\n\n"
                f"CONTRACT TYPE: {contract_type}\n\n"
                f"CLAUSE TEXT:\n```\n{clause_text}\n```\n\n"
                f"APPLICABLE PLAYBOOK RULES:\n{playbook_text}\n\n"
                f"MARKET BENCHMARKS:\n{benchmark_text}\n\n"
                f"JURISDICTION CONTEXT:\n{jurisdiction_text}\n\n"
                "TASK:\n"
                "1. Assess the risk level of this clause.\n"
                "2. Compare against applicable playbook rules.\n"
                "3. Reference market benchmarks.\n"
                "4. Consider jurisdiction-specific factors.\n"
                "5. Provide specific, actionable recommendations.\n\n"
                "GROUND YOUR ANALYSIS IN THE PROVIDED EVIDENCE. "
                "If evidence is insufficient, state this clearly.\n\n"
                "OUTPUT FORMAT (JSON):\n"
                "{\n"
                '  "risk_level": "critical|high|medium|low",\n'
                '  "risk_score": float (0.0-1.0),\n'
                '  "key_findings": ["string"],\n'
                '  "playbook_analysis": "string",\n'
                '  "benchmark_analysis": "string",\n'
                '  "jurisdiction_analysis": "string",\n'
                '  "recommendation": "string",\n'
                '  "alternative_language": "string",\n'
                '  "evidence_gaps": ["string - any missing evidence"]\n'
                "}"
            )

            request = LLMRequest(
                messages=[Message(role=RoleType.USER, content=prompt)],
                temperature=0.1,
                max_tokens=2048,
                tenant_id=tenant_id,
                request_id=f"rag_stage5_{uuid.uuid4().hex[:8]}",
            )
            response = await self._llm_client.complete(request)

            try:
                data = json.loads(response.content.strip())
                stage.context["recommendation"] = data.get("recommendation", "")
                stage.context["risk_level"] = data.get("risk_level", "medium")
                stage.context["risk_score"] = data.get("risk_score", 0.5)
                stage.context["key_findings"] = data.get("key_findings", [])
                stage.context["full_analysis"] = data
            except json.JSONDecodeError:
                stage.context["recommendation"] = response.content[:1000]

            stage.success = True
        except Exception as exc:
            stage.error = str(exc)
            logger.warning("Grounded generation failed: %s", exc)

        stage.retrieval_time_ms = (time.monotonic() - start) * 1000
        return stage
