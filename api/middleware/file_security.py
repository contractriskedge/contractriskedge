"""File upload validation utilities.

Provides magic byte validation, file type detection, and
security checks for uploaded documents.
"""

from __future__ import annotations

import logging
import os
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Magic bytes for supported file types
MAGIC_BYTES: Dict[str, Tuple[bytes, int]] = {
    "pdf": (b"%PDF", 4),
    "docx": (b"PK\x03\x04", 4),  # ZIP-based format
    "doc": (b"\xD0\xCF\x11\xE0", 4),  # OLE2 format
    "rtf": (b"{\\rtf", 5),
}

# Map extensions to their expected magic bytes
EXTENSION_MAGIC: Dict[str, Tuple[bytes, int]] = {
    ".pdf": (b"%PDF", 4),
    ".docx": (b"PK\x03\x04", 4),
    ".doc": (b"\xD0\xCF\x11\xE0", 4),
    ".rtf": (b"{\\rtf", 5),
    ".txt": (b"", 0),  # Text files have no magic bytes
}


def validate_file_magic(file_path: str, expected_ext: str) -> Tuple[bool, str]:
    """Validate a file's magic bytes match its expected extension.

    Args:
        file_path: Path to the uploaded file.
        expected_ext: Expected file extension (e.g., '.pdf').

    Returns:
        Tuple of (is_valid, error_message).
    """
    if expected_ext not in EXTENSION_MAGIC:
        return True, ""  # Unknown extension, skip validation

    expected_magic, num_bytes = EXTENSION_MAGIC[expected_ext]
    if num_bytes == 0:
        return True, ""  # No magic bytes to check

    try:
        with open(file_path, "rb") as f:
            header = f.read(num_bytes)
    except OSError as exc:
        logger.warning("Failed to read file for magic validation: %s", exc)
        return False, f"Cannot read file: {exc}"

    if header == expected_magic:
        return True, ""

    # Try to identify what it actually is
    detected = "unknown"
    for fmt, (magic, _) in MAGIC_BYTES.items():
        if header[:len(magic)] == magic:
            detected = fmt
            break

    return False, (
        f"File content does not match expected format '{expected_ext}'. "
        f"Detected format: '{detected}'. The file may be corrupted or "
        f"intentionally misnamed."
    )


def get_upload_rate_limit_key(tenant_id: str, user_id: str) -> str:
    """Generate a rate limit key for uploads.

    Args:
        tenant_id: Tenant identifier.
        user_id: User identifier.

    Returns:
        Rate limit key string.
    """
    return f"upload_rate:{tenant_id}:{user_id}"


# Upload rate limits: max 50 uploads per hour per user
UPLOAD_RATE_LIMIT = 50
UPLOAD_RATE_WINDOW = 3600  # 1 hour in seconds
