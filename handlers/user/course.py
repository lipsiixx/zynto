"""Просмотр курса по использованию бота."""
from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.queries import settings as settings_q
from keyboards.user_kb import back_to_menu

router = Router(name="user-course")


async def send_course_after_activation(target: Message, db: AsyncSession, bot: Bot) -> None:
    """Отправляет курс отдельным сообщением после покупки/активации кода."""
    enabled = await settings_q.get_setting(db, "course_enabled", "0")
    if enabled != "1":
        return
    file_id = await settings_q.get_setting(db, "course_video_file_id")
    if not file_id:
        return
    caption = await settings_q.get_setting(db, "course_caption", "📚 Курс по использованию бота")
    await bot.send_video(
        target.chat.id,
        video=file_id,
        caption=f"🎓 <b>Курс по использованию бота</b>\n\n{caption}",
        reply_markup=back_to_menu(),
    )


@router.callback_query(F.data == "course")
async def cb_course(call: CallbackQuery, db: AsyncSession) -> None:
    enabled = await settings_q.get_setting(db, "course_enabled", "0")
    if enabled != "1":
        await call.answer("📚 Курс временно недоступен", show_alert=True)
        return
    file_id = await settings_q.get_setting(db, "course_video_file_id")
    if not file_id:
        await call.answer("📚 Курс ещё не загружен", show_alert=True)
        return
    caption = await settings_q.get_setting(db, "course_caption", "📚 Курс по использованию бота")
    await call.message.answer_video(
        video=file_id,
        caption=f"🎓 <b>Курс по использованию бота</b>\n\n{caption}",
        reply_markup=back_to_menu(),
    )
    await call.answer()
