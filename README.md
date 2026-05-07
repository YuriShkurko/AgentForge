# AgentForge

AgentForge is a code generator that turns a **Domain Pack** (a YAML specification describing what your app does) into a runnable **Product Shell app** — a full-stack FastAPI + React application wired up with database models, API routes, a scoring engine, an operations UI, and a Playwright E2E test suite.

```
Domain Pack (YAML)  +  Product Shell Template  →  Generated App
```

## How it works

1. **Domain Pack** — you write a `domain-pack.yaml` that describes your app's archetype (`ingestion_scoring_pipeline`, `agent_dashboard_app`, etc.), the shell modules you need (`pipeline`, `scoring_explanation`, `operations_ui`, …), and your data capabilities.
2. **Generator** — `agentforge generate` reads the pack, selects the right template, substitutes app-name tokens, copies the CI skeleton, and emits a fully self-contained app directory.
3. **Generated App** — a real FastAPI + React project you can install, run, test, and deploy independently. It has no dependency on AgentForge at runtime.

## What v0.1 proves

- A single Domain Pack (`domain-packs/hybrid-scoring-demo/domain-pack.yaml`) generates a working app in `examples/hybrid-scoring-demo/`.
- The generated app passes 40 backend tests (pytest, SQLite in-memory) and builds/lints cleanly (Vite + ESLint).
- The generator itself passes 20 unit/snapshot tests.
- All five Playwright E2E tests pass against the live stack.
- The generator explicitly reports unsupported modules as gaps rather than silently skipping or faking them.

## Current limitations

- Only one archetype template exists: `ingestion_scoring_pipeline` via the `fastapi-react` template.
- Token substitution is string-replace only — no per-capability code generation yet.
- Modules `workspace`, `observability_debug`, `triage_ui`, and `deploy_planner` are reported as gaps, not generated.
- Production database is PostgreSQL; the generator does not yet emit migration scripts.
- No guided UI — the generator is CLI-only.
- `examples/hybrid-scoring-demo/` is a **committed snapshot** of the generated output; it is regenerable and should be treated as disposable (see [Reproducibility](#reproducibility)).

## Quickstart

### 1 — Install the generator

```bash
pip install -e generator/
```

### 2 — Preview what will be generated

```bash
agentforge plan domain-packs/hybrid-scoring-demo/domain-pack.yaml
```

### 3 — Generate the demo app

```bash
agentforge generate domain-packs/hybrid-scoring-demo/domain-pack.yaml --force
# output: examples/hybrid-scoring-demo/
```

### 4 — Run generator tests

```bash
pytest tests/generator/ -v
```

### 5 — Run the generated backend tests

```bash
cd examples/hybrid-scoring-demo/backend
pip install -r requirements-dev.txt
pytest -v
```

### 6 — Build and lint the generated frontend

```bash
cd examples/hybrid-scoring-demo/frontend
npm install
npm run build
npm run lint
```

### 7 — Run Playwright E2E (requires running stack)

```bash
cd examples/hybrid-scoring-demo/frontend
# In separate terminals: start backend and frontend first (see generated README)
npm run test:e2e
```

### All-in-one via Makefile

```bash
make validate          # run all tests and build steps
make generate-demo     # regenerate examples/hybrid-scoring-demo
make test-generator    # generator unit tests
make test-backend      # generated app backend tests
make run-backend       # start backend dev server
make run-frontend      # start frontend dev server
make run-e2e           # run Playwright E2E
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
├── domain-packs/            # Domain Pack YAML files
│   └── hybrid-scoring-demo/ # the v0.1 proof-of-concept pack
├── templates/               # Product Shell templates
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

`examples/hybrid-scoring-demo/` is a generated snapshot committed for convenience. It can be fully regenerated from its domain pack:

```bash
rm -rf examples/hybrid-scoring-demo
agentforge generate domain-packs/hybrid-scoring-demo/domain-pack.yaml
```

The generator skips `__pycache__`, `node_modules`, `dist`, and `.venv` — those are never committed.

## Documentation

- [Domain Pack Specification](docs/DOMAIN_PACK_SPEC.md)
- [Architecture](docs/AGENTFORGE_V0_ARCHITECTURE.md)
- [Archetype Model](docs/ARCHETYPE_MODEL.md)
- [Roadmap](docs/AGENTFORGE_ROADMAP.md)
