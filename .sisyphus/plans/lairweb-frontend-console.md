# Work Plan: Complete `lairweb` Frontend Console

## Objective

Build a complete first version of the OpenLair Web console in `lairweb/` using Vue 3 + TypeScript + Vite. The frontend must be usable for real backend debugging: it should run as a local dev server, read backend configuration from Vite `.env` variables, call the FastAPI assistant endpoint, and present a polished assistant console instead of the default scaffold page.

## Current Context

- Repository root: `/code/lair`
- Backend module: `lairservice/`
- Web module: `lairweb/`
- Backend assistant endpoint: `POST /assistant/invoke`
- Backend health endpoint: `GET /health`
- Backend default dev URL: `http://127.0.0.1:8000`; in this session, port 8000 was occupied by another project, so `lairservice` was verified on `http://127.0.0.1:8001` through local `.env.local`.
- Web stack chosen by user: Vue 3 + TypeScript
- The backend already has real model integration tests through `~/.openlair/openlair.json` and `~/.openlair/.env`.
- `lairweb/` has been initialized with Vite's `vue-ts` template and `npm install` has been run.

## User Requirements

- Use Vue, specifically Vue + TypeScript.
- Do not leave the frontend as an empty scaffold.
- Implement a complete usable frontend work item, not just create files.
- Read backend API configuration from `.env` variables rather than hardcoding it.
- Keep the backend running while frontend debugging is needed.
- Follow repo command discipline: only document commands after verifying them.
- Follow repo commit discipline: after a complete feature is implemented and verified, commit the feature boundary.

## Non-Goals

- Do not implement product modules such as vocabulary, accounting, calendar, notes, or habits yet.
- Do not add Vue Router, Pinia, ESLint, Prettier, Vitest, or E2E tooling unless this work requires them and their commands are verified.
- Do not introduce CI workflows.
- Do not commit secrets or local `.env` files containing private values.
- Do not bypass TypeScript safety with `as any`, `@ts-ignore`, or `@ts-expect-error`.

## Planned Deliverables

1. `lairweb/` Vue 3 + TypeScript project with real manifest and lockfile.
2. A polished OpenLair assistant console in `src/App.vue` and `src/style.css`.
3. Vite config that reads `LAIRWEB_API_PROXY_TARGET`/`VITE_API_BASE_URL` through `loadEnv` and defaults to `http://127.0.0.1:8000` for local development.
4. `.env.example` documenting `LAIRWEB_API_PROXY_TARGET` and `VITE_API_BASE_URL`.
5. Frontend README updated with commands and env guidance.
6. Root README updated to say Web uses Vue + TypeScript / Vite.
7. `AGENTS.md` updated with verified `lairweb/` commands:
   - `npm install`
   - `npm run dev`
   - `npm run build`
   - `npm run preview`
8. `docs/backend-architecture.md` updated so web admin references are current.
9. Backend dev server started for frontend debugging. Prefer `127.0.0.1:8000`; use `LAIRWEB_API_PROXY_TARGET` when another local port is required.
10. Frontend dev server started for browser verification.
11. Browser verification of the frontend page and at least one assistant request path.
12. A git commit for the complete frontend initialization/console feature.

## Implementation Steps

### 1. Stabilize backend dev service

- Start `lairservice` through its local venv:
  - working directory: `/code/lair/lairservice`
  - command: `.venv/bin/python -m uvicorn lairservice.main:app --host 127.0.0.1 --port 8000`
- Verify `GET http://127.0.0.1:8000/health` returns `{"status":"ok"}`.
- If port 8000 is occupied by another local project, start on another free port and set `LAIRWEB_API_PROXY_TARGET` in `lairweb/.env.local`.
- If the command is not yet documented in `AGENTS.md`, document it only after successful verification.

### 2. Complete frontend app behavior

- Keep all application code TypeScript-safe.
- Implement request types for `/assistant/invoke` response.
- Submit message, `user_id`, and `session_id` to the backend.
- Show user and assistant messages in the UI.
- Preserve returned `session_id`.
- Surface request failures in the UI.
- Disable the submit button while a request is in flight.
- Avoid global state libraries until the app actually needs them.

### 3. Complete frontend configuration

- Use `import.meta.env.VITE_API_BASE_URL || ''` in browser code.
- Use `loadEnv(mode, process.cwd(), '')` in `vite.config.ts`.
- Use `LAIRWEB_API_PROXY_TARGET` as the local dev proxy target when set; fall back to `VITE_API_BASE_URL` and then `http://127.0.0.1:8000`.
- Default proxy target to `http://127.0.0.1:8000` when unset.
- Add `.env.example` with:
  - `LAIRWEB_API_PROXY_TARGET=http://127.0.0.1:8000`
  - `VITE_API_BASE_URL=`
- Do not commit `.env.local` or secrets.

### 4. Polish the UI

- Replace the default Vite scaffold UI.
- Use an OpenLair-specific visual direction: warm dark console, strong typography, clear assistant/debug status.
- Keep the layout responsive.
- Make the UI readable and practical for daily debugging.
- Avoid generic purple-gradient AI aesthetics.

### 5. Verification

- Run frontend build:
  - working directory: `/code/lair/lairweb`
  - command: `npm run build`
- Check TypeScript/Vue diagnostics where available.
- Start frontend dev server:
  - working directory: `/code/lair/lairweb`
  - command: `npm run dev`
- Use a browser to verify:
  - page loads
  - no visible runtime error
  - assistant console renders
  - request can reach backend through env/proxy configuration
- Optionally run backend tests if backend code changed. If only frontend/docs changed, backend pytest is not required unless a regression is suspected.

### 6. Documentation

- Update root `README.md` Web stack row.
- Update `AGENTS.md` current state, planned boundaries, and verified `lairweb/` commands.
- Update `docs/backend-architecture.md` web admin wording.
- Keep command documentation limited to commands that were actually run and verified.

### 7. Git commit

- Inspect status and diff before committing.
- Stage only intended files.
- Commit with `GIT_MASTER=1` according to repo convention.
- Suggested commit message:
  - `feat: initialize Vue web console`

## Acceptance Criteria

- `lairweb/package.json` exists and identifies a Vue + TypeScript Vite project.
- `lairweb/package-lock.json` exists after dependency installation.
- `npm run build` passes in `/code/lair/lairweb`.
- `src/App.vue` contains a working assistant console, not the default Vite demo.
- `src/App.vue` does not use `as any`, `@ts-ignore`, or `@ts-expect-error`.
- `vite.config.ts` reads `.env` API configuration and configures dev proxy from it.
- `.env.example` exists and documents `LAIRWEB_API_PROXY_TARGET` and `VITE_API_BASE_URL`.
- `README.md`, `AGENTS.md`, and `docs/backend-architecture.md` match the new Vue + TypeScript web reality.
- Backend and frontend dev servers can run concurrently for local debugging.
- Browser verification confirms the UI is usable.
- A git commit records the complete frontend feature.

## Risks and Mitigations

- **Backend not running**: Start it before browser verification and check `/health`.
- **Real model latency/failure**: UI must show loading and error state instead of hanging silently.
- **CORS/proxy confusion**: In dev, prefer Vite proxy when `VITE_API_BASE_URL` is empty; use `.env.local` only when direct backend URL is needed.
- **Untracked generated artifacts**: Do not commit `node_modules/` or `dist/`.
- **Over-scoping frontend architecture**: Avoid router/state/test tooling until a second page or shared state makes it necessary.

## Files Expected to Change

- `lairweb/package.json`
- `lairweb/package-lock.json`
- `lairweb/index.html`
- `lairweb/README.md`
- `lairweb/.env.example`
- `lairweb/vite.config.ts`
- `lairweb/src/App.vue`
- `lairweb/src/style.css`
- `README.md`
- `AGENTS.md`
- `docs/backend-architecture.md`
- `.sisyphus/plans/lairweb-frontend-console.md`

## Execution Notes

- If `npm create vue@latest` flags fail due to CLI version differences, Vite's `vue-ts` template is acceptable because it produces a current Vue 3 + TypeScript Vite project.
- Keep the first frontend focused on the assistant console because `/assistant/invoke` is the backend's current core harness entrypoint.
