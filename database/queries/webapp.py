"""Запросы для пользовательского мини-апп."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import case, desc, func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import ContactTrust, MessageLog, User


def _compute_auto_score(total: int, deleted_from_them: int) -> int:
    delete_ratio = deleted_from_them / max(total, 1)
    activity_bonus = min(total / 100.0, 20.0)
    score = 50.0 - delete_ratio * 50.0 + activity_bonus
    return max(0, min(100, round(score)))


async def get_user_contacts(
    db: AsyncSession,
    telegram_id: int,
    q: str | None = None,
    page: int = 1,
    limit: int = 30,
) -> tuple[list[dict], int]:
    base = (
        select(
            MessageLog.chat_id,
            func.max(MessageLog.chat_title).label("chat_title"),
            func.count(MessageLog.id).label("total_messages"),
            func.sum(
                case((MessageLog.is_deleted.is_(True), 1), else_=0)
            ).label("deleted_count"),
            func.sum(
                case((MessageLog.is_edited.is_(True), 1), else_=0)
            ).label("edited_count"),
            func.sum(
                case(
                    (MessageLog.is_deleted.is_(True) & MessageLog.is_outgoing.is_(False), 1),
                    else_=0,
                )
            ).label("deleted_from_them"),
            func.max(MessageLog.received_at).label("last_message_at"),
        )
        .where(MessageLog.user_id == telegram_id)
        .group_by(MessageLog.chat_id)
    )

    if q:
        base = base.having(func.max(MessageLog.chat_title).ilike(f"%{q}%"))

    count_q = select(func.count()).select_from(base.subquery())
    total = int((await db.execute(count_q)).scalar() or 0)

    rows = (
        await db.execute(base.order_by(desc("last_message_at")).limit(limit).offset((page - 1) * limit))
    ).all()

    # Load trust overrides for these chats
    chat_ids = [r.chat_id for r in rows]
    trust_map: dict[int, int | None] = {}
    if chat_ids:
        trust_rows = await db.execute(
            select(ContactTrust.chat_id, ContactTrust.manual_score).where(
                ContactTrust.user_id == telegram_id,
                ContactTrust.chat_id.in_(chat_ids),
            )
        )
        for chat_id, manual_score in trust_rows.all():
            trust_map[chat_id] = manual_score

    result = []
    for r in rows:
        auto = _compute_auto_score(r.total_messages, r.deleted_from_them)
        manual = trust_map.get(r.chat_id)
        result.append({
            "chat_id": r.chat_id,
            "chat_title": r.chat_title,
            "total_messages": r.total_messages,
            "deleted_count": r.deleted_count,
            "edited_count": r.edited_count,
            "auto_score": auto,
            "manual_score": manual,
            "trust_score": manual if manual is not None else auto,
            "last_message_at": r.last_message_at,
        })
    return result, total


async def get_contact_events(
    db: AsyncSession,
    telegram_id: int,
    chat_id: int,
    flt: str = "all",
    page: int = 1,
    limit: int = 20,
) -> tuple[list[MessageLog], int]:
    from sqlalchemy import or_

    base = select(MessageLog).where(
        MessageLog.user_id == telegram_id,
        MessageLog.chat_id == chat_id,
    )
    if flt == "deleted":
        base = base.where(MessageLog.is_deleted.is_(True))
    elif flt == "edited":
        base = base.where(MessageLog.is_edited.is_(True))
    elif flt == "media":
        base = base.where(MessageLog.file_id.is_not(None))
    else:
        base = base.where(
            or_(MessageLog.is_deleted.is_(True), MessageLog.is_edited.is_(True))
        )

    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0)
    rows = await db.execute(
        base.order_by(desc(MessageLog.received_at)).limit(limit).offset((page - 1) * limit)
    )
    return list(rows.scalars().all()), total


async def get_contact_stats(
    db: AsyncSession,
    telegram_id: int,
    chat_id: int,
    days: int = 30,
) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = await db.execute(
        text(
            """
            SELECT
                DATE_TRUNC('day', received_at AT TIME ZONE 'UTC')::date AS day,
                COUNT(*) AS total,
                SUM(CASE WHEN is_deleted THEN 1 ELSE 0 END) AS deleted,
                SUM(CASE WHEN is_edited THEN 1 ELSE 0 END) AS edited
            FROM messages_log
            WHERE user_id = :uid AND chat_id = :cid AND received_at >= :since
            GROUP BY day
            ORDER BY day
            """
        ),
        {"uid": telegram_id, "cid": chat_id, "since": since},
    )
    return [
        {"day": str(r.day), "total": r.total, "deleted": r.deleted, "edited": r.edited}
        for r in rows.all()
    ]


async def get_trust(db: AsyncSession, telegram_id: int, chat_id: int) -> ContactTrust | None:
    res = await db.execute(
        select(ContactTrust).where(
            ContactTrust.user_id == telegram_id,
            ContactTrust.chat_id == chat_id,
        )
    )
    return res.scalar_one_or_none()


async def set_trust_score(
    db: AsyncSession, telegram_id: int, chat_id: int, score: int
) -> None:
    stmt = pg_insert(ContactTrust).values(
        user_id=telegram_id,
        chat_id=chat_id,
        manual_score=score,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["user_id", "chat_id"],
        set_={"manual_score": score, "updated_at": func.now()},
    )
    await db.execute(stmt)
    await db.commit()


async def clear_trust_score(db: AsyncSession, telegram_id: int, chat_id: int) -> None:
    record = await get_trust(db, telegram_id, chat_id)
    if record is not None:
        record.manual_score = None
        await db.commit()


async def get_user_summary(db: AsyncSession, telegram_id: int) -> dict:
    row = await db.execute(
        select(
            func.count(func.distinct(MessageLog.chat_id)).label("contacts"),
            func.count(MessageLog.id).label("total_messages"),
            func.sum(case((MessageLog.is_deleted.is_(True), 1), else_=0)).label("deleted"),
            func.sum(case((MessageLog.is_edited.is_(True), 1), else_=0)).label("edited"),
        ).where(MessageLog.user_id == telegram_id)
    )
    r = row.one()
    return {
        "contacts": r.contacts or 0,
        "total_messages": r.total_messages or 0,
        "deleted": r.deleted or 0,
        "edited": r.edited or 0,
    }
