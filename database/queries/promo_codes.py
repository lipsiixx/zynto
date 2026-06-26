"""Генерация и активация промокодов."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import PromoCode


def _now() -> datetime:
    return datetime.now(timezone.utc)


def is_available(promo: PromoCode) -> bool:
    """Можно ли ещё активировать этот код прямо сейчас."""
    if promo.code_expires_at is not None:
        exp = promo.code_expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < _now():
            return False
    # старый одноразовый (used_by заполнен, max_uses=1)
    if promo.max_uses == 1 and promo.used_by is not None:
        return False
    # новый с лимитом
    if promo.max_uses is not None and promo.uses_count >= promo.max_uses:
        return False
    return True


async def get_by_code(db: AsyncSession, code: str) -> PromoCode | None:
    res = await db.execute(select(PromoCode).where(func.upper(PromoCode.code) == code.upper()))
    return res.scalars().first()


async def get_by_id(db: AsyncSession, promo_id: int) -> PromoCode | None:
    res = await db.execute(select(PromoCode).where(PromoCode.id == promo_id))
    return res.scalar_one_or_none()


async def create_promo(
    db: AsyncSession,
    code: str,
    created_by: int,
    code_type: str,
    duration_days: int | None,
    duration_label: str | None,
    max_uses: int | None,
    code_expires_at: datetime | None,
    note: str | None,
    discount_stars: int | None = None,
    discount_tariff_id: int | None = None,
) -> PromoCode:
    promo = PromoCode(
        code=code,
        created_by=created_by,
        code_type=code_type,
        duration_days=duration_days,
        duration_label=duration_label,
        max_uses=max_uses,
        uses_count=0,
        code_expires_at=code_expires_at,
        note=note,
        discount_stars=discount_stars,
        discount_tariff_id=discount_tariff_id,
    )
    db.add(promo)
    await db.commit()
    await db.refresh(promo)
    return promo


async def record_use(
    db: AsyncSession,
    promo: PromoCode,
    user_id: int,
    access_expires_at: datetime | None = None,
) -> None:
    """Записывает одно использование кода."""
    promo.uses_count += 1
    promo.used_at = _now()
    if promo.max_uses == 1:
        # одноразовый — заполняем used_by для обратной совместимости
        promo.used_by = user_id
        promo.access_expires_at = access_expires_at
    await db.commit()


# backward-compat alias
async def mark_used(
    db: AsyncSession,
    promo: PromoCode,
    used_by: int,
    access_expires_at: datetime | None,
) -> None:
    await record_use(db, promo, used_by, access_expires_at)


async def list_recent(db: AsyncSession, limit: int = 20, flt: str = "all") -> list[PromoCode]:
    now = _now()
    stmt = select(PromoCode)

    not_expired_date = or_(PromoCode.code_expires_at.is_(None), PromoCode.code_expires_at > now)
    exhausted = or_(
        and_(PromoCode.max_uses == 1, PromoCode.used_by.is_not(None)),
        and_(PromoCode.max_uses.is_not(None), PromoCode.uses_count >= PromoCode.max_uses),
    )
    not_exhausted = or_(
        PromoCode.max_uses.is_(None),
        and_(PromoCode.max_uses == 1, PromoCode.used_by.is_(None)),
        and_(PromoCode.max_uses > 1, PromoCode.uses_count < PromoCode.max_uses),
    )

    if flt == "active":
        stmt = stmt.where(not_expired_date, not_exhausted)
    elif flt == "used":
        stmt = stmt.where(exhausted)
    elif flt == "expired":
        stmt = stmt.where(PromoCode.code_expires_at < now, not_exhausted)

    stmt = stmt.order_by(desc(PromoCode.created_at)).limit(limit)
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def count_all(db: AsyncSession) -> int:
    return int((await db.execute(select(func.count(PromoCode.id)))).scalar() or 0)


async def count_used(db: AsyncSession) -> int:
    res = await db.execute(select(func.count(PromoCode.id)).where(PromoCode.used_by.is_not(None)))
    return int(res.scalar() or 0)
