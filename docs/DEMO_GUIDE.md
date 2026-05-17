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

### Optional: Builder Assistant chat path

With `agentforge serve-builder` running, the Describe step exposes an inline chat panel backed by the deterministic local assistant (`/api/planner/assistant/*`). Use this path when you want to show the conversational front door for a model-driven app.

After applying an assistant proposal, use the Review step's Local Control Room to validate the active Blueprint, generate a sandboxed app under `.tmp/builder-runs/<safe-run-id>/app`, and run `make validate` while showing the equivalent commands and logs. This is local-only: no GitHub, deployment, arbitrary shell commands, output path selection, or generated app server process management.

Suggested flow:

1. Send a deliberately vague idea such as `app` and show that the assistant asks bounded clarifying questions instead of guessing.
2. Send a specific idea such as `support ticket triage with title, status, priority, owner, and notes to close tickets, sync from github issues` and point out:
   - the **Proposed Blueprint diff** summary with per-entity / per-page / per-action / per-import / per-provider rows;
   - the **Imports** and **Providers** meta rows listing `ticket_import` and a read-only `github_issues` provider with `target_import=ticket_import` and env-var *names* `GITHUB_TOKEN` / `GITHUB_REPO` (no secret values are stored);
   - the assistant message confirming the proposal validated through the same Python schema path the CLI uses.
3. Click **Reject** to show the draft is untouched, then re-send the same idea and click **Apply** to install the proposal into the Builder draft. Apply re-runs `DomainPack.model_validate` through `apply-preview` before any state changes.
4. (Optional) Edit the YAML preview to break it — e.g. set a provider `target_import` to a missing id — and click Apply again. The assistant surfaces a structured **Validation guidance** block with a category tag (`missing_target_import`), a plain-language message, a suggested manual fix, an optional follow-up question, and a collapsible raw error. Nothing is repaired automatically; the user has to edit and re-Apply.

Trust points to call out:

- scripted, deterministic, offline — no live LLM in the default path;
- no GitHub, deployment, OAuth, or secret handling;
- Apply mutates only the in-memory Builder draft; Reject leaves it alone;
- raw schema errors stay visible alongside the assistant's guidance.

For local-only live Assistant demos, you may put `AGENTFORGE_ASSISTANT_PROVIDER=openai`, `OPENAI_API_KEY=...`, and optional `AGENTFORGE_ASSISTANT_LLM_MODEL=...` in a `.env` file before running `agentforge serve-builder`. The Builder server loads that file only for local Builder development, does not override exported shell variables, and never prints secret values or exposes them through `/api/planner/status`. Do not commit real `.env` files.

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
cd .tmp/project-workspace-demo
make validate
```

The generated Project Workspace app demonstrates seeded projects/tasks, task status and priority updates, notes/activity, scripted agent chat over project tools, and pinned workspace widgets. It does not use scoring, triage, notification previews, live LLMs, or external APIs.

Suggested screenshot flow:

1. Seed the sample workspace and show the project overview/dashboard.
2. Click a task status to show task list/status updates.
3. Add an operator note and show notes/activity.
4. Ask the scripted agent to `pin task list` and show the agent/workspace area.
5. Refresh and show the pinned widget still present.

## Experimental model-driven app demo

Use this to show the bounded model-driven path beyond fixed app templates:

```bash
agentforge plan domain-packs/client-onboarding-workspace/domain-pack.yaml
agentforge generate domain-packs/client-onboarding-workspace/domain-pack.yaml --output .tmp/client-onboarding-workspace --force
agentforge plan domain-packs/vendor-risk-tracker/domain-pack.yaml
agentforge generate domain-packs/vendor-risk-tracker/domain-pack.yaml --output .tmp/vendor-risk-tracker --force
```

Both examples use `app_archetype: model_driven_app` and the same generator path. They produce different FastAPI routes, SQLAlchemy/Pydantic models, React labels/pages/forms, enum values, workflow actions, seed records, dashboard cards, accent colors, entity layouts, bounded page compositions, and visual recipes from their `model` blocks. Client Onboarding uses a board/workspace composition with a workspace-board recipe; Vendor Risk uses a register/table composition with an executive-register recipe. This is bounded CRUD/workflow generation with controlled presentation hints, not arbitrary app generation, per-prompt UI design, arbitrary connector DSLs, or visual builder support. Provider Runtime v0 is a separate bounded model-driven option demonstrated below.

Suggested validation:

```bash
cd .tmp/client-onboarding-workspace
make validate
```

Provider Runtime v0 can be shown with either the GitHub Issues Workspace example or the local HTTP JSON Vendor Feed example.

GitHub Issues Workspace:

```bash
agentforge plan domain-packs/github-issues-workspace/domain-pack.yaml
agentforge generate domain-packs/github-issues-workspace/domain-pack.yaml --output .tmp/github-issues-workspace --force
cd .tmp/github-issues-workspace
make validate
```

HTTP JSON Vendor Feed, using a local mock JSON endpoint instead of a real external API:

```bash
agentforge generate domain-packs/http-json-vendor-feed/domain-pack.yaml --output .tmp/http-json-vendor-feed --force
cd .tmp/http-json-vendor-feed
make validate
```

The Providers panel is read-only and reuses the generated import pipeline. Without environment variables it shows missing env var names and still passes default validation because generated tests mock provider responses. For GitHub, `GITHUB_REPO` must be `owner/repo`. For the HTTP JSON Vendor Feed pack, set `EXTERNAL_VENDOR_FEED_URL` plus `EXTERNAL_VENDOR_FEED_TOKEN`; the token can be a fake local value because the pack configures `auth: bearer` and the mock server does not validate it. v0 has no OAuth, no write-back, no repo mutation, no provider marketplace, no arbitrary connector DSL, no scheduled sync, and no live network requirement for default validation.

For the optional real-data GitHub variant — generating the app, configuring `GITHUB_TOKEN`/`GITHUB_REPO`, running preview/sync against a public repo, and verifying upsert behavior on a second sync — see [GITHUB_ISSUES_PROVIDER_DEMO.md](GITHUB_ISSUES_PROVIDER_DEMO.md).

For the local generic HTTP JSON provider demo — generating HTTP JSON Vendor Feed, serving `.tmp/mock-feed/vendors.json`, setting `EXTERNAL_VENDOR_FEED_URL`/`EXTERNAL_VENDOR_FEED_TOKEN`, previewing, syncing, syncing again, and checking run history — see [HTTP_JSON_PROVIDER_DEMO.md](HTTP_JSON_PROVIDER_DEMO.md).

Suggested screenshot flow:

1. Load seed data.
2. Switch between generated entity pages.
3. Create a record with enum/select fields.
4. Run the generated workflow action.
5. Compare with Vendor Risk Tracker to show different entities/routes, dashboard cards, accent colors, page compositions, empty states, badge treatments, and visual recipes from the same path: Client Onboarding is board/workspace-like, while Vendor Risk is compact register/table-like.

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
- `builder-plan.png` — drafted Blueprint review, Customize app details panel, and Live app plan;
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
