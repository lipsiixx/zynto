"""Вебхук Tribute (СБП-оплата): подписки и цифровые товары.

Tribute шлёт POST на /v1/tribute/webhook с заголовком trbt-signature —
HMAC-SHA256(raw_body, TRIBUTE_API_KEY) в hex. Любой неизвестный/неуспешный
кейс (кроме неверной подписи) отвечаем {"ok": True}, чтобы Tribute не ретраил.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging

from aiogram import Bot
from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings as cfg
from database.engine import SessionLocal
from database.queries import settings as settings_q
from database.queries import users as users_q
from services import subscription as sub_service
from utils.formatters import fmt_date

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tribute", tags=["tribute"])

_PERIOD_TO_DAYS = {
    "weekly": 7,
    "monthly": 30,
    "quarterly": 90,
    "yearly": 365,
}


def _period_to_days(period: str | None) -> int:
    return _PERIOD_TO_DAYS.get((period or "").lower(), 30)


def _verify_signature(raw: bytes, signature: str | None) -> bool:
    if not cfg.tribute_api_key:
        logger.warning("TRIBUTE_API_KEY не задан — пропускаем проверку подписи (dev-режим)")
        return True
    if not signature:
        return False
    expected = hmac.new(cfg.tribute_api_key.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _get_bot(request: Request) -> Bot | None:
    return getattr(request.app.state, "bot", None)


async def _notify(bot: Bot | None, telegram_id: int, expires_at) -> None:
    if bot is None:
        return
    period = "навсегда" if expires_at is None else f"до {fmt_date(expires_at)}"
    try:
        await bot.send_message(
            telegram_id,
            f"✅ <b>Подписка через СБП активирована!</b>\nДоступ открыт {period}.",
        )
    except Exception:  # noqa: BLE001
        logger.warning("Не удалось уведомить пользователя %s об активации Tribute", telegram_id)


@router.post("/webhook")
async def tribute_webhook(request: Request) -> dict:
    raw = await request.body()
    signature = request.headers.get("trbt-signature")

    if not _verify_signature(raw, signature):
        logger.warning("Tribute webhook: неверная подпись")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_signature")

    try:
        body = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        logger.warning("Tribute webhook: невалидный JSON")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_json")

    event_name = body.get("name")
    payload = body.get("payload") or {}
    bot = _get_bot(request)

    async with SessionLocal() as db:
        if event_name in ("new_subscription", "renewed_subscription"):
            await _handle_subscription(db, payload, bot)
        elif event_name == "cancelled_subscription":
            logger.info(
                "Tribute: cancelled_subscription subscription_id=%s expires_at=%s — доступ сохраняется до истечения",
                payload.get("subscription_id"), payload.get("expires_at"),
            )
        elif event_name == "new_digital_product":
            await _handle_digital_product(db, payload, bot)
        else:
            logger.info("Tribute webhook: необработанное событие %s", event_name)

    return {"ok": True}


async def _handle_subscription(db: AsyncSession, payload: dict, bot: Bot | None) -> None:
    telegram_user_id = payload.get("telegram_user_id")
    subscription_id = payload.get("subscription_id")
    period = payload.get("period")
    days = _period_to_days(period)

    user = await users_q.get_user(db, telegram_user_id)
    if user is None:
        logger.warning("Tribute: пользователь %s не найден (subscription_id=%s)", telegram_user_id, subscription_id)
        return

    try:
        expires_at = await sub_service.activate_subscription(
            db,
            user,
            duration_days=days,
            payment_method="tribute_sbp",
            telegram_payment_charge_id=f"tribute_sub_{subscription_id}",
        )
    except IntegrityError:
        await db.rollback()
        logger.info("Tribute: повторная доставка subscription_id=%s (дубль), игнорируем", subscription_id)
        return

    await _notify(bot, telegram_user_id, expires_at)


async def _handle_digital_product(db: AsyncSession, payload: dict, bot: Bot | None) -> None:
    telegram_user_id = payload.get("telegram_user_id")
    purchase_id = payload.get("purchase_id")

    user = await users_q.get_user(db, telegram_user_id)
    if user is None:
        logger.warning("Tribute: пользователь %s не найден (purchase_id=%s)", telegram_user_id, purchase_id)
        return

    days = await settings_q.get_int_setting(db, "tribute_digital_product_days", 30)

    try:
        expires_at = await sub_service.activate_subscription(
            db,
            user,
            duration_days=days,
            payment_method="tribute_sbp",
            telegram_payment_charge_id=f"tribute_product_{purchase_id}",
        )
    except IntegrityError:
        await db.rollback()
        logger.info("Tribute: повторная доставка purchase_id=%s (дубль), игнорируем", purchase_id)
        return

    await _notify(bot, telegram_user_id, expires_at)
