# Generated app Makefile
# Assumes Python, pip, Node, and npm are available in your active shell.

.PHONY: help install install-backend install-frontend test test-backend build-frontend lint-frontend validate run-backend run-frontend

help:
	@echo "Generated app commands:"
	@echo "  make install          Install backend and frontend dependencies"
	@echo "  make test             Run backend tests"
	@echo "  make build-frontend   Build the React frontend"
	@echo "  make lint-frontend    Lint the React frontend"
	@echo "  make validate         Run backend tests plus frontend build/lint"
	@echo "  make run-backend      Start FastAPI backend on :8000 with local SQLite"
	@echo "  make run-frontend     Start Vite frontend on :5173"

install: install-backend install-frontend

install-backend:
	python -m pip install -r backend/requirements-dev.txt

install-frontend:
	cd frontend && npm install

test: test-backend
	@echo "No frontend unit test target is defined; backend tests completed."

test-backend: install-backend
	cd backend && python -m pytest -q

build-frontend: install-frontend
	cd frontend && npm run build

lint-frontend: install-frontend
	cd frontend && npm run lint

validate: test-backend build-frontend lint-frontend
	@echo "Generated app validation complete."

run-backend:
	cd backend && python -c "import os, subprocess, sys; os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///./demo.db'); raise SystemExit(subprocess.call([sys.executable, '-m', 'uvicorn', 'app.main:app', '--reload', '--host', '0.0.0.0', '--port', '8000']))"

run-frontend:
	cd frontend && npm run dev
