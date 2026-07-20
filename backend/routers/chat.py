from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from dependencies import get_current_user
from schemas.auth import UserResponse
from schemas.chat import ChatRequest
from services.chat import list_conversations, list_messages, stream_chat


router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat")
def chat(data: ChatRequest, current_user: Annotated[UserResponse, Depends(get_current_user)]) -> StreamingResponse:
    return StreamingResponse(
        stream_chat(current_user.id, data.message, data.conversation_id, data.agent_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/conversations")
def conversations(current_user: Annotated[UserResponse, Depends(get_current_user)]) -> dict[str, list[dict[str, str]]]:
    return {"data": list_conversations(current_user.id)}


@router.get("/conversations/{conversation_id}/messages")
def messages(conversation_id: UUID, current_user: Annotated[UserResponse, Depends(get_current_user)]) -> dict[str, list[dict[str, str]]]:
    return {"data": list_messages(current_user.id, conversation_id)}
