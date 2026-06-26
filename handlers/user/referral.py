"""Реферальная программа: пригласить друга."""
from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery

from database.models import User
from database.queries import users as users_q
from keyboards.user_kb import back_to_menu
from sqlalchemy.ext.asyncio import AsyncSession

router = Router(name="user-referral")


@router.callback_query(F.data == "referral")
async def cb_referral(call: CallbackQuery, user: User, db: AsyncSession, bot: Bot) -> None:
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start=ref{user.telegram_id}"

    stats = await users_q.get_referral_stats_for_user(db, user.telegram_id)

    await call.message.edit_text(
        "👥 <b>Пригласи друга — получи бонус!</b>\n\n"
        "За каждого друга, который оформит подписку, "
        "ты получишь бесплатные дни доступа.\n\n"
        f"🔗 Твоя реферальная ссылка:\n<code>{link}</code>\n\n"
        f"👤 Приглашено: <b>{stats['total']}</b>\n"
        f"✅ Оплатили подписку: <b>{stats['rewarded']}</b>",
        reply_markup=back_to_menu(),
    )
    await call.answer()
