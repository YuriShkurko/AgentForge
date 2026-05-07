from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ProviderRun
from app.schemas import RunsListOut

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("", response_model=RunsListOut)
async def list_runs(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ProviderRun).order_by(ProviderRun.started_at.desc()).limit(limit)
    )
    runs = result.scalars().all()
    return {"runs": runs}
