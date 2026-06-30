"""Одноразовый скрипт: удаляет ВСЕ медиа-записи из messages_log и очищает media_cache.

Контекст: до фичи "Медиа = только удалённое + одноразовое" в БД накопились записи
messages_log с обычным (не удалённым, не view-once) медиа, которое больше не должно
попадать в выдачу мини-аппа. Этот скрипт физически удаляет такие записи (и файлы на
диске), чтобы не копить мёртвый вес — фильтрация в queries их и так больше не отдаёт,
но строки/файлы продолжали бы занимать место.

ВАЖНО: скрипт удаляет данные безвозвратно. Запускать только вручную, после явного
ревью и разрешения. НЕ вызывается из кода приложения, не импортируется нигде.

Запуск (из корня проекта, с активным venv):
    python scripts/purge_media.py            # сухой прогон с подтверждением
    python scripts/purge_media.py --yes       # без интерактивного подтверждения

Что делает:
  1. Находит все строки messages_log, где file_id IS NOT NULL (т.е. с медиа).
  2. Для каждой — если local_path задан и существует на диске и находится внутри
     settings.media_path — удаляет файл.
  3. Удаляет (DELETE) сами строки messages_log с медиа. Текстовые сообщения без
     медиа НЕ затрагиваются.
  4. Полностью очищает таблицу media_cache (TRUNCATE) — она хранит only-media записи
     и после удаления messages_log стала бы содержать орфанные ссылки.
  5. Печатает итоговую статистику: сколько строк и файлов удалено.

Скрипт НЕ трогает другие таблицы (users, payments, promo_codes, и т.д.).
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Позволяет запускать как `python scripts/purge_media.py` из корня проекта.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, text  # noqa: E402

from config import settings  # noqa: E402
from database.engine import SessionLocal, dispose_db  # noqa: E402
from database.models import MessageLog  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("purge_media")


def _safe_unlink(local_path: str | None) -> bool:
    """Удаляет файл, только если путь существует и лежит внутри settings.media_path.

    Возвращает True, если файл реально удалён."""
    if not local_path:
        return False
    try:
        path = Path(local_path).resolve()
        media_root = settings.media_path.resolve()
        # Path внутри media_root (защита от выхода за пределы media-директории).
        path.relative_to(media_root)
    except (ValueError, OSError):
        logger.warning("Пропуск файла вне media_path (или некорректный путь): %s", local_path)
        return False

    if not path.exists() or not path.is_file():
        return False

    try:
        path.unlink()
        return True
    except OSError as exc:
        logger.warning("Не удалось удалить файл %s: %s", path, exc)
        return False


async def purge(dry_run: bool = False) -> None:
    async with SessionLocal() as db:
        res = await db.execute(select(MessageLog).where(MessageLog.file_id.is_not(None)))
        records = list(res.scalars().all())
        total_rows = len(records)
        logger.info("Найдено %s строк messages_log с медиа.", total_rows)

        if dry_run:
            logger.info("Сухой прогон (--dry-run): ничего не удаляю.")
            await dispose_db()
            return

        deleted_files = 0
        for record in records:
            if _safe_unlink(record.local_path):
                deleted_files += 1

        ids = [r.id for r in records]
        if ids:
            await db.execute(
                MessageLog.__table__.delete().where(MessageLog.id.in_(ids))
            )

        # media_cache теперь содержит только орфанные ссылки на удалённые файлы — чистим целиком.
        await db.execute(text("TRUNCATE TABLE media_cache RESTART IDENTITY"))

        await db.commit()

        logger.info(
            "Готово: удалено строк messages_log=%s, файлов с диска=%s, media_cache очищен.",
            total_rows, deleted_files,
        )

    await dispose_db()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--yes", action="store_true",
        help="Не спрашивать подтверждение перед удалением.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Только посчитать, что будет удалено, без реального удаления.",
    )
    args = parser.parse_args()

    if not args.dry_run and not args.yes:
        answer = input(
            "Это БЕЗВОЗВРАТНО удалит все строки messages_log с медиа (включая файлы на диске) "
            "и очистит media_cache. Продолжить? [yes/N]: "
        )
        if answer.strip().lower() != "yes":
            logger.info("Отменено пользователем.")
            return

    asyncio.run(purge(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
