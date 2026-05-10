import pytest

from app.agent.runtime import list_conversation_messages, run_agent_chat, run_agent_chat_stream_events


@pytest.mark.asyncio
async def test_agent_simple_response_persists_messages(db):
    result = await run_agent_chat("What can you do?", db)

    assert result["conversation_id"]
    assert result["tool_events"] == []
    assert "ingest fixture records" in result["assistant_message"]["content"]
    assert [message["role"] for message in result["messages"]] == ["user", "assistant"]


@pytest.mark.asyncio
async def test_agent_tool_call_scores_records(db):
    await run_agent_chat("ingest records", db)
    result = await run_agent_chat("score the records", db)

    assert result["tool_events"][0]["tool_name"] == "score_records"
    assert result["tool_events"][0]["ok"] is True
    assert result["tool_events"][0]["result"]["scores_written"] > 0
    assert result["messages"][-2]["role"] == "tool"
    assert result["messages"][-1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_agent_unknown_tool_records_error(db):
    result = await run_agent_chat("please call an unknown tool", db)

    assert result["tool_events"][0]["ok"] is False
    assert result["tool_events"][0]["error_code"] == "unknown_tool"
    assert "unknown tool" in result["tool_events"][0]["error"]
    assert "Tool error" in result["assistant_message"]["content"]


@pytest.mark.asyncio
async def test_agent_invalid_tool_arguments_records_structured_error(db):
    result = await run_agent_chat("please use invalid args", db)

    assert result["tool_events"][0]["tool_name"] == "score_records"
    assert result["tool_events"][0]["ok"] is False
    assert result["tool_events"][0]["error_code"] == "invalid_arguments"
    assert "rescore must be a boolean" in result["tool_events"][0]["error"]


@pytest.mark.asyncio
async def test_agent_stream_events_are_ordered_for_tool_call(db):
    await run_agent_chat("ingest records", db)

    events = [event async for event in run_agent_chat_stream_events("score the records", db)]
    event_names = [event["event"] for event in events]

    assert event_names[0:3] == ["message_start", "tool_call", "tool_result"]
    assert "text_delta" in event_names
    assert event_names[-1] == "done"
    assert events[2]["data"]["ok"] is True
    assert events[-1]["data"]["ok"] is True


@pytest.mark.asyncio
async def test_agent_stream_returns_tool_error_without_crashing(db):
    events = [event async for event in run_agent_chat_stream_events("please use invalid args", db)]

    tool_result = next(event for event in events if event["event"] == "tool_result")
    assert tool_result["data"]["ok"] is False
    assert tool_result["data"]["error_code"] == "invalid_arguments"
    assert events[-1]["event"] == "done"
    assert events[-1]["data"]["ok"] is True


@pytest.mark.asyncio
async def test_agent_conversation_can_continue(db):
    first = await run_agent_chat("What can you do?", db)
    second = await run_agent_chat("show action history", db, first["conversation_id"])

    assert second["conversation_id"] == first["conversation_id"]
    messages = await list_conversation_messages(first["conversation_id"], db)
    assert len(messages) == 5
    assert messages[-1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_agent_rejects_empty_message(db):
    with pytest.raises(ValueError):
        await run_agent_chat("   ", db)
