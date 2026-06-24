"""Обработка deleted_business_messages."""
from __future__ import annotations

import logging

from aiogram import Bot, Router
from aiogram.types import BusinessMessagesDeleted
from sqlalchemy.ext.asyncio import AsyncSession

from database.queries import messages as messages_q
from handlers.business.message_handler import resolve_owner
from services.notifier import get_notifier

logger = logging.getLogger(__name__)
router = Router(name="business-delete")


@router.deleted_business_messages()
async def on_deleted_business_messages(
    event: BusinessMessagesDeleted, db: AsyncSession, bot: Bot
) -> None:
    bc_id = event.business_connection_id
    owner = await resolve_owner(db, bc_id, bot)
    if owner is None:
        return

    chat_id = event.chat.id
    notifier = get_notifier()

    for message_id in event.message_ids:
        record = await messages_q.find_message(db, owner.telegram_id, chat_id, message_id)
        if record is None:
            continue  # сообщение пришло до подключения бота
        await messages_q.mark_deleted(db, record)
        logger.info("Удалено: user=%s chat=%s msg=%s", owner.telegram_id, chat_id, message_id)
        await notifier.notify_deleted(owner.telegram_id, record)
