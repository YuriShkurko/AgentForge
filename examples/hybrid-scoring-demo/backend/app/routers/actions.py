import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import ActionHistoryOut, ActionRequest, ActionResult
from app.services.actions import list_action_history, list_record_action_history, record_action

router = APIRouter(prefix="/records", tags=["actions"])
history_router = APIRouter(prefix="/actions", tags=["actions"])


@router.post("/{record_id}/action", response_model=ActionResult)
async def post_action(
    record_id: uuid.UUID,
    body: ActionRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await record_action(record_id, body.action_type, db)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return result


@router.get("/{record_id}/actions", response_model=ActionHistoryOut)
async def get_record_action_history(
    record_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    try:
        events = await list_record_action_history(record_id, db)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"events": events}


@history_router.get("/history", response_model=ActionHistoryOut)
async def get_action_history(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    return {"events": await list_action_history(db, limit=limit)}
