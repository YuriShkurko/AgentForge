import uuid
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import NormalizedRecord, ProviderRun
from app.providers.fixture.provider import FixtureRecordProvider
from app.services.actions import list_action_history, record_action
from app.services.ingest import run_ingest
from app.services.notifications import create_notification_previews
from app.services.score import run_score

ToolHandler = Callable[[dict[str, Any], AsyncSession], Awaitable[dict[str, Any]]]


@dataclass(frozen=True)
class ToolArgument:
    type_name: str
    required: bool = False
    default: Any = None
    choices: tuple[str, ...] = ()


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, ToolArgument]
    handler: ToolHandler


class ToolExecutionError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _validate_tool_arguments(tool: ToolDefinition, arguments: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(arguments, dict):
        raise ToolExecutionError("invalid_arguments", "tool arguments must be an object")

    allowed = set(tool.input_schema)
    unknown = set(arguments) - allowed
    if unknown:
        raise ToolExecutionError("invalid_arguments", f"unknown argument(s): {', '.join(sorted(unknown))}")

    validated: dict[str, Any] = {}
    for name, spec in tool.input_schema.items():
        if name not in arguments:
            if spec.required:
                raise ToolExecutionError("invalid_arguments", f"missing required argument: {name}")
            if spec.default is not None:
                validated[name] = spec.default
            continue

        value = arguments[name]
        if spec.type_name == "boolean":
            if not isinstance(value, bool):
                raise ToolExecutionError("invalid_arguments", f"{name} must be a boolean")
        elif spec.type_name == "integer":
            if not isinstance(value, int) or isinstance(value, bool):
                raise ToolExecutionError("invalid_arguments", f"{name} must be an integer")
        elif spec.type_name == "uuid":
            try:
                value = str(uuid.UUID(str(value)))
            except ValueError as exc:
                raise ToolExecutionError("invalid_arguments", f"{name} must be a UUID") from exc
        elif spec.type_name == "string":
            if not isinstance(value, str):
                raise ToolExecutionError("invalid_arguments", f"{name} must be a string")
        else:
            raise ToolExecutionError("invalid_schema", f"unsupported schema type: {spec.type_name}")

        if spec.choices and value not in spec.choices:
            raise ToolExecutionError("invalid_arguments", f"{name} must be one of {', '.join(spec.choices)}")

        validated[name] = value

    return validated


async def _run_ingest(args: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
    result = await run_ingest(FixtureRecordProvider(), db)
    return {
        "run_id": str(result["run_id"]),
        "raw_records_inserted": result["raw_records_inserted"],
        "normalized_inserted": result["normalized_inserted"],
    }


async def _score_records(args: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
    rescore = bool(args.get("rescore", False))
    return await run_score(db, rescore=rescore)


async def _get_run_history(args: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
    limit = int(args.get("limit", 5))
    result = await db.execute(select(ProviderRun).order_by(ProviderRun.started_at.desc()).limit(limit))
    runs = result.scalars().all()
    return {
        "runs": [
            {
                "id": str(run.id),
                "provider_name": run.provider_name,
                "status": run.status,
                "stats": run.stats,
            }
            for run in runs
        ]
    }


async def _get_scored_records(args: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
    limit = int(args.get("limit", 3))
    result = await db.execute(
        select(NormalizedRecord).options(selectinload(NormalizedRecord.scores))
    )
    records = []
    for record in result.scalars().all():
        if not record.scores:
            continue
        latest = record.scores[0]
        records.append(
            {
                "id": str(record.id),
                "title": record.title,
                "fit": latest.fit,
                "label": latest.label,
                "recommendation": latest.recommendation,
            }
        )
    records.sort(key=lambda row: row["fit"], reverse=True)
    return {"records": records[:limit]}


async def _create_notification_preview(args: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
    return await create_notification_previews(db)


async def _perform_triage_action(args: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
    record_id = args.get("record_id")
    action_type = args.get("action_type")
    if not record_id or not action_type:
        raise ValueError("record_id and action_type are required")
    result = await record_action(uuid.UUID(str(record_id)), str(action_type), db)
    return {
        "ok": result["ok"],
        "record_id": str(result["record_id"]),
        "action_type": result["action_type"],
        "status": result["status"],
    }


async def _list_action_history(args: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
    limit = int(args.get("limit", 5))
    events = await list_action_history(db, limit=limit)
    return {
        "events": [
            {
                "id": str(event["id"]),
                "record_id": str(event["record_id"]),
                "action_type": event["action_type"],
                "status": event["status"],
                "created_at": event["created_at"].isoformat(),
            }
            for event in events
        ]
    }


TOOLS: dict[str, ToolDefinition] = {
    "run_ingest": ToolDefinition(
        name="run_ingest",
        description="Ingest deterministic fixture records.",
        input_schema={},
        handler=_run_ingest,
    ),
    "score_records": ToolDefinition(
        name="score_records",
        description="Score normalized records with deterministic heuristics.",
        input_schema={"rescore": ToolArgument("boolean", default=False)},
        handler=_score_records,
    ),
    "get_run_history": ToolDefinition(
        name="get_run_history",
        description="Return recent provider run history.",
        input_schema={"limit": ToolArgument("integer", default=5)},
        handler=_get_run_history,
    ),
    "get_scored_records": ToolDefinition(
        name="get_scored_records",
        description="Return top scored records.",
        input_schema={"limit": ToolArgument("integer", default=3)},
        handler=_get_scored_records,
    ),
    "create_notification_preview": ToolDefinition(
        name="create_notification_preview",
        description="Create preview-only notification payloads.",
        input_schema={},
        handler=_create_notification_preview,
    ),
    "perform_triage_action": ToolDefinition(
        name="perform_triage_action",
        description="Record a triage action for a scored record.",
        input_schema={
            "record_id": ToolArgument("uuid", required=True),
            "action_type": ToolArgument("string", required=True, choices=("accept", "skip", "save")),
        },
        handler=_perform_triage_action,
    ),
    "list_action_history": ToolDefinition(
        name="list_action_history",
        description="List recent triage action history.",
        input_schema={"limit": ToolArgument("integer", default=5)},
        handler=_list_action_history,
    ),
}


async def execute_tool(name: str, arguments: dict[str, Any], db: AsyncSession) -> dict[str, Any]:
    tool = TOOLS.get(name)
    if tool is None:
        raise ToolExecutionError("unknown_tool", f"unknown tool: {name}")
    validated = _validate_tool_arguments(tool, arguments)
    return await tool.handler(validated, db)
