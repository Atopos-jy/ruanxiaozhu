# 软小筑 AI 管家 — 系统设计文档

## 版本

| 版本 | 日期       | 作者 | 说明     |
| ---- | ---------- | ---- | -------- |
| 0.1  | 2026-07-17 | —    | 初稿     |
| 0.2  | 2026-07-20 | —    | 补充 LangGraph Agent 学习与实施路线 |

---

## 目录

1. [概述](#1-概述)
2. [系统架构](#2-系统架构)
3. [技术选型](#3-技术选型)
4. [数据模型设计](#4-数据模型设计)
5. [智能体框架设计](#5-智能体框架设计)
6. [API 接口设计](#6-api-接口设计)
7. [前端架构设计](#7-前端架构设计)
8. [安全设计](#8-安全设计)
9. [部署架构](#9-部署架构)

---

## 1. 概述

### 1.1 项目定位

软小筑 AI 管家是一个面向企业与个人用户的**智能体平台**。用户可以与多种 AI 智能体（通用助手、知识库诊断、销售专家等）进行对话，智能体能够调用工具（搜索、计算、知识库检索）完成复杂任务。

### 1.2 核心功能

| 模块         | 说明                                      | 优先级 |
| ------------ | ----------------------------------------- | ------ |
| 用户认证     | 注册、登录、Token 刷新、登出              | P0 ✅  |
| AI 管家对话  | 通用智能助手，支持工具调用和流式输出      | P0     |
| 知识库诊断   | 企业知识库建设必要性分析                  | P1     |
| 销售专家     | 销售策略顾问                              | P1     |
| 智能体市场   | 浏览、启用/禁用智能体                     | P2     |
| 知识库管理   | 文档上传、向量化、检索                    | P2     |

### 1.3 设计原则

- **前后端分离**：React SPA ↔ FastAPI REST API，通过 JWT Bearer Token 认证
- **智能体可插拔**：新增一个智能体 = 注册 Agent 类 + 配系统提示词，无需改基础设施
- **安全优先**：密码 Argon2 哈希、SQL 参数化查询、JWT 令牌吊销
- **渐进增强**：先实现核心通路，再扩展工具和智能体

---

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────┐
│                      客户端层                             │
│  ┌─────────────────────────────────────────────────┐    │
│  │  React 19 SPA (Vite 8)                          │    │
│  │  ├── AuthPage        (登录/注册)                 │    │
│  │  ├── AgentChatPage   (智能体对话，SSE 流式接收)   │    │
│  │  ├── AppLayout       (侧栏导航 + 智能体列表)      │    │
│  │  └── lib/sse.ts      (SSE 流解析器)              │    │
│  └─────────────────────────────────────────────────┘    │
│                          │ HTTP/SSE                       │
└──────────────────────────┼──────────────────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────┐
│                      服务层                               │
│  ┌─────────────────────────────────────────────────┐    │
│  │  FastAPI 后端 (Python 3.12+)                     │    │
│  │                                                  │    │
│  │  routers/                                        │    │
│  │  ├── auth.py      POST /api/auth/*               │    │
│  │  ├── chat.py      POST /api/chat (SSE)           │    │
│  │  └── agent.py     GET  /api/agents               │    │
│  │                                                  │    │
│  │  services/                                       │    │
│  │  ├── auth.py          认证逻辑                    │    │
│  │  ├── chat_service.py  智能体编排 + 流式输出       │    │
│  │  └── conversation_service.py  对话/消息 CRUD     │    │
│  │                                                  │    │
│  │  agents/                  智能体定义               │    │
│  │  ├── base.py             BaseAgent ABC           │    │
│  │  ├── general_assistant.py  AI管家                │    │
│  │  ├── knowledge_diagnosis.py  知识库诊断           │    │
│  │  └── sales_expert.py    销售专家                 │    │
│  │                                                  │    │
│  │  tools/                  工具定义                 │    │
│  │  ├── web_search.py                               │    │
│  │  ├── calculator.py                               │    │
│  │  ├── date_time.py                                │    │
│  │  └── knowledge_search.py                         │    │
│  └─────────────────────────────────────────────────┘    │
│                          │                               │
└──────────────────────────┼──────────────────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────┐
│                      数据层                               │
│  ┌─────────────────────────────────────────────────┐    │
│  │  PostgreSQL 16+ + pgvector                       │    │
│  │  ├── users               用户表                  │    │
│  │  ├── auth_sessions       会话表                  │    │
│  │  ├── revoked_tokens      令牌吊销表              │    │
│  │  ├── conversations       对话表                  │    │
│  │  └── messages            消息表                  │    │
│  └─────────────────────────────────────────────────┘    │
│                          │                               │
│  ┌─────────────────────────────────────────────────┐    │
│  │  外部服务                                        │    │
│  │  ├── LLM API  (DeepSeek / 通义千问 / 智谱 GLM)   │    │
│  │  └── Web Search API (Tavily / 后续)              │    │
│  └─────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────┘
```

### 2.2 请求流程（以智能体对话为例）

```
1. 用户输入消息 → POST /api/chat (SSE)
2. Router (chat.py) → 验证 JWT → 调用 chat_service.stream_chat()
3. chat_service:
   a. 从 AGENT_REGISTRY 获取智能体实例
   b. 构建 AgentState { messages: [SystemMessage, HumanMessage] }
   c. 调用 graph.astream(state)
   d. 将 LangGraph 节点输出转为 SSE 事件流
4. LangGraph 内部:
   a. call_model → LLM 决定回复或调工具
   b. 若调工具 → execute_tools → call_model (循环)
   c. 若直接回复 → END
5. 前端 SSE 逐事件渲染:
   message → 追加文本到气泡
   tool_call → 显示"正在调用 xxx 工具…"
   done → 标记完成
6. chat_service 结束后 → 消息写入 messages 表
```

---

## 3. 技术选型

### 3.1 后端

| 组件       | 技术                    | 选型理由                                         |
| ---------- | ----------------------- | ------------------------------------------------ |
| Web 框架   | FastAPI                 | 高性能异步、原生 SSE 支持、自动 OpenAPI 文档生成  |
| 数据库驱动 | psycopg 3               | PostgreSQL 官方推荐驱动，支持 async、dict_row    |
| ORM        | **不使用 ORM**          | 项目规模适中，raw SQL 更灵活、可审计、无 N+1 隐患 |
| 认证       | PyJWT + pwdlib (Argon2) | 自包含 Token、无状态验证、Argon2 防 GPU 暴力破解  |
| AI 框架    | LangChain + LangGraph   | 成熟的工具调用模式、图式状态管理、可观测性       |
| LLM 对接   | langchain-openai        | 兼容 OpenAI API 格式，国内模型均可通过 base_url 对接 |

> **关于 Prisma**：Prisma 是 Node.js/TypeScript 生态的 ORM，不适用于 Python/FastAPI 后端。若未来团队倾向于 Node.js 全栈，可评估迁移至 NestJS + Prisma，但当前 Python 技术栈在 AI/ML 生态上有显著优势（LangChain、pgvector、科学计算库等）。

### 3.2 前端

| 组件     | 技术                     | 选型理由                               |
| -------- | ------------------------ | -------------------------------------- |
| 框架     | React 19                 | 生态成熟、SSE 消费方便                  |
| 类型     | TypeScript 6             | 类型安全                               |
| 构建     | Vite 8                   | 极速 HMR、原生 ESM                     |
| UI 库    | Ant Design 5 + Pro       | 企业级组件、中文友好                    |
| 样式     | Tailwind CSS 4           | 原子化 CSS，与 Ant Design 主题色兼容   |
| 路由     | react-router-dom 7       | 声明式路由、布局嵌套                   |
| SSE 消费 | 原生 ReadableStream API  | 零依赖、精确控制流解析                 |

### 3.3 数据库

| 组件         | 技术                  | 选型理由                     |
| ------------ | --------------------- | ---------------------------- |
| 关系数据库   | PostgreSQL 16+        | 成熟稳定、JSONB 支持         |
| 向量扩展     | pgvector              | 与 PostgreSQL 深度集成       |
| 连接管理     | psycopg 连接池（内置）| 足够当前规模，后续可升级     |

---

## 4. 数据模型设计

### 4.1 Entity-Relationship

```
users ──1:N──→ auth_sessions
  │
  └──1:N──→ conversations ──1:N──→ messages

revoked_tokens (独立，仅关联 JWT jti)
```

### 4.2 表结构

#### users

| 列            | 类型          | 约束        | 说明         |
| ------------- | ------------- | ----------- | ------------ |
| id            | UUID          | PK          | 用户唯一标识 |
| email         | TEXT          | UNIQUE, NOT NULL | 邮箱    |
| password_hash | TEXT          | NOT NULL    | Argon2 哈希  |
| created_at    | TIMESTAMPTZ   | NOT NULL    | 注册时间     |
| last_login_at | TIMESTAMPTZ   |             | 最后登录时间 |

#### auth_sessions

| 列                 | 类型        | 约束            | 说明                    |
| -------------------- | ----------- | --------------- | ----------------------- |
| id                   | UUID        | PK              | 会话 ID                |
| user_id              | UUID        | FK → users.id   | 所属用户               |
| refresh_jti          | UUID        | UNIQUE, NOT NULL | 当前有效的 refresh JTI |
| created_at           | TIMESTAMPTZ | NOT NULL        | 会话创建时间           |
| expires_at           | TIMESTAMPTZ | NOT NULL        | 会话绝对过期时间       |
| refresh_expires_at   | TIMESTAMPTZ | NOT NULL        | refresh token 滑动窗口 |
| revoked_at           | TIMESTAMPTZ |                 | 吊销时间（NULL=有效）  |

#### revoked_tokens

| 列         | 类型        | 约束 | 说明               |
| ---------- | ----------- | ---- | ------------------ |
| jti        | UUID        | PK   | 被吊销的 JWT ID    |
| expires_at | TIMESTAMPTZ | NOT NULL | 令牌原始过期时间  |
| revoked_at | TIMESTAMPTZ | NOT NULL | 吊销时间           |

#### conversations

| 列         | 类型        | 约束            | 说明                       |
| ---------- | ----------- | --------------- | -------------------------- |
| id         | UUID        | PK              | 对话 ID                    |
| user_id    | UUID        | FK → users.id   | 所属用户                   |
| agent_id   | TEXT        | NOT NULL        | 智能体标识（如 "general-assistant"） |
| title      | TEXT        |                 | 对话标题（取自首条消息前50字） |
| created_at | TIMESTAMPTZ | NOT NULL        | 创建时间                   |
| updated_at | TIMESTAMPTZ | NOT NULL        | 最后消息时间               |

索引：`idx_conversations_user ON (user_id, updated_at DESC)`

#### messages

| 列               | 类型        | 约束                    | 说明                        |
| ---------------- | ----------- | ----------------------- | --------------------------- |
| id               | UUID        | PK                      | 消息 ID                     |
| conversation_id  | UUID        | FK → conversations.id   | 所属对话                    |
| role             | TEXT        | CHECK (user/assistant/system/tool) | 消息角色      |
| content          | TEXT        | NOT NULL                | 消息正文                    |
| tool_calls       | JSONB       |                         | 工具调用记录（仅 assistant） |
| created_at       | TIMESTAMPTZ | NOT NULL                | 发送时间                    |

索引：`idx_messages_conversation ON (conversation_id, created_at)`

### 4.3 数据流

```
用户注册:
  POST /api/auth/register
  → INSERT INTO users

用户登录:
  POST /api/auth/login
  → SELECT FROM users (验证密码)
  → UPDATE users SET last_login_at
  → INSERT INTO auth_sessions
  → 返回 JWT pair

智能体对话:
  POST /api/chat
  → INSERT INTO conversations (首次)
  → LangGraph agent 运行
  → INSERT INTO messages (user + assistant)
  → 返回 SSE 流
```

---

## 5. 智能体框架设计

### 5.1 核心抽象

```
BaseAgent (ABC)
  ├── meta: AgentMeta           # 元信息（名称、描述、图标）
  ├── build_graph(): StateGraph # 编译 LangGraph 状态图
  └── get_tools(): list         # 返回该智能体可用的工具列表
```

### 5.2 LangGraph 图结构

```
         ┌──────────────────────┐
         │     call_model       │  ← LLM 调用（绑定工具）
         │  接收消息，返回回复    │
         └──────┬───────────────┘
                │
         ┌──────▼───────────────┐
         │ 有 tool_calls?       │  ← 条件判断
         └──┬────────────┬──────┘
            │ 是         │ 否
    ┌───────▼──────┐    │
    │ execute_tools │    │  → END（输出回复）
    │ 执行工具调用    │    │
    └───────┬──────┘    │
            │           │
            └──→ 循环 ──┘
```

### 5.3 工具系统

每个工具是 `@tool` 装饰的函数，返回字符串：

```python
@tool
def web_search(query: str) -> str:
    """搜索互联网获取最新信息。当需要实时数据或用户询问近期事件时使用。"""
    # 调用搜索 API
    return "搜索结果摘要..."
```

工具在 `tools/__init__.py` 汇总为 `ALL_TOOLS`，各智能体按需选择子集。

### 5.4 LLM 抽象

```python
# llm.py — 工厂函数，支持所有 OpenAI 兼容 API
def create_llm(**overrides) -> ChatOpenAI:
    return ChatOpenAI(
        model=LLM_MODEL,        # deepseek-chat / qwen-plus / glm-4
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL,  # https://api.deepseek.com/v1
        temperature=LLM_TEMPERATURE,
        streaming=True,
    )
```

### 5.5 新增智能体流程

```
1. 创建 agents/my_agent.py → 继承 BaseAgent
2. 在 agents/__init__.py → AGENT_REGISTRY["my-agent"] = MyAgent()
3. 在 chat_service.py → SYSTEM_PROMPTS["my-agent"] = "..."
4. 在 App.tsx → <Route path="/robot/my-agent" element={<AgentChatPage agentId="my-agent" />} />
5. 在 AppLayout.tsx → agents 数组追加条目
```

**不需要**：数据库迁移、新表、新路由、新 service。

---

## 6. API 接口设计

### 6.1 认证相关（已实现）

| 方法   | 端点                  | 说明                    | 认证 |
| ------ | --------------------- | ----------------------- | ---- |
| POST   | /api/auth/register    | 注册新用户              | 否   |
| POST   | /api/auth/login       | 登录，返回 Token 对     | 否   |
| POST   | /api/auth/refresh     | 刷新 Token              | 否   |
| GET    | /api/auth/me          | 获取当前用户信息        | 是   |
| POST   | /api/auth/logout      | 登出，吊销 Token        | 否   |

### 6.2 智能体相关（待实现）

| 方法   | 端点                         | 说明                      | 认证 | 响应类型       |
| ------ | ---------------------------- | ------------------------- | ---- | -------------- |
| POST   | /api/chat                    | 发送消息，流式返回        | 是   | SSE 流         |
| GET    | /api/agents                  | 列出所有可用智能体        | 否   | JSON           |
| GET    | /api/conversations           | 获取当前用户的对话列表    | 是   | JSON           |
| GET    | /api/conversations/{id}      | 获取对话详情              | 是   | JSON           |
| GET    | /api/conversations/{id}/messages | 获取对话历史消息      | 是   | JSON           |

### 6.3 SSE 事件规范

```
event: message
data: {"content": "你好"}

event: tool_call
data: {"tool": "web_search", "args": {"query": "最新AI趋势"}}

event: tool_result
data: {"tool": "web_search", "result": "搜索结果: ..."}

event: done
data: {"conversation_id": "uuid"}

event: error
data: {"detail": "错误描述"}
```

### 6.4 HTTP 状态码规范

| 状态码 | 场景                               |
| ------ | ---------------------------------- |
| 200    | 成功                               |
| 201    | 创建成功（注册）                   |
| 204    | 成功但无响应体（登出）             |
| 400    | 请求参数校验失败                   |
| 401    | 未认证或 Token 无效                |
| 409    | 资源冲突（邮箱已注册）             |
| 422    | Pydantic 校验失败（FastAPI 自动）  |
| 500    | 服务器内部错误                     |

---

## 7. 前端架构设计

### 7.1 组件树

```
<App>
  ├── [未登录] <AuthPage />               # 登录/注册
  └── [已登录] <BrowserRouter>
        └── <AppLayout>                   # 侧栏导航壳
              ├── <Sidebar>
              │     ├── NavItems          # AI管家、智能体、知识库
              │     ├── MyAgents          # 智能体列表
              │     └── UserFooter        # 用户信息 + 退出
              └── <Outlet />
                    ├── /robot/chat        → <AgentChatPage agentId="general-assistant" />
                    ├── /robot/knowledge-diagnosis → <AgentChatPage agentId="knowledge-diagnosis" />
                    ├── /robot/sales-expert → <AgentChatPage agentId="sales-expert" />
                    ├── /app               → <EmptyPage />
                    └── /document          → <EmptyPage />
```

### 7.2 AgentChatPage 内部结构

```
<AgentChatPage>
  ├── <ConversationList />       # 左侧对话历史（可折叠）
  │     ├── "新对话" 按钮
  │     └── 对话列表（标题 + 时间）
  └── <ChatArea>                 # 右侧聊天区
        ├── <MessageList>        # 消息列表（可滚动）
        │     ├── <ChatMessage /> # 用户消息气泡（右对齐，indigo）
        │     ├── <ChatMessage /> # AI 消息气泡（左对齐，白色）
        │     └── <ToolCallCard /># 工具调用卡片（内联、可展开）
        └── <ChatInput />        # 底部输入栏（固定）
              ├── TextArea
              └── 发送按钮（支持 Enter 发送）
```

### 7.3 状态流转

```
[空闲] → 用户输入 → [流式接收中]
  │                      │
  │  SSE message → 追加文本到气泡
  │  SSE tool_call → 显示工具调用卡片
  │  SSE done → 回到 [空闲]，刷新对话列表
  │  SSE error → 显示错误提示，回到 [空闲]
  └──────────────────────┘
```

### 7.4 SSE 消费实现

```typescript
// lib/sse.ts — 基于 ReadableStream 的 SSE 解析器
export async function* streamChat(
  message: string,
  agentId: string,
  conversationId?: string,
): AsyncGenerator<SSEEvent> {
  const response = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${getStoredAccessToken()}`,
    },
    body: JSON.stringify({ message, agent_id: agentId, conversation_id: conversationId }),
  })
  // 逐行读取 SSE 流，解析 event: xxx + data: xxx
  // 通过 AsyncGenerator yield 给 React 组件逐事件消费
}
```

---

## 8. 安全设计

### 8.1 认证机制

```
Access Token (30min) + Refresh Token (滑动窗口 7 天，绝对过期 30 天)

┌─────────┐                    ┌─────────┐
│ 客户端    │                    │ 服务端    │
└────┬────┘                    └────┬────┘
     │ POST /login                  │
     │─────────────────────────────→│ 验证密码
     │←─────────────────────────────│ 返回 Access + Refresh
     │                              │
     │ GET /api/auth/me             │
     │─────────────────────────────→│ 验证 Access Token
     │←─────────────────────────────│ 返回用户信息
     │                              │
     │ (Access Token 即将过期)       │
     │ POST /api/auth/refresh       │
     │─────────────────────────────→│ 验证 Refresh Token
     │←─────────────────────────────│ 返回新 Token 对 (滚动刷新)
     │                              │
     │ POST /api/auth/logout        │
     │─────────────────────────────→│ 吊销 Access Token (加入黑名单)
     │                              │ 吊销 Session (设置 revoked_at)
     │←─────────────────────────────│ 204 No Content
```

### 8.2 安全检查清单

- [x] 密码 Argon2 哈希，不存储明文
- [x] 用户不存在时仍执行哈希验证（防止时序攻击）
- [x] SQL 参数化查询，禁止字符串拼接
- [x] CORS 限制：仅允许 `localhost` / `127.0.0.1`
- [x] Access Token 短有效期（30 分钟）
- [x] Refresh Token 滑动窗口 + 绝对过期
- [x] 登出时吊销 Token（JTI 黑名单）
- [ ] 速率限制（后续加）
- [ ] 请求日志与审计（后续加）

---

## 9. 部署架构

### 9.1 开发环境

```
终端 1: cd backend && fastapi dev main.py     → :8000
终端 2: cd frontend && npm run dev              → :5173
```

### 9.2 生产环境（规划）

```
                    ┌──────────────┐
                    │  Nginx / CDN │  ← 静态资源 + 反向代理
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
     ┌───────▼──────┐  ┌──▼──────────┐  │
     │ 前端静态文件   │  │ Uvicorn     │  │
     │ (Vite build)  │  │ (FastAPI)   │  │
     └──────────────┘  └──┬──────────┘  │
                          │              │
                   ┌──────▼──────┐      │
                   │ PostgreSQL  │      │
                   │ (+ pgvector)│      │
                   └─────────────┘      │
                                        │
                   ┌────────────────────▼──┐
                   │ LLM API (外部)        │
                   │ DeepSeek / 通义千问   │
                   └───────────────────────┘
```

建议配置：
- Uvicorn workers = CPU 核心数 × 2
- PostgreSQL 连接池大小 = workers × 2
- 前端静态资源走 CDN 或 Nginx `try_files`
- HTTPS 通过 Nginx 终止

---

## 附录 A：与 Prisma 的对比说明

本项目选择 **psycopg + raw SQL** 而非 Prisma ORM，原因如下：

| 维度       | psycopg + raw SQL              | Prisma                         |
| ---------- | ------------------------------ | ------------------------------ |
| 语言       | Python 原生                    | TypeScript/Node.js             |
| 生态适配   | 完美适配 FastAPI + LangChain   | 与 Python 不兼容               |
| 查询灵活性 | 完全控制 SQL，无抽象泄露       | 声明式 API，复杂查询需 raw SQL |
| 迁移管理   | 手动管理（`init_database()`）  | 自动化迁移 (`prisma migrate`)  |
| AI 生态    | 直接对接 pgvector、numpy 等    | 通过 Prisma Client 抽象        |
| 学习成本   | 需要 SQL 知识                  | 需要学习 Prisma Schema 语法    |

如果未来团队决定迁移至 Node.js 全栈架构，Prisma 是首选 ORM。届时可按以下路径迁移：

```
1. 编写 schema.prisma 定义数据模型
2. prisma migrate dev 生成迁移
3. 逐模块迁移 router → controller，service → prisma 查询
4. 前端无需变动（API 接口不变）
```
