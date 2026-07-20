import json
import uuid
from collections.abc import Generator
from datetime import datetime, timezone
from typing import Literal

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from agents.ai_manager import build_ai_manager_graph
from config import LLM_API_KEY
from database import get_connection


SYSTEM_PROMPT = """你是软小筑 AI 管家。你的回答应准确、友好、简洁。

当前对话由 LangGraph 基础状态图编排：START → call_model → END。你可以解释
LangGraph、当前 AI 管家的编排方式，以及后续工具调用与 RAG 的开发规划。

当前尚未提供知识库检索、联网搜索、文档创建、日程或自动化执行工具。用户询问
这些能力时，请如实说明当前状态与规划；不要虚构已经查询过资料或执行过操作。"""

EventType = Literal["delta", "tool_call", "tool_result", "done", "error"]


def encode_sse(event_type: EventType, data: dict[str, str]) -> str:
    """Encode one JSON payload as a Server-Sent Event message."""
    payload = {"type": event_type, **data}
    return f"event: message\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def list_conversations(user_id: str) -> list[dict[str, str]]:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT id, agent_id, title, updated_at FROM conversations
                WHERE user_id = %s ORDER BY updated_at DESC""",
                (user_id,),
            )
            return [
                {
                    "id": str(row["id"]),
                    "agent_id": row["agent_id"],
                    "title": row["title"] or "新会话",
                    "updated_at": row["updated_at"].isoformat(),
                }
                for row in cursor.fetchall()
            ]


def list_messages(user_id: str, conversation_id: uuid.UUID) -> list[dict[str, str]]:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM conversations WHERE id = %s AND user_id = %s", (conversation_id, user_id))
            if cursor.fetchone() is None:
                return []
            cursor.execute(
                """SELECT id, role, content, created_at FROM messages
                WHERE conversation_id = %s ORDER BY created_at ASC""",
                (conversation_id,),
            )
            return [
                {
                    "id": str(row["id"]),
                    "role": row["role"],
                    "content": row["content"],
                    "created_at": row["created_at"].isoformat(),
                }
                for row in cursor.fetchall()
            ]


def stream_chat(user_id: str, message: str, conversation_id: uuid.UUID | None, agent_id: str) -> Generator[str, None, None]:
    """Persist a turn and stream the model's response in SSE chunks."""
    if not LLM_API_KEY:
        yield encode_sse("error", {"detail": "LLM_API_KEY 未配置，请先在后端 .env 中设置模型密钥。"})
        return

    is_new_conversation = conversation_id is None
    conversation_id = conversation_id or uuid.uuid4()
    user_message_id, assistant_message_id = uuid.uuid4(), uuid.uuid4()
    now = datetime.now(timezone.utc)
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM conversations WHERE id = %s AND user_id = %s", (conversation_id, user_id))
            existing_conversation = cursor.fetchone()
            if not is_new_conversation and existing_conversation is None:
                yield encode_sse("error", {"detail": "会话不存在或无权访问。"})
                return
            if is_new_conversation:
                cursor.execute(
                    """INSERT INTO conversations (id, user_id, agent_id, title, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)""",
                    (conversation_id, user_id, agent_id, message[:50], now, now),
                )
            cursor.execute(
                """INSERT INTO messages (id, conversation_id, role, content, created_at)
                VALUES (%s, %s, 'user', %s, %s)""",
                (user_message_id, conversation_id, message, now),
            )
            cursor.execute("UPDATE conversations SET updated_at = %s WHERE id = %s", (now, conversation_id))
            cursor.execute("SELECT role, content FROM messages WHERE conversation_id = %s ORDER BY created_at ASC", (conversation_id,))
            rows = cursor.fetchall()

    messages: list[BaseMessage] = [SystemMessage(content=SYSTEM_PROMPT)]
    for row in rows:
        if row["role"] == "assistant":
            messages.append(AIMessage(content=row["content"]))
        elif row["role"] == "user":
            messages.append(HumanMessage(content=row["content"]))

    response_parts: list[str] = []
    try:
        graph = build_ai_manager_graph()
        for mode, payload in graph.stream({"messages": messages}, stream_mode=["custom", "updates"]):
            if mode != "custom" or not isinstance(payload, dict):
                continue
            event_type = payload.get("type")
            if event_type == "tool_call":
                tool_name = payload.get("tool")
                if isinstance(tool_name, str):
                    yield encode_sse("tool_call", {"tool": tool_name})
                continue
            if event_type == "tool_result":
                tool_name, result = payload.get("tool"), payload.get("result")
                if isinstance(tool_name, str) and isinstance(result, str):
                    yield encode_sse("tool_result", {"tool": tool_name, "result": result})
                continue
            content = payload.get("content")
            if event_type != "delta" or not isinstance(content, str) or not content:
                continue
            response_parts.append(content)
            yield encode_sse("delta", {"delta": content, "conversation_id": str(conversation_id), "message_id": str(assistant_message_id)})
    except Exception:
        yield encode_sse("error", {"detail": "模型服务暂时不可用，请稍后再试。"})
        return

    response = "".join(response_parts).strip()
    if not response:
        yield encode_sse("error", {"detail": "模型未返回有效内容，请稍后再试。"})
        return

    finished_at = datetime.now(timezone.utc)
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""INSERT INTO messages (id, conversation_id, role, content, created_at)
                VALUES (%s, %s, 'assistant', %s, %s)""", (assistant_message_id, conversation_id, response, finished_at))
            cursor.execute("UPDATE conversations SET updated_at = %s WHERE id = %s", (finished_at, conversation_id))
    yield encode_sse("done", {"conversation_id": str(conversation_id), "message_id": str(assistant_message_id)})
