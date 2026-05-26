"""Redline operation classification and safe diff construction.

Legal documents require different mutation strategies:
- INSERT: add a missing clause at an anchor (do not delete surrounding text)
- MODIFICATION: change a targeted span within an existing clause
- REPLACE: swap one clause for another (bounded original_text only)
- DELETE: remove a clause span
"""

from __future__ import annotations

import difflib
import re
from enum import Enum
from typing import Optional


class RedlineOperation(str, Enum):
    INSERT = "insert"
    MODIFICATION = "modification"
    DELETE = "delete"
    REPLACE = "replace"


# Clause types that are usually absent rather than rewritten in place.
_MISSING_CLAUSE_TYPES = frozenset({
    "governing_law",
    "force_majeure",
    "insurance",
    "data_privacy",
    "non_compete",
    "ip",
    "intellectual_property",
})

# If original_text exceeds this length it is likely chunk context, not a clause span.
_MAX_SAFE_REPLACE_CHARS = 400


def normalize_operation(value: Optional[str]) -> Optional[RedlineOperation]:
    if not value:
        return None
    raw = str(value).strip().lower()
    aliases = {
        "insert": RedlineOperation.INSERT,
        "insert_after": RedlineOperation.INSERT,
        "add": RedlineOperation.INSERT,
        "modification": RedlineOperation.MODIFICATION,
        "modify": RedlineOperation.MODIFICATION,
        "edit": RedlineOperation.MODIFICATION,
        "delete": RedlineOperation.DELETE,
        "remove": RedlineOperation.DELETE,
        "replace": RedlineOperation.REPLACE,
        "replacement": RedlineOperation.REPLACE,
    }
    return aliases.get(raw)


def infer_operation(
    original_text: str,
    proposed_text: str,
    *,
    clause_type: Optional[str] = None,
    stored_operation: Optional[str] = None,
) -> RedlineOperation:
    """Infer how a redline should be applied when operation is not stored."""
    explicit = normalize_operation(stored_operation)
    if explicit:
        return explicit

    original = (original_text or "").strip()
    proposed = (proposed_text or "").strip()

    if proposed and not original:
        return RedlineOperation.INSERT
    if original and not proposed:
        return RedlineOperation.DELETE

    if not original and not proposed:
        return RedlineOperation.MODIFICATION

    norm_orig = _normalize(original)
    norm_prop = _normalize(proposed)
    ratio = difflib.SequenceMatcher(None, norm_orig, norm_prop).ratio()

    # ── Scope Safety Checks ────────────────────────────────────
    # Detect if the text includes numbering (e.g., "4.2" or "4.") 
    # that indicates the AI grabbed a heading + clause body.
    # In this case, prefer MODIFICATION over REPLACE to avoid
    # replacing the heading structure.
    _has_numbering = bool(re.search(r'^\d+\.\d*\s', original) or re.search(r'^\d+\.\d*\s', proposed))
    
    # If both have numbering but different numbers, the AI changed
    # the section number — this is likely a format error, not intentional.
    _orig_num = re.match(r'^(\d+\.?\d*)', original)
    _prop_num = re.match(r'^(\d+\.?\d*)', proposed)
    _numbering_changed = (
        _orig_num and _prop_num 
        and _orig_num.group(1) != _prop_num.group(1)
    )

    if _numbering_changed and ratio > 0.3:
        # AI likely hallucinated a different section number — treat as MODIFICATION
        # and only change the text body, not the numbering
        return RedlineOperation.MODIFICATION

    if ratio > 0.88:
        return RedlineOperation.MODIFICATION

    prop_in_orig = norm_prop in norm_orig
    orig_in_prop = norm_orig in norm_prop

    # Chunk-level context mistaken for clause text (common AI failure mode).
    if (
        len(original) > _MAX_SAFE_REPLACE_CHARS
        and not prop_in_orig
        and ratio < 0.45
    ):
        return RedlineOperation.INSERT

    if clause_type in _MISSING_CLAUSE_TYPES and not prop_in_orig and ratio < 0.55:
        return RedlineOperation.INSERT

    if orig_in_prop and len(proposed) > len(original) * 1.05:
        return RedlineOperation.MODIFICATION

    if len(original) <= _MAX_SAFE_REPLACE_CHARS and ratio >= 0.35:
        return RedlineOperation.MODIFICATION

    if len(original) > _MAX_SAFE_REPLACE_CHARS:
        return RedlineOperation.INSERT

    # If original has numbering but proposed doesn't (or vice versa),
    # prefer MODIFICATION to avoid corrupting document structure
    if _has_numbering:
        return RedlineOperation.MODIFICATION

    return RedlineOperation.REPLACE


def resolve_apply_texts(
    operation: RedlineOperation,
    original_text: str,
    proposed_text: str,
    anchor_text: str = "",
    reviewer_modified_text: Optional[str] = None,
) -> tuple[str, str, str]:
    """Return (original_span, proposed_span, anchor) for document mutation."""
    proposed = (reviewer_modified_text or proposed_text or "").strip()
    original = (original_text or "").strip()
    anchor = (anchor_text or "").strip()

    if operation == RedlineOperation.INSERT:
        return "", proposed, anchor

    if operation == RedlineOperation.DELETE:
        return original, "", anchor

    return original, proposed, anchor


def build_word_diff(
    operation: RedlineOperation,
    original_text: str,
    proposed_text: str,
) -> list[dict[str, str]]:
    """Build sentence-first, token-second diff segments for legal review UI."""
    original = (original_text or "").strip()
    proposed = (proposed_text or "").strip()

    if operation == RedlineOperation.INSERT:
        if not proposed:
            return []
        return [{"tag": "insert", "text": proposed}]

    if operation == RedlineOperation.DELETE:
        if not original:
            return []
        return [{"tag": "delete", "text": original}]

    if _normalize(original) == _normalize(proposed):
        return [{"tag": "equal", "text": proposed or original}]

    before_sentences = _sentence_chunks(original)
    after_sentences = _sentence_chunks(proposed)
    matcher = difflib.SequenceMatcher(
        None,
        [_normalize(s) for s in before_sentences],
        [_normalize(s) for s in after_sentences],
        autojunk=False,
    )
    segments: list[dict[str, str]] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for text in before_sentences[i1:i2]:
                _append_diff_segment(segments, "equal", text)
        elif tag == "replace":
            segments.extend(_diff_modified_sentence_blocks(
                before_sentences[i1:i2],
                after_sentences[j1:j2],
            ))
        elif tag == "delete":
            for text in before_sentences[i1:i2]:
                _append_diff_segment(segments, "delete", text)
        elif tag == "insert":
            for text in after_sentences[j1:j2]:
                _append_diff_segment(segments, "insert", text)

    return segments


def change_type_for_operation(operation: RedlineOperation) -> str:
    return operation.value


def is_chunk_mistaken_as_original(original_text: str, proposed_text: str) -> bool:
    """True when original_text is likely ingestion chunk context, not the clause being changed."""
    original = (original_text or "").strip()
    proposed = (proposed_text or "").strip()
    if not proposed:
        return False
    if not original:
        return True
    norm_orig = _normalize(original)
    norm_prop = _normalize(proposed)
    if norm_prop in norm_orig or norm_orig in norm_prop:
        return False
    ratio = difflib.SequenceMatcher(None, norm_orig, norm_prop).ratio()
    if len(original) > _MAX_SAFE_REPLACE_CHARS and ratio < 0.45:
        return True
    # Title/recital block paired with a numbered clause body (common AI failure).
    if (
        "master services agreement" in norm_orig[:120]
        or "effective date" in norm_orig[:200]
    ) and re.search(r"^\d+\.", proposed.strip()):
        return True
    return False


# Roman numeral mapping for proposed text matching (I, II, III, IV, V, VI, VII, VIII, IX, X, ...)
_ROMAN_TO_INT = {
    "i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5,
    "vi": 6, "vii": 7, "viii": 8, "ix": 9, "x": 10,
    "xi": 11, "xii": 12, "xiii": 13, "xiv": 14, "xv": 15,
}
# Reverse mapping for searching Roman numerals in text
_INT_TO_ROMAN = {v: k.upper() for k, v in _ROMAN_TO_INT.items()}


def _find_section_line(lines: list[str], section_num: int) -> Optional[str]:
    """Find a line containing the given section number (e.g. '3.' or 'Section 3.').

    Uses flexible matching — the section number can appear anywhere in the line,
    not just at the start. Handles multi-line headers where the section number
    is on its own line (e.g. "3." followed by "Term" on the next line).
    Also handles Roman numeral equivalents (e.g. section 3 → "III.").

    Returns the first matching line (truncated to 120 chars), or None.
    """
    # Build search terms: Arabic numeral + Roman equivalent
    search_terms = [str(section_num)]
    roman = _INT_TO_ROMAN.get(section_num)
    if roman:
        search_terms.append(roman)

    patterns = []
    for term in search_terms:
        patterns.extend([
            # "Section 3. Term", "Article 3 - Term", "ARTICLE 3: Term", "3. Term"
            re.compile(rf"(?:^|Section\s+|Article\s+|ART(?:ICLE)?\s+){term}[\.\-\:\s]"),
            # "§3. Term" or "§3 Term"
            re.compile(rf"(?:^|§){term}\.(?:\s|$)"),
            # Bare "3." on its own line (multi-line header)
            re.compile(rf"^{term}\.$"),
        ])

    for i, line in enumerate(lines):
        # Allow bare "X." lines (len >= 2) for multi-line header case
        is_bare = any(re.match(rf"^{re.escape(t)}\.$", line) for t in search_terms)
        min_len = 2 if is_bare else 4
        if len(line) < min_len or len(line) > 200:
            continue
        for pat in patterns:
            if pat.search(line):
                # If this is a bare "3." line, try to include the next line as context
                if is_bare and i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if len(next_line) >= 2 and len(next_line) <= 120:
                        combined = f"{line} {next_line}"[:120]
                        return combined
                return line[:120]
    return None


def _parse_proposed_section(proposed_text: str) -> tuple[int | None, int | None]:
    """Extract target section and subsection numbers from proposed text.

    Handles: "4. Indemnification", "4.5 Subsection", "§4. Test", "IV. Roman"
    Returns (section_number, subsection_number) or (None, None).
    """
    text = (proposed_text or "").strip()
    if not text:
        return None, None

    # Try Arabic numerals: "4.", "4.5", "§4.", "§4.5"
    m = re.match(r"^(?:§)?(\d+)(?:\.(\d+))?[.\s]", text)
    if m:
        return int(m.group(1)), (int(m.group(2)) if m.group(2) else None)

    # Try Roman numerals: "IV.", "IV.5"
    m = re.match(r"^([IVXLCDM]+)(?:\.(\d+))?[.\s]", text, re.I)
    if m:
        roman = m.group(1).lower()
        if roman in _ROMAN_TO_INT:
            return _ROMAN_TO_INT[roman], (int(m.group(2)) if m.group(2) else None)

    return None, None


def infer_anchor_from_context(
    contract_excerpt: str,
    proposed_text: str = "",
) -> str:
    """Pick a short phrase from contract text suitable for Locate / insert-after."""
    excerpt = (contract_excerpt or "").strip()
    if not excerpt:
        return ""

    lines = [ln.strip() for ln in excerpt.splitlines() if ln.strip()]

    target_section, target_subsection = _parse_proposed_section(proposed_text)
    if target_section is not None:
        # For subsection proposals (e.g. 2.3), anchor after the parent section (2).
        # For top-level proposals (e.g. 4), anchor after the nearest preceding section.
        search_start = target_section if target_subsection is not None else (target_section - 1)
        for prior in range(search_start, 0, -1):
            match = _find_section_line(lines, prior)
            if match:
                return match
        # Gap in extraction (e.g. §4 proposed but only §1–2 and §9 in text): anchor before next section.
        for line in lines:
            if len(line) < 4 or len(line) > 200:
                continue
            m = re.search(r"(?:^|Section\s+|Article\s+|ART(?:ICLE)?\s+|§)(\d+)\.?", line)
            if m and int(m.group(1)) > target_section:
                if not re.search(
                    r"master services agreement|effective date|^between:",
                    line,
                    re.I,
                ):
                    return line[:120]

    for line in reversed(lines):
        if 4 <= len(line) <= 200 and re.search(r"(?:^|Section\s+|Article\s+|ART(?:ICLE)?\s+|§)\d+\.?", line):
            if not re.search(
                r"master services agreement|effective date|^between:",
                line,
                re.I,
            ):
                return line[:120]

    for line in reversed(lines):
        if 10 <= len(line) <= 200 and not re.search(
            r"master services agreement|effective date|^between:",
            line,
            re.I,
        ):
            return line[:120]

    return lines[-1][:120] if lines else ""


def build_insert_context_snippet(
    contract_excerpt: str,
    anchor_text: str,
    *,
    max_len: int = 320,
) -> Optional[str]:
    """Short excerpt around the insertion anchor — not the full AI chunk."""
    excerpt = (contract_excerpt or "").strip()
    anchor = (anchor_text or "").strip()
    if not excerpt or not anchor:
        return None

    lower_excerpt = excerpt.lower()
    lower_anchor = anchor.lower()
    pos = lower_excerpt.find(lower_anchor)
    if pos < 0:
        for probe_len in (min(len(anchor), 80), 40, 20):
            probe = anchor[:probe_len].strip()
            if len(probe) < 8:
                continue
            pos = lower_excerpt.find(probe.lower())
            if pos >= 0:
                break
    if pos < 0:
        return None

    start = max(0, pos - 60)
    end = min(len(excerpt), pos + len(anchor) + max_len)
    snippet = excerpt[start:end].strip()
    if start > 0:
        snippet = "…" + snippet
    if end < len(excerpt):
        snippet = snippet + "…"
    return snippet


def prepare_redline_display(
    original_text: str,
    proposed_text: str,
    *,
    clause_type: Optional[str] = None,
    stored_operation: Optional[str] = None,
    anchor_text: str = "",
    reviewer_modified_text: Optional[str] = None,
) -> dict:
    """Normalize redline fields for API/UI (insert vs replace, word diff)."""
    proposed = (reviewer_modified_text or proposed_text or "").strip()
    stored_orig = (original_text or "").strip()
    anchor = (anchor_text or "").strip()
    context_excerpt: Optional[str] = None

    operation = infer_operation(
        stored_orig,
        proposed,
        clause_type=clause_type,
        stored_operation=stored_operation,
    )
    if is_chunk_mistaken_as_original(stored_orig, proposed):
        operation = RedlineOperation.INSERT

    if operation == RedlineOperation.INSERT:
        if stored_orig and is_chunk_mistaken_as_original(stored_orig, proposed):
            if not anchor:
                anchor = infer_anchor_from_context(stored_orig, proposed)
            context_excerpt = build_insert_context_snippet(stored_orig, anchor)
        display_original = ""
    else:
        display_original = stored_orig

    word_diff = build_word_diff(
        operation,
        stored_orig if operation != RedlineOperation.INSERT else "",
        proposed,
    )

    return {
        "operation": operation.value,
        "anchor_text": anchor,
        "display_original": display_original,
        "context_excerpt": context_excerpt,
        "word_diff": word_diff,
    }


def _diff_spans(original: str, proposed: str) -> tuple[str, str]:
    """Trim unchanged prefix/suffix so only the mutated span is diffed."""
    if not original:
        return "", proposed
    if not proposed:
        return original, ""

    orig_words = original.split()
    prop_words = proposed.split()

    prefix = 0
    while (
        prefix < len(orig_words)
        and prefix < len(prop_words)
        and orig_words[prefix].lower() == prop_words[prefix].lower()
    ):
        prefix += 1

    suffix = 0
    while (
        suffix < len(orig_words) - prefix
        and suffix < len(prop_words) - prefix
        and orig_words[-(suffix + 1)].lower() == prop_words[-(suffix + 1)].lower()
    ):
        suffix += 1

    end_o = len(orig_words) - suffix if suffix else len(orig_words)
    end_p = len(prop_words) - suffix if suffix else len(prop_words)

    before = " ".join(orig_words[prefix:end_o])
    after = " ".join(prop_words[prefix:end_p])
    return before, after


_SECTION_HEADING_RE = re.compile(
    r"^(?:§\s*)?(?:\d+(?:\.\d+)*\.?\s+)?[A-Z][A-Za-z0-9,&()/-]*(?:\s+[A-Z][A-Za-z0-9,&()/-]*){0,8}$"
)


def _sentence_chunks(text: str) -> list[str]:
    """Split legal text into sentence/heading chunks while preserving spacing."""
    chunks: list[str] = []
    if not text:
        return chunks

    for raw_line in re.findall(r"[^\n]*(?:\n|$)", text):
        if not raw_line:
            continue

        trailing_newline = "\n" if raw_line.endswith("\n") else ""
        line = raw_line[:-1] if trailing_newline else raw_line
        stripped = line.strip()

        if not stripped:
            chunks.append(raw_line)
            continue

        if _SECTION_HEADING_RE.match(stripped) and not re.search(r"[.!?:;]$", stripped):
            chunks.append(raw_line)
            continue

        start = 0
        for match in re.finditer(r"[.!?;](?=\s|$)", line):
            end = match.end()
            chunks.append(line[start:end])
            start = end

        if start < len(line):
            chunks.append(line[start:])

        if trailing_newline and chunks:
            chunks[-1] += trailing_newline

    return [chunk for chunk in chunks if chunk]


def _token_chunks(text: str) -> list[str]:
    return re.findall(r"\s+|[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)*|[^\sA-Za-z0-9]", text)


def _append_diff_segment(segments: list[dict[str, str]], tag: str, text: str) -> None:
    if not text:
        return
    if segments and segments[-1]["tag"] == tag:
        segments[-1]["text"] += text
    else:
        segments.append({"tag": tag, "text": text})


def _token_level_diff(before: str, after: str) -> list[dict[str, str]]:
    before_tokens = _token_chunks(before)
    after_tokens = _token_chunks(after)
    matcher = difflib.SequenceMatcher(None, before_tokens, after_tokens, autojunk=False)
    segments: list[dict[str, str]] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            _append_diff_segment(segments, "equal", "".join(before_tokens[i1:i2]))
        elif tag == "replace":
            _append_diff_segment(segments, "delete", "".join(before_tokens[i1:i2]))
            _append_diff_segment(segments, "insert", "".join(after_tokens[j1:j2]))
        elif tag == "delete":
            _append_diff_segment(segments, "delete", "".join(before_tokens[i1:i2]))
        elif tag == "insert":
            _append_diff_segment(segments, "insert", "".join(after_tokens[j1:j2]))

    return segments


def _sentence_similarity(a: str, b: str) -> float:
    a_tokens = {t for t in _token_chunks(_normalize(a)) if t.strip()}
    b_tokens = {t for t in _token_chunks(_normalize(b)) if t.strip()}
    if not a_tokens and not b_tokens:
        return 1.0
    return len(a_tokens & b_tokens) / max(len(a_tokens), len(b_tokens))


def _diff_modified_sentence_blocks(deleted: list[str], inserted: list[str]) -> list[dict[str, str]]:
    segments: list[dict[str, str]] = []

    for idx in range(max(len(deleted), len(inserted))):
        before = deleted[idx] if idx < len(deleted) else ""
        after = inserted[idx] if idx < len(inserted) else ""

        if before and after and _sentence_similarity(before, after) >= 0.2:
            for segment in _token_level_diff(before, after):
                _append_diff_segment(segments, segment["tag"], segment["text"])
        else:
            _append_diff_segment(segments, "delete", before)
            _append_diff_segment(segments, "insert", after)

    return segments


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()
