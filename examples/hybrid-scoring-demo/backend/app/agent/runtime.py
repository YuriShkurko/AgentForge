import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.providers import AgentPlan, ScriptedAgentProvider
from app.agent.tools import ToolExecutionError, execute_tool
from app.models import Conversation, ConversationMessage

AgentEventSink = Callable[[dict[str, Any]], Awaitable[None]]


def _message_out(message: ConversationMessage) -> dict:
    return {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "metadata": message.message_metadata,
        "created_at": message.created_at,
    }


async def _get_or_create_conversation(
    db: AsyncSession,
    conversation_id: uuid.UUID | None,
) -> Conversation:
    if conversation_id is not None:
        conversation = await db.get(Conversation, conversation_id)
        if conversation is None:
            raise LookupError(f"conversation {conversation_id} not found")
        return conversation

    conversation = Conversation(title="Hybrid Scoring Demo Agent")
    db.add(conversation)
    await db.flush()
    return conversation


async def list_conversation_messages(
    conversation_id: uuid.UUID,
    db: AsyncSession,
) -> list[dict]:
    conversation = await db.get(Conversation, conversation_id)
    if conversation is None:
        raise LookupError(f"conversation {conversation_id} not found")

    result = await db.execute(
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conversation_id)
        .order_by(ConversationMessage.created_at)
    )
    return [_message_out(message) for message in result.scalars().all()]


async def run_agent_chat(
    message: str,
    db: AsyncSession,
    conversation_id: uuid.UUID | None = None,
) -> dict:
    return await _run_agent_chat(message, db, conversation_id)


async def run_agent_chat_stream_events(
    message: str,
    db: AsyncSession,
    conversation_id: uuid.UUID | None = None,
) -> AsyncIterator[dict[str, Any]]:
    try:
        cleaned = message.strip()
        if not cleaned:
            raise ValueError("message must not be empty")

        conversation = await _get_or_create_conversation(db, conversation_id)
        user_message = ConversationMessage(
            conversation_id=conversation.id,
            role="user",
            content=cleaned,
            created_at=datetime.now(UTC),
        )
        db.add(user_message)
        await db.flush()

        yield {
            "event": "message_start",
            "data": {
                "conversation_id": str(conversation.id),
                "message_id": str(user_message.id),
                "role": "user",
            },
        }

        provider = ScriptedAgentProvider()
        plan: AgentPlan = provider.plan(cleaned)
        tool_events = []

        for call in plan.tool_calls:
            yield {"event": "tool_call", "data": {"tool_name": call.name, "arguments": call.arguments}}
            try:
                result = await execute_tool(call.name, call.arguments, db)
                event = {
                    "tool_name": call.name,
                    "arguments": call.arguments,
                    "ok": True,
                    "result": result,
                    "error": None,
                    "error_code": None,
                }
                tool_content = f"{call.name} returned {result}"
            except ToolExecutionError as exc:
                event = {
                    "tool_name": call.name,
                    "arguments": call.arguments,
                    "ok": False,
                    "result": None,
                    "error": exc.message,
                    "error_code": exc.code,
                }
                tool_content = f"{call.name} failed: {exc.message}"
            except Exception as exc:
                event = {
                    "tool_name": call.name,
                    "arguments": call.arguments,
                    "ok": False,
                    "result": None,
                    "error": str(exc),
                    "error_code": "tool_error",
                }
                tool_content = f"{call.name} failed: {exc}"

            tool_events.append(event)
            yield {"event": "tool_result", "data": event}
            db.add(
                ConversationMessage(
                    conversation_id=conversation.id,
                    role="tool",
                    content=tool_content,
                    message_metadata=event,
                    created_at=datetime.now(UTC),
                )
            )

        assistant_text = _render_assistant_text(plan.final_text, tool_events)
        for chunk in _text_chunks(assistant_text):
            yield {"event": "text_delta", "data": {"text": chunk}}

        assistant_message = ConversationMessage(
            conversation_id=conversation.id,
            role="assistant",
            content=assistant_text,
            message_metadata={"provider": "scripted", "tool_events": tool_events},
            created_at=datetime.now(UTC),
        )
        db.add(assistant_message)
        conversation.updated_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(assistant_message)

        messages = await list_conversation_messages(conversation.id, db)
    except ValueError as exc:
        yield {"event": "error", "data": {"error": str(exc), "error_code": "invalid_message"}}
        yield {"event": "done", "data": {"ok": False}}
        return
    except LookupError as exc:
        yield {"event": "error", "data": {"error": str(exc), "error_code": "not_found"}}
        yield {"event": "done", "data": {"ok": False}}
        return

    yield {
        "event": "done",
        "data": {
            "ok": True,
            "conversation_id": str(conversation.id),
            "messages": messages,
            "tool_events": tool_events,
        },
    }


async def _run_agent_chat(
    message: str,
    db: AsyncSession,
    conversation_id: uuid.UUID | None = None,
    event_sink: AgentEventSink | None = None,
) -> dict:
    cleaned = message.strip()
    if not cleaned:
        raise ValueError("message must not be empty")

    conversation = await _get_or_create_conversation(db, conversation_id)
    now = datetime.now(UTC)
    user_message = ConversationMessage(
        conversation_id=conversation.id,
        role="user",
        content=cleaned,
        created_at=now,
    )
    db.add(user_message)
    await db.flush()

    if event_sink:
        await event_sink(
            {
                "event": "message_start",
                "data": {
                    "conversation_id": str(conversation.id),
                    "message_id": str(user_message.id),
                    "role": "user",
                },
            }
        )

    provider = ScriptedAgentProvider()
    plan: AgentPlan = provider.plan(cleaned)

    tool_events = []
    for call in plan.tool_calls:
        if event_sink:
            await event_sink(
                {
                    "event": "tool_call",
                    "data": {"tool_name": call.name, "arguments": call.arguments},
                }
            )
        try:
            result = await execute_tool(call.name, call.arguments, db)
            event = {
                "tool_name": call.name,
                "arguments": call.arguments,
                "ok": True,
                "result": result,
                "error": None,
                "error_code": None,
            }
            tool_content = f"{call.name} returned {result}"
        except ToolExecutionError as exc:
            event = {
                "tool_name": call.name,
                "arguments": call.arguments,
                "ok": False,
                "result": None,
                "error": exc.message,
                "error_code": exc.code,
            }
            tool_content = f"{call.name} failed: {exc.message}"
        except Exception as exc:
            event = {
                "tool_name": call.name,
                "arguments": call.arguments,
                "ok": False,
                "result": None,
                "error": str(exc),
                "error_code": "tool_error",
            }
            tool_content = f"{call.name} failed: {exc}"

        tool_events.append(event)
        if event_sink:
            await event_sink({"event": "tool_result", "data": event})
        db.add(
            ConversationMessage(
                conversation_id=conversation.id,
                role="tool",
                content=tool_content,
                message_metadata=event,
                created_at=datetime.now(UTC),
            )
        )

    assistant_text = _render_assistant_text(plan.final_text, tool_events)
    if event_sink:
        for chunk in _text_chunks(assistant_text):
            await event_sink({"event": "text_delta", "data": {"text": chunk}})

    assistant_message = ConversationMessage(
        conversation_id=conversation.id,
        role="assistant",
        content=assistant_text,
        message_metadata={"provider": "scripted", "tool_events": tool_events},
        created_at=datetime.now(UTC),
    )
    db.add(assistant_message)
    conversation.updated_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(assistant_message)

    messages = await list_conversation_messages(conversation.id, db)
    return {
        "conversation_id": conversation.id,
        "assistant_message": _message_out(assistant_message),
        "messages": messages,
        "tool_events": tool_events,
    }


def _text_chunks(text: str) -> list[str]:
    words = text.split(" ")
    if len(words) <= 1:
        return [text]
    return [f"{word} " for word in words[:-1]] + [words[-1]]


def _render_assistant_text(final_text: str, tool_events: list[dict]) -> str:
    if not tool_events:
        return final_text

    failed = [event for event in tool_events if not event["ok"]]
    if failed:
        return f"{final_text} Tool error ({failed[0]['error_code']}): {failed[0]['error']}"
    return final_text
