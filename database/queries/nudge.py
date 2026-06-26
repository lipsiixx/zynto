"""CRUD для NudgeMessage и выборка пользователей для подначивания."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import NudgeMessage, User


async def list_nudge_messages(db: AsyncSession) -> list[NudgeMessage]:
    res = await db.execute(select(NudgeMessage).order_by(NudgeMessage.created_at))
    return list(res.scalars().all())


async def get_nudge_message(db: AsyncSession, msg_id: int) -> NudgeMessage | None:
    res = await db.execute(select(NudgeMessage).where(NudgeMessage.id == msg_id))
    return res.scalar_one_or_none()


async def get_random_active_nudge(db: AsyncSession) -> NudgeMessage | None:
    res = await db.execute(
        select(NudgeMessage).where(NudgeMessage.is_active.is_(True)).order_by(func.random())
    )
    return res.scalars().first()


async def create_nudge_message(db: AsyncSession, text: str) -> NudgeMessage:
    msg = NudgeMessage(text=text)
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


async def update_nudge_message(db: AsyncSession, msg_id: int, text: str) -> NudgeMessage | None:
    msg = await get_nudge_message(db, msg_id)
    if msg is None:
        return None
    msg.text = text
    await db.commit()
    return msg


async def toggle_nudge_message(db: AsyncSession, msg_id: int) -> NudgeMessage | None:
    msg = await get_nudge_message(db, msg_id)
    if msg is None:
        return None
    msg.is_active = not msg.is_active
    await db.commit()
    return msg


async def delete_nudge_message(db: AsyncSession, msg_id: int) -> bool:
    msg = await get_nudge_message(db, msg_id)
    if msg is None:
        return False
    await db.delete(msg)
    await db.commit()
    return True


async def get_users_to_schedule(db: AsyncSession, grace_days: int) -> list[User]:
    """Пользователи, которым нужно назначить время первой отправки."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=grace_days)
    res = await db.execute(
        select(User).where(
            User.subscription_status == "expired",
            User.subscription_expires_at <= cutoff,
            User.is_banned.is_(False),
            User.is_blocked.is_(False),
            User.nudge_next_at.is_(None),
        )
    )
    return list(res.scalars().all())


async def get_users_due_for_nudge(db: AsyncSession) -> list[User]:
    """Пользователи, у которых nudge_next_at уже наступил."""
    now = datetime.now(timezone.utc)
    res = await db.execute(
        select(User).where(
            User.nudge_next_at <= now,
            User.is_banned.is_(False),
            User.is_blocked.is_(False),
        )
    )
    return list(res.scalars().all())
