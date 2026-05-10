import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    WorkspaceReorderOut,
    WorkspaceReorderRequest,
    WorkspaceWidgetCreate,
    WorkspaceWidgetCreateOut,
    WorkspaceWidgetDeleteOut,
    WorkspaceWidgetsListOut,
)
from app.services.workspace import WorkspaceError, create_widget, list_widgets, remove_widget, reorder_widgets

router = APIRouter(prefix="/workspace", tags=["workspace"])


@router.get("/widgets", response_model=WorkspaceWidgetsListOut)
async def get_workspace_widgets(db: AsyncSession = Depends(get_db)):
    return {"widgets": await list_widgets(db)}


@router.post("/widgets", response_model=WorkspaceWidgetCreateOut)
async def post_workspace_widget(
    body: WorkspaceWidgetCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        widget = await create_widget(
            db,
            widget_type=body.widget_type,
            title=body.title,
            source_tool=body.source_tool,
            data=body.data,
            metadata=body.metadata,
        )
    except WorkspaceError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"error_code": exc.code, "message": exc.message})
    return {"widget": widget}


@router.delete("/widgets/{widget_id}", response_model=WorkspaceWidgetDeleteOut)
async def delete_workspace_widget(
    widget_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await remove_widget(db, widget_id)
    except WorkspaceError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"error_code": exc.code, "message": exc.message})


@router.post("/widgets/reorder", response_model=WorkspaceReorderOut)
async def post_workspace_reorder(
    body: WorkspaceReorderRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await reorder_widgets(db, body.widget_ids)
    except WorkspaceError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"error_code": exc.code, "message": exc.message})
