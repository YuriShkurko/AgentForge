import pytest


@pytest.mark.asyncio
async def test_score_after_ingest(client):
    await client.post("/ingest")
    response = await client.post("/records/score")
    assert response.status_code == 200
    data = response.json()
    assert data["scores_written"] > 0


@pytest.mark.asyncio
async def test_import_user_records_and_score(client):
    response = await client.post(
        "/ingest/import",
        json={
            "source": "manual_import",
            "records": [
                {"external_id": "user-1", "name": "Urgent renewal", "type": "support", "priority": 95},
                {"external_id": "bad-1", "category": "support", "value": 10},
            ],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] == 1
    assert data["skipped"] == 1
    assert data["errors"][0]["error"].startswith("title is required")

    score = (await client.post("/records/score")).json()
    assert score["scores_written"] == 1
    scored = (await client.get("/records/scored")).json()["records"]
    assert scored[0]["record"]["external_id"] == "user-1"


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
