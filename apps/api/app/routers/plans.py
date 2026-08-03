from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.entities import Plan
from app.schemas import PlanOut

router = APIRouter(prefix="/api/v1", tags=["plans"])


@router.get("/plans", response_model=list[PlanOut])
async def list_plans(db: AsyncSession = Depends(get_db)) -> list[Plan]:
    result = await db.execute(
        select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.sort_order.asc(), Plan.price_rub.asc())
    )
    return list(result.scalars().all())
