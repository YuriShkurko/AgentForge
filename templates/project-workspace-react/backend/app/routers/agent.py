import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.runtime import chat
from app.database import get_db
from app.schemas import AgentChatIn, AgentChatOut

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/chat", response_model=AgentChatOut)
async def agent_chat(payload: AgentChatIn, db: AsyncSession = Depends(get_db)):
    try:
        return await chat(db, payload.message, payload.conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/chat/stream")
async def agent_chat_stream(payload: AgentChatIn, db: AsyncSession = Depends(get_db)):
    try:
        result = await chat(db, payload.message, payload.conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    async def events():
        yield f"event: message_start\ndata: {json.dumps({'conversation_id': str(result['conversation_id'])})}\n\n"
        for event in result["tool_events"]:
            yield f"event: tool_call\ndata: {json.dumps({'tool_name': event['tool_name'], 'arguments': event['arguments']})}\n\n"
            yield f"event: tool_result\ndata: {json.dumps(event, default=str)}\n\n"
        yield f"event: text_delta\ndata: {json.dumps({'text': result['assistant_message']['content']})}\n\n"
        yield f"event: done\ndata: {json.dumps({'ok': True, 'conversation_id': str(result['conversation_id']), 'messages': result['messages']}, default=str)}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")
