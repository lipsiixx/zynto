"""Просмотр и покупка подписки, оплата Telegram Stars, подключение мониторинга."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from database.queries import business as business_q
from database.queries import tariffs as tariffs_q
from keyboards.user_kb import (
    back_to_menu,
    main_menu,
    renew_kb,
    subscribe_button,
    tariffs_kb,
)
from services import subscription as sub_service
from utils.formatters import subscription_status_text

logger = logging.getLogger(__name__)
router = Router(name="user-subscription")

HOW_CONNECT = (
    "📡 <b>Как подключить бота (3 простых шага):</b>\n\n"
    "1️⃣ <b>Открой настройки профиля</b>\n"
    "   📱 iPhone: Профиль → «Изменить»\n"
    "   🤖 Android: Настройки → «Аккаунт»\n\n"
    "2️⃣ <b>Найди раздел «Автоматизация чатов»</b>\n"
    "   Пролистай список вниз до этого пункта.\n\n"
    "3️⃣ <b>Введи имя бота и добавь его</b>\n"
    "   Напиши в поле: <code>@zynto_bot</code>\n"
    "   Нажми кнопку <b>«Добавить»</b> — готово!\n\n"
    "✅ <b>Telegram Premium не требуется</b> — работает с обычным аккаунтом.\n\n"
    "📌 После подключения бот пришлёт подтверждение автоматически."
)


async def _show_subscription(target: Message, user: User, db: AsyncSession, edit: bool) -> None:
    if sub_service.has_active_subscription(user):
        text = (
            "💳 <b>Твоя подписка</b>\n\n"
            f"Статус: {subscription_status_text(user.subscription_status, user.subscription_expires_at)}"
        )
        markup = renew_kb()
    else:
        tariffs = await tariffs_q.list_tariffs(db, only_active=True)
        if not tariffs:
            text = "💳 Сейчас нет доступных тарифов. Загляни позже."
            markup = back_to_menu()
        else:
            text = "💳 <b>Выбери тариф:</b>"
            markup = tariffs_kb(tariffs, prefix="buy")
    if edit:
        await target.edit_text(text, reply_markup=markup)
    else:
        await target.answer(text, reply_markup=markup)


@router.callback_query(F.data == "subscription")
async def cb_subscription(call: CallbackQuery, user: User, db: AsyncSession) -> None:
    await _show_subscription(call.message, user, db, edit=True)
    await call.answer()


@router.callback_query(F.data == "renew")
async def cb_renew(call: CallbackQuery, db: AsyncSession) -> None:
    tariffs = await tariffs_q.list_tariffs(db, only_active=True)
    if not tariffs:
        await call.answer("Нет доступных тарифов", show_alert=True)
        return
    await call.message.edit_text("🔄 <b>Выбери тариф для продления:</b>", reply_markup=tariffs_kb(tariffs, prefix="buy"))
    await call.answer()


@router.callback_query(F.data == "connect")
async def cb_connect(call: CallbackQuery, user: User, db: AsyncSession) -> None:
    if not sub_service.has_active_subscription(user):
        await call.message.edit_text(
            "🔒 Для мониторинга нужна активная подписка.",
            reply_markup=subscribe_button(),
        )
        await call.answer()
        return

    conn = await business_q.get_active_for_user(db, user.telegram_id)
    if conn:
        text = "✅ <b>Мониторинг активен.</b>\nПодключено к бизнес-аккаунту. Слежу за всей перепиской."
    else:
        text = HOW_CONNECT
    await call.message.edit_text(text, reply_markup=back_to_menu())
    await call.answer()


@router.callback_query(F.data.startswith("buy:"))
async def cb_buy(call: CallbackQuery, db: AsyncSession) -> None:
    tariff_id = int(call.data.split(":", 1)[1])
    tariff = await tariffs_q.get_tariff(db, tariff_id)
    if tariff is None or not tariff.is_active:
        await call.answer("Тариф недоступен", show_alert=True)
        return

    await call.message.answer_invoice(
        title=tariff.name,
        description=tariff.description or f"Подписка на мониторинг: {tariff.name}",
        payload=f"tariff_{tariff.id}_{call.from_user.id}",
        provider_token="",  # пусто для Stars
        currency="XTR",
        prices=[LabeledPrice(label=tariff.name, amount=tariff.price_stars)],
    )
    await call.answer()


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery) -> None:
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def on_successful_payment(message: Message, user: User, db: AsyncSession) -> None:
    sp = message.successful_payment
    payload = sp.invoice_payload or ""

    # Подарочная покупка обрабатывается в gift.py
    if payload.startswith("gift_"):
        from handlers.user.gift import process_gift_payment
        await process_gift_payment(message, user, db, payload, sp.telegram_payment_charge_id)
        return

    if not payload.startswith("tariff_"):
        logger.warning("Неизвестный payload оплаты: %s", payload)
        return

    parts = payload.split("_")
    try:
        tariff_id = int(parts[1])
    except (IndexError, ValueError):
        logger.warning("Не удалось распарсить payload: %s", payload)
        return

    tariff = await tariffs_q.get_tariff(db, tariff_id)
    if tariff is None:
        await message.answer("⚠️ Тариф не найден, обратись в поддержку.")
        return

    await sub_service.activate_subscription(
        db,
        user,
        duration_days=tariff.duration_days,
        payment_method="stars",
        tariff_id=tariff.id,
        telegram_payment_charge_id=sp.telegram_payment_charge_id,
    )
    await message.answer(
        "✅ <b>Подписка активирована!</b> Приятного использования.",
        reply_markup=main_menu(),
    )
