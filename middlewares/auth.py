"""AuthMiddleware — регистрация юзера, проверка бана и подписки.

Применяется только к обновлениям от реальных пользователей
(message / callback_query). Бизнес-обновления не трогает.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, User as TgUser

from database.queries import tariffs as tariffs_q
from database.queries import users as users_q
from keyboards.user_kb import tariffs_kb


class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user: TgUser | None = data.get("event_from_user")
        if tg_user is None or tg_user.is_bot:
            return await handler(event, data)

        db = data["db"]
        user = await users_q.get_or_create_user(
            db,
            telegram_id=tg_user.id,
            username=tg_user.username,
            full_name=tg_user.full_name,
            language_code=tg_user.language_code,
        )

        # Проверка бана
        if user.is_banned:
            text = "🚫 Вы заблокированы в этом боте."
            if user.ban_reason:
                text += f"\nПричина: {user.ban_reason}"
            if isinstance(event, Message):
                await event.answer(text)
            elif isinstance(event, CallbackQuery):
                await event.answer(text, show_alert=True)
            return None

        # Истечение подписки
        if (
            user.subscription_status == "active"
            and user.subscription_expires_at is not None
            and user.subscription_expires_at < datetime.now(timezone.utc)
        ):
            await users_q.update_subscription_fields(db, user.telegram_id, "expired", user.subscription_expires_at)
            user.subscription_status = "expired"
            if isinstance(event, Message):
                tariff_list = await tariffs_q.list_tariffs(db, only_active=True)
                await event.answer(
                    "😔 <b>Ваша подписка истекла.</b> Оформите новую и возвращайтесь!",
                    reply_markup=tariffs_kb(tariff_list, prefix="buy"),
                )

        data["user"] = user
        return await handler(event, data)
