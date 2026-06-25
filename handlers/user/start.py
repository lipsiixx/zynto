"""/start, главное меню, «Как это работает», /myid."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards.user_kb import back_to_menu, main_menu

router = Router(name="user-start")

WELCOME = (
    "👁 <b>Привет!</b> Я слежу за удалёнными и изменёнными сообщениями в твоей переписке.\n"
    "Если кто-то удалит или изменит сообщение — я сразу покажу тебе оригинал."
)

HOW_IT_WORKS = (
    "📖 <b>Как подключить мониторинг:</b>\n\n"
    "✅ <b>Telegram Premium не нужен</b> — подключить можно и без него.\n\n"
    "1️⃣ Перейди в Настройки → <b>Telegram для бизнеса</b> → <b>Чат-боты</b>\n"
    "2️⃣ Вставь и добавь меня: <code>@zynto_bot</code>\n"
    "3️⃣ Включи доступ ко всем чатам (управление сообщениями)\n\n"
    "📱 <b>iPhone:</b> прокрути вниз → «Добавьте бота»\n"
    "🤖 <b>Android:</b> Настройки → Аккаунт → прокрути вниз → «Готово»\n\n"
    "4️⃣ Вернись сюда и нажми «Подключить мониторинг»\n\n"
    "После подключения я начну перехватывать все сообщения и уведомлять тебя об "
    "удалениях и изменениях в реальном времени."
)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(WELCOME, reply_markup=main_menu())


@router.message(Command("myid"))
async def cmd_myid(message: Message) -> None:
    await message.answer(f"🆔 Твой Telegram ID: <code>{message.from_user.id}</code>")


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(WELCOME, reply_markup=main_menu())


@router.callback_query(F.data == "menu")
async def cb_menu(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_text(WELCOME, reply_markup=main_menu())
    await call.answer()


@router.callback_query(F.data == "how")
async def cb_how(call: CallbackQuery) -> None:
    await call.message.edit_text(HOW_IT_WORKS, reply_markup=back_to_menu())
    await call.answer()
