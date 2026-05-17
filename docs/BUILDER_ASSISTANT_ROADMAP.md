# Builder Assistant v0 Roadmap

## 1. Product goal

Builder Assistant v0 should turn the current Builder from a wizard-like form into a safe conversational product/schema assistant. The assistant should guide app design conversationally, ask focused clarifying questions, help users define model-driven entities/fields/relations, suggest imports/providers when the requested workflow implies them, suggest bounded UI recipe/composition choices, validate the App Blueprint/model, and show proposed changes before the user applies them.

The default experience must remain local-first and deterministic. Builder Assistant should work with the existing scripted planner and Python schema validation without requiring a live LLM, API keys, network access, GitHub access, or deployment credentials.

## 2. Non-goals

Builder Assistant v0 explicitly does **not** include:

- GitHub repo creation.
- Pushing generated apps to GitHub.
- Deployment execution or cloud provisioning.
- OAuth flows.
- A live LLM requirement.
- Autonomous repo edits.
- Hidden YAML mutations.
- Arbitrary code generation.
- Visual drag/drop builder behavior.
- Secret collection or secret storage.
- Scheduled sync or background automation.

## 3. User flow

1. User opens Builder and starts with a plain-English app idea.
2. Assistant responds in a chat-style panel with a summary of what it understood.
3. Assistant asks clarifying questions when the idea is underspecified, such as target users, entities, fields, workflow actions, imports, providers, and UI style.
4. User answers in chat.
5. Assistant proposes a structured App Blueprint/model update.
6. Builder shows a human-readable summary and a field-level/YAML diff preview.
7. User explicitly chooses **Apply** or **Reject**.
8. If applied, Builder updates the in-memory draft only and runs validation through the existing planner/server schema path.
9. Validation results are shown clearly, with next suggested fixes when possible.
10. User can keep iterating or proceed to save/copy the Blueprint and generate the app through existing CLI commands.

## 4. Architecture proposal

Builder Assistant should reuse the current Builder/planner shape instead of introducing a second schema or a separate generation path.

- **Builder frontend chat panel**: add an assistant panel to `builder/index.html`, state/rendering in `builder/app.mjs`, and styling in `builder/styles.css`. The panel should show messages, questions, proposed changes, validation state, and explicit Apply/Reject controls.
- **Local planner/server endpoints**: extend `generator/agentforge/planner/server.py` with assistant-specific JSON endpoints such as `/api/planner/assistant/start`, `/api/planner/assistant/message`, and `/api/planner/assistant/apply-preview` or equivalent. Endpoints should return structured conversation state and proposed patches, not mutate files.
- **Scripted assistant engine**: add a deterministic engine near `generator/agentforge/planner/scripted.py` or a sibling module such as `assistant.py`. It should encode a small state machine for requirements gathering, model suggestions, import/provider suggestions, and validation guidance.
- **Schema validation through existing `pack.py`**: all proposed blueprints must validate with `DomainPack.model_validate` before the assistant marks them apply-ready. Model-driven references, provider target imports, UI fields, enum values, and relation targets should rely on existing schema validation wherever possible.
- **Reuse existing blueprint generation/refinement paths**: use `generator/agentforge/blueprints.py`, `ScriptedPlanner.draft`, `ScriptedPlanner.refine`, and `validate_blueprint_result` where they already fit. Avoid duplicating starter Blueprint construction logic in the frontend.
- **Diff/patch boundary**: assistant output should be a structured proposed change set against the current in-memory Blueprint. Builder applies it only after user confirmation.

## 5. Assistant capabilities by phase

### Phase 0 — roadmap/design only

- **Goal**: define scope, safety boundaries, architecture, and phased implementation plan.
- **User-visible behavior**: none; documentation only.
- **Files likely touched**: `docs/BUILDER_ASSISTANT_ROADMAP.md`; possibly Scribe artifacts only.
- **Tests needed**: docs validation/lint only if available.
- **Risks**: over-scoping into live LLM, GitHub, deployment, or visual builder work.
- **Done criteria**: roadmap exists, first slice is clear, non-goals and safety model are explicit.

### Phase 1 — deterministic assistant state machine

- **Goal**: implement a local deterministic assistant engine that can run a basic conversation and produce safe proposed Blueprint changes.
- **User-visible behavior**: API-only or test-only assistant can ask clarifying questions and return a proposal for a model-driven draft.
- **Files likely touched**: `generator/agentforge/planner/assistant.py` or `scripted.py`, `generator/agentforge/planner/server.py`, `generator/agentforge/planner/__init__.py`, tests under `tests/generator/`.
- **Tests needed**: conversation state transitions, clarification flow, proposal shape, invalid input handling, schema validation success/failure, no file writes.
- **Risks**: duplicating Blueprint construction logic, returning unvalidated patches, making conversation state too complex.
- **Done criteria**: deterministic tests prove start → clarify → propose → validate behavior; no live LLM; no filesystem mutation.

### Phase 2 — Builder chat UI

- **Goal**: expose the deterministic assistant in the Builder UI.
- **User-visible behavior**: a chat panel appears beside or within the Builder flow; user can send an idea/answer and see assistant messages/questions.
- **Files likely touched**: `builder/index.html`, `builder/app.mjs`, `builder/styles.css`, `builder/README.md`, frontend-related generator tests if present.
- **Tests needed**: UI element presence, message rendering, unavailable-planner fallback, existing wizard flow still works, accessibility smoke for buttons/labels.
- **Risks**: cluttering the current focused Builder, breaking static/manual mode, reducing clarity of the Live app plan.
- **Done criteria**: chat UI works with `agentforge serve-builder`; static mode degrades gracefully; no hidden Blueprint changes.

### Phase 3 — assistant-proposed blueprint diffs

- **Goal**: make proposals reviewable before apply.
- **User-visible behavior**: assistant shows a summary and a diff/changed-fields list; user can Apply or Reject.
- **Files likely touched**: `builder/app.mjs`, `builder/blueprint-builder.mjs`, `builder/index.html`, `builder/styles.css`, planner server/assistant modules.
- **Tests needed**: proposal diff generation, Apply mutates only in-memory Builder state, Reject leaves state unchanged, validation runs after Apply, copied YAML matches applied state.
- **Risks**: patch ambiguity, accidental hidden mutation, differences between frontend YAML and Python validated Blueprint.
- **Done criteria**: every assistant change is visible before apply; Apply/Reject behavior is deterministic and tested.

### Phase 4 — model-driven helpers for entities/fields/relations/imports/providers

- **Goal**: expand assistant suggestions for model-driven app design.
- **User-visible behavior**: assistant can suggest entities, fields, enum values, relations, CSV/JSON imports, read-only GitHub Issues providers, read-only HTTP JSON providers, and UI presentation hints.
- **Files likely touched**: assistant engine, `pack.py` only if existing schema is insufficient, `blueprints.py`, Builder UI files, tests.
- **Tests needed**: entity/field naming, relation target validation, enum values, import `upsert_key`, provider `target_import`, `http_json` env/url/token shape, GitHub repo/token env names, UI recipe/composition references.
- **Risks**: implying arbitrary provider support, invalid relation references, overfitting to one domain, suggesting unsupported OAuth/write-back/scheduling.
- **Done criteria**: assistant produces valid bounded `model_driven_app` proposals for at least two domains and rejects/repairs invalid references.

### Phase 5 — validation explanation loop

- **Goal**: convert schema validation errors into actionable assistant guidance.
- **User-visible behavior**: when validation fails, assistant explains the issue and proposes a safe fix or asks a targeted follow-up question.
- **Files likely touched**: assistant engine, server validation endpoint, Builder UI rendering for validation messages.
- **Tests needed**: common validation errors for missing relation target, invalid enum, bad provider env, missing target import, unsupported UI field reference; no destructive auto-fix.
- **Risks**: hiding raw validation details, producing misleading fixes, applying fixes without confirmation.
- **Done criteria**: errors remain visible, assistant guidance is clear, fixes still require Apply.

### Phase 6 — optional live LLM adapter behind env flag (shipped)

- **Goal**: optionally route assistant planning through a live LLM adapter only when explicitly enabled.
- **User-visible behavior**: default remains scripted. When `AGENTFORGE_ASSISTANT_PROVIDER=openai` is set, the assistant runs in live mode and the `/api/planner/status` endpoint reports `live_provider: true`. Each proposal carries `turn_mode` (`live` or `scripted`) and a `fallback_reason` when live failed.
- **Files touched**: `generator/agentforge/planner/live_llm.py` (new), `generator/agentforge/planner/assistant.py`, `generator/agentforge/planner/server.py`, `tests/generator/test_builder_assistant_live.py` (new).
- **Tests**: env flag disabled by default, opt-in env builds the OpenAI client, mock adapter happy path produces a live spec, multiple fallback scenarios (raise, non-JSON, sanitized to nothing, schema rejection), no network calls in default mode, and `/api/planner/status` reflects live capability.
- **Risks mitigated**: spec is bounded (entities + fields only — scaffolding stays scripted); every blueprint flows through `DomainPack.model_validate`; secrets are read from env only and never logged or echoed; fallback path keeps Builder usable when the live call misbehaves.
- **Done**: default offline, live mode opt-in, mocked in tests, every output validated and user-applied.

### Phase 7 — Builder Local Control Room MVP (shipped)

- **Goal**: after an assistant proposal is applied, let the local Builder validate the active Blueprint, generate the app into a safe local run directory, run the generated app validation target, and show the exact commands/logs back in the UI.
- **User-visible behavior**: Review gains a local control room panel for the active in-memory Blueprint. The user can run a bounded sequence: validate Blueprint → generate to `.tmp/builder-runs/<safe-run-id>/` → run `make validate` inside that generated app → inspect stdout/stderr, exit status, generated path, and copyable equivalent CLI commands.
- **Safety boundaries**: no GitHub repo creation, no deployment, no arbitrary shell commands, no secret collection/display, no writes outside `.tmp/builder-runs`, no generated-app server start/stop, no backend/frontend process management, and no background automation. Every action is user-clicked, bounded to known commands, and tied to the active validated Blueprint.
- **Architecture plan**: add planner-server endpoints for a local run lifecycle such as `/api/planner/local-run/validate-blueprint`, `/api/planner/local-run/generate`, and `/api/planner/local-run/validate-app`. The server writes a transient Blueprint file under the run directory, invokes existing AgentForge generation/validation paths with fixed arguments, captures logs with timeouts, and returns structured step results. The Builder UI renders the run state, command equivalents, log output, and next safe action.
- **Files likely touched**: `generator/agentforge/planner/server.py`, possibly a small helper module such as `generator/agentforge/planner/local_run.py`, `builder/app.mjs`, `builder/index.html`, `builder/styles.css`, `builder/README.md`, `docs/DEMO_GUIDE.md`, and tests under `tests/generator/`.
- **Tests needed**: safe run-id/path traversal rejection, writes only under `.tmp/builder-runs`, Blueprint validation success/failure, generation success/failure, `make validate` success/failure, timeout/log truncation behavior, command allowlist enforcement, UI button/log rendering, and no GitHub/deploy/process-management calls.
- **Risks**: path traversal or accidental writes outside the sandbox, exposing secrets in logs, hanging validation commands, confusing local validation with deployment, and making the browser appear to run arbitrary commands.
- **Done criteria**: the full local sequence works from Builder for an assistant-applied Blueprint; failures are visible and actionable; command/log output is copyable; generated files stay under `.tmp/builder-runs`; no GitHub, deployment, arbitrary shell, or app process management is implemented.
- **Done**: implemented serve-builder-only local run endpoints for Blueprint validation, generation, and `make validate`; Builder Review renders status/path/commands/logs; tests cover path safety, command allowlisting, failures, timeout/log truncation, static unavailable state, and browser smoke.

### Phase 8 — GitHub repo creation later, not now

- **Goal**: reserve GitHub repo creation as a separate future project after Builder Assistant v0 is safe and reviewed.
- **User-visible behavior**: none in v0, except explicit non-goal language.
- **Files likely touched**: future docs/spec only.
- **Tests needed**: future work only.
- **Risks**: scope creep into credentials, OAuth, remote mutations, and repository management.
- **Done criteria**: no GitHub repo creation in Builder Assistant v0.

## 6. First implementation slice recommendation

Implement Phase 1 first, then the smallest Phase 2/3 UI slice.

Recommended first slice:

- Add a deterministic scripted assistant endpoint to the local planner server.
- Add a minimal assistant state machine that can:
  - start from an idea;
  - ask clarifying questions;
  - infer a `model_driven_app` direction when appropriate;
  - propose model-driven Blueprint changes for entities, fields, and a UI recipe;
  - validate the proposed Blueprint through existing `DomainPack` validation.
- Add a chat panel in Builder that calls the endpoint.
- Show a proposal summary and changed fields before applying.
- Require the user to click **Apply** before any in-memory Builder state changes.
- Do not add live LLM support.
- Do not add GitHub/deploy automation.
- Do not write files or generate apps from the assistant.

This slice is useful because it changes the Builder feel from form-first to assistant-guided while preserving all current safety guarantees.

## 7. Safety model

Builder Assistant v0 must preserve the current AgentForge safety posture:

- No automatic file writes.
- No external side effects.
- No generated app creation unless the user explicitly uses existing Generate/CLI flow.
- No GitHub calls.
- No deployment calls.
- No secret collection, secret storage, or secret display.
- No live LLM in the default path.
- All proposed changes are visible before apply.
- Apply changes only to the in-memory Builder draft.
- Reject leaves the current draft unchanged.
- Validation errors are shown clearly and are not hidden behind assistant prose.
- Python schema validation remains authoritative.
- Builder YAML preview/export remains user-controlled.

## 8. Test strategy

Tests should cover both assistant logic and regression safety for existing Builder behavior.

- **Assistant conversation state**: start, collect idea, ask questions, accept answers, propose, apply-ready, rejected, validation-error states.
- **Clarifying question flow**: vague ideas trigger questions; answered questions reduce ambiguity and produce proposals.
- **Proposed Blueprint patch/diff**: proposals include changed paths/summary, validate before apply, and avoid unsupported schema fields.
- **Apply/reject behavior**: Apply mutates only in-memory Builder state; Reject leaves state unchanged; repeated Apply is idempotent or clearly disabled.
- **Schema validation loop**: invalid entities, fields, relations, imports, providers, and UI hints surface actionable validation errors.
- **Builder UI presence**: chat panel renders, controls have labels, planner-unavailable fallback works, existing wizard steps still function.
- **No hidden mutation**: assistant messages/proposals do not change YAML until Apply; server endpoints do not write files.
- **Existing Builder flows still work**: draft/refine/validate endpoints continue to pass; manual/static mode still produces Blueprint YAML.
- **No network/default live calls**: tests prove no live LLM, GitHub, provider, or deployment calls occur in default mode.

Practical validation targets by phase:

```bash
python -m pytest tests/generator/test_builder_planner.py -q
python -m pytest tests/generator/test_model_driven.py -q
python -m pytest tests/generator/ -q
```

Use broader tests once UI/server code changes are made. For this roadmap-only phase, Scribe lint is sufficient.

## 9. Docs impact

Later implementation phases should update:

- `builder/README.md` — assistant UX, safety model, local scripted mode, Apply/Reject behavior.
- `docs/DEMO_GUIDE.md` — demo flow once the assistant UI is stable.
- `docs/ARCHETYPE_MODEL.md` — only if schema/archetype behavior changes.
- `docs/DOMAIN_PACK_SPEC.md` — only if App Blueprint schema changes.
- `README.md` — only when the assistant is public-facing and validated.

## 10. Recommended next prompt

Phases 1–7 are shipped (deterministic state machine, chat UI, Apply/Reject diff, imports/providers/relations helpers, validation explanation loop, optional live-LLM adapter behind an env flag, and Builder Local Control Room MVP).

Phase 6 is opt-in. Default Builder Assistant mode stays scripted with zero network calls. To enable the live adapter:

```bash
export AGENTFORGE_ASSISTANT_PROVIDER=openai
export OPENAI_API_KEY=...
# optional: export AGENTFORGE_ASSISTANT_LLM_MODEL=gpt-4o-mini
agentforge serve-builder
```

In live mode the LLM only proposes a bounded model spec (entities + fields). The deterministic scaffolding (starter Blueprint, imports/providers, dashboard, UI composition) is still applied, the result is still validated by `DomainPack.model_validate`, and the user still has to click **Apply**. If the live call fails or the spec is invalid, the assistant falls back to scripted and reports the fallback in the response (`turn_mode` and `fallback_reason`).

Remaining un-shipped phases:

- Phase 8 (GitHub repo creation) — deferred indefinitely; out of scope for Builder Assistant v0.
