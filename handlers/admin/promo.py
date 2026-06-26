"""Создание и просмотр промокодов (админ)."""
from __future__ import annotations

from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Admin
from database.queries import promo_codes as promo_q
from database.queries import tariffs as tariffs_q
from keyboards.admin_kb import (
    promo_discount_tariff_kb,
    promo_duration_kb,
    promo_max_uses_kb,
    promo_menu_kb,
    promo_type_kb,
)
from states.admin_states import CreatePromoStates
from utils.code_generator import generate_code
from utils.formatters import fmt_date, fmt_dt

router = Router(name="admin-promo")

DURATION_MAP = {
    "m1":   (1,      "1 минута"),
    "h1":   (60,     "1 час"),
    "d1":   (1440,   "1 день"),
    "d7":   (10080,  "7 дней"),
    "d30":  (43200,  "1 месяц"),
    "d90":  (129600, "3 месяца"),
    "life": (None,   "Навсегда"),
}


# ── меню промокодов ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "a:promo")
async def cb_promo(call: CallbackQuery) -> None:
    await call.message.edit_text("🎟 <b>Промокоды</b>", reply_markup=promo_menu_kb())
    await call.answer()


# ── шаг 1: выбор типа ───────────────────────────────────────────────────────

@router.callback_query(F.data == "a:promo_new")
async def cb_new(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(CreatePromoStates.waiting_type)
    await call.message.edit_text("Выбери тип промокода:", reply_markup=promo_type_kb())
    await call.answer()


# ── ветка ACCESS: длительность ──────────────────────────────────────────────

@router.callback_query(CreatePromoStates.waiting_type, F.data == "a:promotype:access")
async def cb_type_access(call: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(code_type="access")
    await state.set_state(CreatePromoStates.waiting_duration)
    await call.message.edit_text("На какой срок выдать доступ?", reply_markup=promo_duration_kb())
    await call.answer()


@router.callback_query(CreatePromoStates.waiting_duration, F.data.startswith("a:promodur:"))
async def cb_duration(call: CallbackQuery, state: FSMContext) -> None:
    code = call.data.split(":")[-1]
    if code == "custom":
        await state.set_state(CreatePromoStates.waiting_custom_days)
        await call.message.answer("Введи количество дней доступа:")
        await call.answer()
        return
    minutes, label = DURATION_MAP[code]
    await state.update_data(minutes=minutes, label=label)
    await state.set_state(CreatePromoStates.waiting_max_uses)
    await call.message.answer("Сколько раз можно активировать?", reply_markup=promo_max_uses_kb())
    await call.answer()


@router.message(CreatePromoStates.waiting_custom_days)
async def st_custom_days(message: Message, state: FSMContext) -> None:
    try:
        days = int(message.text.strip())
        if days < 1:
            raise ValueError
    except ValueError:
        await message.answer("Нужно положительное число. Попробуй ещё раз:")
        return
    await state.update_data(minutes=days * 1440, label=f"{days} дн.")
    await state.set_state(CreatePromoStates.waiting_max_uses)
    await message.answer("Сколько раз можно активировать?", reply_markup=promo_max_uses_kb())


# ── ветка DISCOUNT: тариф → сумма скидки ────────────────────────────────────

@router.callback_query(CreatePromoStates.waiting_type, F.data == "a:promotype:discount")
async def cb_type_discount(call: CallbackQuery, state: FSMContext, db: AsyncSession) -> None:
    await state.update_data(code_type="discount")
    tariffs = await tariffs_q.list_tariffs(db, only_active=True)
    await state.set_state(CreatePromoStates.waiting_discount_tariff)
    await call.message.edit_text(
        "На какой тариф даём скидку?",
        reply_markup=promo_discount_tariff_kb(tariffs),
    )
    await call.answer()


@router.callback_query(CreatePromoStates.waiting_discount_tariff, F.data.startswith("a:promodtariff:"))
async def cb_discount_tariff(call: CallbackQuery, state: FSMContext) -> None:
    raw = call.data.split(":")[-1]
    if raw == "any":
        await state.update_data(discount_tariff_id=None, discount_tariff_label="любой тариф")
    else:
        tariff_id = int(raw)
        await state.update_data(discount_tariff_id=tariff_id, discount_tariff_label=f"тариф #{tariff_id}")
    await state.set_state(CreatePromoStates.waiting_discount_amount)
    await call.message.answer("На сколько звёзд (XTR) скидка? Введи число:")
    await call.answer()


@router.message(CreatePromoStates.waiting_discount_amount)
async def st_discount_amount(message: Message, state: FSMContext) -> None:
    try:
        stars = int(message.text.strip())
        if stars < 1:
            raise ValueError
    except ValueError:
        await message.answer("Нужно положительное число звёзд. Попробуй ещё раз:")
        return
    await state.update_data(discount_stars=stars)
    await state.set_state(CreatePromoStates.waiting_max_uses)
    await message.answer("Сколько раз можно активировать?", reply_markup=promo_max_uses_kb())


# ── общий шаг: количество использований ─────────────────────────────────────

@router.callback_query(CreatePromoStates.waiting_max_uses, F.data.startswith("a:promouses:"))
async def cb_max_uses(call: CallbackQuery, state: FSMContext) -> None:
    raw = call.data.split(":")[-1]
    max_uses = None if raw == "0" else int(raw)
    await state.update_data(max_uses=max_uses)
    await state.set_state(CreatePromoStates.waiting_code_expiry)
    await call.message.answer("Когда истечёт сам код? (дата ДД.ММ.ГГГГ или /skip для бессрочного):")
    await call.answer()


# ── общий шаг: срок жизни кода ──────────────────────────────────────────────

@router.message(CreatePromoStates.waiting_code_expiry)
async def st_code_expiry(message: Message, state: FSMContext) -> None:
    raw = message.text.strip()
    code_expires = None
    if raw != "/skip":
        try:
            code_expires = datetime.strptime(raw, "%d.%m.%Y").replace(tzinfo=timezone.utc)
        except ValueError:
            await message.answer("Формат даты: ДД.ММ.ГГГГ (или /skip). Попробуй ещё раз:")
            return
    await state.update_data(code_expires=code_expires.isoformat() if code_expires else None)
    await state.set_state(CreatePromoStates.waiting_note)
    await message.answer("Заметка для себя (или /skip):")


# ── финальный шаг: заметка → создание ───────────────────────────────────────

@router.message(CreatePromoStates.waiting_note)
async def st_note(message: Message, db: AsyncSession, admin: Admin, state: FSMContext) -> None:
    note = None if message.text.strip() == "/skip" else message.text.strip()
    data = await state.get_data()
    await state.clear()

    code_str = generate_code(8)
    code_expires_raw = data.get("code_expires")
    code_expires = datetime.fromisoformat(code_expires_raw) if code_expires_raw else None
    code_type = data.get("code_type", "access")
    max_uses: int | None = data.get("max_uses", 1)

    await promo_q.create_promo(
        db,
        code=code_str,
        created_by=admin.telegram_id,
        code_type=code_type,
        duration_days=data.get("minutes") if code_type == "access" else None,
        duration_label=data.get("label") if code_type == "access" else None,
        max_uses=max_uses,
        code_expires_at=code_expires,
        note=note,
        discount_stars=data.get("discount_stars") if code_type == "discount" else None,
        discount_tariff_id=data.get("discount_tariff_id") if code_type == "discount" else None,
    )

    uses_label = "одноразовый" if max_uses == 1 else ("без лимита" if max_uses is None else f"{max_uses} раз")

    if code_type == "access":
        detail = f"Доступ: {data.get('label')}\nИспользований: {uses_label}"
    else:
        tariff_label = data.get("discount_tariff_label", "любой тариф")
        detail = f"Скидка: {data.get('discount_stars')}⭐ на {tariff_label}\nИспользований: {uses_label}"

    await message.answer(
        "✅ <b>Промокод создан!</b>\n\n"
        f"Код: <code>{code_str}</code>\n"
        f"{detail}\n"
        f"Истекает: {fmt_date(code_expires) if code_expires else 'бессрочно'}\n"
        f"Заметка: {note or '—'}\n\n"
        "Скопируй и отправь пользователю.",
        reply_markup=promo_menu_kb(),
    )


# ── список промокодов ────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("a:promo_list:"))
async def cb_list(call: CallbackQuery, db: AsyncSession) -> None:
    flt = call.data.split(":")[-1]
    promos = await promo_q.list_recent(db, limit=20, flt=flt)
    if not promos:
        await call.message.edit_text("Промокодов нет.", reply_markup=promo_menu_kb())
        await call.answer()
        return

    now = datetime.now(timezone.utc)
    lines = []
    for p in promos:
        # статус
        exhausted = (p.max_uses == 1 and p.used_by is not None) or (
            p.max_uses is not None and p.uses_count >= p.max_uses
        )
        expired_date = False
        if p.code_expires_at is not None:
            exp = p.code_expires_at if p.code_expires_at.tzinfo else p.code_expires_at.replace(tzinfo=timezone.utc)
            expired_date = exp < now

        if exhausted:
            status = "✅ исчерпан"
        elif expired_date:
            status = "⏰ истёк"
        else:
            uses_info = f"{p.uses_count}/{p.max_uses}" if p.max_uses is not None else f"{p.uses_count}/∞"
            status = f"🟢 активен ({uses_info})"

        # тип и детали
        if p.code_type == "discount":
            tariff_part = f"тариф #{p.discount_tariff_id}" if p.discount_tariff_id else "любой тариф"
            kind = f"скидка {p.discount_stars}⭐ на {tariff_part}"
        else:
            kind = p.duration_label or "—"

        lines.append(
            f"<code>{p.code}</code> • {kind} • {status} • {fmt_dt(p.created_at)}"
        )

    await call.message.edit_text(
        f"🎟 <b>Промокоды ({flt})</b>\n\n" + "\n".join(lines),
        reply_markup=promo_menu_kb(),
    )
    await call.answer()
