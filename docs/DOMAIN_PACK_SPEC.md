# App Blueprint Specification (`domain-pack.yaml`)

An **App Blueprint** (config name: `domain-pack`) is the complete machine-readable definition of one app domain. Combined with an Application Template, it produces a runnable app.

**Application Template + App Blueprint = Generated App.**

The Application Template provides reusable runtime infrastructure: APIs, persistence, run history, integration adapters, deterministic test harness, frontend surfaces, notifications, observability, and local/dev workflow. The App Blueprint provides the variable surface: identity, archetype declaration, required/optional feature modules, capabilities, schemas, providers/adapters, workflows, UI surfaces, seed data, and tests.

The feature modules an app needs depend on its archetype. An agentic dashboard uses the Agent Runtime Module and Dashboard/Workspace Module. A pipeline app uses the Ingestion Pipeline Module and Scoring Module. A notification app uses the Triage/Action Module. A project workspace app uses task/activity persistence with scripted agent tools and workspace widgets. The generator reads `app_archetype` and `required_shell_modules` to decide which modules to wire.

App Blueprints may also include a small `customization` block for supported app copy and labels. This is a controlled configuration layer, not a DSL or arbitrary app generator.

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
- `project_workspace_app` — local project/task workspace with notes, activity, scripted agent tools, and persisted widgets
- `model_driven_app` — bounded model-driven CRUD/workflow app generated from explicit entities, fields, pages, actions, and seed data

`required_shell_modules`: List of feature modules the generator must wire. Example: `[pipeline, provider_adapter, scoring_explanation, operations_ui, persistence, test]`.

`optional_shell_modules`: Feature modules wired only when declared. Example: `[notification_action, observability_debug, agent_runtime]`.

`agent_runtime` *(optional when `agent_runtime` is declared as a feature module)*: Configuration for the Agent Runtime Module. Fields include `enabled`, `provider_mode` (`scripted`, `mock`, or `openai_compatible_placeholder`), `scripted_fixture_path` or inline `scripted_turns`, `tools` exposed to the agent, `conversation_persistence`, `streaming`, and `guardrails`. When `streaming.enabled` is true, generated apps expose `/agent/chat/stream` as `text/event-stream` with structured `message_start`, `text_delta`, `tool_call`, `tool_result`, `error`, and `done` events.

`workspace` *(optional when `workspace` is declared as a feature module)*: Configuration for the Dashboard/Workspace Module. Fields include `enabled`, `persistence` (table/field expectations), `default_layout`, `remove_enabled`, `reorder_enabled`, `empty_state`, and `frontend_surface`. v0.4 stores direct widget JSON payloads, validates compatibility on the backend, and supports list/create/remove/reorder operations.

`model` *(required for `model_driven_app`)*: Bounded app model used to generate simple CRUD/workflow apps. Fields:
- `entities`: each entity has `name`, `label_singular`, `label_plural`, and `fields`.
- Entity `fields`: each field has `name`, optional `label`, `type`, optional `required`; supported types are `string`, `text`, `integer`, `boolean`, `date`, `enum`, and `relation`.
- `enum` fields must declare `enum_values`.
- `relation` fields must declare `target_entity`; v0 treats relations as reference IDs and supports only simple `many_to_one`/`reference` style relations.
- `pages`: limited to `dashboard`, `entity_list`, and `entity_detail`.
- `actions`: limited to safe workflow patterns: `update_status`, `mark_complete`, and `add_note` acknowledgement.
- `seed_data`: deterministic records keyed by entity name.
- `ui` *(optional)*: bounded model-driven presentation hints. Missing `ui` uses deterministic defaults. Supported fields are:
  - `composition`: one of `standard`, `board_workspace`, or `register_table`. `board_workspace` prioritizes a grouped board and secondary record panel. `register_table` prioritizes a compact table/register and side summary panel.
  - `recipe`: one of `standard`, `workspace_board`, `executive_register`, or `ops_console`. Recipes are bounded visual treatments for density, shell styling, empty states, badges, and component emphasis.
  - `style.accent`: one of `blue`, `emerald`, `amber`, `red`, `slate`, or `violet`.
  - `style.density`: one of `compact`, `comfortable`, or `spacious`.
  - `style.layout`: one of `workspace`, `register`, or `operations`.
  - `focus.primary_entity`, optional `focus.secondary_entity`, optional `focus.group_by`, and optional `focus.title_field`/`badge_field`/`secondary_field`; references must point to existing entities/fields, and `board_workspace.group_by` must be an enum field when provided.
  - `dashboard.title`, optional `dashboard.primary_entity`, and `dashboard.cards` with `count`, `enum_breakdown`, or `attention_list` card types.
  - `entities.<entity>.display.layout`: `table`, `cards`, or `board_by_status`, plus optional `title_field`, `subtitle_field`, `badge_field`, and `secondary_field` references.
  - optional field `semantic` hints from `status`, `priority`, `severity`, `owner`, `due_date`, `title`, and `description`.
- `imports` *(optional)*: list of importer configurations the generated app should expose. Each entry has:
  - `id`: stable snake_case identifier, unique within the pack.
  - `label`: optional human label for the import.
  - `entity`: target model entity name.
  - `formats`: subset of `[csv, json]`; defaults to both.
  - `upsert_key`: optional field on `entity`. When set, commits update an existing row whose `upsert_key` matches; otherwise they insert. Without `upsert_key` every valid row is inserted.
  - `field_map`: optional `{source_column: entity_field}` mapping. Source columns can be human-readable headers; entity-side targets must be fields on `entity`. Columns whose normalized name already matches an entity field auto-map and need no explicit entry.
  - Generated apps expose `GET /imports`, `GET /imports/runs`, `POST /imports/{import_id}/preview`, and `POST /imports/{import_id}/commit`. CSV and JSON are thin parsing adapters; mapping, validation, upsert, and run history are shared. JSON payloads may be either an array of objects or an object with a `records`, `items`, or `data` array. Commit is reject-on-invalid: any invalid row aborts the commit and persists a `rejected` import run; with no invalid rows the import succeeds and persists an `ok` run. Relation fields accept either integer ids or existing related-record labels/names via safe aliases such as `client` for `client_id`; missing or ambiguous labels are rejected and related records are not created implicitly.
- `providers` *(optional, Provider Runtime v0)*: list of read-only external source adapters that feed a target model import. v0 supports only `mode: read_only` with `type: github_issues` or `type: http_json`. Each provider has `id`, optional `label`, `type`, `mode`, `target_import`, and env/source settings for its bounded adapter. `github_issues` uses `env.token`, `env.repo`, and optional `source.state`/`source.labels`. `http_json` uses `env.url`, optional `env.token`, optional `source.auth` (`none` or `bearer`), and optional simple dotted `source.records_path`; it extracts records from a top-level array, `records`/`items`/`data` wrapper, or the configured path. `target_import` must reference an existing `model.imports` entry; that import owns field mapping, validation, and upsert behavior. Generated apps expose `GET /providers`, `GET /providers/runs`, `POST /providers/{provider_id}/preview`, and `POST /providers/{provider_id}/sync` when providers are configured. Providers fetch and normalize records, then call the same importer preview/commit functions used by CSV/JSON. Provider v0 has no OAuth, no secret entry UI, no write-back, no scheduled sync, no provider marketplace, and no live network requirement for default tests.

The model-driven presentation layer is controlled configuration, not arbitrary UI generation. It can select from supported compositions, presentation recipes, layouts, dashboard cards, safe accent/density values, and existing model fields. It also humanizes enum-like display values and emits generic empty states. It does not generate arbitrary code, arbitrary providers/integrations, auth, billing, deployment, visual model editing, per-prompt freeform UI design, or visual-builder behavior.

`customization` *(optional)*: Controlled visible-label configuration. Missing fields use deterministic defaults. Supported nested fields:
- `app.subtitle`, `app.target_user_label`, `app.workflow_label`
- `agent_starters`
- `workspace.empty_state`, `workspace.widget_label`, `workspace.pinned_label`
- `scoring.record_label.singular/plural`, `scoring.criteria_labels`, `scoring.review_queue_label`, `scoring.notification_label`, `scoring.sample_data_label`
- `project_workspace.project_label.singular/plural`, `project_workspace.task_label.singular/plural`, `project_workspace.activity_label`, `project_workspace.sample_data_label`

Customization values are validated as bounded text/list fields and are emitted into generated frontend configuration. They must not contain code, routes, components, scripts, or live-provider settings.

`agent_shell_contract` *(agent_dashboard_app / hybrid_agent_pipeline only)*: Broader capabilities expected from a full Agent Shell runtime — `chat`, `streaming_sse`, `tool_calling`, `persistent_conversations`, `persistent_workspace_widgets`, `workspace_events`, `dashboard_layout`, `guardrails`, `scripted_llm_testing`.

## Capability and Tool Fields

`capabilities`: All operational capabilities exposed by the app — endpoint operations, pipeline steps, scoring actions. Use `capabilities` as the general term for any app archetype. Each entry includes `name`, `purpose`, `input_summary`, `output_shape`, `mutates_state`, `data_mode`, `deterministic_test_safe`, `implementation_status`, and optional `source_files`.

`tools` *(agent_dashboard_app or `agent_runtime.tools`)*: Agent-callable capabilities exposed to the chat/tool-calling runtime. A subset of `capabilities`. For dashboard apps, each entry can include `allowed_widget_types`. For pipeline apps, prefer `agent_runtime.tools` so deterministic tools remain scoped to the Agent Runtime Module rather than implying a Dashboard/Workspace Module. Tool `input_schema` entries should be typed objects where practical, for example `{type: boolean, required: false, default: false}` or `{type: string, required: true, choices: [accept, skip, save]}`. Generated runtimes validate tool arguments before execution and return structured `unknown_tool` or `invalid_arguments` tool errors without crashing chat requests.

`widgets` *(required when `workspace` is enabled)*: Renderable workspace widget types. Each entry includes `widget_type`, `renderer`, `compatible_source_tools`, `section`, `expected_data_shape`, `empty_state`, `implementation_status`. v0.4 supports generic widgets only; domain-specific renderers must be declared and implemented separately.

`tool_widget_compatibility` *(required when `workspace` is enabled; empty map otherwise)*: Authoritative mapping from `source_tool` to allowed `widget_type` values. Generators use this map to produce backend validation that prevents an agent from pinning unrenderable widgets.

`ui_surfaces`: General UI surfaces the app exposes — tables, cards, triage queues, operations panels, dashboards. Covers both persisted workspace widgets and non-persistent operational views. Each entry includes `surface_type`, `renderer`, `data_source`, `section`, `expected_data_shape`, `empty_state`.

## Data Flow Fields

`providers`: Capability sources — where data or execution capability comes from. Mock providers, offline fixtures, external APIs, IMAP fetchers, notification channels. Each entry includes `name`, `class` or `interface`, `source`, `current_status`.

`adapters`: Normalization layers that convert provider output into stable domain DTOs. Each entry includes `name`, `purpose`, `normalized_shape` or `source_file`.

`run_history` *(ingestion_scoring_pipeline, notification_triage_app)*: Expectations for provider/capability run logging. Fields: `enabled`, `table_name`, `tracked_fields` (e.g. `[provider_name, started_at, finished_at, status, stats, error]`), `frontend_surface`.

`notification_actions` *(notification_triage_app, ingestion_scoring_pipeline)*: Action definitions for the notification/triage loop. Each action includes `name`, `trigger`, `delivery_channel`, optional `delivery_mode` (for v0.2 this is `preview_only`), `decision_states` (e.g. `[pending, accepted, skipped, saved]`), `dedupe_key`, `persistence_table`, optional `history_table`, and optional `preview_table`.

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
| Agent Runtime Module | `agent_runtime` | Optional scripted chat/tool-calling runtime with persisted conversations, SSE events, and typed tool validation |
| Dashboard/Workspace Module | `workspace` | Optional persisted workspace widgets with generic rendering and backend source-tool/widget compatibility validation |
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
- Notification previews: scored records produce deterministic preview payloads without external delivery.
- Action persistence: current decision state plus append-only history for repeated actions.
- Agent Runtime Module: scripted provider simple response, ordered SSE events, valid tool execution, invalid argument and unknown tool error paths, non-streaming fallback, conversation persistence, and no live LLM dependency.
- UI surface: renders correctly for expected data shapes and empty state.
- Playwright or E2E: proves core workflow end-to-end.
- CI: all checks run without live LLM or paid API dependency.

For agent_dashboard_app additionally:
- Tool registry and compatibility maps.
- Scripted LLM provider flows.
- Guardrail and routing behavior.

## Generator/Scaffolder Contract

The generator reads `app_archetype` and `required_shell_modules` to select generation behavior. Fixed archetypes select existing app templates. `model_driven_app` uses the `model` block to emit readable FastAPI/SQLite and React/Vite files for custom entities, fields, routes, pages, seed data, simple workflow actions, and bounded presentation hints. Other archetypes use `capabilities`/`tools`, `providers`, `adapters`, `ui_surfaces`/`widgets`, `run_history`, `agent_runtime`, `notification_actions`, and `seed_data` to wire domain-specific behavior into the shell.

Rules:
- Generator must not invent current capabilities from `future_extensions`.
- Generator must not wire optional shell modules unless declared in `optional_shell_modules`.
- Generator must not force `tools`, `widgets`, or `tool_widget_compatibility` for pipeline archetypes.
- Generator must not force the Agent Runtime Module or Dashboard/Workspace Module unless `agent_runtime` or `workspace` appears in `required_shell_modules` or `optional_shell_modules`.
- Agent runtime tests must use `scripted` or `mock` provider modes; live OpenAI-compatible providers are configuration placeholders only until explicitly implemented.
- Streaming must be honest `text/event-stream` delivery. Do not claim streaming support from a buffered non-streaming response.
- Tool arguments must be validated against declared/generated typed schemas before handlers run, and validation errors must be returned as structured tool results.
- `customization` may alter visible copy, labels, starter prompts, and sample/workspace wording only; it must not create arbitrary frontend code, backend routes, external integrations, or new feature modules.

## Blueprint Builder And Planner Contract

The Blueprint Builder and v0.6 scripted planner draft this same App Blueprint format. They are not second schemas and must not make generation UI-only.

Rules:
- The builder may mirror a small subset of fields in browser-side code for live YAML preview.
- `agentforge.pack.load_pack` and `agentforge plan` remain the validation source of truth.
- Planner output must pass the Python generator schema before being returned as `status="draft"`.
- The local planner server may expose scripted draft/clarify/refine/validate endpoints, but it must not execute generation or mutate source code.
- Builder defaults must stay deterministic: fixture provider data, `preview_only` notifications, and `scripted` Agent Runtime provider mode.
- The builder and planner must not add live LLM/API requirements, repo analysis, repo conversion, deployment planning, or autonomous code modification.
- Export is copy/download by default; filesystem writes should stay in the CLI path such as `agentforge init-blueprint`.
