# AgentForge Blueprint Builder

The Blueprint Builder is the local product front door for AgentForge. The v1.0 UX is intentionally no-key and demo-first: describe what you want to build, review a plain-language plan, then copy/save the App Blueprint and run the CLI.

The main promise is visible in the UI: **no API keys, no cloud account, and no external provider setup are required for the local demo path.**

The long-term direction is an agent-chat builder. For now, the UI is a compact app-like workspace with one active step visible at a time and a persistent Live app plan:

```text
Start → describe idea → review plan → generate locally with CLI
```

## Modes

- Static/manual mode: open `index.html` directly, edit the advanced fields if needed, review the generation preview, and copy or download the Blueprint Source YAML.
- Scripted planner mode: run `agentforge serve-builder`, open the printed URL, then draft/refine/validate through the local Python planner.

## Primary path: start from an app idea

Use **Start from an app idea** for the main flow. The generated demo can be tested with included sample records and a scripted local agent.

The Builder asks for one plain-English idea, then the local scripted planner can:

- draft an App Blueprint;
- ask clarifying questions for vague ideas;
- refine a draft with bounded instructions;
- show assumptions, warnings, recommended modules, YAML, and CLI commands;
- validate the current draft against the Python generator schema.

Example:

```bash
agentforge serve-builder
```

Then open the local URL and describe the app you want to build.

## Fastest test path

Use the committed demo when you want to prove the app works without external services:

```bash
agentforge generate domain-packs/hybrid-scoring-demo/domain-pack.yaml --force
make run-backend
make run-frontend
```

Then open the generated app, ingest included sample records, score them, use agent chat, pin a workspace widget, and refresh to confirm persistence.

## Review and generate

The Builder treats generated outcomes as the main review surface before raw YAML or module details:

- app type in plain language;
- what AgentForge will generate;
- assumptions and warnings;
- concise safety cues;
- next CLI commands.

Module IDs, planned gaps, deterministic configuration, exact command blocks, and raw YAML remain available behind advanced disclosure. The right-side **Live app plan** stays visible on desktop and groups capabilities as app foundation, AI workflow, product surfaces, and validation so it feels like an active plan instead of metadata.

The CLI remains the source of truth:

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

The generation preview summarizes tangible app pieces such as FastAPI backend, React frontend, included sample records, deterministic scoring, notification/triage, scripted local agent chat, dashboard/workspace, tests, Docker/CI/local validation, supported modules, planned gaps, and next commands. No external provider setup is needed for the demo path.

## Blueprint Source

YAML remains available as **Blueprint Source (Advanced)** with copy/download support. This is still the file format consumed by the CLI.

## Boundaries

The Builder does not call a live LLM, inspect local repositories from the browser, run extension/deployment planning in the browser, convert existing apps, deploy infrastructure, apply patches from the browser, modify files automatically, or replace CLI validation. Patch bundle/apply and deployment planning remain CLI-only and explicit.

For a CLI-only starter file:

```bash
agentforge init-blueprint my-app --optional-module agent_runtime
```
