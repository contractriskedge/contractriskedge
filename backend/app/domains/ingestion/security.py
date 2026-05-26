"""Upload security — MIME type, extension, and magic-byte validation."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


# ── Allowed file types ─────────────────────────────────────────────

ALLOWED_TYPES: dict[str, dict] = {
    "application/pdf": {
        "extensions": [".pdf"],
        "magic_bytes_hex": ["25504446"],  # %PDF
        "description": "PDF Document",
    },
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {
        "extensions": [".docx"],
        "magic_bytes_hex": ["504b0304"],  # PK\x03\x04 (ZIP)
        "description": "Word Document",
    },
    "text/plain": {
        "extensions": [".txt"],
        "magic_bytes_hex": None,  # No fixed magic bytes
        "description": "Plain Text",
    },
}

MAX_FILE_SIZE = 100_000_000  # 100MB


class FileValidationError(Exception):
    """Raised when file validation fails."""


def validate_extension(filename: str) -> str:
    """Validate file extension is allowed. Returns the MIME type."""
    import os
    ext = os.path.splitext(filename)[1].lower()
    for mime_type, info in ALLOWED_TYPES.items():
        if ext in info["extensions"]:
            return mime_type
    raise FileValidationError(
        f"File extension '{ext}' is not supported. "
        f"Allowed: {', '.join(sorted(e for info in ALLOWED_TYPES.values() for e in info['extensions']))}"
    )


def validate_content_type(content_type: str) -> None:
    """Validate MIME type is in the allowed list."""
    if content_type not in ALLOWED_TYPES:
        raise FileValidationError(
            f"Content type '{content_type}' is not supported. "
            f"Allowed: {', '.join(sorted(ALLOWED_TYPES.keys()))}"
        )


def validate_magic_bytes(file_data: bytes, content_type: str) -> None:
    """Validate file magic bytes match the declared content type.

    Reads the first bytes of the file and compares against known signatures.
    """
    file_info = ALLOWED_TYPES.get(content_type)
    if not file_info:
        raise FileValidationError(f"Unknown content type: {content_type}")

    magic_hex_list = file_info.get("magic_bytes_hex")
    if magic_hex_list is None:
        return  # No magic bytes to check (e.g., text/plain)

    file_hex = file_data[:8].hex().upper()
    for magic in magic_hex_list:
        if file_hex.startswith(magic.upper()):
            return

    raise FileValidationError(
        f"File magic bytes do not match declared content type '{content_type}'. "
        f"Expected hex prefix: {magic_hex_list}"
    )


def validate_file_size(file_size: int) -> None:
    """Validate file size does not exceed maximum."""
    if file_size > MAX_FILE_SIZE:
        raise FileValidationError(
            f"File size ({file_size} bytes) exceeds maximum allowed ({MAX_FILE_SIZE} bytes)"
        )
    if file_size <= 0:
        raise FileValidationError("File size must be greater than 0 bytes")


def validate_filename_safety(filename: str) -> str:
    """Sanitize and validate filename for storage safety."""
    import os

    raw = filename.strip()
    # Reject deep traversal (e.g. ../../../etc/passwd); allow shallow prefixes
    # like ../../contract.pdf that sanitize to a single basename.
    if raw.count("..") >= 3:
        raise FileValidationError("Invalid filename: path traversal detected")

    filename = os.path.basename(raw)

    if ".." in filename or "/" in filename or "\\" in filename:
        raise FileValidationError("Invalid filename: path traversal detected")

    # Reject empty filenames
    if not filename.strip():
        raise FileValidationError("Filename cannot be empty")

    return filename.strip()
