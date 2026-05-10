# Hybrid Scoring Demo

A generated **Hybrid Scoring Demo** app built with the AgentForge `ingestion_scoring_pipeline` archetype.

This app was generated from `domain-packs/hybrid-scoring-demo/domain-pack.yaml` by the AgentForge generator. Do not edit it as a primary artifact — edit the domain pack and regenerate.

The demo is intentionally deterministic. It proves the generated app structure, persistence, UI surfaces, notification/triage loop, and Agent Runtime Module without requiring a live LLM, a paid provider API, or external notification delivery.

## What it does

1. **Ingest** — pulls fixture records from a `FixtureRecordProvider`, normalises them, and stores them in the database with deduplication by `external_id`.
2. **Score** — runs a deterministic scoring engine over all unscored records, assigning a `fit` score (0–1), a label (`high`/`medium`/`low`), and a recommendation (`accept`/`review`/`skip`).
3. **Preview** — creates preview-only notification payloads from scored records without external delivery.
4. **Act** — operator accepts, skips, or saves individual scored records from the table or preview panel.
5. **Chat** — uses the Agent Runtime Module with a scripted provider, SSE events, and typed tool validation to call deterministic tools such as score or preview.
6. **Review** — the UI shows ingest run history, scored records, notification previews, current action state, action history, and persisted agent messages.

## Agent Runtime Module

The generated agent runtime is local and scripted by design. It is meant to prove the contract between chat, tools, persistence, and UI before a live provider is added.

- `POST /agent/chat` runs a full non-streaming scripted turn.
- `POST /agent/chat/stream` streams the same kind of turn as SSE events.
- Persisted conversations survive page reloads through `/agent/conversations/{id}`.
- Tool calls wrap deterministic app capabilities such as ingest, score, scored-record lookup, notification preview creation, and action history.
- Tool arguments are validated before execution. Unknown tools and invalid arguments return structured tool errors instead of crashing the request.
- The frontend shows running/succeeded/failed tool activity and streams assistant text progressively when SSE is available.

SSE events emitted by `/agent/chat/stream`:

- `message_start`
- `tool_call`
- `tool_result`
- `text_delta`
- `error`
- `done`

## Stack

- **Backend**: FastAPI + SQLAlchemy 2.0 async — `backend/`
- **Frontend**: React 18 + TypeScript + Vite — `frontend/`
- **Database**: PostgreSQL (prod), SQLite in-memory (tests)
- **E2E tests**: Playwright — `frontend/e2e/`

## Shell modules

| Module | Where |
|---|---|
| `pipeline` | `backend/app/services/ingest.py` |
| `provider_adapter` | `backend/app/providers/fixture/` |
| `scoring_explanation` | `backend/app/adapters/scoring.py`, `backend/app/services/score.py` |
| `operations_ui` | `frontend/src/components/OpsPanel.tsx` |
| `persistence` | `backend/app/models.py`, `backend/app/database.py` |
| `run_history` | `backend/app/routers/runs.py` |
| `notification_action` | `backend/app/routers/actions.py`, `backend/app/services/actions.py` |
| `triage_ui` | `frontend/src/components/NotificationPreviewPanel.tsx`, `frontend/src/components/ActionHistoryPanel.tsx` |
| `agent_runtime` | `backend/app/agent/`, `backend/app/routers/agent.py`, `frontend/src/components/AgentChatPanel.tsx` |

## API routes

| Method | Path | Description |
|---|---|---|
| `POST` | `/ingest` | Run ingestion — fetches records from provider |
| `GET` | `/runs` | List provider run history |
| `GET` | `/records` | List normalised records |
| `POST` | `/records/score` | Score all unscored records |
| `GET` | `/records/scored` | List scored records (ordered by fit desc) |
| `POST` | `/records/{id}/action` | Submit an action (`accept`, `skip`, `save`) |
| `GET` | `/actions/history` | List append-only action history |
| `POST` | `/notifications/previews` | Generate preview-only notification payloads |
| `GET` | `/notifications/previews` | List notification previews |
| `POST` | `/agent/chat` | Send a message to the scripted Agent Runtime Module |
| `POST` | `/agent/chat/stream` | Stream a scripted agent turn as SSE events: `message_start`, `text_delta`, `tool_call`, `tool_result`, `error`, `done` |
| `GET` | `/agent/conversations/{id}` | Load persisted agent conversation messages |

Interactive docs at `http://localhost:8000/docs`.

## Local development

### Backend

```bash
cd backend
pip install -r requirements-dev.txt
# Run tests (SQLite in-memory — no Postgres needed)
pytest -v
# Start dev server with SQLite for local demo usage
set DATABASE_URL=sqlite+aiosqlite:///./demo.db
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev      # dev server on :5173
npm run build    # production build
npm run lint     # ESLint
```

### Playwright E2E

Start both servers first, then:

```bash
cd frontend
# On Windows: clear Vite cache if you hit EBUSY
rmdir /s /q node_modules\.vite
npm run test:e2e
```

### Full stack (Docker Compose)

```bash
docker compose up --build
```

Backend on `:8000`, frontend on `:5173`.

## Known limitations

- `FixtureRecordProvider` emits 10 static records — replace with a real provider for production use.
- Scoring is deterministic (`fit = value / 100`) — replace `backend/app/adapters/scoring.py` with real logic.
- No authentication or multi-user support.
- No migration tooling (Alembic) — schema is created on startup via `Base.metadata.create_all`.
- Notification delivery is preview-only; no Telegram/email/Slack adapter is wired.
- Agent Runtime uses a scripted provider; no live LLM/API provider is configured.
- Agent Runtime tools validate typed arguments before execution and return structured tool errors instead of crashing the chat turn.
- Agent streaming is SSE-based and deterministic; the non-streaming `/agent/chat` route remains available as fallback.
- Modules `workspace`, `observability_debug`, and `deploy_planner` are reported as gaps by the generator and are not present.
