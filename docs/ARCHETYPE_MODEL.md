# AgentForge Archetype Model

AgentForge selects an app archetype before selecting feature modules. The archetype tells the generator which application template modules are required and which App Blueprint (`domain-pack.yaml`) fields must be present. The v0.7 Repo Analyzer can guess likely archetypes from an existing repository, but those guesses are advisory and must be reviewed before creating or changing an App Blueprint.

> **Terms:** "shell module" = feature module (pipeline, scoring, agent runtime, etc.); "Product Shell" = Application Template; "Domain Pack" = App Blueprint. See [README terminology table](../README.md#terminology).

## Archetype Summary

| Archetype | Based on | Core UX | Required shell modules | Status |
| --- | --- | --- | --- | --- |
| `agent_dashboard_app` | Business Insight | Conversational dashboard and workspace | Agent Shell, Workspace Shell, Provider/Adapter Shell, Test Shell | Current pack proves it |
| `ingestion_scoring_pipeline` | AI Job Radar | Ops UI for ingest, normalize, score, inspect | Pipeline Shell, Provider/Adapter Shell, Scoring Shell, Operations UI Shell | Current pack proves it |
| `notification_triage_app` | AI Job Radar | Recommendations plus user decisions | Notification/Action Shell, Triage UI Shell, Persistence Shell | Current pack proves it |
| `deploy_planner_app` | Future | Plan, validate, and stage deployment work | Pipeline Shell, Policy/Approval Shell, Audit Shell | Future |
| `hybrid_agent_pipeline` | Future | Chat or command UX over deterministic pipeline | Pipeline Shell plus optional Agent Shell | Future |

## `agent_dashboard_app`

Required shell modules:

- Agent Runtime Module: chat endpoint, scripted provider, tool calling, persisted conversations, guardrails.
- Full Agent Shell: streaming, broader orchestration, and workspace-aware behavior.
- Workspace Shell: widget persistence, widget lifecycle events, layout, compatibility validation.
- Provider/Adapter Shell: source provider contracts and normalized domain data.
- Test Shell: deterministic scripted LLM, tool registry tests, widget tests, Playwright.

Optional shell modules:

- Notification/Action Shell.
- Observability/Debug Shell.
- Pipeline run history.

Expected Domain Pack fields:

- `domain`
- `app_archetype: agent_dashboard_app`
- `required_shell_modules`
- `tools`
- `widgets`
- `tool_widget_compatibility`
- `providers`
- `adapters`
- `workflows`
- `prompts`
- `seed_data`
- `tests`

Example generated app: a review analytics dashboard where a user asks questions, tools retrieve or compute insights, and the agent pins compatible widgets into a dashboard.

## `ingestion_scoring_pipeline`

Required shell modules:

- Pipeline Shell: provider runs, normalization, dedupe hooks, run history.
- Provider/Adapter Shell: source provider and normalized DTO contracts.
- Scoring/Explanation Shell: deterministic scoring result shape.
- Operations UI Shell: run controls, tables, status, logs.
- Persistence Shell.
- Test Shell.

Optional shell modules:

- Notification/Action Shell.
- Debug MCP/inspection tools.
- Agent Runtime Module as a command/chat facade over deterministic tools.
- Dashboard/Workspace Module for persisted generic widgets over deterministic tool results.

Expected Domain Pack fields:

- `domain`
- `app_archetype: ingestion_scoring_pipeline`
- `required_shell_modules`
- `capabilities`
- `ui_surfaces`
- `providers`
- `adapters`
- `workflows`
- `seed_data`
- `tests`
- `agent_runtime` when the optional Agent Runtime Module is enabled
- `observability`

Example generated app: a job, lead, or opportunity pipeline that ingests records from a fixture provider, normalizes them, scores them, and shows run/scored result tables.

## `notification_triage_app`

Required shell modules:

- Notification/Action Shell: preview/no-op delivery adapter, action definitions, dedupe, current status, and history.
- Triage UI Shell: preview cards, queue, decision controls, and action history.
- Persistence Shell: previews, decisions, and delivery/action history.
- Scoring/Explanation Shell: recommendation summary.

Optional shell modules:

- Pipeline Shell.
- Agent Shell.
- Agent Runtime Module.
- External channel providers.

Expected Domain Pack fields:

- `domain`
- `app_archetype: notification_triage_app`
- `required_shell_modules`
- `capabilities`
- `ui_surfaces`
- `notification_actions`
- `workflows`
- `tests`

Example generated app: a scored recommendation queue where each item can be previewed, accepted, skipped, saved, and audited without sending to an external channel.

## `deploy_planner_app`

Required shell modules:

- Pipeline Shell.
- Policy/Approval Shell.
- Audit/Run History Shell.
- Test Shell.

Optional shell modules:

- Agent Runtime Module.
- Workspace Shell.
- Notification Shell.

Expected Domain Pack fields:

- deployment targets.
- validation capabilities.
- approval gates.
- rollback/plan schemas.
- tests with dry-run-only behavior.

Example generated app: a deployment planner that creates deployment plans, validates preconditions, and records approval history without directly deploying in v0.

## `hybrid_agent_pipeline`

Required shell modules:

- Pipeline Shell.
- Provider/Adapter Shell.
- Operations UI Shell.

Optional shell modules:

- Agent Shell.
- Workspace Shell.
- Notification/Action Shell.

Expected Domain Pack fields:

- deterministic pipeline capabilities.
- optional Agent Runtime routing over those capabilities.
- explicit guardrails around what the agent may mutate.

Example generated app: an ingestion/scoring pipeline with a command panel or chat facade that can trigger approved deterministic workflows.

## Module Selection Rule

The generator starts from `app_archetype`, loads required feature modules, then wires optional feature modules only when the App Blueprint declares them. This prevents pipeline apps from being forced into chat/workspace behavior.

As of v0.4, `workspace` is supported as a generic Dashboard/Workspace Module. It covers persisted generic widgets, backend compatibility validation, and simple remove/reorder behavior; it does not imply support for every domain-specific Business Insight widget renderer.

## Blueprint Builder Mapping

The v0.7.1 Blueprint Builder is the local product front door for this same archetype model. It presents public labels such as Application Template, Feature Modules, Integration Adapters, and Test Harness, then emits the existing internal config fields such as `app_archetype`, `required_shell_modules`, `optional_shell_modules`, `agent_runtime`, `workspace`, and `tool_widget_compatibility`.

The builder can display pasted Repo Analyzer JSON and show advisory archetype guesses, but it does not define a separate archetype schema. Its generated YAML must still load through `agentforge.pack.load_pack`, and `agentforge plan` remains the authoritative module support/gap check.
