# 软小筑 AI 管家

## 项目结构

- `frontend/`：React + TypeScript 前端页面
- `backend/`：FastAPI 后端与 AI 功能

## 本地启动

前端：进入 `frontend` 后运行 `pnpm install`，再运行 `pnpm dev`。

后端：在 `backend/` 中安装 `requirements.txt`，复制 `.env.example` 为 `.env` 并配置 PostgreSQL 连接，然后运行 `fastapi dev main.py`。

## 注册与登录

- 注册页和登录页由前端首页提供，可通过“立即登录 / 立即注册”切换。
- 后端使用 PostgreSQL 保存用户、会话与令牌数据，并在启动时启用 pgvector 扩展。
- 部署前，复制 `backend/.env.example` 为 `backend/.env`，设置 `DATABASE_URL` 与随机的 `AUTH_SECRET_KEY`。不要提交真实 `.env` 文件。
- 接口包括：`POST /api/auth/register`、`POST /api/auth/login`、`GET /api/auth/me`、`POST /api/auth/logout`。
