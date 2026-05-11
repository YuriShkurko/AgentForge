# AgentForge Deployment Planner

`agentforge plan-deployment` is the v0.9 planning-only deployment readiness tool.

It inspects a local repository or an `agentforge analyze-repo --json` report and produces an advisory readiness report. It does **not** deploy, provision cloud resources, create paid infrastructure, run cloud CLIs, run target repo scripts, install packages, read/store secrets, commit, stage, push, or modify the target repo by default.

## Commands

```bash
agentforge plan-deployment ../my-project
agentforge plan-deployment analysis.json --from-report --format md
agentforge plan-deployment ../my-project --platform railway --output deploy-plan.md
agentforge plan-deployment ../my-project --docs-bundle --output agentforge-output/deploy-plan
agentforge plan-deployment ../my-project --format json
```

Options:

- `--from-report`: read an analyzer JSON report instead of scanning a repo path.
- `--format text|md|json`: choose report format.
- `--json`: shortcut for `--format json`.
- `--output <path>`: write report file, or docs bundle directory with `--docs-bundle`.
- `--platform railway|render|fly|aws-ecs|docker-vps|auto`: filter platform recommendations.
- `--include-cost-notes`: include additional advisory cost notes.
- `--docs-bundle`: write `README.md`, `deployment-plan.md`, checklists, platform recommendations, and risk notes.
- `--max-files`, `--include-tests`: scanning controls for repo path input.

## Readiness statuses

- `ready`: strong evidence is present.
- `nearly_ready`: partial evidence exists but review is needed.
- `needs_work`: important deployment prerequisites are missing.
- `blocked` / `unknown`: insufficient information or major blockers.

Readiness areas include local validation, build commands, Docker readiness, env examples, database/migrations, health checks, CI, secrets handling, frontend/backend separation, and production start commands.

## Detection scope

The planner looks for safe signals only:

- backend framework hints such as FastAPI, Flask, Django, Express, or Next API;
- frontend framework/build hints such as Vite, React, Next.js, build scripts, output directory, and public env prefixes;
- database and migration hints such as PostgreSQL, SQLite, MongoDB, Alembic, and Prisma;
- Dockerfile, compose files, exposed ports, and healthcheck hints;
- GitHub Actions, Makefile, test/build command hints;
- `.env.example` and env var names from config code without reading real secret values;
- health, readiness, metrics, and logging hints.

## Platform recommendations

Recommendations are advisory and include fit, rationale, requirements, missing pieces, cost/risk notes, and manual next steps for:

- Railway
- Render
- Fly.io
- AWS ECS/Fargate
- generic Docker VPS
- local Docker Compose only / manual Docker path where appropriate

AgentForge intentionally omits commands that create paid resources. Review provider pricing and risk manually before creating anything.

## Docs bundle

With `--docs-bundle --output <dir>`, AgentForge writes:

- `README.md`
- `deployment-plan.md`
- `env-checklist.md`
- `docker-readiness.md`
- `ci-readiness.md`
- `platform-recommendations.md`
- `risk-notes.md`

The bundle is written to the explicit output directory. It does not touch the target repo unless you intentionally choose an output path inside it.

## Future work

Future versions may add richer platform templates or deployment manifest previews, but v0.9 remains planning-only and does not execute deployment actions.
