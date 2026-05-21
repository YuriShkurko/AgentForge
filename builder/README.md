# AgentForge Blueprint Builder

The Blueprint Builder is the local product front door for AgentForge. The current UX is intentionally no-key and demo-first: describe what you want to build, review and apply a plain-language plan, then validate, generate, check, start, and open a local app from the Builder.

The main promise is visible in the UI: **no API keys, no cloud account, and no external provider setup are required for the local demo path.**

The UI is now an agent-first workspace with a main assistant canvas, Plan / Build / Run flow, compact right rail HUD, and Advanced surfaces for YAML, CLI commands, and logs:

```text
Describe idea -> review plan -> validate Blueprint -> generate locally -> run checks -> start app -> open app
```

## Modes

- Static/manual mode: open `index.html` directly, edit the advanced fields if needed, review the generation preview, and copy or download the Blueprint Source YAML.
- Scripted planner mode: run `agentforge serve-builder`, open the printed URL, then draft/refine/validate through the local Python planner.
- Builder Assistant chat (default scripted): once the planner server is running, the Describe step shows an inline chat panel that talks to the deterministic local assistant (`/api/planner/assistant/*`). The assistant asks clarifying questions for vague ideas, proposes a `model_driven_app` Blueprint with a per-field/per-entity/per-import/per-provider diff, and exposes explicit **Apply** / **Reject** controls. Apply mutates only the in-memory Builder draft after re-running `DomainPack` validation through the planner; Reject leaves the draft unchanged. If a tampered or otherwise invalid proposal fails validation, a dedicated guidance panel explains the error category (e.g. missing relation target, bad provider env, missing import target) with a suggested manual fix and, when ambiguous, a targeted follow-up question — never an auto-applied repair. The panel degrades gracefully when the planner is offline.

## Primary path: start from an app idea

Use **Start from an app idea** for the main flow. The generated demo can be tested with included sample records and a scripted local agent.

The Builder asks for one plain-English idea, then the local scripted planner can:

- draft an App Blueprint;
- ask clarifying questions for vague ideas;
- refine a draft with bounded instructions;
- show assumptions, warnings, recommended modules, YAML, and CLI commands;
- include controlled app customization such as labels, workflow copy, starter prompts, and workspace wording when the idea clearly implies them;
- validate the current draft against the Python generator schema.

Example:

```bash
agentforge serve-builder
```

Then open the local URL and describe the app you want to build.

## Optional live Builder Assistant mode

After an assistant proposal is applied, the Plan / Build / Run workspace exposes local run controls when running through `agentforge serve-builder`. It can validate the active in-memory Blueprint, generate the app under `.tmp/builder-runs/<safe-run-id>/app`, run the generated app's fixed `make validate` target, start/stop the generated backend/frontend with allowlisted `make` targets, open the frontend, and show status, exit code, generated path, equivalent commands, and stdout/stderr logs. Static browser mode shows these controls as unavailable. The control room does not accept arbitrary shell commands or output paths, and it does not create GitHub repos or deploy.

The Builder Assistant is scripted by default and does not require an API key, network access, GitHub access, deployment credentials, or OAuth. Live LLM assistance is strictly opt-in for local development:

```bash
export AGENTFORGE_ASSISTANT_PROVIDER=openai
export OPENAI_API_KEY=...
# optional: export AGENTFORGE_ASSISTANT_LLM_MODEL=gpt-4o-mini
agentforge serve-builder
```

For local Builder development only, `agentforge serve-builder` also reads a `.env` file from the current working directory if one exists:

```dotenv
AGENTFORGE_ASSISTANT_PROVIDER=openai
OPENAI_API_KEY=...
# optional
AGENTFORGE_ASSISTANT_LLM_MODEL=gpt-4o-mini
```

The loader supports `KEY=value`, single-quoted values, double-quoted values, blank lines, and full-line comments starting with `#`. It ignores malformed lines, never prints values, and never overrides variables already set in your shell. Keep real `.env` files out of git; if the Builder sees a `.env` that is not git-ignored, it prints a warning without showing contents.

In live mode, `/api/planner/status` reports only `mode` and `live_provider: true`; it does not expose API keys or loaded values. Assistant responses include `turn_mode` (`live` or `scripted`) plus `fallback_reason` when the live path could not be used.

Live mode is intentionally bounded:

- the LLM may propose only a model spec: entities and fields;
- deterministic Builder code still creates the Blueprint, imports/providers, dashboard, UI composition, and YAML;
- every proposal is validated through `DomainPack` before it is shown as apply-ready;
- Apply revalidates the proposal and still changes only the in-memory Builder draft;
- tests use mocks/dummy keys and must not require live network calls.

If the provider is missing, unavailable, returns non-JSON, returns an unusable model spec, or produces a Blueprint that fails schema validation, the assistant falls back to scripted mode and reports why. Do not paste real provider tokens into the Builder; generated provider examples use environment-variable names only.

## Fastest test path

Use a committed demo Blueprint when you want to prove generation works without external services:

```bash
agentforge generate domain-packs/hybrid-scoring-demo/domain-pack.yaml --force
agentforge generate domain-packs/project-workspace-demo/domain-pack.yaml --output .tmp/project-workspace-demo --force
```

The scoring demo shows ingest/score/triage plus agent/workspace persistence. The project workspace demo shows projects, tasks, notes/activity, scripted agent tools, and pinned widgets.

## Review and generate

The Builder treats generated outcomes as the main review surface before raw YAML or module details:

- detected app family/archetype in plain language;
- a focused **Customize app details** panel for safe labels, app subtitle, starter prompts, and workspace/sample wording;
- what AgentForge will generate;
- assumptions and warnings;
- concise safety cues;
- next CLI commands.

Module IDs, planned gaps, deterministic configuration, exact command blocks, and raw YAML remain available behind advanced disclosure. The right-side **Live app plan** stays visible on desktop and groups capabilities as app foundation, AI workflow, product surfaces, and validation so it feels like an active plan instead of metadata.

The Builder uses the same schema and generator path as the CLI. For CLI-only validation or automation, use:

```bash
agentforge plan path/to/domain-pack.yaml
agentforge generate path/to/domain-pack.yaml
make validate
```

## Secondary path: start from an existing repo

Existing-repo planning remains available, but it is intentionally secondary to the new-app flow and collapsed by default.

Use the Repo Analyzer and Repo Extension Planner outside the browser, then optionally paste JSON output into the Builder:

```bash
agentforge analyze-repo ../my-project --format md
agentforge analyze-repo ../my-project --json --output report.json
agentforge plan-extension ../my-project --format md --output extension-plan.md
agentforge plan-extension report.json --from-report
agentforge prepare-extension ../my-project --dry-run
agentforge plan-deployment ../my-project --format md
```

The analyzer, extension planner, and deployment planner are planning-only. `prepare-extension` bundle mode is a safe preview, and `--dry-run` reports planned writes, apply-eligible files, dirty repo state, overwrite conflicts, safety checks, and next steps without writing files. Apply mode requires `--apply` plus interactive `yes` or `--yes`, refuses dirty repos/overwrites by default, and only writes low-risk docs/blueprint/checklist files. `plan-deployment` reports readiness and platform recommendations only; it does not deploy, provision resources, run cloud CLIs, store secrets, or run target scripts. None of these commands call live LLMs, call external APIs, or require internet access.

## What will be generated

The generation preview summarizes tangible app pieces such as FastAPI backend, React frontend, included sample data, app-specific workflow surfaces, scripted local agent chat, dashboard/workspace, tests, Docker/CI/local validation, supported modules, planned gaps, and next commands. No external provider setup is needed for the demo path.

## Customize app details

After drafting a Blueprint, the review step shows a compact customization panel before generation. It displays the detected family as either **Scoring / triage workflow** or **Project / task workspace**, then exposes only bounded text/list fields for that family. Scoring apps show record/review/notification/sample/criteria labels; project workspace apps show project/task/activity/sample labels. Common app subtitle, target user label, workflow label, agent starter prompts, and workspace empty-state wording are available for both.

The panel writes into the same `customization` block shown in the advanced YAML preview. If users leave the fields alone, Builder defaults are preserved.

## Blueprint Source

YAML remains available as **Blueprint Source (Advanced)** with copy/download support. This is still the file format consumed by the CLI.

Builder YAML may include a `customization` block. It is a bounded set of text/list fields for the current supported app families, not a way to define arbitrary routes, components, providers, or deployment behavior.

## Boundaries

By default, the Builder does not call a live LLM, inspect local repositories from the browser, run extension/deployment planning in the browser, convert existing apps, deploy infrastructure, apply patches from the browser, modify files automatically, or replace CLI validation. Optional live Builder Assistant mode must be explicitly enabled with `AGENTFORGE_ASSISTANT_PROVIDER=openai`; even then, it proposes only bounded model specs and has no GitHub automation, deployment, OAuth, file-write, hidden-apply, or repo-mutation behavior. Patch bundle/apply and deployment planning remain CLI-only and explicit.

For a CLI-only starter file:

```bash
agentforge init-blueprint my-app --optional-module agent_runtime
```
