"""Состояние активного прокси (админ).

Активный прокси выбирается при старте (`select_proxy_session` в main.py); фоновый
`ProxyMonitor` пингует его и шлёт суперадмину предупреждения. Здесь — ручной просмотр
текущего состояния и кнопка немедленной перепроверки. Если бот подключён напрямую
(без прокси), монитор отсутствует — показываем это явно.
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery

from keyboards.admin_kb import admin_back, proxy_kb
from services import proxy_monitor as proxy_monitor_module

router = Router(name="admin-proxy")

_DIRECT_TEXT = (
    "🌐 <b>Прокси</b>\n\n"
    "Бот подключён к Telegram напрямую, без прокси.\n"
    "Мониторинг прокси не запущен."
)


async def _show(call: CallbackQuery, text: str) -> None:
    """Безопасно обновляет сообщение (глотает «message is not modified»)."""
    monitor = proxy_monitor_module.monitor
    kb = proxy_kb() if monitor is not None else admin_back()
    try:
        await call.message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        pass


@router.callback_query(F.data == "a:proxy")
async def cb_proxy(call: CallbackQuery) -> None:
    await call.answer()
    monitor = proxy_monitor_module.monitor
    text = monitor.status_text() if monitor is not None else _DIRECT_TEXT
    await _show(call, text)


@router.callback_query(F.data == "a:proxy_check")
async def cb_proxy_check(call: CallbackQuery) -> None:
    monitor = proxy_monitor_module.monitor
    if monitor is None:
        await call.answer()
        await _show(call, _DIRECT_TEXT)
        return
    await call.answer("Проверяю прокси…")
    text = await monitor.check_now()
    await _show(call, text)
