"""Adapter that turns an `AppRecipe` choice into a model-driven blueprint spec.

This is a deliberately thin bridge between the new deterministic seam
(`app_intent` -> `recipe_select` -> `app_shape`) and the existing scripted
planner inside `agentforge.planner.assistant`. The assistant's scripted keyword
chain still owns the prompts it already handles well; this adapter is only
consulted as a last resort, when the scripted chain would otherwise fall back
to the generic `_task_model()`.

No live LLM. No I/O. No randomness. Same prompt -> same spec dict.
"""
from __future__ import annotations

import re
from typing import Any

from agentforge.app_intent import IntentSpec, extract_intent
from agentforge.app_shape import AppShape, EntitySpec, FieldSpec, compile_app_shape
from agentforge.recipe_select import RecipeSelection, select_recipe
from agentforge.recipes import AppRecipe


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


def is_recipe_confident(text: str) -> bool:
    """Cheap check: does the scorer return a confident non-fallback recipe?

    Used by the assistant's clarification gate to bypass entity/field/workflow
    prompts when the recipe seam already understands the request. Skips the
    AppShape compilation step that `recipe_aware_spec` does.
    """
    if not (text or "").strip():
        return False
    intent = extract_intent(text)
    selection = select_recipe(intent)
    return selection.verdict == "confident" and not selection.picked.is_fallback


def recipe_metadata(text: str) -> dict[str, Any] | None:
    """Return recipe selection metadata for *any* prompt, or None if blank.

    Always reports the recipe the scorer would pick (including `generic_dashboard`
    fallback) so callers can attach it to the blueprint regardless of whether
    they chose to use the recipe-derived spec.
    """
    if not (text or "").strip():
        return None
    intent = extract_intent(text)
    selection = select_recipe(intent)
    shape = compile_app_shape(intent, selection.picked)
    return _metadata_payload(selection, shape)


def recipe_aware_spec(text: str) -> dict[str, Any] | None:
    """Return a model-driven spec built from the recipe registry, or None.

    Returns None when the recipe scorer is not confident in a non-fallback
    pick. Callers should keep their existing logic in that case so we never
    silently override prompts the scripted path handles well.
    """
    if not (text or "").strip():
        return None
    intent = extract_intent(text)
    selection = select_recipe(intent)
    if selection.verdict != "confident":
        return None
    recipe = selection.picked
    if recipe.is_fallback:
        return None
    shape = compile_app_shape(intent, recipe)
    return _spec_from_shape(shape)


def _spec_from_shape(shape: AppShape) -> dict[str, Any]:
    entities = [_pack_entity(entity) for entity in shape.entities]
    primary_name = _pick_primary(entities)
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
    actions = _actions_from_entities(entities)
    seed = _seed_from_entities(entities)
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


def _pack_entity(entity: EntitySpec) -> dict[str, Any]:
    snake = _snake(entity.name)
    label_singular = entity.label or entity.name
    label_plural = _pluralize(label_singular)
    fields = [_pack_field(field) for field in entity.fields]
    # Pack requires at least one field; recipes always declare some, but guard
    # against future empty templates by injecting a title field.
    if not fields:
        fields = [{"name": "title", "label": "Title", "type": "string", "required": True, "semantic": "title"}]
    # Ensure the first string field is marked as the semantic title for UI focus.
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


def _pick_primary(entities: list[dict[str, Any]]) -> str:
    for entity in entities:
        if any(field["type"] == "enum" and field["name"] == "status" for field in entity["fields"]):
            return entity["name"]
    return entities[0]["name"] if entities else ""


def _actions_from_entities(entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for entity in entities:
        status_field = next(
            (field for field in entity["fields"] if field["type"] == "enum" and field["name"] == "status"),
            None,
        )
        if not status_field:
            continue
        enum_values = list(status_field.get("enum_values") or [])
        terminal = _pick_terminal_status(enum_values)
        if not terminal:
            continue
        actions.append({
            "name": f"mark_{entity['name']}_{terminal}",
            "label": f"Mark {entity['label_singular'].lower()} {terminal.replace('_', ' ')}",
            "type": "update_status",
            "entity": entity["name"],
            "field": "status",
            "value": terminal,
        })
    return actions


_TERMINAL_PREFERENCE: tuple[str, ...] = (
    "completed", "complete", "done", "resolved", "closed", "approved", "paid",
    "received", "delivered", "won", "shipped",
)


def _pick_terminal_status(enum_values: list[str]) -> str | None:
    for candidate in _TERMINAL_PREFERENCE:
        if candidate in enum_values:
            return candidate
    return enum_values[-1] if enum_values else None


def _seed_from_entities(entities: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    seed: dict[str, list[dict[str, Any]]] = {}
    for entity in entities:
        row: dict[str, Any] = {}
        for field in entity["fields"]:
            if field["type"] == "relation":
                continue
            value = _sample_value(entity, field)
            if value is None:
                continue
            row[field["name"]] = value
        if row:
            seed[entity["name"]] = [row]
    return seed


def _sample_value(entity: dict[str, Any], field: dict[str, Any]) -> Any:
    semantic = field.get("semantic")
    name = field["name"]
    if field["type"] == "enum":
        return (field.get("enum_values") or ["pending"])[0]
    if field["type"] == "string":
        if semantic == "title" or name in {"title", "name"}:
            return f"Sample {entity['label_singular'].lower()}"
        return ""
    if field["type"] == "text":
        return f"Notes for the first {entity['label_singular'].lower()}."
    if field["type"] in {"integer", "boolean", "date"}:
        return None
    return None


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
    return {
        "composition": "standard",
        "recipe": "standard",
        "dashboard": {"title": "Dashboard", "primary_entity": primary_name, "cards": cards},
    }


def _metadata_payload(selection: RecipeSelection, shape: AppShape) -> dict[str, Any]:
    picked: AppRecipe = selection.picked
    return {
        "recipe_id": picked.id,
        "recipe_version": picked.version,
        "display_name": picked.display_name,
        "verdict": selection.verdict,
        "home_surface": shape.home_surface,
        "primary_workflow": shape.primary_workflow.label if shape.primary_workflow else None,
        "demo_moment": shape.demo_moment,
        "candidate_recipe_ids": [score.recipe_id for score in selection.candidates],
        "is_fallback": picked.is_fallback,
    }


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
    # Use plain pluralised entity name as page id (snake_case).
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


__all__ = ["is_recipe_confident", "recipe_aware_spec", "recipe_metadata"]
