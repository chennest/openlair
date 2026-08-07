# AGENTS.md

## Current state

- `lairservice/` contains the FastAPI + LangGraph agent harness runtime plus the full business API: unified `{code, message, data}` envelope, JWT auth (register/login/logout/me), ledger/books/todo/calendar/notes/habits/overview modules over SQLAlchemy repositories + services.
- `lairweb/` contains the Vue + TypeScript web admin console. In dev it runs against the in-memory mock layer (`lairweb/mock/`); the real backend on port 8001 serves the identical API contract, so switching means pointing the Vite proxy at it.
- There are no CI workflows, formatter configs, lint configs, or codegen configs yet. Do not invent commands beyond those listed here.
- `README.md` and `docs/backend-architecture.md` are the verified project sources of truth at the moment.

## Verified commands

Run these from `lairservice/` (Python environment is managed by `uv`; `uv sync` auto-downloads CPython 3.14.5 into `.venv` and writes `uv.lock`):

- Create/recreate the local venv and install all deps: `uv sync`（dev 依赖：`uv sync --extra dev`）
- Run backend tests (business API suite uses an isolated SQLite file per test; the real-model integration tests additionally need valid `~/.openlair/openlair.json` + `~/.openlair/.env` credentials): `uv run pytest`
- Start the local backend dev server (port 8001): `uv run uvicorn lairservice.main:app --host 127.0.0.1 --port 8001`
- JWT signing key `OPENLAIR_JWT_SECRET` is read from (priority order): process env → `~/.openlair/.env` (or the dir of `OPENLAIR_CONFIG`) → `lairservice/.env` → dev default. Template: `lairservice/.env.example`.

Run these from `lairweb/`:

- Install web dependencies: `npm install`
- Start the Vue/Vite dev server: `npm run dev`
- Build and typecheck the web app: `npm run build`
- Preview the production build locally: `npm run preview`

Environment notes:

- Python is managed by `uv` (auto-installed CPython 3.14.5; lockfile `lairservice/uv.lock`).
- `.venv/`, `lairservice/.env`, `data/` are local-only and ignored by `.gitignore`.

## Planned boundaries

- `lairservice/`: Python/FastAPI backend, described as the core brain.
- `lairapp/`: Flutter client for iOS, Android, macOS, and Windows.
- `lairweb/`: Vue + TypeScript web admin UI backed by Vite. Browser API base is configured with `VITE_API_BASE_URL` from `.env`/`.env.local`; keep it empty for local same-origin proxying. Vite dev proxy reads `LAIRWEB_API_PROXY_TARGET`, then `VITE_API_BASE_URL`, then defaults to `http://127.0.0.1:8000`.
- `docs/`: Project documentation.

## Product modules from README

- Vocabulary: SM-2 spaced repetition, multilingual recognition, conversational recitation.
- Accounting: natural-language bookkeeping and category statistics.
- Calendar: schedule management and reminders.
- Notes: quick capture and summarization.
- Habits: check-in tracking.
- Proactive assistant: morning review, evening summary, and vocabulary reminders.

## Workflow guidance for future agents

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

- Before adding code, initialize the relevant module with its real manifest/config first, then document the exact commands here.
- After adding any build, lint, typecheck, test, codegen, migration, or dev-server command, update this file with the verified command and its working directory.
- Treat SQLite, SQLAlchemy, the multi-provider model gateway, and LangGraph orchestration as planned stack choices from `README.md` and `docs/backend-architecture.md`; the current core backend focus is the agent harness loop, not product modules.
- The implemented harness currently covers `learn-claude-code` style `s01` through `s14`, plus `s19`: agent loop, tool dispatch, permission checks, hooks, todo_write, subagent isolation, skill loading, context compact, memory, runtime system prompt assembly, error recovery, persistent task graph, background task execution, cron scheduling tools, and MCP plugin-style external tool routing.
- Product startup reads global configuration from `OPENLAIR_CONFIG` when set, otherwise `~/.openlair/openlair.json`; create the template file automatically when it is missing. Model settings live under the top-level `model` object. Model provider `api_key` may be a raw key or `$NAME`; `$NAME` resolves from the same directory's `.env` first, then process environment. Do not add implicit Echo/model fallback paths. The default pytest suite includes real model integration tests and requires valid local OpenLair model credentials; deterministic unit tests may still inject `ScriptedAgentModelGateway` directly.
- LangGraph is part of the MVP backend architecture; keep business modules behind service interfaces so graph nodes orchestrate module calls without owning domain logic.
- Use SQLAlchemy repositories for persistence instead of direct `sqlite3` calls, so SQLite remains replaceable by another SQL database later.
- Treat `lairservice/` as an agent harness: expose tools, knowledge, observation, action interfaces, and permission boundaries; do not try to encode intelligence with brittle procedural branches.
- Add runtime extension points around model calls, tool/module calls, and database writes before scattering cross-cutting concerns through graph nodes.
- Keep prompts/context lean: load detailed module instructions or skills only when a flow needs them, rather than putting everything into the default graph state or system prompt.
- Commit discipline: after each complete feature is implemented and verified, create a git commit so work is recoverable. A complete feature may span multiple files; commit by complete feature boundary, not by individual file.
