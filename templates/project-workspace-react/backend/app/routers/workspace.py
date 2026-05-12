import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import WorkspaceWidgetIn, WorkspaceWidgetOut
from app.services.workspace import WorkspaceError, create_widget, list_widgets, remove_widget

router = APIRouter(prefix="/workspace", tags=["workspace"])


@router.get("/widgets", response_model=list[WorkspaceWidgetOut])
async def widgets(db: AsyncSession = Depends(get_db)):
    return await list_widgets(db)


@router.post("/widgets", response_model=WorkspaceWidgetOut)
async def create_workspace_widget(payload: WorkspaceWidgetIn, db: AsyncSession = Depends(get_db)):
    try:
        return await create_widget(db, widget_type=payload.widget_type, title=payload.title, source_tool=payload.source_tool, data=payload.data, metadata=payload.metadata)
    except WorkspaceError as exc:
        raise HTTPException(status_code=422, detail={"code": exc.code, "message": exc.message}) from exc


@router.delete("/widgets/{widget_id}")
async def delete_workspace_widget(widget_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    try:
        return await remove_widget(db, widget_id)
    except WorkspaceError as exc:
        raise HTTPException(status_code=404, detail={"code": exc.code, "message": exc.message}) from exc
