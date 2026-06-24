"""Генерация и активация промокодов."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import PromoCode


async def get_by_code(db: AsyncSession, code: str) -> PromoCode | None:
    res = await db.execute(select(PromoCode).where(func.upper(PromoCode.code) == code.upper()))
    return res.scalars().first()


async def create_promo(
    db: AsyncSession,
    code: str,
    created_by: int,
    duration_days: int | None,
    duration_label: str | None,
    code_expires_at: datetime | None,
    note: str | None,
) -> PromoCode:
    promo = PromoCode(
        code=code,
        created_by=created_by,
        duration_days=duration_days,
        duration_label=duration_label,
        code_expires_at=code_expires_at,
        note=note,
    )
    db.add(promo)
    await db.commit()
    await db.refresh(promo)
    return promo


async def mark_used(
    db: AsyncSession,
    promo: PromoCode,
    used_by: int,
    access_expires_at: datetime | None,
) -> None:
    promo.used_by = used_by
    promo.used_at = datetime.now(timezone.utc)
    promo.access_expires_at = access_expires_at
    await db.commit()


async def list_recent(db: AsyncSession, limit: int = 20, flt: str = "all") -> list[PromoCode]:
    now = datetime.now(timezone.utc)
    stmt = select(PromoCode)
    if flt == "active":
        stmt = stmt.where(PromoCode.used_by.is_(None)).where(
            (PromoCode.code_expires_at.is_(None)) | (PromoCode.code_expires_at > now)
        )
    elif flt == "used":
        stmt = stmt.where(PromoCode.used_by.is_not(None))
    elif flt == "expired":
        stmt = stmt.where(PromoCode.used_by.is_(None)).where(PromoCode.code_expires_at < now)
    stmt = stmt.order_by(desc(PromoCode.created_at)).limit(limit)
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def count_all(db: AsyncSession) -> int:
    return int((await db.execute(select(func.count(PromoCode.id)))).scalar() or 0)


async def count_used(db: AsyncSession) -> int:
    res = await db.execute(select(func.count(PromoCode.id)).where(PromoCode.used_by.is_not(None)))
    return int(res.scalar() or 0)
