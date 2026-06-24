"""/activate КОД и активация через кнопку."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from database.queries import promo_codes as promo_q
from keyboards.user_kb import main_menu
from services import subscription as sub_service
from states.user_states import ActivateCodeStates
from utils.formatters import fmt_dt

logger = logging.getLogger(__name__)
router = Router(name="user-activate")


async def _activate(message: Message, user: User, db: AsyncSession, code: str) -> None:
    code = code.strip()
    promo = await promo_q.get_by_code(db, code)
    if promo is None:
        await message.answer("❌ Код не найден.")
        return
    if promo.used_by is not None:
        await message.answer("❌ Этот код уже был активирован.")
        return
    now = datetime.now(timezone.utc)
    if promo.code_expires_at is not None:
        exp = promo.code_expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < now:
            await message.answer("❌ Срок действия кода истёк.")
            return

    access_expires = await sub_service.activate_promo(db, user, promo)
    await promo_q.mark_used(db, promo, user.telegram_id, access_expires)
    period = "навсегда" if promo.duration_days is None else f"до {fmt_dt(access_expires)}"
    logger.info("Промокод активирован: code=%s user=%s", code, user.telegram_id)
    await message.answer(
        f"✅ <b>Код активирован!</b> Доступ открыт {period}.",
        reply_markup=main_menu(),
    )


@router.message(Command("activate"))
async def cmd_activate(message: Message, user: User, db: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Использование: <code>/activate КОД</code>\nНапример: /activate A3BK9QTZ")
        return
    await _activate(message, user, db, parts[1])


@router.callback_query(F.data == "activate")
async def cb_activate(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ActivateCodeStates.waiting_code)
    await call.message.answer("🎟 Введи промокод:")
    await call.answer()


@router.message(ActivateCodeStates.waiting_code)
async def on_code_entered(message: Message, user: User, db: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    await _activate(message, user, db, message.text)
