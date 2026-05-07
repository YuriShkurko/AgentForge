# AgentForge Roadmap

This roadmap is based on the Business Insight and AI Job Radar domain packs. It favors one small generated app over a broad framework.

## v0.1 Recommended Scope

Build one tiny hybrid sample app that proves the reusable Product Shell pieces common to both packs.

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

- `agentforge generate examples/hybrid-scoring-demo` or equivalent creates the sample app from a small Domain Pack.
- The generated app runs locally with Docker Compose or documented local commands.
- Ingesting fixture data creates a run history row.
- Scoring writes deterministic explanation output.
- The frontend displays run history and scored records.
- A notification/action stub records a user action without external delivery.
- Backend deterministic tests pass.
- Playwright happy path passes.
- CI skeleton runs the same checks.
- Docs explain how to create a second Domain Pack and choose an archetype.

## Implementation Milestones

### Milestone 1: Spec Stabilization

Deliverables:

- Finalize `app_archetype`, `required_shell_modules`, `optional_shell_modules`, `capabilities`, `ui_surfaces`, `run_history`, and `notification_actions` additions to `DOMAIN_PACK_SPEC.md`.
- Add a minimal example Domain Pack for the v0.1 sample.
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

- Generator command reads the sample Domain Pack.
- Generator copies/wires selected shell modules.
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

- The generator identifies required/optional shell modules correctly.
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

