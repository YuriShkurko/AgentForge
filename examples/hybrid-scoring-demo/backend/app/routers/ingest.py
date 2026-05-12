from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import NormalizedRecord, ProviderRun, RawRecord
from app.providers.fixture.provider import FixtureRecordProvider
from app.providers.interface import RawRecord as ProviderRawRecord
from app.schemas import ImportRecordsOut, ImportRecordsRequest, IngestOut
from app.services.ingest import run_ingest

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("", response_model=IngestOut)
async def ingest(db: AsyncSession = Depends(get_db)):
    provider = FixtureRecordProvider()
    result = await run_ingest(provider, db)
    return result


@router.post("/import", response_model=ImportRecordsOut)
async def import_records(payload: ImportRecordsRequest, db: AsyncSession = Depends(get_db)):
    """Import user-provided JSON records without requiring external providers or API keys."""
    source = _clean_source(payload.source)
    run = ProviderRun(provider_name=source, status="running")
    db.add(run)
    await db.flush()

    accepted = 0
    skipped = 0
    errors: list[dict[str, Any]] = []

    for index, item in enumerate(payload.records):
        parsed, error = _parse_import_record(item, index, source)
        if error:
            errors.append(error)
            skipped += 1
            continue

        assert parsed is not None
        existing = await db.scalar(
            select(NormalizedRecord).where(NormalizedRecord.external_id == parsed.external_id)
        )
        if existing is not None:
            errors.append({"index": index, "external_id": parsed.external_id, "error": "duplicate external_id"})
            skipped += 1
            continue

        db.add(
            RawRecord(
                run_id=run.id,
                external_id=parsed.external_id,
                source=parsed.source,
                raw_payload=parsed.raw_payload,
            )
        )
        db.add(
            NormalizedRecord(
                external_id=parsed.external_id,
                source=parsed.source,
                title=parsed.title,
                category=parsed.category,
                value=parsed.value,
                raw_payload=parsed.raw_payload,
            )
        )
        accepted += 1

    run.status = "complete"
    run.finished_at = datetime.now(timezone.utc)
    run.stats = {"raw_inserted": accepted, "normalized_inserted": accepted, "skipped": skipped}
    await db.commit()

    return {"run_id": run.id, "accepted": accepted, "skipped": skipped, "errors": errors}


def _clean_source(value: str) -> str:
    cleaned = "".join(ch for ch in value.lower().strip() if ch.isalnum() or ch in {"_", "-"})
    return (cleaned or "manual_import")[:64]


def _parse_import_record(item: Any, index: int, source: str) -> tuple[ProviderRawRecord | None, dict[str, Any] | None]:
    if not isinstance(item, dict):
        return None, {"index": index, "external_id": None, "error": "record must be an object"}

    external_id = str(item.get("external_id") or item.get("id") or f"{source}-{index + 1}").strip()
    title = str(_first_present(item, "title", "name", "subject") or "").strip()
    category = str(_first_present(item, "category", "type", "status") or "general").strip().lower()

    if not external_id:
        return None, {"index": index, "external_id": None, "error": "external_id or id is required"}
    if not title:
        return None, {"index": index, "external_id": external_id, "error": "title is required; accepted aliases: title, name, subject"}

    try:
        value = max(0.0, min(100.0, float(_first_present(item, "value", "amount", "score", "priority") or 0)))
    except (TypeError, ValueError):
        return None, {"index": index, "external_id": external_id, "error": "value must be numeric"}

    raw_payload = item.get("raw_payload") if isinstance(item.get("raw_payload"), dict) else dict(item)
    return ProviderRawRecord(
        external_id=external_id[:256],
        source=source,
        title=title[:256],
        category=(category or "general")[:64],
        value=value,
        raw_payload=raw_payload,
    ), None


def _first_present(item: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return value
    return None
