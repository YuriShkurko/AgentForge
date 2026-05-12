import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import ActivityEvent, Project, Task
from app.schemas import ProjectCreate, TaskCreate, TaskUpdate

VALID_STATUSES = {"todo", "in_progress", "blocked", "done"}
VALID_PRIORITIES = {"low", "medium", "high"}

SAMPLE_PROJECTS = [
    {
        "name": "Launch Readiness",
        "description": "Coordinate local demo polish, docs, and validation before launch.",
        "owner": "Maya",
        "tasks": [
            {"title": "Finalize README walkthrough", "status": "done", "priority": "high", "owner": "Maya", "due_date": date(2026, 5, 15)},
            {"title": "Review generated app validation", "status": "in_progress", "priority": "high", "owner": "Eli", "due_date": date(2026, 5, 16)},
            {"title": "Collect follow-up demo notes", "status": "todo", "priority": "medium", "owner": "Sam", "due_date": date(2026, 5, 20)},
        ],
    },
    {
        "name": "Customer Pilot Workspace",
        "description": "Track pilot onboarding tasks and risk notes for a local-first app trial.",
        "owner": "Nora",
        "tasks": [
            {"title": "Prepare pilot checklist", "status": "in_progress", "priority": "medium", "owner": "Nora", "due_date": date(2026, 5, 18)},
            {"title": "Resolve data import question", "status": "blocked", "priority": "high", "owner": "Dev", "due_date": date(2026, 5, 17)},
        ],
    },
]


def _validate_status(value: str) -> str:
    if value not in VALID_STATUSES:
        raise ValueError(f"status must be one of {', '.join(sorted(VALID_STATUSES))}")
    return value


def _validate_priority(value: str) -> str:
    if value not in VALID_PRIORITIES:
        raise ValueError(f"priority must be one of {', '.join(sorted(VALID_PRIORITIES))}")
    return value


async def seed_sample_data(db: AsyncSession) -> dict:
    existing = await db.scalar(select(Project).limit(1))
    if existing:
        return {"created_projects": 0, "created_tasks": 0}

    created_tasks = 0
    for item in SAMPLE_PROJECTS:
        project = Project(name=item["name"], description=item["description"], owner=item["owner"])
        db.add(project)
        await db.flush()
        db.add(ActivityEvent(project_id=project.id, event_type="project_seeded", body=f"Seeded {project.name}", actor="agentforge"))
        for task_item in item["tasks"]:
            task = Task(project_id=project.id, **task_item)
            db.add(task)
            await db.flush()
            db.add(ActivityEvent(project_id=project.id, task_id=task.id, event_type="task_seeded", body=f"Seeded task: {task.title}", actor="agentforge"))
            created_tasks += 1
    await db.commit()
    return {"created_projects": len(SAMPLE_PROJECTS), "created_tasks": created_tasks}


async def list_projects(db: AsyncSession) -> list[Project]:
    result = await db.execute(select(Project).options(selectinload(Project.tasks)).order_by(Project.created_at))
    return list(result.scalars().all())


async def list_tasks(db: AsyncSession, *, project_id: uuid.UUID | None = None, status: str | None = None) -> list[Task]:
    stmt = select(Task).order_by(Task.priority.desc(), Task.created_at)
    if project_id:
        stmt = stmt.where(Task.project_id == project_id)
    if status:
        stmt = stmt.where(Task.status == status)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_project(db: AsyncSession, payload: ProjectCreate) -> Project:
    project = Project(name=payload.name, description=payload.description, owner=payload.owner)
    db.add(project)
    await db.flush()
    db.add(ActivityEvent(project_id=project.id, event_type="project_created", body=f"Created project {project.name}", actor=payload.owner))
    await db.commit()
    await db.refresh(project)
    return project


async def create_task(db: AsyncSession, payload: TaskCreate) -> Task:
    _validate_status(payload.status)
    _validate_priority(payload.priority)
    task = Task(**payload.model_dump())
    db.add(task)
    await db.flush()
    db.add(ActivityEvent(project_id=task.project_id, task_id=task.id, event_type="task_created", body=f"Created task {task.title}", actor=task.owner))
    await db.commit()
    await db.refresh(task)
    return task


async def update_task(db: AsyncSession, task_id: uuid.UUID, payload: TaskUpdate) -> Task:
    task = await db.get(Task, task_id)
    if task is None:
        raise LookupError("task not found")
    updates = payload.model_dump(exclude_unset=True)
    if "status" in updates and updates["status"] is not None:
        _validate_status(updates["status"])
    if "priority" in updates and updates["priority"] is not None:
        _validate_priority(updates["priority"])
    for key, value in updates.items():
        setattr(task, key, value)
    db.add(ActivityEvent(project_id=task.project_id, task_id=task.id, event_type="task_updated", body=f"Updated task {task.title}", actor=task.owner))
    await db.commit()
    await db.refresh(task)
    return task


async def add_note(db: AsyncSession, project_id: uuid.UUID, body: str, *, task_id: uuid.UUID | None = None, actor: str = "operator") -> ActivityEvent:
    project = await db.get(Project, project_id)
    if project is None:
        raise LookupError("project not found")
    if task_id and await db.get(Task, task_id) is None:
        raise LookupError("task not found")
    event = ActivityEvent(project_id=project_id, task_id=task_id, event_type="note_added", body=body, actor=actor)
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def list_activity(db: AsyncSession, *, limit: int = 20) -> list[ActivityEvent]:
    result = await db.execute(select(ActivityEvent).order_by(ActivityEvent.created_at.desc()).limit(limit))
    return list(result.scalars().all())
