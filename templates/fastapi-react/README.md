# Hybrid Scoring Demo

A generated **Hybrid Scoring Demo** app built with the AgentForge `ingestion_scoring_pipeline` archetype.

This app was generated from `domain-packs/hybrid-scoring-demo/domain-pack.yaml` by the AgentForge generator. Do not edit it as a primary artifact — edit the domain pack and regenerate.

## What it does

1. **Ingest** — pulls fixture records from a `FixtureRecordProvider`, normalises them, and stores them in the database with deduplication by `external_id`.
2. **Score** — runs a deterministic scoring engine over all unscored records, assigning a `fit` score (0–1), a label (`high`/`medium`/`low`), and a recommendation (`accept`/`review`/`skip`).
3. **Act** — operator accepts, skips, or saves individual scored records via the Operations Panel.
4. **Review** — the UI shows the ingest run history, scored records ranked by fit, and action badges.

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

## API routes

| Method | Path | Description |
|---|---|---|
| `POST` | `/ingest` | Run ingestion — fetches records from provider |
| `GET` | `/runs` | List provider run history |
| `GET` | `/records` | List normalised records |
| `POST` | `/records/score` | Score all unscored records |
| `GET` | `/records/scored` | List scored records (ordered by fit desc) |
| `POST` | `/records/{id}/action` | Submit an action (`accept`, `skip`, `save`) |

Interactive docs at `http://localhost:8000/docs`.

## Local development

### Backend

```bash
cd backend
pip install -r requirements-dev.txt
# Run tests (SQLite in-memory — no Postgres needed)
pytest -v
# Start dev server (requires .env with DATABASE_URL)
cp .env.example .env   # fill in DATABASE_URL
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
- Modules `workspace`, `observability_debug`, `triage_ui`, and `deploy_planner` were reported as gaps by the generator and are not present.
