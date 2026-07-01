"""Проверка обязательной подписки пользователя на канал (settings.required_channel).

Результат кэшируется в Redis на CACHE_TTL секунд — иначе пришлось бы дёргать
Telegram get_chat_member на каждое сообщение/уведомление.
"""
from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from redis.asyncio import Redis

from config import settings

logger = logging.getLogger(__name__)

CACHE_TTL = 300
_NOT_MEMBER_STATUSES = {"left", "kicked"}

_redis: Redis | None = None


def set_redis(redis: Redis | None) -> None:
    global _redis
    _redis = redis


async def is_subscribed(bot: Bot, user_id: int, *, force: bool = False) -> bool:
    cache_key = f"chsub:{user_id}"
    if _redis is not None and not force:
        try:
            cached = await _redis.get(cache_key)
        except Exception:  # noqa: BLE001
            cached = None
        if cached is not None:
            return cached == "1"

    subscribed = await _check_live(bot, user_id)

    if _redis is not None:
        try:
            await _redis.set(cache_key, "1" if subscribed else "0", ex=CACHE_TTL)
        except Exception:  # noqa: BLE001
            pass
    return subscribed


async def _check_live(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(f"@{settings.required_channel}", user_id)
    except TelegramAPIError as exc:
        # Бот не в канале / канал не найден / временная ошибка API — не блокируем
        # всех пользователей из-за проблемы конфигурации, только логируем.
        logger.warning("Не удалось проверить подписку на канал @%s: %s", settings.required_channel, exc)
        return True
    return member.status not in _NOT_MEMBER_STATUSES
