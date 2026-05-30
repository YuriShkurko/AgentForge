"""Experience registry scaffold checks."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "generator"))

from agentforge.experience import (
    choose_experience_for_recipe,
    get_primitive,
    list_experience_primitives,
    list_experience_recipes,
)


_SNAKE_CASE_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def test_registry_contains_initial_experience_targets() -> None:
    experience_ids = {experience.experience_id for experience in list_experience_recipes()}
    assert experience_ids == {"client_workspace", "pipeline_board", "inventory_ops"}


def test_registry_ids_are_stable_snake_case() -> None:
    primitive_ids = [primitive.primitive_id for primitive in list_experience_primitives()]
    experience_ids = [experience.experience_id for experience in list_experience_recipes()]

    assert len(primitive_ids) == len(set(primitive_ids))
    assert len(experience_ids) == len(set(experience_ids))
    assert all(_SNAKE_CASE_RE.fullmatch(primitive_id) for primitive_id in primitive_ids)
    assert all(_SNAKE_CASE_RE.fullmatch(experience_id) for experience_id in experience_ids)


def test_every_experience_references_existing_primitive() -> None:
    primitive_ids = {primitive.primitive_id for primitive in list_experience_primitives()}

    for experience in list_experience_recipes():
        assert experience.primitive_id in primitive_ids


def test_every_experience_declares_suitable_recipe_ids() -> None:
    for experience in list_experience_recipes():
        assert experience.suitable_recipe_ids


def test_primitive_required_roles_are_expected_roles() -> None:
    for primitive in list_experience_primitives():
        assert set(primitive.required_roles).issubset(set(primitive.expected_roles))


def test_recipe_ids_choose_expected_experiences() -> None:
    assert choose_experience_for_recipe("client_session_manager").experience_id == "client_workspace"  # type: ignore[union-attr]
    assert choose_experience_for_recipe("pipeline_kanban").experience_id == "pipeline_board"  # type: ignore[union-attr]
    assert choose_experience_for_recipe("inventory_asset_tracker").experience_id == "inventory_ops"  # type: ignore[union-attr]


def test_unknown_recipe_id_returns_none() -> None:
    assert choose_experience_for_recipe("unknown_recipe") is None


def test_registry_serializes_to_json_compatible_dicts() -> None:
    payload = {
        "primitives": [
            primitive.to_dict()
            for primitive in list_experience_primitives()
        ],
        "experiences": [
            experience.to_dict()
            for experience in list_experience_recipes()
        ],
    }

    assert get_primitive("client_workspace") is not None
    json.dumps(payload, sort_keys=True)
