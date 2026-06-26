"""CRUD пользователей."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User


async def get_user(db: AsyncSession, telegram_id: int) -> User | None:
    res = await db.execute(select(User).where(User.telegram_id == telegram_id))
    return res.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    username = username.lstrip("@")
    res = await db.execute(select(User).where(func.lower(User.username) == username.lower()))
    return res.scalars().first()


async def get_or_create_user(
    db: AsyncSession,
    telegram_id: int,
    username: str | None,
    full_name: str,
    language_code: str | None = "ru",
) -> User:
    user = await get_user(db, telegram_id)
    now = datetime.now(timezone.utc)
    if user is None:
        user = User(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name or "",
            language_code=language_code or "ru",
            last_active_at=now,
        )
        db.add(user)
        await db.flush()
    else:
        changed = False
        if username != user.username:
            user.username = username
            changed = True
        if full_name and full_name != user.full_name:
            user.full_name = full_name
            changed = True
        user.last_active_at = now
        if user.is_blocked:
            user.is_blocked = False
            changed = True
        _ = changed
    await db.commit()
    await db.refresh(user)
    return user


async def set_banned(db: AsyncSession, telegram_id: int, banned: bool, reason: str | None = None) -> None:
    await db.execute(
        update(User)
        .where(User.telegram_id == telegram_id)
        .values(is_banned=banned, ban_reason=reason if banned else None)
    )
    await db.commit()


async def set_blocked(db: AsyncSession, telegram_id: int, blocked: bool) -> None:
    await db.execute(update(User).where(User.telegram_id == telegram_id).values(is_blocked=blocked))
    await db.commit()


async def update_subscription_fields(
    db: AsyncSession,
    telegram_id: int,
    status: str,
    expires_at: datetime | None,
) -> None:
    await db.execute(
        update(User)
        .where(User.telegram_id == telegram_id)
        .values(subscription_status=status, subscription_expires_at=expires_at)
    )
    await db.commit()


async def count_users(db: AsyncSession) -> int:
    return int((await db.execute(select(func.count(User.id)))).scalar() or 0)


async def count_new_users_since(db: AsyncSession, since: datetime) -> int:
    res = await db.execute(select(func.count(User.id)).where(User.created_at >= since))
    return int(res.scalar() or 0)


async def count_by_status(db: AsyncSession, status: str) -> int:
    res = await db.execute(select(func.count(User.id)).where(User.subscription_status == status))
    return int(res.scalar() or 0)


async def set_pending_promo(db: AsyncSession, telegram_id: int, promo_id: int | None) -> None:
    await db.execute(update(User).where(User.telegram_id == telegram_id).values(pending_promo_id=promo_id))
    await db.commit()


async def count_active_subscribers(db: AsyncSession) -> int:
    res = await db.execute(
        select(func.count(User.id)).where(User.subscription_status.in_(["active", "lifetime"]))
    )
    return int(res.scalar() or 0)
