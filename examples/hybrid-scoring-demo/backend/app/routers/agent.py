import uuid
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.runtime import list_conversation_messages, run_agent_chat, run_agent_chat_stream_events
from app.database import get_db
from app.schemas import AgentChatRequest, AgentChatResponse, AgentConversationOut

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/chat", response_model=AgentChatResponse)
async def post_agent_chat(
    body: AgentChatRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await run_agent_chat(body.message, db, body.conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/chat/stream")
async def post_agent_chat_stream(
    body: AgentChatRequest,
    db: AsyncSession = Depends(get_db),
):
    async def event_stream():
        async for event in run_agent_chat_stream_events(body.message, db, body.conversation_id):
            yield _format_sse(event["event"], event["data"])

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/conversations/{conversation_id}", response_model=AgentConversationOut)
async def get_agent_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    try:
        messages = await list_conversation_messages(conversation_id, db)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"conversation_id": conversation_id, "messages": messages}


def _format_sse(event: str, data: dict) -> str:
    payload = json.dumps(jsonable_encoder(data), separators=(",", ":"))
    return f"event: {event}\ndata: {payload}\n\n"
