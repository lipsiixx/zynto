"""Pydantic-схемы ответов REST API."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, field_validator

_ONLINE_WINDOW_SECONDS = 300  # 5 минут


class Pagination(BaseModel):
    page: int
    limit: int
    total: int
    totalPages: int


class MessageCursor(BaseModel):
    before: Optional[int] = None
    hasMore: bool


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class UserOut(BaseModel):
    id: int
    telegramId: int
    username: Optional[str]
    fullName: str
    languageCode: str
    phone: Optional[str]
    avatarFileUniqueId: Optional[str]
    subscriptionStatus: str
    subscriptionExpiresAt: Optional[datetime]
    isBanned: bool
    isBlocked: bool
    lastActiveAt: datetime
    isOnline: bool
    createdAt: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm(cls, user: Any) -> "UserOut":  # type: ignore[override]
        now = datetime.now(timezone.utc)
        last = user.last_active_at
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        is_online = (now - last).total_seconds() < _ONLINE_WINDOW_SECONDS
        return cls(
            id=user.id,
            telegramId=user.telegram_id,
            username=user.username,
            fullName=user.full_name,
            languageCode=user.language_code,
            phone=getattr(user, "phone", None),
            avatarFileUniqueId=getattr(user, "avatar_file_unique_id", None),
            subscriptionStatus=user.subscription_status,
            subscriptionExpiresAt=user.subscription_expires_at,
            isBanned=user.is_banned,
            isBlocked=user.is_blocked,
            lastActiveAt=user.last_active_at,
            isOnline=is_online,
            createdAt=user.created_at,
        )


class UsersListOut(BaseModel):
    data: list[UserOut]
    pagination: Pagination


# ---------------------------------------------------------------------------
# Chat (агрегат)
# ---------------------------------------------------------------------------

class ChatOut(BaseModel):
    chatId: int
    title: Optional[str]
    userId: int
    messageCount: int
    deletedCount: int
    editedCount: int
    lastMessageAt: Optional[datetime]


class ChatsListOut(BaseModel):
    data: list[ChatOut]
    pagination: Pagination


# ---------------------------------------------------------------------------
# Message
# ---------------------------------------------------------------------------

class MessageOut(BaseModel):
    id: int
    messageId: int
    chatId: int
    userId: int
    businessConnectionId: str
    senderId: Optional[int]
    senderName: Optional[str]
    senderUsername: Optional[str]
    isOutgoing: bool
    messageType: str
    textContent: Optional[str]
    originalText: Optional[str]
    fileUniqueId: Optional[str]
    fileSize: Optional[int]
    mimeType: Optional[str]
    width: Optional[int]
    height: Optional[int]
    durationSeconds: Optional[int]
    isEdited: bool
    isDeleted: bool
    editCount: int
    editedAt: Optional[datetime]
    deletedAt: Optional[datetime]
    receivedAt: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_record(cls, r: Any) -> "MessageOut":
        if r.is_deleted:
            return cls(
                id=r.id,
                messageId=r.message_id,
                chatId=r.chat_id,
                userId=r.user_id,
                businessConnectionId=r.business_connection_id,
                senderId=r.sender_id,
                senderName=r.sender_name,
                senderUsername=None,
                isOutgoing=r.is_outgoing,
                messageType=r.message_type,
                textContent=None,
                originalText=None,
                fileUniqueId=None,
                fileSize=None,
                mimeType=None,
                width=None,
                height=None,
                durationSeconds=None,
                isEdited=r.is_edited,
                isDeleted=True,
                editCount=r.edit_count or 0,
                editedAt=r.edited_at,
                deletedAt=r.deleted_at,
                receivedAt=r.received_at,
            )
        return cls(
            id=r.id,
            messageId=r.message_id,
            chatId=r.chat_id,
            userId=r.user_id,
            businessConnectionId=r.business_connection_id,
            senderId=r.sender_id,
            senderName=r.sender_name,
            senderUsername=r.sender_username,
            isOutgoing=r.is_outgoing,
            messageType=r.message_type,
            textContent=r.text_content,
            originalText=r.original_text,
            fileUniqueId=r.file_unique_id,
            fileSize=r.file_size,
            mimeType=r.mime_type,
            width=r.width,
            height=r.height,
            durationSeconds=r.duration_seconds,
            isEdited=r.is_edited,
            isDeleted=False,
            editCount=r.edit_count or 0,
            editedAt=r.edited_at,
            deletedAt=r.deleted_at,
            receivedAt=r.received_at,
        )


class MessagesListOut(BaseModel):
    data: list[MessageOut]
    cursor: MessageCursor


# ---------------------------------------------------------------------------
# Media
# ---------------------------------------------------------------------------

class MediaOut(BaseModel):
    cacheId: Optional[int]
    fileUniqueId: str
    fileType: Optional[str]
    fileSize: Optional[int]
    mimeType: Optional[str]
    contentHash: Optional[str]
    hasLocalFile: bool
    cachedAt: Optional[datetime]
    lastUsedAt: Optional[datetime]


class MediaListOut(BaseModel):
    data: list[MediaOut]
    pagination: Pagination


# ---------------------------------------------------------------------------
# Contact
# ---------------------------------------------------------------------------

class ContactOut(BaseModel):
    senderId: Optional[int]
    senderName: Optional[str]
    senderUsername: Optional[str]
    messageCount: int
    sharedChatsCount: int


class ContactsListOut(BaseModel):
    data: list[ContactOut]
    pagination: Pagination


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    avatarFileUniqueId: Optional[str]


class GraphEdge(BaseModel):
    source: str
    target: str
    weight: int


class GraphOut(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

class CpuOut(BaseModel):
    usagePercent: float
    cores: int


class MemoryOut(BaseModel):
    totalBytes: int
    usedBytes: int
    freeBytes: int


class DiskOut(BaseModel):
    totalBytes: int
    usedBytes: int
    freeBytes: int


class ServerStatsOut(BaseModel):
    cpu: CpuOut
    memory: MemoryOut
    disk: DiskOut
    uptimeSeconds: float
    loadAvg: list[float]
    measuredAt: datetime


class ProxyInfo(BaseModel):
    proxy: str
    state: str
    avgLatencySeconds: float
    failsInWindow: int
    windowSize: int
    consecutiveFails: int
    consecutiveOks: int
    lastCheckedSecondsAgo: Optional[float]
    monitorRunning: bool


class ProxyStatsOut(BaseModel):
    active: Optional[ProxyInfo]
    noProxy: bool


class GlobalUserStatsOut(BaseModel):
    total: int
    online: int
    newToday: int
    newThisWeek: int
    activeSubscribers: int
    measuredAt: datetime


class UserStatsOut(BaseModel):
    userId: int
    telegramId: int
    totalMessages: int
    deletedMessages: int
    editedMessages: int
    totalMedia: int
    totalChats: int
    firstMessageAt: Optional[datetime]
    lastMessageAt: Optional[datetime]
    isOnline: bool


class UserChatStatsOut(BaseModel):
    userId: int
    chatId: int
    messageCount: int
    deletedCount: int
    editedCount: int
    mediaCount: int
    firstMessageAt: Optional[datetime]
    lastMessageAt: Optional[datetime]
