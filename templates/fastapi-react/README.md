# Hybrid Scoring Demo

A generated **Hybrid Scoring Demo** app built with the AgentForge `ingestion_scoring_pipeline` archetype.

This app was generated from `domain-packs/hybrid-scoring-demo/domain-pack.yaml` by the AgentForge generator. Do not edit it as a primary artifact — edit the domain pack and regenerate.

The demo is intentionally deterministic. It proves the generated app structure, persistence, UI surfaces, notification/triage loop, Agent Runtime Module, and Dashboard/Workspace Module without requiring a live LLM, a paid provider API, or external notification delivery.

## What it does

1. **Ingest** — pulls fixture records from a `FixtureRecordProvider`, normalises them, and stores them in the database with deduplication by `external_id`.
2. **Import** — accepts user-provided JSON records from the Operations panel or `POST /ingest/import`, with visible accepted/skipped counts and validation errors.
3. **Score** — runs a deterministic scoring engine over all unscored records, assigning a `fit` score (0–1), a label (`high`/`medium`/`low`), and a recommendation (`accept`/`review`/`skip`).
3. **Preview** — creates preview-only notification payloads from scored records without external delivery.
4. **Act** — operator accepts, skips, or saves individual scored records from the table or preview panel.
5. **Chat** — uses the Agent Runtime Module with a scripted provider, SSE events, and typed tool validation to call deterministic tools such as score or preview.
6. **Pin** — asks the scripted agent to persist compatible tool results as generic workspace widgets.
7. **Review** — the UI shows ingest run history, scored records, notification previews, current action state, action history, persisted agent messages, and workspace widgets.

## Agent Runtime Module

The generated agent runtime is local and scripted by default. It proves the contract between chat, tools, persistence, and UI without requiring a live provider. Optional OpenAI chat mode can be enabled later with user-provided credentials.

- `POST /agent/chat` runs a full non-streaming scripted or configured-provider turn.
- `POST /agent/chat/stream` streams the same kind of turn as SSE events.
- Persisted conversations survive page reloads through `/agent/conversations/{id}`.
- In scripted mode, tool calls wrap deterministic app capabilities such as ingest, score, scored-record lookup, notification preview creation, and action history.
- Tool arguments are validated before execution. Unknown tools and invalid arguments return structured tool errors instead of crashing the request.
- The frontend shows running/succeeded/failed tool activity and streams assistant text progressively when SSE is available.
- OpenAI mode is chat-only in this first pass; scoring remains deterministic/local and tests do not make live OpenAI calls.

SSE events emitted by `/agent/chat/stream`:

- `message_start`
- `tool_call`
- `tool_result`
- `text_delta`
- `error`
- `done`

### Optional OpenAI chat mode

Default local mode needs no API keys:

```env
AGENT_PROVIDER=scripted
```

To enable optional live chat responses:

```env
AGENT_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

If `AGENT_PROVIDER=openai` is set without `OPENAI_API_KEY`, the API returns a clear configuration error and the scripted default remains available by switching back to `AGENT_PROVIDER=scripted`.

## Dashboard/Workspace Module

The workspace is generic and persistence-first. It stores direct JSON payloads from deterministic tool results in `workspace_widgets`, validates `source_tool` to `widget_type` compatibility on the backend, and renders compact reusable widgets in the frontend.

v0.4.1 is a UI polish pass only. It improves workspace hierarchy, empty/loading/error states, widget card readability, and agent pin success/failure copy without changing workspace APIs, persistence, compatibility rules, or runtime dependencies. Taste Skill-style critique was used as a design review aid; it is not required to run the generated app.

Supported v0.4 widget types:

- `summary_card`
- `ranking_list`
- `score_table`
- `run_history_list`
- `notification_preview_card`
- `action_history_list`

The scripted agent can pin scored records, notification preview results, and action history. Invalid widget types, incompatible source/widget pairs, empty data, unknown widget IDs, and invalid reorder requests return structured errors.

## Screenshot/GIF Checklist

Useful demo captures:

- App overview with agent chat, workspace, and operations visible.
- Agent pinning scored records into the workspace.
- Persisted workspace widget after page refresh.
- Notification preview and triage flow with workspace widgets still visible.

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
| `workspace` | `backend/app/routers/workspace.py`, `backend/app/services/workspace.py`, `frontend/src/components/WorkspacePanel.tsx` |

## API routes

| Method | Path | Description |
|---|---|---|
| `POST` | `/ingest` | Run fixture demo ingestion — fetches records from provider |
| `POST` | `/ingest/import` | Import user-provided JSON records with per-row validation |
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
| `GET` | `/workspace/widgets` | List persisted workspace widgets |
| `POST` | `/workspace/widgets` | Create a validated workspace widget |
| `DELETE` | `/workspace/widgets/{id}` | Remove a workspace widget |
| `POST` | `/workspace/widgets/reorder` | Set deterministic workspace widget order |

Interactive docs at `http://localhost:8000/docs`.

## Local development

From the generated app root, install dependencies once:

```bash
make install
```

Run validation without live services:

```bash
make validate
```

`make validate` runs backend tests plus frontend build/lint. `make test` currently runs backend tests only because this generated app has no frontend unit test target.

Start the app in two terminals:

```bash
make run-backend
make run-frontend
```

The backend runs with a local SQLite demo database. The frontend dev server runs on `http://localhost:5173`.

### Manual backend/frontend commands

```bash
cd backend
pip install -r requirements-dev.txt
pytest -v
DATABASE_URL=sqlite+aiosqlite:///./demo.db uvicorn app.main:app --reload
```

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

## User data import

Paste a JSON array in the Operations panel or send it to `POST /ingest/import`:

```json
{
  "source": "manual_import",
  "records": [
    { "external_id": "user-1", "title": "Urgent customer request", "category": "support", "value": 92 }
  ]
}
```

Required field: `title` (aliases: `name`, `subject`). Optional fields: `external_id`/`id`, `category`/`type`/`status`, `value`/`amount`/`score`/`priority`, and `raw_payload`. Numeric values are clamped to 0–100. Duplicate `external_id` values are skipped with validation errors shown in the UI/API response.

## Known limitations

- `FixtureRecordProvider` emits 10 static records; use JSON import for user-provided local data.
- Scoring is deterministic (`fit = value / 100`) — replace `backend/app/adapters/scoring.py` with real logic.
- No authentication or multi-user support.
- No migration tooling (Alembic) — schema is created on startup via `Base.metadata.create_all`.
- Notification delivery is preview-only; no Telegram/email/Slack adapter is wired.
- Agent Runtime uses a scripted provider by default; optional OpenAI mode is chat-only and requires a user-supplied `OPENAI_API_KEY`.
- Agent Runtime tools validate typed arguments before execution and return structured tool errors instead of crashing the chat turn.
- Agent streaming is SSE-based and deterministic; the non-streaming `/agent/chat` route remains available as fallback.
- Dashboard/Workspace widgets are generic only; domain-specific Business Insight widgets are not generated here.
- Modules `observability_debug` and `deploy_planner` are reported as gaps by the generator and are not present.
