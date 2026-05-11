# AgentForge

AgentForge is an opinionated generator for local-first full-stack AI/product apps. It reads a structured **App Blueprint** (`domain-pack.yaml`) and produces a runnable FastAPI + React project with provider adapters, deterministic scoring, notification triage, an optional scripted Agent Runtime Module, a persisted Dashboard/Workspace Module, tests, and CI-ready project structure.

The project is intentionally narrow right now. It proves reusable application modules, a local Blueprint Builder, and a scripted App Blueprint planner before adding live LLM integrations, deployment automation, repository conversion, or hosted builder flows. The generated demo and planner run locally and deterministically. No paid API or live LLM key is required.

```text
App Blueprint YAML + Application Template = Generated App
```

**Current version:** v0.7 adds an analysis-only Repo Analyzer. `agentforge analyze-repo <path>` inspects a local repository and reports stack signals, AgentForge module compatibility, migration risks, an advisory migration plan, and a draft App Blueprint seed without modifying the analyzed repository.

## Table of Contents

- [What You Can Do Today](#what-you-can-do-today)
- [Quickstart](#quickstart)
- [Blueprint Builder](#blueprint-builder)
- [Scripted Planner](#scripted-planner)
- [Repo Analyzer](#repo-analyzer)
- [Generated Demo Flow](#generated-demo-flow)
- [What Gets Generated](#what-gets-generated)
- [How AgentForge Works](#how-agentforge-works)
- [Commands](#commands)
- [Running the Generated App](#running-the-generated-app)
- [Validation Snapshot](#validation-snapshot)
- [What Is Not Built Yet](#what-is-not-built-yet)
- [Terminology](#terminology)
- [Repository Layout](#repository-layout)
- [Reproducibility](#reproducibility)
- [Version History](#version-history)
- [Further Reading](#further-reading)

## What You Can Do Today

AgentForge can generate and validate one complete local demo app, `hybrid-scoring-demo`.

The demo proves these reusable pieces:

- FastAPI backend with async SQLAlchemy models.
- React + TypeScript frontend built with Vite.
- Fixture provider and normalization adapter.
- Deterministic scoring and explanation output.
- Preview-only notification generation.
- Triage actions with append-only action history.
- Scripted Agent Runtime Module with persisted conversations.
- Server-sent event streaming at `/agent/chat/stream`.
- Typed tool argument validation and structured tool errors.
- Persisted generic workspace widgets.
- Generator tests, backend tests, frontend build/lint, and Playwright E2E coverage.

The v0.6 builder can draft, clarify, refine, and validate App Blueprints through the local scripted planner, while still supporting the static v0.5 manual-editing path.

## Quickstart

Install the generator, inspect the demo plan, generate the app, and run validation:

```bash
pip install -e generator/
agentforge plan domain-packs/hybrid-scoring-demo/domain-pack.yaml
agentforge generate domain-packs/hybrid-scoring-demo/domain-pack.yaml --force
make validate
```

The generated app appears in:

```text
examples/hybrid-scoring-demo/
```

## Blueprint Builder

The Blueprint Builder is a static local developer tool. It lives in [builder/](builder/).

Open it directly in your browser for static/manual mode:

```text
builder/index.html
```

No dev server is required for manual editing.

For scripted planner assistance, run the local builder server and open the printed URL:

```bash
agentforge serve-builder
```

Use the builder to:

- enter app metadata, display name, description, and target persona;
- choose an app archetype;
- select supported Feature Modules;
- see future/planned modules as disabled options;
- configure deterministic defaults such as `preview_only`, `scripted`, fixture provider mode, action labels, and workspace mode;
- preview valid App Blueprint YAML;
- copy or download `domain-pack.yaml`;
- see the `agentforge plan <file>` and `agentforge generate <file>` commands to run next;
- draft a blueprint from a short idea when the local planner server is running;
- answer clarifying questions for vague ideas;
- refine an existing draft with bounded instructions such as `add workspace widgets`;
- validate planner output through the Python generator schema.

The builder does not write files automatically, call live LLMs or live provider APIs, analyze repositories, convert apps, deploy infrastructure, or modify code autonomously. `agentforge plan` remains the source of truth for validation.

You can also create a starter blueprint from the CLI:

```bash
agentforge init-blueprint my-app --optional-module agent_runtime --optional-module workspace
agentforge plan domain-packs/my-app/domain-pack.yaml
```

## Scripted Planner

v0.6 adds a Python planner contract under `generator/agentforge/planner/`, a deterministic scripted backend, a local builder server, and a small CLI draft helper.

The scripted planner can:

- return a structured `PlannerResult`;
- draft deterministic App Blueprints for supported archetypes;
- ask clarifying questions for vague ideas;
- refine an existing blueprint for bounded requests such as adding `agent_runtime` or `workspace`;
- validate every draft through the generator schema before returning `status="draft"`.

CLI draft example:

```bash
agentforge draft-blueprint --idea "triage support tickets and create preview notifications" --out domain-packs/support-triage/domain-pack.yaml
agentforge plan domain-packs/support-triage/domain-pack.yaml
```

The scripted planner does not call live LLMs, make network requests, modify repositories, run generation, or replace `agentforge plan`. It writes a file only when the user explicitly passes `--out`.

## Repo Analyzer

v0.7 adds a deterministic, local-only repository analyzer:

```bash
agentforge analyze-repo path/to/repo
agentforge analyze-repo path/to/repo --format md --output repo-analysis.md
agentforge analyze-repo path/to/repo --json
```

The analyzer is advisory and analysis-only. It does not modify the target repository, generate patches, convert source code, call live LLMs, call external APIs, require internet access, or inspect secret values. It ignores generated/vendor/local directories such as `node_modules`, `.venv`, `.git`, `dist`, `build`, `.next`, `.scribe`, and `.tmp`.

Reports include repository basics, detected stack/config/test/devops/AI/observability signals, architecture signals, AgentForge module compatibility statuses (`compatible`, `partial`, `missing`, `conflict`, `unknown`), likely archetype candidates, risks/blockers, a phased advisory migration plan, and an optional draft App Blueprint seed for review.

See [docs/REPO_ANALYZER.md](docs/REPO_ANALYZER.md) for details.

## Generated Demo Flow

The generated `hybrid-scoring-demo` app demonstrates a full deterministic workflow:

1. Ingest fixture records through a provider interface.
2. Normalize raw provider payloads into stable records.
3. Score records and attach deterministic explanations.
4. Create preview-only notification payloads for scored records.
5. Record triage decisions and preserve action history.
6. Chat with the scripted Agent Runtime Module.
7. Stream agent events over SSE while tools run.
8. Ask the scripted agent to pin compatible tool results into the workspace.
9. Reload the app and recover persisted conversations and workspace widgets.

The agent can call generated tools such as `run_ingest`, `score_records`, `get_scored_records`, `create_notification_preview`, `list_action_history`, and `pin_widget`. Tool arguments and widget compatibility are validated before execution, so invalid arguments, unknown tools, and incompatible widget pins become structured tool results instead of server crashes.

## What Gets Generated

`agentforge generate` reads an App Blueprint and emits a self-contained project directory.

The current `fastapi-react` Application Template includes:

| Area | Generated output |
| --- | --- |
| Backend | FastAPI app with async SQLAlchemy, SQLite for local dev, and PostgreSQL-ready configuration |
| Frontend | React + TypeScript app built with Vite |
| Providers | Fixture provider interface and deterministic sample data |
| Adapters | Normalization layer from raw provider records to stable DTOs |
| Scoring | Deterministic fit score, label, recommendation, drivers, risks, and explanation |
| Operations UI | Ingest, score, run history, and scored records views |
| Notification/Triage | Preview-only notifications, action status, and action history |
| Agent Runtime | Scripted provider, persisted conversations, tool calls, typed validation, and SSE streaming |
| Workspace | Persisted generic widgets with source-tool/widget compatibility checks |
| Tests | Backend pytest suite, generator tests, and Playwright E2E coverage |
| CI | GitHub Actions skeleton with no live LLM or paid API dependency |

## How AgentForge Works

AgentForge has three main pieces:

1. **App Blueprint**: a YAML file that describes the app domain, archetype, Feature Modules, capabilities, providers, adapters, UI surfaces, tests, and future gaps.
2. **Generator**: the `agentforge` CLI reads the blueprint, selects modules, validates gaps, and copies/parameters the Application Template.
3. **Generated App**: a normal FastAPI + React project that can run, test, and evolve independently.

The important command flow is:

```bash
agentforge plan path/to/domain-pack.yaml
agentforge generate path/to/domain-pack.yaml
```

`agentforge plan` is the source of truth for module support and known gaps.

## Commands

Common commands from the repo root:

```bash
make validate          # generator tests + generated backend tests + frontend build/lint
make generate-demo     # regenerate examples/hybrid-scoring-demo
make test-generator    # generator unit tests only
make test-backend      # generated app backend tests only
make run-backend       # start generated backend dev server on :8000
make run-frontend      # start generated frontend dev server on :5173
make run-e2e           # run Playwright E2E; requires the live stack
```

Generator CLI:

```bash
agentforge plan domain-packs/hybrid-scoring-demo/domain-pack.yaml
agentforge generate domain-packs/hybrid-scoring-demo/domain-pack.yaml --force
agentforge init-blueprint my-app --optional-module agent_runtime
agentforge analyze-repo path/to/local/repo --format md
```

## Running the Generated App

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

### Full Stack With Docker Compose

```bash
cd examples/hybrid-scoring-demo
docker-compose up
```

## Validation Snapshot

Latest local validation for v0.5:

| Command | Result |
| --- | --- |
| `python -m pytest tests/generator/ -v --basetemp=.tmp/pytest-generator-v05` | 29 passed |
| `make validate` | passed |
| Generated backend tests | 72 passed |
| Generated frontend build | passed |
| Generated frontend lint | passed |

Playwright was not rerun for v0.5 because the generated app flows were not changed. Existing Playwright coverage remains in the generated frontend and can be run with:

```bash
make run-e2e
```

## What Is Not Built Yet

AgentForge is still early and deliberately constrained.

Not built yet:

- Live LLM provider integration.
- Repository analysis or repository conversion.
- Autonomous code modification.
- Deployment planning or production mutation.
- Real Telegram/email/Slack notification delivery.
- Per-capability code generation from arbitrary schemas.
- Database migration generation.
- Multiple mature Application Templates.
- Business Insight-specific workspace renderers such as `money_flow`, `health_score`, or `signal_timeline`.

Current limitations:

- The only full Application Template is `fastapi-react`.
- Some modules are represented as planned/future gaps.
- Token substitution is still simple string replacement.
- The v0.5 builder mirrors a small schema subset in browser code for live YAML preview; the generator schema and `agentforge plan` remain authoritative.
- `examples/hybrid-scoring-demo/` is a committed generated snapshot for convenience.

## Terminology

| Public term | Config/internal term | Meaning |
| --- | --- | --- |
| App Blueprint | `domain-pack` | YAML definition of one app domain |
| Application Template | `template` | Reusable source tree copied and parameterized by the generator |
| Feature Module | shell module | Reusable capability area such as pipeline, scoring, notifications, agent runtime, or workspace |
| Integration Adapter | provider/adapter | Boundary that normalizes external or fixture data into stable app records |
| Agent Runtime Module | `agent_runtime` | Optional scripted chat/tool runtime with persisted conversations, SSE events, and typed tool validation |
| Dashboard/Workspace Module | `workspace` | Optional persisted widget workspace with generic renderers and compatibility validation |
| Test Harness | deterministic test shell | Fixture-based tests that avoid live external APIs and LLMs |

## Repository Layout

```text
AgentForge/
  builder/                       Static local Blueprint Builder UI
  docs/                          Architecture, roadmap, and App Blueprint docs
  domain-packs/                  App Blueprint YAML files
    hybrid-scoring-demo/         Blueprint for the generated demo
  generator/                     Python package for the AgentForge CLI
    agentforge/
      analyzer.py                Analysis-only local Repo Analyzer
      blueprints.py              Starter blueprint helpers
      cli.py                     agentforge plan/generate/init-blueprint/analyze-repo
      generator.py               Copy and substitution logic
      modules.py                 Archetype to module selection
      pack.py                    Pydantic App Blueprint model
  templates/                     Application Templates
    fastapi-react/               FastAPI + React template
  examples/                      Generated output snapshots
    hybrid-scoring-demo/         Current generated demo app
  tests/
    generator/                   Generator and builder YAML tests
```

## Reproducibility

The generated demo is committed as a snapshot, but it can be regenerated from its App Blueprint:

```bash
agentforge generate domain-packs/hybrid-scoring-demo/domain-pack.yaml --force
```

The generator skips local build/runtime directories such as `__pycache__`, `node_modules`, `dist`, and `.venv`.

## Version History

| Version | Summary |
| --- | --- |
| v0.1 | Initial generator, App Blueprint loading, FastAPI/React template, fixture provider, run history, scoring, and deterministic tests |
| v0.1.1 | Developer-experience hardening: package metadata, Makefile validation, ignore rules, and generated README behavior |
| v0.1.2 | Public terminology cleanup around App Blueprints, Application Templates, Feature Modules, Integration Adapters, and Test Harnesses |
| v0.2 | Notification/Triage Module with previews, current action state, append-only action history, preview/action UI, and `triage_ui` support |
| v0.3 | Agent Runtime Module with scripted provider, tool registry, `/agent/chat`, persistence, chat UI, and deterministic agent tests |
| v0.3.1 | Agent Runtime hardening with `/agent/chat/stream`, SSE events, frontend streaming, typed tool validation, and structured tool errors |
| v0.4 | Dashboard/Workspace Module with persisted generic widgets, compatibility validation, agent pinning, remove/reorder APIs, and workspace UI |
| v0.4.1 | Workspace UI polish with clearer states, readable widget cards/renderers, and clearer agent pin success/failure activity |
| v0.5 | Simple static Blueprint Builder UI plus `agentforge init-blueprint`; generation remains CLI-first |
| v0.6 | Scripted AI-assisted Blueprint Builder with idea drafting, clarification, refinement, local schema validation, `serve-builder`, and `draft-blueprint`; generation remains CLI-first |
| v0.7 | Analysis-only Repo Analyzer with local stack detection, AgentForge module compatibility, archetype guesses, advisory migration plans, JSON/text/Markdown reports, and draft Blueprint seed output |

## Further Reading

- [App Blueprint Specification](docs/DOMAIN_PACK_SPEC.md)
- [AgentForge v0 Architecture](docs/AGENTFORGE_V0_ARCHITECTURE.md)
- [Archetype Model](docs/ARCHETYPE_MODEL.md)
- [Roadmap](docs/AGENTFORGE_ROADMAP.md)
- [Repo Analyzer](docs/REPO_ANALYZER.md)
- [Blueprint Builder README](builder/README.md)
