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
from aiogram import Bot
from database.queries import business as business_q
from database.queries import promo_codes as promo_q
from database.queries import settings as settings_q
from database.queries import tariffs as tariffs_q
from database.queries import users as users_q
from handlers.user.course import send_course_after_activation
from keyboards.user_kb import (
    back_to_menu,
    main_menu_sub,
    renew_kb,
    subscribe_button,
    tariffs_kb,
)
from services import subscription as sub_service
from utils.formatters import days_left, subscription_status_text

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
        if user.subscription_status == "lifetime":
            status_line = "♾ <b>Навсегда</b>"
        else:
            left = days_left(user.subscription_expires_at)
            status_line = f"✅ Активна · {left}"
        text = f"💳 <b>Твоя подписка</b>\n\n{status_line}"
        markup = renew_kb()
    else:
        tariffs = await tariffs_q.list_tariffs(db, only_active=True)
        if not tariffs:
            text = "💳 Сейчас нет доступных тарифов. Загляни позже."
            markup = back_to_menu()
        else:
            # Показываем описания тарифов в тексте
            lines = ["💳 <b>Выбери тариф:</b>\n"]
            for t in tariffs:
                desc = t.description or ""
                lines.append(f"<b>{t.name}</b> — {t.price_stars}⭐\n{desc}")
            # Индикатор скидки
            if user.pending_promo_id:
                promo = await promo_q.get_by_id(db, user.pending_promo_id)
                if promo and promo_q.is_available(promo):
                    tariff_hint = f"тариф «{promo.discount_tariff_id}»" if promo.discount_tariff_id else "любой тариф"
                    if promo.discount_tariff_id:
                        t_obj = await tariffs_q.get_tariff(db, promo.discount_tariff_id)
                        tariff_hint = f"тариф «{t_obj.name}»" if t_obj else tariff_hint
                    lines.append(f"\n🎫 <b>Скидочный код активен:</b> −{promo.discount_stars}⭐ на {tariff_hint}")
            text = "\n\n".join(lines)
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
async def cb_buy(call: CallbackQuery, user: User, db: AsyncSession) -> None:
    tariff_id = int(call.data.split(":", 1)[1])
    tariff = await tariffs_q.get_tariff(db, tariff_id)
    if tariff is None or not tariff.is_active:
        await call.answer("Тариф недоступен", show_alert=True)
        return

    price = tariff.price_stars
    discount_note = ""

    if user.pending_promo_id is not None:
        promo = await promo_q.get_by_id(db, user.pending_promo_id)
        if promo and promo.code_type == "discount" and promo_q.is_available(promo):
            applies = promo.discount_tariff_id is None or promo.discount_tariff_id == tariff.id
            if applies:
                discount = min(promo.discount_stars or 0, price - 1)  # цена минимум 1 XTR
                price = price - discount
                discount_note = f" (скидка {discount}⭐)"

    await call.message.answer_invoice(
        title=tariff.name,
        description=(tariff.description or f"Подписка на мониторинг: {tariff.name}") + discount_note,
        payload=f"tariff_{tariff.id}_{call.from_user.id}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=tariff.name + discount_note, amount=price)],
    )
    await call.answer()


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery) -> None:
    await query.answer(ok=True)


async def _reward_referrer(db: AsyncSession, bot: Bot, user: User) -> None:
    if not user.referred_by or user.referral_rewarded:
        return
    bonus_days = await settings_q.get_int_setting(db, "referral_bonus_days", 1)
    if bonus_days <= 0:
        return
    referrer = await users_q.get_user(db, user.referred_by)
    if referrer is None:
        return
    await sub_service.activate_subscription(
        db, referrer, duration_days=bonus_days, payment_method="referral"
    )
    await users_q.set_referral_rewarded(db, user.telegram_id)
    label = "день" if bonus_days == 1 else f"{bonus_days} дн."
    try:
        await bot.send_message(
            referrer.telegram_id,
            f"🎉 <b>Твой друг оформил подписку!</b>\n\nТебе начислен бонус: +{label} бесплатного доступа.",
        )
    except Exception:  # noqa: BLE001
        pass


@router.message(F.successful_payment)
async def on_successful_payment(message: Message, user: User, db: AsyncSession, bot: Bot) -> None:
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

    # Записываем использование скидочного промокода если был применён
    if user.pending_promo_id is not None:
        promo = await promo_q.get_by_id(db, user.pending_promo_id)
        if promo and promo.code_type == "discount":
            applies = promo.discount_tariff_id is None or promo.discount_tariff_id == tariff.id
            if applies and promo_q.is_available(promo):
                await promo_q.record_use(db, promo, user.telegram_id)
        await users_q.set_pending_promo(db, user.telegram_id, None)

    await sub_service.activate_subscription(
        db,
        user,
        duration_days=tariff.duration_days,
        payment_method="stars",
        tariff_id=tariff.id,
        telegram_payment_charge_id=sp.telegram_payment_charge_id,
    )
    await _reward_referrer(db, bot, user)
    await message.answer(
        "✅ <b>Подписка активирована!</b> Приятного использования.",
        reply_markup=main_menu_sub(),
    )
    await send_course_after_activation(message, db, bot)
