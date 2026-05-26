"""Storage service — S3/MinIO client wrapper with tenant-safe object paths."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import uuid
from datetime import datetime
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError, EndpointConnectionError

from app.config import settings
from app.kernel.web.exceptions import ServiceUnavailableError

logger = logging.getLogger(__name__)


class StorageServiceError(Exception):
    """Base error for storage operations."""


class StorageService:
    """S3-compatible object storage client (sync boto3, run in thread pool).

    Uses boto3 instead of aioboto3 because aioboto3 client startup can take
    20–30s on macOS, which exceeds API request deadlines.
    """

    def __init__(self, endpoint_url: str | None = None):
        self._endpoint = endpoint_url or settings.s3_endpoint
        self._client: Any = None
        self._lock = asyncio.Lock()

    def _boto_config(self) -> Config:
        return Config(
            connect_timeout=settings.s3_connect_timeout_seconds,
            read_timeout=settings.s3_read_timeout_seconds,
            retries={"max_attempts": 2, "mode": "standard"},
            s3={"addressing_style": "path"},
        )

    def _get_sync_client(self) -> Any:
        if self._client is None:
            self._client = boto3.client(
                "s3",
                endpoint_url=self._endpoint,
                aws_access_key_id=settings.s3_access_key,
                aws_secret_access_key=settings.s3_secret_key,
                region_name=settings.s3_region,
                config=self._boto_config(),
            )
        return self._client

    def _storage_unavailable(self, exc: Exception) -> ServiceUnavailableError:
        return ServiceUnavailableError(
            f"Object storage unavailable at {self._endpoint}. "
            "Start MinIO (./scripts/start-minio.sh), then retry. "
            f"Details: {exc}"
        )

    async def _run_sync(self, fn, *, operation: str):
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(fn),
                timeout=settings.s3_operation_timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            raise self._storage_unavailable(
                TimeoutError(f"{operation} timed out after {settings.s3_operation_timeout_seconds}s")
            ) from exc
        except (EndpointConnectionError, BotoCoreError, OSError) as exc:
            raise self._storage_unavailable(exc) from exc
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code in (
                "InvalidAccessKeyId",
                "SignatureDoesNotMatch",
                "AccessDenied",
                "InvalidBucketName",
                "NoSuchBucket",
            ):
                raise self._storage_unavailable(exc) from exc
            raise

    async def warm_up(self) -> None:
        """Create boto3 client and verify bucket (call once at app startup)."""
        async with self._lock:
            bucket = settings.s3_bucket

            def _warm() -> None:
                client = self._get_sync_client()
                if settings.s3_skip_bucket_ensure:
                    return
                try:
                    client.head_bucket(Bucket=bucket)
                except ClientError:
                    try:
                        client.create_bucket(Bucket=bucket)
                        logger.info("Created storage bucket: %s", bucket)
                    except ClientError as create_exc:
                        code = create_exc.response.get("Error", {}).get("Code", "")
                        if code not in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
                            raise

            await self._run_sync(_warm, operation="warm_up")
            logger.info("Storage client ready (endpoint=%s, bucket=%s)", self._endpoint, bucket)

    def build_object_key(self, tenant_id: str, filename: str) -> str:
        """Build tenant-scoped object key with UUID."""
        now = datetime.utcnow()
        obj_uuid = uuid.uuid4()
        return f"{tenant_id}/contracts/{now.year}/{now.month:02d}/{obj_uuid}/{filename}"

    async def ensure_bucket(self, bucket: str) -> None:
        if settings.s3_skip_bucket_ensure:
            return

        def _ensure() -> None:
            client = self._get_sync_client()
            try:
                client.head_bucket(Bucket=bucket)
            except ClientError:
                try:
                    client.create_bucket(Bucket=bucket)
                    logger.info("Created storage bucket: %s", bucket)
                except ClientError as create_exc:
                    code = create_exc.response.get("Error", {}).get("Code", "")
                    if code not in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
                        raise

        await self._run_sync(_ensure, operation="ensure_bucket")

    async def generate_presigned_upload_url(
        self, bucket: str, key: str, content_type: str, expires_in: int = 3600,
    ) -> str:
        def _presign() -> str:
            return self._get_sync_client().generate_presigned_url(
                "put_object",
                Params={"Bucket": bucket, "Key": key, "ContentType": content_type},
                ExpiresIn=expires_in,
            )

        return await self._run_sync(_presign, operation="presign")

    async def upload_fileobj(
        self,
        bucket: str,
        key: str,
        file_body: bytes,
        content_type: str,
        metadata: dict | None = None,
    ) -> str:
        extra_args: dict = {"ContentType": content_type}
        if metadata:
            extra_args["Metadata"] = {k: str(v) for k, v in metadata.items()}

        def _upload() -> str:
            self._get_sync_client().put_object(
                Bucket=bucket,
                Key=key,
                Body=file_body,
                **extra_args,
            )
            return key

        return await self._run_sync(_upload, operation="upload")

    async def download_fileobj(self, bucket: str, key: str) -> bytes:
        def _download() -> bytes:
            response = self._get_sync_client().get_object(Bucket=bucket, Key=key)
            return response["Body"].read()

        return await self._run_sync(_download, operation="download")

    async def delete_object(self, bucket: str, key: str) -> None:
        def _delete() -> None:
            self._get_sync_client().delete_object(Bucket=bucket, Key=key)

        await self._run_sync(_delete, operation="delete")

    async def object_exists(self, bucket: str, key: str) -> bool:
        def _head() -> bool:
            try:
                self._get_sync_client().head_object(Bucket=bucket, Key=key)
                return True
            except ClientError:
                return False

        try:
            return await self._run_sync(_head, operation="head_object")
        except ServiceUnavailableError:
            raise
        except ClientError:
            return False

    @staticmethod
    def compute_sha256(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()


storage_service = StorageService()
