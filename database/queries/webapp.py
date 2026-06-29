"""Запросы для пользовательского мини-апп."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, case, desc, func, or_, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import ContactTrust, MessageLog, MutualRating, User


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


# ── Network helpers ───────────────────────────────────────────────────────

def _has_sub_fields(status: str | None, expires_at: datetime | None) -> bool:
    """Проверяет активность подписки по полям без загрузки объекта User."""
    if status == "lifetime":
        return True
    if status == "active":
        if expires_at is None:
            return True
        exp = expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return exp > datetime.now(timezone.utc)
    return False


# ── Network queries ───────────────────────────────────────────────────────

async def get_network_status(db: AsyncSession, telegram_id: int) -> dict:
    """Статус пользователя в сети связей."""
    res = await db.execute(
        select(User.network_visible, User.network_consent_at).where(
            User.telegram_id == telegram_id
        )
    )
    row = res.one_or_none()
    if row is None:
        return {"in_network": False, "consent_at": None, "visible": False}
    visible, consent_at = row
    return {
        "in_network": consent_at is not None,
        "consent_at": consent_at.isoformat() if consent_at else None,
        "visible": bool(visible),
    }


async def join_network(db: AsyncSession, telegram_id: int, visible: bool) -> dict:
    """Вступить в сеть связей (установить consent_at = NOW())."""
    await db.execute(
        update(User)
        .where(User.telegram_id == telegram_id)
        .values(network_visible=visible, network_consent_at=func.now())
    )
    await db.commit()
    return await get_network_status(db, telegram_id)


async def update_network_visibility(db: AsyncSession, telegram_id: int, visible: bool) -> dict:
    """Обновить видимость пользователя в сети (не меняет consent_at)."""
    await db.execute(
        update(User)
        .where(User.telegram_id == telegram_id)
        .values(network_visible=visible)
    )
    await db.commit()
    return {"visible": visible}


async def get_network_graph(db: AsyncSession, telegram_id: int, is_premium: bool) -> dict:
    """Граф сети связей пользователя.

    1-й уровень — всегда. 2-й уровень — только при is_premium=True.
    """
    nodes: list[dict] = []
    edges: list[dict] = []

    # Self node
    self_res = await db.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    self_user = self_res.scalar_one_or_none()

    if self_user:
        nodes.append({
            "id": f"self:{telegram_id}",
            "label": self_user.full_name,
            "type": "self",
            "has_subscription": _has_sub_fields(self_user.subscription_status, self_user.subscription_expires_at),
            "message_count": 0,
            "trust_score": None,
        })

    # 1st degree: contacts found in messages_log that also have network_visible=True
    first_q = (
        select(
            MessageLog.chat_id,
            func.count(MessageLog.id).label("message_count"),
            User.full_name,
            User.subscription_status,
            User.subscription_expires_at,
        )
        .join(User, and_(User.telegram_id == MessageLog.chat_id, User.network_visible.is_(True)))
        .where(MessageLog.user_id == telegram_id, MessageLog.chat_id != telegram_id)
        .group_by(
            MessageLog.chat_id,
            User.full_name,
            User.subscription_status,
            User.subscription_expires_at,
        )
    )
    first_contacts = (await db.execute(first_q)).all()

    first_ids: set[int] = set()

    for row in first_contacts:
        first_ids.add(row.chat_id)

        # Mutual rating between self and this 1st-degree contact
        mr_res = await db.execute(
            select(MutualRating.mutual_score)
            .where(
                MutualRating.status == "active",
                or_(
                    and_(MutualRating.requester_id == telegram_id, MutualRating.target_id == row.chat_id),
                    and_(MutualRating.requester_id == row.chat_id, MutualRating.target_id == telegram_id),
                ),
            )
            .limit(1)
        )
        trust_score = mr_res.scalar_one_or_none()

        nodes.append({
            "id": f"n:{row.chat_id}",
            "label": row.full_name,
            "type": "first",
            "has_subscription": _has_sub_fields(row.subscription_status, row.subscription_expires_at),
            "message_count": row.message_count,
            "trust_score": trust_score,
        })
        edges.append({
            "source": f"self:{telegram_id}",
            "target": f"n:{row.chat_id}",
            "weight": row.message_count,
            "trust_score": trust_score,
        })

    # 2nd degree (premium only)
    if is_premium and first_ids:
        exclude_ids = first_ids | {telegram_id}
        second_seen: set[int] = set()

        for contact_id in list(first_ids):
            second_q = (
                select(
                    MessageLog.chat_id,
                    func.count(MessageLog.id).label("message_count"),
                    User.full_name,
                    User.subscription_status,
                    User.subscription_expires_at,
                )
                .join(User, and_(User.telegram_id == MessageLog.chat_id, User.network_visible.is_(True)))
                .where(
                    MessageLog.user_id == contact_id,
                    MessageLog.chat_id.not_in(exclude_ids),
                )
                .group_by(
                    MessageLog.chat_id,
                    User.full_name,
                    User.subscription_status,
                    User.subscription_expires_at,
                )
            )
            second_contacts = (await db.execute(second_q)).all()

            for srow in second_contacts:
                if srow.chat_id not in second_seen:
                    second_seen.add(srow.chat_id)
                    nodes.append({
                        "id": f"n:{srow.chat_id}",
                        "label": srow.full_name,
                        "type": "second",
                        "has_subscription": _has_sub_fields(
                            srow.subscription_status, srow.subscription_expires_at
                        ),
                        "message_count": srow.message_count,
                        "trust_score": None,
                    })
                edges.append({
                    "source": f"n:{contact_id}",
                    "target": f"n:{srow.chat_id}",
                    "weight": srow.message_count,
                    "trust_score": None,
                })

    # Total users who have joined the network
    total_res = await db.execute(
        select(func.count()).select_from(User).where(User.network_consent_at.is_not(None))
    )
    total_in_network = int(total_res.scalar() or 0)

    return {
        "nodes": nodes,
        "edges": edges,
        "is_premium": is_premium,
        "total_in_network": total_in_network,
    }
