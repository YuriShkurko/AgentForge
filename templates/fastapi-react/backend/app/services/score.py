from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.normalize import NormalizedRecordDTO
from app.adapters.scoring import score
from app.models import NormalizedRecord, RecordScore


async def run_score(db: AsyncSession, rescore: bool = False) -> dict:
    result = await db.execute(select(NormalizedRecord))
    records = result.scalars().all()

    written = 0
    for record in records:
        if rescore:
            existing = await db.execute(
                select(RecordScore).where(RecordScore.normalized_record_id == record.id)
            )
            for row in existing.scalars().all():
                await db.delete(row)

        dto = NormalizedRecordDTO(
            external_id=record.external_id,
            source=record.source,
            title=record.title,
            category=record.category,
            value=record.value,
            raw_payload=record.raw_payload,
        )
        scored = score(dto)

        row = RecordScore(
            normalized_record_id=record.id,
            fit=scored.fit,
            label=scored.label,
            recommendation=scored.recommendation,
            explanation={
                "fit_score": scored.explanation.fit_score,
                "summary": scored.explanation.summary,
                "drivers": scored.explanation.drivers,
                "risks": scored.explanation.risks,
            },
        )
        db.add(row)
        written += 1

    await db.commit()
    return {"scores_written": written, "rescore": rescore}
