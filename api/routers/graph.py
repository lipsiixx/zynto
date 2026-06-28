"""GET /graph — граф связей между подписчиками и их контактами."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db, require_auth
from api.schemas import GraphEdge, GraphNode, GraphOut
from database.queries import api as api_q

router = APIRouter(prefix="/graph", tags=["graph"], dependencies=[Depends(require_auth)])


@router.get("", response_model=GraphOut)
async def get_graph(
    min_weight: int = Query(1, ge=1),
    db: AsyncSession = Depends(get_db),
) -> GraphOut:
    result = await api_q.get_graph(db, min_weight=min_weight)
    return GraphOut(
        nodes=[GraphNode(**n) for n in result["nodes"]],
        edges=[GraphEdge(**e) for e in result["edges"]],
    )
