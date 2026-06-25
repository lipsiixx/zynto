"""/start, главное меню, «Как это работает», /myid."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards.user_kb import back_to_menu, main_menu

router = Router(name="user-start")

WELCOME = (
    "✨ <b>Добро пожаловать!</b>\n\n"
    "👁 <b>Я — бот-хранитель твоей переписки</b>\n"
    "Я слежу за удалёнными и изменёнными сообщениями в твоих чатах.\n\n"
    "🛡 <b>Как я работаю:</b>\n"
    "• Если кто-то удалит сообщение — я покажу тебе оригинал\n"
    "• Если кто-то изменит сообщение — я покажу, что было до правки\n\n"
    "⚠️ <b>Важно знать:</b>\n"
    "При подключении бота Telegram предупреждает о доступе к чату.\n"
    "Но не переживай — я <b>вижу только удалённые/изменённые</b> сообщения.\n"
    "Полного доступа к чату у меня <b>нет</b>.\n"
    "🔒 <b>Твои данные в полной безопасности!</b>\n\n"
    "❓ Вопросы или предложения?\n"
    "Обращайся к админам:\n"
    "👨‍💻 <a href='https://t.me/MARKBANDANA'>@MARKBANDANA</a>\n"
    "👨‍💻 <a href='https://t.me/whatever891'>@whatever891</a>"
)

HOW_IT_WORKS = (
    "📡 <b>Как подключить бота (3 простых шага):</b>\n\n"
    "1️⃣ <b>Открой настройки профиля</b>\n"
    "   📱 iPhone: Профиль → «Изменить»\n"
    "   🤖 Android: Настройки → «Аккаунт»\n\n"
    "2️⃣ <b>Найди раздел «Автоматизация чатов»</b>\n"
    "   Пролистай список вниз до этого пункта.\n\n"
    "3️⃣ <b>Введи имя бота и добавь его</b>\n"
    "   Напиши в поле: <code>@zynto_bot</code>\n"
    "   Нажми кнопку <b>«Добавить»</b> — готово!\n\n"
    "✅ <b>Telegram Premium не требуется</b> — работает с обычным аккаунтом.\n\n"
    "📌 После подключения бот пришлёт подтверждение автоматически."
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
