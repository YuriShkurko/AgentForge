# App Blueprint Specification (`domain-pack.yaml`)

An **App Blueprint** (config name: `domain-pack`) is the complete machine-readable definition of one app domain. Combined with an Application Template, it produces a runnable app.

**Application Template + App Blueprint = Generated App.**

The Application Template provides reusable runtime infrastructure: APIs, persistence, run history, integration adapters, deterministic test harness, frontend surfaces, notifications, observability, and local/dev workflow. The App Blueprint provides the variable surface: identity, archetype declaration, required/optional feature modules, capabilities, schemas, providers/adapters, workflows, UI surfaces, seed data, and tests.

The feature modules an app needs depend on its archetype. An agentic dashboard uses the Agent Runtime Module and Dashboard/Workspace Module. A pipeline app uses the Ingestion Pipeline Module and Scoring Module. A notification app uses the Triage/Action Module. The generator reads `app_archetype` and `required_shell_modules` to decide which modules to wire.

## Top-Level Fields

`name`: Stable machine name for the pack.

`display_name`: Human-readable product/domain name.

`version`: Pack contract version.

`extracted_from` *(optional)*: Source repo/path/date used for documentation-extracted packs.

`domain`: Basic domain metadata — `domain_name`, `app_type`, `target_users`, `product_purpose`, `main_user_goals`.

`app_archetype`: The archetype that drives module selection. One of:
- `agent_dashboard_app` — conversational dashboard with persistent workspace/widgets
- `ingestion_scoring_pipeline` — ops UI for ingest, normalize, score, inspect
- `notification_triage_app` — recommendations plus user decisions
- `hybrid_agent_pipeline` — chat or command UX over a deterministic pipeline
- `deploy_planner_app` — plan, validate, and stage deployment work *(future)*

`required_shell_modules`: List of feature modules the generator must wire. Example: `[pipeline, provider_adapter, scoring_explanation, operations_ui, persistence, test]`.

`optional_shell_modules`: Feature modules wired only when declared. Example: `[notification_action, observability_debug, agent_runtime]`.

`agent_shell_contract` *(agent_dashboard_app / hybrid_agent_pipeline only)*: Capabilities expected from the Agent Shell runtime — `chat`, `streaming_sse`, `tool_calling`, `persistent_conversations`, `persistent_workspace_widgets`, `workspace_events`, `dashboard_layout`, `guardrails`, `scripted_llm_testing`.

## Capability and Tool Fields

`capabilities`: All operational capabilities exposed by the app — endpoint operations, pipeline steps, scoring actions. Use `capabilities` as the general term for any app archetype. Each entry includes `name`, `purpose`, `input_summary`, `output_shape`, `mutates_state`, `data_mode`, `deterministic_test_safe`, `implementation_status`, and optional `source_files`.

`tools` *(agent_dashboard_app only)*: Agent-callable capabilities exposed to the chat/tool-calling runtime. A subset of `capabilities`. Each entry additionally includes `allowed_widget_types`. Only use `tools` when an agent runtime exists that can invoke them.

`widgets` *(agent_dashboard_app only)*: Renderable workspace widget types. Each entry includes `widget_type`, `renderer`, `compatible_source_tools`, `section`, `expected_data_shape`, `empty_state`, `implementation_status`.

`tool_widget_compatibility` *(required when `workspace_runtime` is enabled; empty map otherwise)*: Authoritative mapping from `source_tool` to allowed `widget_type` values. Generators use this map to produce validation that prevents an agent from pinning unrenderable widgets.

`ui_surfaces`: General UI surfaces the app exposes — tables, cards, triage queues, operations panels, dashboards. Covers both persisted workspace widgets and non-persistent operational views. Each entry includes `surface_type`, `renderer`, `data_source`, `section`, `expected_data_shape`, `empty_state`.

## Data Flow Fields

`providers`: Capability sources — where data or execution capability comes from. Mock providers, offline fixtures, external APIs, IMAP fetchers, notification channels. Each entry includes `name`, `class` or `interface`, `source`, `current_status`.

`adapters`: Normalization layers that convert provider output into stable domain DTOs. Each entry includes `name`, `purpose`, `normalized_shape` or `source_file`.

`run_history` *(ingestion_scoring_pipeline, notification_triage_app)*: Expectations for provider/capability run logging. Fields: `enabled`, `table_name`, `tracked_fields` (e.g. `[provider_name, started_at, finished_at, status, stats, error]`), `frontend_surface`.

`notification_actions` *(notification_triage_app, ingestion_scoring_pipeline)*: Action definitions for the notification/triage loop. Each action includes `name`, `trigger`, `delivery_channel`, `decision_states` (e.g. `[pending, sent, skipped]`), `dedupe_key`, `persistence_table`.

`observability` *(optional)*: Observability expectations. Fields: `prometheus_metrics`, `grafana_dashboard`, `metrics_endpoint`, `debug_tools`.

`debug_tools` *(optional)*: Read-only inspection tools for local development. Each entry includes `name`, `kind` (e.g. `mcp_tool`, `api_endpoint`), `purpose`.

## Other Fields

`workflows`: Named user or app flows. Each entry includes `name`, `trigger_examples`, `steps`, `mutation_behavior`, `current_status`.

`prompts` *(agent_dashboard_app / hybrid_agent_pipeline)*: References or summaries of prompt responsibilities: routing rules, guardrails, data trust boundaries, recovery rules. May be `not_present` or empty for deterministic pipeline apps.

`seed_data`: Demo or fixture data used to make the domain runnable without live providers.

`tests`: Expected deterministic test coverage. Includes `backend` (unit/integration/e2e), `frontend` (unit/playwright), `expectations`, `commands`. Tests must not require live LLM or paid provider access.

`future_extensions`: Planned capabilities not in the current app. Generators must not treat these as current features.

`compatibility_gaps`: Known mismatches, limitations, or places where the current app is less formal than the pack contract.

## Terminology

| Public term | Config / internal term | Meaning |
|---|---|---|
| App Blueprint | `domain-pack` | Machine-readable YAML describing app archetype, capabilities, adapters, UI surfaces, and tests |
| Application Template | template / Product Shell | The reusable FastAPI/React source tree copied and parameterized by the generator |
| Feature Module | shell module | A reusable capability area wired by the generator (pipeline, scoring, agent runtime, etc.) |
| Integration Adapter | provider/adapter | Normalizes external or fixture data into stable app-specific records |
| Test Harness | deterministic test shell | Fixture-based tests that avoid live external APIs or LLMs |
| Provider | provider | Source of data or execution capability (mock, offline, external API, IMAP, etc.) |
| Adapter | adapter | Normalization layer from provider output to stable domain DTO |
| Capability | capability | Any operational app action; general term for all archetypes |
| Tool | tool | Agent-callable capability; only use when Agent Runtime Module exists |
| UI Surface | ui_surface | Any rendered surface: table, card, ops panel, triage queue, dashboard widget |
| Widget | widget | Persisted workspace surface (agent_dashboard_app only) |

## Tool-to-Widget Compatibility (agent_dashboard_app only)

Every persisted widget must have a `source_tool` and a `widget_type`. The pair is valid only if the tool's result shape can be rendered by the widget.

Rules:
- Tools returning review rows → `review_list` only.
- Tools returning chart-ready `series` → `line_chart`.
- Tools returning `bars` → bar-style widgets when semantics match.
- Tools returning `slices` → `pie_chart` or `donut_chart`.
- Tools returning health score fields → `health_score` or `summary_card` fallback.
- Money-flow data → `money_flow` only; do not use bar charts as primary money-flow answer.
- Workspace mutation tools (`pin_widget`, `remove_widget`, `clear_dashboard`, etc.) produce no domain data widgets.

## Test Expectations

Tests must cover (adapt to archetype):
- Provider behavior with fixture data (no live calls).
- Adapter: raw provider output → normalized DTO correctness.
- Run history: row written on provider/capability call.
- Scoring/explanation: deterministic output for known inputs.
- Action persistence: pending/sent/skipped state transitions.
- UI surface: renders correctly for expected data shapes and empty state.
- Playwright or E2E: proves core workflow end-to-end.
- CI: all checks run without live LLM or paid API dependency.

For agent_dashboard_app additionally:
- Tool registry and compatibility maps.
- Scripted LLM provider flows.
- Guardrail and routing behavior.

## Generator/Scaffolder Contract

The generator reads `app_archetype` and `required_shell_modules` to select templates, then uses `capabilities`/`tools`, `providers`, `adapters`, `ui_surfaces`/`widgets`, `run_history`, `notification_actions`, and `seed_data` to wire domain-specific behavior into the shell.

Rules:
- Generator must not invent current capabilities from `future_extensions`.
- Generator must not wire optional shell modules unless declared in `optional_shell_modules`.
- Generator must not force `tools`, `widgets`, or `tool_widget_compatibility` for pipeline archetypes.
- Generator must not force Agent Shell or Workspace Shell unless `agent_runtime` or `workspace_runtime` appears in `required_shell_modules` or `optional_shell_modules`.
