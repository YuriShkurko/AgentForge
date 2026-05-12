import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import WorkspaceWidget

ALLOWED_WIDGETS = {
    "summarize_project": {"project_summary", "summary_card"},
    "list_tasks": {"task_list", "summary_card"},
    "pin_project_summary": {"project_summary", "summary_card"},
    "pin_task_list": {"task_list", "summary_card"},
}


class WorkspaceError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _serialize(widget: WorkspaceWidget) -> dict[str, Any]:
    return {
        "id": widget.id,
        "widget_type": widget.widget_type,
        "title": widget.title,
        "source_tool": widget.source_tool,
        "data": widget.data,
        "position": widget.position,
        "metadata": widget.widget_metadata,
        "created_at": widget.created_at,
        "updated_at": widget.updated_at,
    }


async def list_widgets(db: AsyncSession) -> list[dict[str, Any]]:
    result = await db.execute(select(WorkspaceWidget).order_by(WorkspaceWidget.position, WorkspaceWidget.created_at))
    return [_serialize(widget) for widget in result.scalars().all()]


async def create_widget(db: AsyncSession, *, widget_type: str, title: str, source_tool: str, data: dict[str, Any], metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    allowed = ALLOWED_WIDGETS.get(source_tool)
    if allowed is not None and widget_type not in allowed:
        raise WorkspaceError("incompatible_widget", f"{source_tool} cannot create {widget_type}")
    if not data:
        raise WorkspaceError("empty_widget_data", "workspace widget data must not be empty")
    position = len(await list_widgets(db))
    widget = WorkspaceWidget(widget_type=widget_type, title=title, source_tool=source_tool, data=data, widget_metadata=metadata, position=position)
    db.add(widget)
    await db.commit()
    await db.refresh(widget)
    return _serialize(widget)


async def remove_widget(db: AsyncSession, widget_id: uuid.UUID) -> dict[str, Any]:
    widget = await db.get(WorkspaceWidget, widget_id)
    if widget is None:
        raise WorkspaceError("not_found", "workspace widget not found")
    await db.delete(widget)
    await db.commit()
    return {"removed": True, "widget_id": widget_id}
