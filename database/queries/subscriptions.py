"""Работа с подписками."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Subscription


async def create_subscription(
    db: AsyncSession,
    user_id: int,
    tariff_id: int | None,
    expires_at: datetime | None,
    payment_method: str,
    promo_code_id: int | None = None,
    telegram_payment_charge_id: str | None = None,
) -> Subscription:
    sub = Subscription(
        user_id=user_id,
        tariff_id=tariff_id,
        expires_at=expires_at,
        payment_method=payment_method,
        promo_code_id=promo_code_id,
        telegram_payment_charge_id=telegram_payment_charge_id,
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return sub


async def list_user_subscriptions(db: AsyncSession, user_id: int, limit: int = 20) -> list[Subscription]:
    res = await db.execute(
        select(Subscription)
        .where(Subscription.user_id == user_id)
        .order_by(desc(Subscription.created_at))
        .limit(limit)
    )
    return list(res.scalars().all())


async def get_active_subscription(db: AsyncSession, user_id: int) -> Subscription | None:
    res = await db.execute(
        select(Subscription)
        .where(Subscription.user_id == user_id, Subscription.is_active == True)  # noqa: E712
        .order_by(desc(Subscription.created_at))
        .limit(1)
    )
    return res.scalar_one_or_none()


async def count_active(db: AsyncSession) -> int:
    res = await db.execute(
        select(func.count(Subscription.id)).where(Subscription.is_active == True)  # noqa: E712
    )
    return int(res.scalar() or 0)
