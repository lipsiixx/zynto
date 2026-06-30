"""Управление разделом «О боте»."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.queries import settings as settings_q
from keyboards.admin_kb import about_edit_kb, about_main_kb
from states.admin_states import AboutSettingsStates

router = Router(name="admin-about")


async def _about_text(db: AsyncSession) -> str:
    privacy_en = (await settings_q.get_setting(db, "about_privacy_enabled", "1")) == "1"
    privacy_type = await settings_q.get_setting(db, "about_privacy_type", "text")
    privacy_content = await settings_q.get_setting(db, "about_privacy_content", "")

    terms_en = (await settings_q.get_setting(db, "about_terms_enabled", "1")) == "1"
    terms_type = await settings_q.get_setting(db, "about_terms_type", "text")
    terms_content = await settings_q.get_setting(db, "about_terms_content", "")

    support_en = (await settings_q.get_setting(db, "about_support_enabled", "1")) == "1"
    support_url = await settings_q.get_setting(db, "about_support_url", "")

    def s(en: bool) -> str:
        return "✅" if en else "❌"

    def t(typ: str) -> str:
        return "URL" if typ == "url" else "Текст"

    def p(val: str, n: int = 50) -> str:
        val = val or "—"
        return (val[:n] + "…") if len(val) > n else val

    return (
        "ℹ️ <b>О боте</b>\n\n"
        f"📄 <b>Политика конфиденциальности</b> {s(privacy_en)}\n"
        f"  Тип: {t(privacy_type)} | {p(privacy_content)}\n\n"
        f"📋 <b>Пользовательское соглашение</b> {s(terms_en)}\n"
        f"  Тип: {t(terms_type)} | {p(terms_content)}\n\n"
        f"💬 <b>Поддержка</b> {s(support_en)}\n"
        f"  {p(support_url)}"
    )


async def _refresh(call: CallbackQuery, db: AsyncSession) -> None:
    privacy_en = (await settings_q.get_setting(db, "about_privacy_enabled", "1")) == "1"
    privacy_type = await settings_q.get_setting(db, "about_privacy_type", "text")
    terms_en = (await settings_q.get_setting(db, "about_terms_enabled", "1")) == "1"
    terms_type = await settings_q.get_setting(db, "about_terms_type", "text")
    support_en = (await settings_q.get_setting(db, "about_support_enabled", "1")) == "1"
    try:
        await call.message.edit_text(
            await _about_text(db),
            reply_markup=about_main_kb(privacy_en, privacy_type, terms_en, terms_type, support_en),
        )
    except TelegramBadRequest:
        pass


@router.callback_query(F.data == "a:about")
async def cb_about(call: CallbackQuery, db: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    await _refresh(call, db)
    await call.answer()


# ── Privacy ──

@router.callback_query(F.data == "a:about:privacy:toggle")
async def cb_privacy_toggle(call: CallbackQuery, db: AsyncSession) -> None:
    cur = (await settings_q.get_setting(db, "about_privacy_enabled", "1")) == "1"
    await settings_q.set_setting(db, "about_privacy_enabled", "0" if cur else "1", call.from_user.id)
    await _refresh(call, db)
    await call.answer("Выключено" if cur else "Включено")


@router.callback_query(F.data == "a:about:privacy:type")
async def cb_privacy_type(call: CallbackQuery, db: AsyncSession) -> None:
    cur = await settings_q.get_setting(db, "about_privacy_type", "text")
    new = "url" if cur == "text" else "text"
    await settings_q.set_setting(db, "about_privacy_type", new, call.from_user.id)
    await _refresh(call, db)
    await call.answer(f"Тип: {'URL' if new == 'url' else 'Текст'}")


@router.callback_query(F.data == "a:about:privacy:edit")
async def cb_privacy_edit(call: CallbackQuery, state: FSMContext, db: AsyncSession) -> None:
    typ = await settings_q.get_setting(db, "about_privacy_type", "text")
    hint = "URL (например https://example.com/privacy)" if typ == "url" else "текст политики конфиденциальности"
    await state.set_state(AboutSettingsStates.waiting_privacy_content)
    await call.message.answer(
        f"✏️ Введи {hint}.\n\n/admin — для отмены.",
        reply_markup=about_edit_kb(),
    )
    await call.answer()


@router.message(AboutSettingsStates.waiting_privacy_content, F.text)
async def on_privacy_content(message: Message, db: AsyncSession, state: FSMContext) -> None:
    await settings_q.set_setting(db, "about_privacy_content", message.text.strip(), message.from_user.id)
    await state.clear()
    await message.answer("✅ Политика конфиденциальности обновлена.", reply_markup=about_edit_kb())


# ── Terms ──

@router.callback_query(F.data == "a:about:terms:toggle")
async def cb_terms_toggle(call: CallbackQuery, db: AsyncSession) -> None:
    cur = (await settings_q.get_setting(db, "about_terms_enabled", "1")) == "1"
    await settings_q.set_setting(db, "about_terms_enabled", "0" if cur else "1", call.from_user.id)
    await _refresh(call, db)
    await call.answer("Выключено" if cur else "Включено")


@router.callback_query(F.data == "a:about:terms:type")
async def cb_terms_type(call: CallbackQuery, db: AsyncSession) -> None:
    cur = await settings_q.get_setting(db, "about_terms_type", "text")
    new = "url" if cur == "text" else "text"
    await settings_q.set_setting(db, "about_terms_type", new, call.from_user.id)
    await _refresh(call, db)
    await call.answer(f"Тип: {'URL' if new == 'url' else 'Текст'}")


@router.callback_query(F.data == "a:about:terms:edit")
async def cb_terms_edit(call: CallbackQuery, state: FSMContext, db: AsyncSession) -> None:
    typ = await settings_q.get_setting(db, "about_terms_type", "text")
    hint = "URL (например https://example.com/terms)" if typ == "url" else "текст пользовательского соглашения"
    await state.set_state(AboutSettingsStates.waiting_terms_content)
    await call.message.answer(
        f"✏️ Введи {hint}.\n\n/admin — для отмены.",
        reply_markup=about_edit_kb(),
    )
    await call.answer()


@router.message(AboutSettingsStates.waiting_terms_content, F.text)
async def on_terms_content(message: Message, db: AsyncSession, state: FSMContext) -> None:
    await settings_q.set_setting(db, "about_terms_content", message.text.strip(), message.from_user.id)
    await state.clear()
    await message.answer("✅ Пользовательское соглашение обновлено.", reply_markup=about_edit_kb())


# ── Support ──

@router.callback_query(F.data == "a:about:support:toggle")
async def cb_support_toggle(call: CallbackQuery, db: AsyncSession) -> None:
    cur = (await settings_q.get_setting(db, "about_support_enabled", "1")) == "1"
    await settings_q.set_setting(db, "about_support_enabled", "0" if cur else "1", call.from_user.id)
    await _refresh(call, db)
    await call.answer("Выключено" if cur else "Включено")


@router.callback_query(F.data == "a:about:support:edit")
async def cb_support_edit(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AboutSettingsStates.waiting_support_url)
    await call.message.answer(
        "✏️ Введи ссылку на поддержку.\n\n"
        "Формат: @username или https://t.me/username\n\n"
        "/admin — для отмены.",
        reply_markup=about_edit_kb(),
    )
    await call.answer()


@router.message(AboutSettingsStates.waiting_support_url, F.text)
async def on_support_url(message: Message, db: AsyncSession, state: FSMContext) -> None:
    await settings_q.set_setting(db, "about_support_url", message.text.strip(), message.from_user.id)
    await state.clear()
    await message.answer("✅ Ссылка на поддержку обновлена.", reply_markup=about_edit_kb())
