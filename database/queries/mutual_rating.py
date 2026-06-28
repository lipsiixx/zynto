"""CRUD для взаимного рейтинга (mutual_rating)."""
from __future__ import annotations

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import MutualRating


async def get_for_pair(db: AsyncSession, user_a: int, user_b: int) -> MutualRating | None:
    """Возвращает запись в любом направлении между двумя пользователями."""
    res = await db.execute(
        select(MutualRating).where(
            or_(
                and_(MutualRating.requester_id == user_a, MutualRating.target_id == user_b),
                and_(MutualRating.requester_id == user_b, MutualRating.target_id == user_a),
            )
        ).limit(1)
    )
    return res.scalar_one_or_none()


async def get_pending_incoming(db: AsyncSession, telegram_id: int) -> list[MutualRating]:
    """Входящие pending-запросы для пользователя."""
    res = await db.execute(
        select(MutualRating).where(
            MutualRating.target_id == telegram_id,
            MutualRating.status == "pending",
        )
    )
    return list(res.scalars().all())


async def create_request(
    db: AsyncSession,
    requester_id: int,
    target_id: int,
    requester_score: int,
) -> MutualRating:
    row = MutualRating(
        requester_id=requester_id,
        target_id=target_id,
        status="pending",
        requester_score=requester_score,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def accept(db: AsyncSession, row: MutualRating, target_score: int) -> MutualRating:
    row.target_score = target_score
    row.status = "active"
    rs = row.requester_score or 50
    row.mutual_score = round((rs + target_score) / 2)
    await db.commit()
    await db.refresh(row)
    return row


async def decline(db: AsyncSession, row: MutualRating) -> MutualRating:
    row.status = "declined"
    await db.commit()
    await db.refresh(row)
    return row


async def cancel(db: AsyncSession, row: MutualRating) -> MutualRating:
    row.status = "cancelled"
    await db.commit()
    await db.refresh(row)
    return row
