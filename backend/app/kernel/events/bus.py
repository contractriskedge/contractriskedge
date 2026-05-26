"""Domain event base class and in-memory event bus."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Awaitable
from uuid import uuid4

logger = logging.getLogger(__name__)

Handler = Callable[..., Awaitable[None]]


@dataclass
class DomainEvent:
    """Base class for all domain events."""
    event_id: str = field(default_factory=lambda: str(uuid4()))
    event_type: str = ""
    tenant_id: str = ""
    correlation_id: str = ""
    actor_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    data: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.event_type:
            self.event_type = self.__class__.__name__


class EventBus:
    """In-memory domain event bus. Synchronous within the process."""

    def __init__(self):
        self._handlers: dict[type, list[Handler]] = defaultdict(list)

    def register(self, event_type: type, handler: Handler):
        self._handlers[event_type].append(handler)

    async def emit(self, event) -> None:
        handlers = self._handlers.get(type(event), [])
        if not handlers:
            return
        results = await asyncio.gather(
            *[h(event) for h in handlers],
            return_exceptions=True,
        )
        for handler, result in zip(handlers, results):
            if isinstance(result, Exception):
                logger.error("Handler %s failed for %s: %s", handler.__name__, type(event).__name__, result)
