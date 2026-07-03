"""Агрегаты по дням для страницы «Статистика» webapp-админки.

Все функции возвращают dict {"YYYY-MM-DD": count} только по дням, где есть
данные — нулевые дни дозаполняет вызывающий код (api/routers/webapp_admin.py),
чтобы не гонять пустые строки из БД.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import MessageLog, Subscription, User


def _since(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


async def _daily_counts(db: AsyncSession, column, since: datetime, *where) -> dict[str, int]:
    day = func.date_trunc("day", column).label("day")
    stmt = (
        select(day, func.count().label("cnt"))
        .where(column >= since, *where)
        .group_by(day)
    )
    res = await db.execute(stmt)
    return {row.day.strftime("%Y-%m-%d"): int(row.cnt) for row in res}


async def daily_new_users(db: AsyncSession, days: int) -> dict[str, int]:
    return await _daily_counts(db, User.created_at, _since(days))


async def daily_messages(
    db: AsyncSession, days: int, user_id: int | None = None
) -> dict[str, dict[str, int]]:
    """{'messages': {...}, 'deleted': {...}, 'edited': {...}} по дням.

    deleted/edited считаются по датам самих событий (deleted_at/edited_at),
    а не по дате получения сообщения.
    """
    since = _since(days)
    user_filter_msg = (MessageLog.user_id == user_id,) if user_id else ()
    return {
        "messages": await _daily_counts(db, MessageLog.received_at, since, *user_filter_msg),
        "deleted": await _daily_counts(
            db, MessageLog.deleted_at, since,
            MessageLog.is_deleted.is_(True), *user_filter_msg,
        ),
        "edited": await _daily_counts(
            db, MessageLog.edited_at, since,
            MessageLog.is_edited.is_(True), *user_filter_msg,
        ),
    }


async def daily_payments(db: AsyncSession, days: int) -> dict[str, dict[str, int]]:
    """{'total': {...}, 'paid': {...}} — все выдачи и только реальные оплаты."""
    since = _since(days)
    return {
        "total": await _daily_counts(db, Subscription.created_at, since),
        "paid": await _daily_counts(
            db, Subscription.created_at, since,
            Subscription.payment_method.in_(("stars", "tribute_sbp")),
        ),
    }
