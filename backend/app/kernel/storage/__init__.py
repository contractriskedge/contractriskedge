"""Abstract file storage service — Local, S3, Azure Blob, SharePoint."""
from .service import StorageService, StorageProvider, StoredFile

__all__ = ["StorageService", "StorageProvider", "StoredFile"]
