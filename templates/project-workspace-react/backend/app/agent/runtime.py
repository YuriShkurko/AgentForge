import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.tools import execute_tool
from app.models import Conversation, ConversationMessage


@dataclass
class ToolEvent:
    tool_name: str
    arguments: dict[str, Any]
    ok: bool
    result: dict[str, Any] | None = None
    error: str | None = None
    status: str = "succeeded"


async def _conversation(db: AsyncSession, conversation_id: uuid.UUID | None) -> Conversation:
    if conversation_id:
        existing = await db.get(Conversation, conversation_id)
        if existing:
            return existing
    convo = Conversation()
    db.add(convo)
    await db.flush()
    return convo


def _route(message: str) -> tuple[str | None, dict[str, Any], str]:
    text = message.lower()
    if "pin" in text and "task" in text:
        return "pin_task_list", {}, "I pinned the current task list to the workspace."
    if "pin" in text and ("project" in text or "summary" in text):
        return "pin_project_summary", {}, "I pinned a project summary to the workspace."
    if "summar" in text or "overview" in text:
        return "summarize_project", {}, "I summarized the active project workspace."
    if "done" in text or "complete" in text:
        return "list_tasks", {"status": "done"}, "Here are the completed tasks I found."
    if "blocked" in text:
        return "list_tasks", {"status": "blocked"}, "Here are the blocked tasks I found."
    if "task" in text or "plan" in text:
        return "list_tasks", {}, "Here are the current tasks in the workspace."
    return None, {}, "I can list tasks, summarize projects, add notes, update task status, and pin project/task widgets."


def _serialize_message(message: ConversationMessage) -> dict[str, Any]:
    return {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "metadata": message.message_metadata,
        "created_at": message.created_at,
    }


async def chat(db: AsyncSession, message: str, conversation_id: uuid.UUID | None = None) -> dict[str, Any]:
    if not message.strip():
        raise ValueError("Message must not be empty.")
    convo = await _conversation(db, conversation_id)
    db.add(ConversationMessage(conversation_id=convo.id, role="user", content=message.strip()))

    tool_name, arguments, final_text = _route(message)
    events: list[ToolEvent] = []
    if tool_name:
        try:
            result = await execute_tool(tool_name, arguments, db)
            events.append(ToolEvent(tool_name=tool_name, arguments=arguments, ok=True, result=result))
        except Exception as exc:
            events.append(ToolEvent(tool_name=tool_name, arguments=arguments, ok=False, error=str(exc), status="failed"))
            final_text = f"Tool error while running {tool_name}: {exc}"

    assistant = ConversationMessage(conversation_id=convo.id, role="assistant", content=final_text)
    db.add(assistant)
    await db.commit()
    await db.refresh(assistant)

    rows = await db.execute(select(ConversationMessage).where(ConversationMessage.conversation_id == convo.id).order_by(ConversationMessage.created_at))
    messages = [_serialize_message(row) for row in rows.scalars().all()]
    return {
        "conversation_id": convo.id,
        "assistant_message": _serialize_message(assistant),
        "messages": messages,
        "tool_events": [event.__dict__ for event in events],
    }
