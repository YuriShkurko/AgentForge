# Project Workspace Demo

A generated **Project Workspace Demo** app built with the AgentForge `project_workspace_app` archetype.

This app is deterministic and local-first. It demonstrates project/task persistence, notes/activity, scripted agent tools, workspace widgets, backend tests, and frontend build/lint without live LLM/API requirements.

## Local run

From the generated app root, install dependencies once:

```bash
make install
```

Then run the backend and frontend in separate terminals:

```bash
make run-backend
make run-frontend
```

Open `http://localhost:5173`.

## Validation

From the generated app root:

```bash
make validate
```

`make validate` runs backend tests plus frontend build/lint. `make test` currently runs backend tests only because this generated app has no frontend unit test target.
