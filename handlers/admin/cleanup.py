"""Настройки автоочистки — только суперадмин."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings as cfg
from database.models import Admin
from database.queries import settings as settings_q
from keyboards.admin_kb import cleanup_kb
from states.admin_states import CleanupSettingsStates

router = Router(name="admin-cleanup")


def _retention(days: int) -> str:
    return "вечно" if days == 0 else f"{days} дн."


async def _text(db: AsyncSession) -> str:
    text_days = await settings_q.get_int_setting(db, "text_retention_days", cfg.text_retention_days)
    media_days = await settings_q.get_int_setting(db, "media_retention_days", cfg.media_retention_days)
    return (
        "⚙️ <b>Настройки автоочистки</b>\n\n"
        f"• Тексты хранятся: {_retention(text_days)}\n"
        f"• Медиафайлы хранятся: {_retention(media_days)}"
    )


@router.callback_query(F.data == "a:cleanup")
async def cb_cleanup(call: CallbackQuery, db: AsyncSession, admin: Admin) -> None:
    if not admin.is_superadmin:
        await call.answer("Только для суперадмина", show_alert=True)
        return
    await call.message.edit_text(await _text(db), reply_markup=cleanup_kb())
    await call.answer()


@router.callback_query(F.data == "a:cleanup_text")
async def cb_text(call: CallbackQuery, admin: Admin, state: FSMContext) -> None:
    if not admin.is_superadmin:
        await call.answer("Только для суперадмина", show_alert=True)
        return
    await state.set_state(CleanupSettingsStates.waiting_text_days)
    await call.message.answer("Введи количество дней хранения текстов (0 = хранить вечно):")
    await call.answer()


@router.callback_query(F.data == "a:cleanup_media")
async def cb_media(call: CallbackQuery, admin: Admin, state: FSMContext) -> None:
    if not admin.is_superadmin:
        await call.answer("Только для суперадмина", show_alert=True)
        return
    await state.set_state(CleanupSettingsStates.waiting_media_days)
    await call.message.answer("Введи количество дней хранения медиа (0 = хранить вечно):")
    await call.answer()


async def _save(message: Message, db: AsyncSession, key: str, state: FSMContext) -> None:
    try:
        days = int(message.text.strip())
        if days < 0:
            raise ValueError
    except ValueError:
        await message.answer("Нужно неотрицательное число. Попробуй ещё раз:")
        return
    await settings_q.set_setting(db, key, str(days), updated_by=message.from_user.id)
    await state.clear()
    await message.answer(await _text(db), reply_markup=cleanup_kb())


@router.message(CleanupSettingsStates.waiting_text_days)
async def on_text_days(message: Message, db: AsyncSession, state: FSMContext) -> None:
    await _save(message, db, "text_retention_days", state)


@router.message(CleanupSettingsStates.waiting_media_days)
async def on_media_days(message: Message, db: AsyncSession, state: FSMContext) -> None:
    await _save(message, db, "media_retention_days", state)
