"""Deterministic compiler: `AppShape` -> model-driven blueprint spec dict.

The output is the same `{"primary": str, "model": {...}}` shape that
`agentforge.planner.assistant._model_blueprint_from_spec` already consumes,
so the assistant doesn't need to learn a new internal contract. Recipe
selection happens upstream (`agentforge.recipe_select`); compilation here
is pure data conversion driven by the recipe templates plus AppShape fields.

Design rules:
  * Same inputs -> byte-identical output (no clocks, no env, no RNG).
  * Output passes `DomainPack.model_validate` for the four anchor recipes.
  * Workflows map to `update_status` actions only when the recipe's effect
    string spells out `status=<terminal>` on a real enum field; everything
    else is silently skipped so we never invent an unsupported action.
  * UI promotes a `status` enum to `board_workspace.group_by`; otherwise
    falls back to `standard` composition (no fabricated enum fields).
"""
from __future__ import annotations

import re
from typing import Any

from agentforge.app_shape import AppShape, EntitySpec, FieldSpec
from agentforge.recipes import AppRecipe
from agentforge.recipes._base import WorkflowTemplate


_KIND_TO_PACK_TYPE: dict[str, str] = {
    "string": "string",
    "text": "text",
    "number": "integer",
    "integer": "integer",
    "date": "date",
    "datetime": "date",
    "enum": "enum",
    "reference": "relation",
}

# Action effect parser. Matches `set status=foo` and `set Item.status=foo`.
_EFFECT_SET_RE = re.compile(r"set\s+(?:([A-Za-z_][A-Za-z0-9_]*)\.)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([A-Za-z_][A-Za-z0-9_]*)")


def compile_blueprint_spec(shape: AppShape, recipe: AppRecipe) -> dict[str, Any]:
    """Compile an AppShape + chosen AppRecipe into a model-driven spec dict.

    The result is consumable by
    `agentforge.planner.assistant._model_blueprint_from_spec` and produces a
    DomainPack-valid blueprint when wrapped with the existing starter helpers.
    """
    entities = [_pack_entity(entity) for entity in shape.entities]
    primary_name = _pick_primary(entities, shape)
    pages: list[dict[str, Any]] = [
        {"name": "dashboard", "type": "dashboard", "title": "Dashboard"}
    ]
    for entity in entities:
        pages.append({
            "name": _page_name(entity["name"]),
            "type": "entity_list",
            "entity": entity["name"],
            "title": entity["label_plural"],
        })
    actions = _actions_from_recipe(entities, recipe)
    seed = _seed_from_recipe(entities, recipe)
    ui = _ui_from_entities(primary_name, entities)
    return {
        "primary": primary_name,
        "model": {
            "entities": entities,
            "pages": pages,
            "actions": actions,
            "seed_data": seed,
            "ui": ui,
        },
    }


# --- entity / field conversion ------------------------------------------------


def _pack_entity(entity: EntitySpec) -> dict[str, Any]:
    snake = _snake(entity.name)
    label_singular = entity.label or entity.name
    label_plural = _pluralize(label_singular)
    fields = [_pack_field(field) for field in entity.fields]
    if not fields:
        fields = [{"name": "title", "label": "Title", "type": "string", "required": True, "semantic": "title"}]
    if not any(field.get("semantic") == "title" for field in fields):
        for field in fields:
            if field["type"] == "string":
                field["semantic"] = "title"
                break
    return {
        "name": snake,
        "label_singular": label_singular,
        "label_plural": label_plural,
        "fields": fields,
    }


def _pack_field(field: FieldSpec) -> dict[str, Any]:
    pack_type = _KIND_TO_PACK_TYPE.get(field.kind, "string")
    payload: dict[str, Any] = {
        "name": _snake(field.name),
        "label": field.label or field.name,
        "type": pack_type,
        "required": bool(field.required),
    }
    if pack_type == "enum":
        payload["enum_values"] = list(field.enum_values) or ["pending", "done"]
    if pack_type == "relation":
        payload["target_entity"] = _snake(field.references or field.name)
    semantic = _semantic_for(field.name, pack_type)
    if semantic:
        payload["semantic"] = semantic
    return payload


def _semantic_for(name: str, pack_type: str) -> str:
    lowered = name.lower()
    if lowered == "status" and pack_type == "enum":
        return "status"
    if lowered == "priority" and pack_type == "enum":
        return "priority"
    if lowered == "severity" and pack_type == "enum":
        return "severity"
    if lowered in {"owner", "assignee", "reviewer"}:
        return "owner"
    if lowered in {"due_on", "due_date", "deadline"}:
        return "due_date"
    if lowered in {"title", "name", "subject"}:
        return "title"
    if lowered in {"notes", "description", "evidence", "rationale"}:
        return "description"
    return ""


def _pick_primary(entities: list[dict[str, Any]], shape: AppShape) -> str:
    for entity in entities:
        if any(field["type"] == "enum" and field["name"] == "status" for field in entity["fields"]):
            return entity["name"]
    if shape.primary_workflow:
        target = _snake(shape.primary_workflow.target_entity)
        if any(entity["name"] == target for entity in entities):
            return target
    return entities[0]["name"] if entities else ""


# --- workflow -> action mapping ----------------------------------------------


def _actions_from_recipe(entities: list[dict[str, Any]], recipe: AppRecipe) -> list[dict[str, Any]]:
    entity_map = {entity["name"]: entity for entity in entities}
    actions: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    for workflow in recipe.typical_workflows:
        action = _action_from_workflow(workflow, entity_map)
        if action is None:
            continue
        if action["name"] in seen_names:
            continue
        seen_names.add(action["name"])
        actions.append(action)
    return actions


def _action_from_workflow(
    workflow: WorkflowTemplate,
    entity_map: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    target_snake = _snake(workflow.target_entity)
    entity = entity_map.get(target_snake)
    if entity is None:
        return None
    for effect in workflow.effects:
        match = _EFFECT_SET_RE.search(effect)
        if not match:
            continue
        owner, field_name, value = match.group(1), match.group(2), match.group(3)
        if owner and _snake(owner) != target_snake:
            continue
        field = next((field for field in entity["fields"] if field["name"] == field_name), None)
        if field is None or field["type"] != "enum":
            continue
        if value not in (field.get("enum_values") or []):
            continue
        return {
            "name": _snake(workflow.name),
            "label": workflow.label,
            "type": "update_status",
            "entity": entity["name"],
            "field": field_name,
            "value": value,
        }
    return None


# --- seed data ---------------------------------------------------------------


def _seed_from_recipe(entities: list[dict[str, Any]], recipe: AppRecipe) -> dict[str, list[dict[str, Any]]]:
    counts = _per_entity_counts(entities, recipe)
    seed: dict[str, list[dict[str, Any]]] = {}
    for entity in entities:
        count = max(1, counts.get(entity["name"], 1))
        rows: list[dict[str, Any]] = []
        for index in range(count):
            row = _seed_row(entity, index, count, counts)
            if row:
                rows.append(row)
        if rows:
            seed[entity["name"]] = rows
    return seed


def _per_entity_counts(entities: list[dict[str, Any]], recipe: AppRecipe) -> dict[str, int]:
    """Translate recipe's per-entity counts (CamelCase) to snake_case entity ids."""
    counts: dict[str, int] = {}
    for camel, count in (recipe.sample_data_style.per_entity_counts or {}).items():
        counts[_snake(camel)] = max(1, int(count))
    # Ensure every declared entity has at least one row for the demo.
    for entity in entities:
        counts.setdefault(entity["name"], 1)
    return counts


def _seed_row(entity: dict[str, Any], index: int, count: int, counts: dict[str, int]) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for field in entity["fields"]:
        if field["type"] == "relation":
            value = _sample_relation_id(field, index, counts)
        else:
            value = _sample_value(entity, field, index, count)
        if value is None:
            continue
        row[field["name"]] = value
    return row


def _sample_relation_id(field: dict[str, Any], index: int, counts: dict[str, int]) -> int | None:
    if not field.get("required"):
        return None
    target = field.get("target_entity") or ""
    target_count = counts.get(target, 0)
    if target_count <= 0:
        return None
    return (index % target_count) + 1


def _sample_value(entity: dict[str, Any], field: dict[str, Any], index: int, count: int) -> Any:
    semantic = field.get("semantic")
    name = field["name"]
    if field["type"] == "enum":
        values = list(field.get("enum_values") or [])
        if not values:
            return None
        return values[index % len(values)]
    if field["type"] == "string":
        if semantic == "title" or name in {"title", "name"}:
            label = entity["label_singular"]
            return f"Sample {label.lower()} {index + 1}" if count > 1 else f"Sample {label.lower()}"
        return ""
    if field["type"] == "text":
        return f"Notes for {entity['label_singular'].lower()} {index + 1}."
    if field["type"] == "integer":
        if field.get("required"):
            return index + 1
        return None
    if field["type"] == "date":
        if field.get("required"):
            day = (index % 28) + 1
            return f"2026-01-{day:02d}"
        return None
    if field["type"] == "boolean":
        return None
    return None


# --- UI -----------------------------------------------------------------------


def _ui_from_entities(primary_name: str, entities: list[dict[str, Any]]) -> dict[str, Any]:
    primary = next((entity for entity in entities if entity["name"] == primary_name), None)
    if primary is None:
        return {
            "composition": "standard",
            "recipe": "standard",
            "dashboard": {"title": "Dashboard", "primary_entity": "", "cards": []},
        }
    status_field = next(
        (field for field in primary["fields"] if field["type"] == "enum" and field["name"] == "status"),
        None,
    )
    title_field = next(
        (field["name"] for field in primary["fields"] if field.get("semantic") == "title"),
        primary["fields"][0]["name"] if primary["fields"] else "",
    )
    cards: list[dict[str, Any]] = [
        {"type": "count", "entity": primary_name, "label": f"Total {primary['label_plural'].lower()}"},
    ]
    if status_field:
        cards.append({
            "type": "enum_breakdown",
            "entity": primary_name,
            "field": "status",
            "label": "By status",
        })
        return {
            "composition": "board_workspace",
            "recipe": "workspace_board",
            "style": {"accent": "emerald", "density": "comfortable", "layout": "workspace"},
            "focus": {
                "primary_entity": primary_name,
                "group_by": "status",
                "title_field": title_field,
                "badge_field": "status",
            },
            "entities": {
                primary_name: {
                    "display": {
                        "layout": "board_by_status",
                        "title_field": title_field,
                        "badge_field": "status",
                    },
                },
            },
            "dashboard": {"title": "Dashboard", "primary_entity": primary_name, "cards": cards},
        }
    lane_relation = _lane_relation_field(primary, entities)
    if lane_relation is not None:
        return {
            "composition": "board_workspace",
            "recipe": "workspace_board",
            "style": {"accent": "emerald", "density": "comfortable", "layout": "workspace"},
            "focus": {
                "primary_entity": primary_name,
                "group_by": lane_relation["name"],
                "title_field": title_field,
            },
            "entities": {
                primary_name: {
                    "display": {
                        "layout": "board_by_relation",
                        "title_field": title_field,
                    },
                },
            },
            "dashboard": {"title": "Dashboard", "primary_entity": primary_name, "cards": cards},
        }
    return {
        "composition": "standard",
        "recipe": "standard",
        "dashboard": {"title": "Dashboard", "primary_entity": primary_name, "cards": cards},
    }


def _lane_relation_field(
    primary: dict[str, Any],
    entities: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Pick the relation field on `primary` that should drive board lanes, or None.

    Preference: a required relation whose target entity exists in this spec.
    This is how pipeline_kanban's `Card.stage` becomes the lane axis when no
    status enum is available.
    """
    entity_names = {entity["name"] for entity in entities}
    for field in primary["fields"]:
        if field["type"] != "relation" or not field.get("required"):
            continue
        if field.get("target_entity") in entity_names:
            return field
    for field in primary["fields"]:
        if field["type"] == "relation" and field.get("target_entity") in entity_names:
            return field
    return None


# --- string helpers ----------------------------------------------------------


_SNAKE_BOUNDARY = re.compile(r"(?<!^)(?=[A-Z])")
_NON_IDENT = re.compile(r"[^a-z0-9_]+")


def _snake(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = _SNAKE_BOUNDARY.sub("_", text)
    text = text.lower().replace("-", "_").replace(" ", "_")
    text = _NON_IDENT.sub("_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    if text and text[0].isdigit():
        text = f"x_{text}"
    return text or "entity"


def _page_name(entity_name: str) -> str:
    return _snake(_pluralize_token(entity_name))


def _pluralize(label: str) -> str:
    text = label.strip()
    if not text:
        return "Items"
    if text.endswith("s") or text.endswith("S"):
        return text
    if text.endswith("y") and len(text) > 1 and text[-2].lower() not in "aeiou":
        return text[:-1] + "ies"
    return text + "s"


def _pluralize_token(token: str) -> str:
    text = token.strip()
    if not text:
        return "items"
    if text.endswith("s"):
        return text
    if text.endswith("y") and len(text) > 1 and text[-2].lower() not in "aeiou":
        return text[:-1] + "ies"
    return text + "s"


__all__ = ["compile_blueprint_spec"]
