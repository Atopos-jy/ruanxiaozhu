# 贡献指南

## 提交前检查

- 不提交 `.env`、密码、访问令牌、数据库文件或其他个人数据。
- 后端在 `backend/` 中执行依赖安装后，应能通过 Python 语法检查。
- 前端在 `frontend/` 中应能执行 `pnpm build`。
- 修改 API、部署方式或环境变量时，同步更新 `README.md` 与 `.env.example`。

## 提交信息

使用简短的 Conventional Commits 格式：

```text
feat: 添加知识库文档接口
fix: 修复刷新令牌校验
docs: 更新 PostgreSQL 部署说明
chore: 更新开发依赖
```

一次提交只处理一个明确目的；不要混合无关的格式化、重构和功能修改。

## 分支与合并

- `main` 保持可运行。
- 功能使用 `feat/` 前缀，修复使用 `fix/` 前缀。
- 合并前应通过 CI，并在 PR 中说明测试方式与环境变量变更。
