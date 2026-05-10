import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import WorkspaceWidget


WIDGET_TYPES = {
    "summary_card",
    "ranking_list",
    "score_table",
    "run_history_list",
    "notification_preview_card",
    "action_history_list",
}

TOOL_WIDGET_COMPATIBILITY: dict[str, set[str]] = {
    "get_scored_records": {"ranking_list", "score_table"},
    "get_run_history": {"run_history_list", "summary_card"},
    "create_notification_preview": {"notification_preview_card", "summary_card"},
    "list_action_history": {"action_history_list", "summary_card"},
    "score_records": {"summary_card"},
    "run_ingest": {"summary_card"},
}


class WorkspaceError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def _widget_out(widget: WorkspaceWidget) -> dict[str, Any]:
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


def _validate_widget_payload(widget_type: str, source_tool: str, data: Any) -> None:
    if widget_type not in WIDGET_TYPES:
        raise WorkspaceError("unknown_widget_type", f"unknown widget_type: {widget_type}")

    allowed = TOOL_WIDGET_COMPATIBILITY.get(source_tool)
    if not allowed or widget_type not in allowed:
        allowed_list = ", ".join(sorted(allowed or [])) or "none"
        raise WorkspaceError(
            "incompatible_widget",
            f"{source_tool} cannot be rendered as {widget_type}; allowed widget types: {allowed_list}",
        )

    if data is None:
        raise WorkspaceError("empty_widget_data", "widget data must not be empty")
    if isinstance(data, dict) and len(data) == 0:
        raise WorkspaceError("empty_widget_data", "widget data must not be empty")
    if isinstance(data, list) and len(data) == 0:
        raise WorkspaceError("empty_widget_data", "widget data must not be empty")


async def list_widgets(db: AsyncSession) -> list[dict[str, Any]]:
    result = await db.execute(select(WorkspaceWidget).order_by(WorkspaceWidget.position, WorkspaceWidget.created_at))
    return [_widget_out(widget) for widget in result.scalars().all()]


async def create_widget(
    db: AsyncSession,
    *,
    widget_type: str,
    title: str,
    source_tool: str,
    data: Any,
    metadata: dict | None = None,
) -> dict[str, Any]:
    _validate_widget_payload(widget_type, source_tool, data)

    max_position = await db.scalar(select(func.max(WorkspaceWidget.position)))
    widget = WorkspaceWidget(
        widget_type=widget_type,
        title=title.strip() or widget_type.replace("_", " ").title(),
        source_tool=source_tool,
        data=data,
        position=0 if max_position is None else int(max_position) + 1,
        widget_metadata=metadata,
    )
    db.add(widget)
    await db.commit()
    await db.refresh(widget)
    return _widget_out(widget)


async def remove_widget(db: AsyncSession, widget_id: uuid.UUID) -> dict[str, Any]:
    widget = await db.get(WorkspaceWidget, widget_id)
    if widget is None:
        raise WorkspaceError("widget_not_found", f"workspace widget not found: {widget_id}", status_code=404)

    await db.delete(widget)
    await db.commit()
    await _compact_positions(db)
    return {"removed": True, "widget_id": widget_id}


async def reorder_widgets(db: AsyncSession, widget_ids: list[uuid.UUID]) -> dict[str, Any]:
    if len(widget_ids) == 0:
        raise WorkspaceError("invalid_reorder", "widget_ids must not be empty")
    if len(set(widget_ids)) != len(widget_ids):
        raise WorkspaceError("invalid_reorder", "widget_ids must not contain duplicates")

    result = await db.execute(select(WorkspaceWidget))
    widgets = result.scalars().all()
    by_id = {widget.id: widget for widget in widgets}
    current_ids = set(by_id)
    requested_ids = set(widget_ids)

    if requested_ids != current_ids:
        missing = sorted(str(item) for item in current_ids - requested_ids)
        unknown = sorted(str(item) for item in requested_ids - current_ids)
        details = []
        if missing:
            details.append(f"missing widget ids: {', '.join(missing)}")
        if unknown:
            details.append(f"unknown widget ids: {', '.join(unknown)}")
        raise WorkspaceError("invalid_reorder", "; ".join(details))

    for position, widget_id in enumerate(widget_ids):
        by_id[widget_id].position = position

    await db.commit()
    return {"reordered": True, "widget_ids": widget_ids, "widgets": await list_widgets(db)}


async def _compact_positions(db: AsyncSession) -> None:
    result = await db.execute(select(WorkspaceWidget).order_by(WorkspaceWidget.position, WorkspaceWidget.created_at))
    for position, widget in enumerate(result.scalars().all()):
        widget.position = position
    await db.commit()
