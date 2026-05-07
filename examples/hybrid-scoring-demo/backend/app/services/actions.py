"""Notification/action loop stub — records decisions, no external delivery."""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import NormalizedRecord, RecordAction

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

    await db.commit()
    return {"ok": True, "record_id": record_id, "action_type": action_type, "status": status}
