# AgentForge Command Reference

Commands are grouped by user intent. Each section notes write behavior and safety boundaries.

## Create new apps

| Command | What it does | Writes files? | Existing repo modification? | Safety notes |
| --- | --- | --- | --- | --- |
| `agentforge serve-builder` | Starts the local Builder/planner server | No target app writes | No | Local deterministic planner; no live LLM/API required |
| `agentforge draft-blueprint` | Drafts an App Blueprint from an idea | Only with `--out` | No | Validates draft output through the generator schema |
| `agentforge init-blueprint` | Creates a starter Blueprint | Yes | No | Writes Blueprint files only |
| `agentforge plan` | Validates a Blueprint and previews generation | No | No | Use before generation |
| `agentforge generate` | Generates a FastAPI + React app from a Blueprint | Yes | No existing repo mutation by default | `--force` intentionally replaces generated output |

### Builder

```bash
agentforge serve-builder
```

Open the printed URL. The Builder is the recommended front door for the primary demo.

### Draft a Blueprint

```bash
agentforge draft-blueprint \
  --idea "triage support tickets and create preview notifications" \
  --out domain-packs/support-triage/domain-pack.yaml
```

Without `--out`, the command does not write a Blueprint file.

### Initialize a starter Blueprint

```bash
agentforge init-blueprint my-app --optional-module agent_runtime --optional-module workspace
agentforge plan domain-packs/my-app/domain-pack.yaml
```

### Plan and generate

```bash
agentforge plan domain-packs/hybrid-scoring-demo/domain-pack.yaml
agentforge generate domain-packs/hybrid-scoring-demo/domain-pack.yaml --force
```

`agentforge plan` is the validation source of truth. `agentforge generate` writes generated output.

## Understand existing repos

| Command | What it does | Writes files? | Existing repo modification? | Safety notes |
| --- | --- | --- | --- | --- |
| `agentforge analyze-repo` | Creates a compatibility and architecture report | Only with `--output` | No | Analysis-only; skips vendor/local/generated directories |
| `agentforge plan-extension` | Plans possible AgentForge module additions | Only with `--output` | No | Advisory; no packages, routes, runtime code, or patches applied |
| `agentforge prepare-extension` | Creates or previews extension planning artifacts | Bundle mode writes output; dry-run writes nothing | Only with explicit apply mode | Apply is limited to approved low-risk files |
| `agentforge plan-deployment` | Creates deployment readiness guidance | Only with `--output` or docs bundle | No by default | Does not deploy, provision, or store secrets |

### Analyze a repo

```bash
agentforge analyze-repo path/to/repo
agentforge analyze-repo path/to/repo --format md --output repo-analysis.md
agentforge analyze-repo path/to/repo --json
```

The analyzer is read-only and local-only.

### Plan an extension

```bash
agentforge plan-extension path/to/repo
agentforge plan-extension analysis.json --from-report
agentforge plan-extension path/to/repo --modules agent_runtime,dashboard_workspace --format md --output extension-plan.md
```

The extension planner describes likely file impact, prerequisites, phases, and risks. It does not apply patches.

### Prepare extension artifacts

```bash
agentforge prepare-extension path/to/repo --output agentforge-output/repo-extension
agentforge prepare-extension path/to/repo --modules agent_runtime --dry-run
agentforge prepare-extension path/to/repo --modules agent_runtime --apply
agentforge prepare-extension path/to/repo --modules agent_runtime --apply --yes
```

Default and dry-run behavior are safe planning flows. Apply mode is explicit and limited to approved docs, Blueprint seed, and checklist files. It does not modify runtime code, install packages, stage/commit/push, deploy, or run target scripts.

### Plan deployment

```bash
agentforge plan-deployment path/to/repo
agentforge plan-deployment analysis.json --from-report --format md
agentforge plan-deployment path/to/repo --platform railway --output deploy-plan.md
agentforge plan-deployment path/to/repo --docs-bundle --output agentforge-output/deploy-plan
```

The deployment planner creates readiness checklists and recommendations. It does not deploy infrastructure or run cloud CLIs.

## Safety / planning commands

| Command | Recommended use |
| --- | --- |
| `prepare-extension --dry-run` | Preview planned writes, conflicts, dirty git state, validation commands, and next steps before any apply |
| `prepare-extension --apply --yes` | Use only when intentionally writing approved low-risk docs/blueprint/checklist files |
| `plan-deployment` | Produce platform recommendations and release checklists without deploying |

## Validation commands

```bash
python -m pytest tests/generator/ -v
make validate
```

`make validate` runs generator tests, generated backend tests, frontend build, and frontend lint. It does not require live LLM/API keys.

With live backend and frontend servers running:

```bash
make run-e2e
```
