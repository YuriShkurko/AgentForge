import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import ActivityOut, NoteCreate, ProjectCreate, ProjectOut, TaskCreate, TaskOut, TaskUpdate
from app.services.projects import add_note, create_project, create_task, list_activity, list_projects, list_tasks, seed_sample_data, update_task

router = APIRouter(tags=["projects"])


@router.post("/seed")
async def seed(db: AsyncSession = Depends(get_db)):
    return await seed_sample_data(db)


@router.get("/projects", response_model=list[ProjectOut])
async def projects(db: AsyncSession = Depends(get_db)):
    return await list_projects(db)


@router.post("/projects", response_model=ProjectOut)
async def create_project_route(payload: ProjectCreate, db: AsyncSession = Depends(get_db)):
    return await create_project(db, payload)


@router.get("/tasks", response_model=list[TaskOut])
async def tasks(project_id: uuid.UUID | None = None, status: str | None = None, db: AsyncSession = Depends(get_db)):
    return await list_tasks(db, project_id=project_id, status=status)


@router.post("/tasks", response_model=TaskOut)
async def create_task_route(payload: TaskCreate, db: AsyncSession = Depends(get_db)):
    try:
        return await create_task(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch("/tasks/{task_id}", response_model=TaskOut)
async def update_task_route(task_id: uuid.UUID, payload: TaskUpdate, db: AsyncSession = Depends(get_db)):
    try:
        return await update_task(db, task_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/projects/{project_id}/notes", response_model=ActivityOut)
async def add_note_route(project_id: uuid.UUID, payload: NoteCreate, db: AsyncSession = Depends(get_db)):
    try:
        return await add_note(db, project_id, payload.body, task_id=payload.task_id, actor=payload.actor)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/activity", response_model=list[ActivityOut])
async def activity(limit: int = 20, db: AsyncSession = Depends(get_db)):
    return await list_activity(db, limit=limit)
