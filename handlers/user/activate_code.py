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
from database.queries import tariffs as tariffs_q
from database.queries import users as users_q
from keyboards.user_kb import main_menu, subscribe_button, tariffs_kb
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
    if not promo_q.is_available(promo):
        if promo.code_expires_at is not None:
            exp = promo.code_expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if exp < datetime.now(timezone.utc):
                await message.answer("❌ Срок действия кода истёк.")
                return
        await message.answer("❌ Этот код уже использован.")
        return

    if promo.code_type == "discount":
        await _activate_discount(message, user, db, promo)
    else:
        await _activate_access(message, user, db, promo)


async def _activate_access(message: Message, user: User, db: AsyncSession, promo) -> None:
    access_expires = await sub_service.activate_promo(db, user, promo)
    await promo_q.record_use(db, promo, user.telegram_id, access_expires)
    period = "навсегда" if promo.duration_days is None else f"до {fmt_dt(access_expires)}"
    logger.info("Промокод доступа активирован: code=%s user=%s", promo.code, user.telegram_id)
    await message.answer(
        f"✅ <b>Код активирован!</b> Доступ открыт {period}.",
        reply_markup=main_menu(),
    )


async def _activate_discount(message: Message, user: User, db: AsyncSession, promo) -> None:
    # Сохраняем как ожидающий — применится при следующей покупке
    await users_q.set_pending_promo(db, user.telegram_id, promo.id)
    logger.info("Скидочный промокод активирован: code=%s user=%s", promo.code, user.telegram_id)

    if promo.discount_tariff_id is not None:
        tariff = await tariffs_q.get_tariff(db, promo.discount_tariff_id)
        tariff_label = tariff.name if tariff else f"тариф #{promo.discount_tariff_id}"
    else:
        tariff_label = "любой тариф"

    tariffs = await tariffs_q.list_tariffs(db, only_active=True)
    await message.answer(
        f"🎫 <b>Скидочный код принят!</b>\n\n"
        f"Скидка: <b>{promo.discount_stars}⭐</b> на {tariff_label}\n\n"
        "Выбери тариф для покупки со скидкой:",
        reply_markup=tariffs_kb(tariffs, prefix="buy"),
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
