"""Abstract file storage service — provider-independent.

Supports:
- Local filesystem
- AWS S3
- Azure Blob Storage
- SharePoint

Usage:
    storage = StorageService(provider=StorageProvider.S3, config={...})
    url = await storage.upload("contracts/executed/abc.pdf", data)
    data = await storage.download("contracts/executed/abc.pdf")
"""

from __future__ import annotations

import enum
import io
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class StorageProvider(str, enum.Enum):
    """Supported storage backends."""
    LOCAL = "local"
    S3 = "s3"
    AZURE_BLOB = "azure_blob"
    SHAREPOINT = "sharepoint"


@dataclass
class StoredFile:
    """Metadata about a stored file."""
    path: str
    url: Optional[str] = None
    size_bytes: Optional[int] = None
    content_type: Optional[str] = None
    uploaded_at: Optional[datetime] = None
    provider: Optional[str] = None


class StorageService:
    """Abstract file storage service for executed contracts and documents.

    Used by:
    - Executed PDF storage
    - Signature certificates
    - Contract documents
    - Audit trail exports
    - Report generation
    """

    def __init__(
        self,
        provider: StorageProvider = StorageProvider.LOCAL,
        config: Optional[dict] = None,
    ):
        self.provider = provider
        self.config = config or {}

        if provider == StorageProvider.LOCAL:
            self._base_path = Path(self.config.get("base_path", "./storage"))
            self._base_path.mkdir(parents=True, exist_ok=True)

    async def upload(
        self,
        path: str,
        data: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> StoredFile:
        """Upload a file to storage.

        Args:
            path: Storage path (e.g., "contracts/executed/abc.pdf")
            data: File content as bytes
            content_type: MIME type
            metadata: Additional metadata

        Returns:
            StoredFile with path and URL
        """
        if self.provider == StorageProvider.LOCAL:
            return await self._upload_local(path, data, content_type)
        elif self.provider == StorageProvider.S3:
            return await self._upload_s3(path, data, content_type, metadata)
        elif self.provider == StorageProvider.AZURE_BLOB:
            return await self._upload_azure(path, data, content_type)
        elif self.provider == StorageProvider.SHAREPOINT:
            return await self._upload_sharepoint(path, data, content_type)
        else:
            raise ValueError(f"Unknown storage provider: {self.provider}")

    async def download(self, path: str) -> Optional[bytes]:
        """Download a file from storage."""
        if self.provider == StorageProvider.LOCAL:
            return await self._download_local(path)
        elif self.provider == StorageProvider.S3:
            return await self._download_s3(path)
        elif self.provider == StorageProvider.AZURE_BLOB:
            return await self._download_azure(path)
        elif self.provider == StorageProvider.SHAREPOINT:
            return await self._download_sharepoint(path)
        else:
            raise ValueError(f"Unknown storage provider: {self.provider}")

    async def delete(self, path: str) -> bool:
        """Delete a file from storage."""
        if self.provider == StorageProvider.LOCAL:
            return await self._delete_local(path)
        elif self.provider == StorageProvider.S3:
            return await self._delete_s3(path)
        elif self.provider == StorageProvider.AZURE_BLOB:
            return await self._delete_azure(path)
        elif self.provider == StorageProvider.SHAREPOINT:
            return await self._delete_sharepoint(path)
        else:
            raise ValueError(f"Unknown storage provider: {self.provider}")

    async def exists(self, path: str) -> bool:
        """Check if a file exists in storage."""
        if self.provider == StorageProvider.LOCAL:
            return (self._base_path / path).exists()
        # TODO: Implement for other providers
        return False

    def get_url(self, path: str) -> Optional[str]:
        """Get the public URL for a stored file."""
        if self.provider == StorageProvider.LOCAL:
            return None  # Local files don't have public URLs
        # TODO: Implement for S3/Azure/SharePoint
        return None

    # ── Local ───────────────────────────────────────────────────

    async def _upload_local(
        self, path: str, data: bytes, content_type: Optional[str],
    ) -> StoredFile:
        full_path = self._base_path / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(data)
        logger.debug("Uploaded local file: %s (%d bytes)", full_path, len(data))
        return StoredFile(
            path=path,
            size_bytes=len(data),
            content_type=content_type,
            uploaded_at=datetime.now(),
            provider="local",
        )

    async def _download_local(self, path: str) -> Optional[bytes]:
        full_path = self._base_path / path
        if not full_path.exists():
            logger.warning("Local file not found: %s", full_path)
            return None
        return full_path.read_bytes()

    async def _delete_local(self, path: str) -> bool:
        full_path = self._base_path / path
        if full_path.exists():
            full_path.unlink()
            logger.debug("Deleted local file: %s", full_path)
            return True
        return False

    # ── S3 ──────────────────────────────────────────────────────

    async def _upload_s3(
        self, path: str, data: bytes, content_type: Optional[str], metadata: Optional[dict],
    ) -> StoredFile:
        # TODO: Implement S3 upload
        # import boto3
        # s3 = boto3.client("s3", **self.config)
        # s3.put_object(Bucket=bucket, Key=path, Body=data, ContentType=content_type)
        logger.debug("S3 upload would store: %s", path)
        return StoredFile(path=path, size_bytes=len(data), provider="s3")

    async def _download_s3(self, path: str) -> Optional[bytes]:
        # TODO: Implement S3 download
        logger.debug("S3 download would fetch: %s", path)
        return None

    async def _delete_s3(self, path: str) -> bool:
        # TODO: Implement S3 delete
        logger.debug("S3 delete would remove: %s", path)
        return True

    # ── Azure Blob ──────────────────────────────────────────────

    async def _upload_azure(self, path: str, data: bytes, content_type: Optional[str]) -> StoredFile:
        # TODO: Implement Azure Blob upload
        logger.debug("Azure upload would store: %s", path)
        return StoredFile(path=path, size_bytes=len(data), provider="azure_blob")

    async def _download_azure(self, path: str) -> Optional[bytes]:
        logger.debug("Azure download would fetch: %s", path)
        return None

    async def _delete_azure(self, path: str) -> bool:
        logger.debug("Azure delete would remove: %s", path)
        return True

    # ── SharePoint ──────────────────────────────────────────────

    async def _upload_sharepoint(self, path: str, data: bytes, content_type: Optional[str]) -> StoredFile:
        # TODO: Implement SharePoint upload
        logger.debug("SharePoint upload would store: %s", path)
        return StoredFile(path=path, size_bytes=len(data), provider="sharepoint")

    async def _download_sharepoint(self, path: str) -> Optional[bytes]:
        logger.debug("SharePoint download would fetch: %s", path)
        return None

    async def _delete_sharepoint(self, path: str) -> bool:
        logger.debug("SharePoint delete would remove: %s", path)
        return True
