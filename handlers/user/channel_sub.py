"""Обязательная подписка на канал — колбэки проверки."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from database.queries import messages as messages_q
from services.channel_sub import is_subscribed
from services.notifier import get_notifier

router = Router(name="channel-sub")


@router.callback_query(F.data == "checksub")
async def cb_check_sub(call: CallbackQuery, user: User) -> None:
    subscribed = await is_subscribed(call.bot, user.telegram_id, force=True)
    if not subscribed:
        await call.answer("Вы всё ещё не подписаны 🙁", show_alert=True)
        return
    await call.answer("✅ Подписка подтверждена!")
    if call.message:
        await call.message.answer("✅ Отлично, бот снова работает. Отправьте /start.")


@router.callback_query(F.data.startswith("subchk:"))
async def cb_check_sub_reveal(call: CallbackQuery, user: User, db: AsyncSession) -> None:
    """Раскрывает содержимое конкретного заблокированного уведомления (edited/deleted)."""
    _, kind, record_id_raw = call.data.split(":", 2)
    record_id = int(record_id_raw)

    subscribed = await is_subscribed(call.bot, user.telegram_id, force=True)
    if not subscribed:
        await call.answer("Вы всё ещё не подписаны 🙁", show_alert=True)
        return

    record = await messages_q.get_by_id(db, record_id)
    if record is None or record.user_id != user.telegram_id:
        await call.answer("Запись не найдена", show_alert=True)
        return

    await call.answer("✅ Подписка подтверждена!")
    notifier = get_notifier()
    if kind == "edited":
        await notifier.reveal_edited(user.telegram_id, record)
    else:
        await notifier.reveal_deleted(user.telegram_id, record)
