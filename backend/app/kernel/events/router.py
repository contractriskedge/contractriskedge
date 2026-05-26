"""Real-time event router — WebSocket endpoint for live operational updates.

Provides:
- /api/v1/ws/events — WebSocket connection for real-time events
- /api/v1/ws/health — Health check for the event system
"""

from __future__ import annotations

import asyncio
import json
import logging
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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["Real-time Events"])


@router.websocket("/events")
async def websocket_events(websocket: WebSocket):
    """WebSocket endpoint for real-time operational events.

    Client must send an auth token as a query parameter or first message.
    Connection is tagged with tenant_id for isolation.

    Events received:
    - notification.created
    - job.updated
    - job.completed
    - review.status_changed
    - upload.completed
    - ai.completed
    - recommendation.created

    Usage:
        const ws = new WebSocket(`ws://localhost:8000/api/v1/ws/events`);

        // Send auth on connect
        ws.onopen = () => ws.send(JSON.stringify({
            type: "auth",
            token: "your-jwt-token"
        }));

        ws.onmessage = (event) => {
            const { type, data } = JSON.parse(event.data);
        };
    """
    tenant_id = "unknown"
    authenticated = False

    try:
        # Accept the connection immediately
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

        # Send confirmation
        await websocket.send_json({
            "type": "connected",
            "data": {
                "tenant_id": tenant_id[:8] + "...",
                "timestamp": time.time(),
            },
        })

        # Keep connection alive, handle incoming messages
        while True:
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                msg = json.loads(raw)
                # Handle ping/pong for keepalive
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                # Send heartbeat
                try:
                    await websocket.send_json({"type": "heartbeat"})
                except Exception:
                    break

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: tenant=%s", tenant_id[:8])
    except Exception as exc:
        logger.error("WebSocket error: %s", exc)
    finally:
        if authenticated:
            await event_manager.disconnect(websocket, tenant_id)


@router.get("/health")
async def websocket_health():
    """Health check for the real-time event system."""
    return JSONResponse(await event_manager.health_check())
