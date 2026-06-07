"""Sprint 25 Task 3.3 — Large Contract Validation Benchmark (v2).

Measures extraction, chunking, and estimates embedding/AI costs.
Skips real API calls (OpenAI) — uses local measurement for the
critical path, then projects embedding/AI costs from chunk counts.

Usage:
    cd backend && python tests/test_large_contract_benchmark.py
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("contract_benchmark")


# ── Synthetic Contract Generator ─────────────────────────────────

LEGAL_CLAUSES = [
    "1. Definitions. In this Agreement, unless the context otherwise requires: (a) 'Affiliate' means any entity that directly or indirectly controls, is controlled by, or is under common control with a party; (b) 'Confidential Information' means all information disclosed by one party to the other in connection with this Agreement.",
    "2. Scope of Services. The Provider shall perform the Services described in Exhibit A in accordance with the Service Level Agreement attached hereto as Exhibit B. The Customer shall provide reasonable access to its facilities, systems, and personnel as necessary for the performance of the Services.",
    "3. Term and Termination. This Agreement shall commence on the Effective Date and continue for a period of twelve (12) months unless earlier terminated. Either party may terminate this Agreement for convenience upon ninety (90) days written notice. Either party may terminate immediately if the other party materially breaches and fails to cure within thirty (30) days.",
    "4. Payment Terms. The Customer shall pay the fees set forth in Exhibit A within thirty (30) days of receipt of a valid invoice. Late payments shall accrue interest at the rate of one and one-half percent (1.5%) per month or the maximum rate permitted by applicable law, whichever is less.",
    "5. Confidentiality. Each party agrees to hold the other party's Confidential Information in strict confidence and not to disclose such information to any third party without the prior written consent of the disclosing party.",
    "6. Intellectual Property Rights. As between the parties, the Provider retains all right, title, and interest in and to its pre-existing intellectual property. The Customer retains all right, title, and interest in and to its data and pre-existing intellectual property.",
    "7. Representations and Warranties. Each party represents and warrants that: (a) it has the full power and authority to enter into this Agreement; (b) the execution and performance of this Agreement does not violate any applicable law or regulation.",
    "8. Limitation of Liability. NEITHER PARTY SHALL BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES. EACH PARTY'S TOTAL LIABILITY SHALL NOT EXCEED THE TOTAL FEES PAID DURING THE TWELVE (12) MONTHS PRECEDING THE CLAIM.",
    "9. Indemnification. Each party shall indemnify, defend, and hold harmless the other party from and against any third-party claims arising from the Indemnitor's breach of this Agreement, gross negligence, or willful misconduct.",
    "10. Insurance. The Provider shall maintain Commercial General Liability insurance with limits of not less than $1,000,000 per occurrence and Professional Liability insurance with limits of not less than $2,000,000 per claim.",
    "11. Data Protection. Each party shall comply with all applicable data protection laws including GDPR and CCPA. The Provider shall implement appropriate technical and organizational measures to protect personal data against unauthorized access or disclosure.",
    "12. Audit Rights. The Customer shall have the right, upon reasonable notice and during normal business hours, to audit the Provider's facilities, systems, and records to verify compliance with this Agreement.",
    "13. Force Majeure. Neither party shall be liable for any failure or delay in performing its obligations if caused by circumstances beyond its reasonable control, including acts of God, natural disasters, war, terrorism, pandemics, or infrastructure failures.",
    "14. Governing Law. This Agreement shall be governed by and construed in accordance with the laws of the State of Delaware. Any dispute shall first be submitted to mediation administered by JAMS, and if mediation fails, resolved by binding arbitration.",
    "15. Assignment. Neither party may assign this Agreement without the prior written consent of the other party. Any attempted assignment in violation of this Section shall be void.",
    "16. Notices. All notices shall be in writing and shall be deemed given when: (a) delivered personally; (b) sent by confirmed email; (c) sent by overnight courier; or (d) deposited in the mail, postage prepaid, certified mail.",
    "17. Entire Agreement. This Agreement, together with all exhibits and schedules, constitutes the entire agreement between the parties and supersedes all prior agreements, understandings, negotiations, and discussions.",
    "18. Amendments. This Agreement may not be amended except by a written instrument signed by authorized representatives of both parties.",
    "19. Severability. If any provision is held to be invalid or unenforceable, such provision shall be deemed modified to the minimum extent necessary to make it enforceable.",
    "20. Waiver. The failure of either party to enforce any provision shall not be construed as a waiver of such provision or the right to enforce such provision thereafter.",
    "21. Independent Contractor. The Provider is an independent contractor and nothing in this Agreement shall create a partnership, joint venture, agency, or employment relationship.",
    "22. Export Compliance. Each party agrees to comply with all applicable export control laws and regulations, including the U.S. Export Administration Regulations.",
    "23. Anti-Corruption. Each party represents that it has not and shall not pay any money or anything of value to any government official for the purpose of influencing any act or decision.",
    "24. Subcontracting. The Provider may subcontract any of its obligations to qualified third parties, provided that the Provider shall remain fully responsible for the performance of all subcontractors.",
    "25. Records Retention. Each party shall maintain complete and accurate records relating to the performance of this Agreement for a period of at least three (3) years following termination.",
    "26. Publicity. Neither party shall issue any press release or make any public announcement regarding this Agreement without the prior written consent of the other party.",
    "27. Third-Party Beneficiaries. This Agreement is for the sole benefit of the parties hereto and their permitted assigns and nothing herein shall confer upon any other person any legal or equitable right.",
    "28. Counterparts. This Agreement may be executed in one or more counterparts, each of which shall be deemed an original, and all of which together shall constitute one and the same instrument.",
    "29. Survival. The provisions of Sections 5 (Confidentiality), 6 (Intellectual Property), 8 (Limitation of Liability), 9 (Indemnification), 11 (Data Protection), 14 (Governing Law), and this Section 29 shall survive termination.",
    "30. Signatures. IN WITNESS WHEREOF, the parties have executed this Agreement by their duly authorized representatives as of the Effective Date.",
]


def generate_contract_page(page_num: int, total_pages: int) -> str:
    lines = [f"Page {page_num} of {total_pages}", "=" * 60, ""]
    if page_num == 1:
        lines.append("MASTER SERVICES AGREEMENT")
        lines.append("")
        lines.append("This Agreement is entered into as of the Effective Date by and between")
        lines.append("ContractEdge Technologies, Inc. ('Provider') and [Customer Name] ('Customer').")
        lines.append("")
        lines.append("WHEREAS, Provider offers contract risk analysis and management services; and")
        lines.append("WHEREAS, Customer desires to subscribe to such services.")
        lines.append("NOW, THEREFORE, the parties agree as follows:")
    elif page_num == total_pages:
        lines.append("IN WITNESS WHEREOF, the parties have executed this Agreement.")
        lines.append("")
        lines.append("PROVIDER:                         CUSTOMER:")
        lines.append("By: ____________________          By: ____________________")
        lines.append("")
        lines.append("[End of Agreement]")
    else:
        idx = ((page_num - 2) * 2) % len(LEGAL_CLAUSES)
        for i in range(2):
            c = LEGAL_CLAUSES[(idx + i) % len(LEGAL_CLAUSES)]
            lines.append(c)
            lines.append("")
        lines.append("The parties agree to the foregoing terms and conditions.")
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
    style = ParagraphStyle("Contract", parent=styles["Normal"],
                           fontSize=9, leading=12, spaceAfter=6)
    story = []
    for pn in range(1, page_count + 1):
        for line in generate_contract_page(pn, page_count).split("\n"):
            if line.strip():
                story.append(Paragraph(
                    line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), style))
            else:
                story.append(Spacer(1, 6))
        if pn < page_count:
            story.append(PageBreak())
    doc.build(story)
    return output_path


# ── Benchmark Data Model ─────────────────────────────────────────

@dataclass
class BenchmarkResult:
    pages: int
    file_size_bytes: int = 0
    file_size_mb: float = 0.0
    extract_duration_ms: float = 0.0
    chunk_duration_ms: float = 0.0
    chunk_count: int = 0
    tokens_consumed: int = 0
    memory_delta_mb: float = 0.0
    estimated_embedding_ms: float = 0.0
    estimated_ai_analysis_ms: float = 0.0
    estimated_total_ms: float = 0.0
    errors: list[str] = field(default_factory=list)

    @property
    def estimated_db_rows(self) -> int:
        return self.chunk_count

    @property
    def estimated_storage_bytes(self) -> int:
        return self.chunk_count * (500 * 2 + 1536 * 4)


# ── Benchmark Runner ─────────────────────────────────────────────

class Benchmark:
    PDF_DIR = Path("/tmp/contract_benchmark/pdfs")

    def __init__(self, page_sizes: list[int]):
        self.page_sizes = sorted(page_sizes)
        self.results: list[BenchmarkResult] = []
        self.PDF_DIR.mkdir(parents=True, exist_ok=True)

    def generate_pdfs(self) -> dict[int, str]:
        paths = {}
        for p in self.page_sizes:
            path = str(self.PDF_DIR / f"contract_{p}p.pdf")
            if not os.path.exists(path):
                logger.info(f"Generating {p}-page PDF...")
                t0 = time.time()
                generate_contract_pdf(p, path)
                logger.info(f"  Done ({time.time()-t0:.1f}s, {os.path.getsize(path):,} bytes)")
            paths[p] = path
        return paths

    def run_single(self, pages: int, pdf_path: str) -> BenchmarkResult:
        r = BenchmarkResult(pages=pages)
        r.file_size_bytes = os.path.getsize(pdf_path)
        r.file_size_mb = round(r.file_size_bytes / (1024 * 1024), 2)

        logger.info(f"\n{'='*60}")
        logger.info(f"Benchmark: {pages}-page ({r.file_size_mb} MB)")
        logger.info(f"{'='*60}")

        with open(pdf_path, "rb") as f:
            file_data = f.read()

        import psutil
        proc = psutil.Process(os.getpid())
        mem_before = proc.memory_info().rss

        # ── Extract ──
        logger.info("  [1/4] Extracting text...")
        t0 = time.time()
        try:
            import fitz
            doc = fitz.open(stream=file_data, filetype="pdf")
            pages_text = []
            for i in range(len(doc)):
                pages_text.append({"page_number": i + 1, "text": doc[i].get_text()})
            doc.close()
            r.extract_duration_ms = round((time.time() - t0) * 1000, 1)
            logger.info(f"         {r.extract_duration_ms:.0f}ms ({len(pages_text)} pages)")
        except Exception as e:
            r.errors.append(f"Extraction: {e}")
            logger.error(f"         FAILED: {e}")
            return r

        # ── Chunk ──
        logger.info("  [2/4] Chunking...")
        t0 = time.time()
        try:
            from app.domains.vectors.chunking import chunking_service
            chunks = chunking_service.chunk_pages(pages_text, strategy="semantic")
            r.chunk_duration_ms = round((time.time() - t0) * 1000, 1)
            r.chunk_count = len(chunks)
            r.tokens_consumed = sum(c.token_count for c in chunks)
            logger.info(f"         {r.chunk_duration_ms:.0f}ms -> {r.chunk_count} chunks, {r.tokens_consumed:,} tokens")
        except Exception as e:
            r.errors.append(f"Chunking: {e}")
            logger.error(f"         FAILED: {e}")
            return r

        # ── Estimate embedding cost ──
        EMBED_MS_PER_CHUNK = 50
        r.estimated_embedding_ms = r.chunk_count * EMBED_MS_PER_CHUNK
        batches = max(1, r.chunk_count // 20)
        logger.info(f"  [3/4] Embedding (est): {r.estimated_embedding_ms:.0f}ms ({batches} batches)")

        # ── Estimate AI analysis cost ──
        AI_MS_PER_BATCH = 2000
        ai_batches = max(1, r.chunk_count // 5)
        r.estimated_ai_analysis_ms = ai_batches * AI_MS_PER_BATCH
        logger.info(f"  [4/4] AI analysis (est): {r.estimated_ai_analysis_ms:.0f}ms ({ai_batches} batches)")

        r.estimated_total_ms = r.extract_duration_ms + r.chunk_duration_ms + \
            r.estimated_embedding_ms + r.estimated_ai_analysis_ms

        mem_after = proc.memory_info().rss
        r.memory_delta_mb = round((mem_after - mem_before) / (1024 * 1024), 2)
        logger.info(f"  Memory: +{r.memory_delta_mb} MB")
        logger.info(f"  Est. total: {r.estimated_total_ms:.0f}ms ({r.estimated_total_ms/1000:.1f}s)")

        return r

    def run_all(self) -> list[BenchmarkResult]:
        pdfs = self.generate_pdfs()
        for pages in self.page_sizes:
            r = self.run_single(pages, pdfs[pages])
            self.results.append(r)
            time.sleep(0.5)
        return self.results


# ── Report ───────────────────────────────────────────────────────

def generate_report(results: list[BenchmarkResult]) -> str:
    lines = []
    lines.append("=" * 100)
    lines.append("SPRINT 25 TASK 3.3 - LARGE CONTRACT VALIDATION BENCHMARK")
    lines.append(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"))
    lines.append("=" * 100)
    lines.append("")

    lines.append("-" * 100)
    lines.append("PERFORMANCE TABLE")
    lines.append("-" * 100)
    hdr = (f"{'Pages':>6} | {'Size':>8} | {'Extract':>10} | {'Chunk':>10} | "
           f"{'Chunks':>7} | {'Tokens':>8} | {'Embed(est)':>10} | {'AI(est)':>10} | "
           f"{'Total(est)':>10} | {'Mem D':>8}")
    lines.append(hdr)
    lines.append("-" * 100)
    for r in results:
        lines.append(
            f"{r.pages:>6} | {r.file_size_mb:>7.2f}MB | {r.extract_duration_ms:>8.0f}ms | "
            f"{r.chunk_duration_ms:>8.0f}ms | {r.chunk_count:>7} | {r.tokens_consumed:>8,} | "
            f"{r.estimated_embedding_ms:>8.0f}ms | {r.estimated_ai_analysis_ms:>8.0f}ms | "
            f"{r.estimated_total_ms:>8.0f}ms | {r.memory_delta_mb:>+7.1f}MB"
        )
    lines.append("")

    for r in results:
        lines.append(f"-- {r.pages}-page Contract --")
        lines.append(f"  File size:           {r.file_size_mb} MB ({r.file_size_bytes:,} bytes)")
        lines.append(f"  Text extraction:     {r.extract_duration_ms:.0f} ms")
        lines.append(f"  Chunking:            {r.chunk_duration_ms:.0f} ms")
        lines.append(f"  Chunk count:         {r.chunk_count}")
        lines.append(f"  Tokens consumed:     {r.tokens_consumed:,}")
        lines.append(f"  Est. embedding:      {r.estimated_embedding_ms:.0f} ms")
        lines.append(f"  Est. AI analysis:    {r.estimated_ai_analysis_ms:.0f} ms")
        lines.append(f"  Est. total pipeline: {r.estimated_total_ms:.0f} ms ({r.estimated_total_ms/1000:.1f}s)")
        lines.append(f"  Est. DB rows:        {r.estimated_db_rows} (chunks)")
        lines.append(f"  Est. storage:        {r.estimated_storage_bytes:,} bytes ({r.estimated_storage_bytes/1024/1024:.1f} MB)")
        lines.append(f"  Memory delta:        {r.memory_delta_mb:+.1f} MB")
        if r.errors:
            lines.append(f"  Errors:             {len(r.errors)}")
            for e in r.errors:
                lines.append(f"    - {e}")
        lines.append("")

    lines.append("-" * 100)
    lines.append("FAILURE POINTS")
    lines.append("-" * 100)
    all_errors = [(r.pages, e) for r in results if r.errors]
    if all_errors:
        for p, e in all_errors:
            lines.append(f"  [{p}p] {e}")
    else:
        lines.append("  None - all sizes processed successfully.")
    lines.append("")

    lines.append("-" * 100)
    lines.append("MAXIMUM SAFE DOCUMENT SIZE")
    lines.append("-" * 100)
    max_ok = max((r.pages for r in results if not r.errors), default=0)
    bottleneck = "None identified"
    for r in sorted(results, key=lambda x: x.pages):
        if r.errors:
            bottleneck = r.errors[0]
            break
    lines.append(f"  Maximum tested OK:  {max_ok} pages")
    lines.append(f"  Bottleneck:         {bottleneck}")
    lines.append("")

    lines.append("-" * 100)
    lines.append("RECOMMENDED PRODUCTION LIMITS")
    lines.append("-" * 100)
    lines.append("")
    max_chunks = max(r.chunk_count for r in results) if results else 0
    max_extract = max(r.extract_duration_ms for r in results) if results else 0
    max_mem = max(r.memory_delta_mb for r in results) if results else 0
    max_pages = max(r.pages for r in results) if results else 500
    lines.append(f"  {'Metric':<40} {'Recommended Limit':<30}")
    lines.append(f"  {'------':<40} {'-----------------':<30}")
    lines.append(f"  {'Maximum pages':<40} {max_pages}+ pages")
    lines.append(f"  {'Maximum file size':<40} 100 MB (hard config limit)")
    lines.append(f"  {'Maximum chunks per document':<40} {max_chunks}")
    lines.append(f"  {'Expected extract time (per 100p)':<40} {max_extract/max(1,max_pages/100):.0f} ms")
    lines.append(f"  {'Expected memory per 100 pages':<40} {max_mem/max(1,max_pages/100):.1f} MB")
    lines.append(f"  {'Max concurrent large docs (>250p)':<40} 3")
    lines.append(f"  {'Embedding batch size':<40} 20 chunks")
    lines.append(f"  {'AI analysis timeout':<40} 300s (5 min)")
    lines.append(f"  {'Chunk size (tokens)':<40} 800 (default)")
    lines.append(f"  {'Chunk overlap (tokens)':<40} 120 (default)")
    lines.append("")

    lines.append("-" * 100)
    lines.append("SUMMARY")
    lines.append("-" * 100)
    passed = sum(1 for r in results if not r.errors)
    lines.append(f"  Sizes tested:      {len(results)}")
    lines.append(f"  Passed:            {passed}")
    lines.append(f"  Failed:            {len(results) - passed}")
    lines.append(f"  Max pages tested:  {max_pages}")
    lines.append(f"  Max chunks:        {max_chunks:,}")
    lines.append(f"  Max extract time:  {max_extract:.0f} ms")
    lines.append(f"  Max memory delta:  {max_mem:+.0f} MB")
    lines.append(f"  Est. max pipeline: {max(r.estimated_total_ms for r in results)/1000:.1f}s")
    lines.append("")
    lines.append("=" * 100)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", nargs="+", type=int, default=[50, 100, 250, 500])
    parser.add_argument("--output", default="/tmp/contract_benchmark/report.txt")
    args = parser.parse_args()

    bench = Benchmark(args.pages)
    results = bench.run_all()

    report = generate_report(results)
    print("\n" + report)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        f.write(report)

    json_path = args.output.replace(".txt", ".json")
    with open(json_path, "w") as f:
        json.dump([{
            "pages": r.pages, "file_size_mb": r.file_size_mb,
            "extract_duration_ms": r.extract_duration_ms,
            "chunk_duration_ms": r.chunk_duration_ms,
            "chunk_count": r.chunk_count, "tokens_consumed": r.tokens_consumed,
            "estimated_embedding_ms": r.estimated_embedding_ms,
            "estimated_ai_analysis_ms": r.estimated_ai_analysis_ms,
            "estimated_total_ms": r.estimated_total_ms,
            "memory_delta_mb": r.memory_delta_mb, "errors": r.errors,
        } for r in results], f, indent=2)

    logger.info(f"Report: {args.output}")
    logger.info(f"JSON:   {json_path}")


if __name__ == "__main__":
    main()
