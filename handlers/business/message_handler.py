"""Перехват business_message — сохраняем КАЖДОЕ сообщение (вкл. исходящие)."""
from __future__ import annotations

import logging

from aiogram import Bot, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from database.queries import business as business_q
from database.queries import messages as messages_q
from database.queries import users as users_q
from handlers.business.extract import chat_title, extract
from services import media as media_service
from services import subscription as sub_service

logger = logging.getLogger(__name__)
router = Router(name="business-message")


async def _heal_connection(db: AsyncSession, bot: Bot, bc_id: str):
    """Если записи о подключении нет (потерян одноразовый business_connection-апдейт),
    дозапрашиваем её у Telegram и сохраняем — система самовосстанавливается."""
    try:
        info = await bot.get_business_connection(bc_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Не удалось дозапросить business_connection %s: %s", bc_id, exc)
        return None
    owner_tg = info.user
    await users_q.get_or_create_user(
        db,
        telegram_id=owner_tg.id,
        username=owner_tg.username,
        full_name=owner_tg.full_name,
        language_code=owner_tg.language_code,
    )
    conn = await business_q.upsert_connection(db, owner_tg.id, bc_id, bool(info.is_enabled))
    logger.info("Подключение восстановлено из API: user=%s bc=%s active=%s", owner_tg.id, bc_id, conn.is_active)
    return conn


async def resolve_owner(db: AsyncSession, bc_id: str, bot: Bot | None = None) -> User | None:
    """Возвращает владельца бизнес-аккаунта по business_connection_id, если подписка активна.

    Если записи о подключении нет, а `bot` передан — пытается восстановить её через API
    (на случай потерянного апдейта business_connection)."""
    conn = await business_q.get_by_connection_id(db, bc_id)
    if conn is None and bot is not None:
        conn = await _heal_connection(db, bot, bc_id)
    if conn is None or not conn.is_active:
        return None
    owner = await users_q.get_user(db, conn.user_id)
    if owner is None or not sub_service.has_active_subscription(owner):
        return None
    return owner


async def _try_heal_media_from_reply(
    db: AsyncSession, bot: Bot, owner, reply_msg: Message
) -> None:
    """Пытаемся скачать медиа из reply_to_message.

    Актуально для одноразовых (view-once) фото/видео: при первом получении
    Telegram не отдаёт боту файл, но при ответе на такое сообщение передаёт
    оригинал в поле reply_to_message с доступным file_id.
    """
    data = extract(reply_msg)
    logger.debug(
        "reply_to_message: msg_id=%s type=%s file_id=%s",
        reply_msg.message_id, data.message_type,
        (data.file_id or "")[:30] if data.file_id else "нет",
    )
    if not data.file_id or not data.file_unique_id:
        logger.info(
            "reply_to_message без медиа (msg_id=%s type=%s) — view-once не перехвачено",
            reply_msg.message_id, data.message_type,
        )
        return
    record = await messages_q.find_message(
        db, owner.telegram_id, reply_msg.chat.id, reply_msg.message_id
    )
    if record is None:
        logger.debug("reply_to_message msg_id=%s не найдено в БД", reply_msg.message_id)
        return
    if record.local_path is not None:
        return  # медиа уже скачано ранее
    logger.info(
        "Пытаемся восстановить view-once медиа: user=%s msg_id=%s type=%s",
        owner.telegram_id, reply_msg.message_id, data.message_type,
    )
    local_path = await media_service.get_or_cache_media(
        bot, db, data.file_id, data.file_unique_id,
        data.message_type, data.file_size, data.mime_type
    )
    if local_path:
        await messages_q.update_media_fields(
            db, record,
            file_id=data.file_id,
            file_unique_id=data.file_unique_id,
            message_type=data.message_type,
            local_path=local_path,
            file_size=data.file_size,
            mime_type=data.mime_type,
            width=data.width,
            height=data.height,
        )
        logger.info(
            "Медиа восстановлено из контекста ответа: user=%s msg_id=%s type=%s",
            owner.telegram_id, reply_msg.message_id, data.message_type,
        )
        from services.notifier import get_notifier
        await get_notifier().notify_one_time_captured(owner.telegram_id, record)
    else:
        logger.warning(
            "Не удалось скачать view-once медиа из reply_to_message: user=%s msg_id=%s",
            owner.telegram_id, reply_msg.message_id,
        )


@router.business_message()
async def on_business_message(message: Message, db: AsyncSession, bot: Bot) -> None:
    bc_id = message.business_connection_id
    if not bc_id:
        return
    owner = await resolve_owner(db, bc_id, bot)
    if owner is None:
        return

    sender = message.from_user
    bot_id = int(bot.token.split(":")[0])
    if sender and sender.id == bot_id:
        return

    data = extract(message)
    logger.debug(
        "business_message: user=%s chat=%s msg=%s type=%s file_id=%s has_photo=%s has_video=%s",
        owner.telegram_id, message.chat.id, message.message_id,
        data.message_type,
        (data.file_id or "")[:20] if data.file_id else "нет",
        bool(message.photo),
        bool(message.video),
    )

    local_path = None
    if data.file_id and data.file_unique_id:
        local_path = await media_service.get_or_cache_media(
            bot, db, data.file_id, data.file_unique_id, data.message_type, data.file_size, data.mime_type
        )

    is_outgoing = bool(sender and sender.id == owner.telegram_id)

    await messages_q.save_message(
        db,
        user_id=owner.telegram_id,
        business_connection_id=bc_id,
        message_id=message.message_id,
        chat_id=message.chat.id,
        chat_title=chat_title(message),
        sender_id=sender.id if sender else None,
        sender_name=sender.full_name if sender else None,
        sender_username=sender.username if sender else None,
        is_outgoing=is_outgoing,
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

    # Если это ответ на сообщение — пытаемся подтянуть медиа, которое не удалось
    # скачать при первом получении (view-once фото/видео).
    if message.reply_to_message:
        await _try_heal_media_from_reply(db, bot, owner, message.reply_to_message)
    # Никаких уведомлений при обычном получении — только при удалении/изменении.
