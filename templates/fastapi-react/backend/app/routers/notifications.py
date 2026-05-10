from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import NotificationPreviewCreateOut, NotificationPreviewsListOut
from app.services.notifications import create_notification_previews, list_notification_previews

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("/previews", response_model=NotificationPreviewCreateOut)
async def post_notification_previews(db: AsyncSession = Depends(get_db)):
    return await create_notification_previews(db)


@router.get("/previews", response_model=NotificationPreviewsListOut)
async def get_notification_previews(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    return {"previews": await list_notification_previews(db, limit=limit)}
