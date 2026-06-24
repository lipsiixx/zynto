"""Управление админами — только суперадмин."""
from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Admin
from database.queries import admins as admins_q
from database.queries import users as users_q
from keyboards.admin_kb import admins_list_kb, confirm_kb
from states.admin_states import AddAdminStates

logger = logging.getLogger(__name__)
router = Router(name="admin-admins")


def _ensure_super(admin: Admin) -> bool:
    return bool(admin and admin.is_superadmin)


@router.callback_query(F.data == "a:admins")
async def cb_admins(call: CallbackQuery, db: AsyncSession, admin: Admin) -> None:
    if not _ensure_super(admin):
        await call.answer("Только для суперадмина", show_alert=True)
        return
    admins = await admins_q.list_admins(db, include_superadmin=False)
    text = "👮 <b>Админы</b>" if admins else "👮 Других админов пока нет."
    await call.message.edit_text(text, reply_markup=admins_list_kb(admins))
    await call.answer()


@router.callback_query(F.data == "a:admin_add")
async def cb_add(call: CallbackQuery, admin: Admin, state: FSMContext) -> None:
    if not _ensure_super(admin):
        await call.answer("Только для суперадмина", show_alert=True)
        return
    await state.set_state(AddAdminStates.waiting_identifier)
    await call.message.answer("Введи Telegram ID или @username нового админа:")
    await call.answer()


@router.message(AddAdminStates.waiting_identifier)
async def on_identifier(message: Message, db: AsyncSession, state: FSMContext) -> None:
    ident = message.text.strip()
    if ident.startswith("@") or not ident.isdigit():
        user = await users_q.get_user_by_username(db, ident)
    else:
        user = await users_q.get_user(db, int(ident))

    if user is None:
        await message.answer("Пользователь не найден в базе (он должен сначала запустить бота). Попробуй ещё раз или /admin для отмены.")
        return

    await state.update_data(target_id=user.telegram_id, username=user.username, full_name=user.full_name)
    await state.set_state(AddAdminStates.confirm)
    await message.answer(
        f"Добавить <b>{user.full_name}</b> (@{user.username or '—'}) как админа?",
        reply_markup=confirm_kb("a:admin_confirm", "a:main"),
    )


@router.callback_query(AddAdminStates.confirm, F.data == "a:admin_confirm")
async def cb_confirm(call: CallbackQuery, db: AsyncSession, admin: Admin, bot: Bot, state: FSMContext) -> None:
    data = await state.get_data()
    await state.clear()
    target_id = data["target_id"]
    await admins_q.add_admin(db, target_id, data.get("username"), data.get("full_name"), admin.telegram_id)
    logger.info("Добавлен админ %s суперадмином %s", target_id, admin.telegram_id)
    try:
        await bot.send_message(target_id, "👮 Тебе выдан доступ к панели администратора. /admin")
    except Exception:  # noqa: BLE001
        pass
    admins = await admins_q.list_admins(db, include_superadmin=False)
    await call.message.edit_text("✅ Админ добавлен.", reply_markup=admins_list_kb(admins))
    await call.answer()


@router.callback_query(F.data.startswith("a:admin_del:"))
async def cb_del(call: CallbackQuery, db: AsyncSession, admin: Admin) -> None:
    if not _ensure_super(admin):
        await call.answer("Только для суперадмина", show_alert=True)
        return
    target_id = int(call.data.split(":")[-1])
    await admins_q.remove_admin(db, target_id)
    logger.info("Удалён админ %s", target_id)
    admins = await admins_q.list_admins(db, include_superadmin=False)
    await call.message.edit_text("🗑 Админ удалён.", reply_markup=admins_list_kb(admins))
    await call.answer()
