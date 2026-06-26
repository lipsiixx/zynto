"""Управление подначивающими сообщениями и настройками отправки."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.queries import nudge as nudge_q
from database.queries import settings as settings_q
from keyboards.admin_kb import admin_back, nudge_main_kb, nudge_msg_kb, nudge_msgs_kb
from states.admin_states import NudgeStates

logger = logging.getLogger(__name__)
router = Router(name="admin-nudge")


async def _settings_text(db: AsyncSession) -> str:
    enabled = await settings_q.get_setting(db, "nudge_enabled", "0")
    interval = await settings_q.get_int_setting(db, "nudge_interval_days", 1)
    grace = await settings_q.get_int_setting(db, "nudge_grace_days", 3)
    messages = await nudge_q.list_nudge_messages(db)
    active_count = sum(1 for m in messages if m.is_active)
    status = "✅ Включены" if enabled == "1" else "❌ Выключены"
    return (
        f"💬 <b>Подначивающие сообщения</b>\n\n"
        f"Статус: {status}\n"
        f"Периодичность: каждые <b>{interval} дн.</b>\n"
        f"Порог: через <b>{grace} дн.</b> после истечения подписки\n"
        f"Текстов: <b>{len(messages)}</b> (активных: {active_count})\n\n"
        f"Отправляются в случайное время с 10:00 до 21:00 МСК."
    )


# ─── Главная страница ──────────────────────────────────────────────────────

@router.callback_query(F.data == "a:nudge")
async def cb_nudge(call: CallbackQuery, db: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    enabled = await settings_q.get_setting(db, "nudge_enabled", "0")
    text = await _settings_text(db)
    try:
        await call.message.edit_text(text, reply_markup=nudge_main_kb(enabled == "1"))
    except TelegramBadRequest:
        pass
    await call.answer()


@router.callback_query(F.data == "a:nudge_toggle")
async def cb_nudge_toggle(call: CallbackQuery, db: AsyncSession) -> None:
    current = await settings_q.get_setting(db, "nudge_enabled", "0")
    new_val = "0" if current == "1" else "1"
    await settings_q.set_setting(db, "nudge_enabled", new_val, call.from_user.id)
    enabled = new_val == "1"
    text = await _settings_text(db)
    try:
        await call.message.edit_text(text, reply_markup=nudge_main_kb(enabled))
    except TelegramBadRequest:
        pass
    await call.answer("✅ Включены" if enabled else "❌ Выключены")
    logger.info("Nudge: статус → %s admin=%s", new_val, call.from_user.id)


# ─── Периодичность ────────────────────────────────────────────────────────

@router.callback_query(F.data == "a:nudge_set_interval")
async def cb_nudge_set_interval(call: CallbackQuery, state: FSMContext) -> None:
    interval = 1  # default shown in prompt
    await state.set_state(NudgeStates.waiting_interval)
    await call.message.answer(
        "⏱ <b>Периодичность отправки (в днях)</b>\n\n"
        "Введи число — раз в сколько дней отправлять сообщение.\n"
        "Например: <code>1</code> — раз в день, <code>3</code> — раз в 3 дня.\n\n"
        "/admin — для отмены."
    )
    await call.answer()


@router.message(NudgeStates.waiting_interval, F.text)
async def on_nudge_interval(message: Message, db: AsyncSession, state: FSMContext) -> None:
    try:
        days = int(message.text.strip())
        if days < 1:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введи целое число ≥ 1.")
        return
    await settings_q.set_setting(db, "nudge_interval_days", str(days), message.from_user.id)
    await state.clear()
    logger.info("Nudge: интервал → %d дн. admin=%s", days, message.from_user.id)
    await message.answer(f"✅ Периодичность: каждые <b>{days} дн.</b>", reply_markup=admin_back())


# ─── Порог (grace) ────────────────────────────────────────────────────────

@router.callback_query(F.data == "a:nudge_set_grace")
async def cb_nudge_set_grace(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(NudgeStates.waiting_grace)
    await call.message.answer(
        "⏳ <b>Порог (дней после истечения подписки)</b>\n\n"
        "Сообщения начнут отправляться только через X дней после того, "
        "как у пользователя истекла подписка.\n"
        "Например: <code>3</code> — начинать через 3 дня.\n\n"
        "/admin — для отмены."
    )
    await call.answer()


@router.message(NudgeStates.waiting_grace, F.text)
async def on_nudge_grace(message: Message, db: AsyncSession, state: FSMContext) -> None:
    try:
        days = int(message.text.strip())
        if days < 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введи целое число ≥ 0.")
        return
    await settings_q.set_setting(db, "nudge_grace_days", str(days), message.from_user.id)
    await state.clear()
    logger.info("Nudge: grace → %d дн. admin=%s", days, message.from_user.id)
    await message.answer(
        f"✅ Подначивания начнутся через <b>{days} дн.</b> после истечения подписки.",
        reply_markup=admin_back(),
    )


# ─── Список текстов ───────────────────────────────────────────────────────

@router.callback_query(F.data == "a:nudge_msgs")
async def cb_nudge_msgs(call: CallbackQuery, db: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    messages = await nudge_q.list_nudge_messages(db)
    if not messages:
        text = "📝 <b>Тексты подначиваний</b>\n\nСписок пуст. Добавь первый текст."
    else:
        text = f"📝 <b>Тексты подначиваний</b> ({len(messages)} шт.)\n\nВыбери текст для управления:"
    try:
        await call.message.edit_text(text, reply_markup=nudge_msgs_kb(messages))
    except TelegramBadRequest:
        pass
    await call.answer()


# ─── Добавить текст ───────────────────────────────────────────────────────

@router.callback_query(F.data == "a:nudge_add")
async def cb_nudge_add(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(NudgeStates.waiting_text)
    await call.message.answer(
        "✏️ <b>Новое подначивающее сообщение</b>\n\n"
        "Отправь текст (HTML-разметка поддерживается: <b>жирный</b>, <i>курсив</i>, ссылки).\n\n"
        "/admin — для отмены."
    )
    await call.answer()


@router.message(NudgeStates.waiting_text, F.text)
async def on_nudge_text(message: Message, db: AsyncSession, state: FSMContext) -> None:
    msg = await nudge_q.create_nudge_message(db, message.text)
    await state.clear()
    logger.info("Nudge: добавлен текст id=%s admin=%s", msg.id, message.from_user.id)
    await message.answer("✅ Текст добавлен и активен.", reply_markup=admin_back())


# ─── Просмотр одного текста ───────────────────────────────────────────────

@router.callback_query(F.data.startswith("a:nudge_view:"))
async def cb_nudge_view(call: CallbackQuery, db: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    msg_id = int(call.data.split(":")[-1])
    msg = await nudge_q.get_nudge_message(db, msg_id)
    if msg is None:
        await call.answer("Сообщение не найдено", show_alert=True)
        return
    status = "🟢 Активно" if msg.is_active else "🔴 Неактивно"
    text = f"💬 <b>Текст #{msg.id}</b> [{status}]\n\n{msg.text}"
    try:
        await call.message.edit_text(text, reply_markup=nudge_msg_kb(msg.id, msg.is_active))
    except TelegramBadRequest:
        pass
    await call.answer()


# ─── Переключить активность ───────────────────────────────────────────────

@router.callback_query(F.data.startswith("a:nudge_mtoggle:"))
async def cb_nudge_mtoggle(call: CallbackQuery, db: AsyncSession) -> None:
    msg_id = int(call.data.split(":")[-1])
    msg = await nudge_q.toggle_nudge_message(db, msg_id)
    if msg is None:
        await call.answer("Не найдено", show_alert=True)
        return
    status = "🟢 Активно" if msg.is_active else "🔴 Неактивно"
    text = f"💬 <b>Текст #{msg.id}</b> [{status}]\n\n{msg.text}"
    try:
        await call.message.edit_text(text, reply_markup=nudge_msg_kb(msg.id, msg.is_active))
    except TelegramBadRequest:
        pass
    await call.answer(status)
    logger.info("Nudge: msg=%s активность → %s admin=%s", msg_id, msg.is_active, call.from_user.id)


# ─── Редактировать текст ─────────────────────────────────────────────────

@router.callback_query(F.data.startswith("a:nudge_edit:"))
async def cb_nudge_edit(call: CallbackQuery, state: FSMContext) -> None:
    msg_id = int(call.data.split(":")[-1])
    await state.set_state(NudgeStates.waiting_edit_text)
    await state.update_data(edit_msg_id=msg_id)
    await call.message.answer(
        f"✏️ <b>Редактирование текста #{msg_id}</b>\n\n"
        "Отправь новый текст (HTML поддерживается).\n\n"
        "/admin — для отмены."
    )
    await call.answer()


@router.message(NudgeStates.waiting_edit_text, F.text)
async def on_nudge_edit_text(message: Message, db: AsyncSession, state: FSMContext) -> None:
    data = await state.get_data()
    msg_id = data.get("edit_msg_id")
    msg = await nudge_q.update_nudge_message(db, msg_id, message.text)
    await state.clear()
    if msg is None:
        await message.answer("❌ Сообщение не найдено.", reply_markup=admin_back())
        return
    logger.info("Nudge: обновлён текст id=%s admin=%s", msg_id, message.from_user.id)
    await message.answer("✅ Текст обновлён.", reply_markup=admin_back())


# ─── Удалить текст ───────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("a:nudge_del:"))
async def cb_nudge_del(call: CallbackQuery, db: AsyncSession) -> None:
    msg_id = int(call.data.split(":")[-1])
    deleted = await nudge_q.delete_nudge_message(db, msg_id)
    if not deleted:
        await call.answer("Не найдено", show_alert=True)
        return
    messages = await nudge_q.list_nudge_messages(db)
    text = (
        f"📝 <b>Тексты подначиваний</b> ({len(messages)} шт.)\n\nВыбери текст для управления:"
        if messages else
        "📝 <b>Тексты подначиваний</b>\n\nСписок пуст. Добавь первый текст."
    )
    try:
        await call.message.edit_text(text, reply_markup=nudge_msgs_kb(messages))
    except TelegramBadRequest:
        pass
    await call.answer("🗑 Удалено")
    logger.info("Nudge: удалён текст id=%s admin=%s", msg_id, call.from_user.id)
