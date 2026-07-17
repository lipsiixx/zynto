"""Мониторинг заполненности диска: внеплановая очистка БД/медиа при нехватке места."""
from __future__ import annotations

import logging
import shutil

from config import BASE_DIR
from services import cleaner

logger = logging.getLogger(__name__)

# При достижении этого порога использования диска запускаем ту же очистку,
# что и по суточному расписанию (services.cleaner.run_cleanup).
DISK_USAGE_THRESHOLD = 0.70


async def check_disk_usage() -> None:
    """Проверяет использование диска и при превышении порога чистит БД/медиа.

    В качестве пути берём config.BASE_DIR — это диск, на котором живёт код и
    локальные медиафайлы бота. В докер-компоузе бот и Postgres обычно сидят на
    одном хосте, так что это разумное приближение к реальному диску БД, но не
    гарантия для конфигураций с вынесенными volume'ами БД на отдельный диск.
    """
    usage = shutil.disk_usage(BASE_DIR)
    if usage.total <= 0:
        return
    used_ratio = usage.used / usage.total
    if used_ratio >= DISK_USAGE_THRESHOLD:
        logger.warning(
            "Диск заполнен на %.1f%% (порог %.0f%%) — запускаю внеплановую очистку",
            used_ratio * 100, DISK_USAGE_THRESHOLD * 100,
        )
        await cleaner.run_cleanup()
