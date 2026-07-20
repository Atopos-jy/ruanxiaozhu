import unittest
from collections.abc import Iterator

from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, HumanMessage

from agents.ai_manager import build_ai_manager_graph


class FakeChatModel:
    def bind_tools(self, tools: list[object]) -> "FakeChatModel":
        del tools
        return self

    def stream(self, input: list[BaseMessage]) -> Iterator[AIMessageChunk]:
        del input
        yield AIMessageChunk(content="图已执行")


class AiManagerGraphTests(unittest.TestCase):
    def test_call_model_appends_an_ai_message_to_state(self) -> None:
        graph = build_ai_manager_graph(FakeChatModel())

        result = graph.invoke({"messages": [HumanMessage(content="你好")]})

        self.assertEqual(len(result["messages"]), 2)
        self.assertIsInstance(result["messages"][-1], AIMessage)
        self.assertEqual(result["messages"][-1].content, "图已执行")

    def test_graph_emits_custom_delta_for_sse(self) -> None:
        graph = build_ai_manager_graph(FakeChatModel())

        events = list(graph.stream({"messages": [HumanMessage(content="你好")]}, stream_mode=["custom", "updates"]))

        custom_events = [payload for mode, payload in events if mode == "custom"]
        self.assertEqual(custom_events, [{"type": "delta", "content": "图已执行"}])


class ToolCallingFakeChatModel:
    def bind_tools(self, tools: list[object]) -> "ToolCallingFakeChatModel":
        del tools
        return self

    def stream(self, input: list[BaseMessage]) -> Iterator[AIMessageChunk]:
        if any(message.type == "tool" for message in input):
            yield AIMessageChunk(content="已根据工具结果完成回答。")
            return
        yield AIMessageChunk(content="", tool_calls=[{"name": "get_current_time", "args": {}, "id": "time-call", "type": "tool_call"}])


class AiManagerToolGraphTests(unittest.TestCase):
    def test_tool_call_returns_to_model_with_tool_result(self) -> None:
        graph = build_ai_manager_graph(ToolCallingFakeChatModel())

        result = graph.invoke({"messages": [HumanMessage(content="现在几点？")]})

        self.assertEqual(result["messages"][-1].content, "已根据工具结果完成回答。")
        self.assertEqual(result["messages"][-2].type, "tool")

    def test_tool_call_emits_custom_progress_events(self) -> None:
        graph = build_ai_manager_graph(ToolCallingFakeChatModel())

        events = list(graph.stream({"messages": [HumanMessage(content="现在几点？")]}, stream_mode=["custom", "updates"]))

        custom_events = [payload for mode, payload in events if mode == "custom"]
        self.assertEqual(custom_events[0], {"type": "tool_call", "tool": "get_current_time"})
        self.assertEqual(custom_events[1]["type"], "tool_result")
        self.assertEqual(custom_events[2], {"type": "delta", "content": "已根据工具结果完成回答。"})


if __name__ == "__main__":
    unittest.main()
