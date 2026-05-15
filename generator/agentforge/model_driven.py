"""Bounded model-driven FastAPI/React app generation."""
from __future__ import annotations

import json
import pprint
import textwrap
from pathlib import Path
from typing import Any

from agentforge.pack import DomainPack, ModelDrivenApp, ModelField, ModelImport


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
    files = {
        "backend/app/__init__.py": "",
        "backend/app/database.py": _backend_database(),
        "backend/app/models.py": _backend_models(model),
        "backend/app/schemas.py": _backend_schemas(model),
        "backend/app/imports.py": _backend_imports_module(model),
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
    if model.providers:
        files["backend/app/providers.py"] = _backend_providers_module(model)
        files[".env.example"] = _env_example(model)
    return files


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
        "imports": [
            {
                "id": spec.id,
                "label": spec.label or f"Import {spec.entity.replace('_', ' ')}",
                "entity": spec.entity,
                "formats": spec.formats,
                "upsertKey": spec.upsert_key,
                "fieldMap": spec.field_map,
            }
            for spec in model.imports
        ],
        "providers": [
            {
                "id": provider.id,
                "label": provider.label or provider.id.replace("_", " ").title(),
                "type": provider.type,
                "mode": provider.mode,
                "targetImport": provider.target_import,
                "env": provider.env.model_dump(),
                "source": provider.source.model_dump(),
            }
            for provider in model.providers
        ],
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
    chunks.append(_import_run_model())
    return "\n\n".join(chunks)


def _import_run_model() -> str:
    return textwrap.dedent('''
        class ImportRun(Base):
            __tablename__ = "import_runs"

            id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
            import_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
            entity: Mapped[str] = mapped_column(String(120), nullable=False)
            format: Mapped[str] = mapped_column(String(16), nullable=False)
            status: Mapped[str] = mapped_column(String(32), nullable=False)
            total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
            created_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
            updated_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
            skipped_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
            error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
            error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ''').strip()


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
    chunks.append("class ImportPayload(BaseModel):\n    format: str\n    data: str")
    return "\n\n".join(chunks)


def _field_descriptor(field: ModelField) -> dict[str, Any]:
    return {
        "name": field.name,
        "type": field.type,
        "required": field.required,
        "enum_values": list(field.enum_values),
        "target_entity": field.target_entity,
    }


def _backend_imports_module(model: ModelDrivenApp) -> str:
    entity_fields = {entity.name: [_field_descriptor(f) for f in entity.fields] for entity in model.entities}
    entity_classes = {entity.name: _class_name(entity.name) for entity in model.entities}
    entity_meta = {
        entity.name: {
            "label_singular": entity.label_singular,
            "label_plural": entity.label_plural,
            "display_title_field": (model.ui.entities.get(entity.name).display.title_field if entity.name in model.ui.entities else ""),
        }
        for entity in model.entities
    }
    imports_payload = [
        {
            "id": spec.id,
            "label": spec.label or f"Import {spec.entity.replace('_', ' ')}",
            "entity": spec.entity,
            "formats": list(spec.formats),
            "upsert_key": spec.upsert_key,
            "field_map": dict(spec.field_map),
        }
        for spec in model.imports
    ]

    header = textwrap.dedent('''
        """Generic importer pipeline (model-driven app).

        CSV and JSON are thin input adapters that produce the same list[dict] shape.
        After parsing, mapping/validation/upsert/run-history logic is shared.
        """
        from __future__ import annotations

        import csv
        import io
        import json
        from datetime import date
        from typing import Any, Iterable

        from sqlalchemy.orm import Session

        from app import models
    ''').strip()

    imports_literal = f"IMPORTS: list[dict[str, Any]] = {pprint.pformat(imports_payload, indent=4, width=100, sort_dicts=False)}"
    fields_literal = f"ENTITY_FIELDS: dict[str, list[dict[str, Any]]] = {pprint.pformat(entity_fields, indent=4, width=100, sort_dicts=False)}"
    meta_literal = f"ENTITY_META: dict[str, dict[str, Any]] = {pprint.pformat(entity_meta, indent=4, width=100, sort_dicts=False)}"
    classes_lines = ["ENTITY_MODELS = {"]
    for name, cls in entity_classes.items():
        classes_lines.append(f"    {name!r}: models.{cls},")
    classes_lines.append("}")
    classes_literal = "\n".join(classes_lines)

    body = textwrap.dedent('''
        def get_import(import_id: str) -> dict | None:
            for spec in IMPORTS:
                if spec["id"] == import_id:
                    return spec
            return None


        def _normalize_key(text: str) -> str:
            return "".join(ch if ch.isalnum() else "_" for ch in str(text).strip().lower()).strip("_")


        def parse_csv(text: str) -> list[dict[str, Any]]:
            reader = csv.DictReader(io.StringIO(text or ""))
            rows: list[dict[str, Any]] = []
            for row in reader:
                cleaned: dict[str, Any] = {}
                for key, value in row.items():
                    if key is None:
                        continue
                    header = key.strip()
                    if not header:
                        continue
                    cleaned[header] = value if value is not None else ""
                rows.append(cleaned)
            return rows


        def parse_json(text: str) -> list[dict[str, Any]]:
            try:
                payload = json.loads(text or "")
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON: {exc.msg}") from exc
            if isinstance(payload, list):
                records = payload
            elif isinstance(payload, dict):
                records = None
                for key in ("records", "items", "data"):
                    candidate = payload.get(key)
                    if isinstance(candidate, list):
                        records = candidate
                        break
                if records is None:
                    raise ValueError("JSON object must include a 'records', 'items', or 'data' array")
            else:
                raise ValueError("JSON payload must be a list of objects or an object with records/items/data")
            out: list[dict[str, Any]] = []
            for record in records:
                if not isinstance(record, dict):
                    raise ValueError("JSON records must be objects")
                out.append(dict(record))
            return out


        def _relation_aliases(field: dict) -> set[str]:
            aliases = {field["name"], field.get("label") or ""}
            if field["name"].endswith("_id"):
                aliases.add(field["name"][:-3])
            target = ENTITY_META.get(field.get("target_entity") or "", {})
            aliases.add(target.get("label_singular") or "")
            aliases.add(target.get("label_plural") or "")
            return {_normalize_key(alias) for alias in aliases if str(alias).strip()}


        def _build_mapping(spec: dict, source_keys: Iterable[str]) -> dict[str, str]:
            fields = ENTITY_FIELDS[spec["entity"]]
            field_names = {field["name"] for field in fields}
            relation_aliases = {
                alias: field["name"]
                for field in fields
                if field["type"] == "relation"
                for alias in _relation_aliases(field)
            }
            mapping: dict[str, str] = {}
            for key in source_keys:
                normalized = _normalize_key(key)
                if normalized in field_names:
                    mapping[key] = normalized
                elif normalized in relation_aliases:
                    mapping[key] = relation_aliases[normalized]
            for source, target in (spec.get("field_map") or {}).items():
                if target in field_names:
                    mapping[source] = target
            return mapping


        def _relation_display_field(entity_name: str) -> str:
            meta = ENTITY_META.get(entity_name, {})
            explicit = meta.get("display_title_field") or ""
            fields = ENTITY_FIELDS.get(entity_name, [])
            names = {field["name"] for field in fields}
            if explicit and explicit in names:
                return explicit
            for preferred in ("name", "title", "label", "summary"):
                if preferred in names:
                    return preferred
            for field in fields:
                if field["type"] in ("string", "text"):
                    return field["name"]
            return "id"


        def _relation_source_name(field: dict) -> str:
            if field["name"].endswith("_id"):
                return field["name"][:-3]
            return _normalize_key(field.get("label") or field["name"]) or field["name"]


        def _resolve_relation(field: dict, raw: Any, db: Session) -> tuple[int | None, str | None, dict[str, Any] | None]:
            text = str(raw).strip()
            source_name = _relation_source_name(field)
            target_entity = field.get("target_entity") or ""
            target_label = ENTITY_META.get(target_entity, {}).get("label_singular") or target_entity.replace("_", " " ).title()
            Model = ENTITY_MODELS.get(target_entity)
            if Model is None:
                return None, f"{source_name} targets unknown entity {target_entity}", None
            try:
                matched_id = int(text)
                return matched_id, None, {"field": field["name"], "source_field": source_name, "target_entity": target_entity, "matched_id": matched_id, "matched_by": "id"}
            except (ValueError, TypeError):
                pass
            display_field = _relation_display_field(target_entity)
            if display_field == "id":
                return None, f"{source_name} '{text}' must be an existing {target_label} id", None
            matches = db.query(Model).filter(getattr(Model, display_field) == text).limit(2).all()
            if not matches:
                return None, f"{source_name} '{text}' did not match any {target_label} record", None
            if len(matches) > 1:
                return None, f"{source_name} '{text}' matched multiple {target_label} records", None
            matched_id = matches[0].id
            return matched_id, None, {"field": field["name"], "source_field": source_name, "target_entity": target_entity, "target_label": target_label, "display_field": display_field, "source_value": text, "matched_id": matched_id, "matched_by": "label"}


        def _coerce(field: dict, raw: Any, db: Session) -> tuple[Any, str | None, dict[str, Any] | None]:
            if raw is None or (isinstance(raw, str) and raw.strip() == ""):
                if field.get("required"):
                    return None, f"{field['name']} is required", None
                return None, None, None
            kind = field["type"]
            if kind in ("string", "text"):
                return str(raw), None, None
            if kind == "integer":
                try:
                    return int(str(raw).strip()), None, None
                except (ValueError, TypeError):
                    return None, f"{field['name']} must be an integer", None
            if kind == "boolean":
                if isinstance(raw, bool):
                    return raw, None, None
                text = str(raw).strip().lower()
                if text in ("true", "1", "yes", "y"):
                    return True, None, None
                if text in ("false", "0", "no", "n"):
                    return False, None, None
                return None, f"{field['name']} must be a boolean (true/false)", None
            if kind == "date":
                try:
                    return date.fromisoformat(str(raw).strip()), None, None
                except (ValueError, TypeError):
                    return None, f"{field['name']} must be an ISO date (YYYY-MM-DD)", None
            if kind == "enum":
                text = str(raw).strip()
                if text not in field["enum_values"]:
                    return None, f"{field['name']} must be one of {', '.join(field['enum_values'])}", None
                return text, None, None
            if kind == "relation":
                return _resolve_relation(field, raw, db)
            return raw, None, None


        def _map_and_validate(spec: dict, raw_rows: list[dict[str, Any]], db: Session) -> tuple[list[dict[str, Any] | None], list[dict[str, Any]], dict[str, str], list[dict[str, Any]]]:
            fields = ENTITY_FIELDS[spec["entity"]]
            fields_by_name = {field["name"]: field for field in fields}
            source_keys: list[str] = []
            seen: set[str] = set()
            for row in raw_rows:
                for key in row.keys():
                    if key not in seen:
                        seen.add(key)
                        source_keys.append(key)
            mapping = _build_mapping(spec, source_keys)
            cleaned: list[dict[str, Any] | None] = []
            errors: list[dict[str, Any]] = []
            relation_resolutions: list[dict[str, Any]] = []
            for index, row in enumerate(raw_rows):
                mapped: dict[str, Any] = {}
                row_errors: list[str] = []
                for source, target in mapping.items():
                    if source in row:
                        value, err, info = _coerce(fields_by_name[target], row[source], db)
                        if err:
                            row_errors.append(err)
                        elif value is not None:
                            mapped[target] = value
                            if info:
                                relation_resolutions.append({"row": index + 1, "source_column": source, **info})
                for field in fields:
                    if field.get("required") and field["name"] not in mapped:
                        message = f"{field['name']} is required"
                        if message not in row_errors:
                            row_errors.append(message)
                if row_errors:
                    cleaned.append(None)
                    errors.append({"row": index + 1, "errors": row_errors})
                else:
                    cleaned.append(mapped)
            return cleaned, errors, mapping, relation_resolutions


        def preview_records(spec: dict, raw_rows: list[dict[str, Any]], db: Session, fmt: str = "records") -> dict:
            cleaned, errors, mapping, relation_resolutions = _map_and_validate(spec, raw_rows, db)
            valid_rows = [row for row in cleaned if row is not None]
            upsert_key = spec.get("upsert_key") or ""
            would_create = 0
            would_update = 0
            if upsert_key:
                Model = ENTITY_MODELS[spec["entity"]]
                for row in valid_rows:
                    key_value = row.get(upsert_key)
                    if key_value is None:
                        would_create += 1
                        continue
                    existing = db.query(Model).filter(getattr(Model, upsert_key) == key_value).one_or_none()
                    if existing is None:
                        would_create += 1
                    else:
                        would_update += 1
            else:
                would_create = len(valid_rows)
            return {
                "import_id": spec["id"],
                "entity": spec["entity"],
                "format": fmt,
                "total_rows": len(raw_rows),
                "valid_rows": len(valid_rows),
                "invalid_rows": len(errors),
                "errors": errors,
                "mapped_fields": sorted({target for target in mapping.values()}),
                "would_create": would_create,
                "would_update": would_update,
                "relation_resolutions": relation_resolutions,
            }


        def preview(spec: dict, fmt: str, data: str, db: Session) -> dict:
            raw_rows = parse_csv(data) if fmt == "csv" else parse_json(data)
            return preview_records(spec, raw_rows, db, fmt)


        def commit_records(spec: dict, raw_rows: list[dict[str, Any]], db: Session, fmt: str = "records") -> dict:
            cleaned, errors, _, _relation_resolutions = _map_and_validate(spec, raw_rows, db)
            invalid_count = len(errors)
            created_count = 0
            updated_count = 0
            skipped_count = 0
            if invalid_count == 0:
                Model = ENTITY_MODELS[spec["entity"]]
                upsert_key = spec.get("upsert_key") or ""
                for row in cleaned:
                    if row is None:
                        continue
                    if upsert_key and row.get(upsert_key) is not None:
                        existing = db.query(Model).filter(getattr(Model, upsert_key) == row[upsert_key]).one_or_none()
                        if existing is None:
                            db.add(Model(**row))
                            created_count += 1
                        else:
                            for key, value in row.items():
                                setattr(existing, key, value)
                            updated_count += 1
                    else:
                        db.add(Model(**row))
                        created_count += 1
                db.commit()
                status = "ok"
            else:
                status = "rejected"
                skipped_count = len(raw_rows)
            summary = "; ".join(f"row {entry['row']}: {', '.join(entry['errors'])}" for entry in errors[:5])
            run = models.ImportRun(
                import_id=spec["id"],
                entity=spec["entity"],
                format=fmt,
                status=status,
                total_rows=len(raw_rows),
                created_count=created_count,
                updated_count=updated_count,
                skipped_count=skipped_count,
                error_count=invalid_count,
                error_summary=(summary[:512] if summary else None),
            )
            db.add(run)
            db.commit()
            db.refresh(run)
            return {
                "import_id": spec["id"],
                "status": status,
                "total_rows": len(raw_rows),
                "valid_rows": len(raw_rows) - invalid_count,
                "invalid_rows": invalid_count,
                "created_count": created_count,
                "updated_count": updated_count,
                "skipped_count": skipped_count,
                "error_count": invalid_count,
                "errors": errors,
                "run_id": run.id,
            }


        def commit(spec: dict, fmt: str, data: str, db: Session) -> dict:
            raw_rows = parse_csv(data) if fmt == "csv" else parse_json(data)
            return commit_records(spec, raw_rows, db, fmt)
    ''').strip()

    return "\n\n".join([header, imports_literal, fields_literal, meta_literal, classes_literal, body]) + "\n"


def _seed_value(value: Any, field: ModelField | None = None) -> str:
    if field and field.type == "date" and isinstance(value, str):
        return f"date.fromisoformat({value!r})"
    return repr(value)


def _backend_providers_module(model: ModelDrivenApp) -> str:
    providers_payload = [
        {
            "id": provider.id,
            "label": provider.label or provider.id.replace("_", " ").title(),
            "type": provider.type,
            "mode": provider.mode,
            "target_import": provider.target_import,
            "env": provider.env.model_dump(),
            "source": provider.source.model_dump(),
        }
        for provider in model.providers
    ]
    providers_literal = f"PROVIDERS: list[dict[str, Any]] = {pprint.pformat(providers_payload, indent=4, width=100, sort_dicts=False)}"
    body = textwrap.dedent('''
        """Provider Runtime v0 for model-driven apps.

        Providers are thin source adapters. They fetch and normalize external records,
        then delegate validation, mapping, upsert, commit, and run history to the
        generated generic importer pipeline.
        """
        from __future__ import annotations

        import json
        import os
        import urllib.error
        import urllib.parse
        import urllib.request
        from typing import Any

        from sqlalchemy.orm import Session

        from app import imports as importer
    ''').strip()
    impl = textwrap.dedent('''
        def get_provider(provider_id: str) -> dict | None:
            for provider in PROVIDERS:
                if provider["id"] == provider_id:
                    return provider
            return None


        def env_status(provider: dict) -> dict:
            names = [provider["env"]["token"], provider["env"]["repo"]]
            missing = [name for name in names if not os.getenv(name)]
            return {"configured": len(missing) == 0, "missing": missing, "required": names}


        def public_provider(provider: dict) -> dict:
            spec = importer.get_import(provider["target_import"])
            status = env_status(provider)
            return {
                "id": provider["id"],
                "label": provider["label"],
                "type": provider["type"],
                "mode": provider["mode"],
                "target_import": provider["target_import"],
                "target_entity": spec["entity"] if spec else "",
                "env_status": status,
                "source": provider.get("source") or {},
            }


        def _require_ready(provider: dict) -> None:
            status = env_status(provider)
            if not status["configured"]:
                raise ValueError("missing provider env vars: " + ", ".join(status["missing"]))
            if importer.get_import(provider["target_import"]) is None:
                raise ValueError("provider target import not found")


        def fetch_github_issues(provider: dict) -> list[dict[str, Any]]:
            env = provider["env"]
            source = provider.get("source") or {}
            token = os.environ[env["token"]]
            repo = os.environ[env["repo"]]
            if "/" not in repo:
                raise ValueError(f"{env['repo']} must be in owner/repo format")
            params: dict[str, str] = {"state": source.get("state") or "open", "per_page": "100"}
            labels = source.get("labels") or []
            if labels:
                params["labels"] = ",".join(labels)
            url = f"https://api.github.com/repos/{repo}/issues?{urllib.parse.urlencode(params)}"
            request = urllib.request.Request(
                url,
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {token}",
                    "User-Agent": "AgentForge-ProviderRuntime-v0",
                },
            )
            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    payload = json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")[:200]
                raise ValueError(f"GitHub API error {exc.code}: {detail}") from exc
            except urllib.error.URLError as exc:
                raise ValueError(f"GitHub API request failed: {exc.reason}") from exc
            if not isinstance(payload, list):
                raise ValueError("GitHub API response was not a list")
            return [dict(item) for item in payload if isinstance(item, dict)]


        def normalize_github_issues(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
            normalized: list[dict[str, Any]] = []
            for record in records:
                if record.get("pull_request"):
                    continue
                labels = record.get("labels") or []
                label_names = [str(item.get("name", "")) for item in labels if isinstance(item, dict) and item.get("name")]
                user = record.get("user") if isinstance(record.get("user"), dict) else {}
                normalized.append(
                    {
                        "number": str(record.get("number", "")),
                        "title": record.get("title") or "",
                        "body": record.get("body") or "",
                        "state": record.get("state") or "",
                        "html_url": record.get("html_url") or "",
                        "labels": ", ".join(label_names),
                        "user_login": user.get("login") or "",
                        "updated_at": record.get("updated_at") or "",
                    }
                )
            return normalized


        def fetch_records(provider: dict) -> list[dict[str, Any]]:
            if provider["type"] == "github_issues":
                return normalize_github_issues(fetch_github_issues(provider))
            raise ValueError(f"unsupported provider type: {provider['type']}")


        def preview(provider: dict, db: Session) -> dict:
            _require_ready(provider)
            spec = importer.get_import(provider["target_import"])
            if spec is None:
                raise ValueError("provider target import not found")
            records = fetch_records(provider)
            result = importer.preview_records(spec, records, db, "provider")
            result["provider_id"] = provider["id"]
            return result


        def sync(provider: dict, db: Session) -> dict:
            _require_ready(provider)
            spec = importer.get_import(provider["target_import"])
            if spec is None:
                raise ValueError("provider target import not found")
            records = fetch_records(provider)
            result = importer.commit_records(spec, records, db, "provider")
            result["provider_id"] = provider["id"]
            return result
    ''').strip()
    return "\n\n".join([body, providers_literal, impl]) + "\n"


def _env_example(model: ModelDrivenApp) -> str:
    names: list[str] = []
    for provider in model.providers:
        for name in (provider.env.token, provider.env.repo):
            if name not in names:
                names.append(name)
    lines = ["# Provider Runtime v0 environment variables"]
    for name in names:
        value = "owner/repo" if name.endswith("REPO") else ""
        lines.append(f"{name}={value}")
    return "\n".join(lines) + "\n"


def _backend_main(pack: DomainPack, model: ModelDrivenApp) -> str:
    imports = ["from datetime import date", "from fastapi import Depends, FastAPI, HTTPException", "from fastapi.middleware.cors import CORSMiddleware", "from sqlalchemy.orm import Session", "from app.database import Base, engine, get_db", "from app import models, schemas", "from app import imports as importer"]
    if model.providers:
        imports.append("from app import providers as provider_runtime")
    imports.append("")
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
    body += [
        "@app.get('/imports')",
        "def list_imports():",
        "    return [",
        "        {",
        "            'id': spec['id'],",
        "            'label': spec['label'],",
        "            'entity': spec['entity'],",
        "            'formats': spec['formats'],",
        "            'upsert_key': spec['upsert_key'],",
        "            'field_map': spec['field_map'],",
        "        }",
        "        for spec in importer.IMPORTS",
        "    ]",
        "",
        "@app.get('/imports/runs')",
        "def list_import_runs(db: Session = Depends(get_db)):",
        "    runs = db.query(models.ImportRun).order_by(models.ImportRun.id.desc()).limit(50).all()",
        "    return [",
        "        {",
        "            'id': run.id,",
        "            'import_id': run.import_id,",
        "            'entity': run.entity,",
        "            'format': run.format,",
        "            'status': run.status,",
        "            'total_rows': run.total_rows,",
        "            'created_count': run.created_count,",
        "            'updated_count': run.updated_count,",
        "            'skipped_count': run.skipped_count,",
        "            'error_count': run.error_count,",
        "            'error_summary': run.error_summary,",
        "        }",
        "        for run in runs",
        "    ]",
        "",
    ]
    if model.providers:
        body += [
            "@app.get('/providers')",
            "def list_providers():",
            "    return [provider_runtime.public_provider(provider) for provider in provider_runtime.PROVIDERS]",
            "",
            "@app.get('/providers/runs')",
            "def list_provider_runs(db: Session = Depends(get_db)):",
            "    target_imports = {provider['target_import'] for provider in provider_runtime.PROVIDERS}",
            "    runs = db.query(models.ImportRun).filter(models.ImportRun.import_id.in_(target_imports)).order_by(models.ImportRun.id.desc()).limit(50).all() if target_imports else []",
            "    return [",
            "        {",
            "            'id': run.id,",
            "            'import_id': run.import_id,",
            "            'entity': run.entity,",
            "            'format': run.format,",
            "            'status': run.status,",
            "            'total_rows': run.total_rows,",
            "            'created_count': run.created_count,",
            "            'updated_count': run.updated_count,",
            "            'skipped_count': run.skipped_count,",
            "            'error_count': run.error_count,",
            "            'error_summary': run.error_summary,",
            "        }",
            "        for run in runs",
            "    ]",
            "",
            "def _resolve_provider(provider_id: str) -> dict:",
            "    provider = provider_runtime.get_provider(provider_id)",
            "    if not provider:",
            "        raise HTTPException(status_code=404, detail='provider not found')",
            "    return provider",
            "",
            "@app.post('/providers/{provider_id}/preview')",
            "def preview_provider(provider_id: str, db: Session = Depends(get_db)):",
            "    provider = _resolve_provider(provider_id)",
            "    try:",
            "        return provider_runtime.preview(provider, db)",
            "    except ValueError as exc:",
            "        raise HTTPException(status_code=400, detail=str(exc))",
            "",
            "@app.post('/providers/{provider_id}/sync')",
            "def sync_provider(provider_id: str, db: Session = Depends(get_db)):",
            "    provider = _resolve_provider(provider_id)",
            "    try:",
            "        return provider_runtime.sync(provider, db)",
            "    except ValueError as exc:",
            "        raise HTTPException(status_code=400, detail=str(exc))",
            "",
        ]
    body += [
        "def _resolve_import(import_id: str, fmt: str) -> dict:",
        "    spec = importer.get_import(import_id)",
        "    if not spec:",
        "        raise HTTPException(status_code=404, detail='import not found')",
        "    if fmt not in spec['formats']:",
        "        raise HTTPException(status_code=400, detail=f\"format must be one of {spec['formats']}\")",
        "    return spec",
        "",
        "@app.post('/imports/{import_id}/preview')",
        "def preview_import(import_id: str, payload: schemas.ImportPayload, db: Session = Depends(get_db)):",
        "    spec = _resolve_import(import_id, payload.format)",
        "    try:",
        "        return importer.preview(spec, payload.format, payload.data, db)",
        "    except ValueError as exc:",
        "        raise HTTPException(status_code=400, detail=str(exc))",
        "",
        "@app.post('/imports/{import_id}/commit')",
        "def commit_import(import_id: str, payload: schemas.ImportPayload, db: Session = Depends(get_db)):",
        "    spec = _resolve_import(import_id, payload.format)",
        "    try:",
        "        return importer.commit(spec, payload.format, payload.data, db)",
        "    except ValueError as exc:",
        "        raise HTTPException(status_code=400, detail=str(exc))",
        "",
    ]
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
    lines += _import_test_lines(model)
    lines += _provider_test_lines(model)
    return "\n".join(lines)


def _provider_test_lines(model: ModelDrivenApp) -> list[str]:
    if not model.providers:
        return []
    provider = model.providers[0]
    target_import = next((item for item in model.imports if item.id == provider.target_import), None)
    if target_import is None:
        return []
    route = target_import.entity.replace('_', '-')
    return [
        "",
        "def test_providers_endpoint_reports_missing_env(monkeypatch):",
        "    monkeypatch.delenv('GITHUB_TOKEN', raising=False)",
        "    monkeypatch.delenv('GITHUB_REPO', raising=False)",
        "    response = client.get('/providers')",
        "    assert response.status_code == 200",
        "    provider = response.json()[0]",
        "    assert provider['id'] == 'github_issues'",
        "    assert provider['env_status']['configured'] is False",
        "    assert 'GITHUB_TOKEN' in provider['env_status']['missing']",
        "    assert 'GITHUB_REPO' in provider['env_status']['missing']",
        "    assert 'token' not in provider and 'secret' not in provider",
        "",
        "def test_provider_preview_and_sync_use_importer(monkeypatch):",
        "    monkeypatch.setenv('GITHUB_TOKEN', 'test-token')",
        "    monkeypatch.setenv('GITHUB_REPO', 'owner/repo')",
        "    from app import providers",
        "    fixture = [",
        "        {'number': 202, 'title': 'Provider issue', 'body': 'From GitHub', 'state': 'open', 'html_url': 'https://github.com/owner/repo/issues/202', 'labels': [{'name': 'bug'}], 'user': {'login': 'octocat'}, 'updated_at': '2026-05-15T00:00:00Z'},",
        "        {'number': 203, 'title': 'PR should be ignored', 'state': 'open', 'pull_request': {'url': 'https://api.github.com/pr/203'}},",
        "    ]",
        "    monkeypatch.setattr(providers, 'fetch_github_issues', lambda provider: fixture)",
        "    preview = client.post('/providers/github_issues/preview')",
        "    assert preview.status_code == 200",
        "    preview_body = preview.json()",
        "    assert preview_body['provider_id'] == 'github_issues'",
        "    assert preview_body['total_rows'] == 1",
        "    assert preview_body['valid_rows'] == 1",
        "    first = client.post('/providers/github_issues/sync').json()",
        "    second = client.post('/providers/github_issues/sync').json()",
        "    assert first['status'] == 'ok' and second['status'] == 'ok'",
        "    assert first['created_count'] == 1",
        "    assert second['updated_count'] == 1",
        f"    listing = client.get('/{route}').json()",
        "    matches = [row for row in listing if row.get('external_id') == '202']",
        "    assert len(matches) == 1",
        "    runs = client.get('/providers/runs').json()",
        "    assert runs and runs[0]['format'] == 'provider'",
        "",
        "def test_provider_missing_env_returns_clear_error(monkeypatch):",
        "    monkeypatch.delenv('GITHUB_TOKEN', raising=False)",
        "    monkeypatch.delenv('GITHUB_REPO', raising=False)",
        "    response = client.post('/providers/github_issues/preview')",
        "    assert response.status_code == 400",
        "    assert 'missing provider env vars' in response.json()['detail']",
    ]


def _import_test_lines(model: ModelDrivenApp) -> list[str]:
    if not model.imports:
        return []
    entity_map = {entity.name: entity for entity in model.entities}
    spec = next((item for item in model.imports if (entity_map.get(item.entity) and not any(f.type == 'relation' for f in entity_map[item.entity].fields))), model.imports[0])
    entity = entity_map[spec.entity]
    target_to_source: dict[str, str] = {}
    for source, target in spec.field_map.items():
        target_to_source.setdefault(target, source)
    for field in entity.fields:
        target_to_source.setdefault(field.name, field.name)

    def sample_value(field: ModelField, variant: str = "primary") -> Any:
        if field.type == 'enum':
            return field.enum_values[0]
        if field.type == 'boolean':
            return True
        if field.type == 'integer':
            return 1
        if field.type == 'relation':
            return 1
        if field.type == 'date':
            return "2026-09-01"
        if variant == "primary":
            return f"Imported {field.name}"
        return f"Updated {field.name}"

    primary_row = {target_to_source[field.name]: sample_value(field, "primary") for field in entity.fields}
    header_keys = list(primary_row.keys())
    csv_header = ",".join(header_keys)
    csv_row = ",".join(str(primary_row[key]) for key in header_keys)
    csv_payload = f"{csv_header}\n{csv_row}"
    json_payload = json.dumps([primary_row])
    enum_field = next((field for field in entity.fields if field.type == 'enum'), None)

    lines = [
        "",
        "def test_imports_endpoint_lists_configured_imports():",
        "    response = client.get('/imports')",
        "    assert response.status_code == 200",
        "    ids = [item['id'] for item in response.json()]",
        f"    assert {spec.id!r} in ids",
        "",
        "def test_import_preview_csv():",
        f"    payload = {{'format': 'csv', 'data': {csv_payload!r}}}",
        f"    response = client.post('/imports/{spec.id}/preview', json=payload)",
        "    assert response.status_code == 200",
        "    body = response.json()",
        "    assert body['total_rows'] == 1",
        "    assert body['valid_rows'] == 1",
        "    assert body['invalid_rows'] == 0",
        "",
        "def test_import_preview_json():",
        f"    payload = {{'format': 'json', 'data': {json_payload!r}}}",
        f"    response = client.post('/imports/{spec.id}/preview', json=payload)",
        "    assert response.status_code == 200",
        "    body = response.json()",
        "    assert body['total_rows'] == 1",
        "    assert body['valid_rows'] == 1",
        "",
        "def test_import_preview_json_records_envelope():",
        f"    envelope = {{'records': [{primary_row!r}]}}",
        f"    response = client.post('/imports/{spec.id}/preview', json={{'format': 'json', 'data': __import__('json').dumps(envelope)}})",
        "    assert response.status_code == 200",
        "    assert response.json()['total_rows'] == 1",
    ]

    if enum_field:
        bad_row = dict(primary_row)
        bad_row[target_to_source[enum_field.name]] = "not_allowed"
        bad_csv_header = ",".join(bad_row.keys())
        bad_csv_row = ",".join(str(bad_row[key]) for key in bad_row.keys())
        bad_csv_payload = f"{bad_csv_header}\n{bad_csv_row}"
        lines += [
            "",
            "def test_import_preview_invalid_enum_row():",
            f"    payload = {{'format': 'csv', 'data': {bad_csv_payload!r}}}",
            f"    response = client.post('/imports/{spec.id}/preview', json=payload)",
            "    body = response.json()",
            "    assert body['invalid_rows'] == 1",
            "    assert body['valid_rows'] == 0",
            "    assert body['errors']",
        ]

    integer_field = next((field for field in entity.fields if field.type == 'integer'), None)
    if integer_field:
        bad_row = dict(primary_row)
        bad_row[target_to_source[integer_field.name]] = "not-a-number"
        bad_csv_header = ",".join(bad_row.keys())
        bad_csv_row = ",".join(str(bad_row[key]) for key in bad_row.keys())
        bad_csv_payload = f"{bad_csv_header}\n{bad_csv_row}"
        lines += [
            "",
            "def test_import_preview_invalid_integer_row():",
            f"    payload = {{'format': 'csv', 'data': {bad_csv_payload!r}}}",
            f"    response = client.post('/imports/{spec.id}/preview', json=payload)",
            "    assert response.json()['invalid_rows'] == 1",
        ]

    primary_target_value = sample_value(next((f for f in entity.fields if f.required and f.type in ("string", "text")), entity.fields[0]), "primary")
    primary_target_field = next((f.name for f in entity.fields if f.required and f.type in ("string", "text")), entity.fields[0].name)
    lines += [
        "",
        "def test_import_commit_creates_records():",
        f"    payload = {{'format': 'csv', 'data': {csv_payload!r}}}",
        f"    response = client.post('/imports/{spec.id}/commit', json=payload)",
        "    body = response.json()",
        "    assert body['status'] == 'ok'",
        "    assert body['error_count'] == 0",
        "    assert body['created_count'] + body['updated_count'] >= 1",
        f"    listing = client.get('/{spec.entity.replace('_', '-')}').json()",
        f"    assert any(row.get({primary_target_field!r}) == {primary_target_value!r} for row in listing)",
        "    runs = client.get('/imports/runs').json()",
        f"    assert any(run['import_id'] == {spec.id!r} for run in runs)",
    ]

    if spec.upsert_key:
        lines += [
            "",
            "def test_import_commit_upsert_is_idempotent():",
            f"    payload = {{'format': 'csv', 'data': {csv_payload!r}}}",
            f"    first = client.post('/imports/{spec.id}/commit', json=payload).json()",
            f"    second = client.post('/imports/{spec.id}/commit', json=payload).json()",
            "    assert first['status'] == 'ok' and second['status'] == 'ok'",
            "    assert second['updated_count'] >= 1 or second['created_count'] == 0",
            "    listing = client.get('/imports').json()",
            f"    spec = next(item for item in listing if item['id'] == {spec.id!r})",
            f"    assert spec['upsert_key'] == {spec.upsert_key!r}",
        ]

    if enum_field:
        bad_row = dict(primary_row)
        bad_row[target_to_source[enum_field.name]] = "not_allowed"
        bad_csv_header = ",".join(bad_row.keys())
        bad_csv_row = ",".join(str(bad_row[key]) for key in bad_row.keys())
        bad_csv_payload = f"{bad_csv_header}\n{bad_csv_row}"
        lines += [
            "",
            "def test_import_commit_rejects_invalid_rows():",
            f"    payload = {{'format': 'csv', 'data': {bad_csv_payload!r}}}",
            f"    response = client.post('/imports/{spec.id}/commit', json=payload)",
            "    body = response.json()",
            "    assert body['status'] == 'rejected'",
            "    assert body['created_count'] == 0",
            "    assert body['error_count'] >= 1",
        ]

    return lines


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
type ImportConfig = {{ id: string; label: string; entity: string; formats: string[]; upsertKey: string; fieldMap: Record<string, string> }};
type ImportRun = {{ id: number; import_id: string; entity: string; format: string; status: string; total_rows: number; created_count: number; updated_count: number; skipped_count: number; error_count: number; error_summary: string | null }};
type RelationResolution = {{ row: number; source_column: string; field: string; source_field: string; target_entity: string; target_label?: string; display_field?: string; source_value?: string; matched_id: number; matched_by: 'id' | 'label' }};
type ImportPreview = {{ import_id: string; entity: string; format: string; total_rows: number; valid_rows: number; invalid_rows: number; errors: {{ row: number; errors: string[] }}[]; mapped_fields: string[]; would_create: number; would_update: number; relation_resolutions?: RelationResolution[] }};
type ImportCommit = {{ import_id: string; status: string; total_rows: number; valid_rows: number; invalid_rows: number; created_count: number; updated_count: number; skipped_count: number; error_count: number; errors: {{ row: number; errors: string[] }}[]; run_id: number; provider_id?: string }};
type ProviderConfig = {{ id: string; label: string; type: string; mode: string; targetImport: string; env: {{ token: string; repo: string }}; source: {{ state?: string; labels?: string[] }} }};
type ProviderStatus = {{ id: string; label: string; type: string; mode: string; target_import: string; target_entity: string; env_status: {{ configured: boolean; missing: string[]; required: string[] }}; source: {{ state?: string; labels?: string[] }} }};
type AppModel = {{ app: {{ name: string; displayName: string; description: string }}; entities: Entity[]; actions: Action[]; pages?: unknown[]; seedData?: unknown; imports: ImportConfig[]; providers: ProviderConfig[]; ui: {{ composition: 'standard' | 'board_workspace' | 'register_table'; recipe: 'standard' | 'workspace_board' | 'executive_register' | 'ops_console'; style: {{ accent: string; density: string; layout: string }}; focus: Focus; dashboard: {{ title: string; primary_entity?: string; cards: Card[] }}; entities?: unknown }} }};
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
  const importsMode = active === '__imports__';
  const providersMode = active === '__providers__';
  return <main className={{shellClass}} data-composition={{model.ui.composition}} data-recipe={{model.ui.recipe}} data-active-entity={{active}} data-primary-active={{isPrimaryActive ? 'true' : 'false'}} data-imports-active={{importsMode ? 'true' : 'false'}} data-providers-active={{providersMode ? 'true' : 'false'}}>
    <Sidebar active={{active}} setActive={{setActive}} seed={{seed}} />
    {{providersMode ? <ProviderPanel reload={{loadAll}} /> : importsMode ? <ImportPanel reload={{loadAll}} /> : model.ui.composition === 'standard' ? <StandardLayout {{...context}} /> : isPrimaryActive && model.ui.composition === 'board_workspace' ? <BoardWorkspace {{...context}} /> : isPrimaryActive && model.ui.composition === 'register_table' ? <RegisterTable {{...context}} /> : <FocusedSurface {{...context}} />}}
  </main>;
}}

function Sidebar({{ active, setActive, seed }}: {{ active: string; setActive: (name: string) => void; seed: () => void }}) {{ return <aside><p className="eyebrow">AgentForge model-driven app</p><h1>{pack.display_name}</h1><p>{pack.domain.product_purpose}</p><button onClick={{seed}}>Load seed data</button>{{model.entities.map((item) => <button className={{item.name === active ? 'active' : ''}} key={{item.name}} onClick={{() => setActive(item.name)}}>{{item.labelPlural}}</button>)}}{{model.imports.length > 0 && <button className={{active === '__imports__' ? 'active' : ''}} data-ui-control="imports-nav" onClick={{() => setActive('__imports__')}}>Imports</button>}}{{model.providers.length > 0 && <button className={{active === '__providers__' ? 'active' : ''}} data-ui-control="providers-nav" onClick={{() => setActive('__providers__')}}>Providers</button>}}</aside>; }}

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

function relationImportAliases(field: Field, config: ImportConfig): string[] {{ const aliases = new Set<string>(); aliases.add(field.name); if (field.name.endsWith('_id')) aliases.add(field.name.slice(0, -3)); if (field.label) aliases.add(field.label); const target = entityByName(field.targetEntity); if (target) {{ aliases.add(target.labelSingular); aliases.add(target.labelPlural); }} Object.entries(config.fieldMap || {{}}).forEach(([source, targetField]) => {{ if (targetField === field.name) aliases.add(source); }}); return Array.from(aliases).filter(Boolean); }}
function relationFieldsForImport(config?: ImportConfig): {{ field: Field; aliases: string[]; target?: Entity }}[] {{ if (!config) return []; const entity = entityByName(config.entity); if (!entity) return []; return entity.fields.filter((field) => field.type === 'relation').map((field) => ({{ field, aliases: relationImportAliases(field, config), target: entityByName(field.targetEntity) }})); }}

function ProviderPanel({{ reload }}: {{ reload: () => Promise<void> }}) {{ const [providers, setProviders] = useState<ProviderStatus[]>([]); const [selectedId, setSelectedId] = useState<string>(model.providers[0]?.id || ''); const [preview, setPreview] = useState<ImportPreview | null>(null); const [synced, setSynced] = useState<ImportCommit | null>(null); const [runs, setRuns] = useState<ImportRun[]>([]); const [error, setError] = useState<string>(''); async function loadProviders() {{ const response = await fetch(`${{API}}/providers`); if (response.ok) {{ const data = (await response.json()) as ProviderStatus[]; setProviders(data); if (!selectedId && data[0]) setSelectedId(data[0].id); }} }} async function loadRuns() {{ const response = await fetch(`${{API}}/providers/runs`); if (response.ok) setRuns(await response.json()); }} useEffect(() => {{ void loadProviders(); void loadRuns(); }}, []); const provider = providers.find((item) => item.id === selectedId) || providers[0]; async function callProvider(path: 'preview' | 'sync') {{ if (!provider) return; try {{ setError(''); const response = await fetch(`${{API}}/providers/${{provider.id}}/${{path}}`, {{ method: 'POST' }}); if (!response.ok) {{ const detail = await response.json().catch(() => ({{}})); throw new Error((detail && detail.detail) || `${{path}} failed`); }} const result = await response.json(); if (path === 'preview') {{ setPreview(result as ImportPreview); setSynced(null); }} else {{ setSynced(result as ImportCommit); await loadRuns(); await reload(); }} }} catch (caught) {{ setError((caught as Error).message); }} }} if (model.providers.length === 0) return <section className="content"><h2>No providers configured</h2></section>; const missing = provider?.env_status.missing || []; const ready = provider?.env_status.configured ?? false; return <section className="content provider-panel" data-ui-surface="provider-panel"><section className="hero"><div><p className="eyebrow">Provider Runtime v0</p><h2>Providers</h2><p>Preview and sync read-only external records through the shared importer pipeline.</p></div><strong>{{runs.length}} {{runs.length === 1 ? 'run' : 'runs'}}</strong></section><div className="card provider-controls"><label>Provider<select value={{provider?.id || ''}} onChange={{(event) => {{ setSelectedId(event.target.value); setPreview(null); setSynced(null); setError(''); }}}} data-ui-control="provider-select">{{providers.map((item) => <option key={{item.id}} value={{item.id}}>{{item.label}}</option>)}}</select></label>{{provider && <><p><b>{{provider.label}}</b> · {{provider.type}} · {{provider.mode}} · target {{provider.target_import}}/{{provider.target_entity}}</p><p data-ui-state={{ready ? 'configured' : 'missing-env'}}>{{ready ? 'Environment configured' : `Missing env vars: ${{missing.join(', ')}}`}}</p><p><small>Required env vars: {{provider.env_status.required.join(', ')}}. Secret values are never shown.</small></p><div className="import-buttons"><button type="button" onClick={{() => callProvider('preview')}} data-ui-action="provider-preview" disabled={{!ready}}>Preview</button><button type="button" onClick={{() => callProvider('sync')}} data-ui-action="provider-sync" disabled={{!ready || !preview || preview.invalid_rows > 0}}>Sync</button></div></>}}{{error && <p className="import-error" data-ui-state="error">{{error}}</p>}}</div>{{preview && <article className="card import-preview" data-ui-surface="provider-preview"><h3>Preview</h3><p><b>{{preview.total_rows}}</b> rows · <b>{{preview.valid_rows}}</b> valid · <b>{{preview.invalid_rows}}</b> invalid · would create <b>{{preview.would_create}}</b>, update <b>{{preview.would_update}}</b></p><p><small>Mapped fields: {{preview.mapped_fields.join(', ') || 'none'}}</small></p>{{preview.errors.length > 0 && <ul className="import-errors">{{preview.errors.slice(0, 10).map((err) => <li key={{err.row}}>Row {{err.row}}: {{err.errors.join(', ')}}</li>)}}</ul>}}</article>}}{{synced && <article className="card import-commit" data-ui-surface="provider-sync"><h3>Last sync</h3><p>Status: <b>{{synced.status}}</b> · Created <b>{{synced.created_count}}</b> · Updated <b>{{synced.updated_count}}</b> · Skipped <b>{{synced.skipped_count}}</b> · Errors <b>{{synced.error_count}}</b></p></article>}}<article className="card import-runs" data-ui-surface="provider-runs"><h3>Recent provider/import runs</h3>{{runs.length === 0 ? <EmptyState text="No provider syncs yet." /> : <ul>{{runs.slice(0, 10).map((run) => <li key={{run.id}}><b>{{run.import_id}}</b> · {{run.format}} · {{run.status}} · created {{run.created_count}} · updated {{run.updated_count}} · errors {{run.error_count}}{{run.error_summary ? ` — ${{run.error_summary}}` : ''}}</li>)}}</ul>}}</article></section>; }}

function ImportPanel({{ reload }}: {{ reload: () => Promise<void> }}) {{ const [selectedId, setSelectedId] = useState<string>(model.imports[0]?.id || ''); const config = model.imports.find((item) => item.id === selectedId) || model.imports[0]; const [format, setFormat] = useState<string>(config?.formats[0] || 'csv'); const [data, setData] = useState<string>(''); const [preview, setPreview] = useState<ImportPreview | null>(null); const [committed, setCommitted] = useState<ImportCommit | null>(null); const [runs, setRuns] = useState<ImportRun[]>([]); const [error, setError] = useState<string>(''); async function loadRuns() {{ const response = await fetch(`${{API}}/imports/runs`); if (response.ok) setRuns(await response.json()); }} useEffect(() => {{ void loadRuns(); }}, []); useEffect(() => {{ setPreview(null); setCommitted(null); setError(''); setFormat(config?.formats[0] || 'csv'); }}, [selectedId]); useEffect(() => {{ setPreview(null); setCommitted(null); }}, [data, format]); async function callEndpoint(path: string): Promise<unknown> {{ const response = await fetch(`${{API}}/imports/${{config.id}}/${{path}}`, {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, body: JSON.stringify({{ format, data }}) }}); if (!response.ok) {{ const detail = await response.json().catch(() => ({{}})); throw new Error((detail && detail.detail) || `${{path}} failed`); }} return response.json(); }} async function runPreview() {{ try {{ setError(''); const result = (await callEndpoint('preview')) as ImportPreview; setPreview(result); setCommitted(null); }} catch (caught) {{ setError((caught as Error).message); }} }} async function runCommit() {{ try {{ setError(''); const result = (await callEndpoint('commit')) as ImportCommit; setCommitted(result); await loadRuns(); await reload(); }} catch (caught) {{ setError((caught as Error).message); }} }} if (!config) return <section className="content"><h2>No imports configured</h2></section>; const previewValid = !!preview && preview.invalid_rows === 0; const relationFields = relationFieldsForImport(config); return <section className="content import-panel" data-ui-surface="import-panel"><section className="hero"><div><p className="eyebrow">{{model.ui.dashboard.title}}</p><h2>Imports</h2><p>Paste CSV or JSON to preview, validate, and commit records.</p></div><strong>{{runs.length}} {{runs.length === 1 ? 'run' : 'runs'}}</strong></section>{{relationFields.length > 0 && <article className="card import-relation-help" data-ui-surface="import-relation-help"><h3>Relation columns</h3><p>Relation columns can use either IDs or related record names. Related records must already exist; ambiguous or missing names are rejected.</p><ul>{{relationFields.map((item) => <li key={{item.field.name}}><b>{{item.field.label}}</b> → {{item.target?.labelSingular || item.field.targetEntity}}. Accepted columns: {{item.aliases.join(', ')}}.</li>)}}</ul></article>}}<div className="card import-controls"><label>Import config<select value={{config.id}} onChange={{(event) => setSelectedId(event.target.value)}} data-ui-control="import-select">{{model.imports.map((item) => <option key={{item.id}} value={{item.id}}>{{item.label}}</option>)}}</select></label><label>Format<select value={{format}} onChange={{(event) => setFormat(event.target.value)}} data-ui-control="import-format">{{config.formats.map((fmt) => <option key={{fmt}} value={{fmt}}>{{fmt.toUpperCase()}}</option>)}}</select></label><label className="import-data-label">Data ({{format.toUpperCase()}})<textarea value={{data}} onChange={{(event) => setData(event.target.value)}} placeholder={{format === 'csv' ? 'paste CSV here (with header row)' : 'paste JSON array or {{ "records": [...] }}'}} data-ui-control="import-data" rows={{8}} /></label><div className="import-buttons"><button type="button" onClick={{runPreview}} data-ui-action="import-preview" disabled={{!data.trim()}}>Preview</button><button type="button" onClick={{runCommit}} data-ui-action="import-commit" disabled={{!previewValid}}>Commit import</button></div>{{error && <p className="import-error" data-ui-state="error">{{error}}</p>}}</div>{{preview && <article className="card import-preview" data-ui-surface="import-preview"><h3>Preview</h3><p><b>{{preview.total_rows}}</b> rows · <b>{{preview.valid_rows}}</b> valid · <b>{{preview.invalid_rows}}</b> invalid · would create <b>{{preview.would_create}}</b>, update <b>{{preview.would_update}}</b></p><p><small>Mapped fields: {{preview.mapped_fields.join(', ') || 'none'}}</small></p>{{preview.errors.length > 0 && <ul className="import-errors">{{preview.errors.slice(0, 10).map((err) => <li key={{err.row}}>Row {{err.row}}: {{err.errors.join(', ')}}</li>)}}</ul>}}</article>}}{{committed && <article className="card import-commit" data-ui-surface="import-commit"><h3>Last commit</h3><p>Status: <b>{{committed.status}}</b> · Created <b>{{committed.created_count}}</b> · Updated <b>{{committed.updated_count}}</b> · Skipped <b>{{committed.skipped_count}}</b> · Errors <b>{{committed.error_count}}</b></p>{{committed.status === 'rejected' && committed.errors.length > 0 && <ul className="import-errors">{{committed.errors.slice(0, 10).map((err) => <li key={{err.row}}>Row {{err.row}}: {{err.errors.join(', ')}}</li>)}}</ul>}}</article>}}<article className="card import-runs" data-ui-surface="import-runs"><h3>Recent import runs</h3>{{runs.length === 0 ? <EmptyState text="No imports yet — preview and commit one to record a run." /> : <ul>{{runs.slice(0, 10).map((run) => <li key={{run.id}}><b>{{run.import_id}}</b> · {{run.format}} · {{run.status}} · created {{run.created_count}} · updated {{run.updated_count}} · errors {{run.error_count}}{{run.error_summary ? ` — ${{run.error_summary}}` : ''}}</li>)}}</ul>}}</article></section>; }}
'''


def _frontend_styles() -> str:
    return "body{margin:0;font-family:Inter,system-ui,sans-serif;background:#f4f7fb;color:#172033}.shell{--accent:#3157d5;display:grid;grid-template-columns:240px minmax(0,1fr);gap:18px;padding:22px;max-width:1440px;margin:0 auto;box-sizing:border-box}.accent-emerald{--accent:#059669}.accent-blue{--accent:#2563eb}.accent-amber{--accent:#d97706}.accent-red{--accent:#dc2626}.accent-slate{--accent:#475569}.accent-violet{--accent:#7c3aed}.density-compact{gap:12px;padding:16px}.density-spacious{gap:26px;padding:30px}aside,.card,.hero,.stat-card,.record-card,.lane,.secondary-panel,.register-side,.workspace-header,.register-title{background:white;border:1px solid #dbe3f8;border-radius:16px;padding:16px;box-shadow:0 12px 30px #1f2a4420;min-width:0}aside{height:fit-content;display:grid;gap:12px;border-top:5px solid var(--accent)}button{border:0;border-radius:12px;background:var(--accent);color:white;padding:10px 14px;font-weight:700;cursor:pointer}button.active{background:#172033}.content{display:grid;gap:18px}.hero,.workspace-header,.register-top{display:flex;justify-content:space-between;align-items:stretch;gap:18px}.workspace-header{background:linear-gradient(135deg,#fff,#ecfdf5)}.register-title{background:linear-gradient(135deg,#fff,#fffbeb);min-width:260px}.eyebrow{text-transform:uppercase;letter-spacing:.08em;color:var(--accent);font-size:12px;font-weight:800}.dashboard-grid,.entity-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}.compact-dashboard{grid-template-columns:repeat(auto-fit,minmax(150px,1fr));flex:1;min-width:0}.stat-card strong{display:block;font-size:34px;color:var(--accent)}.breakdown span{display:flex;justify-content:space-between;border-top:1px solid #edf1fb;padding:8px 0}.attention small{display:block;margin-top:8px}.form-card{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}.compact-form{grid-template-columns:1fr}label{display:grid;gap:6px;font-weight:700;min-width:0}input,select{border:1px solid #cbd5ef;border-radius:10px;padding:9px;max-width:100%;box-sizing:border-box}.table-scroll{overflow-x:auto;max-width:100%}table{width:100%;border-collapse:collapse;table-layout:auto}th,td{text-align:left;border-bottom:1px solid #e7ecfb;padding:9px;vertical-align:top;word-break:break-word}td{max-width:260px}td button{margin-right:6px;background:#5a6f9f}.board-scroll{overflow-x:auto;max-width:100%}.board{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(220px,1fr);gap:12px;align-items:start;min-width:100%}.lane{background:#f8fafc;min-height:240px;min-width:0}.record-card{display:grid;gap:12px;border-left:5px solid var(--accent);margin-bottom:10px}.badge{display:inline-block;border-radius:999px;background:color-mix(in srgb,var(--accent) 14%,white);color:var(--accent);font-weight:800;padding:4px 9px}small{color:#64748b}.workspace-main{display:grid;grid-template-columns:minmax(0,1fr) clamp(240px,26vw,300px);gap:14px;align-items:start;min-width:0}.workspace-board{min-width:0;display:grid;gap:12px}.secondary-panel{min-width:0}.secondary-panel .entity-grid{grid-template-columns:1fr}.compact-create{max-width:100%;min-width:0}.compact-create .form-card{grid-template-columns:repeat(auto-fit,minmax(180px,1fr))}.register-top{align-items:stretch;flex-wrap:wrap}.register-main{display:grid;grid-template-columns:minmax(0,1fr) clamp(260px,28vw,320px);gap:14px;align-items:start;min-width:0}.register-focus{min-width:0}.register-card{border-top:5px solid var(--accent);overflow:hidden;min-width:0}.register-card .table-scroll{max-width:100%;overflow-x:auto}.register-card table{font-size:14px;min-width:520px}.register-card th{background:#f8fafc;position:sticky;top:0}.register-side{display:grid;gap:12px;min-width:0}.register-side .entity-grid{grid-template-columns:1fr}.register-side .form-card{grid-template-columns:1fr}.composition-register_table aside{border-top-color:var(--accent)}.secondary-panel,.register-side{max-height:calc(100vh - 180px);overflow-y:auto;scrollbar-gutter:stable}.secondary-panel .entity-grid,.register-side .entity-grid{grid-template-columns:1fr;gap:10px}.focused-surface{display:grid;gap:14px}.focused-main{display:grid;grid-template-columns:minmax(0,1fr) clamp(260px,28vw,320px);gap:14px;align-items:start;min-width:0}.focused-list,.focused-create{min-width:0}.focused-create .form-card{grid-template-columns:1fr}.focused-create h3{margin-top:0}@media(max-width:1180px){.focused-main{grid-template-columns:1fr}}.empty-state{border:1px dashed #cbd5e1;border-radius:14px;color:#64748b;background:#f8fafc;padding:18px;text-align:center;font-weight:700}.compact-empty{padding:12px;font-size:13px}.recipe-workspace_board{background:linear-gradient(135deg,#ecfdf5,#f8fafc)}.recipe-workspace_board aside{background:#ffffffcc;box-shadow:none;border-color:#bbf7d0}.recipe-workspace_board .lane{background:#f0fdf4;border-color:#bbf7d0;box-shadow:0 8px 18px #16653414}.recipe-workspace_board .record-card{border-radius:16px;box-shadow:0 8px 18px #16653412}.recipe-workspace_board .compact-create .form-card{box-shadow:none;background:#ffffffb8}.recipe-executive_register{background:#0f172a;color:#172033}.recipe-executive_register aside,.recipe-executive_register .register-side{background:#111827;color:#e5e7eb;border-color:#334155;box-shadow:none}.recipe-executive_register aside p,.recipe-executive_register aside h1{color:#e5e7eb}.recipe-executive_register .register-title,.recipe-executive_register .stat-card{border-radius:10px;box-shadow:none}.recipe-executive_register .register-card{border-radius:10px;box-shadow:none}.recipe-executive_register th,.recipe-executive_register td{padding:8px}.recipe-executive_register .badge{border-radius:6px;text-transform:uppercase;font-size:11px;letter-spacing:.06em}.recipe-executive_register .register-side h3{color:#f1f5f9;letter-spacing:.04em}.recipe-executive_register .register-side .record-card{background:#1f2937;color:#f1f5f9;border:1px solid #475569;border-left:5px solid var(--accent);box-shadow:none}.recipe-executive_register .register-side .record-card h3{color:#f8fafc;margin:0}.recipe-executive_register .register-side .record-card p{color:#cbd5e1;margin:0}.recipe-executive_register .register-side .record-card small{color:#94a3b8}.recipe-executive_register .register-side .record-card .badge{background:color-mix(in srgb,var(--accent) 32%,#0f172a);color:#fef3c7;border:1px solid color-mix(in srgb,var(--accent) 55%,#0f172a)}.recipe-executive_register .register-side .empty-state{background:#111827;color:#cbd5e1;border-color:#475569}.recipe-executive_register .register-side .form-card{background:#1f2937;color:#f1f5f9;border-color:#475569}.recipe-executive_register .register-side .form-card h3,.recipe-executive_register .register-side .form-card label{color:#f1f5f9}.recipe-executive_register .register-side .form-card input,.recipe-executive_register .register-side .form-card select{background:#0f172a;color:#f1f5f9;border-color:#475569}.badge-high,.badge-critical,.badge-blocked{background:#fee2e2;color:#b91c1c}.badge-medium,.badge-investigating,.badge-in-progress{background:#fef3c7;color:#92400e}.badge-low,.badge-open,.badge-todo{background:#dbeafe;color:#1d4ed8}.badge-done,.badge-mitigated,.badge-accepted{background:#dcfce7;color:#166534}@media(max-width:1280px){.workspace-main,.register-main{grid-template-columns:minmax(0,1fr)}.workspace-header,.register-top{display:grid}.compact-dashboard{grid-template-columns:repeat(auto-fit,minmax(150px,1fr))}.shell{padding:18px;gap:14px}}@media(max-width:980px){.shell{grid-template-columns:1fr}aside{position:static;border-top-width:3px}}@media(max-width:720px){.dashboard-grid,.entity-grid{grid-template-columns:1fr}.compact-dashboard{grid-template-columns:1fr}.form-card{grid-template-columns:1fr}}.import-panel{display:grid;gap:14px}.import-controls{display:grid;gap:12px}.import-data-label textarea{width:100%;min-height:180px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:13px;padding:10px;border:1px solid #cbd5ef;border-radius:10px;box-sizing:border-box;resize:vertical}.import-buttons{display:flex;gap:10px;flex-wrap:wrap}.import-buttons button:disabled{opacity:.45;cursor:not-allowed}.import-preview p,.import-commit p{margin:6px 0}.import-errors{margin:8px 0 0;padding-left:20px;color:#b91c1c;font-size:13px}.import-runs ul{list-style:none;padding:0;margin:0;display:grid;gap:8px}.import-runs li{border-top:1px solid #edf1fb;padding:8px 0;font-size:13px}.import-runs li:first-child{border-top:0}.import-error{color:#b91c1c;font-weight:700;margin:0}"


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


def _relation_import_examples(pack: DomainPack) -> str:
    if not pack.model:
        return ""
    entities = {entity.name: entity for entity in pack.model.entities}
    import_by_entity = {spec.entity: spec for spec in pack.model.imports}
    lines: list[str] = []
    for spec in pack.model.imports:
        entity = entities.get(spec.entity)
        if not entity:
            continue
        relation_fields = [field for field in entity.fields if field.type == "relation"]
        for field in relation_fields:
            target = entities.get(field.target_entity)
            if not target:
                continue
            target_import = import_by_entity.get(target.name)
            label_alias = field.name[:-3] if field.name.endswith("_id") else _label(field).lower().replace(" ", "_")
            display_field = (pack.model.ui.entities.get(target.name).display.title_field if target.name in pack.model.ui.entities else "") or next((candidate for candidate in ["name", "title", "label", "summary"] if any(item.name == candidate for item in target.fields)), "id")
            prefix = f"First import {target.label_plural}"
            if target_import:
                prefix += f" with `{target_import.id}`"
            lines.append(f"- {prefix}, then import {entity.label_plural} with `{label_alias}` containing the related {target.label_singular} `{display_field}` value, or `{field.name}` containing the related id.")
    if not lines:
        return ""
    return """
        ### Relation import examples

        """ + "\n".join(lines) + "\n"


def _readme(pack: DomainPack) -> str:
    provider_doc = ""
    if pack.model and pack.model.providers:
        env_lines = []
        seen: set[str] = set()
        for provider in pack.model.providers:
            for name in (provider.env.token, provider.env.repo):
                if name not in seen:
                    seen.add(name)
                    env_lines.append(f"{name}={'owner/repo' if name.endswith('REPO') else ''}")
        provider_doc = """
        ## Providers panel

        This generated app includes Provider Runtime v0. Providers are optional, read-only input adapters that fetch external records and feed the same generic importer pipeline used by CSV/JSON imports. Provider sync uses the target import config for mapping, validation, upsert/idempotency, and import-run history.

        Configured provider support is bounded to GitHub Issues in read-only mode. There is no OAuth flow, secret entry UI, write-back behavior, provider marketplace, or GitHub repo mutation.

        To use the Providers panel with a real GitHub repo, copy `.env.example` values into your shell environment before starting the backend:

        ```bash
        """ + "\n".join(env_lines) + """
        ```

        `GITHUB_REPO` must use `owner/repo` format. Secret values are never shown in the UI. Default generated backend tests use mocked provider responses and do not require a live GitHub token or network access.
        """
    relation_examples = _relation_import_examples(pack)
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

        ## Import panel (CSV/JSON)

        When the Blueprint declares `model.imports`, the sidebar exposes an **Imports** button. The panel lets you paste either CSV or JSON, preview the parsed/validated rows, and commit the import. CSV and JSON flow through the same generic pipeline; after parsing they share mapping, validation, upsert, and run-history logic.

        - **CSV format**: a single header row followed by data rows. Header names are matched against entity fields; if the Blueprint defines a `field_map` it overrides auto-matching.
        - **JSON format**: either an array of objects (`[{{...}}, {{...}}]`) or an object with a `records`, `items`, or `data` array (`{{"records": [{{...}}]}}`).
        - **Upsert**: when an import config sets `upsert_key`, commits update an existing record whose `upsert_key` value matches; otherwise they insert.
        - **Commit semantics**: any invalid row rejects the entire commit and persists a `rejected` import run — fix the data and retry. Valid commits create/update records and persist an `ok` run.
        - **Relation fields**: supply either the integer id of an existing related record (e.g. `client_id: 1`) or a related record label/name using a safe alias column such as `client` or `vendor`. Related records must already exist; ambiguous or missing labels are rejected.

        {relation_examples}
        Each commit and rejection is logged via `GET /imports/runs`.

        {provider_doc}
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
