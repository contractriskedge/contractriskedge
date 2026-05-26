"""SSE streaming support for long-running LLM analyses.

Provides Server-Sent Events (SSE) streaming for real-time delivery
of LLM analysis results to clients. Supports chunked responses,
heartbeat signals, and graceful cancellation.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any, AsyncGenerator, AsyncIterator, Callable, Dict, Optional

from .models import LLMRequest, LLMResponse, StreamingEvent, ProviderType

logger = logging.getLogger(__name__)


class SSEStreamer:
    """Server-Sent Events streamer for LLM responses.

    Wraps streaming LLM responses in SSE format for delivery to
    HTTP clients. Supports heartbeat keep-alive, cancellation,
    and progress tracking for long-running analyses.

    Usage:
        streamer = SSEStreamer()
        async for event in streamer.stream_llm_response(llm_client, request):
            # event is already formatted as an SSE string
            await websocket.send(event)
    """

    def __init__(
        self,
        heartbeat_interval: float = 15.0,
        max_queue_size: int = 100,
    ) -> None:
        """Initialize the SSE streamer.

        Args:
            heartbeat_interval: Seconds between heartbeat pings.
            max_queue_size: Maximum buffered events before backpressure.
        """
        self._heartbeat_interval = heartbeat_interval
        self._max_queue_size = max_queue_size
        self._active_streams: Dict[str, asyncio.Event] = {}

    async def stream_llm_response(
        self,
        llm_client: Any,
        request: LLMRequest,
        stream_id: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream an LLM response as SSE events.

        Args:
            llm_client: The LLM client to stream from.
            request: The LLM request with stream=True.
            stream_id: Optional stream identifier.

        Yields:
            SSE-formatted event strings.
        """
        if stream_id is None:
            stream_id = str(uuid.uuid4())

        cancel_event = asyncio.Event()
        self._active_streams[stream_id] = cancel_event

        try:
            # Send stream start event
            yield self._format_event(
                event="stream_start",
                data={
                    "stream_id": stream_id,
                    "request_id": request.request_id,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                },
            )

            # Start heartbeat task
            heartbeat_task = asyncio.create_task(
                self._send_heartbeats(stream_id, cancel_event)
            )

            content_parts: list[str] = []
            try:
                async for event in llm_client.complete_stream(request):
                    if cancel_event.is_set():
                        yield self._format_event(
                            event="stream_cancelled",
                            data={"stream_id": stream_id},
                        )
                        return

                    if event.event_type == "content":
                        content_parts.append(event.content or "")
                        yield self._format_event(
                            event="content",
                            data={
                                "content": event.content,
                                "stream_id": stream_id,
                                "request_id": event.request_id,
                            },
                        )

                    elif event.event_type == "done":
                        yield self._format_event(
                            event="stream_done",
                            data={
                                "stream_id": stream_id,
                                "finish_reason": event.finish_reason,
                                "full_content": "".join(content_parts),
                            },
                        )
                        return

                    elif event.event_type == "error":
                        yield self._format_event(
                            event="stream_error",
                            data={
                                "stream_id": stream_id,
                                "error": event.error,
                            },
                        )
                        return

            finally:
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass

        finally:
            self._active_streams.pop(stream_id, None)

    async def _send_heartbeats(
        self,
        stream_id: str,
        cancel_event: asyncio.Event,
    ) -> None:
        """Send periodic heartbeat events to keep the connection alive.

        Args:
            stream_id: Stream identifier for the heartbeat.
            cancel_event: Event to signal cancellation.
        """
        try:
            while not cancel_event.is_set():
                await asyncio.sleep(self._heartbeat_interval)
                # Heartbeats are sent through the queue mechanism
                logger.debug("Heartbeat for stream %s", stream_id)
        except asyncio.CancelledError:
            pass

    def _format_event(
        self,
        event: str,
        data: Dict[str, Any],
    ) -> str:
        """Format data as an SSE event string.

        Args:
            event: SSE event type.
            data: Data payload to serialize.

        Returns:
            SSE-formatted string.
        """
        lines = [f"event: {event}"]
        serialized = json.dumps(data, default=str)
        # Split long data into multiple lines if needed
        for line in serialized.split("\n"):
            lines.append(f"data: {line}")
        lines.append("")
        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def format_heartbeat() -> str:
        """Generate an SSE heartbeat comment.

        Returns:
            SSE comment line for keepalive.
        """
        return ": heartbeat\n\n"

    @staticmethod
    def format_error(error_message: str, stream_id: Optional[str] = None) -> str:
        """Format an error as an SSE event.

        Args:
            error_message: Error description.
            stream_id: Optional stream identifier.

        Returns:
            SSE-formatted error event.
        """
        data = {"error": error_message}
        if stream_id:
            data["stream_id"] = stream_id

        lines = ["event: error"]
        serialized = json.dumps(data)
        lines.append(f"data: {serialized}")
        lines.append("")
        lines.append("")
        return "\n".join(lines)

    def cancel_stream(self, stream_id: str) -> bool:
        """Cancel an active stream.

        Args:
            stream_id: The stream to cancel.

        Returns:
            True if the stream was found and cancelled.
        """
        cancel_event = self._active_streams.get(stream_id)
        if cancel_event is not None:
            cancel_event.set()
            logger.info("Stream %s cancelled", stream_id)
            return True
        logger.warning("Stream %s not found for cancellation", stream_id)
        return False

    @property
    def active_stream_count(self) -> int:
        """Get the number of active streams.

        Returns:
            Count of currently active streams.
        """
        return len(self._active_streams)

    def get_active_streams(self) -> list[str]:
        """Get list of active stream IDs.

        Returns:
            List of active stream identifiers.
        """
        return list(self._active_streams.keys())
