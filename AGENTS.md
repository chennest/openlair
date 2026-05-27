# AGENTS.md

## Current state

- This repo is in early implementation: `lairservice/` contains the FastAPI + LangGraph agent harness runtime; `lairweb/` contains the Vue + TypeScript web admin console; `lairapp/` currently contains no files; `docs/` contains backend architecture notes.
- There are no CI workflows, formatter configs, lint configs, or codegen configs yet. Do not invent commands beyond those listed here.
- `README.md` and `docs/backend-architecture.md` are the verified project sources of truth at the moment.

## Verified commands

Run these from `lairservice/`:

- Create/recreate the local venv with vfox Python 3.14: `vfox exec python@3.14.5 -- python -m venv --clear .venv`
- Install backend dev dependencies: `.venv/bin/python -m pip install -e .[dev]`
- Run backend tests, including real model integration through `~/.openlair/openlair.json` and `~/.openlair/.env`: `.venv/bin/python -m pytest`
- Start the local backend dev server: `.venv/bin/python -m uvicorn lairservice.main:app --host 127.0.0.1 --port 8001`

Run these from `lairweb/`:

- Install web dependencies: `npm install`
- Start the Vue/Vite dev server: `npm run dev`
- Build and typecheck the web app: `npm run build`
- Preview the production build locally: `npm run preview`

Environment notes:

- Python is managed through vfox; the verified interpreter is Python 3.14.5.
- Global pyenv was removed to avoid `python` resolution conflicts.
- `.venv/` is local-only and ignored by `.gitignore`.

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
