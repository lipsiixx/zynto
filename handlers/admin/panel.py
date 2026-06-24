"""Главная админ-панель /admin."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.exceptions import TelegramBadRequest
from database.models import Admin
from keyboards.admin_kb import admin_main

router = Router(name="admin-panel")

ADMIN_TITLE = "🛠 <b>Админ-панель</b>\nВыбери раздел:"


@router.message(Command("admin"))
async def cmd_admin(message: Message, admin: Admin, state: FSMContext) -> None:
    await state.clear()
    await message.answer(ADMIN_TITLE, reply_markup=admin_main(admin.is_superadmin))


@router.callback_query(F.data == "a:main")
async def cb_main(call: CallbackQuery, admin: Admin, state: FSMContext) -> None:
    try:
        await state.clear()
        await call.message.edit_text(ADMIN_TITLE, reply_markup=admin_main(admin.is_superadmin))
        await call.answer()
    except TelegramBadRequest:
        pass
