# 软小筑 AI 管家 — 开发规范与指南

## 目录

1. [项目架构](#1-项目架构)
2. [技术栈](#2-技术栈)
3. [目录结构规范](#3-目录结构规范)
4. [命名规范](#4-命名规范)
5. [代码格式](#5-代码格式)
6. [前端开发规范](#6-前端开发规范)
7. [后端开发规范](#7-后端开发规范)
8. [Git 工作流](#8-git-工作流)
9. [环境配置](#9-环境配置)
10. [检查清单](#10-检查清单)

---

## 1. 项目架构

```
用户浏览器 (React SPA)
      │
      ├── HTTP/HTTPS ──► FastAPI 后端 (REST API)
      │                        │
      │                        ├── PostgreSQL (用户/会话/令牌)
      │                        ├── pgvector (向量检索 — 知识库)
      │                        └── AI 智能体服务 (后续扩展)
      │
      └── 静态资源 (Vite 开发服务器 / 生产构建)
```

### 分层架构（后端）

```
routers/          ← 路由层：定义 API 端点，处理 HTTP 请求/响应
    │
services/         ← 服务层：业务逻辑，调用数据库、外部服务
    │
schemas/          ← 数据层：Pydantic 模型，请求/响应校验
    │
database.py       ← 持久化层：数据库连接与表结构初始化
```

### 数据流

```
请求 → Router → Schema 校验 → Service 处理 → Database → Service → Router → 响应
```

---

## 2. 技术栈

| 层级     | 技术                                      | 版本 |
| -------- | ----------------------------------------- | ---- |
| 前端框架 | React                                     | 19.x |
| 类型系统 | TypeScript                                | 6.x  |
| 构建工具 | Vite                                      | 8.x  |
| UI 库    | Ant Design 5 + @ant-design/pro-components | 5.x  |
| 样式     | Tailwind CSS                              | 4.x  |
| 路由     | react-router-dom                          | 7.x  |
| 后端框架 | FastAPI                                   | 最新 |
| 数据库   | PostgreSQL + pgvector                     | 16+  |
| 认证     | JWT (HS256) + bcrypt/argon2 密码哈希      | —    |
| Python   | 3.12+                                     | —    |

---

## 3. 目录结构规范

### 3.1 顶层结构

```
ruanxiaozhu/
├── frontend/                # 前端项目（React SPA）
│   ├── src/
│   │   ├── layouts/         # 布局组件（壳组件，含导航/侧栏/底部）
│   │   ├── lib/             # 工具函数与 API 客户端
│   │   ├── pages/           # 页面组件（一个文件一个页面）
│   │   ├── types/           # TypeScript 类型定义
│   │   ├── App.tsx          # 根组件（路由、全局状态、Provider）
│   │   ├── main.tsx         # 入口文件
│   │   └── style.css        # 全局样式（Tailwind 导入 + 基础重置）
│   ├── public/              # 静态资源（图片、字体等）
│   ├── docs/                # 前端技术文档
│   ├── package.json
│   └── vite.config.ts       # Vite 配置
│
├── backend/                 # 后端项目（FastAPI）
│   ├── routers/             # API 路由（一篇 router 对应一个资源/领域）
│   ├── schemas/             # Pydantic 请求/响应模型
│   ├── services/            # 业务逻辑层
│   ├── main.py              # FastAPI 入口，CORS + 中间件 + 路由注册
│   ├── config.py            # 环境变量与全局配置
│   ├── database.py          # 数据库连接、初始化
│   ├── dependencies.py      # FastAPI 依赖注入（认证等）
│   ├── .env.example         # 环境变量模板
│   └── requirements.txt     # Python 依赖
│
├── docs/                    # 项目级文档（本文件所属目录）
├── README.md
├── CONTRIBUTING.md
└── .gitignore
```

### 3.2 文件组织原则

- **一个文件只做一件事**：一个页面文件只导出一个页面组件；一个 service 文件只负责一个领域（如 auth）。
- **按领域划分**：`routers/`、`schemas/`、`services/` 三个目录的拆分方式保持一致 — 新的业务领域需要同时在三个目录中添加对应文件。
- **公共逻辑抽取**：跨页面复用的逻辑放 `lib/`；跨 service 复用的放独立的工具模块。

---

## 4. 命名规范

### 4.1 文件命名

| 类型                | 规则                | 示例                                |
| ------------------- | ------------------- | ----------------------------------- |
| React 页面组件      | PascalCase          | `AuthPage.tsx`, `AiManagerPage.tsx` |
| React 布局组件      | PascalCase          | `AppLayout.tsx`                     |
| 工具/库文件         | camelCase           | `auth.ts`                           |
| TypeScript 类型文件 | camelCase（领域名） | `auth.ts`, `chat.ts`                |
| Python 模块         | snake_case          | `auth.py`, `chat.py`                |
| Python 包           | 全小写 + 短名字     | `routers/`, `schemas/`              |

### 4.2 代码命名

| 对象                    | 语言       | 规则             | 示例                                          |
| ----------------------- | ---------- | ---------------- | --------------------------------------------- |
| React 组件              | TypeScript | PascalCase       | `AuthPage`, `AppLayout`                       |
| React Props 类型        | TypeScript | 组件名 + `Props` | `type AuthPageProps = { ... }`                |
| 普通函数/工具函数       | TypeScript | camelCase        | `getStoredAccessToken`, `saveTokens`          |
| 事件处理函数            | TypeScript | `handle` + 动作  | `handleLogout`, `handleSubmit`                |
| 常量                    | TypeScript | UPPER_SNAKE      | `API_BASE`, `ACCESS_TOKEN_KEY`                |
| Python 函数             | Python     | snake_case       | `register_user`, `get_current_user`           |
| Python 类/Pydantic 模型 | Python     | PascalCase       | `RegisterRequest`, `UserResponse`             |
| Python 常量             | Python     | UPPER_SNAKE      | `DATABASE_URL`, `ACCESS_TOKEN_EXPIRE_MINUTES` |

### 4.3 数据库命名

| 对象   | 规则                  | 示例                        |
| ------ | --------------------- | --------------------------- |
| 表名   | 小写 + 下划线（复数） | `users`, `auth_sessions`    |
| 列名   | 小写 + 下划线         | `created_at`, `refresh_jti` |
| 主键   | `id`                  | —                           |
| 时间列 | `_at` 后缀            | `created_at`, `expires_at`  |
| 外键   | `表名_id`             | `user_id`                   |

### 4.4 API 端点命名

| 规则                  | 示例                                        |
| --------------------- | ------------------------------------------- |
| URL 用名词复数 + 小写 | `/api/auth/register`, `/api/auth/me`        |
| 用 HTTP 方法区分操作  | `POST /register`, `GET /me`, `POST /logout` |

---

## 5. 代码格式

### 5.1 TypeScript / React

- **缩进**：2 空格
- **引号**：单引号 `'`
- **分号**：不写（项目当前风格）
- **逗号**：尾随逗号（对象/数组最后一项后面加逗号）
- **行宽**：不超过 120 字符
- **类型注解**：优先使用 `type` 定义，不用 `interface`（除非需要 extend）

```typescript
// ✅ 推荐
export type User = {
    id: string;
    email: string;
};

type Props = { user: User; onLogout: () => void };

// ❌ 避免
export interface User {
    id: string;
    email: string;
}
```

- **组件导出**：使用命名导出（`export function`），`App.tsx` 本身用默认导出

```typescript
// ✅ 推荐
export function AuthPage({ onAuthenticated }: Props) { ... }

// App.tsx 例外：作为根组件使用默认导出
function App() { ... }
export default App
```

- **导入顺序**（空行分隔组）：
    1. React 核心（`react`, `react-dom`）
    2. 第三方 UI 库（`antd`, `@ant-design/...`）
    3. 第三方工具库（`react-router-dom`）
    4. 项目内部模块（`../lib/...`, `../types/...`）

### 5.2 Python

- **缩进**：4 空格
- **引号**：双引号 `"`（字符串内容含双引号时可单引号）
- **行宽**：不超过 100 字符
- **函数与类之间**：两个空行（顶层定义之间）
- **方法之间**：一个空行
- **类型注解**：所有函数参数和返回值必须标注类型

```python
# ✅ 推荐
def register_user(data: RegisterRequest) -> UserResponse:
    ...

# ❌ 避免
def register_user(data):
    ...
```

- **导入顺序**（空行分隔组）：
    1. 标准库
    2. 第三方库
    3. 项目内部模块

### 5.3 补充规则

- 终端不输出 `print` 日志 — 使用 `logging` 模块。
- 不在代码中硬编码密钥、URL 或密码 — 一律走环境变量或 `config.py`。

---

## 6. 前端开发规范

### 6.1 新增页面

1. 在 `frontend/src/pages/` 下新建 `XxxPage.tsx`
2. 使用命名导出：`export function XxxPage() { ... }`
3. 页面组件的 Props 类型定义在组件文件顶部（不单独放 types/）
4. 如果页面有自己的子组件，在 `frontend/src/pages/` 或 `components/` 下建子目录
5. 在 `App.tsx` 中注册路由

```typescript
// pages/XxxPage.tsx
type Props = { userId?: string }

export function XxxPage({ userId }: Props) {
  return <main>...</main>
}
```

### 6.2 API 调用

- 所有 API 调用集中在 `lib/` 目录的领域文件中（目前是 `auth.ts`，后续新增 `chat.ts` 等）。
- 基础 URL 统一定义为常量 `API_BASE`（后续改用环境变量）。
- 错误处理统一走 `getApiError()` 提取后端返回的 `detail`。

```typescript
// ✅ 推荐：封装到 lib/xxx.ts
const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8000'

export async function sendMessage(message: string): Promise<string> {
  const response = await fetch(`${API_BASE}/api/chat`, { ... })
  ...
}
```

```typescript
// ❌ 避免：在页面组件中直接散落 fetch
const response = await fetch('http://127.0.0.1:8000/api/chat', { ... })
```

### 6.3 组件设计

- **布局组件 vs 页面组件**：
    - 布局组件（`layouts/`）：提供导航壳，通过 `<Outlet />` 渲染子页面
    - 页面组件（`pages/`）：具体的业务页面内容
- **状态管理**：当前项目规模使用 React `useState` + `useEffect`，暂不引入全局状态库（需引入时评估 Redux/Zustand）。
- **加载状态**：所有异步操作要有 loading 和 error 状态，不能静默失败。

```typescript
const [loading, setLoading] = useState(false)
const [error, setError] = useState('')
// 渲染时：
if (loading) return <Spin />
if (error) return <Alert type="error" message={error} />
```

### 6.4 样式

- **优先 Tailwind 原子类**，避免写自定义 CSS。
- 自定义样式只在 `style.css` 中写全局重置或 Tailwind 无法覆盖的场景。
- 颜色使用 Tailwind 内置色板（`slate-50`, `indigo-500` 等），与 Ant Design 主题色 `#4f6cff` 保持协调。

---

## 7. 后端开发规范

### 7.1 新增 API 端点

每个领域需要三部分，按以下模板新增：

#### Step 1：定义 Schema（`schemas/xxx.py`）

```python
from pydantic import BaseModel, Field

class XxxRequest(BaseModel):
    field_name: str = Field(min_length=1, max_length=200)

class XxxResponse(BaseModel):
    id: str
    field_name: str
```

#### Step 2：实现 Service（`services/xxx.py`）

```python
from schemas.xxx import XxxRequest, XxxResponse

def do_something(data: XxxRequest) -> XxxResponse:
    # 业务逻辑
    ...
```

#### Step 3：注册路由（`routers/xxx.py`）

```python
from typing import Annotated
from fastapi import APIRouter, Depends
from dependencies import get_current_user
from schemas.xxx import XxxRequest, XxxResponse
from schemas.auth import UserResponse
from services.xxx import do_something

router = APIRouter(prefix="/api/xxx", tags=["xxx"])

@router.post("/action", response_model=XxxResponse)
def action(
    data: XxxRequest,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> XxxResponse:
    return do_something(data)
```

#### Step 4：在 `main.py` 中注册

```python
from routers import xxx
app.include_router(xxx.router)
```

### 7.2 错误处理

- 业务异常统一用 `HTTPException`，指定合适的 HTTP 状态码和中文 `detail` 消息。
- 不要返回原始数据库错误给客户端。

```python
# ✅ 推荐
raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识库不存在")

# ❌ 避免
return {"error": str(db_error)}
```

### 7.3 数据库操作

- 数据库操作走 `services/` 层，不要直接在 `routers/` 中操作数据库。
- 每次操作使用 `get_connection()` 获取连接，用完后 `with` 语句自动关闭。
- SQL 参数化查询，**禁止字符串拼接 SQL**。

```python
# ✅ 推荐
cursor.execute("SELECT * FROM users WHERE email = %s", (email,))

# ❌ 禁止
cursor.execute(f"SELECT * FROM users WHERE email = '{email}'")
```

### 7.4 认证与权限

- 需要登录的端点使用 Depends 注入 `get_current_user`。
- 公开端点直接声明，不加 `current_user` 依赖。
- 令牌前缀必须为 `Bearer`。

---

## 8. Git 工作流

### 8.1 分支策略

| 分支       | 用途                      |
| ---------- | ------------------------- |
| `main`     | 始终可运行的生产/演示分支 |
| `feat/xxx` | 新功能开发                |
| `fix/xxx`  | Bug 修复                  |

### 8.2 提交信息格式

遵循 Conventional Commits（与现有 CONTRIBUTING.md 一致）：

```text
feat: 简短描述（中文，不超过 72 字符）
fix: 简短描述
docs: 简短描述
chore: 简短描述
refactor: 简短描述
```

- 一条提交只做一件事。
- 提交前确保前端能 `build`、后端能 `fastapi dev main.py` 启动。
- **不提交** `.env`、`node_modules`、`__pycache__`、密码、令牌。

### 8.3 合并前检查

- [ ] `npm run build` 通过
- [ ] 后端语法无错误
- [ ] API 变更同步更新了 `.env.example` 和相关文档
- [ ] 新增依赖已加入 `package.json` 或 `requirements.txt`

---

## 9. 环境配置

### 9.1 必需环境变量（backend/.env）

```env
DATABASE_URL=postgresql://用户名:密码@主机:端口/数据库名
AUTH_SECRET_KEY=至少32字符的随机密钥
```

### 9.2 本地开发流程

```bash
# 1. 后端
cd backend
cp .env.example .env          # 编辑 .env 填入真实配置
pip install -r requirements.txt
fastapi dev main.py            # 默认 http://127.0.0.1:8000

# 2. 前端（新终端）
cd frontend
npm install
npm run dev                    # 默认 http://127.0.0.1:5173
```

### 9.3 常用命令速查

| 操作                  | 命令                                          |
| --------------------- | --------------------------------------------- |
| 前端开发服务器        | `cd frontend && npm run dev`                  |
| 前端生产构建          | `cd frontend && npm run build`                |
| 后端开发服务器        | `cd backend && fastapi dev main.py`           |
| 安装新前端依赖        | `cd frontend && npm install <pkg>`            |
| 安装新后端依赖        | `cd backend && pip install <pkg>`             |
| 更新 requirements.txt | `cd backend && pip freeze > requirements.txt` |

> 注意：更新 `requirements.txt` 前需要过滤掉不需要的依赖，保持文件精简。

---

## 10. 检查清单

新增功能时，按以下顺序完成：

### 后端

- [ ] 定义 Pydantic Schema（`schemas/xxx.py`）
- [ ] 实现 Service 逻辑（`services/xxx.py`）
- [ ] 编写 Router（`routers/xxx.py`）
- [ ] 在 `main.py` 注册路由
- [ ] 需要认证时注入 `get_current_user`
- [ ] 需要新增数据库表时在 `database.py` 的 `init_database()` 中添加
- [ ] 手动测试端点（curl 或 Swagger UI `http://127.0.0.1:8000/docs`）

### 前端

- [ ] 在 `types/` 中定义接口类型
- [ ] 在 `lib/` 中封装 API 调用函数
- [ ] 在 `pages/` 中创建页面组件
- [ ] 在 `App.tsx` 中注册路由
- [ ] 处理 loading / error / empty 三种状态
- [ ] 新增依赖时确认与现有版本兼容

### 共同

- [ ] 新增环境变量时同步更新 `.env.example`
- [ ] 提交信息符合 Conventional Commits 格式
- [ ] 不提交敏感信息
