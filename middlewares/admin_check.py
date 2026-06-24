"""AdminCheckMiddleware — допускает только активных админов."""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, User as TgUser

from database.queries import admins as admins_q


class AdminCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user: TgUser | None = data.get("event_from_user")
        db = data.get("db")
        if tg_user is None or db is None:
            return None

        admin = await admins_q.get_admin(db, tg_user.id)
        if admin is None or not admin.is_active:
            if isinstance(event, Message):
                await event.answer("⛔ У вас нет доступа.")
            elif isinstance(event, CallbackQuery):
                await event.answer("⛔ У вас нет доступа.", show_alert=True)
            return None

        data["admin"] = admin
        return await handler(event, data)
