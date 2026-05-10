import pytest


def _parse_sse_events(body: str) -> list[tuple[str, dict]]:
    events = []
    for frame in body.strip().split("\n\n"):
        lines = frame.splitlines()
        event_name = next(line.removeprefix("event: ") for line in lines if line.startswith("event: "))
        data = next(line.removeprefix("data: ") for line in lines if line.startswith("data: "))
        import json

        events.append((event_name, json.loads(data)))
    return events


@pytest.mark.asyncio
async def test_agent_chat_simple_response(client):
    response = await client.post("/agent/chat", json={"message": "What can you do?"})

    assert response.status_code == 200
    data = response.json()
    assert data["conversation_id"]
    assert data["assistant_message"]["role"] == "assistant"
    assert data["tool_events"] == []


@pytest.mark.asyncio
async def test_agent_chat_tool_flow_and_history(client):
    ingest = await client.post("/agent/chat", json={"message": "ingest records"})
    conversation_id = ingest.json()["conversation_id"]

    score = await client.post(
        "/agent/chat",
        json={"conversation_id": conversation_id, "message": "score the records"},
    )

    assert score.status_code == 200
    data = score.json()
    assert data["tool_events"][0]["tool_name"] == "score_records"
    assert data["tool_events"][0]["ok"] is True

    history = await client.get(f"/agent/conversations/{conversation_id}")
    assert history.status_code == 200
    roles = [message["role"] for message in history.json()["messages"]]
    assert roles == ["user", "tool", "assistant", "user", "tool", "assistant"]


@pytest.mark.asyncio
async def test_agent_chat_stream_returns_ordered_events(client):
    await client.post("/agent/chat", json={"message": "ingest records"})

    response = await client.post("/agent/chat/stream", json={"message": "score the records"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = _parse_sse_events(response.text)
    event_names = [event[0] for event in events]
    assert event_names[0:3] == ["message_start", "tool_call", "tool_result"]
    assert "text_delta" in event_names
    assert event_names[-1] == "done"
    assert events[-1][1]["ok"] is True


@pytest.mark.asyncio
async def test_agent_chat_stream_returns_validation_error_event(client):
    response = await client.post("/agent/chat/stream", json={"message": "please use invalid args"})

    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    tool_result = next(data for name, data in events if name == "tool_result")
    assert tool_result["ok"] is False
    assert tool_result["error_code"] == "invalid_arguments"
    assert events[-1][0] == "done"


@pytest.mark.asyncio
async def test_agent_chat_rejects_empty_message(client):
    response = await client.post("/agent/chat", json={"message": "   "})

    assert response.status_code == 422
