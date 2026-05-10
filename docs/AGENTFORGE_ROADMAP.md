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

