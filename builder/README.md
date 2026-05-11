# AgentForge Blueprint Builder

The Blueprint Builder is the local product front door for AgentForge. It helps you start from either:

1. a new app idea, or
2. an existing repository that you analyze with `agentforge analyze-repo` and plan with `agentforge plan-extension`.

It remains local-first and CLI-first. The builder helps draft and review an App Blueprint, but `agentforge plan` and `agentforge generate` remain the source of truth for validation and generation.

## Modes

- Static/manual mode: open `index.html` directly, edit fields, review the generation preview, and copy or download the Blueprint Source YAML.
- Scripted planner mode: run `agentforge serve-builder`, open the printed URL, then draft/refine/validate through the local Python planner.

## Start from an app idea

Use the idea panel to describe the product you want to build. The local scripted planner can:

- draft from a short app idea;
- ask clarifying questions for vague ideas;
- refine a draft with bounded instructions;
- show assumptions, warnings, recommended modules, YAML, and CLI commands;
- validate the current draft against the Python generator schema.

Example:

```bash
agentforge serve-builder
```

Then open the local URL and use **Start from an app idea**.

## Start from an existing repo

Use the Repo Analyzer and Repo Extension Planner outside the browser, then paste JSON output into the builder:

```bash
agentforge analyze-repo ../my-project
agentforge analyze-repo ../my-project --format md
agentforge analyze-repo ../my-project --json --output report.json
agentforge plan-extension ../my-project
agentforge plan-extension report.json --from-report
agentforge plan-extension ../my-project --modules agent_runtime,dashboard_workspace --format md --output extension-plan.md
agentforge prepare-extension ../my-project --output agentforge-output/my-project-extension
agentforge prepare-extension ../my-project --modules agent_runtime --dry-run
# Explicit low-risk docs/blueprint/checklist apply only:
agentforge prepare-extension ../my-project --modules agent_runtime --apply
agentforge prepare-extension ../my-project --modules agent_runtime --apply --yes
```

The analyzer is analysis-only and the extension planner is planning-only. `prepare-extension` bundle mode is a safe preview, and `--dry-run` reports planned writes, apply-eligible files, dirty repo state, overwrite conflicts, safety checks, and next steps without writing files. Apply mode requires `--apply` plus interactive `yes` or `--yes`, refuses dirty repos/overwrites by default, and only writes low-risk docs/blueprint/checklist files. None of these commands deploy anything, call live LLMs, call external APIs, or require internet access.

When pasted into the builder, analyzer JSON can show:

- detected stack;
- likely archetype;
- compatible/partial/missing AgentForge modules;
- advisory migration phases;
- draft Blueprint seed, if present.

The seed still needs review before it becomes a real `domain-pack.yaml`. Extension planner JSON can also show selected modules, migration phases, file impact, risks, and the explicit no-files-modified statement.

## What will be generated

The builder includes a generation preview for the current Blueprint state. It summarizes generated pieces such as FastAPI backend, React frontend, provider/adapters, deterministic scoring, notification/triage, agent runtime, dashboard/workspace, tests, Docker/CI/local validation, supported modules, planned gaps, and next commands.

## Blueprint Source

YAML remains available as **Blueprint Source (Advanced)** with copy/download support. This is still the file format consumed by the CLI:

```bash
agentforge plan path/to/domain-pack.yaml
agentforge generate path/to/domain-pack.yaml
```

## Boundaries

The builder does not call a live LLM, inspect local repositories from the browser, run extension planning in the browser, convert existing apps, deploy infrastructure, apply patches from the browser, modify files automatically, or replace CLI validation. Patch bundle/apply remains CLI-only and explicit.

For a CLI-only starter file:

```bash
agentforge init-blueprint my-app --optional-module agent_runtime
```
