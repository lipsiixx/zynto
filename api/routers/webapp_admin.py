"""WebApp Admin API — админ-модуль мини-аппа, Фаза 2.

Переносит функционал Telegram-бот-админки (`handlers/admin/*`) в REST API под
`/v1/webapp/admin/*`. Telegram-админка (`/admin`) НЕ изменяется — это второй
интерфейс к тем же данным.

Правила:
  - Доступ: `require_webapp_admin` (обычные эндпоинты) / `require_webapp_superadmin`
    (админы, автоочистка) из `api/deps.py`. Обе кидают 404 на любой отказ — это
    инвариант скрытности, не 401/403.
  - Никакого SQL здесь — только `database/queries/*` и `services/*`.
  - Bot-инстанс — `request.app.state.bot` (см. `_get_bot`).
  - Все даты в ответах — ISO 8601 UTC, null если нет.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import aiohttp
from aiogram import Bot
from aiogram.types import BufferedInputFile
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db, require_webapp_admin, require_webapp_superadmin
from config import settings as cfg
from database.models import Admin, NudgeMessage, PromoCode, Tariff, User
from database.queries import admin_stats as admin_stats_q
from database.queries import admins as admins_q
from database.queries import business as business_q
from database.queries import messages as messages_q
from database.queries import nudge as nudge_q
from database.queries import promo_codes as promo_q
from database.queries import referral as referral_q
from database.queries import settings as settings_q
from database.queries import subscriptions as subs_q
from database.queries import tariffs as tariffs_q
from database.queries import users as users_q
from database.queries import webapp as webapp_q
from services import broadcast_job
from services import proxy_monitor as proxy_monitor_module
from services import server_monitor
from services import stats as stats_service
from services import subscription as sub_service
from utils.code_generator import generate_code

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webapp/admin", tags=["webapp-admin"])

TRIBUTE_PRODUCTS_URL = "https://tribute.tg/api/v1/products"
TRIBUTE_SETTINGS_KEY = "tribute_sbp_products"


def _get_bot(request: Request) -> Bot | None:
    return getattr(request.app.state, "bot", None)


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


# ── Дашборд / система ────────────────────────────────────────────────────

@router.get("/overview")
async def admin_overview(
    _: int = Depends(require_webapp_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    data = await stats_service.collect_stats(db)
    data["now"] = _iso(data.get("now"))
    return data


@router.get("/server")
async def admin_server(
    _: int = Depends(require_webapp_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    data = await server_monitor.collect_server_info(db)
    data["now"] = _iso(data.get("now"))
    return data


def _proxy_status() -> dict:
    monitor = proxy_monitor_module.monitor
    if monitor is None:
        return {"active": False, "text": "direct"}
    return {"active": True, "text": monitor.status_text()}


@router.get("/proxy")
async def admin_proxy(_: int = Depends(require_webapp_admin)) -> dict:
    return _proxy_status()


@router.post("/proxy/check")
async def admin_proxy_check(_: int = Depends(require_webapp_admin)) -> dict:
    monitor = proxy_monitor_module.monitor
    if monitor is None:
        return _proxy_status()
    text = await monitor.check_now()
    return {"active": True, "text": text}


def _day_range(days: int) -> list[str]:
    today = datetime.now(timezone.utc).date()
    return [(today - timedelta(days=d)).strftime("%Y-%m-%d") for d in range(days - 1, -1, -1)]


@router.get("/stats/daily")
async def admin_stats_daily(
    days: int = Query(30, ge=7, le=90),
    _: int = Depends(require_webapp_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Дневная динамика для графиков «Статистики»: нулевые дни дозаполнены."""
    new_users = await admin_stats_q.daily_new_users(db, days)
    msgs = await admin_stats_q.daily_messages(db, days)
    pays = await admin_stats_q.daily_payments(db, days)
    return {
        "items": [
            {
                "date": d,
                "new_users": new_users.get(d, 0),
                "messages": msgs["messages"].get(d, 0),
                "deleted": msgs["deleted"].get(d, 0),
                "edited": msgs["edited"].get(d, 0),
                "grants": pays["total"].get(d, 0),
                "paid": pays["paid"].get(d, 0),
            }
            for d in _day_range(days)
        ]
    }


@router.get("/users/{tid}/stats/daily")
async def admin_user_stats_daily(
    tid: int,
    days: int = Query(30, ge=7, le=90),
    _: int = Depends(require_webapp_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    user = await users_q.get_user(db, tid)
    if user is None:
        raise HTTPException(status_code=404, detail="user_not_found")
    msgs = await admin_stats_q.daily_messages(db, days, user_id=tid)
    return {
        "items": [
            {
                "date": d,
                "messages": msgs["messages"].get(d, 0),
                "deleted": msgs["deleted"].get(d, 0),
                "edited": msgs["edited"].get(d, 0),
            }
            for d in _day_range(days)
        ]
    }


# ── Промокоды ─────────────────────────────────────────────────────────────

def _promo_out(p: PromoCode) -> dict:
    now = datetime.now(timezone.utc)
    exhausted = (p.max_uses == 1 and p.used_by is not None) or (
        p.max_uses is not None and p.uses_count >= p.max_uses
    )
    expired_date = False
    if p.code_expires_at is not None:
        exp = p.code_expires_at if p.code_expires_at.tzinfo else p.code_expires_at.replace(tzinfo=timezone.utc)
        expired_date = exp < now

    if exhausted:
        status = "exhausted"
    elif expired_date:
        status = "expired"
    else:
        status = "active"

    return {
        "id": p.id,
        "code": p.code,
        "code_type": p.code_type,
        "duration_label": p.duration_label,
        "duration_minutes": p.duration_days,
        "discount_stars": p.discount_stars,
        "discount_tariff_id": p.discount_tariff_id,
        "max_uses": p.max_uses,
        "uses_count": p.uses_count,
        "used_by": p.used_by,
        "code_expires_at": _iso(p.code_expires_at),
        "note": p.note,
        "created_at": _iso(p.created_at),
        "status": status,
    }


class PromoCreateBody(BaseModel):
    code_type: str
    minutes: Optional[int] = None
    label: Optional[str] = None
    discount_stars: Optional[int] = None
    discount_tariff_id: Optional[int] = None
    max_uses: Optional[int] = 1
    code_expires_at: Optional[datetime] = None
    note: Optional[str] = None


@router.get("/promo")
async def admin_promo_list(
    filter: str = Query("all"),
    _: int = Depends(require_webapp_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    promos = await promo_q.list_recent(db, limit=50, flt=filter)
    return {"items": [_promo_out(p) for p in promos]}


@router.post("/promo")
async def admin_promo_create(
    body: PromoCreateBody,
    telegram_id: int = Depends(require_webapp_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if body.code_type not in ("access", "discount"):
        raise HTTPException(status_code=422, detail="invalid_code_type")
    if body.code_type == "access":
        if not body.label:
            raise HTTPException(status_code=422, detail="label_required")
    else:
        if not body.discount_stars or body.discount_stars < 1:
            raise HTTPException(status_code=422, detail="discount_stars_required")

    promo = await promo_q.create_promo(
        db,
        code=generate_code(8),
        created_by=telegram_id,
        code_type=body.code_type,
        duration_days=body.minutes if body.code_type == "access" else None,
        duration_label=body.label if body.code_type == "access" else None,
        max_uses=body.max_uses,
        code_expires_at=body.code_expires_at,
        note=body.note,
        discount_stars=body.discount_stars if body.code_type == "discount" else None,
        discount_tariff_id=body.discount_tariff_id if body.code_type == "discount" else None,
    )
    return _promo_out(promo)


@router.delete("/promo/{promo_id}")
async def admin_promo_delete(
    promo_id: int,
    telegram_id: int = Depends(require_webapp_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    promo = await promo_q.get_by_id(db, promo_id)
    if promo is None:
        raise HTTPException(status_code=404, detail="promo_not_found")
    await promo_q.delete_promo(db, promo_id)
    logger.info("WebApp admin: промокод удалён id=%s code=%s by=%s", promo_id, promo.code, telegram_id)
    return {"ok": True}


# ── Тарифы ────────────────────────────────────────────────────────────────

def _tariff_out(t: Tariff) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "description": t.description,
        "duration_days": t.duration_days,
        "price_stars": t.price_stars,
        "sort_order": t.sort_order,
        "is_active": t.is_active,
    }


class TariffCreateBody(BaseModel):
    name: str
    description: Optional[str] = None
    duration_days: Optional[int] = None
    price_stars: int
    sort_order: int = 0


class TariffUpdateBody(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    duration_days: Optional[int] = None
    price_stars: Optional[int] = None
    sort_order: Optional[int] = None


def _validate_tariff_fields(fields: dict) -> None:
    price = fields.get("price_stars")
    if price is not None and not (1 <= price <= tariffs_q.MAX_PRICE_STARS):
        raise HTTPException(status_code=422, detail="invalid_price")
    duration = fields.get("duration_days")
    if "duration_days" in fields and duration is not None and duration < 1:
        raise HTTPException(status_code=422, detail="invalid_duration")
    name = fields.get("name")
    if "name" in fields and (name is None or not name.strip()):
        raise HTTPException(status_code=422, detail="invalid_name")


@router.get("/tariffs")
async def admin_tariffs_list(
    _: int = Depends(require_webapp_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    tariffs = await tariffs_q.list_tariffs(db, only_active=False)
    return {"items": [_tariff_out(t) for t in tariffs]}


@router.post("/tariffs")
async def admin_tariffs_create(
    body: TariffCreateBody,
    telegram_id: int = Depends(require_webapp_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _validate_tariff_fields(body.model_dump())
    t = await tariffs_q.create_tariff(
        db,
        name=body.name,
        description=body.description,
        duration_days=body.duration_days,
        price_stars=body.price_stars,
        sort_order=body.sort_order,
        created_by=telegram_id,
    )
    return _tariff_out(t)


@router.patch("/tariffs/{tariff_id}")
async def admin_tariffs_update(
    tariff_id: int,
    body: TariffUpdateBody,
    _: int = Depends(require_webapp_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    fields = body.model_dump(exclude_unset=True)
    _validate_tariff_fields(fields)
    t = await tariffs_q.update_tariff_fields(db, tariff_id, fields)
    if t is None:
        raise HTTPException(status_code=404, detail="tariff_not_found")
    return _tariff_out(t)


@router.post("/tariffs/{tariff_id}/toggle")
async def admin_tariffs_toggle(
    tariff_id: int,
    _: int = Depends(require_webapp_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    t = await tariffs_q.toggle_tariff(db, tariff_id)
    if t is None:
        raise HTTPException(status_code=404, detail="tariff_not_found")
    return _tariff_out(t)


@router.delete("/tariffs/{tariff_id}")
async def admin_tariffs_delete(
    tariff_id: int,
    _: int = Depends(require_webapp_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    ok = await tariffs_q.delete_tariff(db, tariff_id)
    if not ok:
        raise HTTPException(status_code=404, detail="tariff_not_found")
    return {"ok": True}


# ── Пользователи (управление) ────────────────────────────────────────────

async def _user_profile_out(db: AsyncSession, user: User) -> dict:
    conn = await business_q.get_active_for_user(db, user.telegram_id)
    msg_count = await messages_q.count_for_user(db, user.telegram_id)
    return {
        "telegram_id": user.telegram_id,
        "username": user.username,
        "full_name": user.full_name,
        "created_at": _iso(user.created_at),
        "last_active_at": _iso(user.last_active_at),
        "subscription_status": user.subscription_status,
        "subscription_expires_at": _iso(user.subscription_expires_at),
        "is_banned": user.is_banned,
        "ban_reason": user.ban_reason,
        "business_connected": conn is not None,
        "messages_count": msg_count,
    }


class BanBody(BaseModel):
    reason: str


class GrantBody(BaseModel):
    tariff_id: int


@router.get("/users")
async def admin_users_list(
    q: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    _: int = Depends(require_webapp_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Лёгкий список для «Управления» — без business_connected/messages_count
    (это по 2 запроса на юзера; полный профиль тянется отдельно по клику)."""
    users, total = await users_q.list_users(
        db, q=q or None, status=status or None, page=page, limit=limit, include_admins=True
    )
    return {
        "items": [
            {
                "telegram_id": u.telegram_id,
                "username": u.username,
                "full_name": u.full_name,
                "subscription_status": u.subscription_status,
                "subscription_expires_at": _iso(u.subscription_expires_at),
                "is_banned": u.is_banned,
                "last_active_at": _iso(u.last_active_at),
                "created_at": _iso(u.created_at),
            }
            for u in users
        ],
        "total": total,
        "page": page,
        "pages": max(1, -(-total // limit)),
    }


@router.get("/users/find")
async def admin_users_find(
    q: str = Query(..., min_length=1),
    _: int = Depends(require_webapp_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    user = await users_q.find_by_identifier(db, q)
    if user is None:
        raise HTTPException(status_code=404, detail="user_not_found")
    return await _user_profile_out(db, user)


@router.post("/users/{tid}/ban")
async def admin_users_ban(
    tid: int,
    body: BanBody,
    _: int = Depends(require_webapp_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    user = await users_q.get_user(db, tid)
    if user is None:
        raise HTTPException(status_code=404, detail="user_not_found")
    await users_q.set_banned(db, tid, True, body.reason)
    user = await users_q.get_user(db, tid)
    return await _user_profile_out(db, user)


@router.post("/users/{tid}/unban")
async def admin_users_unban(
    tid: int,
    _: int = Depends(require_webapp_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    user = await users_q.get_user(db, tid)
    if user is None:
        raise HTTPException(status_code=404, detail="user_not_found")
    await users_q.set_banned(db, tid, False)
    user = await users_q.get_user(db, tid)
    return await _user_profile_out(db, user)


@router.post("/users/{tid}/grant")
async def admin_users_grant(
    tid: int,
    body: GrantBody,
    request: Request,
    _: int = Depends(require_webapp_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    user = await users_q.get_user(db, tid)
    if user is None:
        raise HTTPException(status_code=404, detail="user_not_found")
    tariff = await tariffs_q.get_tariff(db, body.tariff_id)
    if tariff is None:
        raise HTTPException(status_code=404, detail="tariff_not_found")

    await sub_service.activate_subscription(
        db, user, duration_days=tariff.duration_days, payment_method="manual", tariff_id=tariff.id
    )
    logger.info("WebApp admin: ручная выдача подписки target=%s tariff=%s", tid, tariff.id)

    bot = _get_bot(request)
    if bot:
        try:
            await bot.send_message(tid, f"🎁 Тебе выдана подписка: <b>{tariff.name}</b>!")
        except Exception:  # noqa: BLE001
            pass

    user = await users_q.get_user(db, tid)
    return await _user_profile_out(db, user)


@router.get("/users/{tid}/subscriptions")
async def admin_users_subscriptions(
    tid: int,
    _: int = Depends(require_webapp_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    subs = await subs_q.list_user_subscriptions(db, tid)
    return {
        "items": [
            {
                "payment_method": s.payment_method,
                "expires_at": _iso(s.expires_at),
                "created_at": _iso(s.created_at),
            }
            for s in subs
        ]
    }


@router.get("/users/{tid}/stats")
async def admin_users_stats(
    tid: int,
    _: int = Depends(require_webapp_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    user = await users_q.get_user(db, tid)
    if user is None:
        raise HTTPException(status_code=404, detail="user_not_found")

    summary = await webapp_q.get_user_summary(db, tid)
    referral = await referral_q.get_stats_for_referrer(db, tid)
    subs = await subs_q.list_user_subscriptions(db, tid, limit=1000)
    by_method: dict[str, int] = {}
    for s in subs:
        by_method[s.payment_method] = by_method.get(s.payment_method, 0) + 1

    return {
        "summary": summary,
        "referral": referral,
        "payments": {"total": len(subs), "by_method": by_method},
    }


class SubscriptionSetBody(BaseModel):
    action: str  # days | lifetime | revoke
    days: Optional[int] = None


@router.post("/users/{tid}/subscription")
async def admin_users_subscription_set(
    tid: int,
    body: SubscriptionSetBody,
    request: Request,
    telegram_id: int = Depends(require_webapp_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Ручная настройка подписки: выдать N дней (продлевает от текущего
    expires_at через grant_access), сделать lifetime или забрать доступ."""
    user = await users_q.get_user(db, tid)
    if user is None:
        raise HTTPException(status_code=404, detail="user_not_found")

    notify_text: str | None = None
    if body.action == "days":
        if not body.days or body.days < 1 or body.days > 3650:
            raise HTTPException(status_code=422, detail="invalid_days")
        expires_at = await sub_service.activate_subscription(
            db, user, duration_days=body.days, payment_method="manual"
        )
        notify_text = f"🎁 Тебе выдан доступ на <b>{body.days} дн.</b>"
        if expires_at:
            notify_text += f" (до {expires_at.strftime('%d.%m.%Y')})"
    elif body.action == "lifetime":
        await sub_service.activate_subscription(
            db, user, duration_days=None, payment_method="manual"
        )
        notify_text = "🎁 Тебе выдан <b>бессрочный</b> доступ!"
    elif body.action == "revoke":
        await users_q.update_subscription_fields(db, tid, "none", None)
    else:
        raise HTTPException(status_code=422, detail="invalid_action")

    logger.info(
        "WebApp admin: ручная настройка подписки target=%s action=%s days=%s by=%s",
        tid, body.action, body.days, telegram_id,
    )

    if notify_text:
        bot = _get_bot(request)
        if bot:
            try:
                await bot.send_message(tid, notify_text)
            except Exception:  # noqa: BLE001
                pass

    user = await users_q.get_user(db, tid)
    return await _user_profile_out(db, user)


# ── Рассылка ──────────────────────────────────────────────────────────────

@router.get("/broadcast/status")
async def admin_broadcast_status(_: int = Depends(require_webapp_admin)) -> dict:
    return broadcast_job.get_status()


@router.get("/broadcast/recipients-count")
async def admin_broadcast_recipients_count(
    _: int = Depends(require_webapp_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    recipients = await users_q.get_broadcast_recipients(db)
    return {"count": len(recipients)}


@router.post("/broadcast")
async def admin_broadcast_start(
    request: Request,
    text: str = Form(""),
    photo: UploadFile | None = File(None),
    telegram_id: int = Depends(require_webapp_admin),
) -> dict:
    bot = _get_bot(request)
    if bot is None:
        raise HTTPException(status_code=503, detail="bot_unavailable")
    if broadcast_job.is_running():
        raise HTTPException(status_code=409, detail="already_running")

    photo_bytes: bytes | None = None
    photo_filename = "broadcast.jpg"
    if photo is not None:
        if not (photo.content_type or "").startswith("image/"):
            raise HTTPException(status_code=422, detail="invalid_photo_type")
        photo_bytes = await photo.read()
        photo_filename = photo.filename or photo_filename

    clean_text = text.strip() if text else ""
    if not clean_text and photo_bytes is None:
        raise HTTPException(status_code=422, detail="text_or_photo_required")

    try:
        total = await broadcast_job.start_broadcast(
            bot, telegram_id, clean_text or None, photo_bytes, photo_filename
        )
    except RuntimeError:
        raise HTTPException(status_code=409, detail="already_running")

    return {"started": True, "total": total}


# ── Админы (только суперадмин) ───────────────────────────────────────────

def _admin_out(a: Admin) -> dict:
    return {
        "telegram_id": a.telegram_id,
        "username": a.username,
        "full_name": a.full_name,
        "added_at": _iso(a.created_at),
    }


class AdminAddBody(BaseModel):
    identifier: str


@router.get("/admins")
async def admin_admins_list(
    _: int = Depends(require_webapp_superadmin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    admins = await admins_q.list_admins(db, include_superadmin=False)
    return {"items": [_admin_out(a) for a in admins]}


@router.post("/admins")
async def admin_admins_add(
    body: AdminAddBody,
    request: Request,
    telegram_id: int = Depends(require_webapp_superadmin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    user = await users_q.find_by_identifier(db, body.identifier)
    if user is None:
        raise HTTPException(status_code=404, detail="user_not_found")

    admin = await admins_q.add_admin(db, user.telegram_id, user.username, user.full_name, telegram_id)
    logger.info("WebApp admin: добавлен админ %s суперадмином %s", user.telegram_id, telegram_id)

    bot = _get_bot(request)
    if bot:
        try:
            await bot.send_message(user.telegram_id, "👮 Тебе выдан доступ к панели администратора. /admin")
        except Exception:  # noqa: BLE001
            pass

    return _admin_out(admin)


@router.delete("/admins/{tid}")
async def admin_admins_delete(
    tid: int,
    _: int = Depends(require_webapp_superadmin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await admins_q.remove_admin(db, tid)
    return {"ok": True}


# ── Nudge ─────────────────────────────────────────────────────────────────

def _nudge_msg_out(m: NudgeMessage) -> dict:
    return {
        "id": m.id,
        "text": m.text,
        "media_type": m.media_type,
        "has_media": bool(m.media_file_id),
        "is_active": m.is_active,
    }


async def _nudge_out(db: AsyncSession) -> dict:
    enabled = (await settings_q.get_setting(db, "nudge_enabled", "0")) == "1"
    interval = await settings_q.get_int_setting(db, "nudge_interval_days", 1)
    grace = await settings_q.get_int_setting(db, "nudge_grace_days", 3)
    messages = await nudge_q.list_nudge_messages(db)
    return {
        "enabled": enabled,
        "interval_days": interval,
        "grace_days": grace,
        "messages": [_nudge_msg_out(m) for m in messages],
    }


class NudgeSettingsBody(BaseModel):
    enabled: Optional[bool] = None
    interval_days: Optional[int] = None
    grace_days: Optional[int] = None


async def _extract_media_upload(
    bot: Bot, admin_id: int, media: UploadFile | None
) -> tuple[str | None, str | None]:
    """Загружает медиафайл боту (отправкой админу) и возвращает (file_id, media_type)."""
    if media is None:
        return None, None
    ctype = media.content_type or ""
    data = await media.read()
    if ctype.startswith("image/"):
        msg = await bot.send_photo(admin_id, BufferedInputFile(data, filename=media.filename or "media.jpg"))
        return msg.photo[-1].file_id, "photo"
    if ctype.startswith("video/"):
        msg = await bot.send_video(admin_id, BufferedInputFile(data, filename=media.filename or "media.mp4"))
        return msg.video.file_id, "video"
    raise HTTPException(status_code=422, detail="unsupported_media_type")


@router.get("/nudge")
async def admin_nudge_get(
    _: int = Depends(require_webapp_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await _nudge_out(db)


@router.put("/nudge/settings")
async def admin_nudge_settings(
    body: NudgeSettingsBody,
    telegram_id: int = Depends(require_webapp_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    data = body.model_dump(exclude_unset=True)
    if "enabled" in data:
        await settings_q.set_setting(db, "nudge_enabled", "1" if data["enabled"] else "0", telegram_id)
    if "interval_days" in data:
        await settings_q.set_setting(db, "nudge_interval_days", str(data["interval_days"]), telegram_id)
    if "grace_days" in data:
        await settings_q.set_setting(db, "nudge_grace_days", str(data["grace_days"]), telegram_id)
    return await _nudge_out(db)


@router.post("/nudge/messages")
async def admin_nudge_msg_create(
    request: Request,
    text: str | None = Form(None),
    media: UploadFile | None = File(None),
    telegram_id: int = Depends(require_webapp_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    clean_text = text.strip() if text else None
    if not clean_text and media is None:
        raise HTTPException(status_code=422, detail="text_or_media_required")

    media_file_id, media_type = None, None
    if media is not None:
        bot = _get_bot(request)
        if bot is None:
            raise HTTPException(status_code=503, detail="bot_unavailable")
        media_file_id, media_type = await _extract_media_upload(bot, telegram_id, media)

    msg = await nudge_q.create_nudge_message(db, text=clean_text, media_file_id=media_file_id, media_type=media_type)
    return _nudge_msg_out(msg)


@router.patch("/nudge/messages/{msg_id}")
async def admin_nudge_msg_update(
    msg_id: int,
    request: Request,
    text: str | None = Form(None),
    media: UploadFile | None = File(None),
    telegram_id: int = Depends(require_webapp_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    clean_text = text.strip() if text else None
    if not clean_text and media is None:
        raise HTTPException(status_code=422, detail="text_or_media_required")

    media_file_id, media_type = None, None
    if media is not None:
        bot = _get_bot(request)
        if bot is None:
            raise HTTPException(status_code=503, detail="bot_unavailable")
        media_file_id, media_type = await _extract_media_upload(bot, telegram_id, media)

    msg = await nudge_q.update_nudge_message(
        db, msg_id, text=clean_text, media_file_id=media_file_id, media_type=media_type
    )
    if msg is None:
        raise HTTPException(status_code=404, detail="not_found")
    return _nudge_msg_out(msg)


@router.post("/nudge/messages/{msg_id}/toggle")
async def admin_nudge_msg_toggle(
    msg_id: int,
    _: int = Depends(require_webapp_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    msg = await nudge_q.toggle_nudge_message(db, msg_id)
    if msg is None:
        raise HTTPException(status_code=404, detail="not_found")
    return _nudge_msg_out(msg)


@router.post("/nudge/messages/{msg_id}/clear-media")
async def admin_nudge_msg_clear_media(
    msg_id: int,
    _: int = Depends(require_webapp_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    msg = await nudge_q.clear_nudge_media(db, msg_id)
    if msg is None:
        raise HTTPException(status_code=404, detail="not_found")
    return _nudge_msg_out(msg)


@router.delete("/nudge/messages/{msg_id}")
async def admin_nudge_msg_delete(
    msg_id: int,
    _: int = Depends(require_webapp_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    deleted = await nudge_q.delete_nudge_message(db, msg_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="not_found")
    return {"ok": True}


@router.post("/nudge/messages/{msg_id}/preview")
async def admin_nudge_msg_preview(
    msg_id: int,
    request: Request,
    telegram_id: int = Depends(require_webapp_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    msg = await nudge_q.get_nudge_message(db, msg_id)
    if msg is None:
        raise HTTPException(status_code=404, detail="not_found")
    bot = _get_bot(request)
    if bot is None:
        raise HTTPException(status_code=503, detail="bot_unavailable")
    try:
        if msg.media_type == "photo" and msg.media_file_id:
            await bot.send_photo(telegram_id, msg.media_file_id, caption=msg.text or None)
        elif msg.media_type == "video" and msg.media_file_id:
            await bot.send_video(telegram_id, msg.media_file_id, caption=msg.text or None)
        elif msg.text:
            await bot.send_message(telegram_id, msg.text)
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=500, detail="preview_send_failed")
    return {"ok": True}


# ── «О боте» ──────────────────────────────────────────────────────────────

async def _about_out(db: AsyncSession) -> dict:
    return {
        "privacy": {
            "enabled": (await settings_q.get_setting(db, "about_privacy_enabled", "1")) == "1",
            "type": await settings_q.get_setting(db, "about_privacy_type", "text"),
            "content": (await settings_q.get_setting(db, "about_privacy_content", "")) or "",
        },
        "terms": {
            "enabled": (await settings_q.get_setting(db, "about_terms_enabled", "1")) == "1",
            "type": await settings_q.get_setting(db, "about_terms_type", "text"),
            "content": (await settings_q.get_setting(db, "about_terms_content", "")) or "",
        },
        "support": {
            "enabled": (await settings_q.get_setting(db, "about_support_enabled", "1")) == "1",
            "url": (await settings_q.get_setting(db, "about_support_url", "")) or "",
        },
    }


class AboutSectionBody(BaseModel):
    enabled: Optional[bool] = None
    type: Optional[str] = None
    content: Optional[str] = None


class AboutSupportBody(BaseModel):
    enabled: Optional[bool] = None
    url: Optional[str] = None


class AboutUpdateBody(BaseModel):
    privacy: Optional[AboutSectionBody] = None
    terms: Optional[AboutSectionBody] = None
    support: Optional[AboutSupportBody] = None


@router.get("/about")
async def admin_about_get(
    _: int = Depends(require_webapp_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await _about_out(db)


@router.put("/about")
async def admin_about_update(
    body: AboutUpdateBody,
    telegram_id: int = Depends(require_webapp_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    data = body.model_dump(exclude_unset=True)

    if "privacy" in data:
        p = data["privacy"]
        if "enabled" in p:
            await settings_q.set_setting(db, "about_privacy_enabled", "1" if p["enabled"] else "0", telegram_id)
        if "type" in p:
            await settings_q.set_setting(db, "about_privacy_type", p["type"], telegram_id)
        if "content" in p:
            await settings_q.set_setting(db, "about_privacy_content", p["content"], telegram_id)

    if "terms" in data:
        t = data["terms"]
        if "enabled" in t:
            await settings_q.set_setting(db, "about_terms_enabled", "1" if t["enabled"] else "0", telegram_id)
        if "type" in t:
            await settings_q.set_setting(db, "about_terms_type", t["type"], telegram_id)
        if "content" in t:
            await settings_q.set_setting(db, "about_terms_content", t["content"], telegram_id)

    if "support" in data:
        s = data["support"]
        if "enabled" in s:
            await settings_q.set_setting(db, "about_support_enabled", "1" if s["enabled"] else "0", telegram_id)
        if "url" in s:
            await settings_q.set_setting(db, "about_support_url", s["url"], telegram_id)

    return await _about_out(db)


# ── Tribute СБП ───────────────────────────────────────────────────────────

class TributeProduct(BaseModel):
    tribute_product_id: Any = None
    name: str
    price: Optional[int] = None
    currency: Optional[str] = None
    web_link: Optional[str] = None
    duration_days: Optional[int] = None


class TributeProductsBody(BaseModel):
    products: list[TributeProduct]


@router.get("/tribute")
async def admin_tribute_get(
    _: int = Depends(require_webapp_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    products = await settings_q.get_json_setting(db, TRIBUTE_SETTINGS_KEY, [])
    return {"products": products or []}


@router.post("/tribute/fetch")
async def admin_tribute_fetch(_: int = Depends(require_webapp_admin)) -> dict:
    if not cfg.tribute_api_key:
        raise HTTPException(status_code=503, detail="tribute_key_missing")

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
                    raise HTTPException(status_code=502, detail="tribute_api_error")
                data = await resp.json()
    except HTTPException:
        raise
    except Exception:
        logger.exception("Не удалось получить список продуктов Tribute")
        raise HTTPException(status_code=502, detail="tribute_api_unreachable")

    rows = data.get("rows", [])
    products = [
        {
            "id": p.get("id"),
            "name": p.get("name"),
            "amount": p.get("amount"),
            "currency": p.get("currency"),
            "webLink": p.get("webLink"),
        }
        for p in rows
        if p.get("status") == "approved"
    ]
    return {"products": products}


@router.put("/tribute/products")
async def admin_tribute_products_update(
    body: TributeProductsBody,
    telegram_id: int = Depends(require_webapp_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    products = [p.model_dump() for p in body.products]
    await settings_q.set_json_setting(db, TRIBUTE_SETTINGS_KEY, products, updated_by=telegram_id)
    return {"products": products}


# ── Курс ──────────────────────────────────────────────────────────────────

async def _course_out(db: AsyncSession) -> dict:
    enabled = (await settings_q.get_setting(db, "course_enabled", "0")) == "1"
    file_id = await settings_q.get_setting(db, "course_video_file_id")
    caption = (await settings_q.get_setting(db, "course_caption", "")) or ""
    return {"enabled": enabled, "has_video": bool(file_id), "caption": caption}


class CourseSettingsBody(BaseModel):
    enabled: Optional[bool] = None
    caption: Optional[str] = None


@router.get("/course")
async def admin_course_get(
    _: int = Depends(require_webapp_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await _course_out(db)


@router.put("/course")
async def admin_course_update(
    body: CourseSettingsBody,
    telegram_id: int = Depends(require_webapp_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    data = body.model_dump(exclude_unset=True)
    if "enabled" in data:
        await settings_q.set_setting(db, "course_enabled", "1" if data["enabled"] else "0", telegram_id)
    if "caption" in data:
        await settings_q.set_setting(db, "course_caption", data["caption"], telegram_id)
    return await _course_out(db)


@router.post("/course/video")
async def admin_course_video(
    request: Request,
    video: UploadFile = File(...),
    telegram_id: int = Depends(require_webapp_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not (video.content_type or "").startswith("video/"):
        raise HTTPException(status_code=422, detail="invalid_video_type")
    bot = _get_bot(request)
    if bot is None:
        raise HTTPException(status_code=503, detail="bot_unavailable")

    data = await video.read()
    msg = await bot.send_video(telegram_id, BufferedInputFile(data, filename=video.filename or "course.mp4"))
    file_id = msg.video.file_id
    await settings_q.set_setting(db, "course_video_file_id", file_id, telegram_id)
    return {"ok": True}


# ── Автоочистка (только суперадмин) ──────────────────────────────────────

async def _cleanup_out(db: AsyncSession) -> dict:
    text_days = await settings_q.get_int_setting(db, "text_retention_days", cfg.text_retention_days)
    media_days = await settings_q.get_int_setting(db, "media_retention_days", cfg.media_retention_days)
    return {"text_retention_days": text_days, "media_retention_days": media_days}


class CleanupBody(BaseModel):
    text_retention_days: Optional[int] = None
    media_retention_days: Optional[int] = None


@router.get("/cleanup")
async def admin_cleanup_get(
    _: int = Depends(require_webapp_superadmin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await _cleanup_out(db)


@router.put("/cleanup")
async def admin_cleanup_update(
    body: CleanupBody,
    telegram_id: int = Depends(require_webapp_superadmin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    data = body.model_dump(exclude_unset=True)
    for key in ("text_retention_days", "media_retention_days"):
        if key in data:
            value = data[key]
            if value is None or value < 0:
                raise HTTPException(status_code=422, detail="invalid_retention_days")
            await settings_q.set_setting(db, key, str(value), telegram_id)
    return await _cleanup_out(db)


# ── Реферальная программа ────────────────────────────────────────────────

class ReferralSettingsBody(BaseModel):
    enabled: Optional[bool] = None
    reward_days: Optional[int] = None


@router.get("/referral")
async def admin_referral_get(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    _: int = Depends(require_webapp_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    enabled = (await settings_q.get_setting(db, "referral_enabled", "1")) != "0"
    reward_days = await settings_q.get_int_setting(db, "referral_reward_days", 3)
    rewards, total = await referral_q.list_all_rewards(db, page=page, limit=limit)
    return {"enabled": enabled, "reward_days": reward_days, "rewards": rewards, "total_rewards": total}


@router.put("/referral")
async def admin_referral_update(
    body: ReferralSettingsBody,
    telegram_id: int = Depends(require_webapp_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    data = body.model_dump(exclude_unset=True)
    if "enabled" in data:
        await settings_q.set_setting(db, "referral_enabled", "1" if data["enabled"] else "0", telegram_id)
    if "reward_days" in data:
        await settings_q.set_setting(db, "referral_reward_days", str(data["reward_days"]), telegram_id)

    enabled = (await settings_q.get_setting(db, "referral_enabled", "1")) != "0"
    reward_days = await settings_q.get_int_setting(db, "referral_reward_days", 3)
    _, total = await referral_q.list_all_rewards(db, page=1, limit=1)
    return {"enabled": enabled, "reward_days": reward_days, "total_rewards": total}
