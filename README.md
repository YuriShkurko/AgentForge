# AgentForge

AgentForge is a local-first Builder that turns a plain-English app idea into a runnable FastAPI + React demo on your machine, with an agent-first planning workspace, deterministic generation, and safe local controls for validating, generating, checking, starting, and opening the app.

## Who It Is For

- Developers prototyping internal tools or agentic product demos.
- Builders who want to turn a workflow idea into a local full-stack demo without setting up cloud infrastructure.
- People evaluating local AI-assisted app generation with explicit review, deterministic outputs, and no deployment by default.

## Current Capabilities

- Builder Agent Workspace with a main assistant canvas, Plan / Build / Run flow, compact right-rail HUD, and Advanced YAML/CLI/log surfaces.
- Scripted planner by default, with optional live OpenAI planning behind environment flags.
- Model-driven Blueprint proposals from plain-English ideas, including bounded entities, fields, imports, providers, pages, workflow actions, seed data, and UI hints.
- Explicit Apply / Reject review before a proposal changes the in-memory Builder draft.
- Blueprint validation through the same Python schema used by the CLI.
- Local app generation into sandboxed run directories.
- Generated app checks through the fixed `make validate` target.
- One-click Builder actions to start backend/frontend services and open the generated app.
- Deterministic generated app output with stable naming, domain-aware copy, seed data, tests, and local validation commands.
- Local safety boundaries: no arbitrary shell, no GitHub automation, no deployment, no hidden file mutation, and no live LLM in the default path.

## Quickstart

Assumptions: Python 3.12+, Node 18+, `pip`, `npm`, and a shell that can run the repo `Makefile` targets. Install the generator package from the repository root:

```bash
pip install -e generator/
agentforge serve-builder
```

Open the local URL printed by `agentforge serve-builder`. Describe an app in the Builder, review the proposed plan, click **Apply**, then use the Builder's Plan / Build / Run actions:

```text
Validate Blueprint -> Generate app locally -> Run checks -> Start app -> Open app
```

The default path is fully local and scripted. To opt into live planner assistance for local Builder development only:

```bash
export AGENTFORGE_ASSISTANT_PROVIDER=openai
export OPENAI_API_KEY=...
# optional
export AGENTFORGE_ASSISTANT_LLM_MODEL=gpt-4o-mini
agentforge serve-builder
```

Live mode only helps produce a bounded planning spec. The deterministic Builder still creates and validates the Blueprint, and you still choose Apply or Reject before anything changes.

## Builder Flow

The Builder starts with an assistant prompt: describe the app you want, or answer the assistant's clarifying questions when the idea is too vague. The planner returns a human-readable proposal with the app shape, data model, imports/providers when relevant, workflow actions, assumptions, warnings, and changed fields.

Review happens before mutation. **Apply** installs the proposal into the in-memory Builder draft after validation; **Reject** leaves the draft untouched. From there, the Plan / Build / Run workspace guides the local sequence: validate the Blueprint, generate the app, run generated checks, start services, and open the frontend.

Advanced surfaces remain available for developers. YAML, equivalent CLI commands, raw logs, planner diagnostics, generated paths, and detailed run output live behind Advanced instead of blocking the main flow. The right rail is a compact HUD for mode, next step, app summary, service status, and recent history.

## Generated App Flow

Generated apps are local FastAPI + React demos. A model-driven Blueprint can define bounded entities, fields, pages, workflow actions, CSV/JSON imports, optional read-only providers, seed data, and UI presentation hints. The generator emits a backend, frontend, `Makefile`, generated tests, `app-model.json`, and run instructions.

The backend uses FastAPI, SQLite persistence, generated SQLAlchemy/Pydantic models, CRUD routes, import/workflow endpoints, and optional read-only provider sync paths. The frontend uses React with generated dashboard, entity, form, import/provider, and workflow surfaces. Seed data lets the app show a meaningful local demo immediately.

Generated apps are intentionally demo-oriented. Static demo families include scripted agent chat and workspace widgets; the newer model-driven path focuses on CRUD/workflow/import/provider surfaces and does not yet ship generated-app runtime agents.

## Safety Boundaries

- No deployment by default.
- No GitHub repo creation, pushing, OAuth, or remote automation.
- No arbitrary shell from the Builder.
- Local Builder generation stays under `.tmp/builder-runs/<safe-run-id>/app`.
- Builder-run commands are allowlisted: `make validate`, `make run-backend`, and `make run-frontend`.
- Optional live LLM use is only for planning and is off by default.
- Generated app subprocesses get a secret-stripped environment.
- Existing-repo tools are planning-first and do not mutate target repos by default.
- Generated apps are local demos, not production-ready deployed services.

## Architecture Overview

```text
User
  -> Builder UI
  -> Planner Assistant
  -> Blueprint / DomainPack
  -> Local-run Server
  -> Generator
  -> Generated App
```

The Builder UI in `builder/` is a local browser workspace. The planner server in `generator/agentforge/planner/` serves scripted planning, optional live planning, proposal validation, and local-run endpoints. Blueprint data is validated through `DomainPack` models in `generator/agentforge/pack.py`. The generator turns validated packs into deterministic FastAPI + React file trees. Generated apps run locally from `.tmp/builder-runs/` or from explicit CLI output paths.

## Development And Testing

Useful validation commands from the repository root:

```bash
python -m pytest tests/generator/ -v
python -m pytest tests/generator/ -q --ignore=*_browser.py
python -m pytest tests/generator/test_builder_assistant_browser.py tests/generator/test_builder_local_run_browser.py -q
node --check builder/app.mjs
node --check builder/blueprint-builder.mjs
```

Generated apps include their own validation target:

```bash
cd .tmp/builder-runs/<safe-run-id>/app
make validate
make run-backend
make run-frontend
```

The root `make validate` target validates the committed hybrid-scoring demo path. Scribe is the work-graph source of truth for AgentForge planning and reconciliation; run the local Scribe lint/check before handoff when Scribe is available.

## Roadmap And Limitations

- Generated-app runtime agents are not shipped for the model-driven path yet.
- Generated apps are improving, but they are still local demos rather than production systems.
- Builder UX persistence and progress polish are next; generated-app intelligence v2 is future work.
- The README reflects the shipped local product, not future deployment automation.
- Broad arbitrary app generation, cloud provisioning, GitHub automation, hosted SaaS behavior, and production deployment remain out of scope for the current local product.

## Docs

- [Docs Index](docs/README.md)
- [Getting Started](docs/GETTING_STARTED.md)
- [Demo Guide](docs/DEMO_GUIDE.md)
- [Command Reference](docs/COMMAND_REFERENCE.md)
- [Safety Model](docs/SAFETY_MODEL.md)
- [App Blueprint Specification](docs/DOMAIN_PACK_SPEC.md)
- [AgentForge v0 Architecture](docs/AGENTFORGE_V0_ARCHITECTURE.md)
- [Blueprint Builder README](builder/README.md)
