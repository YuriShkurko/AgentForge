"""Notification/action loop stub — records decisions, no external delivery."""
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import NormalizedRecord, RecordAction, RecordActionEvent

_ACTION_TO_STATUS = {
    "accept": "accepted",
    "skip": "skipped",
    "save": "saved",
}

VALID_ACTION_TYPES = set(_ACTION_TO_STATUS.keys())


async def record_action(record_id: uuid.UUID, action_type: str, db: AsyncSession) -> dict:
    if action_type not in VALID_ACTION_TYPES:
        raise ValueError(f"action_type must be one of {sorted(VALID_ACTION_TYPES)}")

    record = await db.get(NormalizedRecord, record_id)
    if record is None:
        raise LookupError(f"record {record_id} not found")

    existing = await db.scalar(
        select(RecordAction).where(RecordAction.normalized_record_id == record_id)
    )

    status = _ACTION_TO_STATUS[action_type]

    if existing:
        existing.action_type = action_type
        existing.status = status
        action = existing
    else:
        action = RecordAction(
            normalized_record_id=record_id,
            action_type=action_type,
            status=status,
        )
        db.add(action)

    event = RecordActionEvent(
        normalized_record_id=record_id,
        action_type=action_type,
        status=status,
        event_metadata={"source": "api"},
        created_at=datetime.now(UTC),
    )
    db.add(event)
    await db.flush()

    await db.commit()
    return {"ok": True, "record_id": record_id, "action_type": action_type, "status": status}


async def list_action_history(db: AsyncSession, limit: int = 50) -> list[dict]:
    result = await db.execute(
        select(RecordActionEvent)
        .order_by(RecordActionEvent.created_at.desc())
        .limit(limit)
    )
    return [
        {
            "id": event.id,
            "record_id": event.normalized_record_id,
            "action_type": event.action_type,
            "status": event.status,
            "created_at": event.created_at,
        }
        for event in result.scalars().all()
    ]


async def list_record_action_history(record_id: uuid.UUID, db: AsyncSession) -> list[dict]:
    record = await db.get(NormalizedRecord, record_id)
    if record is None:
        raise LookupError(f"record {record_id} not found")

    result = await db.execute(
        select(RecordActionEvent)
        .where(RecordActionEvent.normalized_record_id == record_id)
        .order_by(RecordActionEvent.created_at.desc())
    )
    return [
        {
            "id": event.id,
            "record_id": event.normalized_record_id,
            "action_type": event.action_type,
            "status": event.status,
            "created_at": event.created_at,
        }
        for event in result.scalars().all()
    ]
