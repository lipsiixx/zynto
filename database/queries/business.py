"""Бизнес-подключения."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import BusinessConnection


async def get_by_connection_id(db: AsyncSession, bc_id: str) -> BusinessConnection | None:
    res = await db.execute(
        select(BusinessConnection).where(BusinessConnection.business_connection_id == bc_id)
    )
    return res.scalar_one_or_none()


async def get_active_for_user(db: AsyncSession, user_id: int) -> BusinessConnection | None:
    res = await db.execute(
        select(BusinessConnection)
        .where(BusinessConnection.user_id == user_id, BusinessConnection.is_active == True)  # noqa: E712
        .order_by(BusinessConnection.connected_at.desc())
    )
    return res.scalars().first()


async def upsert_connection(
    db: AsyncSession, user_id: int, bc_id: str, is_enabled: bool
) -> BusinessConnection:
    conn = await get_by_connection_id(db, bc_id)
    now = datetime.now(timezone.utc)
    if conn is None:
        conn = BusinessConnection(
            user_id=user_id,
            business_connection_id=bc_id,
            is_active=is_enabled,
            disconnected_at=None if is_enabled else now,
        )
        db.add(conn)
    else:
        conn.is_active = is_enabled
        conn.user_id = user_id
        conn.disconnected_at = None if is_enabled else now
    await db.commit()
    await db.refresh(conn)
    return conn


async def count_active(db: AsyncSession) -> int:
    res = await db.execute(
        select(func.count(BusinessConnection.id)).where(BusinessConnection.is_active == True)  # noqa: E712
    )
    return int(res.scalar() or 0)
