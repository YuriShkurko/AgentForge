import pytest


def _parse_sse_events(body: str) -> list[tuple[str, dict]]:
    import json
    events = []
    for frame in body.strip().split("\n\n"):
        lines = frame.splitlines()
        event_name = next(line.removeprefix("event: ") for line in lines if line.startswith("event: "))
        data = next(line.removeprefix("data: ") for line in lines if line.startswith("data: "))
        events.append((event_name, json.loads(data)))
    return events


@pytest.mark.asyncio
async def test_agent_lists_tasks_and_pins_workspace_widget(client):
    await client.post("/seed")

    response = await client.post("/agent/chat", json={"message": "list tasks"})
    assert response.status_code == 200
    data = response.json()
    assert data["conversation_id"]
    assert data["tool_events"][0]["tool_name"] == "list_tasks"
    assert data["tool_events"][0]["ok"] is True

    stream = await client.post("/agent/chat/stream", json={"conversation_id": data["conversation_id"], "message": "pin task list"})
    assert stream.status_code == 200
    events = _parse_sse_events(stream.text)
    assert events[-1][0] == "done"
    assert any(payload.get("tool_name") == "pin_task_list" for name, payload in events if name == "tool_result")

    widgets = await client.get("/workspace/widgets")
    assert widgets.status_code == 200
    assert widgets.json()[0]["widget_type"] == "task_list"


@pytest.mark.asyncio
async def test_workspace_rejects_incompatible_widget(client):
    response = await client.post("/workspace/widgets", json={
        "widget_type": "task_list",
        "title": "Bad widget",
        "source_tool": "summarize_project",
        "data": {"ok": True},
    })
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "incompatible_widget"
