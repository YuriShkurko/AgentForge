"""Deterministic guidance for Builder Assistant validation errors.

Phase 5: pattern-match raw ``DomainPack`` validation errors into structured
guidance entries the Builder can render alongside (never instead of) the raw
error text. No auto-applied fixes — every entry yields explanation +
suggested manual action and, when ambiguous, a targeted follow-up question.

Classification is offline and deterministic. The assistant never silently
rewrites a tampered Blueprint; the user must edit the proposal and click
Apply again to re-validate.
"""
from __future__ import annotations

import re
from typing import Any, Callable, Iterable


def summarize_validation_errors(errors: Iterable[str] | None) -> list[dict[str, Any]]:
    """Return one guidance entry per raw validation error string."""
    return [_classify(str(raw)) for raw in (errors or []) if str(raw).strip()]


def _classify(raw: str) -> dict[str, Any]:
    for pattern, category, builder in _PATTERNS:
        match = pattern.search(raw)
        if match:
            entry: dict[str, Any] = {"error": raw, "category": category}
            entry.update(builder(match))
            return entry
    return {
        "error": raw,
        "category": "unknown",
        "message": "Schema validation failed but the assistant did not recognize the error pattern.",
        "suggested_fix": "Review the raw error above, edit the Blueprint, and click Apply again to re-validate.",
    }


def _missing_relation(match: re.Match[str]) -> dict[str, Any]:
    field_path = match.group(1)
    target = match.group(2)
    return {
        "message": f"Relation field '{field_path}' points at an entity '{target}' that isn't defined.",
        "suggested_fix": (
            f"Add an entity named '{target}' to model.entities, or change relation '{field_path}' "
            "to reference an entity that already exists."
        ),
        "follow_up_question": f"Which existing entity should '{field_path}' reference?",
    }


def _missing_enum_values(match: re.Match[str]) -> dict[str, Any]:
    field_name = match.group(1)
    return {
        "message": f"Enum field '{field_name}' has no allowed values defined.",
        "suggested_fix": (
            f"Add an enum_values list to '{field_name}' (for example [\"open\", \"closed\"])."
        ),
        "follow_up_question": f"What allowed values should '{field_name}' accept?",
    }


def _invalid_enum_value(match: re.Match[str]) -> dict[str, Any]:
    action = match.group(1)
    allowed = match.group(2).strip()
    return {
        "message": (
            f"Action '{action}' wants to set a value that isn't in the allowed enum {allowed}."
        ),
        "suggested_fix": (
            f"Choose a value from {allowed} for action '{action}', or add the desired value to the "
            "field's enum_values list."
        ),
    }


def _update_status_field(match: re.Match[str]) -> dict[str, Any]:
    action = match.group(1)
    return {
        "message": f"Action '{action}' targets a non-enum field; update_status only works on enum fields.",
        "suggested_fix": (
            f"Point action '{action}' at an enum field, or convert the target field to type 'enum' "
            "with enum_values."
        ),
    }


def _github_provider_env(match: re.Match[str]) -> dict[str, Any]:
    provider = match.group(1)
    missing = match.group(2)
    return {
        "message": f"GitHub Issues provider '{provider}' is missing required env-var names: {missing}.",
        "suggested_fix": (
            f"Set env.token=GITHUB_TOKEN and env.repo=GITHUB_REPO on provider '{provider}'. The "
            "Builder stores env-var names only — do not paste real tokens."
        ),
    }


def _http_json_env(match: re.Match[str]) -> dict[str, Any]:
    provider = match.group(1)
    suggested = re.sub(r"[^A-Z0-9]+", "_", provider.upper()).strip("_") or "EXTERNAL"
    return {
        "message": f"HTTP JSON provider '{provider}' is missing an env.url placeholder.",
        "suggested_fix": (
            f"Set env.url on provider '{provider}' to an UPPER_SNAKE_CASE env var name "
            f"(for example {suggested}_URL)."
        ),
    }


def _bad_env_var_name(match: re.Match[str]) -> dict[str, Any]:
    field = match.group(1)
    raw_value = match.group(2)
    cleaned = re.sub(r"[^A-Z0-9_]+", "_", raw_value.upper()).strip("_") or "API_TOKEN"
    return {
        "message": f"Provider {field} value '{raw_value}' is not a valid env-var name.",
        "suggested_fix": (
            f"Use UPPER_SNAKE_CASE for {field} (for example {cleaned}). The Builder stores env-var "
            "names, never secret values."
        ),
    }


def _missing_target_import(match: re.Match[str]) -> dict[str, Any]:
    provider = match.group(1)
    target = match.group(2)
    return {
        "message": (
            f"Provider '{provider}' targets import '{target}' which is not declared in model.imports."
        ),
        "suggested_fix": (
            f"Either add an import with id '{target}' to model.imports, or change provider "
            f"'{provider}' target_import to an existing import id."
        ),
        "follow_up_question": f"Which import should provider '{provider}' write into?",
    }


def _target_import_required(_: re.Match[str]) -> dict[str, Any]:
    return {
        "message": "A provider was declared without a target_import.",
        "suggested_fix": "Set target_import on the provider to the id of an existing import.",
    }


def _ui_focus_field(match: re.Match[str]) -> dict[str, Any]:
    attr = match.group(1)
    field_name = match.group(2)
    entity = match.group(3)
    return {
        "message": (
            f"UI focus.{attr} points at field '{field_name}' which is not defined on entity '{entity}'."
        ),
        "suggested_fix": (
            f"Either add field '{field_name}' to entity '{entity}' or change focus.{attr} to an "
            "existing field on that entity."
        ),
    }


def _ui_entity_field(match: re.Match[str]) -> dict[str, Any]:
    entity = match.group(1)
    attr = match.group(2)
    field_name = match.group(3)
    return {
        "message": (
            f"UI display.{attr} on entity '{entity}' references unknown field '{field_name}'."
        ),
        "suggested_fix": (
            f"Point display.{attr} at an existing field on '{entity}', or add field '{field_name}'."
        ),
    }


def _ui_composition_requires_focus(match: re.Match[str]) -> dict[str, Any]:
    composition = match.group(1)
    return {
        "message": f"UI composition '{composition}' needs a focus.primary_entity.",
        "suggested_fix": (
            f"Set focus.primary_entity to the entity this composition should highlight, "
            "or switch composition to 'standard'."
        ),
    }


def _dashboard_primary_entity(match: re.Match[str]) -> dict[str, Any]:
    entity = match.group(1)
    return {
        "message": f"Dashboard primary_entity '{entity}' is not defined in model.entities.",
        "suggested_fix": (
            f"Add an entity named '{entity}' or change dashboard.primary_entity to an existing entity name."
        ),
    }


def _page_unknown_entity(match: re.Match[str]) -> dict[str, Any]:
    page = match.group(1)
    entity = match.group(2)
    return {
        "message": f"Page '{page}' references entity '{entity}' which is not defined.",
        "suggested_fix": (
            f"Add entity '{entity}' to model.entities, or update page '{page}' to reference an existing entity."
        ),
    }


def _action_unknown_entity(match: re.Match[str]) -> dict[str, Any]:
    action = match.group(1)
    entity = match.group(2)
    return {
        "message": f"Action '{action}' references unknown entity '{entity}'.",
        "suggested_fix": (
            f"Point action '{action}' at an existing entity, or add entity '{entity}' to model.entities."
        ),
    }


def _import_upsert_field(match: re.Match[str]) -> dict[str, Any]:
    import_id = match.group(1)
    field_name = match.group(2)
    return {
        "message": f"Import '{import_id}' upsert_key '{field_name}' is not a field on the target entity.",
        "suggested_fix": (
            f"Set upsert_key on import '{import_id}' to an existing field name "
            "(for example 'title' or 'external_id')."
        ),
    }


def _import_field_map_target(match: re.Match[str]) -> dict[str, Any]:
    import_id = match.group(1)
    field_name = match.group(2)
    return {
        "message": f"Import '{import_id}' field_map points at unknown target field '{field_name}'.",
        "suggested_fix": (
            f"Either map to an existing field on the target entity, or add field '{field_name}'."
        ),
    }


def _duplicate_entities(_: re.Match[str]) -> dict[str, Any]:
    return {
        "message": "Two or more entities share the same name.",
        "suggested_fix": "Rename one of the duplicate entities to a unique snake_case identifier.",
    }


def _missing_entity(_: re.Match[str]) -> dict[str, Any]:
    return {
        "message": "model_driven_app has no entities.",
        "suggested_fix": (
            "Add at least one entity with name, label_singular, label_plural, and at least one field."
        ),
        "follow_up_question": "What entity should this app manage?",
    }


def _missing_blueprint(_: re.Match[str]) -> dict[str, Any]:
    return {
        "message": "The apply request is missing a Blueprint object.",
        "suggested_fix": (
            "Re-run the assistant start or message endpoint to produce a Blueprint proposal, "
            "then click Apply."
        ),
    }


_BUILDERS: list[tuple[str, str, Callable[[re.Match[str]], dict[str, Any]]]] = [
    (r"relation field '(.+?)' targets unknown entity '(.+?)'", "missing_relation_target", _missing_relation),
    (r"enum field '(.+?)' must define enum_values", "missing_enum_values", _missing_enum_values),
    (r"update_status action '(.+?)' value must be one of (.+)", "invalid_enum_value", _invalid_enum_value),
    (r"update_status action '(.+?)' field must be enum", "invalid_enum_value", _update_status_field),
    (r"github_issues provider '(.+?)' requires (.+)", "bad_provider_env", _github_provider_env),
    (r"http_json provider '(.+?)' requires env\.url", "bad_provider_env", _http_json_env),
    (r"provider (env\.\w+) must be an UPPER_SNAKE_CASE env var name; got '(.+?)'", "bad_provider_env", _bad_env_var_name),
    (r"provider '(.+?)' target_import references unknown import '(.+?)'", "missing_target_import", _missing_target_import),
    (r"provider target_import is required", "missing_target_import", _target_import_required),
    (r"ui focus (\w+) references unknown field '(.+?)' on '(.+?)'", "unsupported_ui_field", _ui_focus_field),
    (r"ui entity '(.+?)' (\w+) references unknown field '(.+?)'", "unsupported_ui_field", _ui_entity_field),
    (r"ui composition '(.+?)' requires focus\.primary_entity", "unsupported_ui_field", _ui_composition_requires_focus),
    (r"dashboard primary_entity references unknown entity '(.+?)'", "unknown_entity_reference", _dashboard_primary_entity),
    (r"page '(.+?)' references unknown entity '(.+?)'", "unknown_entity_reference", _page_unknown_entity),
    (r"action '(.+?)' references unknown entity '(.+?)'", "unknown_entity_reference", _action_unknown_entity),
    (r"import '(.+?)' upsert_key references unknown field '(.+?)'", "unknown_import_field", _import_upsert_field),
    (r"import '(.+?)' field_map target field '(.+?)' is not defined", "unknown_import_field", _import_field_map_target),
    (r"model_driven_app entity names must be unique", "duplicate_entity_names", _duplicate_entities),
    (r"model_driven_app requires at least one entity", "missing_entity", _missing_entity),
    (r"assistant proposal must include a blueprint", "missing_blueprint", _missing_blueprint),
]


_PATTERNS: list[tuple[re.Pattern[str], str, Callable[[re.Match[str]], dict[str, Any]]]] = [
    (re.compile(pattern), category, builder) for pattern, category, builder in _BUILDERS
]


__all__ = ["summarize_validation_errors"]
