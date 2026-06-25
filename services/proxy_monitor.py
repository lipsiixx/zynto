"""Мониторинг стабильности активного прокси и предупреждения суперадмину.

Активный прокси выбирается один раз при старте (`select_proxy_session` в main.py)
и дальше не меняется. Этот сервис фоном периодически пингует Telegram через ту же
сессию (`bot.get_me`), измеряет задержку и считает неудачи. По скользящему окну
последних проверок определяет состояние прокси и шлёт суперадмину предупреждения:

  ⚠️  нестабилен          — растёт задержка или появляются редкие сбои;
  🟠  может скоро отключиться — несколько неудач подряд (связь вот-вот пропадёт);
  🔴  не отвечает          — соединение с Telegram потеряно;
  🟢  снова стабилен       — восстановление после проблемы.

Чтобы не спамить, повторное предупреждение об одном и том же состоянии шлётся не
чаще чем раз в RENOTIFY_AFTER. Восстановление подтверждается несколькими успешными
проверками подряд (защита от «мигания»).
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from enum import Enum

from aiogram import Bot

from config import mask_proxy, settings

logger = logging.getLogger(__name__)


class ProxyState(str, Enum):
    HEALTHY = "healthy"    # стабильно
    UNSTABLE = "unstable"  # высокая задержка / редкие сбои
    AT_RISK = "at_risk"    # сбои подряд — скоро отключится
    DOWN = "down"          # прокси не отвечает


_SEVERITY = {
    ProxyState.HEALTHY: 0,
    ProxyState.UNSTABLE: 1,
    ProxyState.AT_RISK: 2,
    ProxyState.DOWN: 3,
}

# Параметры мониторинга
PROBE_INTERVAL = 30        # секунд между проверками
PROBE_TIMEOUT = 8          # таймаут одной проверки
WINDOW_SIZE = 10           # сколько последних проверок учитываем
SLOW_LATENCY = 3.0         # секунд — порог «медленного» ответа (средний по окну)
UNSTABLE_FAILS = 3         # сбоев в окне → нестабильно
AT_RISK_FAILS = 2          # сбоев ПОДРЯД → риск отключения
DOWN_FAILS = 4             # сбоев ПОДРЯД → считаем отключённым
RECOVER_OK = 3             # успехов подряд → подтверждённое восстановление
RENOTIFY_AFTER = 30 * 60   # повтор предупреждения не чаще раза в 30 мин


class ProxyMonitor:
    def __init__(self, bot: Bot, proxy_url: str) -> None:
        self.bot = bot
        self.proxy_url = proxy_url
        self.masked = mask_proxy(proxy_url)
        self._task: asyncio.Task | None = None
        self._results: deque[bool] = deque(maxlen=WINDOW_SIZE)
        self._latencies: deque[float] = deque(maxlen=WINDOW_SIZE)
        self._consecutive_fails = 0
        self._consecutive_oks = 0
        self._state = ProxyState.HEALTHY
        self._last_notify = 0.0
        self._last_probe = 0.0

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run(), name="proxy-monitor")
            logger.info("Мониторинг прокси запущен: %s", self.masked)

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _run(self) -> None:
        # стартовая пауза, чтобы не пересекаться с инициализацией polling
        try:
            await asyncio.sleep(PROBE_INTERVAL)
            while True:
                latency = await self._probe()
                self._record(latency)
                await self._react(self._evaluate())
                await asyncio.sleep(PROBE_INTERVAL)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 — монитор не должен ронять процесс
            logger.exception("Сбой в мониторинге прокси, перезапуск через %d с", PROBE_INTERVAL)
            await asyncio.sleep(PROBE_INTERVAL)
            self._task = asyncio.create_task(self._run(), name="proxy-monitor")

    async def _probe(self) -> float | None:
        """Пингует Telegram через активную сессию. Задержка в секундах или None при сбое."""
        start = time.monotonic()
        try:
            await asyncio.wait_for(self.bot.get_me(), timeout=PROBE_TIMEOUT)
            return time.monotonic() - start
        except Exception as exc:  # noqa: BLE001
            logger.debug("Проба прокси не удалась: %s", exc)
            return None

    def _record(self, latency: float | None) -> None:
        self._last_probe = time.monotonic()
        ok = latency is not None
        self._results.append(ok)
        if ok:
            self._latencies.append(latency)
            self._consecutive_oks += 1
            self._consecutive_fails = 0
        else:
            self._consecutive_fails += 1
            self._consecutive_oks = 0

    def _evaluate(self) -> ProxyState:
        fails = self._results.count(False)
        avg = sum(self._latencies) / len(self._latencies) if self._latencies else 0.0
        if self._consecutive_fails >= DOWN_FAILS:
            return ProxyState.DOWN
        if self._consecutive_fails >= AT_RISK_FAILS:
            return ProxyState.AT_RISK
        if fails >= UNSTABLE_FAILS or avg >= SLOW_LATENCY:
            return ProxyState.UNSTABLE
        return ProxyState.HEALTHY

    async def _react(self, new_state: ProxyState) -> None:
        now = time.monotonic()

        if new_state == ProxyState.HEALTHY:
            # восстановление подтверждаем только после нескольких успехов подряд
            if self._state != ProxyState.HEALTHY and self._consecutive_oks >= RECOVER_OK:
                await self._notify(self._recovery_text())
                self._state = ProxyState.HEALTHY
                self._last_notify = 0.0
            return

        worsened = _SEVERITY[new_state] > _SEVERITY[self._state]
        stale = (now - self._last_notify) >= RENOTIFY_AFTER
        if worsened or stale:
            await self._notify(self._state_text(new_state))
            self._last_notify = now
        self._state = new_state

    def _stats(self) -> str:
        avg = sum(self._latencies) / len(self._latencies) if self._latencies else 0.0
        fails = self._results.count(False)
        total = len(self._results)
        return (
            f"Прокси: <code>{self.masked}</code>\n"
            f"Средняя задержка: {avg:.1f} с\n"
            f"Сбоев за последние {total} проверок: {fails}"
        )

    def _state_text(self, state: ProxyState) -> str:
        if state == ProxyState.DOWN:
            return (
                "🔴 <b>Прокси не отвечает</b>\n"
                f"{self._consecutive_fails} неудачных проверок подряд — "
                "связь с Telegram потеряна, бот может не получать сообщения.\n\n"
                f"{self._stats()}"
            )
        if state == ProxyState.AT_RISK:
            return (
                "🟠 <b>Прокси может скоро отключиться</b>\n"
                f"{self._consecutive_fails} сбоя подряд. Если так продолжится — "
                "бот потеряет связь с Telegram. Стоит подготовить запасной прокси.\n\n"
                f"{self._stats()}"
            )
        return (
            "⚠️ <b>Прокси нестабилен</b>\n"
            "Растёт задержка или появляются сбои — возможны пропуски сообщений.\n\n"
            f"{self._stats()}"
        )

    def _recovery_text(self) -> str:
        return (
            "🟢 <b>Прокси снова стабилен</b>\n"
            f"Соединение восстановлено.\n\n{self._stats()}"
        )

    # --- ручная проверка из админки ---

    _ICONS = {
        ProxyState.HEALTHY: "🟢",
        ProxyState.UNSTABLE: "⚠️",
        ProxyState.AT_RISK: "🟠",
        ProxyState.DOWN: "🔴",
    }
    _LABELS = {
        ProxyState.HEALTHY: "стабилен",
        ProxyState.UNSTABLE: "нестабилен",
        ProxyState.AT_RISK: "может скоро отключиться",
        ProxyState.DOWN: "не отвечает",
    }

    def _last_probe_age(self) -> str:
        if not self._results:
            return "ещё не проверялся"
        secs = int(time.monotonic() - self._last_probe)
        if secs < 60:
            return f"{secs} с назад"
        return f"{secs // 60} мин назад"

    def status_text(self) -> str:
        """Текущее состояние прокси для ручного просмотра в админке."""
        state = self._evaluate()
        running = "включён" if self._task is not None and not self._task.done() else "остановлен"
        return (
            f"{self._ICONS[state]} <b>Прокси: {self._LABELS[state]}</b>\n\n"
            f"{self._stats()}\n"
            f"Подряд неудач: {self._consecutive_fails}\n"
            f"Последняя проверка: {self._last_probe_age()}\n"
            f"Мониторинг: {running} (каждые {PROBE_INTERVAL} с)"
        )

    async def check_now(self) -> str:
        """Немедленно пингует прокси и возвращает свежий статус (без уведомлений)."""
        self._record(await self._probe())
        return self.status_text()

    async def _notify(self, text: str) -> None:
        logger.info("Состояние прокси %s: %s", self.masked, text.splitlines()[0])
        if not settings.superadmin_id:
            return
        try:
            await self.bot.send_message(settings.superadmin_id, text)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Не удалось отправить предупреждение о прокси: %s", exc)


# Активный монитор (создаётся в main.py при наличии прокси). None — прямое соединение.
monitor: ProxyMonitor | None = None
