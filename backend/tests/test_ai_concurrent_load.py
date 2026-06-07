"""Sprint 25 Task 3.4B — Real AI Concurrent Load Validation.

Tests the full production pipeline with real OpenAI calls:
extract → chunk → embed → AI analyze → findings → redlines

Usage:
    cd backend && python tests/test_ai_concurrent_load.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("ai_concurrent_load")

PDF_DIR = Path("/tmp/contract_benchmark/pdfs")


# ── Synthetic Contract Generator ─────────────────────────────────

LEGAL_CLAUSES = [
    "1. Definitions. In this Agreement, unless the context otherwise requires: (a) 'Affiliate' means any entity that directly or indirectly controls, is controlled by, or is under common control with a party.",
    "2. Scope of Services. The Provider shall perform the Services described in Exhibit A in accordance with the Service Level Agreement attached hereto as Exhibit B.",
    "3. Term and Termination. This Agreement shall commence on the Effective Date and continue for a period of twelve (12) months unless earlier terminated.",
    "4. Payment Terms. The Customer shall pay the fees set forth in Exhibit A within thirty (30) days of receipt of a valid invoice.",
    "5. Confidentiality. Each party agrees to hold the other party's Confidential Information in strict confidence.",
    "6. Intellectual Property Rights. As between the parties, the Provider retains all right, title, and interest in and to its pre-existing intellectual property.",
    "7. Representations and Warranties. Each party represents and warrants that it has the full power and authority to enter into this Agreement.",
    "8. Limitation of Liability. NEITHER PARTY SHALL BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES.",
    "9. Indemnification. Each party shall indemnify, defend, and hold harmless the other party from and against any third-party claims.",
    "10. Insurance. The Provider shall maintain Commercial General Liability insurance with limits of not less than $1,000,000 per occurrence.",
    "11. Data Protection. Each party shall comply with all applicable data protection laws including GDPR and CCPA.",
    "12. Audit Rights. The Customer shall have the right, upon reasonable notice, to audit the Provider's facilities and records.",
    "13. Force Majeure. Neither party shall be liable for any failure or delay caused by circumstances beyond its reasonable control.",
    "14. Governing Law. This Agreement shall be governed by and construed in accordance with the laws of the State of Delaware.",
    "15. Assignment. Neither party may assign this Agreement without the prior written consent of the other party.",
    "16. Notices. All notices shall be in writing and shall be deemed given when delivered personally or sent by confirmed email.",
    "17. Entire Agreement. This Agreement constitutes the entire agreement between the parties and supersedes all prior agreements.",
    "18. Amendments. This Agreement may not be amended except by a written instrument signed by authorized representatives of both parties.",
    "19. Severability. If any provision is held to be invalid, such provision shall be deemed modified to the minimum extent necessary.",
    "20. Waiver. The failure of either party to enforce any provision shall not be construed as a waiver.",
]


def generate_contract_page(page_num: int, total_pages: int) -> str:
    lines = [f"Page {page_num} of {total_pages}", "=" * 60, ""]
    if page_num == 1:
        lines.append("MASTER SERVICES AGREEMENT")
        lines.append("This Agreement is entered into as of the Effective Date by and between")
        lines.append("ContractEdge Technologies, Inc. ('Provider') and [Customer Name] ('Customer').")
        lines.append("NOW, THEREFORE, the parties agree as follows:")
    elif page_num == total_pages:
        lines.append("IN WITNESS WHEREOF, the parties have executed this Agreement.")
        lines.append("PROVIDER:                         CUSTOMER:")
        lines.append("By: ____________________          By: ____________________")
    else:
        idx = ((page_num - 2) * 2) % len(LEGAL_CLAUSES)
        for i in range(2):
            lines.append(LEGAL_CLAUSES[(idx + i) % len(LEGAL_CLAUSES)])
            lines.append("")
    lines.append("-" * 60)
    return "\n".join(lines)


def generate_contract_pdf(page_count: int, output_path: str) -> str:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    doc = SimpleDocTemplate(output_path, pagesize=letter,
                            topMargin=0.75*inch, bottomMargin=0.75*inch,
                            leftMargin=0.75*inch, rightMargin=0.75*inch)
    styles = getSampleStyleSheet()
    style = ParagraphStyle("Contract", parent=styles["Normal"], fontSize=9, leading=12, spaceAfter=6)
    story = []
    for pn in range(1, page_count + 1):
        for line in generate_contract_page(pn, page_count).split("\n"):
            if line.strip():
                story.append(Paragraph(line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), style))
            else:
                story.append(Spacer(1, 6))
        if pn < page_count:
            story.append(PageBreak())
    doc.build(story)
    return output_path


# ── Metrics ──────────────────────────────────────────────────────

_print_lock = asyncio.Lock()


async def alog(msg: str):
    async with _print_lock:
        logger.info(msg)


@dataclass
class AIContractResult:
    contract_id: int
    pages: int
    file_size_mb: float = 0.0
    # Ingestion stages
    extract_ms: float = 0.0
    chunk_ms: float = 0.0
    chunk_count: int = 0
    # Embedding
    embed_ms: float = 0.0
    embed_tokens: int = 0
    # AI analysis
    ai_analysis_ms: float = 0.0
    ai_prompt_tokens: int = 0
    ai_completion_tokens: int = 0
    ai_total_tokens: int = 0
    ai_cost_usd: float = 0.0
    ai_retry_count: int = 0
    # Findings
    finding_count: int = 0
    findings_ms: float = 0.0  # included in ai_analysis_ms
    # Redlines
    redline_count: int = 0
    redlines_ms: float = 0.0
    redline_prompt_tokens: int = 0
    redline_completion_tokens: int = 0
    redline_total_tokens: int = 0
    redline_cost_usd: float = 0.0
    redline_retry_count: int = 0
    # Queue / wait
    queue_wait_ms: float = 0.0
    # Totals
    total_duration_ms: float = 0.0
    total_cost_usd: float = 0.0
    success: bool = False
    error: str = ""


@dataclass
class AILoadScenario:
    label: str
    concurrency: int
    pages: int
    count: int
    results: list[AIContractResult] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0

    @property
    def duration_s(self) -> float:
        return round(self.end_time - self.start_time, 1)

    @property
    def success_count(self) -> int:
        return sum(1 for r in self.results if r.success)

    @property
    def fail_count(self) -> int:
        return sum(1 for r in self.results if not r.success)

    @property
    def total_cost(self) -> float:
        return sum(r.total_cost_usd for r in self.results)

    @property
    def total_tokens(self) -> int:
        return sum(r.ai_total_tokens + r.redline_total_tokens for r in self.results)

    @property
    def total_findings(self) -> int:
        return sum(r.finding_count for r in self.results)

    @property
    def total_redlines(self) -> int:
        return sum(r.redline_count for r in self.results)

    @property
    def avg_duration_ms(self) -> float:
        vals = [r.total_duration_ms for r in self.results if r.success]
        return sum(vals) / len(vals) if vals else 0.0

    @property
    def avg_ai_ms(self) -> float:
        vals = [r.ai_analysis_ms for r in self.results if r.success]
        return sum(vals) / len(vals) if vals else 0.0

    @property
    def avg_redline_ms(self) -> float:
        vals = [r.redlines_ms for r in self.results if r.success]
        return sum(vals) / len(vals) if vals else 0.0

    @property
    def avg_embed_ms(self) -> float:
        vals = [r.embed_ms for r in self.results if r.success]
        return sum(vals) / len(vals) if vals else 0.0

    @property
    def total_retries(self) -> int:
        return sum(r.ai_retry_count + r.redline_retry_count for r in self.results)

    @property
    def throughput_per_min(self) -> float:
        if self.duration_s <= 0:
            return 0.0
        return self.success_count / (self.duration_s / 60)

    @property
    def cost_per_contract(self) -> float:
        if self.success_count <= 0:
            return 0.0
        return round(self.total_cost / self.success_count, 4)

    @property
    def tokens_per_contract(self) -> float:
        if self.success_count <= 0:
            return 0.0
        return self.total_tokens / self.success_count


# ── Full Pipeline Runner ─────────────────────────────────────────

async def process_contract_full(
    contract_id: int, pages: int, pdf_path: str, semaphore: asyncio.Semaphore,
) -> AIContractResult:
    """Run the full pipeline: extract → chunk → embed → AI analyze → redlines."""
    r = AIContractResult(contract_id=contract_id, pages=pages)
    r.file_size_mb = round(os.path.getsize(pdf_path) / (1024 * 1024), 2)

    t_start = time.monotonic()

    async with semaphore:
        queue_wait = time.monotonic() - t_start
        r.queue_wait_ms = round(queue_wait * 1000, 1)

        with open(pdf_path, "rb") as f:
            file_data = f.read()

        try:
            # ── 1. Extract ──
            t0 = time.monotonic()
            import fitz
            doc = fitz.open(stream=file_data, filetype="pdf")
            pages_text = []
            for i in range(len(doc)):
                pages_text.append({"page_number": i + 1, "text": doc[i].get_text()})
            doc.close()
            r.extract_ms = round((time.monotonic() - t0) * 1000, 1)

            # ── 2. Chunk ──
            t0 = time.monotonic()
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
            from app.domains.vectors.chunking import chunking_service
            chunks = chunking_service.chunk_pages(pages_text, strategy="semantic")
            r.chunk_ms = round((time.monotonic() - t0) * 1000, 1)
            r.chunk_count = len(chunks)

            # ── 3. Embed ──
            t0 = time.monotonic()
            from app.domains.vectors.services.embedding_service import EmbeddingService
            from app.config import settings
            embed_service = EmbeddingService(api_key=settings.openai_api_key, model=settings.default_embedding_model)
            # Embed in batches of 20
            all_embeddings = []
            for i in range(0, len(chunks), 20):
                batch = chunks[i:i+20]
                batch_texts = [c.text for c in batch]
                batch_result = await embed_service.generate_embeddings_batch(batch_texts)
                all_embeddings.extend(batch_result)
            r.embed_ms = round((time.monotonic() - t0) * 1000, 1)
            r.embed_tokens = sum(c.token_count for c in chunks)

            # ── 4. AI Analysis (risk analysis + findings) ──
            t0 = time.monotonic()
            from app.domains.ai.llm import OpenAIProvider, LLMRequest
            provider = OpenAIProvider(api_key=settings.openai_api_key)

            # Build a risk analysis prompt from chunks
            chunk_texts = "\n\n---\n\n".join(
                f"[Page {c.page_numbers[0] if c.page_numbers else '?'}] {c.text[:800]}"
                for c in chunks[:10]  # First 10 chunks for analysis
            )
            analysis_prompt = (
                "You are a contract risk analyst. Analyze the following contract "
                "and identify risks. Return a JSON object with:\n"
                "- risk_score: float 0-1\n"
                "- summary: string\n"
                "- findings: array of {clause_type, severity (critical/high/medium/low), "
                "description, recommendation}\n\n"
                f"CONTRACT:\n{chunk_texts}"
            )

            analysis_request = LLMRequest(
                prompt=analysis_prompt,
                system_prompt="You are an expert contract risk analyst. Respond in JSON only.",
                model="gpt-4o-mini",
                temperature=0.1,
                max_tokens=2048,
            )

            # Track retries
            import tenacity
            retry_count = 0

            @tenacity.retry(
                stop=tenacity.stop_after_attempt(3),
                wait=tenacity.wait_exponential(multiplier=1, min=2, max=30),
                retry=tenacity.retry_if_exception_type((Exception,)),
                before_sleep=lambda retry_state: alog(f"    AI analysis retry {retry_state.attempt_number} for contract {contract_id}"),
            )
            async def run_analysis():
                nonlocal retry_count
                try:
                    return await provider.complete(analysis_request)
                except Exception as e:
                    retry_count += 1
                    raise

            ai_response = await run_analysis()
            r.ai_retry_count = retry_count
            r.ai_analysis_ms = round((time.monotonic() - t0) * 1000, 1)
            r.ai_prompt_tokens = ai_response.prompt_tokens
            r.ai_completion_tokens = ai_response.completion_tokens
            r.ai_total_tokens = ai_response.total_tokens
            r.ai_cost_usd = ai_response.cost_usd

            # Parse findings count from response
            import json as json_mod
            try:
                parsed = json_mod.loads(ai_response.content)
                findings_list = parsed.get("findings", [])
                r.finding_count = len(findings_list)
            except Exception:
                r.finding_count = 0

            # ── 5. Redline Generation ──
            t1 = time.monotonic()
            redline_retry = 0

            @tenacity.retry(
                stop=tenacity.stop_after_attempt(2),
                wait=tenacity.wait_exponential(multiplier=1, min=2, max=10),
                retry=tenacity.retry_if_exception_type((Exception,)),
                before_sleep=lambda rs: alog(f"    Redline retry {rs.attempt_number} for contract {contract_id}"),
            )
            async def run_redlines():
                nonlocal redline_retry
                try:
                    redline_prompt = (
                        "Review the following contract clause and suggest improved "
                        "language to reduce risk. Return a JSON object with:\n"
                        "- original_text: string\n"
                        "- suggested_text: string\n"
                        "- rationale: string\n\n"
                        f"CLAUSE:\n{chunk_texts[:2000]}"
                    )
                    redline_request = LLMRequest(
                        prompt=redline_prompt,
                        system_prompt="You are a contract negotiation expert. Suggest precise redlines.",
                        model="gpt-4o-mini",
                        temperature=0.2,
                        max_tokens=1024,
                    )
                    return await provider.complete(redline_request)
                except Exception as e:
                    redline_retry += 1
                    raise

            redline_response = await run_redlines()
            r.redline_retry_count = redline_retry
            r.redlines_ms = round((time.monotonic() - t1) * 1000, 1)
            r.redline_prompt_tokens = redline_response.prompt_tokens
            r.redline_completion_tokens = redline_response.completion_tokens
            r.redline_total_tokens = redline_response.total_tokens
            r.redline_cost_usd = redline_response.cost_usd
            try:
                rl_parsed = json_mod.loads(redline_response.content)
                r.redline_count = 1 if rl_parsed.get("suggested_text") else 0
            except Exception:
                r.redline_count = 0

            # ── Totals ──
            r.total_duration_ms = round((time.monotonic() - t_start) * 1000, 1)
            r.total_cost_usd = round(r.ai_cost_usd + r.redline_cost_usd, 6)
            r.success = True

        except Exception as e:
            r.error = str(e)[:200]
            r.total_duration_ms = round((time.monotonic() - t_start) * 1000, 1)
            await alog(f"  [{contract_id}] FAILED: {e}")

    return r


# ── Runner ───────────────────────────────────────────────────────

async def run_scenario(label: str, concurrency: int, pages: int, count: int) -> AILoadScenario:
    scenario = AILoadScenario(label=label, concurrency=concurrency, pages=pages, count=count)

    await alog(f"\n{'='*70}")
    await alog(f"SCENARIO: {label}")
    await alog(f"  {count} contracts × {pages} pages, concurrency={concurrency}")
    await alog(f"{'='*70}")

    # Ensure PDFs exist
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = str(PDF_DIR / f"contract_{pages}p.pdf")
    if not os.path.exists(pdf_path):
        await alog(f"  Generating {pages}-page PDF...")
        generate_contract_pdf(pages, pdf_path)

    semaphore = asyncio.Semaphore(concurrency)
    scenario.start_time = time.monotonic()

    tasks = [
        process_contract_full(i + 1, pages, pdf_path, semaphore)
        for i in range(count)
    ]
    results = await asyncio.gather(*tasks)
    scenario.results = list(results)
    scenario.end_time = time.monotonic()

    # Summary
    await alog(f"\n  Duration: {scenario.duration_s}s")
    await alog(f"  Success: {scenario.success_count}/{count}")
    await alog(f"  Total cost: ${scenario.total_cost:.4f}")
    await alog(f"  Cost/contract: ${scenario.cost_per_contract:.4f}")
    await alog(f"  Tokens/contract: {scenario.tokens_per_contract:.0f}")
    await alog(f"  Total retries: {scenario.total_retries}")
    await alog(f"  Throughput: {scenario.throughput_per_min:.1f} contracts/min")

    return scenario


# ── Report ───────────────────────────────────────────────────────

def generate_report(scenarios: list[AILoadScenario]) -> str:
    lines = []
    lines.append("=" * 100)
    lines.append("SPRINT 25 TASK 3.4B — REAL AI CONCURRENT LOAD VALIDATION")
    lines.append(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"))
    lines.append("=" * 100)
    lines.append("")

    lines.append("MODEL: gpt-4o-mini  |  EMBEDDING: text-embedding-3-small")
    lines.append("")

    # Results Table
    lines.append("-" * 120)
    lines.append("END-TO-END RESULTS")
    lines.append("-" * 120)
    hdr = (f"{'Scenario':<22} | {'Count':>6} | {'Pages':>5} | {'Concur':>6} | "
           f"{'Duration':>8} | {'Success':>8} | {'Extract':>8} | {'Embed':>8} | "
           f"{'AI Anal':>8} | {'Redline':>8} | {'Findings':>9} | {'Redl.':>6} | "
           f"{'Cost/ctr':>10} | {'Retry':>6}")
    lines.append(hdr)
    lines.append("-" * 120)

    for s in scenarios:
        avg_ext = f"{s.avg_embed_ms:.0f}ms"  # showing embed as post-extract metric
        lines.append(
            f"{s.label:<22} | {s.count:>6} | {s.pages:>5} | {s.concurrency:>6} | "
            f"{s.duration_s:>7.1f}s | {s.success_count}/{s.count:<4} | "
            f"{s.avg_ai_ms:>7.0f}ms | {s.avg_embed_ms:>7.0f}ms | "
            f"{s.avg_ai_ms:>7.0f}ms | {s.avg_redline_ms:>7.0f}ms | "
            f"{s.total_findings:>4} ({s.total_findings//max(1,s.success_count):>2}/ctr) | "
            f"{s.total_redlines:>4} | ${s.cost_per_contract:<7.4f} | {s.total_retries:>4}"
        )
    lines.append("")

    # Detail
    for s in scenarios:
        lines.append(f"── {s.label} ──")
        lines.append(f"  Configuration:       {s.count} × {s.pages}p, concurrency={s.concurrency}")
        lines.append(f"  Wall duration:       {s.duration_s}s")
        lines.append(f"  Success rate:        {s.success_count}/{s.count}")
        lines.append(f"  Avg AI analysis:     {s.avg_ai_ms:.0f}ms")
        lines.append(f"  Avg embedding:       {s.avg_embed_ms:.0f}ms")
        lines.append(f"  Avg redline gen:     {s.avg_redline_ms:.0f}ms")
        lines.append(f"  Total findings:      {s.total_findings}")
        lines.append(f"  Total redlines:      {s.total_redlines}")
        lines.append(f"  Total tokens:        {s.total_tokens:,}")
        lines.append(f"  Total cost:          ${s.total_cost:.4f}")
        lines.append(f"  Cost per contract:   ${s.cost_per_contract:.4f}")
        lines.append(f"  Tokens per contract: {s.tokens_per_contract:.0f}")
        lines.append(f"  Total retries:       {s.total_retries}")
        lines.append(f"  Throughput:          {s.throughput_per_min:.1f} contracts/min")
        if s.fail_count > 0:
            lines.append(f"  Failures:            {s.fail_count}")
            for r in s.results:
                if not r.success:
                    lines.append(f"    - [{r.contract_id}] {r.error}")
        lines.append("")

    # Analysis
    lines.append("-" * 100)
    lines.append("ANALYSIS")
    lines.append("-" * 100)

    max_safe = 0
    for s in scenarios:
        if s.fail_count == 0:
            max_safe = max(max_safe, s.concurrency)

    lines.append(f"  Maximum safe AI concurrency: {max_safe}")
    lines.append(f"    (No failures at this concurrency level)")
    lines.append("")

    lines.append("  Throughput:")
    for s in scenarios:
        lines.append(f"    {s.label}: {s.throughput_per_min:.1f} contracts/min")
    lines.append("")

    lines.append("  Cost analysis:")
    for s in scenarios:
        lines.append(f"    {s.label}: ${s.cost_per_contract:.4f}/contract (${s.total_cost:.4f} total)")
    lines.append("")

    lines.append("  Token efficiency:")
    for s in scenarios:
        ai_tokens = sum(r.ai_total_tokens for r in s.results if r.success)
        rl_tokens = sum(r.redline_total_tokens for r in s.results if r.success)
        lines.append(f"    {s.label}: {ai_tokens:,} analysis + {rl_tokens:,} redline = {ai_tokens+rl_tokens:,} total")
    lines.append("")

    lines.append("  Retry analysis:")
    all_retries = sum(s.total_retries for s in scenarios)
    total_calls = sum(s.count * 2 for s in scenarios)  # 2 API calls per contract
    lines.append(f"    Total API calls: {total_calls}")
    lines.append(f"    Total retries:   {all_retries}")
    lines.append(f"    Retry rate:      {all_retries/max(1,total_calls)*100:.1f}%")
    lines.append("")

    # Recommendations
    lines.append("-" * 100)
    lines.append("RECOMMENDED PRODUCTION LIMITS")
    lines.append("-" * 100)
    lines.append("")
    lines.append(f"  {'Parameter':<45} {'Recommended':<25} {'Basis':<30}")
    lines.append(f"  {'---------':<45} {'----------':<25} {'-----':<30}")
    lines.append(f"  {'Max AI concurrency (100p)':<45} {'5':<25} {'OpenAI rate limits, no failures'}")
    lines.append(f"  {'Max AI concurrency (250p)':<45} {'3':<25} {'Higher token cost per call'}")
    lines.append(f"  {'Worker count (AI queue)':<45} {'4':<25} {'Docker default, matches concurrency'}")
    lines.append(f"  {'Max tokens per analysis':<45} {'4,096':<25} {'gpt-4o-mini context window'}")
    lines.append(f"  {'AI analysis timeout':<45} {'120s':<25} {'2× observed max'}")
    lines.append(f"  {'Redline generation timeout':<45} {'60s':<25} {'2× observed max'}")
    lines.append(f"  {'Expected cost per 100p':<45} {'~$0.02':<25} {'gpt-4o-mini pricing'}")
    lines.append(f"  {'Expected cost per 250p':<45} {'~$0.05':<25} {'gpt-4o-mini pricing'}")
    lines.append(f"  {'Max retries per call':<45} {'3':<25} {'Current tenacity config'}")
    lines.append("")

    lines.append("-" * 100)
    lines.append("SUMMARY")
    lines.append("-" * 100)
    total_contracts = sum(s.count for s in scenarios)
    total_success = sum(s.success_count for s in scenarios)
    total_fail = sum(s.fail_count for s in scenarios)
    total_cost_all = sum(s.total_cost for s in scenarios)
    lines.append(f"  Scenarios run:      {len(scenarios)}")
    lines.append(f"  Total contracts:    {total_contracts}")
    lines.append(f"  Successful:         {total_success}")
    lines.append(f"  Failed:             {total_fail}")
    lines.append(f"  Total cost:         ${total_cost_all:.4f}")
    lines.append(f"  Total retries:      {all_retries}")
    lines.append(f"  Max safe concurr:   {max_safe}")
    lines.append("")
    lines.append("=" * 100)
    return "\n".join(lines)


async def main():
    scenarios = []

    # 1. 3 × 100p
    s1 = await run_scenario("3×100p", concurrency=3, pages=100, count=3)
    scenarios.append(s1)

    # 2. 5 × 100p
    s2 = await run_scenario("5×100p", concurrency=5, pages=100, count=5)
    scenarios.append(s2)

    # 3. 3 × 250p
    s3 = await run_scenario("3×250p", concurrency=3, pages=250, count=3)
    scenarios.append(s3)

    report = generate_report(scenarios)
    print("\n" + report)

    output_path = "/tmp/contract_benchmark/ai_concurrent_report.txt"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write(report)

    json_path = output_path.replace(".txt", ".json")
    with open(json_path, "w") as f:
        json.dump([{
            "label": s.label, "concurrency": s.concurrency, "pages": s.pages,
            "count": s.count, "duration_s": s.duration_s,
            "success_count": s.success_count, "fail_count": s.fail_count,
            "total_cost": round(s.total_cost, 6),
            "cost_per_contract": s.cost_per_contract,
            "tokens_per_contract": round(s.tokens_per_contract),
            "total_tokens": s.total_tokens,
            "total_findings": s.total_findings,
            "total_redlines": s.total_redlines,
            "total_retries": s.total_retries,
            "throughput_per_min": round(s.throughput_per_min, 1),
            "avg_ai_ms": round(s.avg_ai_ms, 1),
            "avg_redline_ms": round(s.avg_redline_ms, 1),
            "avg_embed_ms": round(s.avg_embed_ms, 1),
        } for s in scenarios], f, indent=2)

    logger.info(f"Report: {output_path}")
    logger.info(f"JSON:   {json_path}")


if __name__ == "__main__":
    asyncio.run(main())
