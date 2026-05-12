import uuid
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import NoteCreate, TaskUpdate
from app.services.projects import add_note, list_projects, list_tasks, update_task
from app.services.workspace import create_widget

ToolHandler = Callable[[dict[str, Any], AsyncSession], Awaitable[dict[str, Any]]]


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    handler: ToolHandler


async def _list_tasks(args: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
    tasks = await list_tasks(db, status=args.get("status"))
    return {
        "tasks": [
            {
                "id": str(task.id),
                "project_id": str(task.project_id),
                "title": task.title,
                "status": task.status,
                "priority": task.priority,
                "owner": task.owner,
                "due_date": task.due_date.isoformat() if task.due_date else None,
            }
            for task in tasks
        ]
    }


async def _summarize_project(args: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
    projects = await list_projects(db)
    if not projects:
        return {"summary": "No projects yet.", "projects": []}
    summaries = []
    for project in projects:
        counts: dict[str, int] = {}
        for task in project.tasks:
            counts[task.status] = counts.get(task.status, 0) + 1
        summaries.append({"id": str(project.id), "name": project.name, "owner": project.owner, "task_counts": counts})
    return {"summary": f"{len(projects)} active project workspace(s).", "projects": summaries}


async def _update_task_status(args: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
    task_id = uuid.UUID(str(args["task_id"]))
    task = await update_task(db, task_id, TaskUpdate(status=str(args["status"])))
    return {"task": {"id": str(task.id), "title": task.title, "status": task.status, "priority": task.priority}}


async def _add_note(args: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
    event = await add_note(db, uuid.UUID(str(args["project_id"])), str(args["body"]), actor="agent")
    return {"event": {"id": str(event.id), "body": event.body, "event_type": event.event_type}}


async def _pin_project_summary(args: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
    summary = await _summarize_project({}, db)
    widget = await create_widget(db, widget_type="project_summary", title="Project summary", source_tool="summarize_project", data=summary)
    return {"pinned": True, "widget": widget}


async def _pin_task_list(args: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
    tasks = await _list_tasks({}, db)
    widget = await create_widget(db, widget_type="task_list", title="Task list", source_tool="list_tasks", data=tasks)
    return {"pinned": True, "widget": widget}


TOOLS: dict[str, ToolDefinition] = {
    "list_tasks": ToolDefinition("list_tasks", "List project workspace tasks.", _list_tasks),
    "summarize_project": ToolDefinition("summarize_project", "Summarize project task status.", _summarize_project),
    "update_task_status": ToolDefinition("update_task_status", "Update a task status.", _update_task_status),
    "add_note": ToolDefinition("add_note", "Add a project note/activity event.", _add_note),
    "pin_project_summary": ToolDefinition("pin_project_summary", "Pin project summary widget.", _pin_project_summary),
    "pin_task_list": ToolDefinition("pin_task_list", "Pin task list widget.", _pin_task_list),
}


async def execute_tool(name: str, arguments: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
    tool = TOOLS.get(name)
    if tool is None:
        raise ValueError(f"unknown tool: {name}")
    return await tool.handler(arguments, db)
