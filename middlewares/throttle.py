"""ThrottleMiddleware — антифлуд через Redis (1 запрос/сек на пользователя)."""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject, User as TgUser
from redis.asyncio import Redis


class ThrottleMiddleware(BaseMiddleware):
    def __init__(self, redis: Redis | None, rate_limit: float = 1.0) -> None:
        self.redis = redis
        self.rate_limit = rate_limit

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if self.redis is None:
            return await handler(event, data)

        # Никогда не throttl'им оплату — потеря этого апдейта недопустима
        if isinstance(event, Message) and event.successful_payment is not None:
            return await handler(event, data)

        tg_user: TgUser | None = data.get("event_from_user")
        if tg_user is None:
            return await handler(event, data)

        key = f"throttle:{tg_user.id}"
        try:
            # SET key 1 NX EX/ PX — если ключ уже есть, значит лимит превышен
            ok = await self.redis.set(key, 1, nx=True, px=int(self.rate_limit * 1000))
        except Exception:  # noqa: BLE001  — Redis недоступен, не блокируем
            return await handler(event, data)

        if not ok:
            # Тихо игнорируем апдейт
            return None
        return await handler(event, data)
