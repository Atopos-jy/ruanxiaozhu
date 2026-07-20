from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8_000)
    conversation_id: UUID | None = None
    agent_id: str = Field(default="ai-manager", min_length=1, max_length=64)
