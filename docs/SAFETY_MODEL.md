# AgentForge Safety Model

AgentForge v1.0 emphasizes trust. The project should be safe to inspect, run, validate, and demo locally.

## Core guarantees

AgentForge does not:

- deploy infrastructure;
- spend money;
- modify existing repositories by default;
- require live LLM/API access for validation;
- run cloud CLIs;
- store real secrets;
- stage, commit, or push changes;
- autonomously rewrite application code.

## New-app generation safety

The new-app flow uses an App Blueprint and a local Application Template.

```bash
agentforge plan domain-packs/hybrid-scoring-demo/domain-pack.yaml
agentforge generate domain-packs/hybrid-scoring-demo/domain-pack.yaml --force
```

Safety boundaries:

- `agentforge plan` validates and reports; it does not write generated app files.
- `agentforge generate` writes generated output from the Blueprint/template pair.
- The generated demo uses fixture data and deterministic logic.
- No live LLM or paid provider API is required.
- Notification behavior is preview-only; no real external delivery is wired.

## Builder and scripted planner safety

The Builder and scripted planner are local and deterministic.

They do not:

- call live LLMs;
- call external provider APIs;
- deploy;
- modify repositories;
- write files from the browser automatically.

`agentforge draft-blueprint` writes only when an explicit `--out` path is provided.

## Existing-repo analysis safety

`agentforge analyze-repo` is analysis-only.

It does not:

- mutate the target repo;
- generate or apply patches;
- install packages;
- run target scripts;
- call live LLMs/APIs;
- require internet access;
- inspect secret values.

It skips local/vendor/generated directories such as `.git`, `node_modules`, `.venv`, `dist`, `build`, `.next`, `.scribe`, and `.tmp`.

## Extension planning safety

`agentforge plan-extension` is advisory. It describes possible module additions, likely file impact, migration phases, prerequisites, and risks.

It does not:

- apply patches;
- overwrite files;
- install dependencies;
- create branches;
- run scripts;
- modify runtime code.

## Patch bundle and apply safety

`agentforge prepare-extension` supports bundle, dry-run, and explicit apply workflows.

Safe defaults:

- bundle mode writes a separate planning output directory;
- `--dry-run` prints planned writes and safety checks without writing files;
- apply mode requires `--apply` and interactive confirmation or `--yes`;
- dirty git state and overwrite conflicts are refused by default;
- no staging, commits, pushes, installs, script runs, or deployments occur.

Approved apply scope is intentionally narrow:

- AgentForge docs;
- App Blueprint seed files;
- migration or validation checklists.

Apply mode must not write risky runtime/package/router/CI files.

## Deployment planner safety

`agentforge plan-deployment` is planning-only.

It can detect signals and write reports/checklists, but it does not:

- deploy;
- provision cloud resources;
- run cloud CLIs;
- create accounts;
- spend money;
- store secrets;
- modify target repositories by default.

## Validation safety

The main validation commands are local:

```bash
python -m pytest tests/generator/ -v
make validate
```

They do not require live LLM/API keys. Playwright E2E requires a live local generated stack but still does not require paid external services.

## CI and badge policy

A green CI badge is useful for release trust, but only if it is real.

For v1.0 readiness:

- check whether `.github/workflows/` exists;
- if CI exists, verify it passes;
- if CI does not exist, either add minimal CI or explicitly defer it;
- add a README badge only when CI is present and reliable.

Do not fake CI status.
