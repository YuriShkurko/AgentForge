import uuid
from datetime import datetime

from pydantic import BaseModel
from typing import Any


# --- Provider Run ---

class RunOut(BaseModel):
    id: uuid.UUID
    provider_name: str
    started_at: datetime
    finished_at: datetime | None
    status: str
    stats: dict | None
    error: str | None

    model_config = {"from_attributes": True}


class RunsListOut(BaseModel):
    runs: list[RunOut]


# --- Ingest ---

class IngestOut(BaseModel):
    run_id: uuid.UUID
    raw_records_inserted: int
    normalized_inserted: int


# --- Score ---

class ScoreOut(BaseModel):
    scores_written: int
    rescore: bool


# --- Records ---

class RecordOut(BaseModel):
    id: uuid.UUID
    external_id: str
    source: str
    title: str
    category: str
    value: float
    ingested_at: datetime

    model_config = {"from_attributes": True}


class RecordsListOut(BaseModel):
    records: list[RecordOut]


# --- Scored Records ---

class ExplanationOut(BaseModel):
    fit_score: float
    summary: str
    drivers: list[str]
    risks: list[str]


class ScoreDetailOut(BaseModel):
    fit: float
    label: str
    recommendation: str
    explanation: ExplanationOut

    model_config = {"from_attributes": True}


class ActionOut(BaseModel):
    action_type: str
    status: str
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ScoredRecordOut(BaseModel):
    record: RecordOut
    score: ScoreDetailOut
    action: ActionOut | None


class ScoredRecordsListOut(BaseModel):
    records: list[ScoredRecordOut]


# --- Action ---

class ActionRequest(BaseModel):
    action_type: str  # accept / skip / save


class ActionResult(BaseModel):
    ok: bool
    record_id: uuid.UUID
    action_type: str
    status: str


class ActionEventOut(BaseModel):
    id: uuid.UUID
    record_id: uuid.UUID
    action_type: str
    status: str
    created_at: datetime


class ActionHistoryOut(BaseModel):
    events: list[ActionEventOut]


# --- Notification Preview ---

class NotificationPreviewCreateOut(BaseModel):
    previews_written: int


class NotificationPreviewOut(BaseModel):
    id: uuid.UUID
    record_id: uuid.UUID
    title: str
    score: float
    label: str
    recommendation: str
    summary: str
    drivers: list[str]
    risks: list[str]
    available_actions: list[str]
    delivery_channel: str
    delivery_status: str
    action: ActionOut | None
    created_at: datetime
    updated_at: datetime


class NotificationPreviewsListOut(BaseModel):
    previews: list[NotificationPreviewOut]


# --- Agent Runtime ---

class AgentChatRequest(BaseModel):
    message: str
    conversation_id: uuid.UUID | None = None


class AgentMessageOut(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    metadata: dict | None = None
    created_at: datetime


class AgentToolEventOut(BaseModel):
    tool_name: str
    arguments: dict
    ok: bool
    result: dict | None = None
    error: str | None = None
    error_code: str | None = None


class AgentChatResponse(BaseModel):
    conversation_id: uuid.UUID
    assistant_message: AgentMessageOut
    messages: list[AgentMessageOut]
    tool_events: list[AgentToolEventOut]


class AgentConversationOut(BaseModel):
    conversation_id: uuid.UUID
    messages: list[AgentMessageOut]


# --- Workspace ---

class WorkspaceWidgetOut(BaseModel):
    id: uuid.UUID
    widget_type: str
    title: str
    source_tool: str
    data: Any
    position: int
    metadata: dict | None = None
    created_at: datetime
    updated_at: datetime


class WorkspaceWidgetsListOut(BaseModel):
    widgets: list[WorkspaceWidgetOut]


class WorkspaceWidgetCreate(BaseModel):
    widget_type: str
    title: str
    source_tool: str
    data: Any
    metadata: dict | None = None


class WorkspaceWidgetCreateOut(BaseModel):
    widget: WorkspaceWidgetOut


class WorkspaceWidgetDeleteOut(BaseModel):
    removed: bool
    widget_id: uuid.UUID


class WorkspaceReorderRequest(BaseModel):
    widget_ids: list[uuid.UUID]


class WorkspaceReorderOut(BaseModel):
    reordered: bool
    widget_ids: list[uuid.UUID]
    widgets: list[WorkspaceWidgetOut]
