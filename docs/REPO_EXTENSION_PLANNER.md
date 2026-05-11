# AgentForge Repo Extension Planner

`agentforge plan-extension` is the v0.8 planning-only layer after the v0.7 Repo Analyzer.

It consumes either a local repository path or a JSON report from `agentforge analyze-repo` and produces an advisory extension/migration plan for adding AgentForge capabilities to an existing repository.

## Commands

```bash
agentforge plan-extension ../my-project
agentforge plan-extension analysis.json --from-report
agentforge plan-extension ../my-project --modules agent_runtime,dashboard_workspace
agentforge plan-extension ../my-project --format md --output extension-plan.md
agentforge plan-extension ../my-project --json
agentforge prepare-extension ../my-project --output agentforge-output/my-project-extension
agentforge prepare-extension analysis.json --from-report --output agentforge-output/from-report
agentforge prepare-extension ../my-project --modules agent_runtime,dashboard_workspace --dry-run
agentforge prepare-extension ../my-project --modules agent_runtime --apply
agentforge prepare-extension ../my-project --modules agent_runtime --apply --yes
```

Options:

- `--from-report`: treat the target argument as `agentforge analyze-repo --json` output.
- `--modules <list>`: comma-separated desired modules.
- `--format text|md|json`: choose report format. Default is `text`.
- `--json`: shortcut for JSON output.
- `--output <path>`: write the plan to the requested path instead of stdout.
- `--max-files <n>`: scan cap when the target is a repo path.
- `--include-tests`: include deep test directory content sniffing when analyzing a repo path.

`prepare-extension` also supports `--output`, `--dry-run`, `--apply`, `--yes`, `--allow-dirty`, and `--overwrite`. Default mode writes only a bundle to the explicit output directory and does not modify the target repo. Dry-run writes nothing and reports planned operations, apply-eligible files, dirty git status, overwrite conflicts, safety checks, validation commands, and next steps.

## Safety boundaries

v0.8 plans repo extension. It does not perform repo extension.

The planner does **not**:

- modify target repository files;
- overwrite user files;
- apply patches;
- create branches;
- stage or commit changes;
- install packages;
- write generated source into the target repo;
- deploy anything;
- call live LLMs or external APIs;
- require internet or GitHub API access.

Patch-related planner output is a patch plan/preview only. v0.8.1-v0.8.3 adds `agentforge prepare-extension`, which reuses planner output to create a safe bundle, provide richer previews, and explicitly apply only low-risk docs/blueprint/checklist files.

## Supported desired modules

- `provider_adapter`
- `pipeline`
- `scoring_explanation`
- `notification_action`
- `triage_ui`
- `agent_runtime`
- `dashboard_workspace`
- `deterministic_test_harness`
- `ci_local_validation`

Unsupported/future requested items are reported as gaps, including:

- `repo_patch_apply`
- `deploy_planner`
- `real_provider_integrations`
- `live_llm_provider`
- `observability_debug`

## What the plan contains

Structured plans include:

- target repo summary;
- source analyzer summary;
- selected modules;
- recommended modules;
- per-module plans with status, evidence, prerequisites, likely files to add/modify, tests, validation commands, rollback notes, and risk;
- prerequisites;
- advisory file impact;
- migration phases;
- risks/blockers;
- unsupported requested items;
- manual steps;
- patch-plan artifact previews;
- commands to run;
- confidence;
- explicit no-files-modified statement.

Module statuses are:

- `ready`: strong analyzer compatibility evidence exists;
- `partial`: some prerequisites or boundary work remain;
- `blocked`: analyzer evidence is missing/weak or the module requires manual architecture review;
- `unsupported`: future/out-of-scope item;
- `not_recommended`: not selected/recommended for the current plan.

## Intended flow

```text
repo path or analyzer JSON
→ repo analysis summary
→ desired/recommended module selection
→ compatibility and gap review
→ file impact plan
→ phased migration plan
→ patch-plan preview
→ user approval before any future modification
```

Use the plan as a review artifact. Use `prepare-extension` bundle mode for a safe preview and `--dry-run` to inspect what would happen without writing. Only use `prepare-extension --apply` after typing `yes`, or `--apply --yes` for scripted local workflows, when you explicitly want low-risk docs/blueprint/checklist files copied into the target repo; runtime integration patches remain future work.

## Builder handoff

The Blueprint Builder shows safe command examples and can display pasted extension planner JSON output. The browser builder does not scan local files and does not run extension planning itself.
