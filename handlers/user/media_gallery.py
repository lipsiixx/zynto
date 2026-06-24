"""Галерея медиафайлов собеседника."""
from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from database.queries import messages as messages_q
from keyboards.user_kb import media_gallery_kb
from services import media as media_service
from services import subscription as sub_service
from utils.formatters import fmt_dt, truncate, type_label
from utils.pagination import PAGE_SIZE, make_page

router = Router(name="user-media")


@router.callback_query(F.data.startswith("media:"))
async def cb_media(call: CallbackQuery, user: User, db: AsyncSession, bot: Bot) -> None:
    if not sub_service.has_active_subscription(user):
        await call.answer("🔒 Нужна активная подписка", show_alert=True)
        return
    _, chat_id_s, page_s = call.data.split(":")
    chat_id = int(chat_id_s)
    page = int(page_s)

    items, total = await messages_q.list_chat_media(
        db, user.telegram_id, chat_id, limit=PAGE_SIZE, offset=page * PAGE_SIZE
    )
    pg = make_page(page, total)

    await call.answer()
    if not items:
        await call.message.edit_text("📎 Медиафайлов нет.", reply_markup=media_gallery_kb(chat_id, 0, 1))
        return

    await call.message.edit_text(
        f"📎 <b>Медиафайлы</b> (стр. {pg.page + 1}/{pg.total_pages}, всего {total})\nОтправляю файлы…",
        reply_markup=media_gallery_kb(chat_id, pg.page, pg.total_pages),
    )

    for record in items:
        status = "🗑" if record.is_deleted else ("✏️" if record.is_edited else "📩")
        caption = f"{status} {type_label(record.message_type)} • {fmt_dt(record.received_at)}"
        if record.text_content:
            caption += f"\n{truncate(record.text_content)}"
        await media_service.send_media(bot, call.from_user.id, record, caption)
