from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

TaskStatus = str
TaskPriority = str


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str = ""
    owner: str = "team"


class TaskCreate(BaseModel):
    project_id: UUID
    title: str = Field(min_length=1, max_length=220)
    description: str = ""
    status: TaskStatus = "todo"
    priority: TaskPriority = "medium"
    owner: str = "unassigned"
    due_date: date | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    owner: str | None = None
    due_date: date | None = None


class NoteCreate(BaseModel):
    body: str = Field(min_length=1)
    task_id: UUID | None = None
    actor: str = "operator"


class ProjectOut(BaseModel):
    id: UUID
    name: str
    description: str
    owner: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskOut(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    description: str
    status: str
    priority: str
    owner: str
    due_date: date | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ActivityOut(BaseModel):
    id: UUID
    project_id: UUID
    task_id: UUID | None
    event_type: str
    body: str
    actor: str
    event_metadata: dict[str, Any] | None
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkspaceWidgetIn(BaseModel):
    widget_type: str
    title: str
    source_tool: str
    data: dict[str, Any]
    metadata: dict[str, Any] | None = None


class WorkspaceWidgetOut(BaseModel):
    id: UUID
    widget_type: str
    title: str
    source_tool: str
    data: Any
    position: int
    metadata: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime


class AgentChatIn(BaseModel):
    message: str
    conversation_id: UUID | None = None


class AgentMessageOut(BaseModel):
    id: UUID
    role: str
    content: str
    metadata: dict[str, Any] | None
    created_at: datetime


class AgentToolEventOut(BaseModel):
    tool_name: str
    arguments: dict[str, Any]
    ok: bool
    result: dict[str, Any] | None = None
    error: str | None = None
    status: str = "succeeded"


class AgentChatOut(BaseModel):
    conversation_id: UUID
    assistant_message: AgentMessageOut
    messages: list[AgentMessageOut]
    tool_events: list[AgentToolEventOut]
