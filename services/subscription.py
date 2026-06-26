"""Логика активации, проверки и истечения подписок.

Соглашения:
  • tariffs.duration_days — длительность в ДНЯХ (None/0 = lifetime).
  • promo_codes.duration_days — длительность доступа в МИНУТАХ (None = lifetime);
    для отображения всегда используется promo_codes.duration_label.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.engine import SessionLocal
from database.models import PromoCode, Subscription, User
from database.queries import subscriptions as subs_q
from database.queries import users as users_q

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _active_future_expiry(user: User) -> datetime | None:
    """Возвращает текущий срок подписки, если он ещё активен (для продления)."""
    if user.subscription_status == "active" and user.subscription_expires_at:
        exp = user.subscription_expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp > _now():
            return exp
    return None


async def grant_access(
    db: AsyncSession,
    user: User,
    *,
    lifetime: bool,
    delta: timedelta | None,
    payment_method: str,
    tariff_id: int | None = None,
    promo_code_id: int | None = None,
    telegram_payment_charge_id: str | None = None,
) -> datetime | None:
    """Ядро активации. Возвращает expires_at (None = lifetime)."""
    if lifetime:
        status = "lifetime"
        expires_at: datetime | None = None
    else:
        assert delta is not None
        base = _active_future_expiry(user) or _now()
        status = "active"
        expires_at = base + delta

    await subs_q.create_subscription(
        db,
        user_id=user.telegram_id,
        tariff_id=tariff_id,
        expires_at=expires_at,
        payment_method=payment_method,
        promo_code_id=promo_code_id,
        telegram_payment_charge_id=telegram_payment_charge_id,
    )
    await users_q.update_subscription_fields(db, user.telegram_id, status, expires_at)
    user.subscription_status = status
    user.subscription_expires_at = expires_at
    logger.info("Подписка активирована: user=%s method=%s", user.telegram_id, payment_method)
    return expires_at


async def activate_subscription(
    db: AsyncSession,
    user: User,
    duration_days: int | None,
    payment_method: str,
    tariff_id: int | None = None,
    promo_code_id: int | None = None,
    telegram_payment_charge_id: str | None = None,
) -> datetime | None:
    """Активация по длительности в ДНЯХ (тарифы, ручная выдача)."""
    lifetime = duration_days is None or duration_days == 0
    delta = None if lifetime else timedelta(days=duration_days)
    return await grant_access(
        db, user,
        lifetime=lifetime,
        delta=delta,
        payment_method=payment_method,
        tariff_id=tariff_id,
        promo_code_id=promo_code_id,
        telegram_payment_charge_id=telegram_payment_charge_id,
    )


async def activate_promo(db: AsyncSession, user: User, promo: PromoCode) -> datetime | None:
    """Активация промокода (длительность в МИНУТАХ)."""
    lifetime = promo.duration_days is None
    delta = None if lifetime else timedelta(minutes=promo.duration_days)
    return await grant_access(
        db, user,
        lifetime=lifetime,
        delta=delta,
        payment_method="promo_code",
        promo_code_id=promo.id,
    )


def has_active_subscription(user: User) -> bool:
    if user.subscription_status == "lifetime":
        return True
    if user.subscription_status == "active":
        if user.subscription_expires_at is None:
            return True
        exp = user.subscription_expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return exp > _now()
    return False


async def check_expired_subscriptions() -> int:
    """Крон: помечает истёкшие подписки и уведомляет пользователей."""
    now = _now()
    async with SessionLocal() as db:
        res = await db.execute(
            select(User.telegram_id).where(
                User.subscription_status == "active",
                User.subscription_expires_at.is_not(None),
                User.subscription_expires_at < now,
            )
        )
        ids = [r[0] for r in res.all()]
        if ids:
            await db.execute(
                update(User).where(User.telegram_id.in_(ids)).values(subscription_status="expired")
            )
            await db.execute(
                update(Subscription)
                .where(Subscription.user_id.in_(ids), Subscription.is_active == True)  # noqa: E712
                .values(is_active=False)
            )
            await db.commit()
        logger.info("check_expired_subscriptions: помечено %s истёкших", len(ids))

    if ids:
        await _notify_expired(ids)

    return len(ids)


async def _notify_expired(user_ids: list[int]) -> None:
    from keyboards.user_kb import tariffs_kb
    from services.notifier import get_notifier
    from database.queries import tariffs as tariffs_q

    try:
        bot = get_notifier().bot
    except AssertionError:
        logger.warning("Notifier не инициализирован, уведомления об истечении не отправлены")
        return

    async with SessionLocal() as db:
        tariff_list = await tariffs_q.list_tariffs(db, only_active=True)
    kb = tariffs_kb(tariff_list, prefix="buy")

    for user_id in user_ids:
        try:
            await bot.send_message(
                user_id,
                "😔 <b>Ваша подписка истекла.</b>\n\n"
                "Оформите новую, чтобы продолжить получать уведомления об удалённых и изменённых сообщениях.",
                reply_markup=kb,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Не удалось уведомить %s об истечении подписки: %s", user_id, exc)
