"""Фоновая рассылка сообщений всем пользователям — REST-версия `handlers/admin/broadcast.py`.

Модульный singleton: одновременно может выполняться только одна рассылка (проверяется
через `is_running()` до старта — вызывающий роутер отвечает 409 `already_running`).
Задача переживает конкретный HTTP-запрос, поэтому использует собственную
`SessionLocal`-сессию, а не `Depends(get_db)`.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import BufferedInputFile

from database.engine import SessionLocal
from database.queries import users as users_q

logger = logging.getLogger(__name__)


@dataclass
class _BroadcastStatus:
    running: bool = False
    total: int = 0
    sent: int = 0
    failed: int = 0
    blocked: int = 0
    finished_at: datetime | None = None

    def as_dict(self) -> dict:
        return {
            "running": self.running,
            "total": self.total,
            "sent": self.sent,
            "failed": self.failed,
            "blocked": self.blocked,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
        }


_status = _BroadcastStatus()
_task: asyncio.Task | None = None


def get_status() -> dict:
    return _status.as_dict()


def is_running() -> bool:
    return _status.running


async def start_broadcast(
    bot: Bot,
    admin_id: int,
    text: str | None,
    photo_bytes: bytes | None,
    photo_filename: str = "broadcast.jpg",
) -> int:
    """Запускает фоновую рассылку.

    Если фото передано — сначала отправляет его АДМИНУ (`admin_id`), чтобы получить
    file_id (см. контракт: пересылка по file_id остальным получателям, это же
    сообщение служит превью админу). Возвращает количество получателей.
    Бросает `RuntimeError`, если рассылка уже идёт.
    """
    global _task
    if _status.running:
        raise RuntimeError("already_running")

    async with SessionLocal() as db:
        recipients = await users_q.get_broadcast_recipients(db)

    photo_file_id: str | None = None
    if photo_bytes is not None:
        msg = await bot.send_photo(
            admin_id,
            BufferedInputFile(photo_bytes, filename=photo_filename),
            caption=text or None,
        )
        photo_file_id = msg.photo[-1].file_id

    _status.running = True
    _status.total = len(recipients)
    _status.sent = 0
    _status.failed = 0
    _status.blocked = 0
    _status.finished_at = None

    _task = asyncio.create_task(_run(bot, recipients, text, photo_file_id))
    return _status.total


async def _run(bot: Bot, recipients: list[int], text: str | None, photo_file_id: str | None) -> None:
    try:
        async with SessionLocal() as db:
            for uid in recipients:
                try:
                    if photo_file_id:
                        await bot.send_photo(uid, photo_file_id, caption=text or None)
                    else:
                        await bot.send_message(uid, text)
                    _status.sent += 1
                except TelegramForbiddenError:
                    await users_q.set_blocked(db, uid, True)
                    _status.blocked += 1
                    _status.failed += 1
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Broadcast: не удалось отправить %s: %s", uid, exc)
                    _status.failed += 1
                await asyncio.sleep(0.05)
    except Exception:  # noqa: BLE001 — задача не должна падать молча
        logger.exception("Broadcast job упал")
    finally:
        _status.running = False
        _status.finished_at = datetime.now(timezone.utc)
        logger.info(
            "Broadcast завершена: sent=%s failed=%s blocked=%s",
            _status.sent, _status.failed, _status.blocked,
        )
