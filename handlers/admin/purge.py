"""Команда /del — глобальная очистка старых сообщений (все пользователи, только админы).

Роутер уже гейтится AdminCheckMiddleware (main.py), доп. проверка прав здесь не нужна.
"""
from __future__ import annotations

import logging
import os

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from database.queries import purge as purge_q

logger = logging.getLogger(__name__)
router = Router(name="admin-purge")

_CONFIRM_CB = "a:purge_confirm"
_CANCEL_CB = "a:purge_cancel"


@router.message(Command("del"))
async def cmd_del(message: Message, db: AsyncSession) -> None:
    count = await purge_q.count_stale(db)
    if count == 0:
        await message.answer(
            f"Нечего удалять — записей старше {purge_q.PURGE_STALE_DAYS} дн. "
            "(без правок/удалений/one-view) не найдено."
        )
        return

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Да, удалить", callback_data=_CONFIRM_CB)
    kb.button(text="❌ Отмена", callback_data=_CANCEL_CB)
    kb.adjust(2)
    await message.answer(
        f"⚠️ Найдено <b>{count}</b> записей старше {purge_q.PURGE_STALE_DAYS} дн. "
        "(не изменённых, не удалённых, не one-view).\n"
        "Они будут удалены безвозвратно вместе с локальными файлами. Продолжить?",
        reply_markup=kb.as_markup(),
    )


@router.callback_query(F.data == _CANCEL_CB)
async def cb_purge_cancel(call: CallbackQuery) -> None:
    await call.message.edit_text("Отменено.")
    await call.answer()


@router.callback_query(F.data == _CONFIRM_CB)
async def cb_purge_confirm(call: CallbackQuery, db: AsyncSession) -> None:
    await call.answer("Удаляю…")
    await call.message.edit_text("⏳ Удаляю, подожди…")

    rows = await purge_q.fetch_stale_with_files(db)
    removed_files = 0
    freed_bytes = 0
    for _id, path in rows:
        if path and os.path.exists(path):
            try:
                freed_bytes += os.path.getsize(path)
                os.remove(path)
                removed_files += 1
            except OSError as exc:
                logger.warning("Не удалось удалить файл %s: %s", path, exc)

    removed_rows = await purge_q.delete_stale(db)
    freed_mb = freed_bytes / 1024**2

    admin_id = call.from_user.id if call.from_user else None
    logger.info(
        "/del: удалено записей=%s, файлов=%s, освобождено=%.2fМБ (admin=%s)",
        removed_rows, removed_files, freed_mb, admin_id,
    )
    await call.message.edit_text(
        f"✅ Удалено записей: <b>{removed_rows}</b>\n"
        f"Удалено файлов: <b>{removed_files}</b>\n"
        f"Освобождено места: <b>{freed_mb:.2f} МБ</b>"
    )
