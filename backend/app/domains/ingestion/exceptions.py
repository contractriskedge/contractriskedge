"""Ingestion domain exceptions with structured error codes."""

from app.kernel.web.exceptions import AppError, ValidationError, NotFoundError, ConflictError
from app.kernel.web.error_codes import ErrorCode


class UploadNotFoundError(NotFoundError):
    """Requested upload session does not exist."""
    def __init__(self, message: str | None = None, details: dict | None = None):
        super().__init__(error_code=ErrorCode.UPLOAD_NOT_FOUND, message=message, details=details)


class UploadNotCompletedError(ConflictError):
    """Upload session has not been completed yet."""
    def __init__(self, message: str | None = None, details: dict | None = None):
        super().__init__(error_code=ErrorCode.CONFLICTING_STATE, message=message, details=details)


class IngestionStateTransitionError(ConflictError):
    """Invalid state transition for ingestion pipeline."""
    def __init__(self, message: str | None = None, details: dict | None = None):
        super().__init__(error_code=ErrorCode.INGESTION_STATE_INVALID, message=message, details=details)


class FileTypeNotAllowedError(ValidationError):
    """File type is not in the allowed list."""
    def __init__(self, message: str | None = None, details: dict | None = None):
        super().__init__(error_code=ErrorCode.INVALID_FILE_TYPE, message=message, details=details)


class FileTooLargeError(ValidationError):
    """File exceeds maximum allowed size."""
    def __init__(self, message: str | None = None, details: dict | None = None):
        super().__init__(error_code=ErrorCode.FILE_TOO_LARGE, message=message, details=details)


class ChecksumMismatchError(ValidationError):
    """Client-provided checksum does not match server-computed checksum."""
    def __init__(self, message: str | None = None, details: dict | None = None):
        super().__init__(error_code=ErrorCode.CHECKSUM_MISMATCH, message=message, details=details)


class StorageUploadError(AppError):
    """Failed to upload file to object storage."""
    def __init__(self, message: str | None = None, details: dict | None = None):
        super().__init__(error_code=ErrorCode.STORAGE_UPLOAD_FAILURE, message=message, details=details)


class StorageDownloadError(AppError):
    """Failed to download file from object storage."""
    def __init__(self, message: str | None = None, details: dict | None = None):
        super().__init__(error_code=ErrorCode.STORAGE_DOWNLOAD_FAILURE, message=message, details=details)


class IngestionRetryLimitExceededError(ConflictError):
    """Maximum retry attempts for ingestion pipeline exceeded."""
    def __init__(self, message: str | None = None, details: dict | None = None):
        super().__init__(error_code=ErrorCode.INGESTION_RETRY_EXCEEDED, message=message, details=details)
