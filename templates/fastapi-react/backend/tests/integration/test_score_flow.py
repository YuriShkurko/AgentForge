import pytest


@pytest.mark.asyncio
async def test_score_after_ingest(client):
    await client.post("/ingest")
    response = await client.post("/records/score")
    assert response.status_code == 200
    data = response.json()
    assert data["scores_written"] > 0


@pytest.mark.asyncio
async def test_scored_records_appear(client):
    await client.post("/ingest")
    await client.post("/records/score")
    scored = (await client.get("/records/scored")).json()["records"]
    assert len(scored) > 0


@pytest.mark.asyncio
async def test_scored_records_ordered_by_fit_desc(client):
    await client.post("/ingest")
    await client.post("/records/score")
    scored = (await client.get("/records/scored")).json()["records"]
    fits = [r["score"]["fit"] for r in scored]
    assert fits == sorted(fits, reverse=True)


@pytest.mark.asyncio
async def test_scored_record_has_explanation(client):
    await client.post("/ingest")
    await client.post("/records/score")
    first = (await client.get("/records/scored")).json()["records"][0]
    exp = first["score"]["explanation"]
    assert "summary" in exp
    assert isinstance(exp["drivers"], list)
    assert isinstance(exp["risks"], list)


@pytest.mark.asyncio
async def test_record_action_flow(client):
    await client.post("/ingest")
    await client.post("/records/score")
    record_id = (await client.get("/records/scored")).json()["records"][0]["record"]["id"]

    resp = await client.post(f"/records/{record_id}/action", json={"action_type": "accept"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["status"] == "accepted"


@pytest.mark.asyncio
async def test_action_reflected_in_scored_list(client):
    await client.post("/ingest")
    await client.post("/records/score")
    record_id = (await client.get("/records/scored")).json()["records"][0]["record"]["id"]
    await client.post(f"/records/{record_id}/action", json={"action_type": "skip"})

    scored = (await client.get("/records/scored")).json()["records"]
    acted = next(r for r in scored if r["record"]["id"] == record_id)
    assert acted["action"]["status"] == "skipped"
