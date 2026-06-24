"""Очистка устаревших записей и медиафайлов (крон-задача)."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select, update

from database.engine import SessionLocal
from database.models import MediaCache, MessageLog
from database.queries import settings as settings_q
from config import settings as cfg

logger = logging.getLogger(__name__)


async def run_cleanup() -> dict:
    now = datetime.now(timezone.utc)
    removed_files = 0
    freed_bytes = 0
    removed_rows = 0

    async with SessionLocal() as db:
        text_days = await settings_q.get_int_setting(db, "text_retention_days", cfg.text_retention_days)
        media_days = await settings_q.get_int_setting(db, "media_retention_days", cfg.media_retention_days)

        # 1. Очистка медиафайлов
        if media_days > 0:
            cutoff = now - timedelta(days=media_days)
            res = await db.execute(
                select(MessageLog).where(
                    MessageLog.local_path.is_not(None),
                    MessageLog.received_at < cutoff,
                )
            )
            for record in res.scalars().all():
                path = record.local_path
                if path and os.path.exists(path):
                    try:
                        freed_bytes += os.path.getsize(path)
                        os.remove(path)
                        removed_files += 1
                    except OSError as exc:
                        logger.warning("Не удалось удалить файл %s: %s", path, exc)
                record.local_path = None
            await db.commit()

            await db.execute(
                update(MediaCache)
                .where(MediaCache.last_used_at < cutoff)
                .values(local_path=None)
            )
            await db.commit()

        # 2. Очистка текстовых записей
        if text_days > 0:
            cutoff = now - timedelta(days=text_days)
            res = await db.execute(
                delete(MessageLog).where(
                    MessageLog.received_at < cutoff,
                    MessageLog.local_path.is_(None),
                )
            )
            removed_rows = res.rowcount or 0
            await db.commit()

            await db.execute(
                delete(MediaCache).where(
                    MediaCache.local_path.is_(None),
                    MediaCache.last_used_at < cutoff,
                )
            )
            await db.commit()

    result = {
        "removed_files": removed_files,
        "freed_mb": freed_bytes / 1024**2,
        "removed_rows": removed_rows,
    }
    logger.info(
        "Очистка завершена: файлов=%s, освобождено=%.2fМБ, записей=%s",
        removed_files, result["freed_mb"], removed_rows,
    )
    return result
