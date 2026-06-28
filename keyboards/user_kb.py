"""Клавиатуры для пользователей."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.models import Tariff
from utils.formatters import duration_text

_STARS_URL = "https://t.me/starsov?start=r8443013313"


def _add_stars_premium(kb: InlineKeyboardBuilder) -> None:
    """Добавляет кнопки покупки Stars и Premium в билдер."""
    kb.row(
        InlineKeyboardButton(text="⭐ Купить Stars", url=_STARS_URL),
        InlineKeyboardButton(text="💎 Купить Premium", url=_STARS_URL),
    )


def main_menu(subscribed: bool = True, connected: bool = False) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if not subscribed:
        kb.button(text="💳 Оформить подписку", callback_data="subscription")
        kb.button(text="🎟 Активировать промокод", callback_data="activate")
        kb.button(text="❓ Как это работает", callback_data="how")
        kb.adjust(1)
        _add_stars_premium(kb)
        return kb.as_markup()
    elif not connected:
        kb.button(text="📡 Подключить мониторинг", callback_data="connect")
        kb.button(text="💳 Подписка", callback_data="subscription")
        kb.button(text="👥 Пригласить друга", callback_data="referral")
        kb.button(text="🎁 Подарить подписку", callback_data="gift")
        kb.button(text="📚 Курс по использованию", callback_data="course")
        kb.button(text="❓ Как подключить", callback_data="how")
    else:
        kb.button(text="📋 История сообщений", callback_data="history")
        kb.button(text="📡 Мониторинг", callback_data="connect")
        kb.button(text="💳 Подписка", callback_data="subscription")
        kb.button(text="👥 Пригласить друга", callback_data="referral")
        kb.button(text="🎁 Подарить подписку", callback_data="gift")
        kb.button(text="📚 Курс по использованию", callback_data="course")
    kb.adjust(1)
    _add_stars_premium(kb)
    return kb.as_markup()


def main_menu_sub() -> InlineKeyboardMarkup:
    """Меню после успешной оплаты/активации — без статусного запроса к БД."""
    kb = InlineKeyboardBuilder()
    kb.button(text="📡 Подключить мониторинг", callback_data="connect")
    kb.button(text="📋 История сообщений", callback_data="history")
    kb.button(text="💳 Подписка", callback_data="subscription")
    kb.button(text="👥 Пригласить друга", callback_data="referral")
    kb.button(text="🎁 Подарить подписку", callback_data="gift")
    kb.button(text="📚 Курс по использованию", callback_data="course")
    kb.adjust(1)
    return kb.as_markup()


def back_to_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ В меню", callback_data="menu")
    return kb.as_markup()


def subscribe_button() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="💳 Оформить подписку", callback_data="subscription")
    kb.button(text="⬅️ В меню", callback_data="menu")
    kb.adjust(1)
    _add_stars_premium(kb)
    return kb.as_markup()


def tariffs_kb(tariffs: list[Tariff], prefix: str = "buy") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for t in tariffs:
        kb.button(text=f"{t.name} — {t.price_stars} ⭐", callback_data=f"{prefix}:{t.id}")
    kb.button(text="🎟 Активировать код", callback_data="activate")
    kb.button(text="⬅️ В меню", callback_data="menu")
    kb.adjust(1)
    _add_stars_premium(kb)
    return kb.as_markup()


def renew_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Продлить", callback_data="renew")
    kb.button(text="⬅️ В меню", callback_data="menu")
    kb.adjust(1)
    _add_stars_premium(kb)
    return kb.as_markup()


def history_chats_kb(chats: list[dict], page: int, total_pages: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for c in chats:
        title = c["chat_title"] or f"Чат {c['chat_id']}"
        label = f"{title} 🗑{c['deleted']} ✏️{c['edited']}"
        kb.button(text=label, callback_data=f"chat:{c['chat_id']}:0:all")
    kb.adjust(1)
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀ Назад", callback_data=f"histpage:{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="Вперёд ▶", callback_data=f"histpage:{page + 1}"))
    if nav:
        kb.row(*nav)
    kb.row(InlineKeyboardButton(text="⬅️ В меню", callback_data="menu"))
    return kb.as_markup()


def chat_events_kb(
    chat_id: int, page: int, total_pages: int, flt: str
) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    filters = [("Все", "all"), ("🗑 Удал.", "deleted"), ("✏️ Изм.", "edited"), ("📎 Медиа", "media")]
    for label, code in filters:
        mark = "• " if code == flt else ""
        kb.button(text=f"{mark}{label}", callback_data=f"chat:{chat_id}:0:{code}")
    kb.adjust(4)
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀", callback_data=f"chat:{chat_id}:{page - 1}:{flt}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="▶", callback_data=f"chat:{chat_id}:{page + 1}:{flt}"))
    if nav:
        kb.row(*nav)
    kb.row(
        InlineKeyboardButton(text="📎 Медиафайлы", callback_data=f"media:{chat_id}:0"),
        InlineKeyboardButton(text="🔍 Поиск", callback_data=f"search:{chat_id}"),
    )
    kb.row(InlineKeyboardButton(text="⬅️ К списку", callback_data="history"))
    return kb.as_markup()


def media_gallery_kb(chat_id: int, page: int, total_pages: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀ Назад", callback_data=f"media:{chat_id}:{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="Вперёд ▶", callback_data=f"media:{chat_id}:{page + 1}"))
    if nav:
        kb.row(*nav)
    kb.row(InlineKeyboardButton(text="⬅️ К чату", callback_data=f"chat:{chat_id}:0:all"))
    return kb.as_markup()


def gift_tariffs_kb(tariffs: list[Tariff]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for t in tariffs:
        kb.button(text=f"{t.name} ({duration_text(t.duration_days)}) — {t.price_stars} ⭐",
                  callback_data=f"giftbuy:{t.id}")
    kb.button(text="⬅️ В меню", callback_data="menu")
    kb.adjust(1)
    return kb.as_markup()


def nudge_kb() -> InlineKeyboardMarkup:
    """Клавиатура к подначивающему сообщению: подписка + Stars/Premium."""
    kb = InlineKeyboardBuilder()
    kb.button(text="💳 Оформить подписку", callback_data="subscription")
    kb.adjust(1)
    _add_stars_premium(kb)
    return kb.as_markup()
