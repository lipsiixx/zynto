"""Агрегационные запросы для REST API веб-панели администратора."""
from __future__ import annotations

from sqlalchemy import and_, case, desc, distinct, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Admin, MediaCache, MessageLog, User


# ---------------------------------------------------------------------------
# Чаты пользователя (агрегация из messages_log)
# ---------------------------------------------------------------------------

async def list_user_chats(
    db: AsyncSession,
    telegram_id: int,
    q: str | None = None,
    filter_: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> tuple[list[dict], int]:
    base = (
        select(
            MessageLog.chat_id,
            func.max(MessageLog.chat_title).label("chat_title"),
            func.count(MessageLog.id).label("message_count"),
            func.sum(case((MessageLog.is_deleted == True, 1), else_=0)).label("deleted_count"),
            func.sum(case((MessageLog.is_edited == True, 1), else_=0)).label("edited_count"),
            func.max(MessageLog.received_at).label("last_message_at"),
        )
        .where(MessageLog.user_id == telegram_id)
        .group_by(MessageLog.chat_id)
    )

    if q:
        base = base.having(func.max(MessageLog.chat_title).ilike(f"%{q}%"))
    if filter_ == "has_deleted":
        base = base.having(func.sum(case((MessageLog.is_deleted == True, 1), else_=0)) > 0)
    elif filter_ == "has_edited":
        base = base.having(func.sum(case((MessageLog.is_edited == True, 1), else_=0)) > 0)

    count_q = select(func.count()).select_from(base.subquery())
    total = int((await db.execute(count_q)).scalar() or 0)

    rows = (await db.execute(
        base.order_by(desc("last_message_at")).limit(limit).offset((page - 1) * limit)
    )).all()

    return [
        {
            "chatId": r.chat_id,
            "title": r.chat_title,
            "userId": telegram_id,
            "messageCount": r.message_count,
            "deletedCount": int(r.deleted_count or 0),
            "editedCount": int(r.edited_count or 0),
            "lastMessageAt": r.last_message_at,
        }
        for r in rows
    ], total


# ---------------------------------------------------------------------------
# Контакты пользователя
# ---------------------------------------------------------------------------

async def list_user_contacts(
    db: AsyncSession,
    telegram_id: int,
    min_weight: int = 1,
    page: int = 1,
    limit: int = 20,
) -> tuple[list[dict], int]:
    base = (
        select(
            MessageLog.sender_id,
            func.max(MessageLog.sender_name).label("sender_name"),
            func.max(MessageLog.sender_username).label("sender_username"),
            func.count(MessageLog.id).label("message_count"),
            func.count(distinct(MessageLog.chat_id)).label("shared_chats_count"),
        )
        .where(
            MessageLog.user_id == telegram_id,
            MessageLog.sender_id.is_not(None),
            MessageLog.is_outgoing == False,  # noqa: E712
        )
        .group_by(MessageLog.sender_id)
        .having(func.count(MessageLog.id) >= min_weight)
    )

    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0)

    rows = (await db.execute(
        base.order_by(desc("message_count")).limit(limit).offset((page - 1) * limit)
    )).all()

    return [
        {
            "senderId": r.sender_id,
            "senderName": r.sender_name,
            "senderUsername": r.sender_username,
            "messageCount": r.message_count,
            "sharedChatsCount": r.shared_chats_count,
        }
        for r in rows
    ], total


# ---------------------------------------------------------------------------
# Сообщения чата (cursor pagination)
# ---------------------------------------------------------------------------

async def list_chat_messages(
    db: AsyncSession,
    user_telegram_id: int,
    chat_id: int,
    before: int | None = None,
    limit: int = 50,
) -> tuple[list[MessageLog], bool]:
    """Возвращает (messages, has_more). Сортировка: от новых к старым."""
    q = (
        select(MessageLog)
        .where(
            MessageLog.user_id == user_telegram_id,
            MessageLog.chat_id == chat_id,
        )
    )
    if before is not None:
        q = q.where(MessageLog.id < before)

    q = q.order_by(desc(MessageLog.id)).limit(limit + 1)
    rows = list((await db.execute(q)).scalars().all())
    has_more = len(rows) > limit
    return rows[:limit], has_more


# ---------------------------------------------------------------------------
# Медиа чата
# ---------------------------------------------------------------------------

async def list_chat_media(
    db: AsyncSession,
    user_telegram_id: int,
    chat_id: int,
    mime_prefix: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> tuple[list[dict], int]:
    base = (
        select(
            MessageLog.file_unique_id,
            MessageLog.file_id,
            MessageLog.message_type,
            MessageLog.file_size,
            MessageLog.mime_type,
            MessageLog.received_at,
            MediaCache.id.label("cache_id"),
            MediaCache.content_hash,
            MediaCache.local_path,
            MediaCache.cached_at,
            MediaCache.last_used_at,
        )
        .join(MediaCache, MediaCache.file_unique_id == MessageLog.file_unique_id, isouter=True)
        .where(
            MessageLog.user_id == user_telegram_id,
            MessageLog.chat_id == chat_id,
            MessageLog.file_unique_id.is_not(None),
        )
    )
    if mime_prefix:
        base = base.where(MessageLog.mime_type.ilike(f"{mime_prefix}%"))

    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar() or 0)
    rows = (await db.execute(
        base.order_by(desc(MessageLog.received_at)).limit(limit).offset((page - 1) * limit)
    )).all()

    return [
        {
            "cacheId": r.cache_id,
            "fileUniqueId": r.file_unique_id,
            "fileType": r.message_type,
            "fileSize": r.file_size,
            "mimeType": r.mime_type,
            "contentHash": r.content_hash,
            "hasLocalFile": bool(r.local_path),
            "cachedAt": r.cached_at or r.received_at,
            "lastUsedAt": r.last_used_at or r.received_at,
        }
        for r in rows
    ], total


# ---------------------------------------------------------------------------
# Граф связей
# ---------------------------------------------------------------------------

async def get_graph(
    db: AsyncSession,
    min_weight: int = 1,
) -> dict:
    # Рёбра: подписчик ↔ контакт
    edge_rows = (await db.execute(
        select(
            MessageLog.user_id.label("source_tg"),
            MessageLog.sender_id.label("target_id"),
            func.count(MessageLog.id).label("weight"),
        )
        .where(
            MessageLog.sender_id.is_not(None),
            MessageLog.is_outgoing == False,  # noqa: E712
        )
        .group_by(MessageLog.user_id, MessageLog.sender_id)
        .having(func.count(MessageLog.id) >= min_weight)
    )).all()

    # telegram_id подписчиков, присутствующих в рёбрах
    subscriber_tg_ids = {r.source_tg for r in edge_rows}
    contact_ids = {r.target_id for r in edge_rows}

    # Данные подписчиков (без админов)
    subscribers: dict[int, User] = {}
    if subscriber_tg_ids:
        admin_ids = set((await db.execute(select(Admin.telegram_id))).scalars().all())
        filtered_ids = subscriber_tg_ids - admin_ids
        if filtered_ids:
            rows = (await db.execute(
                select(User).where(User.telegram_id.in_(filtered_ids))
            )).scalars().all()
            subscribers = {u.telegram_id: u for u in rows}

    # Имена контактов (берём из messages_log)
    contact_names: dict[int, tuple[str | None, str | None]] = {}
    if contact_ids:
        name_rows = (await db.execute(
            select(
                MessageLog.sender_id,
                func.max(MessageLog.sender_name).label("name"),
                func.max(MessageLog.sender_username).label("username"),
            )
            .where(MessageLog.sender_id.in_(contact_ids))
            .group_by(MessageLog.sender_id)
        )).all()
        contact_names = {r.sender_id: (r.name, r.username) for r in name_rows}

    nodes = []
    for tg_id, user in subscribers.items():
        nodes.append({
            "id": f"u:{tg_id}",
            "label": user.full_name or user.username or str(tg_id),
            "type": "subscriber",
            "avatarFileUniqueId": user.avatar_file_unique_id,
        })
    for cid in contact_ids:
        name, uname = contact_names.get(cid, (None, None))
        nodes.append({
            "id": f"c:{cid}",
            "label": name or uname or str(cid),
            "type": "contact",
            "avatarFileUniqueId": None,
        })

    # Только рёбра, у которых source-подписчик есть в users
    valid_subs = set(subscribers.keys())
    edges = [
        {"source": f"u:{r.source_tg}", "target": f"c:{r.target_id}", "weight": r.weight}
        for r in edge_rows
        if r.source_tg in valid_subs
    ]

    return {"nodes": nodes, "edges": edges}


# ---------------------------------------------------------------------------
# Статистика пользователей
# ---------------------------------------------------------------------------

async def get_user_stats(db: AsyncSession, telegram_id: int) -> dict:
    msg_q = select(
        func.count(MessageLog.id).label("total"),
        func.sum(case((MessageLog.is_deleted == True, 1), else_=0)).label("deleted"),
        func.sum(case((MessageLog.is_edited == True, 1), else_=0)).label("edited"),
        func.sum(case((MessageLog.file_unique_id.is_not(None), 1), else_=0)).label("media"),
        func.count(distinct(MessageLog.chat_id)).label("chats"),
        func.min(MessageLog.received_at).label("first_at"),
        func.max(MessageLog.received_at).label("last_at"),
    ).where(MessageLog.user_id == telegram_id)
    r = (await db.execute(msg_q)).one()
    return {
        "totalMessages": r.total or 0,
        "deletedMessages": int(r.deleted or 0),
        "editedMessages": int(r.edited or 0),
        "totalMedia": int(r.media or 0),
        "totalChats": r.chats or 0,
        "firstMessageAt": r.first_at,
        "lastMessageAt": r.last_at,
    }


async def get_user_chat_stats(db: AsyncSession, telegram_id: int, chat_id: int) -> dict:
    r = (await db.execute(
        select(
            func.count(MessageLog.id).label("total"),
            func.sum(case((MessageLog.is_deleted == True, 1), else_=0)).label("deleted"),
            func.sum(case((MessageLog.is_edited == True, 1), else_=0)).label("edited"),
            func.sum(case((MessageLog.file_unique_id.is_not(None), 1), else_=0)).label("media"),
            func.min(MessageLog.received_at).label("first_at"),
            func.max(MessageLog.received_at).label("last_at"),
        )
        .where(MessageLog.user_id == telegram_id, MessageLog.chat_id == chat_id)
    )).one()
    return {
        "userId": telegram_id,
        "chatId": chat_id,
        "messageCount": r.total or 0,
        "deletedCount": int(r.deleted or 0),
        "editedCount": int(r.edited or 0),
        "mediaCount": int(r.media or 0),
        "firstMessageAt": r.first_at,
        "lastMessageAt": r.last_at,
    }
