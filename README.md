# AgentForge

AgentForge is an opinionated generator for full-stack AI/product applications. It turns a structured **App Blueprint** into a runnable FastAPI + React project with integration adapters, deterministic scoring, notification/triage workflows, an Agent Runtime Module, tests, and CI-ready structure.

The current goal is deliberately narrow: prove a reusable generated application foundation before building dashboards, workspace widgets, live LLM integrations, deployment automation, or repo-conversion tooling. Everything in the generated demo runs locally and deterministically. No live LLM or paid API is required.

```
App Blueprint (YAML)  +  Application Template  →  Generated App
```

> **Current scope:** v0.3.1 generates one sample app — `hybrid-scoring-demo` — that proves reusable ingestion, scoring, notification preview, triage actions, persisted conversations, SSE agent streaming, and typed agent tool validation. It is not a generic AI app builder yet.

## What Works Today

AgentForge can generate and validate a complete local demo app:

- A FastAPI backend with async SQLAlchemy models for provider runs, records, scores, notification previews, action history, conversations, and messages.
- A React + TypeScript frontend with operations, scoring, notification preview, action history, and agent chat panels.
- A fixture provider and adapter that make tests deterministic and avoid live APIs.
- A scoring/explanation pipeline that produces fit scores, labels, recommendations, drivers, and risks.
- Preview-only notification generation with accept/skip/save triage actions and append-only action history.
- An Agent Runtime Module with a scripted provider, deterministic tool calls, persisted conversation history, `/agent/chat`, and `/agent/chat/stream`.
- Typed tool argument validation with structured tool errors for unknown tools and invalid arguments.
- Generator, backend, frontend, and Playwright E2E coverage.

## Quickstart

```bash
pip install -e generator/
agentforge plan domain-packs/hybrid-scoring-demo/domain-pack.yaml
agentforge generate domain-packs/hybrid-scoring-demo/domain-pack.yaml --force
make validate
```

This installs the generator CLI, previews the module plan, generates the demo app, then runs all tests and the frontend build.

## Generated Demo Flow

The generated `hybrid-scoring-demo` app demonstrates this path:

1. Ingest fixture records through a provider interface.
2. Normalize raw provider payloads into stable records.
3. Score records deterministically and attach explanations.
4. Create preview-only notification payloads for scored records.
5. Record triage decisions and preserve an append-only action history.
6. Chat with the scripted Agent Runtime Module.
7. Stream agent events over SSE while tools run and assistant text appears.
8. Reload the app and recover persisted agent conversation history.

The agent can call generated tools such as `run_ingest`, `score_records`, `get_scored_records`, `create_notification_preview`, and `list_action_history`. Tool arguments are validated before execution; bad arguments and unknown tools become structured tool results instead of server crashes.

## What it generates

`agentforge generate` reads an App Blueprint (`domain-pack.yaml`) and emits a self-contained project directory. The `hybrid-scoring-demo` output includes:

- **FastAPI backend** with async SQLAlchemy ORM (SQLite for local dev, PostgreSQL for production)
- **React + TypeScript frontend** built with Vite
- **Integration adapter layer** — a fixture provider + normalizer that converts raw records into stable domain DTOs
- **Scoring pipeline** — deterministic fit score (0–100), label (high/medium/low), recommendation, drivers, and risks
- **Operations and triage UI** — ingest/score/preview controls, run history, scored records, notification previews, action status, and action history
- **Notification/Triage Module** — creates preview-only notification payloads and records accept/skip/save decisions without external delivery
- **Agent Runtime Module** — persisted conversations, a scripted LLM provider, deterministic tool calls, typed tool argument validation, SSE streaming, and a compact chat panel
- **Backend tests** (pytest, SQLite in-memory — no Postgres required)
- **Playwright E2E tests** proving the full UI workflow
- **GitHub Actions CI skeleton** with no live LLM or paid API dependency

## Validation Snapshot

Latest local validation for v0.3.1:

- `python -m pytest tests/generator/ -v` — 23 passed.
- Template backend tests — 59 passed.
- Template frontend `npm run build` and `npm run lint` — passed.
- `make validate` — passed.
- Live generated app Playwright E2E — 8 passed.

The generated app was also regenerated from `domain-packs/hybrid-scoring-demo/domain-pack.yaml`, so `examples/hybrid-scoring-demo/` reflects the current template and App Blueprint.

## How it works

1. **App Blueprint** (`domain-pack.yaml`) — describes your app's archetype (`ingestion_scoring_pipeline`, `agent_dashboard_app`, etc.), the feature modules it needs, and its data capabilities. Lives in `domain-packs/`.
2. **Generator** (`agentforge generate`) — reads the blueprint, selects the matching application template, substitutes app-name tokens, and emits a fully self-contained project directory.
3. **Generated app** — a real FastAPI + React project you can install, run, test, and deploy independently. It has no runtime dependency on AgentForge.

## What is not built yet

- Only one application template exists: `ingestion_scoring_pipeline` via the `fastapi-react` template.
- Token substitution is string-replace only — no per-capability code generation yet.
- Feature modules `workspace`, `observability_debug`, and `deploy_planner` are reported as gaps, not generated.
- Notification delivery is preview-only in v0.2; real Telegram/email/Slack adapters are future work.
- The Agent Runtime Module uses a scripted provider in v0.3.1; live LLM providers remain future work.
- SSE streaming is deterministic runtime event streaming, not live model token streaming.
- Tool schemas are currently hand-authored in the generated registry and represented in the App Blueprint; arbitrary schema-driven tool generation is future work.
- Production database is PostgreSQL; the generator does not yet emit migration scripts.
- No guided UI — the generator is CLI-only.
- `examples/hybrid-scoring-demo/` is a **committed snapshot** of the generated output; it is regenerable (see [Reproducibility](#reproducibility)).

## Version History

- **v0.1** — initial generator, App Blueprint loading, FastAPI/React template, fixture provider, run history, scoring, and deterministic tests.
- **v0.1.1** — developer-experience hardening: package metadata, Makefile validation, public repo ignore rules, and generated README behavior.
- **v0.1.2** — public documentation polish and terminology cleanup around App Blueprints, Application Templates, Feature Modules, Integration Adapters, and Test Harnesses.
- **v0.2** — Notification/Triage Module: notification previews, current action state, append-only action history, preview/action UI, and generator support for `triage_ui`.
- **v0.3** — Agent Runtime Module: scripted provider, tool registry, `/agent/chat`, conversation/message persistence, chat UI, and deterministic agent tests.
- **v0.3.1** — Agent Runtime hardening: `/agent/chat/stream` SSE events, frontend streaming consumption, typed tool validation, structured tool errors, and expanded E2E coverage.

## Terminology

| Public term | Config / internal term | Meaning |
|---|---|---|
| App Blueprint | `domain-pack` | Machine-readable YAML describing app archetype, capabilities, adapters, UI surfaces, and tests |
| Application Template | `template` | The reusable FastAPI/React source tree copied and parameterized by the generator |
| Feature Module | shell module | A reusable capability area — pipeline, scoring, notifications, agent runtime, etc. |
| Agent Runtime Module | `agent_runtime` | Optional scripted chat/tool-calling runtime with persisted conversations, SSE events, and typed tool validation |
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
