"""Просмотр истории удалённых/изменённых сообщений и поиск."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from database.queries import messages as messages_q
from keyboards.user_kb import (
    back_to_menu,
    chat_events_kb,
    history_chats_kb,
)
from services import subscription as sub_service
from states.user_states import SearchHistoryStates
from utils.formatters import esc, fmt_dt, truncate, type_label
from utils.pagination import PAGE_SIZE, make_page

router = Router(name="user-history")

NO_SUB = "🔒 История доступна только при активной подписке."


def _require_sub(user: User) -> bool:
    return sub_service.has_active_subscription(user)


async def _safe_edit(message: Message, text: str, reply_markup) -> None:
    """edit_text, который не падает, если контент не изменился (повторное нажатие)."""
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise


async def _render_chats(message: Message, user: User, db: AsyncSession, page: int, edit: bool) -> None:
    chats = await messages_q.list_chats_with_events(db, user.telegram_id)
    if not chats:
        text = "📋 Пока нет удалённых или изменённых сообщений."
        if edit:
            await _safe_edit(message, text, back_to_menu())
        else:
            await message.answer(text, reply_markup=back_to_menu())
        return

    pg = make_page(page, len(chats))
    page_items = chats[pg.offset:pg.offset + pg.limit]
    text = f"📋 <b>Собеседники с событиями</b> (стр. {pg.page + 1}/{pg.total_pages})"
    markup = history_chats_kb(page_items, pg.page, pg.total_pages)
    if edit:
        await _safe_edit(message, text, markup)
    else:
        await message.answer(text, reply_markup=markup)


@router.callback_query(F.data == "history")
async def cb_history(call: CallbackQuery, user: User, db: AsyncSession) -> None:
    if not _require_sub(user):
        await call.message.edit_text(NO_SUB, reply_markup=back_to_menu())
        await call.answer()
        return
    await _render_chats(call.message, user, db, 0, edit=True)
    await call.answer()


@router.callback_query(F.data.startswith("histpage:"))
async def cb_histpage(call: CallbackQuery, user: User, db: AsyncSession) -> None:
    page = int(call.data.split(":", 1)[1])
    await _render_chats(call.message, user, db, page, edit=True)
    await call.answer()


def _event_line(record) -> str:
    if record.is_deleted:
        tag = "🗑 Удалено"
        when = fmt_dt(record.deleted_at)
    elif record.is_edited:
        tag = "✏️ Изменено"
        when = fmt_dt(record.edited_at)
    else:
        tag = "📩"
        when = fmt_dt(record.received_at)

    if record.file_id:
        content = type_label(record.message_type)
        if record.text_content:
            content += f": {truncate(record.text_content)}"
    else:
        content = truncate(record.text_content) or "—"

    line = f"<b>{tag}</b> • {when}\n{esc(content)}"
    if record.is_edited and record.original_text:
        line += f"\n  ↳ было: {esc(truncate(record.original_text))}"
    return line


@router.callback_query(F.data.startswith("chat:"))
async def cb_chat(call: CallbackQuery, user: User, db: AsyncSession) -> None:
    if not _require_sub(user):
        await call.answer(NO_SUB, show_alert=True)
        return
    _, chat_id_s, page_s, flt = call.data.split(":")
    chat_id = int(chat_id_s)
    page = int(page_s)

    events, total = await messages_q.list_chat_events(
        db, user.telegram_id, chat_id, flt=flt, limit=PAGE_SIZE, offset=page * PAGE_SIZE
    )
    pg = make_page(page, total)

    if not events:
        body = "Нет событий по выбранному фильтру."
    else:
        body = "\n\n".join(_event_line(e) for e in events)

    header = f"💬 <b>События</b> (стр. {pg.page + 1}/{pg.total_pages}, всего {total})\n\n"
    await _safe_edit(call.message, header + body, chat_events_kb(chat_id, pg.page, pg.total_pages, flt))
    await call.answer()


@router.callback_query(F.data.startswith("search:"))
async def cb_search(call: CallbackQuery, state: FSMContext) -> None:
    chat_id = int(call.data.split(":", 1)[1])
    await state.set_state(SearchHistoryStates.waiting_query)
    await state.update_data(chat_id=chat_id)
    await call.message.answer("🔍 Введи текст для поиска:")
    await call.answer()


@router.message(SearchHistoryStates.waiting_query)
async def on_search_query(message: Message, user: User, db: AsyncSession, state: FSMContext) -> None:
    data = await state.get_data()
    chat_id = data.get("chat_id")
    await state.clear()
    if chat_id is None:
        await message.answer("Что-то пошло не так, попробуй снова.")
        return
    results = await messages_q.search_text(db, user.telegram_id, chat_id, message.text.strip())
    if not results:
        await message.answer("Ничего не найдено.", reply_markup=back_to_menu())
        return
    body = "\n\n".join(_event_line(r) for r in results)
    await message.answer(f"🔍 <b>Результаты поиска:</b>\n\n{body}", reply_markup=back_to_menu())
