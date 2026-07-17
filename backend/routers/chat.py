from typing import Annotated

from fastapi import APIRouter, Depends

from dependencies import get_current_user
from schemas.auth import UserResponse
from schemas.chat import ChatRequest


router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat")
def chat(data: ChatRequest, current_user: Annotated[UserResponse, Depends(get_current_user)]) -> dict[str, str]:
    return {"reply": f"{current_user.email}，已收到你的问题：{data.message}"}
