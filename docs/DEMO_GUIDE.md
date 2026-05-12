# AgentForge Demo Guide

The demo should make AgentForge understandable in a few minutes: local Builder, drafted App Blueprint, multiple generated FastAPI + React app shapes, deterministic validation, and safe existing-repo planning.

## Primary Golden Demo Path

Use scoring/triage as the main generated-app story:

```text
Open Builder
→ draft Blueprint from app idea
→ validate/plan Blueprint
→ generate app
→ run generated app
→ ingest/score records
→ use agent chat
→ pin workspace widget
→ show persistence/triage
```

## 1. Open the Builder

```bash
pip install -e generator/
agentforge serve-builder
```

Open the local URL printed by the command.

Suggested idea:

```text
Build a local app that ingests customer records, scores which accounts need follow-up, previews outreach notifications, and lets an operator triage results with an agent assistant.
```

Show that the Builder gives a product-oriented front door before dropping into YAML.

## 2. Draft and inspect the Blueprint

Use the Builder's scripted drafting flow, then show the Blueprint source preview.

Key trust points:

- deterministic scripted planner;
- no live LLM/API required;
- no repo writes from the browser;
- controlled Blueprint customization for app copy, labels, and starter prompts within supported archetypes;
- `agentforge plan` remains the validation source of truth.

If you want a CLI-only fallback:

```bash
agentforge draft-blueprint \
  --idea "triage customer records, score follow-up priority, preview notifications, and use an agent workspace" \
  --out domain-packs/demo-v1/domain-pack.yaml
```

## 3. Validate and generate

For the committed demo Blueprint:

```bash
agentforge plan domain-packs/hybrid-scoring-demo/domain-pack.yaml
agentforge generate domain-packs/hybrid-scoring-demo/domain-pack.yaml --force
```

Emphasize that planning is separate from generation.

## 4. Run the generated app

Terminal 1:

```bash
make run-backend
```

Terminal 2:

```bash
make run-frontend
```

Open `http://localhost:5173`.

## 5. Demo the generated workflow

In the generated UI:

1. Run ingestion.
2. Score records.
3. Review scored records and explanations.
4. Create preview notifications.
5. Submit a triage action such as accept, skip, or save.
6. Open agent chat.
7. Ask the agent to summarize or work with scored records.
8. Ask the agent to pin a compatible result into the workspace.
9. Refresh the page.
10. Show persisted conversations, workspace widgets, and action history.

The generated app demonstrates real application surfaces without external delivery, paid APIs, or a live LLM.

If the drafted Blueprint includes `customization`, point out that it changes visible app wording such as record labels, workflow titles, agent starters, and workspace empty states. It does not create arbitrary app features or live integrations.

## Alternate generated-app demo: Project Workspace

Use this after the scoring/triage golden path to show AgentForge can generate a meaningfully different full-stack app:

```bash
agentforge plan domain-packs/project-workspace-demo/domain-pack.yaml
agentforge generate domain-packs/project-workspace-demo/domain-pack.yaml --output .tmp/project-workspace-demo --force
```

Then validate the generated app:

```bash
cd .tmp/project-workspace-demo/backend && pytest
cd ../frontend && npm install && npm run build && npm run lint
```

The generated Project Workspace app demonstrates seeded projects/tasks, task status and priority updates, notes/activity, scripted agent chat over project tools, and pinned workspace widgets. It does not use scoring, triage, notification previews, live LLMs, or external APIs.

Suggested screenshot flow:

1. Seed the sample workspace and show the project overview/dashboard.
2. Click a task status to show task list/status updates.
3. Add an operator note and show notes/activity.
4. Ask the scripted agent to `pin task list` and show the agent/workspace area.
5. Refresh and show the pinned widget still present.

## Secondary Demo Path: existing repo planning

Use this after the primary demo, or when the audience cares about existing applications.

```text
analyze repo
→ plan extension
→ prepare patch bundle
→ plan deployment
```

Example commands:

```bash
agentforge analyze-repo path/to/repo --format md --output repo-analysis.md
agentforge plan-extension path/to/repo --format md --output extension-plan.md
agentforge prepare-extension path/to/repo --dry-run
agentforge plan-deployment path/to/repo --format md --output deployment-plan.md
```

Talking points:

- analyzer is read-only;
- extension planner is advisory;
- prepare-extension defaults to bundle/dry-run workflows;
- apply mode is explicit and limited to low-risk docs/blueprint/checklist files;
- deployment planner does not deploy or provision infrastructure.

## Demo assets

The README uses a small screenshot walkthrough stored in `docs/assets/screenshots/`:

- `builder-start.png` — Builder idea entry screen;
- `builder-plan.png` — drafted Blueprint review and Live app plan;
- `builder-commands.png` — local generation commands;
- `generated-scoring.png` — scoring/triage generated app flow;
- `generated-agent-workspace.png` — scoring app scripted agent pinning a workspace widget;
- `generated-persistence.png` — scoring app workspace state after refresh;
- `generated-project-overview.png` — project workspace overview/dashboard;
- `generated-project-tasks.png` — project workspace task list/status update;
- `generated-project-activity.png` — project workspace notes/activity;
- `generated-project-agent-workspace.png` — project workspace scripted agent and workspace;
- `generated-project-persistence.png` — project workspace pinned widgets after refresh.

Keep screenshots focused on the stable scoring/triage and project/task workspace paths. Defer large GIFs or broad terminal-output galleries if they slow the release or are likely to rot.

## Validation before recording or presenting

```bash
python -m pytest tests/generator/ -v
make validate
```

Run Playwright only when the backend and frontend are already live:

```bash
make run-e2e
```
