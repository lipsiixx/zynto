"""Мониторинг сервера: CPU, RAM, диск, размер БД."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import psutil
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.queries import media as media_q
from database.queries import messages as messages_q

logger = logging.getLogger(__name__)


def _dir_size(path: Path) -> tuple[int, int]:
    """Возвращает (кол-во файлов, суммарный размер в байтах)."""
    count = 0
    total = 0
    if not path.exists():
        return 0, 0
    for f in path.rglob("*"):
        if f.is_file():
            count += 1
            try:
                total += f.stat().st_size
            except OSError:
                pass
    return count, total


async def collect_server_info(db: AsyncSession) -> dict:
    cpu = psutil.cpu_percent(interval=0.5)
    vm = psutil.virtual_memory()
    disk = psutil.disk_usage(str(settings.media_path.anchor or settings.media_path))

    boot = datetime.fromtimestamp(psutil.boot_time(), tz=timezone.utc)
    uptime = datetime.now(timezone.utc) - boot

    media_files, media_bytes = _dir_size(settings.media_path)

    # Размер БД
    db_size_bytes = 0
    try:
        res = await db.execute(text("SELECT pg_database_size(current_database())"))
        db_size_bytes = int(res.scalar() or 0)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Не удалось получить размер БД: %s", exc)

    text_days = await _get_int_setting(db, "text_retention_days", settings.text_retention_days)
    media_days = await _get_int_setting(db, "media_retention_days", settings.media_retention_days)

    return {
        "cpu": cpu,
        "ram_used_gb": (vm.total - vm.available) / 1024**3,
        "ram_total_gb": vm.total / 1024**3,
        "ram_percent": vm.percent,
        "uptime_days": uptime.days,
        "uptime_hours": uptime.seconds // 3600,
        "disk_used_gb": disk.used / 1024**3,
        "disk_total_gb": disk.total / 1024**3,
        "disk_percent": disk.percent,
        "media_files": media_files,
        "media_gb": media_bytes / 1024**3,
        "db_size_mb": db_size_bytes / 1024**2,
        "messages_count": await messages_q.count_all(db),
        "media_cache_count": await media_q.count_all(db),
        "text_retention_days": text_days,
        "media_retention_days": media_days,
        "now": datetime.now(timezone.utc),
    }


async def _get_int_setting(db: AsyncSession, key: str, default: int) -> int:
    from database.queries import settings as settings_q
    return await settings_q.get_int_setting(db, key, default)
