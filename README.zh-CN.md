# OpenLair

![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-backend-009688?logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-agent%20runtime-1C3C3C)
![Vue](https://img.shields.io/badge/Vue-3-42B883?logo=vue.js&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-web-3178C6?logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-dev%20server-646CFF?logo=vite&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-local%20data-003B57?logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

> 一个人的全平台个人 AI 生活助理。

[English](README.md)

## 项目结构

```text
lair/
├── backend/        # FastAPI 服务端（源码在 app/ 包，参照官方 full-stack-fastapi-template 结构）
├── lairapp/        # Flutter 客户端（iOS/Android/macOS/Windows）
├── lairweb/        # Vue + TypeScript Web 管理后台
└── docs/           # 项目文档
```

## 模块规划

- **单词** — 间隔重复（SM-2）+ 多语言识别 + 对话式背诵。
- **记账** — 自然语言记账 + 分类统计。
- **日历** — 日程管理 + 提醒。
- **笔记** — 快速记录 + 总结。
- **习惯** — 打卡追踪。
- **主动助理** — 定时晨间回顾、晚间总结、单词提醒。

## 技术栈

| 组件 | 技术 |
|---|---|
| 服务端 | Python / FastAPI |
| 客户端 | Flutter |
| Web | Vue + TypeScript / Vite |
| 数据库 | SQLite |
| LLM | 多供应商 / 多模型，通过统一模型网关接入 |
| LLM 编排 | LangGraph |

后端架构细节见 [`docs/backend-architecture.md`](docs/backend-architecture.md)。

## 当前实现状态

- `backend/` 包含 FastAPI 后端：统一 `{code, message, data}` 信封 API、JWT 认证，以及基于 SQLAlchemy repositories + services 的记账/账本/待办/日历/笔记/习惯业务模块，配 Alembic 迁移。
- `lairweb/` 已有 Vue + TypeScript Web 控制台；开发环境跑在内存 mock 层（`lairweb/mock/`）上，mock 与 8001 端口真实后端的 API 契约完全一致，切换 Vite proxy 目标即可连上真实后端。

## 开发说明

已验证的本地命令和仓库工作流规则见 [`AGENTS.md`](AGENTS.md)。

## License

MIT
