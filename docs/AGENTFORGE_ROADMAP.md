# AgentForge Roadmap

This roadmap is based on the Business Insight and AI Job Radar App Blueprints (`domain-packs`). It favors one small generated app over a broad framework.

> **Terms used here:** App Blueprint = the machine-readable `domain-pack.yaml`; Application Template = the reusable FastAPI/React source tree; Feature Modules = reusable capability areas (pipeline, scoring, notifications, etc.). See [README terminology table](../README.md#terminology).

## v0.1 Recommended Scope

Build one tiny hybrid sample app that proves the reusable application template modules common to both packs.

The v0.1 generated app should include:

- FastAPI backend.
- React frontend.
- One provider interface.
- One deterministic fixture provider.
- One adapter from raw provider data to a normalized DTO.
- Run history persistence.
- One deterministic scoring/explanation capability.
- One operation UI surface for runs and scored records.
- One notification/action loop stub with persisted action status.
- Deterministic backend tests.
- Frontend build/test check.
- One Playwright happy path.
- Docker Compose for local database/app.
- CI skeleton with no live LLM/API dependency.

Optional v0.1 add-on:

- A simple command panel or minimal chat facade that calls one deterministic capability, without live LLM dependency.

## Acceptance Criteria

- `agentforge generate examples/hybrid-scoring-demo` or equivalent creates the sample app from a small App Blueprint (`domain-pack.yaml`).
- The generated app runs locally with Docker Compose or documented local commands.
- Ingesting fixture data creates a run history row.
- Scoring writes deterministic explanation output.
- The frontend displays run history and scored records.
- A notification/action stub records a user action without external delivery.
- Backend deterministic tests pass.
- Playwright happy path passes.
- CI skeleton runs the same checks.
- Docs explain how to create a second App Blueprint (`domain-pack.yaml`) and choose an archetype.

## v0.2 Notification/Triage Module

Build on the v0.1 action stub by extracting a reusable preview-only Notification/Triage Module.

The v0.2 generated app should include:

- Notification previews generated from scored records.
- A no-op delivery adapter boundary that stores preview payloads but does not call Telegram, email, Slack, or any paid API.
- Current action state for each record.
- Append-only action history so repeated decisions remain auditable.
- A triage UI surface with preview cards, action buttons, and history.
- Generator module selection that treats `notification_action` and `triage_ui` as supported template modules.

Out of scope for v0.2: real external delivery, guided UI, live LLM behavior, autonomous deployment, arbitrary repo conversion, and direct Business Insight or AI Job Radar conversion.

## v0.3 Agent Runtime Module

Add a minimal reusable Agent Runtime Module without turning AgentForge into a full AI app builder.

The v0.3 generated app should include:

- Persisted conversations and messages.
- A scripted LLM provider for deterministic local and CI tests.
- A tool registry that exposes a small set of generated deterministic tools.
- A non-streaming chat endpoint that persists user messages, executes scripted tool calls, persists tool events, and returns assistant responses.
- A compact frontend chat panel that shows messages and tool activity without replacing the operations UI.
- Tests proving simple response, tool call, tool result, unknown tool/error handling, conversation persistence, and no live LLM/API dependency.

Out of scope for v0.3: Dashboard/Workspace Module, guided Blueprint Builder UI, arbitrary repo conversion, autonomous deployment, live LLM calls in tests, multi-agent orchestration, long-term memory beyond persisted conversations, and fake streaming. SSE streaming is deferred until it can be implemented honestly.

## v0.3.1 Agent Runtime Hardening

Tighten the v0.3 Agent Runtime Module before v0.4 Dashboard/Workspace work.

The v0.3.1 generated app should include:

- A real `/agent/chat/stream` SSE endpoint alongside the existing non-streaming `/agent/chat`.
- Structured streaming events: `message_start`, `text_delta`, `tool_call`, `tool_result`, `error`, and `done`.
- Scripted deterministic streaming behavior with no live LLM/API dependency.
- Typed tool argument schemas validated before tool execution.
- Structured `unknown_tool` and `invalid_arguments` tool errors that are visible in API responses and frontend tool activity.
- Frontend streaming consumption with incremental assistant text and graceful fallback to `/agent/chat`.

This prepares for v0.4 Dashboard/Workspace by making agent turns observable as ordered events and by making tool boundaries explicit before tool results are routed into widgets.

Out of scope for v0.3.1: Dashboard/Workspace Module, persisted widgets, guided Blueprint Builder UI, arbitrary repo conversion, autonomous deployment, live LLM providers, multi-agent orchestration, and long-term memory beyond persisted conversations.

## v0.4 Dashboard/Workspace Module

Add a generic persisted workspace without copying Business Insight-specific widgets.

The v0.4 generated app should include:

- `workspace` App Blueprint configuration plus `widgets` and `tool_widget_compatibility`.
- `workspace_widgets` persistence with deterministic ordering.
- Backend APIs for list, create/pin, remove, and reorder.
- Backend-enforced source-tool to widget-type compatibility.
- Generic widget types: `summary_card`, `ranking_list`, `score_table`, `run_history_list`, `notification_preview_card`, and `action_history_list`.
- Agent tools for pinning/listing/removing/reordering widgets through the scripted runtime.
- A compact React workspace panel and generic `WidgetRenderer`.
- Tests proving pin, refresh persistence, remove, reorder, and invalid compatibility paths.

Out of scope for v0.4: guided Blueprint Builder UI, repo analyzer, deploy planner, live LLM/API providers, external integrations, multi-agent orchestration, presentation mode, major visual redesign, and Business Insight-specific widgets such as `money_flow`, `health_score`, and `signal_timeline`.

## v0.4.1 Workspace UI Polish

Polish the generated Dashboard/Workspace Module UI without changing the v0.4 contracts.

The v0.4.1 generated app should include:

- Clearer workspace header, description, widget count, and persisted-widget hint.
- More intentional empty, loading, and error states.
- Readable generic widget cards that display widget type and source tool as product labels rather than raw implementation noise.
- More scannable generic widget renderers for summaries, rankings, score tables, run history, notification previews, and action history.
- Agent tool activity copy that makes widget pin success or failure understandable.

Out of scope for v0.4.1: workspace architecture changes, agent runtime architecture changes, new feature modules, live LLM/API dependencies, guided Blueprint Builder UI, repo analyzer, deployment planner, presentation mode, drag/drop, and Business Insight-specific widgets. Taste Skill-style critique may be used as a review aid only; it must not become a generated runtime dependency.

## v0.5 Simple Blueprint Builder UI

Add a small local/dev Blueprint Builder for creating and editing App Blueprints without making the generated app runtime more complex.

The v0.5 builder should include:

- App metadata fields for name, display name, description, target user/persona, and app archetype.
- Archetype selection for current known archetypes, with future archetypes marked as planned where appropriate.
- Feature Module selection with supported modules enabled and future modules disabled/planned.
- Simple deterministic module configuration: preview-only notification mode, scripted LLM provider mode, fixture provider enabled, action labels, workspace enabled, and generic widget compatibility preset.
- Live App Blueprint YAML preview.
- Copy/download export for `domain-pack.yaml`.
- A plan preview that shows the `agentforge plan <file>` command; CLI planning remains the source of truth.
- A small `agentforge init-blueprint` CLI helper for starter App Blueprints.

Out of scope for v0.5: AI-assisted Blueprint Builder behavior, live LLM/API dependencies, repo analysis, repo conversion, deployment planning, autonomous code modification, generated app redesign, and a hosted builder platform.

## v0.6 AI-Assisted Blueprint Builder

Use v0.5's stable App Blueprint draft flow as the foundation for guided AI assistance.

v0.6 helps users refine App Blueprint intent, module choices, validation gaps, and test expectations while keeping `agentforge plan` and `agentforge generate` authoritative. Repo conversion, deployment automation, and autonomous code modification remain separate future decisions rather than implicit v0.6 scope.

Implemented v0.6 scope:

- Python `Planner` contract and `PlannerResult` structure.
- Deterministic scripted planner for draft, clarify, and refine flows.
- Local `agentforge serve-builder` server exposing scripted planner endpoints to the static builder.
- Builder UI panels for idea drafting, clarification questions, draft review, refinement, and schema validation.
- Optional `agentforge draft-blueprint` helper for writing scripted planner YAML when `--out` is explicit.
- Tests proving planner output round-trips through `load_pack`, vague ideas ask questions, live planner mode fails fast, and the local server endpoints work.

Out of scope for v0.6 remains: live LLM integration, repo analysis/conversion, deployment planning, hosted builder state, autonomous edits, and replacing `agentforge plan` as the validation source of truth.

## v0.7 Repo Analyzer

v0.7 adds an analysis-only local Repo Analyzer. It inspects an existing local repository and produces an AgentForge compatibility and migration report without modifying the analyzed repository.

Implemented v0.7 scope:

- `agentforge analyze-repo <path>` CLI command.
- Deterministic local filesystem scan with safe generated/vendor/cache directory ignores.
- Stack, config, test, devops, AI/agent, observability, and architecture signal detection.
- AgentForge module compatibility statuses with path evidence and suggested migration steps.
- Advisory archetype guesses with confidence and evidence.
- Advisory phased migration plan based on detected gaps.
- Optional draft App Blueprint seed in the report only.
- Text, Markdown, and JSON report output, with optional `--output` when explicitly requested.
- Fixture-based analyzer tests with no internet, live LLM, or external API dependency.

Out of scope for v0.7: repo conversion, source rewriting, automatic patch generation, deployment planning, autonomous code execution, live LLM/API analysis, GitHub API usage, and secret content extraction. Repo extension or patch planning remains a future v0.8+ decision.

## v0.7.1 Builder UX Clarity and Product Front Door

v0.7.1 makes the local Blueprint Builder the clearest first stop for AgentForge.

Implemented v0.7.1 scope:

- Builder landing/front-door panel that explains what AgentForge generates.
- Two explicit starting paths: start from a new app idea, or start from an existing repo.
- New-app flow polish with example ideas, clearer action labels, stronger draft review, and module/archetype chips.
- Existing-repo flow guidance for `agentforge analyze-repo`, including analysis-only safety copy and command examples.
- Pasted analyzer JSON preview for detected stack, archetype, module compatibility, migration phases, and draft Blueprint seed.
- Generation preview panel for app pieces, supported modules, planned gaps, and next CLI commands.
- YAML reframed as advanced Blueprint Source while preserving copy/download and validation behavior.

Out of scope for v0.7.1: browser filesystem access, repo modification, patch generation, repo conversion, deployment planning, live LLM/API dependencies, autonomous code execution, real provider integrations, and generated runtime/template changes. Repo extension/patch planning remains future v0.8+ scope.

## v0.8 Repo Extension Planner

v0.8 adds a planning-only layer after the v0.7 Repo Analyzer. It helps users understand how AgentForge modules could be added to an existing repo without modifying that repo.

Implemented v0.8 scope:

- `agentforge plan-extension <path-or-report>` CLI command.
- Direct repo path input that runs the existing read-only analyzer internally.
- Analyzer JSON input with `--from-report`.
- Desired module selection with `--modules` and conservative recommendations when omitted.
- Structured planning model with selected/recommended modules, module plans, prerequisites, file impact, migration phases, risks, unsupported items, manual steps, generated artifact previews, commands, and confidence.
- Text, Markdown, and JSON report output.
- Builder existing-repo guidance and pasted extension-plan JSON preview.
- Tests proving report input, direct repo input, module selection, unsupported gaps, deterministic phases, report shape, CLI behavior, and no target repo file modification.

Out of scope for v0.8: applying patches, modifying target repos, overwriting files, creating branches, installing packages, running autonomous code execution, deployment planning, live LLM/API dependencies, real provider integrations, and generated runtime/template changes.

## v0.8.1 Safe Patch Bundle

v0.8.1 adds `agentforge prepare-extension` bundle/preview generation. It reuses v0.8 planner output and writes a safe bundle to an explicit output directory with manifest, extension plan, file impact, migration phases, validation checklist, safety notes, patch preview, and proposed low-risk files. Default behavior still does not modify target repos.

## v0.8.2 Approved Low-Risk Apply

v0.8.2 adds explicit `prepare-extension --apply --yes` for approved low-risk files only: App Blueprint seed files, AgentForge migration/extension docs, validation checklists, module TODOs, and env suggestion docs. It refuses dirty git repos and overwrites by default, never stages/commits/pushes/deploys/installs/runs target scripts, and does not edit runtime code, package files, lockfiles, routers, components, CI workflows, or business logic.

## Implementation Milestones

### Milestone 1: Spec Stabilization

Deliverables:

- Finalize `app_archetype`, `required_shell_modules`, `optional_shell_modules`, `capabilities`, `ui_surfaces`, `run_history`, and `notification_actions` additions to `DOMAIN_PACK_SPEC.md`.
- Add a minimal example App Blueprint (`domain-pack.yaml`) for the v0.1 sample.
- Define TypeScript/Python schema fixtures used by generator tests.

Exit criteria:

- Existing Business Insight and AI Job Radar packs can be classified without losing meaning.
- The sample pack validates without requiring agent/workspace fields.

### Milestone 2: Template Skeleton

Deliverables:

- FastAPI + React template.
- Persistence model for runs, normalized records, scores, and actions.
- Fixture provider and adapter template.
- Basic operations UI.

Exit criteria:

- Template can run manually before generator automation.
- No live provider, LLM, or external notification dependency.

### Milestone 3: Generator v0

Deliverables:

- Generator command reads the sample App Blueprint (`domain-pack.yaml`).
- Generator copies/wires selected feature modules.
- Generator emits backend/frontend app and local validation commands.

Exit criteria:

- Generated output matches a snapshot.
- Generated app boots and tests pass.

### Milestone 4: Validation and E2E

Deliverables:

- Backend tests for provider, adapter, run history, scoring, action persistence.
- Frontend or build tests.
- Playwright happy path.
- CI skeleton.

Exit criteria:

- One command runs all deterministic checks.
- Playwright proves the generated UI can drive the core workflow.

### Milestone 5: Second Pack Dry Run

Deliverables:

- Try classifying Business Insight and AI Job Radar against the updated spec.
- Generate only a plan/diff for each, not full app conversion.

Exit criteria:

- The generator identifies required/optional feature modules correctly.
- Gaps are explicit and do not become fake generated features.

## What Not To Build Yet

- Arbitrary repo conversion.
- Autonomous deploy agent.
- Generic all-purpose agent framework.
- Full UI builder.
- Real external providers.
- Too many archetypes.
- Package publishing.
- Live LLM-dependent tests.
- Deployment automation that mutates production systems.

## Spec Changes Recommended

Update `DOMAIN_PACK_SPEC.md` after architecture review to add:

- `app_archetype`
- `required_shell_modules`
- `optional_shell_modules`
- `capabilities`
- `ui_surfaces`
- optional `widgets`
- optional `tool_widget_compatibility`
- `run_history`
- `notification_actions`
- `observability`
- `debug_tools`

Also clarify that:

- `tools` means agent-callable capabilities.
- pipeline apps can have capabilities without chat/tools.
- widgets are persisted workspace surfaces, while UI surfaces include tables, cards, triage queues, and operations panels.
- prompts can be absent for deterministic apps.

## Risks

- Over-abstraction before the first generated app works.
- Forcing all apps into chat-agent UX.
- Treating deterministic pipelines as agents unnecessarily.
- Building UI before generator contracts stabilize.
- Generating code without validation.
- Letting future extensions leak into current generated capabilities.
- Making deployment unsafe by including autonomous deploy behavior too early.

## Near-Term Decision

AgentForge v0.1 should build the hybrid scoring sample, not a Business Insight clone and not an AI Job Radar clone. The sample should be small enough to regenerate repeatedly and rich enough to prove provider/adapters, run history, scoring/explanation, UI, action loop, deterministic tests, and CI.
