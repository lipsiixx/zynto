"""Подарить подписку: покупка звёздами → генерация одноразового промокода."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, LabeledPrice, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from database.queries import promo_codes as promo_q
from database.queries import subscriptions as subs_q
from database.queries import tariffs as tariffs_q
from keyboards.user_kb import back_to_menu, gift_tariffs_kb
from utils.code_generator import generate_gift_code
from utils.formatters import duration_text

logger = logging.getLogger(__name__)
router = Router(name="user-gift")


@router.callback_query(F.data == "gift")
async def cb_gift(call: CallbackQuery, db: AsyncSession) -> None:
    tariffs = await tariffs_q.list_tariffs(db, only_active=True)
    if not tariffs:
        await call.message.edit_text("Сейчас нет тарифов для подарка.", reply_markup=back_to_menu())
        await call.answer()
        return
    await call.message.edit_text(
        "🎁 <b>Подарить подписку</b>\nВыбери тариф — после оплаты получишь одноразовый код для друга.",
        reply_markup=gift_tariffs_kb(tariffs),
    )
    await call.answer()


@router.callback_query(F.data.startswith("giftbuy:"))
async def cb_giftbuy(call: CallbackQuery, db: AsyncSession) -> None:
    tariff_id = int(call.data.split(":", 1)[1])
    tariff = await tariffs_q.get_tariff(db, tariff_id)
    if tariff is None or not tariff.is_active:
        await call.answer("Тариф недоступен", show_alert=True)
        return
    await call.message.answer_invoice(
        title=f"🎁 Подарок: {tariff.name}",
        description=f"Подарочная подписка «{tariff.name}» ({duration_text(tariff.duration_days)})",
        payload=f"gift_{tariff.id}_{call.from_user.id}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=f"Подарок: {tariff.name}", amount=tariff.price_stars)],
    )
    await call.answer()


async def process_gift_payment(
    message: Message,
    user: User,
    db: AsyncSession,
    payload: str,
    charge_id: str | None,
) -> None:
    parts = payload.split("_")
    try:
        tariff_id = int(parts[1])
    except (IndexError, ValueError):
        await message.answer("⚠️ Ошибка обработки подарка, обратись в поддержку.")
        return

    tariff = await tariffs_q.get_tariff(db, tariff_id)
    if tariff is None:
        await message.answer("⚠️ Тариф не найден.")
        return

    code = generate_gift_code()
    label = duration_text(tariff.duration_days)
    # promo_codes.duration_days хранится в МИНУТАХ (None = lifetime)
    if tariff.duration_days is None or tariff.duration_days == 0:
        promo_minutes = None
    else:
        promo_minutes = tariff.duration_days * 24 * 60
    await promo_q.create_promo(
        db,
        code=code,
        created_by=user.telegram_id,
        duration_days=promo_minutes,
        duration_label=label,
        code_expires_at=None,
        note=f"gift от {user.telegram_id}",
    )
    # Запись о покупке подарка (не активирует доступ самому дарителю)
    await subs_q.create_subscription(
        db,
        user_id=user.telegram_id,
        tariff_id=tariff.id,
        expires_at=None,
        payment_method="gift_purchase",
        telegram_payment_charge_id=charge_id,
    )
    logger.info("Подарочный код создан: %s дарителем %s", code, user.telegram_id)

    await message.answer(
        "🎁 <b>Подарочный код создан!</b>\n\n"
        f"Код: <code>{code}</code>\n"
        f"Действителен: {label}\n"
        "Код одноразовый — передай его другу.\n\n"
        f"Друг может активировать командой: <code>/activate {code}</code>",
        reply_markup=back_to_menu(),
    )
