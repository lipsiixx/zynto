"""Агрегаты по дням для страницы «Статистика» webapp-админки.

Все функции возвращают dict {"YYYY-MM-DD": count} только по дням, где есть
данные — нулевые дни дозаполняет вызывающий код (api/routers/webapp_admin.py),
чтобы не гонять пустые строки из БД.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import case, desc, func, select
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


async def top_chats_for_user(db: AsyncSession, user_id: int, limit: int = 10) -> list[dict]:
    """С кем пользователь больше всего общается — по числу залогированных сообщений."""
    stmt = (
        select(
            MessageLog.chat_id,
            func.max(MessageLog.chat_title).label("title"),
            func.count().label("messages"),
            func.sum(case((MessageLog.is_deleted.is_(True), 1), else_=0)).label("deleted"),
            func.sum(case((MessageLog.is_edited.is_(True), 1), else_=0)).label("edited"),
        )
        .where(MessageLog.user_id == user_id)
        .group_by(MessageLog.chat_id)
        .order_by(desc("messages"))
        .limit(limit)
    )
    res = await db.execute(stmt)
    return [
        {
            "chat_id": row.chat_id,
            "title": row.title,
            "messages": int(row.messages),
            "deleted": int(row.deleted or 0),
            "edited": int(row.edited or 0),
        }
        for row in res
    ]


async def top_active_users(db: AsyncSession, days: int, limit: int = 10) -> list[dict]:
    """Топ владельцев бизнес-аккаунтов по числу сообщений за период."""
    stmt = (
        select(
            MessageLog.user_id,
            func.max(User.full_name).label("full_name"),
            func.max(User.username).label("username"),
            func.count(MessageLog.id).label("messages"),
        )
        .join(User, User.telegram_id == MessageLog.user_id)
        .where(MessageLog.received_at >= _since(days))
        .group_by(MessageLog.user_id)
        .order_by(desc("messages"))
        .limit(limit)
    )
    res = await db.execute(stmt)
    return [
        {
            "telegram_id": row.user_id,
            "full_name": row.full_name,
            "username": row.username,
            "messages": int(row.messages),
        }
        for row in res
    ]


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
