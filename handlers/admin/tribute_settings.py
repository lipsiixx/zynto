"""Настройка продуктов оплаты через Tribute (СБП)."""
from __future__ import annotations

import logging

import aiohttp
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings as cfg
from database.models import Admin
from database.queries import settings as settings_q
from keyboards.admin_kb import tribute_days_kb, tribute_kb, tribute_products_kb
from states.admin_states import TributeSettingsStates

logger = logging.getLogger(__name__)

router = Router(name="admin-tribute")

TRIBUTE_PRODUCTS_URL = "https://tribute.tg/api/v1/products"

SETTINGS_KEY = "tribute_sbp_products"


async def _text(db: AsyncSession) -> str:
    products: list[dict] = await settings_q.get_json_setting(db, SETTINGS_KEY, [])
    if not products:
        products_block = "<i>список пуст</i>"
    else:
        lines = []
        for p in products:
            name = p.get("name", "Без названия")
            duration = p.get("duration_days")
            duration_label = "навсегда" if not duration else f"{duration} дн."
            price = p.get("price")
            currency = p.get("currency", "")
            price_label = f" — {price / 100:g} {currency}" if price is not None else ""
            lines.append(f"• {name}{price_label} → <b>{duration_label}</b>")
        products_block = "\n".join(lines)

    return (
        "🏦 <b>Tribute СБП — продукты</b>\n\n"
        f"{products_block}\n\n"
        "Это продукты Tribute (СБП), каждому из которых сопоставлен срок подписки. "
        "При оплате через Tribute срок будет взят из этого списка."
    )


@router.callback_query(F.data == "a:tribute_settings")
async def cb_tribute_settings(call: CallbackQuery, db: AsyncSession, admin: Admin, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_text(await _text(db), reply_markup=tribute_kb())
    await call.answer()


@router.callback_query(F.data == "a:tribute_load_products")
async def cb_tribute_load_products(call: CallbackQuery, state: FSMContext) -> None:
    if not cfg.tribute_api_key:
        await call.answer("TRIBUTE_API_KEY не настроен в .env", show_alert=True)
        return

    await call.answer("Загружаю список продуктов…")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                TRIBUTE_PRODUCTS_URL,
                headers={"Api-Key": cfg.tribute_api_key},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.warning("Tribute API вернул %s: %s", resp.status, body[:300])
                    await call.answer(f"Ошибка Tribute API: HTTP {resp.status}", show_alert=True)
                    return
                data = await resp.json()
    except Exception as e:
        logger.exception("Не удалось получить список продуктов Tribute")
        await call.answer(f"Не удалось связаться с Tribute API: {e}", show_alert=True)
        return

    rows = data.get("rows", [])
    products = [p for p in rows if p.get("status") == "approved"]

    if not products:
        await call.answer("Нет одобренных продуктов в Tribute", show_alert=True)
        return

    await state.update_data(tribute_products=products)
    await call.message.edit_text(
        "🏦 <b>Tribute СБП — выбери продукт</b>\n\n"
        "Дальше нужно будет указать срок подписки для выбранного продукта.",
        reply_markup=tribute_products_kb(products),
    )


@router.callback_query(F.data.startswith("a:tribute_pick:"))
async def cb_tribute_pick(call: CallbackQuery, state: FSMContext) -> None:
    try:
        index = int(call.data.split(":", 2)[2])
    except (ValueError, IndexError):
        await call.answer("Некорректный выбор", show_alert=True)
        return

    data = await state.get_data()
    products: list[dict] = data.get("tribute_products", [])

    if not (0 <= index < len(products)):
        await call.answer("Список продуктов устарел, загрузи заново", show_alert=True)
        return

    product = products[index]
    web_link = product.get("webLink")
    if not web_link:
        await call.answer("У продукта нет ссылки на оплату", show_alert=True)
        return

    pending_product = {
        "tribute_product_id": product.get("id"),
        "name": product.get("name", "Без названия"),
        "price": product.get("amount"),
        "currency": product.get("currency"),
        "web_link": web_link,
    }
    await state.update_data(tribute_products=None, tribute_pending_product=pending_product)

    name = pending_product["name"]
    await call.answer(f"Выбрано: {name}")
    await call.message.edit_text(
        f"🏦 <b>{name}</b>\n\nВыбери срок подписки для этого продукта:",
        reply_markup=tribute_days_kb(),
    )


async def _save_pending_product(db: AsyncSession, state: FSMContext, duration_days: int, updated_by: int) -> dict | None:
    data = await state.get_data()
    pending_product: dict | None = data.get("tribute_pending_product")
    if not pending_product:
        return None

    pending_product["duration_days"] = duration_days

    products: list[dict] = await settings_q.get_json_setting(db, SETTINGS_KEY, []) or []
    product_id = pending_product.get("tribute_product_id")

    updated = False
    for i, p in enumerate(products):
        if p.get("tribute_product_id") == product_id:
            products[i] = pending_product
            updated = True
            break
    if not updated:
        products.append(pending_product)

    await settings_q.set_json_setting(db, SETTINGS_KEY, products, updated_by=updated_by)
    await state.update_data(tribute_pending_product=None)
    return pending_product


@router.callback_query(F.data.startswith("a:tribute_set_days:"))
async def cb_tribute_set_days(call: CallbackQuery, db: AsyncSession, state: FSMContext) -> None:
    try:
        duration_days = int(call.data.split(":", 2)[2])
    except (ValueError, IndexError):
        await call.answer("Некорректный срок", show_alert=True)
        return

    saved = await _save_pending_product(db, state, duration_days, call.from_user.id)
    if saved is None:
        await call.answer("Продукт не выбран, начни заново", show_alert=True)
        await call.message.edit_text(await _text(db), reply_markup=tribute_kb())
        return

    await state.set_state(None)
    duration_label = "навсегда" if not duration_days else f"{duration_days} дн."
    await call.answer(f"✅ Сохранено: {saved['name']} → {duration_label}")
    await call.message.edit_text(await _text(db), reply_markup=tribute_kb())


@router.callback_query(F.data == "a:tribute_days_custom")
async def cb_tribute_days_custom(call: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    if not data.get("tribute_pending_product"):
        await call.answer("Продукт не выбран, начни заново", show_alert=True)
        return

    await state.set_state(TributeSettingsStates.waiting_days)
    await call.message.edit_text(
        "✏️ Введи срок подписки в днях (0 — навсегда):",
        reply_markup=tribute_days_kb(),
    )
    await call.answer()


@router.message(TributeSettingsStates.waiting_days)
async def on_tribute_days_input(message: Message, db: AsyncSession, state: FSMContext) -> None:
    raw = message.text.strip() if message.text else ""
    if not raw.isdigit():
        await message.answer("❌ Введи целое число дней (0 — навсегда)")
        return

    duration_days = int(raw)
    saved = await _save_pending_product(db, state, duration_days, message.from_user.id)
    if saved is None:
        await state.clear()
        await message.answer("Продукт не выбран, начни заново")
        await message.answer(await _text(db), reply_markup=tribute_kb())
        return

    await state.set_state(None)
    duration_label = "навсегда" if not duration_days else f"{duration_days} дн."
    await message.answer(f"✅ Сохранено: {saved['name']} → {duration_label}")
    await message.answer(await _text(db), reply_markup=tribute_kb())


@router.callback_query(F.data == "a:tribute_clear_products")
async def cb_tribute_clear_products_confirm(call: CallbackQuery) -> None:
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Да, очистить", callback_data="a:tribute_clear_products_confirm")
    kb.button(text="❌ Отмена", callback_data="a:tribute_settings")
    kb.adjust(1)
    await call.message.edit_text(
        "⚠️ Очистить весь список продуктов Tribute СБП?",
        reply_markup=kb.as_markup(),
    )
    await call.answer()


@router.callback_query(F.data == "a:tribute_clear_products_confirm")
async def cb_tribute_clear_products(call: CallbackQuery, db: AsyncSession, admin: Admin, state: FSMContext) -> None:
    await settings_q.set_json_setting(db, SETTINGS_KEY, [], updated_by=call.from_user.id)
    await state.clear()
    await call.message.edit_text(await _text(db), reply_markup=tribute_kb())
    await call.answer("Список очищен")
