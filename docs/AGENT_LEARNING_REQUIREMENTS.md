# AI 管家 Agent 学习与实施需求

## 1. 目标

本项目不仅要实现 RAG 问答，还要以 AI 管家为载体，循序掌握 LangGraph 的 Agent 构建能力。

学习主线是：理解并亲自实现 **State（状态）**、**Node（节点）**、**Edge（边）** 如何协作，使模型能够根据状态决定“直接回答”或“调用工具后再回答”。

RAG 的定位是一个可被 Agent 调用的“知识库检索工具”，不是 Agent 的全部。

## 2. 当前基础与边界

已具备：JWT 认证、PostgreSQL 对话/消息持久化、DeepSeek 调用、SSE 流式传输、AI 管家界面。

当前 AI 管家仍是“系统提示词 + 对话历史 + 单次模型调用”，尚未使用 LangGraph 进行编排，也没有工具调用循环。

本阶段不实现：多智能体协作、可写入外部系统的工具、自动执行高风险操作、知识库文件上传界面。

## 3. LangGraph 核心学习模型

```text
定义 AgentState
        │
        ▼
StateGraph(AgentState)
        │
        ▼
add_node：为图注册执行单元
        │
        ▼
add_edge / add_conditional_edges：定义固定或条件流转
        │
        ▼
compile：得到可执行图
        │
        ▼
graph.invoke / graph.astream：以初始状态运行
```

首个状态图必须保持最小：

```text
START → call_model → END
```

其中：

- `AgentState` 至少包含 `messages`，用于累计系统消息、用户消息、模型消息；
- `call_model` 是第一个 Node，调用 LLM 并将 AI 消息追加回 State；
- `START`、`END` 是 LangGraph 的特殊边界，不是业务 Node；
- 编译后的图替代当前服务中直接调用 `create_llm().stream(...)` 的实现。

## 4. 分阶段实施计划

### 阶段 A：第一个可运行状态图

状态：已实现，待通过本地 FastAPI 进程完成页面联调。

目标：把现有单次 LLM 调用迁移为一个最小 LangGraph，功能体验保持不变。

实现内容：

1. 新建 `backend/agents/ai_manager.py`，定义 `AgentState` 与 `build_ai_manager_graph()`。
2. 创建 `call_model` 节点，输入为 State 的消息列表，输出为新增的 AI 消息。
3. 创建 `START → call_model → END` 边并调用 `compile()`。
4. 在聊天服务中调用图的 `astream()`，将模型文本仍以 SSE `delta` 推给前端。
5. 为图写最小单元测试，验证节点输出会追加一条 AI 消息。

验收标准：普通问题能与当前版本相同地流式回复、会话会保存、测试能够独立证明 State 和 Edge 的执行顺序。

### 阶段 B：第一个只读工具循环

状态：已实现，待通过本地 FastAPI 进程完成页面联调。

目标：掌握条件边与工具循环，而不是马上接入 RAG。

图结构：

```text
START → call_model → should_continue ──否→ END
                              │
                              是
                              ▼
                         execute_tools
                              │
                              └────────→ call_model
```

实现内容：

1. 先实现一个无外部副作用的 `get_current_time` 工具。
2. 将工具绑定给模型；当模型返回工具调用时，`should_continue` 通过条件边转到 `execute_tools`。
3. 工具结果作为 ToolMessage 追加进 State，图回到 `call_model` 生成最终自然语言答案。
4. SSE 新增 `tool_call`、`tool_result` 事件；前端显示工具执行状态。
5. 为“无需工具直接回答”和“调用时间工具后回答”分别编写测试。

验收标准：询问当前时间时，界面可以看到工具调用过程；普通闲聊不会无谓调用工具；工具结果与最终回答均会被保存。

### 阶段 C：RAG 作为知识库检索工具

目标：将 RAG 接入已经验证过的 Agent 工具循环。

实现内容：文档切分、Embedding、pgvector 向量表、`knowledge_search` 工具、检索结果引用和权限过滤。

验收标准：模型只在需要资料依据时调用检索工具；回答显示引用来源；不同用户不能检索到无权访问的文档。

### 阶段 D：多 Agent 与任务能力

目标：在单 Agent 稳定后再引入专长 Agent 与路由。

实现内容：Agent 注册表、路由/监督节点、知识库诊断和销售专家等只读专业 Agent；所有有副作用的操作必须经过显式用户确认。

## 5. 实施原则

- 每一阶段均先画图、定义 State 和验收用例，再写实现代码。
- 每次只新增一个可观测能力，使用 SSE 展示节点或工具过程。
- 工具默认只读；任何写文件、发消息、创建任务等操作必须独立设计授权与确认流程。
- 复用现有认证、会话和 SSE 协议，不重构无关模块。
