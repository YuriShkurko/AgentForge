# AgentForge root Makefile
# Requires: Python 3.12+, Node 18+, pip, npm
# Install generator first: pip install -e generator/

DEMO_PACK   := domain-packs/hybrid-scoring-demo/domain-pack.yaml
DEMO_OUT    := examples/hybrid-scoring-demo
BACKEND_DIR := $(DEMO_OUT)/backend
FRONTEND_DIR := $(DEMO_OUT)/frontend

.PHONY: help generate-demo test-generator test-backend run-backend run-frontend run-e2e validate

help:
	@echo "AgentForge Makefile targets:"
	@echo "  generate-demo    Regenerate examples/hybrid-scoring-demo from its domain pack"
	@echo "  test-generator   Run generator unit/snapshot tests"
	@echo "  test-backend     Run generated backend tests (SQLite in-memory, no DB needed)"
	@echo "  run-backend      Start generated backend dev server on :8000"
	@echo "  run-frontend     Start generated frontend dev server on :5173"
	@echo "  run-e2e          Run Playwright E2E tests (requires running stack)"
	@echo "  validate         Run all tests and build steps (no live server needed)"

# ── Generator ────────────────────────────────────────────────────────────────

generate-demo:
	@echo "Regenerating $(DEMO_OUT)..."
	rm -rf $(DEMO_OUT)
	agentforge generate $(DEMO_PACK)
	@echo "Done. See $(DEMO_OUT)/run_commands.txt for next steps."

test-generator:
	pytest tests/generator/ -v --basetemp=.tmp/pytest-generator-validate

# ── Generated app — backend ───────────────────────────────────────────────────

test-backend:
	cd $(BACKEND_DIR) && pip install -r requirements-dev.txt -q && pytest -v

run-backend:
	cd $(BACKEND_DIR) && pip install -r requirements-dev.txt -q && \
	    python -c "import os, subprocess, sys; os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///./demo.db'); raise SystemExit(subprocess.call([sys.executable, '-m', 'uvicorn', 'app.main:app', '--reload', '--host', '0.0.0.0', '--port', '8000']))"

# ── Generated app — frontend ──────────────────────────────────────────────────

run-frontend:
	cd $(FRONTEND_DIR) && npm install --silent && npm run dev

# ── Generated app — E2E ───────────────────────────────────────────────────────

run-e2e:
	@echo "NOTE: backend must be running on :8000 and frontend on :5173"
	cd $(FRONTEND_DIR) && npm install --silent && \
	    rmdir /s /q node_modules\.vite 2>NUL || true && \
	    npm run test:e2e

# ── Full validation (no live server) ─────────────────────────────────────────

validate: test-generator test-backend
	@echo ""
	@echo "Running frontend build + lint..."
	cd $(FRONTEND_DIR) && npm install --silent && npm run build && npm run lint
	@echo ""
	@echo "Validation complete. Run 'make run-e2e' with live stack for E2E."
