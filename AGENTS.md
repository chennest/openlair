# AGENTS.md

## 开工前必读（强制）

任何开发、调试、排错前，先确认环境配置，避免“改代码没效果 / 数据不对 / 连不上”的坑。

### 1. 先看前后端环境配置文件（不读就动手 = 违规）

- **前端**：读 `lairweb/.env.example`，并确认本地 `lairweb/.env`（或 `.env.local`）是否存在、`VITE_USE_MOCK` 当前为何值——这决定前端到底连内存 mock 还是真实后端。
- **后端**：确认 `backend/.env` 是否存在（缺失时从 `backend/.env.example` 复制创建）。`.env` 决定数据库连 SQLite 还是 MySQL、JWT 密钥等。当前本地 `backend/.env` 是从线上 k8s `configmap/openlair-env` 复制的**真实生产配置**（含真实密钥），已 gitignore，禁止提交、禁止外发。
- 所有 `.env` / `.env.local` 均被 gitignore，**不会提交**；改配置不会出现在 git diff 里，别奇怪。

### 2. Mock 是什么（前端）

`lairweb/mock/` 是前端的内存 mock 数据层（内存态 CRUD，重启恢复），API 契约与真实后端完全一致：

- `VITE_USE_MOCK=true`：Vite 挂载 `vite-plugin-mock-dev-server` 拦截 `/api` 返回假数据——**不启动后端也能开发前端**；改的是假数据，不产生真实业务数据。
- `VITE_USE_MOCK=false`：`/api` 经 Vite dev proxy 转发到真实后端（默认 8001）——调试真实接口/数据时用。

### 3. 三个前端环境变量

| 变量 | 作用 |
|---|---|
| `VITE_USE_MOCK` | mock 开关：`true`=走内存 mock（默认），`false`=走真实后端 |
| `VITE_API_BASE_URL` | 浏览器侧后端地址：留空=同源（靠 Vite proxy 转发）；填绝对地址=浏览器直连（后端需开 CORS） |
| `LAIRWEB_API_PROXY_TARGET` | Vite dev proxy 转发目标（仅 dev 生效），默认 `http://127.0.0.1:8001` |

- proxy 回退链：`LAIRWEB_API_PROXY_TARGET` → `VITE_API_BASE_URL` → `http://127.0.0.1:8001`（见 `vite.config.ts`）。

### 4. 常见坑

- 前端页面数据不对 → 先查 `.env` 的 `VITE_USE_MOCK`：改 mock 不生效 / 连不上后端，多半是开关与预期不符。
- 后端连错库 → 先查 `backend/.env` 的 `DATABASE_URL`。

## 当前状态

- `backend/` 是 FastAPI 后端：统一 `{code, message, data}` 信封、JWT 认证（register/login/logout/me）、基于 SQLAlchemy 仓储层 + 服务层的 ledger/books/todo/calendar/notes/habits/overview 业务模块。源码在 `backend/app/`（扁平布局，包名 `app`），参照官方 full-stack-fastapi-template 结构。
- `lairweb/` 是 Vue + TypeScript 管理台。开发模式下跑在内存 mock 层（`lairweb/mock/`）上；真实后端在 8001 端口提供完全一致的 API 契约，切换 Vite 代理目标即可连上真后端。
- 目前没有 CI 工作流、格式化配置、lint 配置或代码生成配置。不要发明本文件之外的新命令。
- 当前经过验证的权威来源是 `README.md` 和 `docs/backend-architecture.md`。

## 已验证命令

在 `backend/` 下执行（Python 环境由 `uv` 管理；`uv sync` 会自动下载 CPython 3.14.5 到 `.venv` 并写入 `uv.lock`）：

- 创建/重建本地虚拟环境并安装全部依赖：`uv sync`（dev 依赖：`uv sync --extra dev`）
- 运行后端测试（业务 API 测试套件每个用例使用独立的 SQLite 文件）：`uv run pytest`
- 启动本地后端开发服务（端口 8001）：`uv run uvicorn app.main:app --host 127.0.0.1 --port 8001`
- 数据库迁移（Alembic，在 `backend/` 下执行）：生成 `uv run alembic revision --autogenerate -m "..."`，应用 `uv run alembic upgrade head`，回退一步 `uv run alembic downgrade -1`。启动时的 `create_all` 仍会引导全新 SQLite；此后 schema 演进由迁移管理。
- 配置（`app/core/config.py`，pydantic-settings）读取优先级：进程环境变量 → `backend/.env` → 默认值。键：`OPENLAIR_JWT_SECRET`、`DATABASE_URL`。模板：`backend/.env.example`。

在 `lairweb/` 下执行（包管理统一用 pnpm）：

- 安装 web 依赖：`pnpm install`（或 `pnpm i`）
- 启动 Vue/Vite 开发服务：`pnpm run dev`
- 构建并做类型检查：`pnpm run build`
- 本地预览生产构建产物：`pnpm run preview`

环境说明：

- Python 由 `uv` 管理（自动安装 CPython 3.14.5；lockfile `backend/uv.lock`）。
- `.venv/`、`backend/.env`、`data/` 仅本机所有，已被 `.gitignore` 忽略。

## 计划边界

- `backend/`：Python/FastAPI 后端，核心大脑。
- `lairapp/`：Flutter 客户端，覆盖 iOS、Android、macOS、Windows。
- `lairweb/`：Vue + TypeScript web 管理台（Vite 构建）。浏览器侧 API 地址由 `.env`/`.env.local` 中的 `VITE_API_BASE_URL` 配置；本地同源代理时留空。Vite dev proxy 读取 `LAIRWEB_API_PROXY_TARGET` → `VITE_API_BASE_URL` → 默认 `http://127.0.0.1:8001`（环境配置详见顶部「开工前必读」）。
- `docs/`：项目文档。

## README 中的产品模块

- 词汇：SM-2 间隔重复、多语言识别、对话式背诵。
- 记账：自然语言记账与分类统计。
- 日历：日程管理与提醒。
- 笔记：快速记录与摘要。
- 习惯：打卡追踪。
- 主动助手：晨间回顾、晚间总结、词汇提醒。

## 对后续 AI 代理的工作指引

### 前端开发规范（强制读取）

**任何前端改动（含 AI 代理协作）都必须先读取 `docs/frontend/frontend-guide.md`，并严格遵守。**

- 前端代码风格、目录结构、命名规范、组件规范、API 封装、样式 token、mock 约定，全部以该文件为准。
- 项目文件风格同样遵循该文件：新增业务模块必须走 `src/modules/<模块>/` 目录（api.ts + index.vue + 子组件），禁止在单文件堆大页面。
- 目录结构速览：
  - `lairweb/src/modules/<模块>/` 业务模块目录
  - `lairweb/src/api/request.ts` 公共请求封装
  - `lairweb/src/components/` 通用组件（BaseModal、Tag）
  - `lairweb/mock/` mock 数据层（内存态 CRUD，重启恢复）

---

- 写代码前，先用真实的 manifest/配置初始化相关模块，然后把确切的命令记录到本文件。
- 新增任何构建、lint、类型检查、测试、代码生成、迁移或开发服务命令后，把已验证的命令及其工作目录更新到本文件。
- 按计划技术栈使用 SQLite（可通过 `DATABASE_URL` 换成 MySQL/PostgreSQL）和 SQLAlchemy；业务 API 契约是 `{ code, message, data }` + Bearer JWT，`lairweb/mock/` 与真实后端完全一致。
- 后端分层：`api/routes`（薄 HTTP）→ `services`（业务逻辑 + DTO）→ `repositories`（SQLAlchemy 持久化）→ `models`（ORM）。服务层保持不依赖 HTTP 可独立调用，仓储层是唯一的数据访问通道。
- JWT 密钥和数据库地址读取优先级：进程环境变量 → `backend/.env` → 默认值；模板是 `backend/.env.example`。
- 持久化统一走 SQLAlchemy 仓储层，不要直接用 `sqlite3` 调用，保证以后 SQLite 可平滑替换为其他 SQL 数据库。
- 提交纪律：每个完整功能实现并验证后创建一个 git 提交，保证工作可回退。一个完整功能可能跨多个文件；按完整功能边界提交，而不是按单个文件提交。
