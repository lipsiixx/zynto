"""ConcurrencyLimitMiddleware — ограничивает число одновременно обрабатываемых апдейтов.

aiogram Dispatcher обрабатывает апдейты конкурентно без встроенного лимита. При всплеске
(например, сотни business_message почти одновременно) это может исчерпать пулы Redis/БД
раньше, чем помогут увеличенные лимиты пулов. Семафор — простой backpressure: лишние
апдейты просто ждут своей очереди вместо того, чтобы разом хватать соединения.
"""
from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject


class ConcurrencyLimitMiddleware(BaseMiddleware):
    def __init__(self, limit: int = 25) -> None:
        self._semaphore = asyncio.Semaphore(limit)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with self._semaphore:
            return await handler(event, data)
