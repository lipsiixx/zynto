"""Управление пользователями: поиск, бан/разбан, ручная выдача подписки."""
from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from database.queries import business as business_q
from database.queries import messages as messages_q
from database.queries import subscriptions as subs_q
from database.queries import tariffs as tariffs_q
from database.queries import users as users_q
from keyboards.admin_kb import admin_back, grant_tariffs_kb, user_profile_kb
from states.admin_states import BanUserStates, FindUserStates
from utils.formatters import fmt_dt, subscription_status_text

logger = logging.getLogger(__name__)
router = Router(name="admin-users")


async def _find_user(db: AsyncSession, identifier: str) -> User | None:
    identifier = identifier.strip()
    if identifier.startswith("@"):
        return await users_q.get_user_by_username(db, identifier)
    if identifier.isdigit():
        return await users_q.get_user(db, int(identifier))
    return await users_q.get_user_by_username(db, identifier)


async def _show_profile(target_msg: Message, db: AsyncSession, user: User, edit: bool) -> None:
    conn = await business_q.get_active_for_user(db, user.telegram_id)
    msg_count = await messages_q.count_for_user(db, user.telegram_id)
    text = (
        f"👤 <b>{user.full_name}</b> (@{user.username or '—'})\n"
        f"ID: <code>{user.telegram_id}</code>\n"
        f"Регистрация: {fmt_dt(user.created_at)}\n"
        f"Последняя активность: {fmt_dt(user.last_active_at)}\n"
        f"Подписка: {subscription_status_text(user.subscription_status, user.subscription_expires_at)}\n"
        f"Бизнес-подключение: {'активно' if conn else 'нет'}\n"
        f"Сообщений перехвачено: {msg_count}\n"
        f"Бан: {'да — ' + (user.ban_reason or '') if user.is_banned else 'нет'}"
    )
    markup = user_profile_kb(user.telegram_id, user.is_banned)
    if edit:
        await target_msg.edit_text(text, reply_markup=markup)
    else:
        await target_msg.answer(text, reply_markup=markup)


@router.callback_query(F.data == "a:users")
async def cb_users(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(FindUserStates.waiting_identifier)
    await call.message.edit_text(
        "👤 <b>Поиск пользователя</b>\nВведи @username или Telegram ID:",
        reply_markup=admin_back(),
    )
    await call.answer()


@router.message(Command("user"))
async def cmd_user(message: Message, db: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Использование: <code>/user @username</code> или <code>/user 123456789</code>")
        return
    user = await _find_user(db, parts[1])
    if user is None:
        await message.answer("Пользователь не найден.")
        return
    await _show_profile(message, db, user, edit=False)


@router.message(FindUserStates.waiting_identifier)
async def on_identifier(message: Message, db: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    user = await _find_user(db, message.text)
    if user is None:
        await message.answer("Пользователь не найден.", reply_markup=admin_back())
        return
    await _show_profile(message, db, user, edit=False)


@router.callback_query(F.data.startswith("a:unban:"))
async def cb_unban(call: CallbackQuery, db: AsyncSession) -> None:
    target_id = int(call.data.split(":")[-1])
    await users_q.set_banned(db, target_id, False)
    user = await users_q.get_user(db, target_id)
    await _show_profile(call.message, db, user, edit=True)
    await call.answer("Разбанен")


@router.callback_query(F.data.startswith("a:ban:"))
async def cb_ban(call: CallbackQuery, state: FSMContext) -> None:
    target_id = int(call.data.split(":")[-1])
    await state.set_state(BanUserStates.waiting_reason)
    await state.update_data(target_id=target_id)
    await call.message.answer("Введи причину бана:")
    await call.answer()


@router.message(BanUserStates.waiting_reason)
async def on_ban_reason(message: Message, db: AsyncSession, state: FSMContext) -> None:
    data = await state.get_data()
    target_id = data["target_id"]
    await state.clear()
    await users_q.set_banned(db, target_id, True, message.text.strip())
    user = await users_q.get_user(db, target_id)
    logger.info("Пользователь %s забанен", target_id)
    await _show_profile(message, db, user, edit=False)


@router.callback_query(F.data.startswith("a:grant:"))
async def cb_grant(call: CallbackQuery, db: AsyncSession) -> None:
    target_id = int(call.data.split(":")[-1])
    tariffs = await tariffs_q.list_tariffs(db, only_active=False)
    if not tariffs:
        await call.answer("Нет тарифов для выдачи", show_alert=True)
        return
    await call.message.edit_text(
        "🎁 Выбери тариф для ручной выдачи:", reply_markup=grant_tariffs_kb(tariffs, target_id)
    )
    await call.answer()


@router.callback_query(F.data.startswith("a:grantt:"))
async def cb_grant_tariff(call: CallbackQuery, db: AsyncSession, bot: Bot) -> None:
    from services import subscription as sub_service

    _, _, target_id_s, tariff_id_s = call.data.split(":")
    target_id = int(target_id_s)
    tariff = await tariffs_q.get_tariff(db, int(tariff_id_s))
    user = await users_q.get_user(db, target_id)
    if tariff is None or user is None:
        await call.answer("Не найдено", show_alert=True)
        return
    await sub_service.activate_subscription(
        db, user, duration_days=tariff.duration_days, payment_method="manual", tariff_id=tariff.id
    )
    logger.info("Ручная выдача подписки: target=%s tariff=%s", target_id, tariff.id)
    try:
        await bot.send_message(target_id, f"🎁 Тебе выдана подписка: <b>{tariff.name}</b>!")
    except Exception:  # noqa: BLE001
        pass
    await _show_profile(call.message, db, user, edit=True)
    await call.answer("Подписка выдана")


@router.callback_query(F.data.startswith("a:subs:"))
async def cb_subs(call: CallbackQuery, db: AsyncSession) -> None:
    target_id = int(call.data.split(":")[-1])
    subs = await subs_q.list_user_subscriptions(db, target_id)
    if not subs:
        await call.message.edit_text("История подписок пуста.", reply_markup=admin_back())
        await call.answer()
        return
    lines = []
    for s in subs:
        exp = fmt_dt(s.expires_at) if s.expires_at else "♾"
        lines.append(f"• {s.payment_method} • до {exp} • {fmt_dt(s.created_at)}")
    await call.message.edit_text(
        f"📋 <b>История подписок</b> (ID {target_id})\n\n" + "\n".join(lines),
        reply_markup=admin_back(),
    )
    await call.answer()
