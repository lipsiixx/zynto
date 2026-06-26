"""Рассылка сообщений всем пользователям (админ)."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.text_decorations import html_decoration

from database.models import Admin
from database.queries import users as users_q
from keyboards.admin_kb import admin_main, admin_back, broadcast_confirm_kb
from sqlalchemy.ext.asyncio import AsyncSession
from states.admin_states import BroadcastStates

logger = logging.getLogger(__name__)
router = Router(name="admin-broadcast")


@router.callback_query(F.data == "a:broadcast")
async def cb_broadcast(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BroadcastStates.waiting_content)
    await call.message.edit_text(
        "📢 <b>Рассылка</b>\n\n"
        "Отправь сообщение — текст или фото с подписью.\n"
        "Поддерживается форматирование (жирный, курсив и т.д.).\n\n"
        "Для отмены нажми ⬅️ или отправь /cancel",
        reply_markup=admin_back(),
    )
    await call.answer()


@router.message(BroadcastStates.waiting_content, F.text == "/cancel")
async def on_cancel(message: Message, state: FSMContext, admin: Admin) -> None:
    await state.clear()
    await message.answer("Рассылка отменена.", reply_markup=admin_main(admin.is_superadmin))


@router.message(BroadcastStates.waiting_content)
async def on_content(message: Message, state: FSMContext, db: AsyncSession) -> None:
    if message.photo:
        photo_id = message.photo[-1].file_id
        caption = html_decoration.unparse(message.caption or "", message.caption_entities or [])
        await state.update_data(photo_id=photo_id, caption=caption, text=None)
    elif message.text:
        await state.update_data(text=message.html_text, photo_id=None, caption=None)
    else:
        await message.answer("Поддерживаются только текст или фото с подписью. Попробуй ещё раз:")
        return

    await state.set_state(BroadcastStates.confirm)

    count = len(await users_q.get_broadcast_recipients(db))
    await message.answer("👁 <b>Предпросмотр:</b>")

    data = await state.get_data()
    if data.get("photo_id"):
        await message.answer_photo(data["photo_id"], caption=data["caption"] or None)
    else:
        await message.answer(data["text"])

    await message.answer(
        f"Получателей: <b>{count}</b>\nОтправить?",
        reply_markup=broadcast_confirm_kb(),
    )


@router.callback_query(BroadcastStates.confirm, F.data == "a:broadcast_confirm")
async def cb_confirm(call: CallbackQuery, state: FSMContext, db: AsyncSession, bot: Bot, admin: Admin) -> None:
    data = await state.get_data()
    await state.clear()

    recipients = await users_q.get_broadcast_recipients(db)
    await call.message.edit_text(f"📢 Рассылка запущена — {len(recipients)} получателей...")
    await call.answer()

    sent = 0
    failed = 0
    blocked = 0

    for uid in recipients:
        try:
            if data.get("photo_id"):
                await bot.send_photo(uid, data["photo_id"], caption=data["caption"] or None)
            else:
                await bot.send_message(uid, data["text"])
            sent += 1
        except TelegramForbiddenError:
            await users_q.set_blocked(db, uid, True)
            blocked += 1
            failed += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("Broadcast: не удалось отправить %s: %s", uid, exc)
            failed += 1
        await asyncio.sleep(0.05)

    logger.info("Broadcast завершена: sent=%s failed=%s blocked=%s by admin=%s", sent, failed, blocked, admin.telegram_id)
    await call.message.answer(
        f"✅ <b>Рассылка завершена</b>\n\n"
        f"📨 Отправлено: {sent}\n"
        f"❌ Не доставлено: {failed}\n"
        f"🚫 Заблокировали бота: {blocked}",
        reply_markup=admin_main(admin.is_superadmin),
    )
