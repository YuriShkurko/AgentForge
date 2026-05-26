"""Tests for `agentforge.app_shape.compile_app_shape`."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "generator"))

from agentforge.app_intent import extract_intent
from agentforge.app_shape import AppShape, compile_app_shape
from agentforge.recipe_select import select_recipe
from agentforge.recipes import ALL_RECIPES, FALLBACK_RECIPE, get_recipe


def _shape_for(prompt: str) -> AppShape:
    intent = extract_intent(prompt)
    selection = select_recipe(intent)
    return compile_app_shape(intent, selection.picked)


def test_app_shape_carries_recipe_id_and_version():
    shape = _shape_for(
        "I am a basketball coach, want to track clients, lessons, payments, and court vendors"
    )
    assert shape.recipe_id == "client_session_manager"
    assert shape.recipe_version == 1


def test_app_shape_has_entities_and_workflows():
    shape = _shape_for("I am a basketball coach tracking clients and lessons")
    assert len(shape.entities) >= 2
    assert len(shape.workflows) >= 1
    assert shape.primary_workflow is not None


def test_app_shape_screens_include_home_and_per_entity_detail():
    shape = _shape_for("I am a basketball coach tracking clients and lessons")
    kinds = [s.kind for s in shape.screens]
    assert "home" in kinds
    detail_entities = {s.entity for s in shape.screens if s.kind == "detail"}
    entity_names = {e.name for e in shape.entities}
    assert detail_entities == entity_names


def test_app_shape_home_surface_matches_recipe():
    shape = _shape_for("I am a basketball coach tracking clients and lessons")
    assert shape.home_surface == "split"

    shape_board = compile_app_shape(
        extract_intent("manage a hiring pipeline of candidates"),
        get_recipe("pipeline_kanban"),
    )
    assert shape_board.home_surface == "board"

    shape_queue = compile_app_shape(
        extract_intent("review vendor risk findings"),
        get_recipe("approval_review_queue"),
    )
    assert shape_queue.home_surface == "queue"


def test_app_shape_purpose_uses_jtbd_when_available():
    shape = _shape_for(
        "I am a basketball coach, want to track clients, lessons, payments, and court vendors"
    )
    # Either form is fine; purpose must mention recipe name.
    assert shape.recipe_id == "client_session_manager"
    assert "Client" in shape.purpose or "client" in shape.purpose.lower()


def test_app_shape_sample_data_plan_includes_recipe_counts():
    shape = _shape_for("I am a basketball coach tracking clients and lessons")
    counts = dict(shape.sample_data_plan.per_entity_counts)
    assert counts.get("Client", 0) >= 1
    assert counts.get("Session", 0) >= 1


def test_app_shape_demo_moment_is_non_empty():
    shape = _shape_for("I am a basketball coach tracking clients and lessons")
    assert shape.demo_moment
    assert len(shape.demo_moment) > 10


def test_app_shape_records_fallback_note():
    shape = _shape_for("xyzzy quux foobar")
    assert shape.recipe_id == FALLBACK_RECIPE.id
    assert any("fallback" in n.lower() for n in shape.notes)


def test_app_shape_records_vague_note_for_vague_intent():
    intent = extract_intent("an app")
    shape = compile_app_shape(intent, FALLBACK_RECIPE)
    assert any("vague" in n.lower() for n in shape.notes)


def test_app_shape_is_deterministic():
    a = _shape_for("I am a basketball coach tracking clients and lessons")
    b = _shape_for("I am a basketball coach tracking clients and lessons")
    assert a.to_dict() == b.to_dict()


def test_app_shape_to_dict_is_json_serializable():
    import json

    shape = _shape_for("I am a basketball coach tracking clients and lessons")
    payload = json.dumps(shape.to_dict())
    assert "client_session_manager" in payload


@pytest.mark.parametrize("recipe", ALL_RECIPES)
def test_compile_app_shape_works_for_every_anchor_recipe(recipe):
    intent = extract_intent("manage a small workflow")
    shape = compile_app_shape(intent, recipe)
    assert shape.recipe_id == recipe.id
    assert shape.entities  # every anchor recipe declares at least one entity
    assert shape.home_surface == recipe.home_surface
