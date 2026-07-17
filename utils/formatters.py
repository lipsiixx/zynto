"""Форматирование дат, текстов уведомлений и описаний типов."""
from __future__ import annotations

import html
from datetime import datetime, timezone, timedelta

MAX_TEXT_LEN = 1000

# Московское время UTC+3 — используем для всех отображаемых дат/времени
MSK = timezone(timedelta(hours=3))

# Дефолтное значение персональной настройки User.history_retention_hours (48ч =
# 2 дня) — используется как server_default в модели/миграции. Сама настройка
# управляет ОДНОВРЕМЕННО двумя вещами: окном видимости истории в мини-аппе
# (GET /webapp/contacts/{chat_id}/events, см. database/queries/webapp.py::
# get_contact_events) и порогом подавления Telegram-уведомлений об edit/delete
# (is_message_too_old_to_notify ниже). Не относится к retention в БД
# (services/cleaner.py, services/disk_monitor.py, /del) — то, что физически
# хранится, настраивается независимо через bot_settings.
DEFAULT_HISTORY_RETENTION_HOURS = 48

# Допустимые значения History Retention: 1-12 часов ИЛИ кратно 24 от 24 (1 день)
# до 168 (неделя). Единственный источник правды для валидации в API — сверяйся
# с этой функцией при описании контракта для фронтенда.
_VALID_RETENTION_DAY_HOURS = (24, 48, 72, 96, 120, 144, 168)


def is_valid_retention_hours(hours: int) -> bool:
    """1-12 часов ИЛИ кратно 24 от 24 (1 день) до 168 (неделя)."""
    if 1 <= hours <= 12:
        return True
    return hours in _VALID_RETENTION_DAY_HOURS

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
    return dt.astimezone(MSK).strftime("%d.%m.%Y %H:%M")


def fmt_date(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(MSK).strftime("%d.%m.%Y")


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


def days_left(dt: datetime | None) -> str:
    """Возвращает строку вида «осталось 3 дня» / «истекает сегодня»."""
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = dt - datetime.now(timezone.utc)
    days = delta.days
    if days < 0:
        return "истекла"
    if days == 0:
        return "истекает сегодня"
    if days == 1:
        return "остался 1 день"
    if 2 <= days <= 4:
        return f"осталось {days} дня"
    return f"осталось {days} дней"


def is_message_too_old_to_notify(record, retention_hours: int) -> bool:
    """True, если сообщение получено раньше retention_hours назад — уведомлять о его
    правке/удалении не нужно (сама запись в БД при этом обновляется как обычно).

    retention_hours — персональная настройка владельца (User.history_retention_hours),
    та же величина, что ограничивает видимость истории в мини-аппе.
    """
    received_at = getattr(record, "received_at", None)
    if received_at is None:
        return False
    if received_at.tzinfo is None:
        received_at = received_at.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - received_at > timedelta(hours=retention_hours)


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
