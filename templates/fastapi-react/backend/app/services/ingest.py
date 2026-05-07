import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.normalize import normalize
from app.models import NormalizedRecord, ProviderRun, RawRecord
from app.providers.interface import RecordProvider


async def run_ingest(provider: RecordProvider, db: AsyncSession) -> dict:
    run = ProviderRun(provider_name=provider.name, status="running")
    db.add(run)
    await db.flush()

    try:
        raw_records = provider.fetch()

        raw_inserted = 0
        normalized_inserted = 0

        for raw in raw_records:
            row = RawRecord(
                run_id=run.id,
                external_id=raw.external_id,
                source=raw.source,
                raw_payload=raw.raw_payload,
            )
            db.add(row)
            raw_inserted += 1

            existing = await db.scalar(
                select(NormalizedRecord).where(NormalizedRecord.external_id == raw.external_id)
            )
            if existing is None:
                dto = normalize(raw)
                norm = NormalizedRecord(
                    external_id=dto.external_id,
                    source=dto.source,
                    title=dto.title,
                    category=dto.category,
                    value=dto.value,
                    raw_payload=dto.raw_payload,
                )
                db.add(norm)
                normalized_inserted += 1

        run.status = "complete"
        run.finished_at = datetime.now(timezone.utc)
        run.stats = {"raw_inserted": raw_inserted, "normalized_inserted": normalized_inserted}
        await db.commit()

    except Exception as exc:
        run.status = "error"
        run.finished_at = datetime.now(timezone.utc)
        run.error = str(exc)
        await db.commit()
        raise

    return {"run_id": run.id, "raw_records_inserted": raw_inserted, "normalized_inserted": normalized_inserted}
