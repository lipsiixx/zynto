"""Статистика бота (админ)."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.admin_kb import admin_back
from services import stats as stats_service
from utils.formatters import fmt_dt

router = Router(name="admin-stats")


@router.callback_query(F.data == "a:stats")
async def cb_stats(call: CallbackQuery, db: AsyncSession) -> None:
    s = await stats_service.collect_stats(db)
    text = (
        "📊 <b>Статистика бота</b>\n\n"
        "👥 <b>Пользователи:</b>\n"
        f"• Всего: {s['users_total']}\n"
        f"• С активной подпиской: {s['users_active_sub']}\n"
        f"• Новых сегодня: {s['users_new_today']}\n"
        f"• Новых за 7 дней: {s['users_new_week']}\n"
        f"• Новых за 30 дней: {s['users_new_month']}\n\n"
        "💰 <b>Подписки:</b>\n"
        f"• Активных: {s['sub_active']}\n"
        f"• Lifetime: {s['sub_lifetime']}\n"
        f"• Истёкших: {s['sub_expired']}\n\n"
        "📡 <b>Мониторинг:</b>\n"
        f"• Подключённых бизнес-аккаунтов: {s['biz_connected']}\n"
        f"• Сохранено сообщений всего: {s['messages_total']}\n"
        f"• Удалённых перехвачено: {s['messages_deleted']}\n"
        f"• Изменённых перехвачено: {s['messages_edited']}\n\n"
        "🎟 <b>Промокоды:</b>\n"
        f"• Создано: {s['promo_total']}\n"
        f"• Использовано: {s['promo_used']}\n\n"
        f"🕐 Обновлено: {fmt_dt(s['now'])}"
    )
    await call.message.edit_text(text, reply_markup=admin_back())
    await call.answer()
