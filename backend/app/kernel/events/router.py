"""Real-time event router — WebSocket endpoint for live operational updates.

Provides:
- /api/v1/ws/events — WebSocket connection for real-time events
- /api/v1/ws/health — Health check for the event system

Security:
- JWT authentication required on connect (token in first message or query param)
- Origin validation against allowed CORS origins
- Tenant isolation: connections tagged by tenant_id
- Idle timeout: connections closed after 60s of inactivity
- Rate limiting: max 100 messages per minute per connection
- Message schema validation: all client messages validated against schema
- Reconnect storm detection: exponential backoff enforced

Delivery Protocol:
- All events include a ``sequence_id`` for ordering
- Clients should send ``{ type: "ack", event_id: "..." }`` to acknowledge delivery
- On reconnect, clients can send ``{ type: "replay", last_sequence_id: 123 }``
  to receive missed events from the outbox
- Server sends ``{ type: "heartbeat" }`` every 30 seconds for keepalive
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from app.kernel.events.realtime import event_manager
from app.kernel.security.auth import JWTValidator
from app.config import settings

# Initialize JWT validator for WebSocket auth
_jwt_validator = JWTValidator(
    domain=settings.auth0_domain,
    audience=settings.auth0_audience,
    issuer=settings.auth0_issuer or f"https://{settings.auth0_domain}/",
    dev_secret=settings.secret_key,
    environment=settings.environment,
)

# Allowed origins for WebSocket connections
ALLOWED_ORIGINS = set(settings.cors_origins or [
    "http://localhost:3000",
    "https://app.contractriskedge.com",
])

# Message rate limiting: max messages per minute per connection
MAX_MESSAGES_PER_MINUTE = 100

# Idle timeout: close connection after this many seconds with no client message
IDLE_TIMEOUT_SECONDS = 60

# Valid client message schemas
VALID_CLIENT_MESSAGES = {
    "auth": {"required": ["type", "token"], "optional": ["last_sequence_id"]},
    "ack": {"required": ["type", "event_id"]},
    "replay": {"required": ["type", "last_sequence_id"]},
    "ping": {"required": ["type"]},
    "subscribe": {"required": ["type"], "optional": ["topics"]},
    "pong": {"required": ["type"]},
}

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["Real-time Events"])


def _validate_origin(websocket: WebSocket) -> bool:
    """Validate the WebSocket origin against allowed origins."""
    origin = websocket.headers.get("origin", websocket.headers.get("sec-websocket-origin", ""))
    if not origin:
        # Allow connections without origin header (internal clients)
        return True
    # Check exact match or wildcard subdomain match
    for allowed in ALLOWED_ORIGINS:
        if origin == allowed:
            return True
        if allowed.startswith("*.") and origin.endswith(allowed[1:]):
            return True
    logger.warning("WebSocket connection rejected: invalid origin %s", origin)
    return False


def _validate_message_schema(msg: dict) -> tuple[bool, str]:
    """Validate client message against known schemas."""
    msg_type = msg.get("type", "")
    schema = VALID_CLIENT_MESSAGES.get(msg_type)
    if not schema:
        return False, f"Unknown message type: {msg_type}"

    for field in schema["required"]:
        if field not in msg:
            return False, f"Missing required field '{field}' in {msg_type} message"

    # Validate field types
    if msg_type == "auth":
        if not isinstance(msg.get("token"), str) or len(msg["token"]) < 10:
            return False, "Invalid token format"
    if msg_type == "ack":
        if not isinstance(msg.get("event_id"), str):
            return False, "Invalid event_id format"
    if msg_type == "replay":
        if not isinstance(msg.get("last_sequence_id"), (int, float)):
            return False, "Invalid last_sequence_id format"

    return True, ""


@router.websocket("/events")
async def websocket_events(websocket: WebSocket):
    """WebSocket endpoint for real-time operational events.

    Client must send an auth token as a query parameter or first message.
    Connection is tagged with tenant_id for isolation.

    Security:
    - Origin validation against allowed CORS origins
    - JWT authentication required
    - Tenant isolation enforced
    - Rate limited (100 msg/min)
    - Idle timeout (60s)
    - Message schema validation

    Events received:
    - notification.created
    - job.updated
    - job.completed
    - review.status_changed
    - upload.completed
    - ai.completed
    - recommendation.created
    - recovery.action_taken
    - recovery.review_flagged
    - recovery.review_assigned
    - recovery.max_escalation_reached
    - recovery.cooldown_active

    Client messages:
    - ``{ type: "auth", token: "..." }`` — Authentication (required first message)
    - ``{ type: "ack", event_id: "..." }`` — Acknowledge event delivery
    - ``{ type: "replay", last_sequence_id: 123 }`` — Request replay of missed events
    - ``{ type: "ping" }`` — Keepalive ping (server responds with pong)
    - ``{ type: "subscribe", topics: [...] }`` — Subscribe to specific event types
    """
    tenant_id = "unknown"
    authenticated = False
    last_sequence_id = 0
    message_count = 0
    rate_limit_reset = time.time() + 60
    last_client_message = time.time()

    # Origin validation
    if not _validate_origin(websocket):
        await websocket.close(4001)
        return

    try:
        await websocket.accept()

        # Wait for auth message
        try:
            raw = await asyncio.wait_for(websocket.receive_text(), timeout=10)
            msg = json.loads(raw)
        except (asyncio.TimeoutError, json.JSONDecodeError):
            await websocket.send_json({"type": "error", "data": {"message": "Authentication required. Send { type: 'auth', token: '...' }"}})
            await websocket.close(4001)
            return

        # Verify token
        if msg.get("type") == "auth" and msg.get("token"):
            try:
                user_context = await _jwt_validator.validate(msg["token"])
                if user_context and user_context.tenant_id:
                    tenant_id = user_context.tenant_id
                    authenticated = True
                else:
                    await websocket.send_json({"type": "error", "data": {"message": "Invalid token: no tenant context"}})
                    await websocket.close(4001)
                    return
            except Exception as auth_err:
                await websocket.send_json({"type": "error", "data": {"message": f"Authentication failed: {auth_err}"}})
                await websocket.close(4001)
                return
        else:
            await websocket.send_json({"type": "error", "data": {"message": "Auth message must be { type: 'auth', token: '...' }"}})
            await websocket.close(4001)
            return

        # Register connection
        await event_manager.connect(websocket, tenant_id)

        # Send confirmation with server timestamp for clock skew estimation
        await websocket.send_json({
            "type": "connected",
            "data": {
                "tenant_id": tenant_id[:8] + "...",
                "server_time": time.time(),
                "protocol_version": 1,
            },
        })

        # Record reconnect (this is a reconnecting client if they have a sequence_id)
        if msg.get("last_sequence_id"):
            event_manager.record_reconnect(tenant_id)

        # Check for replay request in the auth message
        if msg.get("last_sequence_id"):
            await _send_replay_events(websocket, tenant_id, msg["last_sequence_id"])

        # Keep connection alive, handle incoming messages
        while True:
            try:
                # Idle timeout check
                idle_seconds = time.time() - last_client_message
                if idle_seconds > IDLE_TIMEOUT_SECONDS:
                    await websocket.send_json({
                        "type": "error",
                        "data": {"message": f"Connection closed due to inactivity ({IDLE_TIMEOUT_SECONDS}s timeout)"},
                    })
                    await websocket.close(4002)
                    return

                raw = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                last_client_message = time.time()

                # Rate limiting
                message_count += 1
                if time.time() > rate_limit_reset:
                    message_count = 0
                    rate_limit_reset = time.time() + 60
                if message_count > MAX_MESSAGES_PER_MINUTE:
                    await websocket.send_json({
                        "type": "error",
                        "data": {"message": f"Rate limit exceeded: max {MAX_MESSAGES_PER_MINUTE} messages per minute"},
                    })
                    await websocket.close(4003)
                    return

                # Parse and validate message
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    await websocket.send_json({
                        "type": "error",
                        "data": {"message": "Invalid JSON message format"},
                    })
                    continue

                # Schema validation
                is_valid, error_msg = _validate_message_schema(msg)
                if not is_valid:
                    await websocket.send_json({
                        "type": "error",
                        "data": {"message": error_msg},
                    })
                    continue

                msg_type = msg.get("type", "")

                if msg_type == "ping":
                    await websocket.send_json({"type": "pong", "server_time": time.time()})

                elif msg_type == "ack":
                    # Client acknowledged an event — record delivery
                    event_id = msg.get("event_id")
                    if event_id:
                        logger.debug("Event acknowledged: %s (tenant=%s)", event_id[:8], tenant_id[:8])

                elif msg_type == "replay":
                    # Client requesting replay of missed events
                    last_seq = msg.get("last_sequence_id", 0)
                    event_manager.record_reconnect(tenant_id)
                    await _send_replay_events(websocket, tenant_id, last_seq)

                elif msg_type == "subscribe":
                    # Client subscribing to specific event types
                    topics = msg.get("topics", [])
                    event_manager.set_subscriptions(websocket, topics)
                    await websocket.send_json({
                        "type": "subscribed",
                        "data": {
                            "topics": topics if topics else ["* (all)"],
                            "server_time": time.time(),
                        },
                    })
                    logger.debug(
                        "Client subscribed to topics: %s (tenant=%s)",
                        topics if topics else ["*"], tenant_id[:8],
                    )

            except asyncio.TimeoutError:
                # Send heartbeat to detect stale connections
                try:
                    await websocket.send_json({"type": "heartbeat", "server_time": time.time()})
                except Exception:
                    break

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: tenant=%s", tenant_id[:8])
    except Exception as exc:
        logger.error("WebSocket error: %s", exc)
    finally:
        if authenticated:
            await event_manager.disconnect(websocket, tenant_id)


async def _send_replay_events(websocket: WebSocket, tenant_id: str, last_sequence_id: int) -> None:
    """Replay missed events from the outbox for a reconnecting client.

    Queries the event_outbox table for events after the given sequence_id
    and sends them to the client. This ensures no events are lost during
    temporary disconnections.

    The outbox table provides:
    - Durable event storage (events survive server restarts)
    - Monotonic sequence IDs for cursor-based replay
    - Ordered delivery (events are replayed in creation order)
    """
    try:
        from app.kernel.database.session import TenantAwareSessionFactory
        from app.kernel.database.session import db_session_factory
        from app.kernel.events.outbox import OutboxRepository

        factory = db_session_factory
        session = await factory.create_session(
            tenant_id=tenant_id,
            user_id="system",
            user_role="admin",
        )
        try:
            outbox = OutboxRepository(session)
            # Get events after the client's last seen sequence
            from app.kernel.events.outbox import OutboxEvent
            from sqlalchemy import select

            result = await session.execute(
                select(OutboxEvent)
                .where(
                    OutboxEvent.tenant_id == tenant_id,
                    OutboxEvent.sequence_id > last_sequence_id,
                    OutboxEvent.delivery_state.in_(["pending", "delivered"]),
                )
                .order_by(OutboxEvent.sequence_id.asc())
                .limit(200)
            )
            events = list(result.scalars().all())

            if events:
                await websocket.send_json({
                    "type": "replay_start",
                    "data": {
                        "count": len(events),
                        "from_sequence": last_sequence_id,
                        "to_sequence": events[-1].sequence_id,
                    },
                })

                for event in events:
                    await websocket.send_json({
                        "type": event.event_type,
                        "event_id": str(event.event_id),
                        "event_version": event.event_version or "1.0",
                        "sequence_id": event.sequence_id,
                        "data": event.payload,
                        "timestamp": event.created_at.isoformat() if event.created_at else time.time(),
                        "replayed": True,
                    })

                await websocket.send_json({
                    "type": "replay_complete",
                    "data": {"count": len(events)},
                })

                # Record replay metrics
                event_manager.record_replay(tenant_id, len(events))

                logger.info(
                    "Replayed %d missed events to tenant %s (from seq %d)",
                    len(events), tenant_id[:8], last_sequence_id,
                )
        finally:
            await session.close()
    except Exception as exc:
        logger.warning("Failed to replay events for tenant %s: %s", tenant_id[:8], exc)
        await websocket.send_json({
            "type": "replay_error",
            "data": {"message": "Failed to replay missed events", "error": str(exc)},
        })


@router.get("/health")
async def websocket_health():
    """Health check for the real-time event system."""
    return JSONResponse(await event_manager.health_check())
