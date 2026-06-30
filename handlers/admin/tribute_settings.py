"""Настройка URL оплаты через Tribute (СБП)."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Admin
from database.queries import settings as settings_q
from keyboards.admin_kb import tribute_kb, tribute_set_url_kb
from states.admin_states import TributeSettingsStates

router = Router(name="admin-tribute")


async def _text(db: AsyncSession) -> str:
    url = await settings_q.get_setting(db, "tribute_payment_url")
    status = f"<code>{url}</code>" if url else "<i>не настроен</i>"
    return (
        "🏦 <b>Tribute СБП — настройки</b>\n\n"
        f"Текущий URL оплаты: {status}\n\n"
        f"Это ссылка на страницу подписки в Tribute, которую пользователь откроет для оплаты через СБП."
    )


@router.callback_query(F.data == "a:tribute_settings")
async def cb_tribute_settings(call: CallbackQuery, db: AsyncSession, admin: Admin, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_text(await _text(db), reply_markup=tribute_kb())
    await call.answer()


@router.callback_query(F.data == "a:tribute_set_url")
async def cb_tribute_set_url(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(TributeSettingsStates.waiting_url)
    await call.message.edit_text(
        "🔗 Введи URL страницы оплаты Tribute:\n\n"
        "Пример: <code>https://tribute.tg/s/YOUR_CHANNEL</code>",
        reply_markup=tribute_set_url_kb(),
    )
    await call.answer()


@router.message(TributeSettingsStates.waiting_url)
async def on_tribute_url(message: Message, db: AsyncSession, state: FSMContext) -> None:
    url = message.text.strip() if message.text else ""
    if not url.startswith("http"):
        await message.answer("❌ Некорректный URL. Должен начинаться с http:// или https://")
        return
    await settings_q.set_setting(db, "tribute_payment_url", url, updated_by=message.from_user.id)
    await state.clear()
    await message.answer(f"✅ URL оплаты Tribute обновлён:\n<code>{url}</code>")
    await message.answer(await _text(db), reply_markup=tribute_kb())


@router.callback_query(F.data == "a:tribute_clear_url")
async def cb_tribute_clear_url(call: CallbackQuery, db: AsyncSession, admin: Admin, state: FSMContext) -> None:
    from sqlalchemy import delete

    from database.models import BotSetting

    await db.execute(delete(BotSetting).where(BotSetting.key == "tribute_payment_url"))
    await db.commit()
    await call.message.edit_text(await _text(db), reply_markup=tribute_kb())
    await call.answer("Сброшено")
