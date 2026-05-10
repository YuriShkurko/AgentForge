import pytest

from app.providers.fixture.provider import FixtureRecordProvider
from app.services.ingest import run_ingest
from app.services.notifications import create_notification_previews, list_notification_previews
from app.services.score import run_score


async def _seed_scored(db):
    await run_ingest(FixtureRecordProvider(), db)
    await run_score(db)


@pytest.mark.asyncio
async def test_create_notification_previews_from_scored_records(db):
    await _seed_scored(db)

    result = await create_notification_previews(db)

    assert result["previews_written"] > 0


@pytest.mark.asyncio
async def test_notification_preview_contains_payload_fields(db):
    await _seed_scored(db)
    await create_notification_previews(db)

    previews = await list_notification_previews(db)

    assert previews
    first = previews[0]
    assert first["title"]
    assert first["delivery_channel"] == "preview"
    assert first["delivery_status"] == "previewed"
    assert first["available_actions"] == ["accept", "skip", "save"]
    assert isinstance(first["drivers"], list)
    assert isinstance(first["risks"], list)


@pytest.mark.asyncio
async def test_notification_previews_require_scored_records(db):
    await run_ingest(FixtureRecordProvider(), db)

    result = await create_notification_previews(db)

    assert result["previews_written"] == 0
