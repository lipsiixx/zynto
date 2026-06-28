"""GET /users, GET /users/:id, GET /users/:id/chats, GET /users/:id/contacts"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db, require_auth
from api.schemas import (
    ChatOut,
    ChatsListOut,
    ContactOut,
    ContactsListOut,
    Pagination,
    UserOut,
    UsersListOut,
)
from database.queries import api as api_q
from database.queries import users as users_q

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(require_auth)])


@router.get("", response_model=UsersListOut)
async def list_users(
    q: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> UsersListOut:
    users, total = await users_q.list_users(db, q=q, status=status, page=page, limit=limit)
    return UsersListOut(
        data=[UserOut.from_orm(u) for u in users],
        pagination=Pagination(
            page=page,
            limit=limit,
            total=total,
            totalPages=max(1, (total + limit - 1) // limit),
        ),
    )


@router.get("/{user_id}", response_model=UserOut)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)) -> UserOut:
    user = await users_q.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(404, detail="not_found")
    return UserOut.from_orm(user)


@router.get("/{user_id}/chats", response_model=ChatsListOut)
async def get_user_chats(
    user_id: int,
    q: Optional[str] = Query(None),
    filter: Optional[str] = Query(None, alias="filter"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> ChatsListOut:
    user = await users_q.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(404, detail="not_found")
    chats, total = await api_q.list_user_chats(
        db, user.telegram_id, q=q, filter_=filter, page=page, limit=limit
    )
    return ChatsListOut(
        data=[ChatOut(**c) for c in chats],
        pagination=Pagination(
            page=page, limit=limit, total=total,
            totalPages=max(1, (total + limit - 1) // limit),
        ),
    )


@router.get("/{user_id}/contacts", response_model=ContactsListOut)
async def get_user_contacts(
    user_id: int,
    min_weight: int = Query(1, ge=1),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> ContactsListOut:
    user = await users_q.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(404, detail="not_found")
    contacts, total = await api_q.list_user_contacts(
        db, user.telegram_id, min_weight=min_weight, page=page, limit=limit
    )
    return ContactsListOut(
        data=[ContactOut(**c) for c in contacts],
        pagination=Pagination(
            page=page, limit=limit, total=total,
            totalPages=max(1, (total + limit - 1) // limit),
        ),
    )
