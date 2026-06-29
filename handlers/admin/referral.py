"""Управление реферальной программой — для всех админов."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Admin
from database.queries import referral as referral_q
from database.queries import settings as settings_q
from keyboards.admin_kb import admin_back, referral_kb
from states.admin_states import ReferralSettingsStates

router = Router(name="admin-referral")


async def _text(db: AsyncSession) -> str:
    enabled = (await settings_q.get_setting(db, "referral_enabled", "1")) != "0"
    reward_days = await settings_q.get_int_setting(db, "referral_reward_days", 3)

    rewards, total_rewards = await referral_q.list_all_rewards(db, page=1, limit=5)
    referrers = len({r["referrer_id"] for r in rewards})

    status = "✅ Включена" if enabled else "❌ Выключена"
    last_block = ""
    if rewards:
        lines = []
        for r in rewards:
            lines.append(f"  • {r['referrer_name']} → {r['referred_name']} (+{r['days_granted']} дн.)")
        last_block = "\n\n📋 <b>Последние начисления:</b>\n" + "\n".join(lines)

    return (
        "🤝 <b>Реферальная программа</b>\n\n"
        f"Статус: {status}\n"
        f"Награда за покупку реферала: <b>+{reward_days} дн.</b>\n\n"
        f"📊 Всего начислений: <b>{total_rewards}</b>"
        f"{last_block}"
    )


@router.callback_query(F.data == "a:referral")
async def cb_referral(call: CallbackQuery, db: AsyncSession, admin: Admin) -> None:
    await call.message.edit_text(await _text(db), reply_markup=referral_kb())
    await call.answer()


@router.callback_query(F.data == "a:referral_toggle")
async def cb_toggle(call: CallbackQuery, db: AsyncSession, admin: Admin) -> None:
    current = (await settings_q.get_setting(db, "referral_enabled", "1")) != "0"
    new_val = "0" if current else "1"
    await settings_q.set_setting(db, "referral_enabled", new_val, updated_by=call.from_user.id)
    await call.message.edit_text(await _text(db), reply_markup=referral_kb())
    await call.answer("Включено" if new_val == "1" else "Выключено")


@router.callback_query(F.data == "a:referral_edit")
async def cb_edit(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ReferralSettingsStates.waiting_bonus_days)
    await call.message.answer("Введи количество дней награды за покупку приглашённого (целое число ≥ 1):")
    await call.answer()


@router.message(ReferralSettingsStates.waiting_bonus_days)
async def on_bonus_days(message: Message, db: AsyncSession, state: FSMContext, admin: Admin) -> None:
    try:
        days = int(message.text.strip())
        if days < 1:
            raise ValueError
    except ValueError:
        await message.answer("Нужно целое число от 1. Попробуй ещё раз:")
        return
    await settings_q.set_setting(db, "referral_reward_days", str(days), updated_by=message.from_user.id)
    await state.clear()
    await message.answer(await _text(db), reply_markup=referral_kb())
