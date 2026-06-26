"""/start, главное меню, «Как это работает», /myid."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from database.queries import business as business_q
from database.queries import users as users_q
from keyboards.user_kb import main_menu, main_menu_sub, back_to_menu
from services import subscription as sub_service
from utils.formatters import days_left, esc, subscription_status_text

router = Router(name="user-start")

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


async def _home_text(user: User, db: AsyncSession) -> tuple[str, object]:
    """Возвращает (текст, клавиатура) в зависимости от статуса пользователя."""
    first_name = (user.full_name or "").split()[0] if user.full_name else "друг"

    has_sub = sub_service.has_active_subscription(user)

    if not has_sub:
        text = (
            f"👋 Привет, <b>{esc(first_name)}</b>!\n\n"
            "Я слежу за удалёнными и изменёнными сообщениями "
            "в твоих бизнес-чатах и сразу показываю тебе оригинал.\n\n"
            "🔴 <b>Подписка:</b> не оформлена\n\n"
            "Оформи подписку, чтобы начать 👇"
        )
        return text, main_menu(subscribed=False)

    # Строка статуса подписки
    if user.subscription_status == "lifetime":
        sub_line = "♾ <b>Подписка:</b> навсегда"
    else:
        left = days_left(user.subscription_expires_at)
        sub_line = f"✅ <b>Подписка:</b> активна ({left})"

    # Статус мониторинга
    conn = await business_q.get_active_for_user(db, user.telegram_id)
    if conn:
        conn_line = "🟢 <b>Мониторинг:</b> активен"
        markup = main_menu(subscribed=True, connected=True)
    else:
        conn_line = "⚪ <b>Мониторинг:</b> не подключён → нажми «Подключить»"
        markup = main_menu(subscribed=True, connected=False)

    text = (
        f"👋 Привет, <b>{esc(first_name)}</b>!\n\n"
        f"{sub_line}\n"
        f"{conn_line}\n\n"
        "Выбери раздел 👇"
    )
    return text, markup


@router.message(CommandStart())
async def cmd_start(message: Message, user: User, db: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    # Обработка реферальной ссылки: /start ref123456789
    parts = message.text.split(maxsplit=1)
    if len(parts) > 1:
        payload = parts[1]
        if payload.startswith("ref"):
            try:
                referrer_id = int(payload[3:])
                if referrer_id != user.telegram_id and user.referred_by is None:
                    await users_q.set_referred_by(db, user.telegram_id, referrer_id)
                    await db.refresh(user)
            except ValueError:
                pass
    text, markup = await _home_text(user, db)
    await message.answer(text, reply_markup=markup)


@router.message(Command("myid"))
async def cmd_myid(message: Message) -> None:
    await message.answer(f"🆔 Твой Telegram ID: <code>{message.from_user.id}</code>")


@router.message(Command("menu"))
async def cmd_menu(message: Message, user: User, db: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    text, markup = await _home_text(user, db)
    await message.answer(text, reply_markup=markup)


@router.callback_query(F.data == "menu")
async def cb_menu(call: CallbackQuery, user: User, db: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    text, markup = await _home_text(user, db)
    await call.message.edit_text(text, reply_markup=markup)
    await call.answer()


@router.callback_query(F.data == "how")
async def cb_how(call: CallbackQuery) -> None:
    await call.message.edit_text(HOW_IT_WORKS, reply_markup=back_to_menu())
    await call.answer()
