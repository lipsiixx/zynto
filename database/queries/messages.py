"""Сохранение и получение перехваченных сообщений."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import MessageLog


async def find_message(
    db: AsyncSession, user_id: int, chat_id: int, message_id: int
) -> MessageLog | None:
    res = await db.execute(
        select(MessageLog).where(
            MessageLog.user_id == user_id,
            MessageLog.chat_id == chat_id,
            MessageLog.message_id == message_id,
        )
    )
    return res.scalars().first()


async def save_message(db: AsyncSession, **fields) -> MessageLog:
    record = MessageLog(**fields)
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def mark_edited(db: AsyncSession, record: MessageLog, new_text: str | None) -> None:
    if not record.is_edited and record.original_text is None:
        record.original_text = record.text_content
    record.text_content = new_text
    record.is_edited = True
    record.edit_count = (record.edit_count or 0) + 1
    record.edited_at = datetime.now(timezone.utc)
    await db.commit()


async def mark_deleted(db: AsyncSession, record: MessageLog) -> None:
    record.is_deleted = True
    record.deleted_at = datetime.now(timezone.utc)
    await db.commit()


async def list_chats_with_events(db: AsyncSession, user_id: int) -> list[dict]:
    """Собеседники, у которых были удалённые/изменённые сообщения."""
    res = await db.execute(
        select(MessageLog.chat_id, MessageLog.chat_title, MessageLog.is_deleted, MessageLog.is_edited,
               MessageLog.deleted_at, MessageLog.edited_at, MessageLog.received_at)
        .where(MessageLog.user_id == user_id)
        .where(or_(MessageLog.is_deleted == True, MessageLog.is_edited == True))  # noqa: E712
    )
    rows = res.all()
    agg: dict[int, dict] = {}
    for chat_id, title, is_del, is_edit, del_at, edit_at, recv_at in rows:
        entry = agg.setdefault(chat_id, {"chat_id": chat_id, "chat_title": title, "deleted": 0, "edited": 0, "last": recv_at})
        if title:
            entry["chat_title"] = title
        if is_del:
            entry["deleted"] += 1
        if is_edit:
            entry["edited"] += 1
        event_time = del_at or edit_at or recv_at
        if event_time and (entry["last"] is None or event_time > entry["last"]):
            entry["last"] = event_time
    result = list(agg.values())
    result.sort(key=lambda x: (x["last"] is not None, x["last"]), reverse=True)
    return result


async def list_chat_events(
    db: AsyncSession, user_id: int, chat_id: int, flt: str = "all", limit: int = 10, offset: int = 0
) -> tuple[list[MessageLog], int]:
    base = select(MessageLog).where(MessageLog.user_id == user_id, MessageLog.chat_id == chat_id)
    if flt == "deleted":
        base = base.where(MessageLog.is_deleted == True)  # noqa: E712
    elif flt == "edited":
        base = base.where(MessageLog.is_edited == True)  # noqa: E712
    elif flt == "media":
        base = base.where(MessageLog.file_id.is_not(None))
    else:  # all = только события
        base = base.where(or_(MessageLog.is_deleted == True, MessageLog.is_edited == True))  # noqa: E712

    count_stmt = select(func.count()).select_from(base.subquery())
    total = int((await db.execute(count_stmt)).scalar() or 0)

    res = await db.execute(
        base.order_by(desc(MessageLog.received_at)).limit(limit).offset(offset)
    )
    return list(res.scalars().all()), total


async def list_chat_media(
    db: AsyncSession, user_id: int, chat_id: int, limit: int = 10, offset: int = 0
) -> tuple[list[MessageLog], int]:
    base = select(MessageLog).where(
        MessageLog.user_id == user_id,
        MessageLog.chat_id == chat_id,
        MessageLog.file_id.is_not(None),
    )
    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0)
    res = await db.execute(base.order_by(desc(MessageLog.received_at)).limit(limit).offset(offset))
    return list(res.scalars().all()), total


async def search_text(
    db: AsyncSession, user_id: int, chat_id: int, query: str, limit: int = 10
) -> list[MessageLog]:
    res = await db.execute(
        select(MessageLog)
        .where(
            MessageLog.user_id == user_id,
            MessageLog.chat_id == chat_id,
            or_(
                MessageLog.text_content.ilike(f"%{query}%"),
                MessageLog.original_text.ilike(f"%{query}%"),
            ),
        )
        .order_by(desc(MessageLog.received_at))
        .limit(limit)
    )
    return list(res.scalars().all())


async def count_all(db: AsyncSession) -> int:
    return int((await db.execute(select(func.count(MessageLog.id)))).scalar() or 0)


async def count_deleted(db: AsyncSession) -> int:
    res = await db.execute(select(func.count(MessageLog.id)).where(MessageLog.is_deleted == True))  # noqa: E712
    return int(res.scalar() or 0)


async def count_edited(db: AsyncSession) -> int:
    res = await db.execute(select(func.count(MessageLog.id)).where(MessageLog.is_edited == True))  # noqa: E712
    return int(res.scalar() or 0)


async def count_for_user(db: AsyncSession, user_id: int) -> int:
    res = await db.execute(select(func.count(MessageLog.id)).where(MessageLog.user_id == user_id))
    return int(res.scalar() or 0)


def _now() -> datetime:
    return datetime.now(timezone.utc)
