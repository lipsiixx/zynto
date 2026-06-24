"""CRUD тарифов."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Subscription, Tariff


async def get_tariff(db: AsyncSession, tariff_id: int) -> Tariff | None:
    res = await db.execute(select(Tariff).where(Tariff.id == tariff_id))
    return res.scalar_one_or_none()


async def list_tariffs(db: AsyncSession, only_active: bool = True) -> list[Tariff]:
    stmt = select(Tariff)
    if only_active:
        stmt = stmt.where(Tariff.is_active == True)  # noqa: E712
    stmt = stmt.order_by(Tariff.sort_order, Tariff.price_stars)
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def create_tariff(
    db: AsyncSession,
    name: str,
    description: str | None,
    duration_days: int | None,
    price_stars: int,
    sort_order: int,
    created_by: int,
) -> Tariff:
    tariff = Tariff(
        name=name,
        description=description,
        duration_days=duration_days,
        price_stars=price_stars,
        sort_order=sort_order,
        created_by=created_by,
    )
    db.add(tariff)
    await db.commit()
    await db.refresh(tariff)
    return tariff


async def update_tariff(db: AsyncSession, tariff_id: int, **fields) -> Tariff | None:
    tariff = await get_tariff(db, tariff_id)
    if tariff is None:
        return None
    for key, value in fields.items():
        if value is not None and hasattr(tariff, key):
            setattr(tariff, key, value)
    await db.commit()
    await db.refresh(tariff)
    return tariff


async def toggle_tariff(db: AsyncSession, tariff_id: int) -> Tariff | None:
    tariff = await get_tariff(db, tariff_id)
    if tariff is None:
        return None
    tariff.is_active = not tariff.is_active
    await db.commit()
    await db.refresh(tariff)
    return tariff


async def count_subscriptions_for_tariff(db: AsyncSession, tariff_id: int) -> int:
    res = await db.execute(
        select(func.count(Subscription.id)).where(Subscription.tariff_id == tariff_id)
    )
    return int(res.scalar() or 0)


async def delete_tariff(db: AsyncSession, tariff_id: int) -> bool:
    """Удаляет тариф только если на него нет подписок."""
    if await count_subscriptions_for_tariff(db, tariff_id) > 0:
        return False
    tariff = await get_tariff(db, tariff_id)
    if tariff is None:
        return False
    await db.delete(tariff)
    await db.commit()
    return True
