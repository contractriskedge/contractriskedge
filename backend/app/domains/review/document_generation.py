"""Document generation service — creates real .docx artifacts from accepted redlines.

Uses python-docx to:
1. Download the original uploaded document from MinIO/S3
2. Apply accepted redline replacements (clause text substitution)
3. Generate a new .docx with change tracking summary
4. Upload the generated document back to MinIO/S3
5. Record the version with storage_key and checksum

This bridges the gap between "redlines accepted as metadata" and
"actual regenerated contract artifact."
"""

from __future__ import annotations

import hashlib
import io
import logging
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from docx import Document as DocxDocument
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from app.config import settings
from app.integrations.storage.s3 import storage_service
from app.domains.review.models import ReviewRedline, ContractDocumentVersion
from app.domains.review.redline_ops import (
    RedlineOperation,
    infer_operation,
    resolve_apply_texts,
)

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────

STORAGE_BUCKET = settings.s3_bucket
VERSION_STORAGE_PREFIX = "contracts/{review_id}/versions"


@dataclass
class DocumentGenerationResult:
    """Result of a document generation operation."""
    version_id: str
    version_number: int
    storage_key: str
    file_size_bytes: int
    checksum_sha256: str
    change_summary: str


async def generate_version_from_redlines(
    session,
    review_id: str,
    tenant_id: str,
    user_id: str,
    source_upload_id: str,
    original_storage_key: str,
    accepted_redlines: list,
    label: str = "AI Redlines Applied",
    version_number: Optional[int] = None,
) -> Optional[DocumentGenerationResult]:
    """Generate a new document version by applying accepted redlines.

    Steps:
    1. Download the original document from storage
    2. Parse with python-docx
    3. Apply each accepted redline's proposed_text as clause replacement
    4. Add a change summary appendix
    5. Upload the generated document to storage
    6. Return the result for version record creation
    """
    try:
        # Step 1: Download original document
        logger.info(
            "Generating document version for review=%s from key=%s",
            review_id, original_storage_key,
        )
        original_bytes = await storage_service.download_fileobj(
            STORAGE_BUCKET, original_storage_key,
        )

        # Step 2: Parse with python-docx
        doc = DocxDocument(io.BytesIO(original_bytes))

        # Step 2a: Collect all paragraphs once for position tracking
        all_paragraphs = _collect_all_paragraphs(doc)

        # Step 3: Apply accepted redlines (operation-aware, in document order)
        # First, build a list with position hints, then sort by paragraph position
        # so that replacements happen bottom-up (preserving paragraph indices).
        redline_tasks = []
        for redline in accepted_redlines:
            clause_type = redline.get("clause_type", "unknown")
            redline_id = redline.get("redline_id", "")
            operation = infer_operation(
                redline.get("original_text", ""),
                redline.get("proposed_text", ""),
                clause_type=clause_type,
                stored_operation=redline.get("operation"),
            )
            original_text, proposed_text, anchor_text = resolve_apply_texts(
                operation,
                redline.get("original_text", ""),
                redline.get("proposed_text", ""),
                anchor_text=redline.get("anchor_text", ""),
            )

            if operation == RedlineOperation.DELETE and not original_text:
                continue
            if operation != RedlineOperation.DELETE and not proposed_text:
                continue

            # Estimate paragraph position from redline_metadata if available
            metadata = redline.get("redline_metadata", {}) or {}
            para_pos = None
            if isinstance(metadata, dict):
                para_pos = metadata.get("paragraph_position")
            if para_pos is None:
                # Try to locate by matching text
                old_norm = _normalize_text(original_text)
                for i, p in enumerate(all_paragraphs):
                    if old_norm and old_norm in _normalize_text(p.text):
                        para_pos = i
                        break

            redline_tasks.append({
                "redline": redline,
                "operation": operation,
                "original_text": original_text,
                "proposed_text": proposed_text,
                "anchor_text": anchor_text,
                "clause_type": clause_type,
                "redline_id": redline_id,
                "para_pos": para_pos if para_pos is not None else 999999,
            })

        # Sort by paragraph position descending (bottom-up) to preserve indices
        redline_tasks.sort(key=lambda t: t["para_pos"], reverse=True)

        changes_made = []
        for task in redline_tasks:
            operation = task["operation"]
            original_text = task["original_text"]
            proposed_text = task["proposed_text"]
            anchor_text = task["anchor_text"]
            clause_type = task["clause_type"]
            redline_id = task["redline_id"]

            applied = False
            apply_status = "appended"

            if operation == RedlineOperation.INSERT:
                applied = _insert_clause_in_document(doc, proposed_text, anchor_text, _all_paragraphs=all_paragraphs)
                apply_status = "inserted" if applied else "appended"
            elif operation == RedlineOperation.DELETE:
                applied = _replace_text_in_document(doc, original_text, "", _all_paragraphs=all_paragraphs)
                apply_status = "deleted" if applied else "appended"
            else:
                if original_text and len(original_text) <= 400:
                    applied = _replace_text_in_document(doc, original_text, proposed_text, _all_paragraphs=all_paragraphs)
                    apply_status = "replaced" if applied else "appended"
                else:
                    applied = _insert_clause_in_document(doc, proposed_text, anchor_text, _all_paragraphs=all_paragraphs)
                    apply_status = "inserted" if applied else "appended"

            changes_made.append({
                "clause_type": clause_type,
                "redline_id": str(redline_id)[:8],
                "status": apply_status,
                "operation": operation.value,
            })
            logger.info(
                "Redline %s (%s) for %s: %s",
                str(redline_id)[:8], operation.value, clause_type, apply_status,
            )

        # Step 4: Add change summary appendix
        _add_change_summary(doc, changes_made, accepted_redlines)

        # Step 5: Generate the document bytes
        output = io.BytesIO()
        doc.save(output)
        generated_bytes = output.getvalue()

        # Compute checksum
        checksum = hashlib.sha256(generated_bytes).hexdigest()

        # Step 6: Determine version number
        from sqlalchemy import select, func
        result = await session.execute(
            select(func.max(ContractDocumentVersion.version_number)).where(
                ContractDocumentVersion.review_id == review_id,
                ContractDocumentVersion.tenant_id == tenant_id,
            )
        )
        max_version = result.scalar() or 0
        next_version = version_number if version_number is not None else (max_version + 1)

        # Step 7: Upload to storage
        storage_key = f"{VERSION_STORAGE_PREFIX.format(review_id=review_id)}/v{next_version}.docx"
        await storage_service.upload_fileobj(
            bucket=STORAGE_BUCKET,
            key=storage_key,
            file_body=generated_bytes,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            metadata={
                "review_id": str(review_id),
                "version": str(next_version),
                "generated_at": datetime.utcnow().isoformat(),
                "checksum_sha256": checksum,
            },
        )

        # Build change summary
        applied = sum(1 for c in changes_made if c["status"] in ("replaced", "inserted", "deleted"))
        appended = sum(1 for c in changes_made if c["status"] == "appended")
        change_summary = (
            f"Applied {applied} redline(s) to document text"
            + (f", {appended} change(s) appended as notes" if appended else "")
        )

        logger.info(
            "Document version v%d generated: key=%s size=%d checksum=%s",
            next_version, storage_key, len(generated_bytes), checksum[:16],
        )

        return DocumentGenerationResult(
            version_id=str(uuid.uuid4()),
            version_number=next_version,
            storage_key=storage_key,
            file_size_bytes=len(generated_bytes),
            checksum_sha256=checksum,
            change_summary=change_summary,
        )

    except Exception as exc:
        logger.error(
            "Document generation failed for review=%s: %s",
            review_id, exc, exc_info=True,
        )
        return None


def _insert_clause_in_document(
    doc: DocxDocument,
    new_text: str,
    anchor_text: str = "",
    *,
    _all_paragraphs: Optional[list] = None,
) -> bool:
    """Insert a new clause after an anchor phrase without deleting surrounding text."""
    from docx.text.paragraph import Paragraph

    all_paragraphs = _all_paragraphs if _all_paragraphs is not None else _collect_all_paragraphs(doc)

    anchor_norm = _normalize_text(anchor_text) if anchor_text else ""

    if anchor_norm:
        for paragraph in all_paragraphs:
            para_norm = _normalize_text(paragraph.text)
            if anchor_norm in para_norm or anchor_text in paragraph.text:
                _insert_paragraph_after(paragraph, new_text)
                return True

    # No anchor: append before change summary / at document end
    if all_paragraphs:
        _insert_paragraph_after(all_paragraphs[-1], new_text)
        return True

    p = doc.add_paragraph()
    run = p.add_run(new_text)
    run.font.color.rgb = RGBColor(0x00, 0x80, 0x00)
    run.font.bold = True
    return True


def _insert_paragraph_after(paragraph, text: str) -> Paragraph:
    """Insert a new paragraph immediately after the given one."""
    from docx.oxml import OxmlElement
    from docx.text.paragraph import Paragraph

    new_p = OxmlElement("w:p")
    paragraph._p.addnext(new_p)
    new_para = Paragraph(new_p, paragraph._parent)
    run = new_para.add_run(text)
    run.font.color.rgb = RGBColor(0x00, 0x80, 0x00)
    run.font.bold = True
    return new_para


def _find_paragraph_position(
    paragraph,
    all_paragraphs: list,
) -> int:
    """Return the 0-based index of a paragraph in the flat list."""
    try:
        return all_paragraphs.index(paragraph)
    except ValueError:
        return -1


def _collect_all_paragraphs(doc: DocxDocument) -> list:
    """Collect all paragraphs from body and tables into a flat list."""
    all_paragraphs = list(doc.paragraphs)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                all_paragraphs.extend(cell.paragraphs)
    return all_paragraphs


def _replace_text_in_document(
    doc: DocxDocument,
    old_text: str,
    new_text: str,
    *,
    _all_paragraphs: Optional[list] = None,
) -> bool:
    """Replace text in a python-docx document using smart paragraph matching.

    Strategy (in order of precision):
    1. Exact paragraph match — finds the paragraph containing old_text
    2. Fuzzy paragraph match — normalizes whitespace and tries again
    3. Clause boundary match — matches on first 80 chars if longer text

    Includes scope validation to prevent replacing more than intended
    (e.g., matching a heading + full clause when only the clause body was targeted).

    Returns True if at least one replacement was made.
    """
    # Normalize both texts for comparison
    old_normalized = _normalize_text(old_text)
    new_normalized = _normalize_text(new_text)

    if not old_normalized:
        return False

    # Collect all paragraphs (body + tables)
    all_paragraphs = _all_paragraphs or _collect_all_paragraphs(doc)

    replaced = False

    for paragraph in all_paragraphs:
        para_text = paragraph.text
        para_normalized = _normalize_text(para_text)

        if not para_normalized:
            continue

        # Scope validation: if the matched paragraph is MUCH larger than old_text,
        # it means we're about to replace a huge section. Skip unless it's a
        # reasonable scope match.
        para_word_count = len(para_normalized.split())
        old_word_count = len(old_normalized.split())

        # If paragraph is > 3x the size of old_text, this is likely a heading +
        # full clause match, not the intended scope. Skip this paragraph.
        if para_word_count > old_word_count * 3 and old_word_count > 5:
            # Try to find a sentence-level match within the paragraph instead
            # by checking if old_text appears as a contiguous substring
            if old_normalized not in para_normalized:
                continue

        # Strategy 1: Exact match
        if old_text in para_text:
            _replace_in_paragraph(paragraph, old_text, new_text)
            replaced = True
            continue

        # Strategy 2: Normalized match
        if old_normalized in para_normalized:
            # Find the actual text range in the original paragraph
            idx = para_normalized.index(old_normalized)
            # Map back to original — find the substring
            actual_old = _find_original_substring(para_text, old_normalized)
            if actual_old:
                _replace_in_paragraph(paragraph, actual_old, new_text)
                replaced = True
                continue

        # Strategy 3: First 80 chars match (for long clause texts)
        # Only use this if the paragraph isn't massively larger than old_text
        if len(old_normalized) > 80 and para_word_count <= old_word_count * 3:
            prefix = old_normalized[:80]
            if prefix in para_normalized:
                actual_old = _find_original_substring(para_text, old_normalized)
                if actual_old and len(actual_old) > 80:
                    _replace_in_paragraph(paragraph, actual_old, new_text)
                    replaced = True
                    continue

    return replaced


def _normalize_text(text: str) -> str:
    """Normalize whitespace for comparison: collapse multiple spaces, trim."""
    if not text:
        return ""
    return ' '.join(text.split())


def _find_original_substring(para_text: str, normalized_target: str) -> str | None:
    """Find the actual substring in para_text that corresponds to normalized_target.

    Handles whitespace differences between the AI-extracted text and the actual
    document text by doing a character-by-character fuzzy scan.
    """
    if not normalized_target:
        return None

    target_words = normalized_target.split()
    para_words = para_text.split()

    if len(target_words) > len(para_words):
        return None

    # Sliding window over para_words looking for target_words match
    for start in range(len(para_words) - len(target_words) + 1):
        match = True
        for i, tw in enumerate(target_words):
            if _words_match(para_words[start + i], tw):
                continue
            match = False
            break

        if match:
            # Found it — reconstruct the actual text from the paragraph
            matched_para_words = para_words[start:start + len(target_words)]
            return ' '.join(matched_para_words)

    return None


def _words_match(a: str, b: str) -> bool:
    """Check if two words match with tolerance for minor differences."""
    # Direct match
    if a == b:
        return True
    # Case-insensitive
    if a.lower() == b.lower():
        return True
    # One contains the other (handles punctuation differences)
    if len(a) > 3 and len(b) > 3:
        if a.lower().startswith(b.lower()) or b.lower().startswith(a.lower()):
            return True
    return False


def _apply_table_style(table, doc: DocxDocument) -> None:
    """Apply a table style if available (Office theme styles are often missing in minimal docs)."""
    for style_name in ("Table Grid", "Light Grid", "Table Normal", "Normal Table"):
        try:
            table.style = style_name
            return
        except KeyError:
            continue
    try:
        table.style = doc.styles["Table Grid"]
    except KeyError:
        pass  # Unstyled table is still valid


def _replace_in_paragraph(paragraph, old_text: str, new_text: str) -> None:
    """Replace text within a single paragraph with visual change indicators.

    Uses a three-run approach:
    1. [strikethrough red] original text (shows what was removed)
    2. " → " separator
    3. [green] replacement text (shows what was added)

    This creates a visible diff within the document itself.
    """
    if not paragraph.runs:
        paragraph.clear()
        run = paragraph.add_run(new_text)
        return

    full_text = paragraph.text
    if old_text not in full_text:
        return

    # Split the paragraph into three segments: before, target, after
    idx = full_text.index(old_text)
    before_text = full_text[:idx]
    after_text = full_text[idx + len(old_text):]

    # Clear existing runs
    for run in paragraph.runs:
        run.text = ""

    # Rebuild with change indicators
    runs = paragraph.runs
    run_idx = 0

    # Part 1: Text before the change (preserve original formatting)
    if before_text:
        if run_idx < len(runs):
            runs[run_idx].text = before_text
            run_idx += 1
        else:
            runs[0].text = before_text + runs[0].text
            # Don't increment — we merged into first run

    # Part 2: Original text with strikethrough (red)
    if run_idx < len(runs):
        strike_run = runs[run_idx]
        strike_run.text = old_text
        strike_run.font.strike = True
        strike_run.font.color.rgb = RGBColor(0xCC, 0x00, 0x00)
        run_idx += 1
    else:
        strike_run = paragraph.add_run(old_text)
        strike_run.font.strike = True
        strike_run.font.color.rgb = RGBColor(0xCC, 0x00, 0x00)

    # Part 2.5: Separator
    if run_idx < len(runs):
        sep_run = runs[run_idx]
        sep_run.text = " → "
        run_idx += 1
    else:
        paragraph.add_run(" → ")

    # Part 3: Replacement text (green)
    if run_idx < len(runs):
        new_run = runs[run_idx]
        new_run.text = new_text
        new_run.font.color.rgb = RGBColor(0x00, 0x80, 0x00)
        new_run.font.bold = True
        run_idx += 1
    else:
        new_run = paragraph.add_run(new_text)
        new_run.font.color.rgb = RGBColor(0x00, 0x80, 0x00)
        new_run.font.bold = True

    # Part 4: Text after the change
    if after_text:
        if run_idx < len(runs):
            runs[run_idx].text = after_text
        else:
            paragraph.add_run(after_text)


def _add_change_summary(doc: DocxDocument, changes: list[dict], redlines: list) -> None:
    """Add a change summary appendix at the end of the document."""
    # Add page break before appendix
    doc.add_page_break()

    # Appendix title
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = title.add_run("Change Summary — AI-Generated Redlines Applied")
    run.bold = True
    run.font.size = Pt(14)
    run.font.color.rgb = RGBColor(0x1A, 0x1A, 0x2E)

    # Generation metadata
    meta = doc.add_paragraph()
    meta_run = meta.add_run(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    meta_run.font.size = Pt(9)
    meta_run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

    doc.add_paragraph()  # spacer

    # Changes table
    table = doc.add_table(rows=1, cols=3)
    _apply_table_style(table, doc)

    # Header row
    hdr = table.rows[0].cells
    hdr[0].text = "Clause Type"
    hdr[1].text = "Status"
    hdr[2].text = "Change Description"

    for change in changes:
        row_cells = table.add_row().cells
        row_cells[0].text = change["clause_type"].replace("_", " ").title()
        row_cells[1].text = change["status"].title()

        # Find the matching redline for description
        matching = [r for r in redlines if str(r.get("redline_id", ""))[:8] == change["redline_id"]]
        if matching:
            desc = matching[0].get("rationale", "") or ""
            row_cells[2].text = desc[:200]
        else:
            row_cells[2].text = ""

    # Add original redlines as appendix entries for those not found in text
    appended = [c for c in changes if c["status"] == "appended"]
    if appended:
        doc.add_paragraph()
        appendix_title = doc.add_paragraph()
        run = appendix_title.add_run("Proposed Changes (Could Not Auto-Apply)")
        run.bold = True
        run.font.size = Pt(11)

        for change in appended:
            matching = [r for r in redlines if str(r.get("redline_id", ""))[:8] == change["redline_id"]]
            if matching:
                r = matching[0]
                p = doc.add_paragraph()
                try:
                    p.style = doc.styles["Normal"]
                except KeyError:
                    pass
                run_label = p.add_run(f"\nClause: {change['clause_type'].replace('_', ' ').title()}")
                run_label.bold = True

                p_orig = doc.add_paragraph()
                run_orig_label = p_orig.add_run("Original: ")
                run_orig_label.bold = True
                p_orig.add_run(r.get("original_text", "")[:500])

                p_prop = doc.add_paragraph()
                run_prop_label = p_prop.add_run("Proposed: ")
                run_prop_label.bold = True
                p_prop.add_run(r.get("proposed_text", "")[:500])


def generate_tracked_changes_docx(original_bytes: bytes, redlines: list[dict]) -> bytes:
    """Generate a tracked-changes DOCX with python-docx visual markup.

    Uses red strikethrough for deleted text and green underline for inserted text,
    mimicking Microsoft Word's Track Changes visual style.
    """
    doc = DocxDocument(io.BytesIO(original_bytes))

    for redline in redlines:
        original_text = redline.get("original_text", "")
        proposed_text = redline.get("proposed_text", "")
        if not original_text or not proposed_text:
            continue

        # Find and mark the paragraph
        for paragraph in doc.paragraphs:
            if original_text in paragraph.text:
                _apply_tracked_changes(paragraph, original_text, proposed_text)
                break

    output = io.BytesIO()
    doc.save(output)
    return output.getvalue()


def _apply_tracked_changes(paragraph, old_text: str, new_text: str) -> None:
    """Apply tracked-changes style markup to a paragraph.

    Shows original in red strikethrough followed by replacement in green underline.
    """
    if not paragraph.runs:
        return

    full_text = paragraph.text
    if old_text not in full_text:
        return

    idx = full_text.index(old_text)
    before_text = full_text[:idx]
    after_text = full_text[idx + len(old_text):]

    # Clear existing runs
    for run in paragraph.runs:
        run.text = ""

    runs = paragraph.runs
    run_idx = 0

    # Before
    if before_text and run_idx < len(runs):
        runs[run_idx].text = before_text
        run_idx += 1

    # Deleted original (red strikethrough)
    if run_idx < len(runs):
        d_run = runs[run_idx]
        d_run.text = old_text
        d_run.font.strike = True
        d_run.font.color.rgb = RGBColor(0xCC, 0x00, 0x00)
        run_idx += 1
    else:
        d_run = paragraph.add_run(old_text)
        d_run.font.strike = True
        d_run.font.color.rgb = RGBColor(0xCC, 0x00, 0x00)

    # Inserted new (green underline)
    if run_idx < len(runs):
        i_run = runs[run_idx]
        i_run.text = new_text
        i_run.font.underline = True
        i_run.font.color.rgb = RGBColor(0x00, 0x80, 0x00)
        run_idx += 1
    else:
        i_run = paragraph.add_run(new_text)
        i_run.font.underline = True
        i_run.font.color.rgb = RGBColor(0x00, 0x80, 0x00)

    # After
    if after_text and run_idx < len(runs):
        runs[run_idx].text = after_text
    elif after_text:
        paragraph.add_run(after_text)


# ── Finalized Document Generation ────────────────────────────────


async def generate_finalized_document(
    session: AsyncSession,
    review_id: str,
    tenant_id: str,
    user_id: str,
    original_storage_key: str,
    redlines: list,
    approval_metadata: dict[str, Any],
) -> bytes:
    """Generate the FINAL approved contract document.

    Steps:
    1. Download the original document from storage
    2. Apply all accepted/modified redlines
    3. Add approval signature block at the end
    4. Add "FINAL APPROVED CONTRACT" watermark/header
    5. Return the bytes of the generated .docx

    This document is immutable — once generated, it should never be modified.
    """
    from sqlalchemy.ext.asyncio import AsyncSession

    bucket = settings.s3_bucket or "contractrisk-documents"
    original_bytes = await storage_service.download_fileobj(bucket, original_storage_key)

    doc = DocxDocument(io.BytesIO(original_bytes))

    # Step 1: Apply all accepted/modified redlines
    applied_count = 0
    for redline in redlines:
        original_text = redline.original_text if hasattr(redline, 'original_text') else redline.get("original_text", "")
        proposed_text = (
            (redline.reviewer_modified_text if hasattr(redline, 'reviewer_modified_text') else redline.get("reviewer_modified_text"))
            or (redline.proposed_text if hasattr(redline, 'proposed_text') else redline.get("proposed_text", ""))
        )
        if not original_text or not proposed_text:
            continue

        for paragraph in doc.paragraphs:
            if original_text in paragraph.text:
                _apply_final_replacement(paragraph, original_text, proposed_text)
                applied_count += 1
                break

    # Step 2: Add approval signature block
    doc.add_page_break()
    _add_approval_signature_block(doc, approval_metadata)

    # Step 3: Add header/footer marking
    _add_finalized_header_footer(doc, approval_metadata)

    logger.info(
        "Generated finalized document for review %s: %d redlines applied, metadata: %s",
        review_id, applied_count, approval_metadata,
    )

    output = io.BytesIO()
    doc.save(output)
    return output.getvalue()


def _apply_final_replacement(paragraph, old_text: str, new_text: str) -> None:
    """Replace old_text with new_text in a paragraph, preserving formatting."""
    if not paragraph.runs:
        paragraph.text = paragraph.text.replace(old_text, new_text, 1)
        return

    full_text = paragraph.text
    if old_text not in full_text:
        return

    idx = full_text.index(old_text)
    before_text = full_text[:idx]
    after_text = full_text[idx + len(old_text):]

    # Clear existing runs
    for run in paragraph.runs:
        run.text = ""

    runs = paragraph.runs
    run_idx = 0

    # Before
    if before_text:
        if run_idx < len(runs):
            runs[run_idx].text = before_text
            run_idx += 1

    # Replacement text (keep first available run's formatting)
    if run_idx < len(runs):
        runs[run_idx].text = new_text
        run_idx += 1
    else:
        paragraph.add_run(new_text)

    # After
    if after_text:
        if run_idx < len(runs):
            runs[run_idx].text = after_text
        else:
            paragraph.add_run(after_text)


def _add_approval_signature_block(doc: DocxDocument, metadata: dict[str, Any]) -> None:
    """Add an approval signature block to the document."""
    # Separator
    doc.add_paragraph("─" * 60)

    # Title
    title = doc.add_paragraph()
    run = title.add_run("APPROVAL SIGNATURE — FINAL APPROVED CONTRACT")
    run.bold = True
    run.font.size = Pt(14)
    run.font.color.rgb = RGBColor(0x00, 0x50, 0x00)

    doc.add_paragraph()

    # Approval details table
    table = doc.add_table(rows=7, cols=2)
    table.style = "Table Grid"

    labels = [
        ("Document Type", "Final Approved Contract"),
        ("Approved By", metadata.get("approved_by", "Unknown")),
        ("Approved At", metadata.get("approved_at", "Unknown")),
        ("Review Version", str(metadata.get("review_version", 1))),
        ("Comments", metadata.get("approval_comments", "N/A") or "N/A"),
        ("Conditions", str(metadata.get("approval_conditions", {}))),
        ("Generated At", metadata.get("generated_at", "")),
    ]

    for i, (label, value) in enumerate(labels):
        row = table.rows[i]
        row.cells[0].text = label
        row.cells[1].text = value
        # Bold the label
        for paragraph in row.cells[0].paragraphs:
            for run in paragraph.runs:
                run.bold = True

    doc.add_paragraph()
    note = doc.add_paragraph()
    note_run = note.add_run(
        "This document is the FINAL APPROVED version and is immutable. "
        "Any modifications after this point invalidate the approval."
    )
    note_run.font.size = Pt(9)
    note_run.font.italic = True
    note_run.font.color.rgb = RGBColor(0x99, 0x00, 0x00)

    doc.add_paragraph("─" * 60)


def _add_finalized_header_footer(doc: DocxDocument, metadata: dict[str, Any]) -> None:
    """Add header/footer marking the document as FINAL APPROVED."""
    for section in doc.sections:
        # Header
        header = section.header
        header.is_linked_to_previous = False
        hp = header.paragraphs[0] if header.paragraphs else header.add_paragraph()
        hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = hp.add_run("FINAL APPROVED CONTRACT — IMMUTABLE")
        run.bold = True
        run.font.size = Pt(8)
        run.font.color.rgb = RGBColor(0xCC, 0x00, 0x00)

        # Footer
        footer = section.footer
        footer.is_linked_to_previous = False
        fp = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        approved_by = metadata.get("approved_by", "Unknown")
        approved_at = metadata.get("approved_at", "")[:10] if metadata.get("approved_at") else ""
        fp_run = fp.add_run(f"Approved by {approved_by} on {approved_at} | Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        fp_run.font.size = Pt(7)
        fp_run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)
