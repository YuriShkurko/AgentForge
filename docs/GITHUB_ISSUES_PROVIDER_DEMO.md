# GitHub Issues Real-Data Demo

This is the optional real-data variant of the GitHub Issues Workspace demo. It shows the same generated model-driven app talking to a real public GitHub repository through Provider Runtime v0 — read-only, no OAuth, no write-back, and no repo mutation.

The default `make validate` path remains fully offline and mocks GitHub responses. You do not need a token, network access, or this doc to validate the generated app.

## What this proves

- AgentForge generates a runnable model-driven app from `domain-packs/github-issues-workspace/domain-pack.yaml` with no manual code.
- Provider Runtime v0 fetches issues from a real GitHub repo through a read-only adapter.
- Provider sync reuses the shared importer pipeline: same field mapping, validation, upsert, and run history that CSV/JSON imports use.
- No OAuth, no secret entry UI, no write-back to GitHub, and no repo mutation.
- Default generated backend tests mock provider responses, so live GitHub access is not required for `make validate` or generator tests.

## Prerequisites

- A public GitHub repo with safe demo issues (or an owned repo with read access).
- `GITHUB_REPO` in `owner/repo` format. For this demo: `YuriShkurko/agentforge`.
- A GitHub token with read-only access to Issues. A fine-grained personal access token scoped to a single repo with `Issues: Read-only` is recommended.
- Token must be kept out of source control. Never commit `.env`. Never paste a token into chat, logs, screenshots, or commit messages.

## 1. Generate the app

From the AgentForge repo root:

```bash
agentforge plan domain-packs/github-issues-workspace/domain-pack.yaml
agentforge generate domain-packs/github-issues-workspace/domain-pack.yaml --output .tmp/github-issues-workspace --force
cd .tmp/github-issues-workspace
make validate
```

`make validate` runs backend tests (with mocked GitHub responses) plus frontend build/lint. It must pass before configuring real env vars.

## 2. Configure environment variables

The generated app reads `GITHUB_TOKEN` and `GITHUB_REPO` from the backend process environment. They are never persisted by the app and never shown in the UI.

Option A — export in your shell (preferred for one-off demos):

```bash
export GITHUB_REPO=YuriShkurko/agentforge
export GITHUB_TOKEN=<your-fine-grained-token>
```

Option B — use a local `.env` file. The generator writes a `.env.example` in the generated app root listing the expected variable names. Copy it to `.env` and fill in values:

```bash
cp .env.example .env
# edit .env in a local editor; do not paste the token into chat or commits
```

Then load it into the current shell before starting the backend, without printing values:

```bash
set -a
source .env
set +a
```

Safety reminders:

- `.env` must be gitignored. The AgentForge repo's root `.gitignore` already ignores `.env`. Verify in any new generated-app location with `git check-ignore -v .env`.
- Do not `cat`, `echo`, `printf`, or otherwise print `.env` or the token value.
- Do not commit `.env` or the token. Use placeholder text (`<your-fine-grained-token>`) in docs, screenshots, and bug reports.
- Rotate the token if you suspect any leak.

## 3. Run the generated app

In one terminal:

```bash
make run-backend
```

In a second terminal:

```bash
make run-frontend
```

The frontend serves at `http://localhost:5173`; the backend API at `http://localhost:8000` with docs at `http://localhost:8000/docs`.

## 4. Use the Providers panel

1. Open `http://localhost:5173` and click **Providers** in the sidebar.
2. The panel lists the `github_issues` provider and its env status. With `GITHUB_TOKEN` and `GITHUB_REPO` present, status is `configured`; otherwise it shows the missing variable names — secret values are never echoed.
3. Click **Preview** to fetch issues from GitHub and run them through the importer's validation/mapping logic without writing rows. The response shows planned inserts and updates plus any rejected rows.
4. Click **Sync** to commit. Records appear in the **Issues** view with the same fields the importer would have produced from JSON.
5. Open the **Issues** view to confirm rows landed and that titles/state/labels match the live repo.
6. Click **Sync** again. Records should update in place (matched on `external_id` via the `github_issues_import` upsert key) rather than duplicating. The run history should record both runs.
7. Open **Imports → Run history** (or `GET /imports/runs` / `GET /providers/runs`) to see source (`provider`), status (`ok` or `rejected`), counts, and timestamps for each sync.

Equivalent API-only flow (useful for headless smoke):

```bash
curl http://localhost:8000/providers
curl -X POST http://localhost:8000/providers/github_issues/preview
curl -X POST http://localhost:8000/providers/github_issues/sync
curl -X POST http://localhost:8000/providers/github_issues/sync
curl http://localhost:8000/providers/runs
```

## 5. Troubleshooting

- **Missing env vars**: `/providers` reports `configured: false` with `missing: [GITHUB_TOKEN, GITHUB_REPO]`. Re-export and restart the backend so the new environment is picked up.
- **Wrong repo format**: `GITHUB_REPO` must be `owner/repo`. Bare repo names or full URLs are rejected with `GITHUB_REPO must be in owner/repo format`.
- **Token lacks permission**: GitHub returns 403/404. The error surfaces as `GitHub API error 403: ...` from the provider; widen the token's repo scope or use a public repo.
- **Repo has no issues**: Preview/sync return zero records and an `ok` run with empty counts. This is not an error.
- **Private repo access**: Requires a token whose owner has read access to that repo. The provider only reads; it cannot grant access.
- **Rate limits / API errors**: The provider surfaces the raw GitHub error code and a short message. Wait for the rate limit window to reset or use an authenticated token (anonymous limits are far lower).
- **Stale generated app or frontend build**: Re-run `agentforge generate ... --force` and `make validate`. The Providers button only appears when the Blueprint declares `model.providers`.

## 6. Safety notes

- Provider Runtime v0 is **read-only**. There is no code path that creates, updates, comments on, or closes GitHub issues.
- The only GitHub API call is `GET /repos/{owner}/{repo}/issues` with `state` and `labels` filters from the Blueprint.
- Secrets live only in process environment variables. The Providers panel surfaces `configured`/`missing` status, never the values.
- Never commit `.env`, never commit tokens, never paste tokens into chat/screenshots/issues.
- Default `make validate` and generator tests run against mocked provider responses; no token or network is required to validate the generated app.

## Optional live smoke summary

When env vars are already present, a minimal real-data smoke is:

1. Generate the app and run `make validate`.
2. Start backend and frontend.
3. `POST /providers/github_issues/preview` — confirm record count > 0 against the public demo repo.
4. `POST /providers/github_issues/sync` — confirm records persist to the **Issues** view.
5. `POST /providers/github_issues/sync` again — confirm record count is unchanged and run history shows two `ok` runs.
6. Record only non-secret results (counts, run status, any error codes). Never include the token.
