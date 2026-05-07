import uuid
from datetime import datetime

from pydantic import BaseModel


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
