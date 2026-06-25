"""Форматирование дат, текстов уведомлений и описаний типов."""
from __future__ import annotations

import html
from datetime import datetime, timezone

MAX_TEXT_LEN = 1000

MESSAGE_TYPE_LABELS = {
    "text": "текст",
    "photo": "📷 фото",
    "video": "🎬 видео",
    "audio": "🎵 аудио",
    "voice": "🎤 голосовое",
    "video_note": "⭕ видеосообщение",
    "document": "📄 документ",
    "sticker": "🪧 стикер",
    "animation": "🎞 GIF",
    "contact": "👤 контакт",
    "location": "📍 геолокация",
    "poll": "📊 опрос",
    "dice": "🎲 кубик",
    "story": "📖 история",
}


def fmt_dt(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%d.%m.%Y %H:%M")


def fmt_date(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%d.%m.%Y")


def type_label(message_type: str) -> str:
    return MESSAGE_TYPE_LABELS.get(message_type, message_type)


def truncate(text: str | None) -> str:
    if not text:
        return ""
    if len(text) > MAX_TEXT_LEN:
        return text[:MAX_TEXT_LEN] + "… [текст обрезан]"
    return text


def esc(text: str | None) -> str:
    return html.escape(text or "")


def user_mention(name: str | None, username: str | None, user_id: int | None) -> str:
    """Кликабельный тег пользователя: @username, иначе имя-ссылка на профиль."""
    if username:
        return f"@{esc(username)}"
    safe = esc(name) or "Неизвестно"
    if user_id:
        return f'<a href="tg://user?id={user_id}">{safe}</a>'
    return safe


def subscription_status_text(status: str, expires_at: datetime | None) -> str:
    if status == "lifetime":
        return "♾ Навсегда"
    if status == "active":
        return f"✅ активна до {fmt_dt(expires_at)}"
    if status == "expired":
        return "⏰ истекла"
    return "❌ нет"


def duration_text(duration_days: int | None) -> str:
    if duration_days is None:
        return "Навсегда"
    if duration_days == 0:
        return "Навсегда"
    if duration_days == 1:
        return "1 день"
    if duration_days % 30 == 0:
        months = duration_days // 30
        return f"{months} мес."
    return f"{duration_days} дн."
