"""Pub/sub для WebSocket-событий REST API.

Использует asyncio.Queue: каждый подключённый WS-клиент подписывается на очередь.
Когда бот генерирует событие — broadcast рассылает JSON всем подписчикам.
Если очередь переполнена (отстающий клиент) — подписчик отключается.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_listeners: set[asyncio.Queue[str]] = set()

_QUEUE_MAX = 200


def subscribe() -> asyncio.Queue[str]:
    q: asyncio.Queue[str] = asyncio.Queue(maxsize=_QUEUE_MAX)
    _listeners.add(q)
    return q


def unsubscribe(q: asyncio.Queue[str]) -> None:
    _listeners.discard(q)


async def broadcast(event: str, data: dict) -> None:
    if not _listeners:
        return
    msg = json.dumps(
        {"event": event, "data": data, "timestamp": datetime.now(timezone.utc).isoformat()},
        default=str,
    )
    dead: list[asyncio.Queue[str]] = []
    for q in list(_listeners):
        try:
            q.put_nowait(msg)
        except asyncio.QueueFull:
            logger.debug("WS-клиент отстаёт — отключаем")
            dead.append(q)
    for q in dead:
        _listeners.discard(q)
