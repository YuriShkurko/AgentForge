from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.adapters.notifications import build_notification_payload
from app.models import NormalizedRecord, NotificationPreview


def _preview_out(preview: NotificationPreview) -> dict:
    payload = preview.payload
    action = preview.record.action
    return {
        "id": preview.id,
        "record_id": preview.normalized_record_id,
        "title": payload["title"],
        "score": payload["score"],
        "label": payload["label"],
        "recommendation": payload["recommendation"],
        "summary": payload["summary"],
        "drivers": payload["drivers"],
        "risks": payload["risks"],
        "available_actions": payload["available_actions"],
        "delivery_channel": preview.delivery_channel,
        "delivery_status": preview.delivery_status,
        "action": action,
        "created_at": preview.created_at,
        "updated_at": preview.updated_at,
    }


async def create_notification_previews(db: AsyncSession) -> dict:
    result = await db.execute(
        select(NormalizedRecord).options(
            selectinload(NormalizedRecord.scores),
            selectinload(NormalizedRecord.notification_preview),
        )
    )
    records = result.scalars().all()

    written = 0
    for record in records:
        if not record.scores:
            continue
        latest_score = record.scores[0]
        payload = build_notification_payload(record, latest_score)

        if record.notification_preview:
            record.notification_preview.payload = payload
            record.notification_preview.delivery_status = "previewed"
        else:
            db.add(
                NotificationPreview(
                    normalized_record_id=record.id,
                    delivery_channel="preview",
                    delivery_status="previewed",
                    payload=payload,
                )
            )
        written += 1

    await db.commit()
    return {"previews_written": written}


async def list_notification_previews(db: AsyncSession, limit: int = 50) -> list[dict]:
    result = await db.execute(
        select(NotificationPreview)
        .options(
            selectinload(NotificationPreview.record).selectinload(NormalizedRecord.action),
        )
        .order_by(NotificationPreview.updated_at.desc())
        .limit(limit)
    )
    return [_preview_out(preview) for preview in result.scalars().all()]
