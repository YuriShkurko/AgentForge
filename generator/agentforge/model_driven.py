"""Bounded model-driven FastAPI/React app generation."""
from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import Any

from agentforge.pack import DomainPack, ModelDrivenApp, ModelField


def generate_model_driven_app(pack: DomainPack, output_dir: Path, *, dry_run: bool = False) -> list[str]:
    if pack.model is None:
        raise ValueError("model_driven_app requires pack.model")
    files = _files(pack, pack.model)
    written: list[str] = []
    for rel_path, content in files.items():
        written.append(rel_path)
        if dry_run:
            continue
        target = output_dir / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content.rstrip() + "\n", encoding="utf-8")
    return written


def _files(pack: DomainPack, model: ModelDrivenApp) -> dict[str, str]:
    meta = _metadata(pack, model)
    return {
        "backend/app/__init__.py": "",
        "backend/app/database.py": _backend_database(),
        "backend/app/models.py": _backend_models(model),
        "backend/app/schemas.py": _backend_schemas(model),
        "backend/app/main.py": _backend_main(pack, model),
        "backend/tests/__init__.py": "",
        "backend/tests/test_model_driven_app.py": _backend_tests(model),
        "backend/requirements.txt": "fastapi==0.115.5\nuvicorn[standard]==0.32.1\nsqlalchemy==2.0.36\npydantic==2.10.3",
        "backend/requirements-dev.txt": "-r requirements.txt\npytest==8.3.4\nhttpx==0.28.0",
        "frontend/index.html": f'<div id="root"></div><script type="module" src="/src/main.tsx"></script><title>{pack.display_name}</title>',
        "frontend/package.json": _frontend_package(pack),
        "frontend/tsconfig.json": _frontend_tsconfig(),
        "frontend/eslint.config.js": _frontend_eslint(),
        "frontend/src/main.tsx": _frontend_main(),
        "frontend/src/App.tsx": _frontend_app(pack, meta),
        "frontend/src/styles.css": _frontend_styles(),
        "Makefile": _makefile(),
        "README.md": _readme(pack),
        "app-model.json": json.dumps(meta, indent=2),
        "run_commands.txt": _run_commands(pack),
    }


def _class_name(name: str) -> str:
    return "".join(part.capitalize() for part in name.split("_"))


def _label(field: ModelField) -> str:
    return field.label or field.name.replace("_", " ").title()


def _py_type(field: ModelField) -> str:
    return {"integer": "int", "boolean": "bool", "date": "date", "relation": "int"}.get(field.type, "str")


def _column(field: ModelField) -> str:
    if field.type in {"integer", "relation"}:
        return "Integer"
    if field.type == "boolean":
        return "Boolean"
    if field.type == "date":
        return "Date"
    return "Text" if field.type == "text" else "String(255)"


def _metadata(pack: DomainPack, model: ModelDrivenApp) -> dict[str, Any]:
    return {
        "app": {"name": pack.name, "displayName": pack.display_name, "description": pack.domain.product_purpose},
        "entities": [
            {
                "name": e.name,
                "className": _class_name(e.name),
                "labelSingular": e.label_singular,
                "labelPlural": e.label_plural,
                "route": f"/{e.name.replace('_', '-')}",
                "fields": [
                    {
                        "name": f.name,
                        "label": _label(f),
                        "type": f.type,
                        "required": f.required,
                        "enumValues": f.enum_values,
                        "targetEntity": f.target_entity,
                    }
                    for f in e.fields
                ],
            }
            for e in model.entities
        ],
        "pages": [p.model_dump() for p in model.pages],
        "actions": [a.model_dump() for a in model.actions],
        "seedData": model.seed_data,
    }


def _backend_database() -> str:
    return textwrap.dedent('''
        from sqlalchemy import create_engine
        from sqlalchemy.orm import DeclarativeBase, sessionmaker

        DATABASE_URL = "sqlite:///./app.db"
        engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
        SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

        class Base(DeclarativeBase):
            pass

        def get_db():
            db = SessionLocal()
            try:
                yield db
            finally:
                db.close()
    ''')


def _backend_models(model: ModelDrivenApp) -> str:
    chunks = ["from datetime import date\nfrom sqlalchemy import Boolean, Date, Integer, String, Text\nfrom sqlalchemy.orm import Mapped, mapped_column\nfrom app.database import Base\n"]
    for entity in model.entities:
        lines = [f"class {_class_name(entity.name)}(Base):", f"    __tablename__ = \"{entity.name}\"", "", "    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)"]
        for field in entity.fields:
            col = _column(field)
            nullable = "False" if field.required else "True"
            default = ""
            if field.type == "boolean":
                default = ", default=False"
            lines.append(f"    {field.name}: Mapped[{_py_type(field)}{' | None' if not field.required else ''}] = mapped_column({col}, nullable={nullable}{default})")
        chunks.append("\n".join(lines))
    return "\n\n".join(chunks)


def _backend_schemas(model: ModelDrivenApp) -> str:
    chunks = ["from datetime import date\nfrom pydantic import BaseModel, ConfigDict, field_validator\n"]
    for entity in model.entities:
        cls = _class_name(entity.name)
        create = [f"class {cls}Create(BaseModel):"]
        if not entity.fields:
            create.append("    pass")
        for field in entity.fields:
            typ = _py_type(field)
            create.append(f"    {field.name}: {typ}{' | None = None' if not field.required else ''}")
        for field in entity.fields:
            if field.type == "enum":
                values = repr(field.enum_values)
                create += ["", f"    @field_validator(\"{field.name}\")", "    @classmethod", f"    def validate_{field.name}(cls, value):", "        if value is None:", "            return value", f"        if value not in {values}:", f"            raise ValueError(\"{field.name} must be one of {field.enum_values}\")", "        return value"]
        update = [f"class {cls}Update(BaseModel):"] + [f"    {f.name}: {_py_type(f)} | None = None" for f in entity.fields]
        read = [f"class {cls}Read({cls}Create):", "    id: int", "    model_config = ConfigDict(from_attributes=True)"]
        chunks.append("\n".join(create + [""] + update + [""] + read))
    return "\n\n".join(chunks)


def _seed_value(value: Any, field: ModelField | None = None) -> str:
    if field and field.type == "date" and isinstance(value, str):
        return f"date.fromisoformat({value!r})"
    return repr(value)


def _backend_main(pack: DomainPack, model: ModelDrivenApp) -> str:
    imports = ["from datetime import date", "from fastapi import Depends, FastAPI, HTTPException", "from fastapi.middleware.cors import CORSMiddleware", "from sqlalchemy.orm import Session", "from app.database import Base, engine, get_db", "from app import models, schemas", ""]
    body = [*imports, f"app = FastAPI(title={pack.display_name!r})", "app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:5173'], allow_methods=['*'], allow_headers=['*'])", "Base.metadata.create_all(bind=engine)", ""]
    body += ["@app.get('/health')", "def health():", "    return {'status': 'ok'}", ""]
    body += ["@app.post('/seed')", "def seed(db: Session = Depends(get_db)):", "    created = {}"]
    for entity in model.entities:
        cls = _class_name(entity.name)
        rows = model.seed_data.get(entity.name, [])
        body += [f"    if db.query(models.{cls}).count() == 0:"]
        if rows:
            for row in rows:
                field_map = {field.name: field for field in entity.fields}
                args = ", ".join(f"{k}={_seed_value(v, field_map.get(k))}" for k, v in row.items())
                body.append(f"        db.add(models.{cls}({args}))")
        else:
            body.append("        pass")
        body.append(f"    created['{entity.name}'] = db.query(models.{cls}).count()")
    body += ["    db.commit()", "    return created", ""]
    for entity in model.entities:
        cls = _class_name(entity.name); route = entity.name.replace('_','-')
        body += [f"@app.get('/{route}', response_model=list[schemas.{cls}Read])", f"def list_{entity.name}(db: Session = Depends(get_db)):", f"    return db.query(models.{cls}).order_by(models.{cls}.id).all()", ""]
        body += [f"@app.post('/{route}', response_model=schemas.{cls}Read)", f"def create_{entity.name}(payload: schemas.{cls}Create, db: Session = Depends(get_db)):", f"    item = models.{cls}(**payload.model_dump())", "    db.add(item)", "    db.commit()", "    db.refresh(item)", "    return item", ""]
        body += [f"@app.get('/{route}/{{item_id}}', response_model=schemas.{cls}Read)", f"def get_{entity.name}(item_id: int, db: Session = Depends(get_db)):", f"    item = db.get(models.{cls}, item_id)", "    if not item:", "        raise HTTPException(status_code=404, detail='not found')", "    return item", ""]
        body += [f"@app.patch('/{route}/{{item_id}}', response_model=schemas.{cls}Read)", f"def update_{entity.name}(item_id: int, payload: schemas.{cls}Update, db: Session = Depends(get_db)):", f"    item = db.get(models.{cls}, item_id)", "    if not item:", "        raise HTTPException(status_code=404, detail='not found')", "    for key, value in payload.model_dump(exclude_unset=True).items():", "        setattr(item, key, value)", "    db.commit()", "    db.refresh(item)", "    return item", ""]
    for action in model.actions:
        entity = next(e for e in model.entities if e.name == action.entity); cls = _class_name(entity.name); route = entity.name.replace('_','-')
        body += [f"@app.post('/{route}/{{item_id}}/actions/{action.name}')", f"def action_{action.name}(item_id: int, db: Session = Depends(get_db)):", f"    item = db.get(models.{cls}, item_id)", "    if not item:", "        raise HTTPException(status_code=404, detail='not found')"]
        if action.type == "update_status":
            body.append(f"    item.{action.field} = {action.value!r}")
        elif action.type == "mark_complete":
            field = action.field or "complete"
            body.append(f"    item.{field} = True")
        else:
            body.append("    # add_note v0 records acknowledgement only")
        body += ["    db.commit()", "    db.refresh(item)", f"    return {{'ok': True, 'entity': '{entity.name}', 'id': item.id}}", ""]
    return "\n".join(body)


def _backend_tests(model: ModelDrivenApp) -> str:
    first = model.entities[0]
    route = first.name.replace('_','-')
    sample = (model.seed_data.get(first.name) or [{}])[0]
    create = sample or {f.name: (f.enum_values[0] if f.type == 'enum' else False if f.type == 'boolean' else 1 if f.type == 'integer' else 'Test') for f in first.fields if f.required}
    enum_field = next((f for e in model.entities for f in e.fields if f.type == 'enum'), None)
    enum_entity = next((e for e in model.entities if any(f.type == 'enum' for f in e.fields)), first)
    enum_route = enum_entity.name.replace('_','-')
    lines = ["from fastapi.testclient import TestClient", "from app.main import app", "", "client = TestClient(app)", "", "def test_seed_and_list_records():", "    assert client.post('/seed').status_code == 200", f"    response = client.get('/{route}')", "    assert response.status_code == 200", "    assert isinstance(response.json(), list)", "", "def test_create_record():", f"    response = client.post('/{route}', json={create!r})", "    assert response.status_code == 200", "    assert response.json()['id'] >= 1"]
    if enum_field:
        bad = dict(create)
        # ensure payload for enum entity
        bad = {f.name: ("not_allowed" if f.name == enum_field.name else (f.enum_values[0] if f.type == 'enum' else False if f.type == 'boolean' else 1 if f.type == 'integer' else 'Test')) for f in enum_entity.fields if f.required or f.name == enum_field.name}
        lines += ["", "def test_enum_validation_rejects_bad_value():", f"    response = client.post('/{enum_route}', json={bad!r})", "    assert response.status_code == 422"]
    if model.actions:
        a = model.actions[0]; ar = a.entity.replace('_','-')
        lines += ["", "def test_workflow_action_endpoint():", "    client.post('/seed')", f"    records = client.get('/{ar}').json()", "    assert records", f"    response = client.post('/{ar}/{{}}/actions/{a.name}'.format(records[0]['id']))", "    assert response.status_code == 200", "    assert response.json()['ok'] is True"]
    return "\n".join(lines)


def _frontend_package(pack: DomainPack) -> str:
    return json.dumps({"name": f"{pack.name}-frontend", "private": True, "version": "0.1.0", "type": "module", "scripts": {"dev": "vite", "build": "tsc -b && vite build", "lint": "eslint src"}, "dependencies": {"@vitejs/plugin-react": "^4.3.3", "vite": "^5.4.11", "typescript": "^5.6.3", "react": "^18.3.1", "react-dom": "^18.3.1"}, "devDependencies": {"@types/react": "^18.3.12", "@types/react-dom": "^18.3.1", "@typescript-eslint/eslint-plugin": "^8.15.0", "@typescript-eslint/parser": "^8.15.0", "eslint": "^9.15.0"}}, indent=2)


def _frontend_tsconfig() -> str:
    return json.dumps({"compilerOptions": {"target": "ES2020", "useDefineForClassFields": True, "lib": ["DOM", "DOM.Iterable", "ES2020"], "allowJs": False, "skipLibCheck": True, "esModuleInterop": True, "allowSyntheticDefaultImports": True, "strict": True, "forceConsistentCasingInFileNames": True, "module": "ESNext", "moduleResolution": "Node", "resolveJsonModule": True, "isolatedModules": True, "noEmit": True, "jsx": "react-jsx"}, "include": ["src"]}, indent=2)


def _frontend_eslint() -> str:
    return "import tseslint from '@typescript-eslint/eslint-plugin';\nimport tsParser from '@typescript-eslint/parser';\nexport default [{ files: ['src/**/*.{ts,tsx}'], languageOptions: { parser: tsParser, parserOptions: { project: './tsconfig.json' } }, plugins: { '@typescript-eslint': tseslint }, rules: { ...tseslint.configs.recommended.rules } }];"


def _frontend_main() -> str:
    return "import React from 'react';\nimport { createRoot } from 'react-dom/client';\nimport App from './App';\nimport './styles.css';\ncreateRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>);"


def _frontend_app(pack: DomainPack, meta: dict[str, Any]) -> str:
    return f"""import {{ useEffect, useMemo, useState }} from 'react';

type Field = {{ name: string; label: string; type: string; required: boolean; enumValues: string[]; targetEntity: string }};
type Entity = {{ name: string; className: string; labelSingular: string; labelPlural: string; route: string; fields: Field[] }};
type Action = {{ name: string; label?: string; type: string; entity: string; field?: string | null; value?: string | number | boolean | null }};
type AppModel = {{ app: {{ name: string; displayName: string; description: string }}; entities: Entity[]; actions: Action[]; pages?: unknown[]; seedData?: unknown }};
const model: AppModel = {json.dumps(meta, indent=2)};
const API = 'http://localhost:8000';
type Row = Record<string, string | number | boolean | null> & {{ id?: number }};

function routeFor(entity: Entity) {{ return entity.route; }}
function emptyRow(entity: Entity) {{
  const row: Row = {{}};
  entity.fields.forEach((field) => {{ row[field.name] = field.type === 'boolean' ? false : field.type === 'integer' ? 0 : field.enumValues[0] || ''; }});
  return row;
}}

export default function App() {{
  const [active, setActive] = useState(model.entities[0].name);
  const entity = useMemo(() => model.entities.find((item) => item.name === active) || model.entities[0], [active]);
  const [rows, setRows] = useState<Row[]>([]);
  const [form, setForm] = useState<Row>(() => emptyRow(entity));
  const [message, setMessage] = useState('Ready');

  async function load(selected = entity) {{
    const response = await fetch(`${{API}}${{routeFor(selected)}}`);
    setRows(await response.json());
  }}
  useEffect(() => {{ setForm(emptyRow(entity)); void load(entity); }}, [entity]);

  async function seed() {{ await fetch(`${{API}}/seed`, {{ method: 'POST' }}); setMessage('Seed data loaded'); await load(); }}
  async function save(event: React.FormEvent) {{
    event.preventDefault();
    const response = await fetch(`${{API}}${{routeFor(entity)}}`, {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, body: JSON.stringify(form) }});
    if (!response.ok) {{ setMessage('Validation failed'); return; }}
    setMessage(`${{entity.labelSingular}} saved`); setForm(emptyRow(entity)); await load();
  }}
  async function runAction(actionName: string, id: number) {{
    await fetch(`${{API}}${{routeFor(entity)}}/${{id}}/actions/${{actionName}}`, {{ method: 'POST' }});
    setMessage('Workflow action complete'); await load();
  }}
  const actions = model.actions.filter((action) => action.entity === entity.name);
  return <main className="shell">
    <aside><p className="eyebrow">AgentForge model-driven app</p><h1>{pack.display_name}</h1><p>{pack.domain.product_purpose}</p><button onClick={{seed}}>Load seed data</button>{{model.entities.map((item) => <button className={{item.name === active ? 'active' : ''}} key={{item.name}} onClick={{() => setActive(item.name)}}>{{item.labelPlural}}</button>)}}</aside>
    <section className="content"><div className="hero"><div><p className="eyebrow">Dashboard</p><h2>{{entity.labelPlural}}</h2><p>{{message}}</p></div><strong>{{rows.length}} records</strong></div>
      <form onSubmit={{save}} className="card"><h3>Create {{entity.labelSingular}}</h3>{{entity.fields.map((field) => <label key={{field.name}}>{{field.label}}{{field.type === 'enum' ? <select value={{String(form[field.name] ?? '')}} onChange={{(event) => setForm({{...form, [field.name]: event.target.value}})}}>{{field.enumValues.map((value) => <option key={{value}} value={{value}}>{{value}}</option>)}}</select> : field.type === 'boolean' ? <input type="checkbox" checked={{Boolean(form[field.name])}} onChange={{(event) => setForm({{...form, [field.name]: event.target.checked}})}} /> : <input type={{field.type === 'date' ? 'date' : field.type === 'integer' ? 'number' : 'text'}} value={{String(form[field.name] ?? '')}} onChange={{(event) => setForm({{...form, [field.name]: field.type === 'integer' ? Number(event.target.value) : event.target.value}})}} />}}</label>)}}<button type="submit">Save {{entity.labelSingular}}</button></form>
      <div className="card"><h3>{{entity.labelPlural}}</h3><table><thead><tr><th>ID</th>{{entity.fields.map((field) => <th key={{field.name}}>{{field.label}}</th>)}}<th>Actions</th></tr></thead><tbody>{{rows.map((row) => <tr key={{row.id}}><td>{{row.id}}</td>{{entity.fields.map((field) => <td key={{field.name}}>{{String(row[field.name] ?? '')}}</td>)}}<td>{{actions.map((action) => <button key={{action.name}} onClick={{() => row.id && runAction(action.name, row.id)}}>{{action.label || action.name}}</button>)}}</td></tr>)}}</tbody></table></div>
    </section>
  </main>;
}}
"""


def _frontend_styles() -> str:
    return "body{margin:0;font-family:Inter,system-ui,sans-serif;background:#eef2ff;color:#172033}.shell{display:grid;grid-template-columns:280px 1fr;gap:24px;padding:28px}aside,.card,.hero{background:white;border:1px solid #dbe3f8;border-radius:20px;padding:20px;box-shadow:0 12px 30px #1f2a4420}aside{height:fit-content;display:grid;gap:12px}button{border:0;border-radius:12px;background:#3157d5;color:white;padding:10px 14px;font-weight:700;cursor:pointer}button.active{background:#172033}.content{display:grid;gap:18px}.hero{display:flex;justify-content:space-between;align-items:center}.eyebrow{text-transform:uppercase;letter-spacing:.08em;color:#5970aa;font-size:12px;font-weight:800}form{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}label{display:grid;gap:6px;font-weight:700}input,select{border:1px solid #cbd5ef;border-radius:10px;padding:10px}table{width:100%;border-collapse:collapse}th,td{text-align:left;border-bottom:1px solid #e7ecfb;padding:10px}td button{margin-right:6px;background:#5a6f9f}@media(max-width:850px){.shell{grid-template-columns:1fr}}"


def _makefile() -> str:
    return textwrap.dedent('''
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
        	@echo "  make run-backend      Start FastAPI backend on :8000"
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
        	cd backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

        run-frontend:
        	cd frontend && npm run dev
    ''')


def _readme(pack: DomainPack) -> str:
    return textwrap.dedent(f'''
        # {pack.display_name}

        A generated AgentForge `model_driven_app` built from the App Blueprint `model` block.

        ## Setup

        From the generated app root:

        ```bash
        make install
        ```

        ## Validate

        ```bash
        make validate
        ```

        `make validate` runs backend tests plus frontend build/lint. `make test` currently runs backend tests only because this generated app has no frontend unit test target.

        ## Run locally

        Start the backend and frontend in separate terminals:

        ```bash
        make run-backend
        make run-frontend
        ```

        Open `http://localhost:5173`.

        This app uses local SQLite persistence and deterministic seed data. It does not require live APIs, providers, cloud services, or Docker.
    ''')


def _run_commands(pack: DomainPack) -> str:
    return textwrap.dedent(f'''
        # {pack.display_name} — model-driven generated app commands
        # Run from the generated app root. Assumes an active Python environment plus Node/npm.

        ## Install dependencies
        make install

        ## Validate backend and frontend
        make validate

        ## Backend tests only
        make test

        ## Local development servers, in separate terminals
        make run-backend
        make run-frontend
    ''')
