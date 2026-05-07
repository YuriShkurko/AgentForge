import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import ActionRequest, ActionResult
from app.services.actions import record_action

router = APIRouter(prefix="/records", tags=["actions"])


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
