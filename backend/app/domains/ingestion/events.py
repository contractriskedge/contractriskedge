"""Ingestion domain events."""

from dataclasses import dataclass

from app.kernel.events.bus import DomainEvent


@dataclass
class UploadInitiated(DomainEvent):
    event_type: str = "ingestion.upload.initiated"


@dataclass
class UploadValidated(DomainEvent):
    event_type: str = "ingestion.upload.validated"


@dataclass
class UploadCompleted(DomainEvent):
    event_type: str = "ingestion.upload.completed"


@dataclass
class UploadFailed(DomainEvent):
    event_type: str = "ingestion.upload.failed"


@dataclass
class UploadCancelled(DomainEvent):
    event_type: str = "ingestion.upload.cancelled"


@dataclass
class UploadQuarantined(DomainEvent):
    event_type: str = "ingestion.upload.quarantined"


@dataclass
class IngestionStatusChanged(DomainEvent):
    event_type: str = "ingestion.status.changed"
