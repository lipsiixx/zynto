"""Состояние сервера (админ)."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.admin_kb import admin_back
from services import server_monitor
from utils.formatters import fmt_dt

router = Router(name="admin-server")


def _retention(days: int) -> str:
    return "вечно" if days == 0 else f"{days} дн."


@router.callback_query(F.data == "a:server")
async def cb_server(call: CallbackQuery, db: AsyncSession) -> None:
    await call.answer("Собираю данные…")
    s = await server_monitor.collect_server_info(db)
    text = (
        "🖥 <b>Состояние сервера</b>\n\n"
        "💻 <b>Система:</b>\n"
        f"• CPU: {s['cpu']:.0f}%\n"
        f"• RAM: {s['ram_used_gb']:.1f} GB / {s['ram_total_gb']:.1f} GB ({s['ram_percent']:.0f}%)\n"
        f"• Аптайм: {s['uptime_days']} дн. {s['uptime_hours']} ч.\n\n"
        "💾 <b>Диск:</b>\n"
        f"• Занято: {s['disk_used_gb']:.1f} GB / {s['disk_total_gb']:.1f} GB ({s['disk_percent']:.0f}%)\n"
        f"• Медиафайлов: {s['media_files']} ({s['media_gb']:.2f} GB)\n\n"
        "🗄 <b>База данных:</b>\n"
        f"• Размер БД: {s['db_size_mb']:.1f} MB\n"
        f"• Записей сообщений: {s['messages_count']}\n"
        f"• Записей медиакеша: {s['media_cache_count']}\n\n"
        "⚙️ <b>Настройки очистки:</b>\n"
        f"• Хранить тексты: {_retention(s['text_retention_days'])}\n"
        f"• Хранить медиа: {_retention(s['media_retention_days'])}\n\n"
        f"🕐 {fmt_dt(s['now'])}"
    )
    await call.message.edit_text(text, reply_markup=admin_back())
