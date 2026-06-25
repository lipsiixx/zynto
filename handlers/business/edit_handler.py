"""Обработка edited_business_message."""
from __future__ import annotations

import logging

from aiogram import Bot, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.queries import messages as messages_q
from handlers.business.extract import chat_title, extract
from handlers.business.message_handler import resolve_owner
from services import media as media_service
from services.notifier import get_notifier

logger = logging.getLogger(__name__)
router = Router(name="business-edit")


@router.edited_business_message()
async def on_edited_business_message(message: Message, db: AsyncSession, bot: Bot) -> None:
    bc_id = message.business_connection_id
    if not bc_id:
        return
    owner = await resolve_owner(db, bc_id, bot)
    if owner is None:
        return

    # Собственное (исходящее) сообщение владельца — не уведомляем его о своей же правке.
    author = message.from_user
    if author and author.id == owner.telegram_id:
        return

    data = extract(message)
    record = await messages_q.find_message(db, owner.telegram_id, message.chat.id, message.message_id)

    if record is None:
        # Запись не найдена — создаём сразу как изменённую
        sender = message.from_user
        local_path = None
        if data.file_id and data.file_unique_id:
            local_path = await media_service.get_or_cache_media(
                bot, db, data.file_id, data.file_unique_id, data.message_type, data.file_size, data.mime_type
            )
        record = await messages_q.save_message(
            db,
            user_id=owner.telegram_id,
            business_connection_id=bc_id,
            message_id=message.message_id,
            chat_id=message.chat.id,
            chat_title=chat_title(message),
            sender_id=sender.id if sender else None,
            sender_name=sender.full_name if sender else None,
            sender_username=sender.username if sender else None,
            is_outgoing=bool(sender and sender.id == owner.telegram_id),
            message_type=data.message_type,
            text_content=data.text_content,
            file_id=data.file_id,
            file_unique_id=data.file_unique_id,
            file_size=data.file_size,
            local_path=local_path,
            mime_type=data.mime_type,
            duration_seconds=data.duration_seconds,
            width=data.width,
            height=data.height,
        )
        record.is_edited = True
        record.edit_count = 1
        await db.commit()
    else:
        await messages_q.mark_edited(db, record, data.text_content)

    logger.info(
        "Изменено: user=%s chat=%s msg=%s", owner.telegram_id, message.chat.id, message.message_id
    )
    await get_notifier().notify_edited(owner.telegram_id, record)
