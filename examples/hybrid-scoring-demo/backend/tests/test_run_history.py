import pytest

from app.models import ProviderRun
from app.providers.fixture.provider import FixtureRecordProvider
from app.services.ingest import run_ingest


@pytest.mark.asyncio
async def test_ingest_creates_run_row(db):
    result = await run_ingest(FixtureRecordProvider(), db)
    assert "run_id" in result

    run = await db.get(ProviderRun, result["run_id"])
    assert run is not None
    assert run.status == "complete"
    assert run.provider_name == "fixture"
    assert run.finished_at is not None


@pytest.mark.asyncio
async def test_ingest_run_stats(db):
    result = await run_ingest(FixtureRecordProvider(), db)
    run = await db.get(ProviderRun, result["run_id"])
    assert run.stats["raw_inserted"] == result["raw_records_inserted"]
    assert run.stats["normalized_inserted"] == result["normalized_inserted"]


@pytest.mark.asyncio
async def test_second_ingest_deduplicates_normalized(db):
    r1 = await run_ingest(FixtureRecordProvider(), db)
    r2 = await run_ingest(FixtureRecordProvider(), db)
    assert r2["normalized_inserted"] == 0
    assert r2["raw_records_inserted"] == r1["raw_records_inserted"]
