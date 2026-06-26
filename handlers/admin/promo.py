"""Создание и просмотр промокодов (админ)."""
from __future__ import annotations

from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Admin
from database.queries import promo_codes as promo_q
from keyboards.admin_kb import promo_duration_kb, promo_menu_kb
from states.admin_states import CreatePromoStates
from utils.code_generator import generate_code
from utils.formatters import fmt_date, fmt_dt

router = Router(name="admin-promo")

# code -> (минуты доступа | None, человекочитаемая метка)
DURATION_MAP = {
    "m1": (1, "1 минута"),
    "h1": (60, "1 час"),
    "d1": (1440, "1 день"),
    "d7": (10080, "7 дней"),
    "d30": (43200, "1 месяц"),
    "d90": (129600, "3 месяца"),
    "life": (None, "Навсегда"),
}


@router.callback_query(F.data == "a:promo")
async def cb_promo(call: CallbackQuery) -> None:
    await call.message.edit_text("🎟 <b>Промокоды</b>", reply_markup=promo_menu_kb())
    await call.answer()


@router.callback_query(F.data == "a:promo_new")
async def cb_new(call: CallbackQuery, state: FSMContext) -> None:
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
    await state.set_state(CreatePromoStates.waiting_code_expiry)
    await call.message.answer("Когда истечёт сам код? (дата ДД.ММ.ГГГГ или /skip для бессрочного):")
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
    await state.set_state(CreatePromoStates.waiting_code_expiry)
    await message.answer("Когда истечёт сам код? (дата ДД.ММ.ГГГГ или /skip для бессрочного):")


@router.message(CreatePromoStates.waiting_code_expiry)
async def st_code_expiry(message: Message, state: FSMContext) -> None:
    raw = message.text.strip()
    code_expires = None
    if raw != "/skip":
        try:
            code_expires = datetime.strptime(
                raw, "%d.%m.%Y").replace(tzinfo=timezone.utc)
        except ValueError:
            await message.answer("Формат даты: ДД.ММ.ГГГГ (или /skip). Попробуй ещё раз:")
            return
    await state.update_data(code_expires=code_expires.isoformat() if code_expires else None)
    await state.set_state(CreatePromoStates.waiting_note)
    await message.answer("Заметка для себя (или /skip):")


@router.message(CreatePromoStates.waiting_note)
async def st_note(message: Message, db: AsyncSession, admin: Admin, state: FSMContext) -> None:
    note = None if message.text.strip() == "/skip" else message.text.strip()
    data = await state.get_data()
    await state.clear()

    code = generate_code(8)
    code_expires_raw = data.get("code_expires")
    code_expires = datetime.fromisoformat(
        code_expires_raw) if code_expires_raw else None

    await promo_q.create_promo(
        db,
        code=code,
        created_by=admin.telegram_id,
        duration_days=data.get("minutes"),  # минуты (см. соглашение)
        duration_label=data.get("label"),
        code_expires_at=code_expires,
        note=note,
    )

    await message.answer(
        "✅ <b>Промокод создан!</b>\n\n"
        f"Код: <code>{code}</code>\n"
        f"Доступ: {data.get('label')}\n"
        f"Истекает: {fmt_date(code_expires) if code_expires else 'бессрочно'}\n"
        f"Заметка: {note or '—'}\n\n"
        "Скопируй и отправь пользователю.",
        reply_markup=promo_menu_kb(),
    )


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
        expired = False
        if p.code_expires_at is not None:
            exp = p.code_expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            expired = exp < now
        if p.used_by:
            status = f"✅ использован ({p.used_by})"
        elif expired:
            status = "⏰ истёк"
        else:
            status = "🟢 не использован"
        lines.append(
            f"<code>{p.code}</code> • {p.duration_label or '—'} • {status} • {fmt_dt(p.created_at)}"
        )
    await call.message.edit_text(
        f"🎟 <b>Промокоды ({flt})</b>\n\n" + "\n".join(lines),
        reply_markup=promo_menu_kb(),
    )
    await call.answer()
