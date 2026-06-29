"""SQLAlchemy 2.x модели всех таблиц бота."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import TIMESTAMP


class Base(DeclarativeBase):
    pass


def _ts():
    """TIMESTAMPTZ колонка."""
    return TIMESTAMP(timezone=True)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    language_code: Mapped[str] = mapped_column(String(10), default="ru")
    phone: Mapped[str | None] = mapped_column(String(20))
    avatar_file_id: Mapped[str | None] = mapped_column(String(512))
    avatar_file_unique_id: Mapped[str | None] = mapped_column(String(255))
    subscription_status: Mapped[str] = mapped_column(String(20), default="none")  # none|active|lifetime|expired
    subscription_expires_at: Mapped[datetime | None] = mapped_column(_ts())
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    ban_reason: Mapped[str | None] = mapped_column(Text)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)  # заблокировал бота
    pending_promo_id: Mapped[int | None] = mapped_column(BigInteger)  # ожидающий скидочный промокод
    referred_by: Mapped[int | None] = mapped_column(BigInteger)       # telegram_id пригласившего
    referral_rewarded: Mapped[bool] = mapped_column(Boolean, server_default="false", default=False)
    nudge_sent_at: Mapped[datetime | None] = mapped_column(_ts())     # последний раз отправлено подначивание
    nudge_next_at: Mapped[datetime | None] = mapped_column(_ts())     # запланированное время следующего
    created_at: Mapped[datetime] = mapped_column(_ts(), server_default=func.now())
    last_active_at: Mapped[datetime] = mapped_column(_ts(), server_default=func.now())


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(512))
    is_superadmin: Mapped[bool] = mapped_column(Boolean, default=False)
    added_by: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(_ts(), server_default=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Tariff(Base):
    __tablename__ = "tariffs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    duration_days: Mapped[int | None] = mapped_column(Integer)  # NULL = lifetime
    price_stars: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(_ts(), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(_ts(), server_default=func.now(), onupdate=func.now())


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    tariff_id: Mapped[int | None] = mapped_column(BigInteger)
    started_at: Mapped[datetime] = mapped_column(_ts(), server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(_ts())
    payment_method: Mapped[str] = mapped_column(String(20), nullable=False)  # stars|promo_code|gift|gift_purchase|manual
    promo_code_id: Mapped[int | None] = mapped_column(BigInteger)
    telegram_payment_charge_id: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(_ts(), server_default=func.now())


class PromoCode(Base):
    __tablename__ = "promo_codes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    code_type: Mapped[str] = mapped_column(String(20), server_default="access")  # access | discount
    # access-code fields
    duration_days: Mapped[int | None] = mapped_column(Integer)  # минуты (NULL = lifetime)
    duration_label: Mapped[str | None] = mapped_column(String(50))
    # discount-code fields
    discount_stars: Mapped[int | None] = mapped_column(Integer)
    discount_tariff_id: Mapped[int | None] = mapped_column(BigInteger)  # NULL = любой тариф
    # usage tracking
    max_uses: Mapped[int | None] = mapped_column(Integer, server_default="1")  # NULL = без лимита
    uses_count: Mapped[int] = mapped_column(Integer, server_default="0", default=0)
    used_by: Mapped[int | None] = mapped_column(BigInteger)   # для обратной совместимости
    used_at: Mapped[datetime | None] = mapped_column(_ts())
    code_expires_at: Mapped[datetime | None] = mapped_column(_ts())
    access_expires_at: Mapped[datetime | None] = mapped_column(_ts())
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(_ts(), server_default=func.now())


class BusinessConnection(Base):
    __tablename__ = "business_connections"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    business_connection_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    connected_at: Mapped[datetime] = mapped_column(_ts(), server_default=func.now())
    disconnected_at: Mapped[datetime | None] = mapped_column(_ts())


class MessageLog(Base):
    __tablename__ = "messages_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    business_connection_id: Mapped[str] = mapped_column(String(255), nullable=False)
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    chat_title: Mapped[str | None] = mapped_column(String(512))
    sender_id: Mapped[int | None] = mapped_column(BigInteger)
    sender_name: Mapped[str | None] = mapped_column(String(512))
    sender_username: Mapped[str | None] = mapped_column(String(255))
    is_outgoing: Mapped[bool] = mapped_column(Boolean, default=False)
    message_type: Mapped[str] = mapped_column(String(30), nullable=False)

    text_content: Mapped[str | None] = mapped_column(Text)
    original_text: Mapped[str | None] = mapped_column(Text)

    file_id: Mapped[str | None] = mapped_column(String(512))
    file_unique_id: Mapped[str | None] = mapped_column(String(255))
    file_size: Mapped[int | None] = mapped_column(BigInteger)
    local_path: Mapped[str | None] = mapped_column(Text)
    mime_type: Mapped[str | None] = mapped_column(String(100))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False)
    edit_count: Mapped[int] = mapped_column(Integer, default=0)

    received_at: Mapped[datetime] = mapped_column(_ts(), server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(_ts())
    edited_at: Mapped[datetime | None] = mapped_column(_ts())

    __table_args__ = (
        Index("ix_messages_user_chat", "user_id", "chat_id"),
        Index("ix_messages_user_deleted", "user_id", "is_deleted"),
        Index("ix_messages_file_unique", "file_unique_id"),
        Index("ix_messages_received", "received_at"),
        Index("ix_messages_lookup", "user_id", "chat_id", "message_id"),
    )


class MediaCache(Base):
    __tablename__ = "media_cache"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    file_unique_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    file_id: Mapped[str] = mapped_column(String(512), nullable=False)
    file_type: Mapped[str | None] = mapped_column(String(30))
    file_size: Mapped[int | None] = mapped_column(BigInteger)
    content_hash: Mapped[str | None] = mapped_column(String(64))  # SHA-256 hex, для ETag
    local_path: Mapped[str | None] = mapped_column(Text)
    cached_at: Mapped[datetime] = mapped_column(_ts(), server_default=func.now())
    last_used_at: Mapped[datetime] = mapped_column(_ts(), server_default=func.now())


class NudgeMessage(Base):
    __tablename__ = "nudge_messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_file_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_type: Mapped[str | None] = mapped_column(String(10), nullable=True)  # "photo" | "video"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(_ts(), server_default=func.now())


class ContactTrust(Base):
    __tablename__ = "contact_trust"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    manual_score: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0-100, user override
    updated_at: Mapped[datetime] = mapped_column(_ts(), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_contact_trust_user_chat", "user_id", "chat_id", unique=True),
    )


class MutualRating(Base):
    __tablename__ = "mutual_rating"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    requester_id: Mapped[int] = mapped_column(BigInteger, nullable=False)   # кто отправил запрос
    target_id: Mapped[int] = mapped_column(BigInteger, nullable=False)      # кому отправили
    status: Mapped[str] = mapped_column(String(20), default="pending")      # pending|active|declined|cancelled
    requester_score: Mapped[int | None] = mapped_column(Integer)            # оценка от инициатора (0-100)
    target_score: Mapped[int | None] = mapped_column(Integer)               # оценка от получателя (0-100)
    mutual_score: Mapped[int | None] = mapped_column(Integer)               # среднее (вычисляется при активации)
    created_at: Mapped[datetime] = mapped_column(_ts(), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(_ts(), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_mutual_rating_pair", "requester_id", "target_id", unique=True),
        Index("ix_mutual_rating_target", "target_id"),
    )


class ReferralReward(Base):
    __tablename__ = "referral_rewards"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    referrer_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    referred_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    days_granted: Mapped[int] = mapped_column(Integer, nullable=False)
    payment_method: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(_ts(), server_default=func.now())


class BotSetting(Base):
    __tablename__ = "bot_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_by: Mapped[int | None] = mapped_column(BigInteger)
    updated_at: Mapped[datetime] = mapped_column(_ts(), server_default=func.now(), onupdate=func.now())
