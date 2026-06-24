"""Агрегация статистики бота."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from database.queries import business as business_q
from database.queries import messages as messages_q
from database.queries import promo_codes as promo_q
from database.queries import users as users_q


async def collect_stats(db: AsyncSession) -> dict:
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    return {
        "users_total": await users_q.count_users(db),
        "users_active_sub": await users_q.count_active_subscribers(db),
        "users_new_today": await users_q.count_new_users_since(db, day_ago),
        "users_new_week": await users_q.count_new_users_since(db, week_ago),
        "users_new_month": await users_q.count_new_users_since(db, month_ago),
        "sub_active": await users_q.count_by_status(db, "active"),
        "sub_lifetime": await users_q.count_by_status(db, "lifetime"),
        "sub_expired": await users_q.count_by_status(db, "expired"),
        "biz_connected": await business_q.count_active(db),
        "messages_total": await messages_q.count_all(db),
        "messages_deleted": await messages_q.count_deleted(db),
        "messages_edited": await messages_q.count_edited(db),
        "promo_total": await promo_q.count_all(db),
        "promo_used": await promo_q.count_used(db),
        "now": now,
    }
