"""ChannelSubscriptionMiddleware — гейт: бот не отвечает, пока владелец не подписан
на обязательный канал (settings.required_channel)."""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware, Bot
from aiogram.types import CallbackQuery, Message, TelegramObject

from database.models import User
from keyboards.user_kb import require_channel_kb
from services.channel_sub import is_subscribed

REQUIRED_TEXT = (
    "🔒 <b>Бот не будет работать, пока вы не подпишетесь на канал.</b>\n\n"
    "Подпишитесь и нажмите «✅ Я подписался»."
)

# Колбэки самой проверки подписки должны проходить всегда — иначе кнопку
# "Я подписался" будет невозможно нажать.
_EXEMPT_PREFIXES = ("checksub", "subchk:")


class ChannelSubscriptionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("user")
        if user is None:
            return await handler(event, data)

        if isinstance(event, CallbackQuery) and event.data and event.data.startswith(_EXEMPT_PREFIXES):
            return await handler(event, data)

        bot: Bot = data["bot"]
        if await is_subscribed(bot, user.telegram_id):
            return await handler(event, data)

        kb = require_channel_kb()
        if isinstance(event, Message):
            await event.answer(REQUIRED_TEXT, reply_markup=kb)
        elif isinstance(event, CallbackQuery):
            await event.answer()
            if event.message:
                await event.message.answer(REQUIRED_TEXT, reply_markup=kb)
        return None
