"""Text normalization pipeline — cleans and standardizes extracted text."""

from __future__ import annotations

import re
import unicodedata


def normalize_text(text: str) -> str:
    """Full normalization pipeline for extracted text.

    Order matters: each step prepares for the next.
    """
    text = normalize_unicode(text)
    text = normalize_line_endings(text)
    text = remove_ocr_artifacts(text)
    text = normalize_whitespace(text)
    text = remove_control_chars(text)
    return text.strip()


def normalize_unicode(text: str) -> str:
    """Normalize Unicode to NFC form and repair common encoding issues."""
    text = unicodedata.normalize("NFC", text)
    # Replace common Windows-1252 characters that appear in OCR output
    replacements = {
        "\x85": "...",   # ellipsis
        "\x91": "'",     # left single quote
        "\x92": "'",     # right single quote
        "\x93": '"',     # left double quote
        "\x94": '"',     # right double quote
        "\x95": " ",     # bullet
        "\x96": "-",     # en dash
        "\x97": "--",    # em dash
        "\xa0": " ",     # non-breaking space
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def normalize_line_endings(text: str) -> str:
    """Normalize all line endings to \n."""
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")
    return text


def remove_ocr_artifacts(text: str) -> str:
    """Remove common OCR garbage artifacts."""
    # Remove sequences of repeated non-alphanumeric characters (OCR noise)
    text = re.sub(r'([^\w\s])\1{4,}', ' ', text)
    # Remove isolated single characters on their own line (often OCR errors)
    text = re.sub(r'\n\s*[^\w\s]\s*\n', '\n', text)
    # Remove lines that are mostly non-alphanumeric
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            cleaned.append("")
            continue
        alnum = sum(1 for c in stripped if c.isalnum())
        if alnum / max(len(stripped), 1) < 0.3 and len(stripped) > 10:
            continue  # Skip garbage lines
        cleaned.append(line)
    return "\n".join(cleaned)


def normalize_whitespace(text: str) -> str:
    """Collapse multiple spaces, remove trailing whitespace per line."""
    lines = text.split("\n")
    lines = [re.sub(r'[ \t]+', ' ', line).rstrip() for line in lines]
    return "\n".join(lines)


def remove_control_chars(text: str) -> str:
    """Remove non-printable control characters except newlines and tabs."""
    return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
