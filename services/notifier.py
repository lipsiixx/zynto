"""Формирование и отправка уведомлений через asyncio-очередь.

Очередь + автомасштабируемый пул воркеров: уведомления разным пользователям
отправляются параллельно, поэтому медленная загрузка медиа одному не задерживает
остальных. Размер пула определяется автоматически по нагрузке (глубине очереди)
в пределах [MIN_WORKERS, MAX_WORKERS] — растёт под всплеск и сворачивается в простое.
Лимиты Telegram — на каждый чат отдельно, поэтому троттлим ПО ПОЛЬЗОВАТЕЛЮ
(>= PER_CHAT_DELAY между сообщениями одному), а не глобально.
"""
from __future__ import annotations

import asyncio
import logging
import os

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter

from database.engine import SessionLocal
from database.models import MessageLog
from database.queries import users as users_q
from services import media as media_service
from utils.formatters import esc, fmt_dt, truncate, type_label

logger = logging.getLogger(__name__)

PER_CHAT_DELAY = 0.05      # секунд между уведомлениями ОДНОМУ пользователю
MIN_WORKERS = 2           # сколько воркеров держим всегда
# Потолок ограничен не CPU (работа I/O-bound), а пропускной способностью Telegram
# (~30 сообщений/сек на бота) и пулом соединений. Берём разумный максимум.
MAX_WORKERS = max(8, min(32, (os.cpu_count() or 2) * 4))
BACKLOG_PER_WORKER = 4    # если в очереди > воркеров*это — добавляем воркеров
IDLE_TIMEOUT = 30.0       # сек простоя, после которых лишний воркер сворачивается
SCALE_INTERVAL = 1.0      # как часто супервайзер пересматривает размер пула


class Notifier:
    def __init__(
        self, bot: Bot, min_workers: int = MIN_WORKERS, max_workers: int = MAX_WORKERS
    ) -> None:
        self.bot = bot
        self.queue: asyncio.Queue[dict] = asyncio.Queue()
        self._min_workers = max(1, min_workers)
        self._max_workers = max(self._min_workers, max_workers)
        self._workers: set[asyncio.Task] = set()
        self._supervisor: asyncio.Task | None = None
        self._seq = 0
        self._running = False
        # Пер-пользовательские локи: сериализуют отправку одному адресату и
        # гарантируют паузу между его уведомлениями, не мешая другим.
        self._locks: dict[int, asyncio.Lock] = {}

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        for _ in range(self._min_workers):
            self._spawn_worker()
        self._supervisor = asyncio.create_task(self._supervise(), name="notifier-supervisor")
        logger.info(
            "Notifier запущен: воркеров %s..%s", self._min_workers, self._max_workers
        )

    async def stop(self) -> None:
        self._running = False
        if self._supervisor:
            self._supervisor.cancel()
            try:
                await self._supervisor
            except asyncio.CancelledError:
                pass
            self._supervisor = None
        for task in list(self._workers):
            task.cancel()
        for task in list(self._workers):
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._workers.clear()

    def _spawn_worker(self) -> None:
        self._seq += 1
        task = asyncio.create_task(self._worker(), name=f"notifier-{self._seq}")
        self._workers.add(task)

    async def _supervise(self) -> None:
        """Раз в SCALE_INTERVAL подгоняет число воркеров под глубину очереди."""
        while True:
            await asyncio.sleep(SCALE_INTERVAL)
            current = len(self._workers)
            backlog = self.queue.qsize()
            if current < self._max_workers and backlog > current * BACKLOG_PER_WORKER:
                target = min(self._max_workers, (backlog // BACKLOG_PER_WORKER) + 1)
                for _ in range(target - current):
                    self._spawn_worker()
                logger.debug("Notifier scale-up: %s -> %s (очередь %s)", current, len(self._workers), backlog)
            # Scale-down выполняют сами воркеры по IDLE_TIMEOUT (до MIN_WORKERS).

    def _lock_for(self, target: int) -> asyncio.Lock:
        lock = self._locks.get(target)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[target] = lock
        return lock

    async def notify_deleted(self, target_user_id: int, record: MessageLog) -> None:
        await self.queue.put({"kind": "deleted", "target": target_user_id, "record": record})

    async def notify_edited(self, target_user_id: int, record: MessageLog) -> None:
        await self.queue.put({"kind": "edited", "target": target_user_id, "record": record})

    async def _worker(self) -> None:
        task = asyncio.current_task()
        try:
            while True:
                try:
                    job = await asyncio.wait_for(self.queue.get(), timeout=IDLE_TIMEOUT)
                except asyncio.TimeoutError:
                    # Простаиваем — сворачиваемся, если воркеров больше минимума.
                    if len(self._workers) > self._min_workers:
                        return
                    continue
                try:
                    await self._handle(job)
                finally:
                    self.queue.task_done()
        finally:
            self._workers.discard(task)

    async def _handle(self, job: dict) -> None:
        target = job["target"]
        # Лок только на конкретного адресата → отправки разным людям параллельны.
        async with self._lock_for(target):
            try:
                await self._process(job)
            except TelegramRetryAfter as exc:
                logger.warning("FloodWait %s сек, повтор", exc.retry_after)
                await asyncio.sleep(exc.retry_after + 1)
                await self.queue.put(job)  # повторим позже
                return
            except TelegramForbiddenError:
                logger.info("Пользователь %s заблокировал бота", target)
                async with SessionLocal() as db:
                    await users_q.set_blocked(db, target, True)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Ошибка отправки уведомления: %s", exc)
            # Пауза держит лимит на один чат, но НЕ блокирует других адресатов.
            await asyncio.sleep(PER_CHAT_DELAY)

    async def _process(self, job: dict) -> None:
        kind = job["kind"]
        target = job["target"]
        record: MessageLog = job["record"]
        sender = esc(record.sender_name or "—")

        if kind == "deleted":
            await self._send_deleted(target, record, sender)
        elif kind == "edited":
            await self._send_edited(target, record, sender)

    async def _send_deleted(self, target: int, record: MessageLog, sender: str) -> None:
        when_del = fmt_dt(record.deleted_at)
        when_sent = fmt_dt(record.received_at)
        if record.file_id:
            caption = (
                f"🗑 <b>Удалено</b> • 👤 {sender} • 🕐 {when_del}\n"
                f"({type_label(record.message_type)})"
            )
            if record.text_content:
                caption += f"\n💬 {esc(truncate(record.text_content))}"
            await media_service.send_media(self.bot, target, record, caption)
        else:
            text = (
                f"🗑 <b>Сообщение удалено</b>\n\n"
                f"👤 От: {sender}\n"
                f"💬 {esc(truncate(record.text_content)) or '—'}\n"
                f"🕐 {when_del} (отправлено {when_sent})"
            )
            await self.bot.send_message(target, text)

    async def _send_edited(self, target: int, record: MessageLog, sender: str) -> None:
        when = fmt_dt(record.edited_at)
        was = esc(truncate(record.original_text)) or "—"
        now = esc(truncate(record.text_content)) or "—"
        if record.file_id:
            text = (
                f"✏️ <b>Подпись к медиафайлу изменена</b>\n\n"
                f"👤 От: {sender}\n"
                f"❌ Было: {was}\n"
                f"✅ Стало: {now}\n"
                f"🕐 {when}"
            )
        else:
            text = (
                f"✏️ <b>Сообщение изменено</b>\n\n"
                f"👤 От: {sender}\n"
                f"❌ Было: {was}\n"
                f"✅ Стало: {now}\n"
                f"🕐 {when}"
            )
        await self.bot.send_message(target, text)


# Глобальный экземпляр (инициализируется в main.py)
notifier: Notifier | None = None


def get_notifier() -> Notifier:
    assert notifier is not None, "Notifier не инициализирован"
    return notifier
