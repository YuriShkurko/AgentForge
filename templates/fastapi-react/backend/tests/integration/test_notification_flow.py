import pytest


@pytest.mark.asyncio
async def test_notification_preview_flow(client):
    await client.post("/ingest")
    await client.post("/records/score")

    created = await client.post("/notifications/previews")
    assert created.status_code == 200
    assert created.json()["previews_written"] > 0

    previews = (await client.get("/notifications/previews")).json()["previews"]
    assert previews
    assert previews[0]["delivery_status"] == "previewed"


@pytest.mark.asyncio
async def test_action_history_endpoint(client):
    await client.post("/ingest")
    await client.post("/records/score")
    record_id = (await client.get("/records/scored")).json()["records"][0]["record"]["id"]

    await client.post(f"/records/{record_id}/action", json={"action_type": "accept"})
    await client.post(f"/records/{record_id}/action", json={"action_type": "skip"})

    history = (await client.get("/actions/history")).json()["events"]
    assert [event["status"] for event in history[:2]] == ["skipped", "accepted"]
