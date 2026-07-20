from collections.abc import Iterator
from typing import Annotated, Protocol, TypedDict

from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from llm import create_llm
from tools.date_time import get_current_time


class AgentState(TypedDict):
    """The state that flows through every node of the AI manager graph."""

    messages: Annotated[list[BaseMessage], add_messages]


class StreamingChatModel(Protocol):
    """The minimal LangChain model interface used by this first graph."""

    def bind_tools(self, tools: list[BaseTool]) -> "StreamingChatModel": ...

    def stream(self, input: list[BaseMessage]) -> Iterator[AIMessageChunk]: ...


TOOLS: list[BaseTool] = [get_current_time]
TOOLS_BY_NAME = {tool.name: tool for tool in TOOLS}


def _chunk_text(message: AIMessageChunk) -> str:
    return message.content if isinstance(message.content, str) else ""


def build_ai_manager_graph(model: StreamingChatModel | None = None):
    """Compile the first LangGraph: START -> call_model -> END."""
    chat_model = (model or create_llm()).bind_tools(TOOLS)

    def call_model(state: AgentState) -> dict[str, list[AIMessage]]:
        writer = get_stream_writer()
        response_parts: list[str] = []
        full_response: AIMessageChunk | None = None
        for chunk in chat_model.stream(state["messages"]):
            content = _chunk_text(chunk)
            if content:
                response_parts.append(content)
                writer({"type": "delta", "content": content})
            full_response = chunk if full_response is None else full_response + chunk
        if full_response is None:
            return {"messages": [AIMessage(content="")]}
        return {
            "messages": [
                AIMessage(content="".join(response_parts), tool_calls=full_response.tool_calls),
            ],
        }

    def should_continue(state: AgentState) -> str:
        last_message = state["messages"][-1]
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "execute_tools"
        return END

    def execute_tools(state: AgentState) -> dict[str, list[ToolMessage]]:
        writer = get_stream_writer()
        last_message = state["messages"][-1]
        if not isinstance(last_message, AIMessage):
            return {"messages": []}

        tool_messages: list[ToolMessage] = []
        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_call_id = tool_call["id"]
            selected_tool = TOOLS_BY_NAME.get(tool_name)
            if selected_tool is None:
                result = f"不支持工具：{tool_name}"
            else:
                writer({"type": "tool_call", "tool": tool_name})
                result = str(selected_tool.invoke(tool_call["args"]))
                writer({"type": "tool_result", "tool": tool_name, "result": result})
            tool_messages.append(ToolMessage(content=result, tool_call_id=tool_call_id, name=tool_name))
        return {"messages": tool_messages}

    graph = StateGraph(AgentState)
    graph.add_node("call_model", call_model)
    graph.add_node("execute_tools", execute_tools)
    graph.add_edge(START, "call_model")
    graph.add_conditional_edges("call_model", should_continue, ["execute_tools", END])
    graph.add_edge("execute_tools", "call_model")
    return graph.compile()
