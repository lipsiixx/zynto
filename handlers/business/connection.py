"""Обработка business_connection: подключение/отключение бизнес-аккаунта."""
from __future__ import annotations

import logging

from aiogram import Bot, Router
from aiogram.types import BusinessConnection
from sqlalchemy.ext.asyncio import AsyncSession

from database.queries import business as business_q
from database.queries import users as users_q

logger = logging.getLogger(__name__)
router = Router(name="business-connection")


@router.business_connection()
async def on_business_connection(event: BusinessConnection, db: AsyncSession, bot: Bot) -> None:
    owner = event.user
    bc_id = event.id
    is_enabled = bool(event.is_enabled)

    # Убедимся, что владелец есть в users
    await users_q.get_or_create_user(
        db,
        telegram_id=owner.id,
        username=owner.username,
        full_name=owner.full_name,
        language_code=owner.language_code,
    )

    await business_q.upsert_connection(db, owner.id, bc_id, is_enabled)

    if is_enabled:
        logger.info("Бизнес-аккаунт подключён: user=%s bc=%s", owner.id, bc_id)
        text = (
            "✅ <b>Мониторинг подключён!</b> Теперь я слежу за твоей перепиской "
            "и сообщу, если кто-то удалит или изменит сообщение."
        )
    else:
        logger.info("Бизнес-аккаунт отключён: user=%s bc=%s", owner.id, bc_id)
        text = "⚠️ <b>Мониторинг отключён.</b> Ты убрал бота из бизнес-настроек."

    try:
        await bot.send_message(owner.id, text)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Не удалось уведомить владельца %s: %s", owner.id, exc)
