"""Управление реферальной программой — для всех админов."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Admin
from database.queries import settings as settings_q
from database.queries import users as users_q
from keyboards.admin_kb import admin_back, referral_kb
from states.admin_states import ReferralSettingsStates

router = Router(name="admin-referral")


async def _text(db: AsyncSession) -> str:
    bonus = await settings_q.get_int_setting(db, "referral_bonus_days", 1)
    stats = await users_q.get_referral_stats(db)
    status = "✅ Включена" if bonus > 0 else "❌ Выключена (бонус = 0)"
    return (
        "🤝 <b>Реферальная программа</b>\n\n"
        f"Статус: {status}\n"
        f"Бонус за реферала: <b>{bonus} дн.</b>\n\n"
        f"📊 Статистика:\n"
        f"• Зарегистрировано по рефералке: <b>{stats['total']}</b>\n"
        f"• Из них оплатили подписку: <b>{stats['rewarded']}</b>\n\n"
        "ℹ️ Установи 0 дней, чтобы отключить программу."
    )


@router.callback_query(F.data == "a:referral")
async def cb_referral(call: CallbackQuery, db: AsyncSession, admin: Admin) -> None:
    await call.message.edit_text(await _text(db), reply_markup=referral_kb())
    await call.answer()


@router.callback_query(F.data == "a:referral_edit")
async def cb_edit(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ReferralSettingsStates.waiting_bonus_days)
    await call.message.answer("Введи количество дней бонуса за приглашённого друга (0 = выключить программу):")
    await call.answer()


@router.message(ReferralSettingsStates.waiting_bonus_days)
async def on_bonus_days(message: Message, db: AsyncSession, state: FSMContext, admin: Admin) -> None:
    try:
        days = int(message.text.strip())
        if days < 0:
            raise ValueError
    except ValueError:
        await message.answer("Нужно неотрицательное целое число. Попробуй ещё раз:")
        return
    await settings_q.set_setting(db, "referral_bonus_days", str(days), updated_by=message.from_user.id)
    await state.clear()
    await message.answer(await _text(db), reply_markup=referral_kb())
