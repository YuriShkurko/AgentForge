# AgentForge

AgentForge is an opinionated generator for full-stack AI/product applications. It turns a structured **App Blueprint** into a runnable FastAPI + React project — complete with integration adapters, a scoring/explanation pipeline, an operations UI, deterministic tests, and CI-ready structure. No live LLM or paid API required.

```
App Blueprint (YAML)  +  Application Template  →  Generated App
```

> **Current scope:** v0.1 generates one sample app — `hybrid-scoring-demo` — that proves the reusable architecture shared by Business Insight and AI Job Radar. It is not a generic AI app builder yet.

## Quickstart

```bash
pip install -e generator/
agentforge plan domain-packs/hybrid-scoring-demo/domain-pack.yaml
agentforge generate domain-packs/hybrid-scoring-demo/domain-pack.yaml --force
make validate
```

This installs the generator CLI, previews the module plan, generates the demo app, then runs all tests and the frontend build.

## What it generates

`agentforge generate` reads an App Blueprint (`domain-pack.yaml`) and emits a self-contained project directory. The `hybrid-scoring-demo` output includes:

- **FastAPI backend** with async SQLAlchemy ORM (SQLite for local dev, PostgreSQL for production)
- **React + TypeScript frontend** built with Vite
- **Integration adapter layer** — a fixture provider + normalizer that converts raw records into stable domain DTOs
- **Scoring pipeline** — deterministic fit score (0–100), label (high/medium/low), recommendation, drivers, and risks
- **Operations UI** — ingest/score controls, run history table, scored records table, action status badges
- **Action/decision loop stub** — records accept/skip/save decisions without external delivery
- **40 backend tests** (pytest, SQLite in-memory — no Postgres required)
- **5 Playwright E2E tests** proving the full UI workflow
- **GitHub Actions CI skeleton** with no live LLM or paid API dependency

## How it works

1. **App Blueprint** (`domain-pack.yaml`) — describes your app's archetype (`ingestion_scoring_pipeline`, `agent_dashboard_app`, etc.), the feature modules it needs, and its data capabilities. Lives in `domain-packs/`.
2. **Generator** (`agentforge generate`) — reads the blueprint, selects the matching application template, substitutes app-name tokens, and emits a fully self-contained project directory.
3. **Generated app** — a real FastAPI + React project you can install, run, test, and deploy independently. It has no runtime dependency on AgentForge.

## What is not built yet

- Only one application template exists: `ingestion_scoring_pipeline` via the `fastapi-react` template.
- Token substitution is string-replace only — no per-capability code generation yet.
- Feature modules `workspace`, `observability_debug`, `triage_ui`, and `deploy_planner` are reported as gaps, not generated.
- Production database is PostgreSQL; the generator does not yet emit migration scripts.
- No guided UI — the generator is CLI-only.
- `examples/hybrid-scoring-demo/` is a **committed snapshot** of the generated output; it is regenerable (see [Reproducibility](#reproducibility)).

## Terminology

| Public term | Config / internal term | Meaning |
|---|---|---|
| App Blueprint | `domain-pack` | Machine-readable YAML describing app archetype, capabilities, adapters, UI surfaces, and tests |
| Application Template | `template` | The reusable FastAPI/React source tree copied and parameterized by the generator |
| Feature Module | shell module | A reusable capability area — pipeline, scoring, notifications, agent runtime, etc. |
| Integration Adapter | provider/adapter | Normalizes external or fixture data into stable app-specific records |
| Test Harness | deterministic test shell | Fixture-based tests that avoid live external APIs or LLMs |

## All-in-one via Makefile

```bash
make validate          # generator tests + backend tests + frontend build/lint
make generate-demo     # regenerate examples/hybrid-scoring-demo
make test-generator    # generator unit tests only
make test-backend      # generated app backend tests only
make run-backend       # start backend dev server
make run-frontend      # start frontend dev server
make run-e2e           # run Playwright E2E (requires running stack)
```

## Running the generated app manually

### Backend

```bash
cd examples/hybrid-scoring-demo/backend
pip install -r requirements-dev.txt
DATABASE_URL=sqlite+aiosqlite:///./demo.db uvicorn app.main:app --reload
```

### Frontend

```bash
cd examples/hybrid-scoring-demo/frontend
npm install
VITE_API_URL=http://localhost:8000 npm run dev
```

### Full stack (Docker Compose)

```bash
cd examples/hybrid-scoring-demo
docker-compose up
```

## Repository layout

```
AgentForge/
├── generator/               # Python package — the AgentForge CLI
│   ├── agentforge/
│   │   ├── cli.py           # agentforge generate / agentforge plan
│   │   ├── generator.py     # core copy + substitute logic
│   │   ├── modules.py       # archetype → module selection
│   │   └── pack.py          # DomainPack Pydantic model + validation
│   └── pyproject.toml       # pip-installable, entry_point: agentforge
├── domain-packs/            # App Blueprint YAML files
│   └── hybrid-scoring-demo/ # the v0.1 proof-of-concept blueprint
├── templates/               # Application templates
│   ├── fastapi-react/       # FastAPI + React 18 + TypeScript template
│   ├── ci/                  # GitHub Actions CI skeleton
│   └── docker-compose/      # docker-compose.yml template
├── examples/                # GENERATED output (disposable — see below)
│   └── hybrid-scoring-demo/ # snapshot of the generated demo app
├── tests/
│   └── generator/           # generator unit + snapshot tests
└── docs/                    # architecture and spec docs
```

## Reproducibility

`examples/hybrid-scoring-demo/` is a generated snapshot committed for convenience. It can be fully regenerated from its App Blueprint:

```bash
rm -rf examples/hybrid-scoring-demo
agentforge generate domain-packs/hybrid-scoring-demo/domain-pack.yaml
```

The generator skips `__pycache__`, `node_modules`, `dist`, and `.venv` — those are never committed.

## Documentation

- [App Blueprint Specification](docs/DOMAIN_PACK_SPEC.md) — how to write a `domain-pack.yaml`
- [Architecture](docs/AGENTFORGE_V0_ARCHITECTURE.md) — module language and cross-pack comparison
- [Archetype Model](docs/ARCHETYPE_MODEL.md) — archetype definitions and required feature modules
- [Roadmap](docs/AGENTFORGE_ROADMAP.md) — what is and isn't planned
