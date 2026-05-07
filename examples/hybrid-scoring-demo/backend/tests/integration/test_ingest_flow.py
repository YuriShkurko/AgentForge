import pytest


@pytest.mark.asyncio
async def test_ingest_endpoint_returns_200(client):
    response = await client.post("/ingest")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_ingest_response_shape(client):
    data = (await client.post("/ingest")).json()
    assert "run_id" in data
    assert data["raw_records_inserted"] > 0
    assert data["normalized_inserted"] > 0


@pytest.mark.asyncio
async def test_ingest_creates_run_in_list(client):
    await client.post("/ingest")
    runs = (await client.get("/runs")).json()["runs"]
    assert len(runs) == 1
    assert runs[0]["status"] == "complete"
    assert runs[0]["provider_name"] == "fixture"


@pytest.mark.asyncio
async def test_ingest_records_appear_in_list(client):
    await client.post("/ingest")
    records = (await client.get("/records")).json()["records"]
    assert len(records) > 0
    for r in records:
        assert r["title"]
        assert r["category"]
