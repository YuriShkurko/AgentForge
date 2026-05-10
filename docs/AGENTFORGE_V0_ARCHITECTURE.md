# AgentForge v0 Architecture

AgentForge v0 extracts the common reusable application foundation from Business Insight and AI Job Radar without forcing every app into a chat-agent shape.

Business Insight is an agentic chat/workspace/dashboard app. AI Job Radar is a deterministic ingestion, scoring, triage, notification, observability, and debug pipeline. The shared foundation is therefore broader than an agent runtime.

**Terminology used in this document** (see also [README terminology table](../README.md#terminology)):

- **Application Template** (internal: Product Shell) — the reusable app foundation: APIs, providers/adapters, persistence, run history, deterministic tests, frontend surfaces, notifications, observability, and local/dev workflow.
- **Feature Modules** (internal: shell modules) — capability areas wired by the generator based on the app archetype. Optional modules are only included when the App Blueprint declares them.
- **App Blueprint** (internal: domain-pack) — the machine-readable YAML describing one app's identity, archetype, required modules, capabilities, schemas, and tests.

AgentForge v0 module language:

- **Agent Runtime Module** (Agent Shell): optional module for conversational UX, tool calling, streaming, guardrails, scripted LLM testing, and workspace/widget operations.
- **Dashboard/Workspace Module** (Workspace Shell): optional module for persisted widgets, layout, dashboard sections, compatibility validation, and presentation mode.
- **Ingestion Pipeline Module** (Pipeline Shell): optional module for provider runs, normalization, dedupe, scoring, replay, background jobs, and operational controls.
- **Triage/Action Module** (Triage/Notification Shell): optional module for surfaced recommendations, action loops, notifications, and persisted decisions.

## Cross-Pack Comparison

| Axis | Business Insight | AI Job Radar | Architecture implication |
| --- | --- | --- | --- |
| Users/personas | Local SMB owners/managers | Developer/job seeker | Persona belongs in Domain Pack. |
| App type | Agentic business dashboard | Job discovery/scoring/triage pipeline | App archetype must be explicit. |
| Data sources | Reviews, competitors, demo signals, LLM providers | Job boards/email/web, CV/repo profile, Telegram, DB | Provider/adapter contracts are reusable; schemas are domain-specific. |
| Tools/capabilities | Agent tools exposed to chat and widgets | Operational endpoints/services, not agent tools | Use `capabilities` as the general term; `tools` only when agent-callable. |
| Adapters/providers | Review providers, LLM providers, tool adapters | Job source providers, normalization parsers, scoring strategies, notifier | Provider run logging and normalization are shared. |
| Workflows | Ask analytics, build dashboard, pin/remove/reorder widgets | Ingest, normalize, score, dispatch, triage, debug | Workflows should support agent and pipeline triggers. |
| UI surfaces | Chat, dashboard widgets, presentation mode | Ops panel, tables, scored cards, triage queue, card image | Use `ui_surfaces`; widgets are a subtype. |
| Testing | Backend tools, scripted LLM, widget compatibility, Playwright | Backend parser/scoring/strictness tests, build/lint; no frontend tests found | Deterministic tests are mandatory; Playwright belongs in v0 sample. |
| Observability | App/test visibility mostly around agent/workspace flows | Prometheus, Grafana, debug MCP, provider runs | Observability shell should be reusable. |
| Notification/action loop | Workspace events and dashboard actions | Telegram alerts, webhook/review decisions, triage decisions | Action loops generalize well. |
| LLM/agent usage | Central: chat, tool routing, streaming, scripted LLM | Not active for runtime decisions | Agent runtime must be optional. |
| Deployment/dev workflow | Backend/frontend tests and E2E | Makefile, Docker Compose, worker, metrics, dev UI | v0 should generate a local runnable app and CI skeleton, not deployment automation. |

## Shared Reusable Shell Candidates

### Provider/Adapter Interfaces

Why reusable: both packs isolate external or messy data behind provider/adapters.

Proved by: Business Insight review providers and AI Job Radar job source providers/parsers.

Generalize: provider result envelope, source name, raw payload, normalized DTO, provider status/errors, deterministic fixture provider.

Keep specific: review schema, job schema, LinkedIn parser, Outscraper mapping, scoring semantics.

v0 priority: high.

### Run History

Why reusable: every provider-backed app needs inspectable runs, timestamps, stats, and errors.

Proved by: AI Job Radar `provider_runs`; Business Insight has workflow/test visibility but less formal run history.

Generalize: `runs` table/schema, run status enum, stats JSON, error field, frontend run table.

Keep specific: provider names, provider stats shape, retry policy.

v0 priority: high.

### Deterministic Mock/Demo Data

Why reusable: both packs need local/CI behavior without paid APIs or live LLMs.

Proved by: Business Insight mock/offline/scripted providers; AI Job Radar mock provider and parser fixtures.

Generalize: fixture provider registration, seed loader convention, test data mode.

Keep specific: fixture content and demo narratives.

v0 priority: high.

### Scoring/Explanation Schema

Why reusable: both apps turn evidence into a user-facing assessment with reasons.

Proved by: Business Insight health/opportunity/action outputs; AI Job Radar fit/strictness/recommendation.

Generalize: score, label/recommendation, summary, drivers, risks, confidence, limitations, evidence.

Keep specific: score formulas, business health dimensions, job fit heuristics.

v0 priority: high.

### Notification/Action Loop

Why reusable: surfaced outputs should let users act and persist the outcome.

Proved by: AI Job Radar Telegram/triage decisions; Business Insight widget lifecycle and dashboard actions.

Generalize: action definitions, delivery channel, decision persistence, idempotency/dedupe key.

Keep specific: Telegram copy/buttons, APPLY/MAYBE/SKIP, dashboard widget commands.

v0 priority: medium.

### Observability/Metrics

Why reusable: generated apps need visibility into provider runs, scoring, notifications, and failures.

Proved by: AI Job Radar Prometheus/Grafana/debug MCP; Business Insight deterministic E2E traces.

Generalize: `/metrics`, counters/histograms, run status table, debug read APIs/tools.

Keep specific: metric labels and dashboards.

v0 priority: medium.

### Debug Inspection Tools

Why reusable: local agents and developers need safe read-only inspection.

Proved by: AI Job Radar debug MCP.

Generalize: read-only DB snapshots, recent runs, recent normalized rows, parser preview hooks.

Keep specific: domain parser previews.

v0 priority: medium.

### CI/Local Validation

Why reusable: generated apps need known checks.

Proved by: both packs' backend/frontend test commands.

Generalize: generated test scripts, fixture-only CI, no live API/LLM dependency.

Keep specific: command names and test files.

v0 priority: high.

### Frontend Operation Surfaces

Why reusable: both apps need cards, tables, status chips, filters, and action controls.

Proved by: Business Insight widgets/dashboard and AI Job Radar ops/triage UI.

Generalize: card, table, status chip, action button, run history table, empty state pattern.

Keep specific: visual content, dashboard sections, job card fields, review widgets.

v0 priority: medium.

### Optional Agent/Chat Runtime

Why reusable: essential for Business Insight, not currently supported by AI Job Radar.

Proved by: Business Insight.

Generalize: chat API, persisted conversations/messages, tool registry, scripted LLM provider, guardrails, and later streaming events.

Keep specific: prompts, domain routing, tool schemas.

v0 priority: optional for v0.1 sample.

### Optional Workspace/Widget Runtime

Why reusable: useful for dashboard apps, not for all pipeline apps.

Proved by: Business Insight.

Generalize: widget persistence, source capability compatibility, reorder/remove/clear events.

Keep specific: widget renderers and domain data shapes.

v0 priority: defer as a full module; include only if sample app chooses dashboard archetype.

## Agent Runtime vs Application Template

The Agent Runtime Module is not mandatory for every generated app. It is one optional feature module for apps where conversational UX is central.

Business Insight uses:

- Agent Runtime Module (Agent Shell)
- Dashboard/Workspace Module (Workspace Shell)
- Integration Adapter Layer (Provider/Adapter Shell)
- Test Harness (Deterministic Test Shell)

AI Job Radar uses:

- Ingestion Pipeline Module (Pipeline Shell)
- Triage/Action Module (Triage/Notification Shell)
- Integration Adapter Layer (Provider/Adapter Shell)
- Operations UI Module (Operations UI Shell)
- Observability/Debug Module

AgentForge v0 generates apps from archetypes, not from an assumption that every product is an agent.

## AgentForge v0.1 Scope

Recommended v0.1 generated app: a tiny hybrid sample app.

Purpose: prove reusable pieces shared by both packs without over-generalizing into a full agent framework.

Generated app includes:

- FastAPI backend.
- React frontend.
- One provider interface and one deterministic fixture provider.
- One adapter that normalizes provider data into a stable domain DTO.
- Run history persistence for provider/capability runs.
- One scoring/explanation capability using deterministic logic.
- One UI surface that lists runs and scored records.
- One notification/action loop stub that records current action state and append-only action history without real external delivery.
- Optional command panel or simple chat facade that calls one capability; no live LLM required.
- Deterministic tests for provider, adapter, scoring, run history, and action persistence.
- One Playwright happy path proving UI can trigger ingest/score and render the result.
- Docker Compose for local database and app services.
- CI skeleton that runs backend tests, frontend tests/build, and Playwright.

v0.1 should not generate Business Insight or AI Job Radar directly. It should generate a minimal sample that demonstrates the shell modules those packs have in common.

## AgentForge v0.2 Notification/Triage Scope

v0.2 promotes the v0.1 action stub into a reusable preview-only Notification/Triage Module:

- Notification previews are generated from scored records and persisted with delivery metadata.
- Delivery is a no-op preview adapter; no Telegram, email, Slack, live LLM, or paid API call is made.
- Triage actions update the current action state and append an immutable history event.
- The frontend exposes preview cards, action buttons, current state, and action history.
- `notification_action` and `triage_ui` are supported template modules; `workspace`, `observability_debug`, and `deploy_planner` remain explicit gaps.

## AgentForge v0.3 Agent Runtime Scope

v0.3 adds a minimal Agent Runtime Module over the deterministic generated app:

- Conversations and messages are persisted in app-local tables.
- The LLM provider is scripted for deterministic tests; no live LLM or paid API is required.
- The tool registry exposes a small set of generated tools such as ingest, score, list scored records, create notification previews, and list action history.
- The chat endpoint executes scripted tool calls, persists tool events, and returns an assistant response.
- The frontend adds a compact chat panel with visible tool activity and persisted conversation restore.
- Streaming/SSE, Dashboard/Workspace Module behavior, guided blueprint building, multi-agent orchestration, and long-term memory remain out of scope.

## Repo Structure Proposal

```text
docs/
  DOMAIN_PACK_SPEC.md
  AGENTFORGE_V0_ARCHITECTURE.md
  AGENTFORGE_ROADMAP.md
  ARCHETYPE_MODEL.md
domain-packs/
  business-insight/
  ai-job-radar/
examples/
  hybrid-scoring-demo/
shells/
  provider-adapter/
  pipeline/
  scoring-explanation/
  notification-action/
  operations-ui/
  agent-runtime/
  workspace-runtime/
templates/
  fastapi-react/
  docker-compose/
  ci/
generator/
  agentforge/
tests/
  generator/
  snapshots/
```

Use `shells/` for reusable module specifications and templates, `examples/` for generated examples, and `generator/` for the CLI/scaffolder implementation.

## Domain Pack Spec Updates Recommended

After comparing both packs, `DOMAIN_PACK_SPEC.md` should evolve beyond the Business Insight-centric contract:

- Add `app_archetype`.
- Add `required_shell_modules`.
- Add `optional_shell_modules`.
- Add `capabilities` as a superset of agent-callable `tools`.
- Add `ui_surfaces` as a superset of persisted `widgets`.
- Make `tool_widget_compatibility` optional and only required when `workspace_runtime` is enabled.
- Add `run_history` expectations for provider/pipeline apps.
- Add `notification_actions` for triage/action loops.
- Add `observability` and `debug_tools` sections.
- Clarify that `prompts` can be empty or `not_present` when no active agent/LLM path exists.

Do not update the core spec until v0.1 shape is accepted; these are architecture recommendations.

## Risks

- Over-abstraction before one generated app works.
- Forcing deterministic pipeline apps into chat-agent UX.
- Building a generic UI builder before generator contracts are stable.
- Treating provider endpoints as agent tools when no agent runtime exists.
- Making deployment automation unsafe or too broad.
- Generating code without deterministic validation.
- Collapsing widgets and UI surfaces into one concept.
- Hiding project-specific semantics behind generic scoring names.

