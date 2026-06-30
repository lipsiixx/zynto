"""Раздел «О боте» — пользовательские хендлеры."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from database.queries import settings as settings_q

router = Router(name="user-about")


def _normalize_support_url(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("@"):
        return f"https://t.me/{raw[1:]}"
    return raw


async def _build_about_kb(db: AsyncSession) -> tuple[InlineKeyboardMarkup, bool]:
    kb = InlineKeyboardBuilder()
    has_any = False

    privacy_en = (await settings_q.get_setting(db, "about_privacy_enabled", "1")) == "1"
    privacy_type = await settings_q.get_setting(db, "about_privacy_type", "text")
    privacy_content = await settings_q.get_setting(db, "about_privacy_content", "")

    terms_en = (await settings_q.get_setting(db, "about_terms_enabled", "1")) == "1"
    terms_type = await settings_q.get_setting(db, "about_terms_type", "text")
    terms_content = await settings_q.get_setting(db, "about_terms_content", "")

    support_en = (await settings_q.get_setting(db, "about_support_enabled", "1")) == "1"
    support_url = await settings_q.get_setting(db, "about_support_url", "")

    if privacy_en and privacy_content:
        has_any = True
        if privacy_type == "url":
            kb.row(InlineKeyboardButton(text="📄 Политика конфиденциальности", url=privacy_content))
        else:
            kb.row(InlineKeyboardButton(text="📄 Политика конфиденциальности", callback_data="about:privacy"))

    if terms_en and terms_content:
        has_any = True
        if terms_type == "url":
            kb.row(InlineKeyboardButton(text="📋 Пользовательское соглашение", url=terms_content))
        else:
            kb.row(InlineKeyboardButton(text="📋 Пользовательское соглашение", callback_data="about:terms"))

    if support_en and support_url:
        has_any = True
        kb.row(InlineKeyboardButton(text="💬 Поддержка", url=_normalize_support_url(support_url)))

    return kb.as_markup(), has_any


@router.callback_query(F.data == "about")
async def cb_about(call: CallbackQuery, db: AsyncSession) -> None:
    kb, has_any = await _build_about_kb(db)
    text = "ℹ️ <b>О боте</b>\n\nВыбери раздел:" if has_any else "ℹ️ <b>О боте</b>\n\nРаздел временно недоступен."
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()


@router.callback_query(F.data == "about:privacy")
async def cb_about_privacy(call: CallbackQuery, db: AsyncSession) -> None:
    content = await settings_q.get_setting(db, "about_privacy_content", "")
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Назад", callback_data="about")
    await call.message.edit_text(
        f"📄 <b>Политика конфиденциальности</b>\n\n{content}",
        reply_markup=kb.as_markup(),
    )
    await call.answer()


@router.callback_query(F.data == "about:terms")
async def cb_about_terms(call: CallbackQuery, db: AsyncSession) -> None:
    content = await settings_q.get_setting(db, "about_terms_content", "")
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Назад", callback_data="about")
    await call.message.edit_text(
        f"📋 <b>Пользовательское соглашение</b>\n\n{content}",
        reply_markup=kb.as_markup(),
    )
    await call.answer()
