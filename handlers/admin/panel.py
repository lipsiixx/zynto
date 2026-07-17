"""Главная админ-панель /admin."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)
from aiogram.exceptions import TelegramBadRequest
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import settings
from database.models import Admin
from keyboards.admin_kb import admin_main

router = Router(name="admin-panel")

ADMIN_TITLE = "🛠 <b>Админ-панель</b>\nВыбери раздел:"


def _admin_miniapp_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if settings.miniapp_url:
        url = f"{settings.miniapp_url}?admin_entry=full"
        kb.row(InlineKeyboardButton(text="📱 Открыть админ-панель", web_app=WebAppInfo(url=url)))
    else:
        kb.row(InlineKeyboardButton(text="📱 Открыть админ-панель", callback_data="miniapp_unavailable"))
    return kb.as_markup()


@router.message(Command("admin"))
async def cmd_admin(message: Message, admin: Admin, state: FSMContext) -> None:
    await state.clear()
    await message.answer(ADMIN_TITLE, reply_markup=_admin_miniapp_kb())


@router.callback_query(F.data == "a:main")
async def cb_main(call: CallbackQuery, admin: Admin, state: FSMContext) -> None:
    try:
        await state.clear()
        await call.message.edit_text(ADMIN_TITLE, reply_markup=admin_main(admin.is_superadmin))
        await call.answer()
    except TelegramBadRequest:
        pass
