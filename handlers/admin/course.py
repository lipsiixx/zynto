"""Управление курсом для пользователей (видео + подпись)."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.queries import settings as settings_q
from keyboards.admin_kb import admin_back, course_kb
from states.admin_states import CourseEditStates

logger = logging.getLogger(__name__)
router = Router(name="admin-course")


async def _status_text(db: AsyncSession) -> str:
    enabled = await settings_q.get_setting(db, "course_enabled", "0")
    file_id = await settings_q.get_setting(db, "course_video_file_id")
    caption = await settings_q.get_setting(db, "course_caption", "—")
    status = "✅ Включён" if enabled == "1" else "❌ Выключен"
    video_info = "загружено" if file_id else "не загружено"
    caption_preview = (caption[:80] + "…") if len(caption) > 80 else caption
    return (
        f"📹 <b>Курс по использованию бота</b>\n\n"
        f"Статус: {status}\n"
        f"Видео: {video_info}\n"
        f"Подпись: {caption_preview}\n\n"
        "Курс отправляется после первой покупки и активации промокода, "
        "а также доступен из меню пользователя."
    )


@router.callback_query(F.data == "a:course")
async def cb_course(call: CallbackQuery, db: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    text = await _status_text(db)
    enabled = await settings_q.get_setting(db, "course_enabled", "0")
    try:
        await call.message.edit_text(text, reply_markup=course_kb(enabled == "1"))
    except TelegramBadRequest:
        pass
    await call.answer()


@router.callback_query(F.data == "a:course_toggle")
async def cb_course_toggle(call: CallbackQuery, db: AsyncSession) -> None:
    current = await settings_q.get_setting(db, "course_enabled", "0")
    new_val = "0" if current == "1" else "1"
    await settings_q.set_setting(db, "course_enabled", new_val, call.from_user.id)
    text = await _status_text(db)
    try:
        await call.message.edit_text(text, reply_markup=course_kb(new_val == "1"))
    except TelegramBadRequest:
        pass
    label = "✅ Включён" if new_val == "1" else "❌ Выключен"
    await call.answer(label)
    logger.info("Курс: статус изменён на %s admin=%s", new_val, call.from_user.id)


@router.callback_query(F.data == "a:course_video")
async def cb_course_video(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(CourseEditStates.waiting_video)
    await call.message.answer(
        "📹 <b>Отправь видео для курса.</b>\n\n"
        "Видео будет показываться пользователям после покупки и в меню.\n"
        "/admin — для отмены."
    )
    await call.answer()


@router.message(CourseEditStates.waiting_video, F.video)
async def on_course_video(message: Message, db: AsyncSession, state: FSMContext) -> None:
    file_id = message.video.file_id
    await settings_q.set_setting(db, "course_video_file_id", file_id, message.from_user.id)
    await state.clear()
    logger.info("Курс: обновлено видео admin=%s file_id=%s", message.from_user.id, file_id)
    await message.answer("✅ Видео курса сохранено.", reply_markup=admin_back())


@router.message(CourseEditStates.waiting_video)
async def on_course_video_wrong(message: Message) -> None:
    await message.answer("❌ Нужно отправить видеофайл. Попробуй ещё раз или /admin для отмены.")


@router.callback_query(F.data == "a:course_caption")
async def cb_course_caption(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(CourseEditStates.waiting_caption)
    await call.message.answer(
        "✏️ <b>Отправь новую подпись к курсу.</b>\n\n"
        "Это текст, который увидят пользователи под видео.\n"
        "/admin — для отмены."
    )
    await call.answer()


@router.message(CourseEditStates.waiting_caption, F.text)
async def on_course_caption(message: Message, db: AsyncSession, state: FSMContext) -> None:
    await settings_q.set_setting(db, "course_caption", message.text, message.from_user.id)
    await state.clear()
    logger.info("Курс: обновлена подпись admin=%s", message.from_user.id)
    await message.answer("✅ Подпись обновлена.", reply_markup=admin_back())
