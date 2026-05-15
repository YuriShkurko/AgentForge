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
                        "semantic": f.semantic,
                    }
                    for f in e.fields
                ],
                "ui": model.ui.entities.get(e.name).model_dump() if e.name in model.ui.entities else {"display": {"layout": "table", "title_field": "", "subtitle_field": "", "badge_field": "", "secondary_field": ""}},
            }
            for e in model.entities
        ],
        "pages": [p.model_dump() for p in model.pages],
        "actions": [a.model_dump() for a in model.actions],
        "seedData": model.seed_data,
        "ui": model.ui.model_dump(),
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
    lines = ["from fastapi.testclient import TestClient", "from app.main import app", "", "client = TestClient(app)", "", "def test_seed_and_list_records():", "    assert client.post('/seed').status_code == 200", f"    response = client.get('/{route}')", "    assert response.status_code == 200", "    assert isinstance(response.json(), list)", "", "def test_seed_is_idempotent():", "    client.post('/seed')", f"    first = len(client.get('/{route}').json())", "    client.post('/seed')", "    client.post('/seed')", f"    second = len(client.get('/{route}').json())", "    assert first == second", "    assert first >= 1", "", "def test_create_record():", f"    response = client.post('/{route}', json={create!r})", "    assert response.status_code == 200", "    assert response.json()['id'] >= 1"]
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
    meta_json = json.dumps(meta, indent=2)
    return f'''import {{ useEffect, useMemo, useState }} from 'react';

type Field = {{ name: string; label: string; type: string; required: boolean; enumValues: string[]; targetEntity: string; semantic?: string }};
type Display = {{ layout: 'table' | 'cards' | 'board_by_status'; title_field?: string; subtitle_field?: string; badge_field?: string; secondary_field?: string }};
type Entity = {{ name: string; className: string; labelSingular: string; labelPlural: string; route: string; fields: Field[]; ui?: {{ display?: Display }} }};
type Action = {{ name: string; label?: string; type: string; entity: string; field?: string | null; value?: string | number | boolean | null }};
type Card = {{ type: 'count' | 'enum_breakdown' | 'attention_list'; entity: string; label?: string; field?: string; value?: string | number | boolean | null }};
type Focus = {{ primary_entity?: string; secondary_entity?: string; group_by?: string; title_field?: string; badge_field?: string; secondary_field?: string }};
type AppModel = {{ app: {{ name: string; displayName: string; description: string }}; entities: Entity[]; actions: Action[]; pages?: unknown[]; seedData?: unknown; ui: {{ composition: 'standard' | 'board_workspace' | 'register_table'; recipe: 'standard' | 'workspace_board' | 'executive_register' | 'ops_console'; style: {{ accent: string; density: string; layout: string }}; focus: Focus; dashboard: {{ title: string; primary_entity?: string; cards: Card[] }}; entities?: unknown }} }};
type Row = Record<string, string | number | boolean | null> & {{ id?: number }};
type RowMap = Record<string, Row[]>;
const model: AppModel = {meta_json};
const API = 'http://localhost:8000';
const findEntity = (name?: string) => model.entities.find((item) => item.name === name) || model.entities[0];
const entityByName = (name?: string) => name ? model.entities.find((item) => item.name === name) : undefined;
const display = (entity: Entity): Display => entity.ui?.display || {{ layout: 'table' }};
const humanize = (raw: unknown) => {{ const text = String(raw ?? '').replace(/_/g, ' ').trim(); return text ? text.charAt(0).toUpperCase() + text.slice(1).toLowerCase() : ''; }};
const titleize = (raw: unknown) => String(raw ?? '').replace(/_/g, ' ').split(/\\s+/).filter(Boolean).map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()).join(' ');
const inferTitleField = (entity: Entity): string => {{ const preferred = entity.fields.find((field) => ['name','title','summary','label'].includes(field.name)); if (preferred) return preferred.name; const stringy = entity.fields.find((field) => field.type === 'string' || field.type === 'text'); return stringy?.name || ''; }};
const relationLabel = (field: Field, raw: Row[string], rowsByEntity: RowMap): string => {{ if (!field.targetEntity) return String(raw ?? ''); const target = entityByName(field.targetEntity); const id = typeof raw === 'number' ? raw : Number(raw); if (!Number.isFinite(id) || id <= 0) return String(raw ?? ''); const record = (rowsByEntity[field.targetEntity] || []).find((row) => row.id === id); if (record && target) {{ const titleField = (target.ui?.display?.title_field) || inferTitleField(target); if (titleField) {{ const label = String(record[titleField] ?? '').trim(); if (label) return label; }} }} const singular = target?.labelSingular || 'Entity'; return `${{singular}} #${{id}}`; }};
const value = (row: Row, field?: string) => field ? String(row[field] ?? '') : '';
const cellValue = (field: Field | undefined, raw: Row[string], rowsByEntity: RowMap): string => {{ if (!field) return String(raw ?? ''); if (field.type === 'relation') return relationLabel(field, raw, rowsByEntity); if (field.type === 'enum') return humanize(raw); if (field.type === 'boolean') return raw ? 'Yes' : 'No'; return String(raw ?? ''); }};
const emptyRow = (entity: Entity) => Object.fromEntries(entity.fields.map((field) => [field.name, field.type === 'boolean' ? false : field.type === 'integer' || field.type === 'relation' ? 0 : field.enumValues[0] || ''])) as Row;
const fieldFor = (entity: Entity, name?: string) => entity.fields.find((field) => field.name === name);
const uniqueById = (rows: Row[]): Row[] => {{ const seen = new Set<number>(); const out: Row[] = []; for (const row of rows) {{ const id = typeof row.id === 'number' ? row.id : Number(row.id); if (!Number.isFinite(id) || seen.has(id)) continue; seen.add(id); out.push(row); }} return out; }};

export default function App() {{
  const primary = findEntity(model.ui.focus.primary_entity || model.ui.dashboard.primary_entity);
  const secondary = model.ui.focus.secondary_entity ? findEntity(model.ui.focus.secondary_entity) : model.entities.find((item) => item.name !== primary.name);
  const [active, setActive] = useState(primary.name);
  const entity = useMemo(() => findEntity(active), [active]);
  const [rowsByEntity, setRowsByEntity] = useState<RowMap>({{}});
  const [form, setForm] = useState<Row>(() => emptyRow(entity));
  const [message, setMessage] = useState('Ready');
  async function load(selected = entity) {{ const response = await fetch(`${{API}}${{selected.route}}`); const data = await response.json(); setRowsByEntity((current) => ({{ ...current, [selected.name]: data }})); }}
  async function loadAll() {{ await Promise.all(model.entities.map((item) => load(item))); }}
  useEffect(() => {{ void loadAll(); }}, []);
  useEffect(() => {{ setForm(emptyRow(entity)); void load(entity); }}, [entity]);
  async function seed() {{ await fetch(`${{API}}/seed`, {{ method: 'POST' }}); setMessage('Seed data loaded'); await loadAll(); }}
  async function save(event: React.FormEvent) {{ event.preventDefault(); const response = await fetch(`${{API}}${{entity.route}}`, {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, body: JSON.stringify(form) }}); if (!response.ok) {{ setMessage('Validation failed'); return; }} setMessage(`${{entity.labelSingular}} saved`); setForm(emptyRow(entity)); await load(entity); }}
  async function runAction(target: Entity, actionName: string, id: number) {{ await fetch(`${{API}}${{target.route}}/${{id}}/actions/${{actionName}}`, {{ method: 'POST' }}); setMessage('Workflow action complete'); await load(target); }}
  const shellClass = `shell composition-${{model.ui.composition}} recipe-${{model.ui.recipe}} accent-${{model.ui.style.accent}} density-${{model.ui.style.density}} layout-${{model.ui.style.layout}}`;
  const isPrimaryActive = entity.name === primary.name;
  const context = {{ rowsByEntity, form, setForm, save, runAction, activeEntity: entity, message, setActive, seed, primary, secondary, isPrimaryActive }};
  return <main className={{shellClass}} data-composition={{model.ui.composition}} data-recipe={{model.ui.recipe}} data-active-entity={{active}} data-primary-active={{isPrimaryActive ? 'true' : 'false'}}>
    <Sidebar active={{active}} setActive={{setActive}} seed={{seed}} />
    {{model.ui.composition === 'standard' ? <StandardLayout {{...context}} /> : isPrimaryActive && model.ui.composition === 'board_workspace' ? <BoardWorkspace {{...context}} /> : isPrimaryActive && model.ui.composition === 'register_table' ? <RegisterTable {{...context}} /> : <FocusedSurface {{...context}} />}}
  </main>;
}}

function Sidebar({{ active, setActive, seed }}: {{ active: string; setActive: (name: string) => void; seed: () => void }}) {{ return <aside><p className="eyebrow">AgentForge model-driven app</p><h1>{pack.display_name}</h1><p>{pack.domain.product_purpose}</p><button onClick={{seed}}>Load seed data</button>{{model.entities.map((item) => <button className={{item.name === active ? 'active' : ''}} key={{item.name}} onClick={{() => setActive(item.name)}}>{{item.labelPlural}}</button>)}}</aside>; }}

type LayoutContext = {{ rowsByEntity: RowMap; form: Row; setForm: (row: Row) => void; save: (event: React.FormEvent) => void; runAction: (target: Entity, actionName: string, id: number) => void; activeEntity: Entity; message: string; setActive: (name: string) => void; seed: () => void; primary: Entity; secondary?: Entity; isPrimaryActive: boolean }};

function BoardWorkspace(ctx: LayoutContext) {{ const primaryRows = ctx.rowsByEntity[ctx.primary.name] || []; const secondaryRows = ctx.secondary ? uniqueById(ctx.rowsByEntity[ctx.secondary.name] || []) : []; const actions = model.actions.filter((action) => action.entity === ctx.primary.name); return <section className="content board-workspace" data-ui-layout="composition-board-workspace"><div className="workspace-header"><div><p className="eyebrow">{{model.ui.dashboard.title}}</p><h2>{{titleize(`${{ctx.primary.labelPlural}} Board`)}}</h2><p>{{ctx.message}}</p></div><Dashboard rowsByEntity={{ctx.rowsByEntity}} compact /></div><div className="workspace-main"><section className="workspace-board"><EntityRows entity={{ctx.primary}} rows={{primaryRows}} rowsByEntity={{ctx.rowsByEntity}} actions={{actions}} onAction={{ctx.runAction}} forcedLayout="board_by_status" groupBy={{model.ui.focus.group_by}} /><section className="compact-create"><CreateForm entity={{ctx.activeEntity}} form={{ctx.form}} setForm={{ctx.setForm}} save={{ctx.save}} rowsByEntity={{ctx.rowsByEntity}} /></section></section>{{ctx.secondary && <aside className="secondary-panel" data-ui-surface="secondary-related"><h3>{{ctx.secondary.labelPlural}}</h3><EntityRows entity={{ctx.secondary}} rows={{secondaryRows}} rowsByEntity={{ctx.rowsByEntity}} actions={{[]}} onAction={{ctx.runAction}} forcedLayout="cards" /></aside>}}</div></section>; }}

function RegisterTable(ctx: LayoutContext) {{ const primaryRows = ctx.rowsByEntity[ctx.primary.name] || []; const secondaryRows = ctx.secondary ? uniqueById(ctx.rowsByEntity[ctx.secondary.name] || []) : []; const actions = model.actions.filter((action) => action.entity === ctx.primary.name); return <section className="content register-table" data-ui-layout="composition-register-table"><div className="register-top"><div className="register-title"><p className="eyebrow">{{model.ui.dashboard.title}}</p><h2>{{titleize(`${{ctx.primary.labelPlural}} Register`)}}</h2><p>{{ctx.message}}</p></div><Dashboard rowsByEntity={{ctx.rowsByEntity}} compact /></div><div className="register-main"><section className="register-focus"><EntityRows entity={{ctx.primary}} rows={{primaryRows}} rowsByEntity={{ctx.rowsByEntity}} actions={{actions}} onAction={{ctx.runAction}} forcedLayout="table" register /><section className="compact-create"><CreateForm entity={{ctx.activeEntity}} form={{ctx.form}} setForm={{ctx.setForm}} save={{ctx.save}} rowsByEntity={{ctx.rowsByEntity}} /></section></section><aside className="register-side" data-ui-surface="secondary-related">{{ctx.secondary && <><h3>{{ctx.secondary.labelPlural}}</h3><EntityRows entity={{ctx.secondary}} rows={{secondaryRows}} rowsByEntity={{ctx.rowsByEntity}} actions={{[]}} onAction={{ctx.runAction}} forcedLayout="cards" /></>}}</aside></div></section>; }}

function FocusedSurface(ctx: LayoutContext) {{ const entity = ctx.activeEntity; const rows = ctx.rowsByEntity[entity.name] || []; const actions = model.actions.filter((action) => action.entity === entity.name); return <section className="content focused-surface" data-ui-layout="composition-focused" data-focused-entity={{entity.name}}><section className="hero"><div><p className="eyebrow">{{model.ui.dashboard.title}}</p><h2>{{titleize(entity.labelPlural)}}</h2><p>{{ctx.message}}</p></div><strong>{{rows.length}} {{rows.length === 1 ? entity.labelSingular : entity.labelPlural}}</strong></section><div className="focused-main"><section className="focused-list"><EntityRows entity={{entity}} rows={{rows}} rowsByEntity={{ctx.rowsByEntity}} actions={{actions}} onAction={{ctx.runAction}} /></section><aside className="focused-create"><CreateForm entity={{entity}} form={{ctx.form}} setForm={{ctx.setForm}} save={{ctx.save}} rowsByEntity={{ctx.rowsByEntity}} compact /></aside></div></section>; }}

function StandardLayout(ctx: LayoutContext) {{ const rows = ctx.rowsByEntity[ctx.activeEntity.name] || []; const actions = model.actions.filter((action) => action.entity === ctx.activeEntity.name); return <section className="content"><section className="hero"><div><p className="eyebrow">{{model.ui.dashboard.title}}</p><h2>{{titleize(ctx.activeEntity.labelPlural)}}</h2><p>{{ctx.message}}</p></div><strong>{{rows.length}} records</strong></section><Dashboard rowsByEntity={{ctx.rowsByEntity}} /><CreateForm entity={{ctx.activeEntity}} form={{ctx.form}} setForm={{ctx.setForm}} save={{ctx.save}} rowsByEntity={{ctx.rowsByEntity}} /><EntityRows entity={{ctx.activeEntity}} rows={{rows}} rowsByEntity={{ctx.rowsByEntity}} actions={{actions}} onAction={{ctx.runAction}} /></section>; }}

function CreateForm({{ entity, form, setForm, save, rowsByEntity, compact = false }}: {{ entity: Entity; form: Row; setForm: (row: Row) => void; save: (event: React.FormEvent) => void; rowsByEntity: RowMap; compact?: boolean }}) {{ return <form onSubmit={{save}} className={{compact ? 'card form-card compact-form' : 'card form-card'}}><h3>Create {{entity.labelSingular}}</h3>{{entity.fields.map((field) => {{ const targetMeta = field.type === 'relation' ? entityByName(field.targetEntity) : undefined; const targetRows = field.type === 'relation' ? (rowsByEntity[field.targetEntity] || []) : []; const targetLabel = targetMeta?.labelSingular || 'record'; return <label key={{field.name}}>{{field.label}}{{field.type === 'enum' ? <select value={{String(form[field.name] ?? '')}} onChange={{(event) => setForm({{...form, [field.name]: event.target.value}})}}>{{field.enumValues.map((option) => <option key={{option}} value={{option}}>{{humanize(option)}}</option>)}}</select> : field.type === 'boolean' ? <input type="checkbox" checked={{Boolean(form[field.name])}} onChange={{(event) => setForm({{...form, [field.name]: event.target.checked}})}} /> : field.type === 'relation' ? (targetRows.length === 0 ? <select data-ui-control="relation-select" disabled value=""><option value="">{{`Load seed data or create a ${{targetLabel}} first`}}</option></select> : <select data-ui-control="relation-select" value={{String(form[field.name] ?? '')}} onChange={{(event) => setForm({{...form, [field.name]: Number(event.target.value)}})}}><option value="">{{`Select a ${{targetLabel}}`}}</option>{{targetRows.map((option) => <option key={{option.id}} value={{option.id}}>{{relationLabel(field, option.id ?? 0, rowsByEntity)}}</option>)}}</select>) : <input type={{field.type === 'date' ? 'date' : field.type === 'integer' ? 'number' : 'text'}} value={{String(form[field.name] ?? '')}} onChange={{(event) => setForm({{...form, [field.name]: field.type === 'integer' ? Number(event.target.value) : event.target.value}})}} />}}</label>; }})}}<button type="submit">Save {{entity.labelSingular}}</button></form>; }}

function Dashboard({{ rowsByEntity, compact = false }}: {{ rowsByEntity: RowMap; compact?: boolean }}) {{ return <section className={{compact ? 'dashboard-grid compact-dashboard' : 'dashboard-grid'}} data-ui-layout="dashboard-cards">{{model.ui.dashboard.cards.map((card) => {{ const target = model.entities.find((item) => item.name === card.entity); const cardRows = rowsByEntity[card.entity] || []; if (!target) return null; if (card.type === 'count') return <article className="stat-card" key={{card.label}}><p>{{card.label || target.labelPlural}}</p><strong>{{cardRows.length}}</strong></article>; if (card.type === 'attention_list') {{ const hits = cardRows.filter((row) => String(row[card.field || '']) === String(card.value)); const titleFieldName = display(target).title_field || model.ui.focus.title_field; const titleFieldDef = fieldFor(target, titleFieldName); return <article className="stat-card attention" key={{card.label}}><p>{{card.label}}</p><strong>{{hits.length}}</strong>{{hits.slice(0, 3).map((row) => <small key={{row.id}}>{{cellValue(titleFieldDef, row[titleFieldName || ''], rowsByEntity) || `#${{row.id}}`}}</small>)}}</article>; }} const field = fieldFor(target, card.field); return <article className="stat-card breakdown" key={{card.label}}><p>{{card.label}}</p>{{(field?.enumValues || []).map((option) => <span key={{option}}><b>{{humanize(option)}}</b><em>{{cardRows.filter((row) => row[field?.name || ''] === option).length}}</em></span>)}}</article>; }})}}</section>; }}

function EntityRows({{ entity, rows, rowsByEntity, actions, onAction, forcedLayout, groupBy, register = false }}: {{ entity: Entity; rows: Row[]; rowsByEntity: RowMap; actions: Action[]; onAction: (target: Entity, name: string, id: number) => void; forcedLayout?: Display['layout']; groupBy?: string; register?: boolean }}) {{ const view = display(entity); const layout = forcedLayout || view.layout; if (layout === 'cards') return <div className="entity-grid" data-ui-layout="cards">{{rows.length === 0 ? <EmptyState text="No related records yet." /> : rows.map((row) => <RecordCard key={{row.id}} entity={{entity}} row={{row}} rowsByEntity={{rowsByEntity}} actions={{actions}} onAction={{onAction}} />)}}</div>; if (layout === 'board_by_status') {{ const status = fieldFor(entity, groupBy || view.badge_field) || entity.fields.find((item) => item.type === 'enum'); return <div className="board-scroll" data-ui-layout="board_by_status"><div className="board">{{(status?.enumValues || ['records']).map((lane) => {{ const laneRows = rows.filter((row) => !status || String(row[status.name]) === lane); return <section className="lane" key={{lane}}><h3>{{humanize(lane)}}</h3>{{laneRows.length === 0 ? <EmptyState text="No items yet." compact /> : laneRows.map((row) => <RecordCard key={{row.id}} entity={{entity}} row={{row}} rowsByEntity={{rowsByEntity}} actions={{actions}} onAction={{onAction}} />)}}</section>; }})}}</div></div>; }} const badge = model.ui.focus.badge_field || view.badge_field; return <div className={{register ? 'card register-card' : 'card'}} data-ui-layout={{register ? 'register_table' : 'table'}}><h3>{{entity.labelPlural}}</h3><div className="table-scroll"><table><thead><tr><th>ID</th>{{entity.fields.map((field) => <th key={{field.name}}>{{field.label}}</th>)}}<th>Actions</th></tr></thead><tbody>{{rows.length === 0 ? <tr><td colSpan={{entity.fields.length + 2}}><EmptyState text="No records yet — load seed data or create one." /></td></tr> : rows.map((row) => <tr key={{row.id}}><td>{{row.id}}</td>{{entity.fields.map((field) => <td key={{field.name}}>{{field.name === badge ? <span className={{`badge badge-${{String(row[field.name] ?? '').toLowerCase().replace(/[^a-z0-9]+/g, '-')}}`}}>{{cellValue(field, row[field.name], rowsByEntity)}}</span> : cellValue(field, row[field.name], rowsByEntity)}}</td>)}}<td>{{actions.map((action) => <button key={{action.name}} onClick={{() => row.id && onAction(entity, action.name, row.id)}}>{{action.label || humanize(action.name)}}</button>)}}</td></tr>)}}</tbody></table></div></div>; }}

function EmptyState({{ text, compact = false }}: {{ text: string; compact?: boolean }}) {{ return <div className={{compact ? 'empty-state compact-empty' : 'empty-state'}} data-ui-state="empty">{{text}}</div>; }}

function RecordCard({{ entity, row, rowsByEntity, actions, onAction }}: {{ entity: Entity; row: Row; rowsByEntity: RowMap; actions: Action[]; onAction: (target: Entity, name: string, id: number) => void }}) {{ const view = display(entity); const titleField = view.title_field || (entity.name === model.ui.focus.primary_entity ? model.ui.focus.title_field : '') || ''; const badgeField = view.badge_field || (entity.name === model.ui.focus.primary_entity ? model.ui.focus.badge_field : '') || ''; const secondaryField = view.secondary_field || (entity.name === model.ui.focus.primary_entity ? model.ui.focus.secondary_field : '') || ''; const titleFieldDef = fieldFor(entity, titleField); const subtitleFieldDef = fieldFor(entity, view.subtitle_field); const secondaryFieldDef = fieldFor(entity, secondaryField); const badgeFieldDef = fieldFor(entity, badgeField); const badge = value(row, badgeField); const titleText = cellValue(titleFieldDef, row[titleField], rowsByEntity); return <article className="record-card"><div>{{badge && <span className={{`badge badge-${{badge.toLowerCase().replace(/[^a-z0-9]+/g, '-')}}`}}>{{badgeFieldDef ? cellValue(badgeFieldDef, row[badgeField], rowsByEntity) : humanize(badge)}}</span>}}<h3>{{titleText || `${{entity.labelSingular}} #${{row.id}}`}}</h3><p>{{cellValue(subtitleFieldDef, row[view.subtitle_field || ''], rowsByEntity)}}</p><small>{{cellValue(secondaryFieldDef, row[secondaryField], rowsByEntity)}}</small></div><div>{{actions.map((action) => <button key={{action.name}} onClick={{() => row.id && onAction(entity, action.name, row.id)}}>{{action.label || humanize(action.name)}}</button>)}}</div></article>; }}
'''


def _frontend_styles() -> str:
    return "body{margin:0;font-family:Inter,system-ui,sans-serif;background:#f4f7fb;color:#172033}.shell{--accent:#3157d5;display:grid;grid-template-columns:240px minmax(0,1fr);gap:18px;padding:22px;max-width:1440px;margin:0 auto;box-sizing:border-box}.accent-emerald{--accent:#059669}.accent-blue{--accent:#2563eb}.accent-amber{--accent:#d97706}.accent-red{--accent:#dc2626}.accent-slate{--accent:#475569}.accent-violet{--accent:#7c3aed}.density-compact{gap:12px;padding:16px}.density-spacious{gap:26px;padding:30px}aside,.card,.hero,.stat-card,.record-card,.lane,.secondary-panel,.register-side,.workspace-header,.register-title{background:white;border:1px solid #dbe3f8;border-radius:16px;padding:16px;box-shadow:0 12px 30px #1f2a4420;min-width:0}aside{height:fit-content;display:grid;gap:12px;border-top:5px solid var(--accent)}button{border:0;border-radius:12px;background:var(--accent);color:white;padding:10px 14px;font-weight:700;cursor:pointer}button.active{background:#172033}.content{display:grid;gap:18px}.hero,.workspace-header,.register-top{display:flex;justify-content:space-between;align-items:stretch;gap:18px}.workspace-header{background:linear-gradient(135deg,#fff,#ecfdf5)}.register-title{background:linear-gradient(135deg,#fff,#fffbeb);min-width:260px}.eyebrow{text-transform:uppercase;letter-spacing:.08em;color:var(--accent);font-size:12px;font-weight:800}.dashboard-grid,.entity-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}.compact-dashboard{grid-template-columns:repeat(auto-fit,minmax(150px,1fr));flex:1;min-width:0}.stat-card strong{display:block;font-size:34px;color:var(--accent)}.breakdown span{display:flex;justify-content:space-between;border-top:1px solid #edf1fb;padding:8px 0}.attention small{display:block;margin-top:8px}.form-card{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}.compact-form{grid-template-columns:1fr}label{display:grid;gap:6px;font-weight:700;min-width:0}input,select{border:1px solid #cbd5ef;border-radius:10px;padding:9px;max-width:100%;box-sizing:border-box}.table-scroll{overflow-x:auto;max-width:100%}table{width:100%;border-collapse:collapse;table-layout:auto}th,td{text-align:left;border-bottom:1px solid #e7ecfb;padding:9px;vertical-align:top;word-break:break-word}td{max-width:260px}td button{margin-right:6px;background:#5a6f9f}.board-scroll{overflow-x:auto;max-width:100%}.board{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(220px,1fr);gap:12px;align-items:start;min-width:100%}.lane{background:#f8fafc;min-height:240px;min-width:0}.record-card{display:grid;gap:12px;border-left:5px solid var(--accent);margin-bottom:10px}.badge{display:inline-block;border-radius:999px;background:color-mix(in srgb,var(--accent) 14%,white);color:var(--accent);font-weight:800;padding:4px 9px}small{color:#64748b}.workspace-main{display:grid;grid-template-columns:minmax(0,1fr) clamp(240px,26vw,300px);gap:14px;align-items:start;min-width:0}.workspace-board{min-width:0;display:grid;gap:12px}.secondary-panel{min-width:0}.secondary-panel .entity-grid{grid-template-columns:1fr}.compact-create{max-width:100%;min-width:0}.compact-create .form-card{grid-template-columns:repeat(auto-fit,minmax(180px,1fr))}.register-top{align-items:stretch;flex-wrap:wrap}.register-main{display:grid;grid-template-columns:minmax(0,1fr) clamp(260px,28vw,320px);gap:14px;align-items:start;min-width:0}.register-focus{min-width:0}.register-card{border-top:5px solid var(--accent);overflow:hidden;min-width:0}.register-card .table-scroll{max-width:100%;overflow-x:auto}.register-card table{font-size:14px;min-width:520px}.register-card th{background:#f8fafc;position:sticky;top:0}.register-side{display:grid;gap:12px;min-width:0}.register-side .entity-grid{grid-template-columns:1fr}.register-side .form-card{grid-template-columns:1fr}.composition-register_table aside{border-top-color:var(--accent)}.secondary-panel,.register-side{max-height:calc(100vh - 180px);overflow-y:auto;scrollbar-gutter:stable}.secondary-panel .entity-grid,.register-side .entity-grid{grid-template-columns:1fr;gap:10px}.focused-surface{display:grid;gap:14px}.focused-main{display:grid;grid-template-columns:minmax(0,1fr) clamp(260px,28vw,320px);gap:14px;align-items:start;min-width:0}.focused-list,.focused-create{min-width:0}.focused-create .form-card{grid-template-columns:1fr}.focused-create h3{margin-top:0}@media(max-width:1180px){.focused-main{grid-template-columns:1fr}}.empty-state{border:1px dashed #cbd5e1;border-radius:14px;color:#64748b;background:#f8fafc;padding:18px;text-align:center;font-weight:700}.compact-empty{padding:12px;font-size:13px}.recipe-workspace_board{background:linear-gradient(135deg,#ecfdf5,#f8fafc)}.recipe-workspace_board aside{background:#ffffffcc;box-shadow:none;border-color:#bbf7d0}.recipe-workspace_board .lane{background:#f0fdf4;border-color:#bbf7d0;box-shadow:0 8px 18px #16653414}.recipe-workspace_board .record-card{border-radius:16px;box-shadow:0 8px 18px #16653412}.recipe-workspace_board .compact-create .form-card{box-shadow:none;background:#ffffffb8}.recipe-executive_register{background:#0f172a;color:#172033}.recipe-executive_register aside,.recipe-executive_register .register-side{background:#111827;color:#e5e7eb;border-color:#334155;box-shadow:none}.recipe-executive_register aside p,.recipe-executive_register aside h1{color:#e5e7eb}.recipe-executive_register .register-title,.recipe-executive_register .stat-card{border-radius:10px;box-shadow:none}.recipe-executive_register .register-card{border-radius:10px;box-shadow:none}.recipe-executive_register th,.recipe-executive_register td{padding:8px}.recipe-executive_register .badge{border-radius:6px;text-transform:uppercase;font-size:11px;letter-spacing:.06em}.recipe-executive_register .register-side h3{color:#f1f5f9;letter-spacing:.04em}.recipe-executive_register .register-side .record-card{background:#1f2937;color:#f1f5f9;border:1px solid #475569;border-left:5px solid var(--accent);box-shadow:none}.recipe-executive_register .register-side .record-card h3{color:#f8fafc;margin:0}.recipe-executive_register .register-side .record-card p{color:#cbd5e1;margin:0}.recipe-executive_register .register-side .record-card small{color:#94a3b8}.recipe-executive_register .register-side .record-card .badge{background:color-mix(in srgb,var(--accent) 32%,#0f172a);color:#fef3c7;border:1px solid color-mix(in srgb,var(--accent) 55%,#0f172a)}.recipe-executive_register .register-side .empty-state{background:#111827;color:#cbd5e1;border-color:#475569}.recipe-executive_register .register-side .form-card{background:#1f2937;color:#f1f5f9;border-color:#475569}.recipe-executive_register .register-side .form-card h3,.recipe-executive_register .register-side .form-card label{color:#f1f5f9}.recipe-executive_register .register-side .form-card input,.recipe-executive_register .register-side .form-card select{background:#0f172a;color:#f1f5f9;border-color:#475569}.badge-high,.badge-critical,.badge-blocked{background:#fee2e2;color:#b91c1c}.badge-medium,.badge-investigating,.badge-in-progress{background:#fef3c7;color:#92400e}.badge-low,.badge-open,.badge-todo{background:#dbeafe;color:#1d4ed8}.badge-done,.badge-mitigated,.badge-accepted{background:#dcfce7;color:#166534}@media(max-width:1280px){.workspace-main,.register-main{grid-template-columns:minmax(0,1fr)}.workspace-header,.register-top{display:grid}.compact-dashboard{grid-template-columns:repeat(auto-fit,minmax(150px,1fr))}.shell{padding:18px;gap:14px}}@media(max-width:980px){.shell{grid-template-columns:1fr}aside{position:static;border-top-width:3px}}@media(max-width:720px){.dashboard-grid,.entity-grid{grid-template-columns:1fr}.compact-dashboard{grid-template-columns:1fr}.form-card{grid-template-columns:1fr}}"


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
        # {pack.display_name} â€” model-driven generated app commands
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
