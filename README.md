# OpenLair

![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-backend-009688?logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-agent%20runtime-1C3C3C)
![Vue](https://img.shields.io/badge/Vue-3-42B883?logo=vue.js&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-web-3178C6?logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-dev%20server-646CFF?logo=vite&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-local%20data-003B57?logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

> A cross-platform personal AI life assistant for one person.

[简体中文](README.zh-CN.md)

## Project structure

```text
lair/
├── backend/        # FastAPI backend（源码在 app/ 包，参照官方 full-stack-fastapi-template 结构）
├── lairapp/        # Flutter client for iOS, Android, macOS, and Windows
├── lairweb/        # Vue + TypeScript web admin console
└── docs/           # Project documentation
```

## Planned modules

- **Vocabulary** — SM-2 spaced repetition, multilingual recognition, and conversational recitation.
- **Accounting** — Natural-language bookkeeping and category statistics.
- **Calendar** — Schedule management and reminders.
- **Notes** — Quick capture and summarization.
- **Habits** — Check-in tracking.
- **Proactive assistant** — Morning review, evening summary, and vocabulary reminders.

## Tech stack

| Component | Technology |
|---|---|
| Backend | Python / FastAPI |
| Client | Flutter |
| Web | Vue + TypeScript / Vite |
| Database | SQLite |
| LLM | Multi-provider and multi-model gateway |
| LLM orchestration | LangGraph |

Backend architecture details are documented in [`docs/backend-architecture.md`](docs/backend-architecture.md).

## Current implementation status

- `backend/` contains the FastAPI backend: unified `{code, message, data}` envelope API, JWT auth, and ledger/books/todo/calendar/notes/habits business modules over SQLAlchemy repositories + services, with Alembic migrations.
- `lairweb/` contains the Vue + TypeScript web console; in dev it runs against the in-memory mock layer (`lairweb/mock/`) that mirrors the backend API contract exactly.
- Product modules are being built out module by module; the API contract between `lairweb/mock/` and the real backend on port 8001 is identical, so switching the Vite proxy target connects the console to the real backend.

## Development notes

See [`AGENTS.md`](AGENTS.md) for verified local commands and repository workflow rules.

## License

MIT
