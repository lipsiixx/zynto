"""Массовая очистка старых записей MessageLog по команде /del (глобально, все пользователи).

Отдельная сущность от retention-очистки в services/cleaner.py (та завязана на
настраиваемые text_retention_days/media_retention_days) — здесь фиксированный
порог в 2 дня и более узкое условие (не трогаем изменённые/удалённые/one-view
записи, т.к. они всё ещё представляют ценность для истории/статистики).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import MessageLog

# Порог "устаревшести" для /del. Совпадает по значению с константами видимости
# истории/уведомлений (utils/formatters.py), но задан отдельно: это ручная
# админская операция очистки БД, а не автоматическая логика показа/уведомлений.
PURGE_STALE_DAYS = 2


def _cutoff(now: datetime | None = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    return now - timedelta(days=PURGE_STALE_DAYS)


def _stale_filter(cutoff: datetime):
    return (
        MessageLog.received_at < cutoff,
        MessageLog.is_edited.is_(False),
        MessageLog.is_deleted.is_(False),
        MessageLog.is_view_once.is_(False),
    )


async def count_stale(db: AsyncSession, cutoff: datetime | None = None) -> int:
    cutoff = cutoff or _cutoff()
    res = await db.execute(select(func.count(MessageLog.id)).where(*_stale_filter(cutoff)))
    return int(res.scalar() or 0)


async def fetch_stale_with_files(db: AsyncSession, cutoff: datetime | None = None) -> list[tuple[int, str]]:
    """[(id, local_path)] только для записей с реальным локальным файлом на диске."""
    cutoff = cutoff or _cutoff()
    res = await db.execute(
        select(MessageLog.id, MessageLog.local_path).where(
            *_stale_filter(cutoff), MessageLog.local_path.is_not(None)
        )
    )
    return [(row[0], row[1]) for row in res.all()]


async def delete_stale(db: AsyncSession, cutoff: datetime | None = None) -> int:
    """Одним запросом удаляет все устаревшие строки. Возвращает число удалённых строк."""
    cutoff = cutoff or _cutoff()
    res = await db.execute(delete(MessageLog).where(*_stale_filter(cutoff)))
    await db.commit()
    return res.rowcount or 0
