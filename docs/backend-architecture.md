# Backend architecture decision

## Decision

- Use Python/FastAPI for `lairservice/` as the core backend.
- Use LangGraph as the MVP orchestration layer for assistant flows.
- Use a multi-provider, multi-model gateway instead of binding the backend to one LLM vendor or model.
- Use SQLite for the initial single-user data store.

## Why FastAPI

- FastAPI is a good fit for the API boundary: typed request/response models, dependency injection, async I/O, and automatic OpenAPI docs for the Flutter client and future web admin.
- The backend is mostly assistant orchestration, model calls, module dispatch, validation, and persistence. Python has the strongest ecosystem for this work.
- The repo has no existing backend code or manifests, so the move from the earlier Go plan has no implementation migration cost.

## Why LangGraph is in MVP

Lair's MVP target is not only a single-shot intent classifier. It needs assistant-like behavior from the start:

- choose among multiple model providers and model capabilities
- call tools and product modules
- keep conversation/task state across steps
- branch when user intent is ambiguous
- support confirmation or correction loops
- compose proactive flows such as morning review, evening summary, and vocabulary reminders

LangGraph should own orchestration state and flow control. Domain services should still own business logic.

## MVP backend shape

```text
client apps
  -> FastAPI routes
  -> LangGraph assistant graph
  -> model gateway
  -> module services
  -> SQLite repositories
```

The first implementation lives in `lairservice/` and uses an `AssistantRuntime` abstraction backed by a LangGraph runtime implementation. Keep this abstraction even while LangGraph is the only runtime implementation, so Lair owns the runtime boundary and can evolve it later.

### Core layers

- FastAPI routes: HTTP API, auth/session boundary, validation, streaming responses where needed.
- LangGraph assistant graph: intent routing, multi-step orchestration, tool/module calls, clarification loops, and state transitions.
- Model gateway: provider/model selection, failover hooks, request normalization, response normalization, and capability metadata.
- Module services: vocabulary, accounting, calendar, notes, habits, and proactive assistant logic.
- SQLAlchemy repositories: persistence abstraction for app data, using SQLite for early local/light deployment.

## Implemented first work

The current core backend work is the agent harness loop, adapted from the `s01` through `s14` harness pattern, plus `s19` MCP plugin-style external tool routing:

```text
POST /assistant/invoke
  -> LangGraphAssistantRuntime
  -> model step
  -> optional tool execution step
  -> tool_result messages loop back to model
  -> final assistant text response
```

Implemented harness mechanisms:

- `s01` Agent loop: model responses continue while `stop_reason == "tool_use"`.
- `s02` Tool use: tools register through a dispatch map and model-facing schemas.
- `s03` Permission: tool calls pass through a deny/rule policy before execution.
- `s04` Hooks: lifecycle extension points wrap prompt submit, tool use, and stop events.
- `s05` TodoWrite: `todo_write` updates the current task list and supports reminders.
- `s06` Subagent: the `task` tool runs a child loop with fresh context and returns only a summary.
- `s07` Skill Loading: skill catalogs stay cheap in the system prompt; `load_skill` loads full content on demand.
- `s08` Context Compact: tool-result budgeting, snip compaction, micro compaction, transcript persistence, and reactive compaction protect the model context.
- `s09` Memory: `.memory/MEMORY.md` indexes persistent memories, and clear `remember ...` user facts are extracted into files.
- `s10` System Prompt: system prompts are assembled at runtime from identity, tools, workspace, skills, and memory context.
- `s11` Error Recovery: model calls retry transient errors, reactively compact oversized prompts, and escalate `max_tokens` responses before continuing.
- `s12` Task System: persistent harness tasks live under `.tasks/`, support dependencies, claiming, completion, and unlocked downstream reporting.
- `s13` Background Tasks: slow or explicitly marked tool calls can run in daemon background threads and later inject `<task_notification>` messages.
- `s14` Cron Scheduler: `schedule_cron`, `list_crons`, and `cancel_cron` manage five-field cron prompts with durable `.scheduled_tasks.json` persistence.
- `s19` MCP Plugin: `connect_mcp` connects mock MCP servers, dynamically exposes prefixed tools such as `mcp__docs__search`, and routes those calls through the normal tool registry.

This is implemented as a FastAPI + LangGraph service runtime rather than a CLI script. The loop is owned by `LangGraphAssistantRuntime`; tool definitions and handlers live under `lairservice.agent`; model access stays behind `ModelGateway`.

The first business slice is Notes quick capture:

```text
POST /assistant/invoke
  -> LangGraphAssistantRuntime
  -> AssistantService routes to notes
  -> NotesService
  -> SQLAlchemy NotesRepository
  -> SQLite
```

This is intentionally small: it proves the runtime, module boundary, and SQL persistence path without mixing note business logic into graph nodes.

## Model gateway requirements

Do not call model providers directly from product modules or graph nodes. Route all model access through a gateway interface so the backend can support:

- multiple providers
- multiple model classes, such as cheap intent models, stronger reasoning models, embedding models, and summarization models
- per-task model selection
- fallback and retry policies
- consistent logging and cost/latency tracking later

GLM-Flash can be one supported model/provider, but it is not the only planned LLM dependency.

Global product configuration is loaded through `OPENLAIR_CONFIG` when set, otherwise `~/.openlair/openlair.json`. If the default file is missing, startup creates a template with real `openai_compatible` fields; there is no implicit Echo fallback in the product path. Model routing lives under the top-level `model` object, mapping logical routes such as `agent`, `chat`, and `summary` to named providers. Provider entries include `kind`, `model`, `base_url`, and `api_key_env`; secrets stay in environment variables, not in JSON files.

## LangGraph boundaries

- Graph nodes may orchestrate module services, but should not contain durable domain rules such as SM-2 scheduling, accounting categorization storage, or habit streak calculation.
- Keep module services callable outside LangGraph so they can be unit tested directly.
- Keep graph state schemas explicit and small; store durable business data in repositories, not only in graph state.
- Prefer simple subgraphs per assistant capability once flows grow, instead of one giant graph.

## Harness principles

Lair should treat the backend as an agent harness, not as a hand-coded intelligence engine. The model supplies the agency; the backend supplies the controlled environment around it:

- Tools: module services, repositories, external APIs, and model gateway capabilities.
- Knowledge: product/module instructions, user context, and retrieved memories.
- Observation: tool results, database reads, traces, and runtime state.
- Action interfaces: FastAPI endpoints, scheduled entrypoints, module methods, and database writes.
- Permissions: checks before sensitive tool calls, module side effects, or durable writes.

Keep the core runtime path stable and add cross-cutting behavior through explicit extension points. Useful early hook points are before model calls, after model responses, before module/tool calls, after module/tool calls, and before database writes. These hooks should enforce permissions, logging, tracing, and validation without moving business logic into LangGraph nodes.

Context should be loaded progressively. The default graph state should stay small; detailed module instructions, examples, or skill-like guidance should be loaded only when the routed flow needs them.

## Scheduling and background work

- FastAPI `BackgroundTasks` is only suitable for short, non-durable work after a response.
- Proactive reminders and daily summaries need a recoverable scheduling strategy before they are treated as reliable features.
- Scheduled jobs should trigger graph entrypoints or service methods rather than duplicating assistant flow logic.
- The current s13/s14 harness implementation is intentionally local and lightweight: background work uses daemon threads, and cron tools persist definitions but do not yet run a service-wide scheduler loop. Treat reliable proactive execution as a later infrastructure step.
- The current s19 MCP implementation follows the upstream teaching shape with in-process mock servers (`docs`, `deploy`). Real stdio JSON-RPC MCP server management is a later integration step.

## SQLite constraints

- SQLite is appropriate for early single-user local/light deployment.
- Access SQLite through SQLAlchemy models/repositories, not direct `sqlite3` calls, so the backend can move to another SQL database later.
- Avoid assuming high write concurrency.
- If the backend later runs multiple workers or concurrent write-heavy tasks, document the locking behavior and evaluate WAL mode or migration to a server database.
