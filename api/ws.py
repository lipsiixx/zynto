"""WebSocket и SSE эндпоинты для real-time событий."""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from api.auth import verify_token
from services import ws_broadcaster as broadcaster

logger = logging.getLogger(__name__)
router = APIRouter(tags=["realtime"])


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket, token: str = Query(...)) -> None:
    if not verify_token(token):
        await ws.close(code=1008, reason="unauthorized")
        return

    await ws.accept()
    q = broadcaster.subscribe()
    logger.debug("WS-клиент подключён")

    async def _sender() -> None:
        while True:
            msg = await q.get()
            await ws.send_text(msg)

    sender_task = asyncio.create_task(_sender())
    try:
        while True:
            await ws.receive_text()  # ждём pong / keepalive от клиента
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001
        pass
    finally:
        sender_task.cancel()
        broadcaster.unsubscribe(q)
        logger.debug("WS-клиент отключён")


@router.get("/events")
async def sse_endpoint(token: str = Query(...)) -> StreamingResponse:
    if not verify_token(token):
        return StreamingResponse(iter([]), status_code=401)

    async def _generator():
        q = broadcaster.subscribe()
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=25)
                    yield f"data: {msg}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            broadcaster.unsubscribe(q)

    return StreamingResponse(
        _generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
