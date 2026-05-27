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
├── lairservice/    # FastAPI backend, the core agent brain
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

- `lairservice/` contains the current core work: a FastAPI + LangGraph agent harness runtime.
- The backend harness covers the `learn-claude-code` style `s01` through `s14`, plus `s19` MCP plugin-style external tool routing.
- `lairweb/` contains the first Vue + TypeScript web console and can call the backend assistant endpoint through the Vite dev proxy.
- Product modules are still planned; the current backend focus is the agent harness, model gateway, permission boundary, memory/context tools, background tasks, cron tools, and MCP-style tool routing.

## Development notes

See [`AGENTS.md`](AGENTS.md) for verified local commands and repository workflow rules.

## License

MIT
