# Project Workspace Demo

A generated **Project Workspace Demo** app built with the AgentForge `project_workspace_app` archetype.

This app is deterministic and local-first. It demonstrates project/task persistence, notes/activity, scripted agent tools, workspace widgets, backend tests, and frontend build/lint without live LLM/API requirements.

## Local run

```bash
cd backend
pip install -r requirements-dev.txt
DATABASE_URL=sqlite+aiosqlite:///./demo.db uvicorn app.main:app --reload
```

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Validation

From the generated app root, run backend and frontend validation separately:

```bash
cd backend
pytest
```

```bash
cd frontend
npm install
npm run build
npm run lint
```

If you run both blocks in the same shell, return to the generated app root before starting the frontend block.
