"""GET /stats/server, /stats/proxy, /stats/users, /stats/users/:id, /stats/users/:uid/chats/:cid"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import psutil
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import Body
from api.deps import get_db, require_auth
from api.schemas import (
    CpuOut,
    DiskOut,
    GlobalUserStatsOut,
    MemoryOut,
    ProxyInfo,
    ProxyStatsOut,
    ServerStatsOut,
    UserChatStatsOut,
    UserStatsOut,
)
from database.queries import api as api_q
from database.queries import referral as referral_q
from database.queries import settings as settings_q
from database.queries import users as users_q
from services import proxy_monitor as pm_module

router = APIRouter(prefix="/stats", tags=["stats"], dependencies=[Depends(require_auth)])

_BOOT_TIME = psutil.boot_time()


@router.get("/server", response_model=ServerStatsOut)
async def server_stats() -> ServerStatsOut:
    cpu_pct = psutil.cpu_percent(interval=0.2)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    try:
        load = list(psutil.getloadavg())
    except AttributeError:
        load = [0.0, 0.0, 0.0]

    return ServerStatsOut(
        cpu=CpuOut(usagePercent=cpu_pct, cores=psutil.cpu_count(logical=True) or 1),
        memory=MemoryOut(totalBytes=mem.total, usedBytes=mem.used, freeBytes=mem.available),
        disk=DiskOut(totalBytes=disk.total, usedBytes=disk.used, freeBytes=disk.free),
        uptimeSeconds=time.time() - _BOOT_TIME,
        loadAvg=load,
        measuredAt=datetime.now(timezone.utc),
    )


@router.get("/proxy", response_model=ProxyStatsOut)
async def proxy_stats() -> ProxyStatsOut:
    monitor = pm_module.monitor
    if monitor is None:
        return ProxyStatsOut(active=None, noProxy=True)

    state = monitor._evaluate()
    avg = sum(monitor._latencies) / len(monitor._latencies) if monitor._latencies else 0.0
    fails = monitor._results.count(False)
    age: Optional[float] = None
    if monitor._results:
        age = time.monotonic() - monitor._last_probe

    return ProxyStatsOut(
        active=ProxyInfo(
            proxy=monitor.masked,
            state=state.value,
            avgLatencySeconds=round(avg, 3),
            failsInWindow=fails,
            windowSize=len(monitor._results),
            consecutiveFails=monitor._consecutive_fails,
            consecutiveOks=monitor._consecutive_oks,
            lastCheckedSecondsAgo=round(age, 1) if age is not None else None,
            monitorRunning=monitor._task is not None and not monitor._task.done(),
        ),
        noProxy=False,
    )


@router.get("/users", response_model=GlobalUserStatsOut)
async def global_user_stats(db: AsyncSession = Depends(get_db)) -> GlobalUserStatsOut:
    now = datetime.now(timezone.utc)
    total = await users_q.count_users(db)
    active = await users_q.count_active_subscribers(db)
    new_today = await users_q.count_new_users_since(db, now - timedelta(days=1))
    new_week = await users_q.count_new_users_since(db, now - timedelta(days=7))

    # online = активны за последние 5 минут
    from sqlalchemy import func, select
    from database.models import User
    online_res = await db.execute(
        select(func.count(User.id)).where(
            User.last_active_at >= now - timedelta(minutes=5)
        )
    )
    online = int(online_res.scalar() or 0)

    return GlobalUserStatsOut(
        total=total,
        online=online,
        newToday=new_today,
        newThisWeek=new_week,
        activeSubscribers=active,
        measuredAt=now,
    )


@router.get("/users/{user_id}", response_model=UserStatsOut)
async def user_stats(user_id: int, db: AsyncSession = Depends(get_db)) -> UserStatsOut:
    from datetime import timezone
    user = await users_q.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(404, detail="not_found")
    stats = await api_q.get_user_stats(db, user.telegram_id)
    last = user.last_active_at
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    is_online = (datetime.now(timezone.utc) - last).total_seconds() < 300
    return UserStatsOut(
        userId=user.id,
        telegramId=user.telegram_id,
        isOnline=is_online,
        **stats,
    )


@router.get("/users/{user_id}/chats/{chat_id}", response_model=UserChatStatsOut)
async def user_chat_stats(
    user_id: int,
    chat_id: int,
    db: AsyncSession = Depends(get_db),
) -> UserChatStatsOut:
    user = await users_q.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(404, detail="not_found")
    stats = await api_q.get_user_chat_stats(db, user.telegram_id, chat_id)
    return UserChatStatsOut(**stats)


# ── Referral admin endpoints ───────────────────────────────────────────────

@router.get("/referrals")
async def admin_referrals(
    page: int = 1,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Список всех реферальных наград."""
    rewards, total = await referral_q.list_all_rewards(db, page=page, limit=limit)
    return {"data": rewards, "total": total, "page": page}


@router.get("/referrals/settings")
async def admin_referral_settings(db: AsyncSession = Depends(get_db)) -> dict:
    enabled = (await settings_q.get_setting(db, "referral_enabled", "1")) != "0"
    reward_days = await settings_q.get_int_setting(db, "referral_reward_days", 3)
    return {"enabled": enabled, "reward_days": reward_days}


@router.put("/referrals/settings")
async def admin_referral_settings_update(
    enabled: bool = Body(...),
    reward_days: int = Body(..., ge=1, le=365),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await settings_q.set_setting(db, "referral_enabled", "1" if enabled else "0")
    await settings_q.set_setting(db, "referral_reward_days", str(reward_days))
    return {"enabled": enabled, "reward_days": reward_days}
