import pytest


@pytest.mark.asyncio
async def test_invalid_task_status_is_rejected(client):
    await client.post("/seed")
    task = (await client.get("/tasks")).json()[0]

    response = await client.patch(f"/tasks/{task['id']}", json={"status": "scored"})

    assert response.status_code == 422
    assert "status must be" in response.json()["detail"]
