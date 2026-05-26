"""Review domain events."""

from dataclasses import dataclass

from app.kernel.events.bus import DomainEvent


@dataclass
class ReviewEscalated(DomainEvent):
    event_type: str = "review.escalated"


@dataclass
class ReviewApproved(DomainEvent):
    event_type: str = "review.approved"


@dataclass
class ReviewRejected(DomainEvent):
    event_type: str = "review.rejected"
