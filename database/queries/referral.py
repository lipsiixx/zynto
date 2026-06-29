"""Queries для реферальной системы."""
from __future__ import annotations

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import ReferralReward, User


async def record_reward(
    db: AsyncSession,
    referrer_id: int,
    referred_id: int,
    days_granted: int,
    payment_method: str,
) -> ReferralReward:
    row = ReferralReward(
        referrer_id=referrer_id,
        referred_id=referred_id,
        days_granted=days_granted,
        payment_method=payment_method,
    )
    db.add(row)
    await db.flush()
    return row


async def get_stats_for_referrer(db: AsyncSession, referrer_id: int) -> dict:
    total_referred = int((await db.execute(
        select(func.count(User.id)).where(User.referred_by == referrer_id)
    )).scalar() or 0)

    rewards = (await db.execute(
        select(
            func.count(ReferralReward.id).label("count"),
            func.coalesce(func.sum(ReferralReward.days_granted), 0).label("days"),
        ).where(ReferralReward.referrer_id == referrer_id)
    )).one()

    # Уникальных рефералов, принёсших хотя бы одну награду
    converted = int((await db.execute(
        select(func.count(func.distinct(ReferralReward.referred_id)))
        .where(ReferralReward.referrer_id == referrer_id)
    )).scalar() or 0)

    return {
        "total_referred": total_referred,
        "total_converted": converted,
        "total_rewards": int(rewards.count),
        "total_days_earned": int(rewards.days),
    }


async def list_all_rewards(
    db: AsyncSession,
    page: int = 1,
    limit: int = 50,
) -> tuple[list[dict], int]:
    base = select(ReferralReward).order_by(desc(ReferralReward.created_at))
    total = int((await db.execute(
        select(func.count()).select_from(base.subquery())
    )).scalar() or 0)
    rows = list((await db.execute(
        base.limit(limit).offset((page - 1) * limit)
    )).scalars().all())

    # Подтягиваем имена пользователей
    referrer_ids = list({r.referrer_id for r in rows})
    referred_ids = list({r.referred_id for r in rows})
    all_ids = list(set(referrer_ids + referred_ids))

    name_map: dict[int, str] = {}
    if all_ids:
        users = (await db.execute(
            select(User.telegram_id, User.full_name, User.username)
            .where(User.telegram_id.in_(all_ids))
        )).all()
        for u in users:
            label = u.full_name or u.username or str(u.telegram_id)
            name_map[u.telegram_id] = label

    result = [
        {
            "id": r.id,
            "referrer_id": r.referrer_id,
            "referrer_name": name_map.get(r.referrer_id, str(r.referrer_id)),
            "referred_id": r.referred_id,
            "referred_name": name_map.get(r.referred_id, str(r.referred_id)),
            "days_granted": r.days_granted,
            "payment_method": r.payment_method,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
    return result, total
