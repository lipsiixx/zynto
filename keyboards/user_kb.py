"""Клавиатуры для пользователей."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import settings
from database.models import Tariff
from utils.formatters import duration_text

_STARS_URL = "https://t.me/starsov?start=r8443013313"


def _add_stars_premium(kb: InlineKeyboardBuilder) -> None:
    kb.row(
        InlineKeyboardButton(text="⭐ Купить Stars", url=_STARS_URL),
        InlineKeyboardButton(text="💎 Купить Premium", url=_STARS_URL),
    )


def _miniapp_button(text: str = "📱 Открыть панель") -> InlineKeyboardButton:
    if settings.miniapp_url:
        return InlineKeyboardButton(text=text, web_app=WebAppInfo(url=settings.miniapp_url))
    # Fallback if MINIAPP_URL not configured
    return InlineKeyboardButton(text=text, callback_data="miniapp_unavailable")


def main_menu(subscribed: bool = True, connected: bool = False) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(_miniapp_button())
    kb.button(text="📋 Как подключить", callback_data="how_connect")
    if not subscribed:
        kb.button(text="❓ Как это работает", callback_data="how")
    kb.button(text="ℹ️ О боте", callback_data="about")
    kb.adjust(1)
    _add_stars_premium(kb)
    return kb.as_markup()


def main_menu_sub() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(_miniapp_button())
    kb.adjust(1)
    return kb.as_markup()


def back_to_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(_miniapp_button("📱 Открыть панель"))
    return kb.as_markup()


def subscribe_button() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(_miniapp_button("💳 Оформить подписку"))
    kb.adjust(1)
    _add_stars_premium(kb)
    return kb.as_markup()


def tariffs_kb(tariffs: list[Tariff], prefix: str = "buy") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for t in tariffs:
        kb.button(text=f"{t.name} — {t.price_stars} ⭐", callback_data=f"{prefix}:{t.id}")
    kb.row(_miniapp_button("📱 В панель"))
    kb.adjust(1)
    _add_stars_premium(kb)
    return kb.as_markup()


def renew_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Продлить", callback_data="renew")
    kb.row(_miniapp_button("📱 В панель"))
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
    kb.row(_miniapp_button("📱 В панель"))
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
    kb.row(_miniapp_button("📱 В панель"))
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
        kb.button(
            text=f"{t.name} ({duration_text(t.duration_days)}) — {t.price_stars} ⭐",
            callback_data=f"giftbuy:{t.id}",
        )
    kb.row(_miniapp_button("📱 В панель"))
    kb.adjust(1)
    return kb.as_markup()


def nudge_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(_miniapp_button("💳 Оформить подписку"))
    kb.adjust(1)
    _add_stars_premium(kb)
    return kb.as_markup()


def require_channel_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="📢 Подписаться", url=settings.required_channel_url))
    kb.row(InlineKeyboardButton(text="✅ Я подписался", callback_data="checksub"))
    return kb.as_markup()


def locked_notification_kb(kind: str, record_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="📢 Подписаться", url=settings.required_channel_url))
    kb.row(InlineKeyboardButton(text="✅ Я подписался", callback_data=f"subchk:{kind}:{record_id}"))
    return kb.as_markup()
