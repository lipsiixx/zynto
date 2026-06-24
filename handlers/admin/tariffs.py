"""Управление тарифами: список, создание (FSM), редактирование, скрытие, удаление."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Admin
from database.queries import tariffs as tariffs_q
from keyboards.admin_kb import (
    admin_back,
    confirm_kb,
    tariff_actions_kb,
    tariff_edit_fields_kb,
    tariffs_list_kb,
)
from states.admin_states import CreateTariffStates, EditTariffStates
from utils.formatters import duration_text

router = Router(name="admin-tariffs")


def _tariff_card(t) -> str:
    return (
        f"💰 <b>{t.name}</b>\n"
        f"Описание: {t.description or '—'}\n"
        f"Срок: {duration_text(t.duration_days)}\n"
        f"Цена: {t.price_stars} ⭐\n"
        f"Порядок: {t.sort_order}\n"
        f"Статус: {'активен 👁' if t.is_active else 'скрыт 🙈'}"
    )


@router.callback_query(F.data == "a:tariffs")
async def cb_tariffs(call: CallbackQuery, db: AsyncSession) -> None:
    tariffs = await tariffs_q.list_tariffs(db, only_active=False)
    text = "💰 <b>Тарифы</b>" if tariffs else "💰 Тарифов пока нет."
    await call.message.edit_text(text, reply_markup=tariffs_list_kb(tariffs))
    await call.answer()


@router.callback_query(F.data.startswith("a:tariff:"))
async def cb_tariff(call: CallbackQuery, db: AsyncSession) -> None:
    tariff_id = int(call.data.split(":")[-1])
    tariff = await tariffs_q.get_tariff(db, tariff_id)
    if tariff is None:
        await call.answer("Тариф не найден", show_alert=True)
        return
    await call.message.edit_text(_tariff_card(tariff), reply_markup=tariff_actions_kb(tariff))
    await call.answer()


@router.callback_query(F.data.startswith("a:tariff_toggle:"))
async def cb_toggle(call: CallbackQuery, db: AsyncSession) -> None:
    tariff_id = int(call.data.split(":")[-1])
    tariff = await tariffs_q.toggle_tariff(db, tariff_id)
    if tariff is None:
        await call.answer("Тариф не найден", show_alert=True)
        return
    await call.message.edit_text(_tariff_card(tariff), reply_markup=tariff_actions_kb(tariff))
    await call.answer("Готово")


@router.callback_query(F.data.startswith("a:tariff_del:"))
async def cb_delete(call: CallbackQuery, db: AsyncSession) -> None:
    tariff_id = int(call.data.split(":")[-1])
    ok = await tariffs_q.delete_tariff(db, tariff_id)
    if not ok:
        await call.answer("Нельзя удалить: есть подписки на этот тариф или тариф не найден.", show_alert=True)
        return
    tariffs = await tariffs_q.list_tariffs(db, only_active=False)
    await call.message.edit_text("🗑 Тариф удалён.", reply_markup=tariffs_list_kb(tariffs))
    await call.answer()


# ───────────────────────── создание тарифа (FSM) ─────────────────────────
@router.callback_query(F.data == "a:tariff_new")
async def cb_new(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(CreateTariffStates.waiting_name)
    await call.message.answer("➕ <b>Новый тариф</b>\nВведи название тарифа:")
    await call.answer()


@router.message(CreateTariffStates.waiting_name)
async def st_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text.strip())
    await state.set_state(CreateTariffStates.waiting_description)
    await message.answer("Введи описание (или /skip):")


@router.message(CreateTariffStates.waiting_description)
async def st_desc(message: Message, state: FSMContext) -> None:
    desc = None if message.text.strip() == "/skip" else message.text.strip()
    await state.update_data(description=desc)
    await state.set_state(CreateTariffStates.waiting_duration)
    await message.answer("На сколько дней? (число, или 0 для вечного доступа):")


@router.message(CreateTariffStates.waiting_duration)
async def st_duration(message: Message, state: FSMContext) -> None:
    try:
        days = int(message.text.strip())
    except ValueError:
        await message.answer("Нужно число. Попробуй ещё раз:")
        return
    await state.update_data(duration_days=None if days == 0 else days)
    await state.set_state(CreateTariffStates.waiting_price)
    await message.answer("Цена в Telegram Stars:")


@router.message(CreateTariffStates.waiting_price)
async def st_price(message: Message, state: FSMContext) -> None:
    try:
        price = int(message.text.strip())
        if price < 1:
            raise ValueError
    except ValueError:
        await message.answer("Цена должна быть положительным числом. Попробуй ещё раз:")
        return
    await state.update_data(price_stars=price)
    await state.set_state(CreateTariffStates.waiting_sort_order)
    await message.answer("Порядок отображения (число, меньше = выше):")


@router.message(CreateTariffStates.waiting_sort_order)
async def st_sort(message: Message, state: FSMContext) -> None:
    try:
        sort_order = int(message.text.strip())
    except ValueError:
        await message.answer("Нужно число. Попробуй ещё раз:")
        return
    await state.update_data(sort_order=sort_order)
    data = await state.get_data()
    await state.set_state(CreateTariffStates.confirm)
    preview = (
        "👀 <b>Превью тарифа</b>\n\n"
        f"Название: {data['name']}\n"
        f"Описание: {data.get('description') or '—'}\n"
        f"Срок: {duration_text(data.get('duration_days'))}\n"
        f"Цена: {data['price_stars']} ⭐\n"
        f"Порядок: {sort_order}"
    )
    await message.answer(preview, reply_markup=confirm_kb("a:tariff_save"))


@router.callback_query(CreateTariffStates.confirm, F.data == "a:tariff_save")
async def cb_save(call: CallbackQuery, db: AsyncSession, admin: Admin, state: FSMContext) -> None:
    data = await state.get_data()
    await state.clear()
    await tariffs_q.create_tariff(
        db,
        name=data["name"],
        description=data.get("description"),
        duration_days=data.get("duration_days"),
        price_stars=data["price_stars"],
        sort_order=data.get("sort_order", 0),
        created_by=admin.telegram_id,
    )
    tariffs = await tariffs_q.list_tariffs(db, only_active=False)
    await call.message.edit_text("✅ Тариф создан.", reply_markup=tariffs_list_kb(tariffs))
    await call.answer()


# ───────────────────────── редактирование тарифа ─────────────────────────
@router.callback_query(F.data.startswith("a:tariff_edit:"))
async def cb_edit(call: CallbackQuery, db: AsyncSession) -> None:
    tariff_id = int(call.data.split(":")[-1])
    tariff = await tariffs_q.get_tariff(db, tariff_id)
    if tariff is None:
        await call.answer("Тариф не найден", show_alert=True)
        return
    await call.message.edit_text(
        f"✏️ Что изменить в тарифе «{tariff.name}»?", reply_markup=tariff_edit_fields_kb(tariff_id)
    )
    await call.answer()


FIELD_PROMPTS = {
    "name": "Введи новое название:",
    "description": "Введи новое описание:",
    "duration_days": "Введи число дней (0 = вечный):",
    "price_stars": "Введи новую цену в Stars:",
    "sort_order": "Введи новый порядок (число):",
}


@router.callback_query(F.data.startswith("a:tfield:"))
async def cb_field(call: CallbackQuery, state: FSMContext) -> None:
    _, _, tariff_id, field = call.data.split(":")
    await state.set_state(EditTariffStates.waiting_value)
    await state.update_data(tariff_id=int(tariff_id), field=field)
    await call.message.answer(FIELD_PROMPTS[field])
    await call.answer()


@router.message(EditTariffStates.waiting_value)
async def st_value(message: Message, db: AsyncSession, state: FSMContext) -> None:
    data = await state.get_data()
    field = data["field"]
    tariff_id = data["tariff_id"]
    raw = message.text.strip()

    value: object
    if field in ("duration_days", "price_stars", "sort_order"):
        try:
            num = int(raw)
        except ValueError:
            await message.answer("Нужно число. Попробуй ещё раз:")
            return
        if field == "duration_days":
            value = None if num == 0 else num
        else:
            value = num
    else:
        value = raw

    await state.clear()
    # duration_days=None означает lifetime — обновим напрямую
    tariff = await tariffs_q.get_tariff(db, tariff_id)
    if tariff is None:
        await message.answer("Тариф не найден.")
        return
    setattr(tariff, field, value)
    await db.commit()
    await db.refresh(tariff)
    await message.answer(_tariff_card(tariff), reply_markup=tariff_actions_kb(tariff))
