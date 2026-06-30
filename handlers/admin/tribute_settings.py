"""Настройка URL оплаты через Tribute (СБП)."""
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
from keyboards.admin_kb import tribute_kb, tribute_products_kb, tribute_set_url_kb
from states.admin_states import TributeSettingsStates

logger = logging.getLogger(__name__)

router = Router(name="admin-tribute")

TRIBUTE_PRODUCTS_URL = "https://tribute.tg/api/v1/products"


async def _text(db: AsyncSession) -> str:
    url = await settings_q.get_setting(db, "tribute_payment_url")
    status = f"<code>{url}</code>" if url else "<i>не настроен</i>"
    return (
        "🏦 <b>Tribute СБП — настройки</b>\n\n"
        f"Текущий URL оплаты: {status}\n\n"
        f"Это ссылка на страницу подписки в Tribute, которую пользователь откроет для оплаты через СБП."
    )


@router.callback_query(F.data == "a:tribute_settings")
async def cb_tribute_settings(call: CallbackQuery, db: AsyncSession, admin: Admin, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_text(await _text(db), reply_markup=tribute_kb())
    await call.answer()


@router.callback_query(F.data == "a:tribute_set_url")
async def cb_tribute_set_url(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(TributeSettingsStates.waiting_url)
    await call.message.edit_text(
        "🔗 Введи URL страницы оплаты Tribute:\n\n"
        "Пример: <code>https://tribute.tg/s/YOUR_CHANNEL</code>",
        reply_markup=tribute_set_url_kb(),
    )
    await call.answer()


@router.message(TributeSettingsStates.waiting_url)
async def on_tribute_url(message: Message, db: AsyncSession, state: FSMContext) -> None:
    url = message.text.strip() if message.text else ""
    if not url.startswith("http"):
        await message.answer("❌ Некорректный URL. Должен начинаться с http:// или https://")
        return
    await settings_q.set_setting(db, "tribute_payment_url", url, updated_by=message.from_user.id)
    await state.clear()
    await message.answer(f"✅ URL оплаты Tribute обновлён:\n<code>{url}</code>")
    await message.answer(await _text(db), reply_markup=tribute_kb())


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
        "Ссылка на оплату продукта будет сохранена как URL для пользователей.",
        reply_markup=tribute_products_kb(products),
    )


@router.callback_query(F.data.startswith("a:tribute_pick:"))
async def cb_tribute_pick(call: CallbackQuery, db: AsyncSession, state: FSMContext) -> None:
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

    await settings_q.set_setting(db, "tribute_payment_url", web_link, updated_by=call.from_user.id)
    await state.update_data(tribute_products=None)

    name = product.get("name", "Без названия")
    await call.answer(f"✅ Выбрано: {name}")
    await call.message.edit_text(await _text(db), reply_markup=tribute_kb())


@router.callback_query(F.data == "a:tribute_clear_url")
async def cb_tribute_clear_url(call: CallbackQuery, db: AsyncSession, admin: Admin, state: FSMContext) -> None:
    from sqlalchemy import delete

    from database.models import BotSetting

    await db.execute(delete(BotSetting).where(BotSetting.key == "tribute_payment_url"))
    await db.commit()
    await call.message.edit_text(await _text(db), reply_markup=tribute_kb())
    await call.answer("Сброшено")
