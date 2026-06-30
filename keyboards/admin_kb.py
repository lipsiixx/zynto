"""Клавиатуры для админ-панели."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.models import Tariff


def admin_main(is_superadmin: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="💰 Тарифы", callback_data="a:tariffs")
    kb.button(text="🎟 Промокоды", callback_data="a:promo")
    kb.button(text="📊 Статистика", callback_data="a:stats")
    kb.button(text="🖥 Сервер", callback_data="a:server")
    kb.button(text="🌐 Прокси", callback_data="a:proxy")
    kb.button(text="👤 Пользователи", callback_data="a:users")
    kb.button(text="📢 Рассылка", callback_data="a:broadcast")
    kb.button(text="🤝 Рефералы", callback_data="a:referral")
    kb.button(text="📹 Курс для пользователей", callback_data="a:course")
    kb.button(text="💬 Подначивания", callback_data="a:nudge")
    kb.button(text="🏦 Tribute СБП", callback_data="a:tribute_settings")
    if is_superadmin:
        kb.button(text="👮 Управление админами", callback_data="a:admins")
        kb.button(text="⚙️ Настройки очистки", callback_data="a:cleanup")
    kb.adjust(1)
    return kb.as_markup()


def admin_back() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ В админку", callback_data="a:main")
    return kb.as_markup()


def proxy_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Проверить заново", callback_data="a:proxy_check")
    kb.button(text="⬅️ В админку", callback_data="a:main")
    kb.adjust(1)
    return kb.as_markup()


def tariffs_list_kb(tariffs: list[Tariff]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for t in tariffs:
        state = "👁" if t.is_active else "🙈"
        kb.button(text=f"{state} {t.name} — {t.price_stars}⭐",
                  callback_data=f"a:tariff:{t.id}")
    kb.adjust(1)
    kb.row(InlineKeyboardButton(
        text="➕ Создать тариф", callback_data="a:tariff_new"))
    kb.row(InlineKeyboardButton(text="⬅️ В админку", callback_data="a:main"))
    return kb.as_markup()


def tariff_actions_kb(tariff: Tariff) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ Редактировать",
              callback_data=f"a:tariff_edit:{tariff.id}")
    toggle = "🙈 Скрыть" if tariff.is_active else "👁 Показать"
    kb.button(text=toggle, callback_data=f"a:tariff_toggle:{tariff.id}")
    kb.button(text="🗑 Удалить", callback_data=f"a:tariff_del:{tariff.id}")
    kb.button(text="⬅️ К тарифам", callback_data="a:tariffs")
    kb.adjust(1)
    return kb.as_markup()


def tariff_edit_fields_kb(tariff_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    fields = [
        ("Название", "name"), ("Описание", "description"),
        ("Дни", "duration_days"), ("Цена", "price_stars"), ("Порядок", "sort_order"),
    ]
    for label, code in fields:
        kb.button(text=label, callback_data=f"a:tfield:{tariff_id}:{code}")
    kb.button(text="⬅️ Назад", callback_data=f"a:tariff:{tariff_id}")
    kb.adjust(2)
    return kb.as_markup()


def confirm_kb(yes_cb: str, no_cb: str = "a:main") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Создать", callback_data=yes_cb)
    kb.button(text="❌ Отмена", callback_data=no_cb)
    kb.adjust(2)
    return kb.as_markup()


def referral_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Вкл/Выкл программу", callback_data="a:referral_toggle")
    kb.button(text="✏️ Изменить кол-во дней", callback_data="a:referral_edit")
    kb.button(text="⬅️ В админку", callback_data="a:main")
    kb.adjust(1)
    return kb.as_markup()


def tribute_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Загрузить из Tribute", callback_data="a:tribute_load_products")
    kb.button(text="✏️ Изменить URL вручную", callback_data="a:tribute_set_url")
    kb.button(text="🗑 Сбросить", callback_data="a:tribute_clear_url")
    kb.button(text="⬅️ В админку", callback_data="a:main")
    kb.adjust(1)
    return kb.as_markup()


def tribute_set_url_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Отмена", callback_data="a:tribute_settings")
    return kb.as_markup()


def tribute_products_kb(products: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for i, p in enumerate(products):
        amount = p.get("amount", 0) / 100
        currency = p.get("currency", "")
        name = p.get("name", "Без названия")
        kb.button(text=f"{name} — {amount:g} {currency}", callback_data=f"a:tribute_pick:{i}")
    kb.adjust(1)
    kb.row(InlineKeyboardButton(text="⬅️ Отмена", callback_data="a:tribute_settings"))
    return kb.as_markup()


def broadcast_confirm_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Отправить", callback_data="a:broadcast_confirm")
    kb.button(text="❌ Отмена", callback_data="a:main")
    kb.adjust(2)
    return kb.as_markup()


def promo_type_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔑 Код доступа", callback_data="a:promotype:access")
    kb.button(text="🎫 Скидочный код", callback_data="a:promotype:discount")
    kb.button(text="⬅️ В промокоды", callback_data="a:promo")
    kb.adjust(1)
    return kb.as_markup()


def promo_max_uses_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="1️⃣ Одноразовый", callback_data="a:promouses:1")
    kb.button(text="♾ Без лимита", callback_data="a:promouses:0")
    kb.button(text="⬅️ В промокоды", callback_data="a:promo")
    kb.adjust(1)
    return kb.as_markup()


def promo_discount_tariff_kb(tariffs: list[Tariff]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🌐 Любой тариф", callback_data="a:promodtariff:any")
    for t in tariffs:
        kb.button(text=f"{t.name} — {t.price_stars}⭐", callback_data=f"a:promodtariff:{t.id}")
    kb.button(text="⬅️ В промокоды", callback_data="a:promo")
    kb.adjust(1)
    return kb.as_markup()


def promo_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Создать промокод", callback_data="a:promo_new")
    kb.button(text="📋 Список (все)", callback_data="a:promo_list:all")
    kb.button(text="🟢 Активные", callback_data="a:promo_list:active")
    kb.button(text="✅ Использованные", callback_data="a:promo_list:used")
    kb.button(text="⏰ Истёкшие", callback_data="a:promo_list:expired")
    kb.button(text="⬅️ В админку", callback_data="a:main")
    kb.adjust(1)
    return kb.as_markup()


def promo_duration_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    options = [
        ("1 минута", "m1"), ("1 час", "h1"), ("1 день", "d1"), ("7 дней", "d7"),
        ("1 месяц", "d30"), ("3 месяца", "d90"), ("Навсегда", "life"),
        ("Ввести вручную", "custom"),
    ]
    for label, code in options:
        kb.button(text=label, callback_data=f"a:promodur:{code}")
    kb.adjust(2)
    return kb.as_markup()


def cleanup_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ Срок хранения текстов", callback_data="a:cleanup_text")
    kb.button(text="✏️ Срок хранения медиа", callback_data="a:cleanup_media")
    kb.button(text="⬅️ В админку", callback_data="a:main")
    kb.adjust(1)
    return kb.as_markup()


def user_profile_kb(target_id: int, is_banned: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if is_banned:
        kb.button(text="✅ Разбанить", callback_data=f"a:unban:{target_id}")
    else:
        kb.button(text="🚫 Забанить", callback_data=f"a:ban:{target_id}")
    kb.button(text="🎁 Выдать подписку", callback_data=f"a:grant:{target_id}")
    kb.button(text="📋 История подписок", callback_data=f"a:subs:{target_id}")
    kb.button(text="⬅️ В админку", callback_data="a:main")
    kb.adjust(1)
    return kb.as_markup()


def admins_list_kb(admins) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for a in admins:
        name = a.full_name or (
            f"@{a.username}" if a.username else str(a.telegram_id))
        kb.button(text=f"🗑 {name}",
                  callback_data=f"a:admin_del:{a.telegram_id}")
    kb.adjust(1)
    kb.row(InlineKeyboardButton(
        text="➕ Добавить админа", callback_data="a:admin_add"))
    kb.row(InlineKeyboardButton(text="⬅️ В админку", callback_data="a:main"))
    return kb.as_markup()


def course_kb(is_enabled: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    toggle = "❌ Выключить курс" if is_enabled else "✅ Включить курс"
    kb.button(text=toggle, callback_data="a:course_toggle")
    kb.button(text="📹 Загрузить видео", callback_data="a:course_video")
    kb.button(text="✏️ Изменить подпись", callback_data="a:course_caption")
    kb.button(text="⬅️ В админку", callback_data="a:main")
    kb.adjust(1)
    return kb.as_markup()


def nudge_main_kb(is_enabled: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    toggle = "❌ Выключить" if is_enabled else "✅ Включить"
    kb.button(text=toggle, callback_data="a:nudge_toggle")
    kb.button(text="⏱ Периодичность", callback_data="a:nudge_set_interval")
    kb.button(text="⏳ Порог (дней после истечения)", callback_data="a:nudge_set_grace")
    kb.button(text="📝 Тексты сообщений", callback_data="a:nudge_msgs")
    kb.button(text="⬅️ В админку", callback_data="a:main")
    kb.adjust(1)
    return kb.as_markup()


def nudge_msgs_kb(messages) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for m in messages:
        active_icon = "🟢" if m.is_active else "🔴"
        media_icon = " 📷" if m.media_type == "photo" else (" 🎥" if m.media_type == "video" else "")
        raw = m.text or "(без текста)"
        preview = raw[:35].replace("\n", " ") + ("…" if len(raw) > 35 else "")
        kb.button(text=f"{active_icon}{media_icon} {preview}", callback_data=f"a:nudge_view:{m.id}")
    kb.adjust(1)
    kb.row(InlineKeyboardButton(text="➕ Добавить сообщение", callback_data="a:nudge_add"))
    kb.row(InlineKeyboardButton(text="⬅️ Настройки", callback_data="a:nudge"))
    return kb.as_markup()


def nudge_msg_kb(msg_id: int, is_active: bool, has_media: bool = False) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    toggle = "🔴 Деактивировать" if is_active else "🟢 Активировать"
    kb.button(text=toggle, callback_data=f"a:nudge_mtoggle:{msg_id}")
    kb.button(text="✏️ Редактировать", callback_data=f"a:nudge_edit:{msg_id}")
    if has_media:
        kb.button(text="🗑 Удалить медиа", callback_data=f"a:nudge_clearmedia:{msg_id}")
    kb.button(text="🗑 Удалить", callback_data=f"a:nudge_del:{msg_id}")
    kb.button(text="⬅️ К списку", callback_data="a:nudge_msgs")
    kb.adjust(1)
    return kb.as_markup()


def grant_tariffs_kb(tariffs: list[Tariff], target_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for t in tariffs:
        kb.button(text=f"{t.name}",
                  callback_data=f"a:grantt:{target_id}:{t.id}")
    kb.button(text="❌ Отмена", callback_data="a:main")
    kb.adjust(1)
    return kb.as_markup()
