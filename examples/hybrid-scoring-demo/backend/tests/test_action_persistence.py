import pytest
from sqlalchemy import select

from app.models import NormalizedRecord, RecordAction
from app.providers.fixture.provider import FixtureRecordProvider
from app.services.actions import record_action
from app.services.ingest import run_ingest


async def _seed(db):
    await run_ingest(FixtureRecordProvider(), db)
    result = await db.execute(select(NormalizedRecord).limit(1))
    return result.scalar_one()


@pytest.mark.asyncio
async def test_accept_creates_action(db):
    record = await _seed(db)
    result = await record_action(record.id, "accept", db)
    assert result["ok"] is True
    assert result["status"] == "accepted"


@pytest.mark.asyncio
async def test_skip_creates_action(db):
    record = await _seed(db)
    result = await record_action(record.id, "skip", db)
    assert result["status"] == "skipped"


@pytest.mark.asyncio
async def test_save_creates_action(db):
    record = await _seed(db)
    result = await record_action(record.id, "save", db)
    assert result["status"] == "saved"


@pytest.mark.asyncio
async def test_action_is_persisted(db):
    record = await _seed(db)
    await record_action(record.id, "accept", db)
    action = await db.scalar(
        select(RecordAction).where(RecordAction.normalized_record_id == record.id)
    )
    assert action is not None
    assert action.status == "accepted"


@pytest.mark.asyncio
async def test_action_updates_on_repeat(db):
    record = await _seed(db)
    await record_action(record.id, "accept", db)
    await record_action(record.id, "skip", db)
    action = await db.scalar(
        select(RecordAction).where(RecordAction.normalized_record_id == record.id)
    )
    assert action.status == "skipped"


@pytest.mark.asyncio
async def test_invalid_action_type_raises(db):
    record = await _seed(db)
    with pytest.raises(ValueError):
        await record_action(record.id, "explode", db)


@pytest.mark.asyncio
async def test_unknown_record_raises(db):
    import uuid
    with pytest.raises(LookupError):
        await record_action(uuid.uuid4(), "accept", db)
