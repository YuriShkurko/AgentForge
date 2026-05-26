"""Tests for the deterministic AppShape -> blueprint spec compiler.

Validates the four anchor recipes end-to-end through the compiler: entities
are translated into pack-schema-valid model entities, recipe workflow effects
that flip an enum status become `update_status` actions, seed-data counts
honour the recipe's sample_data_style, and UI composition promotes a status
enum to `board_workspace` when one exists.

The compiler output also wraps cleanly into a DomainPack via the existing
starter helpers (proven in the assistant integration tests); here we focus on
shape and determinism so failures point at the compiler, not the assistant.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "generator"))

from agentforge.app_intent import extract_intent
from agentforge.app_shape import compile_app_shape
from agentforge.app_shape_blueprint import compile_blueprint_spec
from agentforge.recipes import (
    APPROVAL_REVIEW_QUEUE,
    CLIENT_SESSION_MANAGER,
    GENERIC_DASHBOARD,
    PIPELINE_KANBAN,
    AppRecipe,
)


def _spec(recipe: AppRecipe, prompt: str = "manage a small workflow") -> dict:
    intent = extract_intent(prompt)
    shape = compile_app_shape(intent, recipe)
    return compile_blueprint_spec(shape, recipe)


def _entity_names(spec: dict) -> set[str]:
    return {entity["name"] for entity in spec["model"]["entities"]}


def _action_names(spec: dict) -> set[str]:
    return {action["name"] for action in spec["model"]["actions"]}


# --- client_session_manager --------------------------------------------------


def test_client_session_manager_compiles_clients_sessions_payments():
    spec = _spec(CLIENT_SESSION_MANAGER, "i am a tutor scheduling student sessions")
    assert spec["primary"] == "session"
    assert _entity_names(spec) == {"client", "session", "payment"}


def test_client_session_manager_session_has_status_enum_and_actions():
    spec = _spec(CLIENT_SESSION_MANAGER)
    session = next(entity for entity in spec["model"]["entities"] if entity["name"] == "session")
    status_field = next(field for field in session["fields"] if field["name"] == "status")
    assert status_field["type"] == "enum"
    assert "completed" in status_field["enum_values"]
    actions = _action_names(spec)
    assert "mark_session_completed" in actions
    # schedule_session sets status=scheduled (an enum value), so it should map too.
    assert "schedule_session" in actions


def test_client_session_manager_ui_is_board_workspace_grouped_by_status():
    spec = _spec(CLIENT_SESSION_MANAGER)
    ui = spec["model"]["ui"]
    assert ui["composition"] == "board_workspace"
    assert ui["focus"]["primary_entity"] == "session"
    assert ui["focus"]["group_by"] == "status"


# --- pipeline_kanban ---------------------------------------------------------


def test_pipeline_kanban_compiles_stage_card_owner():
    spec = _spec(PIPELINE_KANBAN, "I want to manage job applications")
    assert _entity_names(spec) == {"stage", "card", "owner"}


def test_pipeline_kanban_skips_actions_when_no_enum_status():
    # Card's stage is a relation, not an enum status, so no update_status
    # action should be invented. We never want to fabricate enum fields.
    spec = _spec(PIPELINE_KANBAN)
    assert spec["model"]["actions"] == []


def test_pipeline_kanban_falls_back_to_standard_ui_without_status_enum():
    spec = _spec(PIPELINE_KANBAN)
    ui = spec["model"]["ui"]
    assert ui["composition"] == "standard"
    # Primary is the workflow's target entity (Card), even without status enum.
    assert spec["primary"] == "card"


# --- approval_review_queue ---------------------------------------------------


def test_approval_review_queue_compiles_item_reviewer_decision():
    spec = _spec(APPROVAL_REVIEW_QUEUE, "review vendor risk findings")
    assert _entity_names(spec) == {"item", "reviewer", "decision"}
    assert spec["primary"] == "item"


def test_approval_review_queue_maps_each_workflow_to_an_update_status_action():
    spec = _spec(APPROVAL_REVIEW_QUEUE)
    actions = _action_names(spec)
    # Each workflow's effect names an Item.status transition.
    assert {"claim_item", "approve", "reject", "request_changes"}.issubset(actions)
    # Every action targets the item entity.
    for action in spec["model"]["actions"]:
        assert action["entity"] == "item"
        assert action["field"] == "status"
        assert action["type"] == "update_status"


def test_approval_review_queue_ui_groups_item_by_status():
    spec = _spec(APPROVAL_REVIEW_QUEUE)
    ui = spec["model"]["ui"]
    assert ui["composition"] == "board_workspace"
    assert ui["focus"]["primary_entity"] == "item"
    assert ui["focus"]["group_by"] == "status"


# --- generic_dashboard fallback ----------------------------------------------


def test_generic_dashboard_compiles_single_item_entity():
    spec = _spec(GENERIC_DASHBOARD, "manage records")
    assert _entity_names(spec) == {"item"}
    # No status enum on Item, so composition stays standard.
    assert spec["model"]["ui"]["composition"] == "standard"


# --- seed data honours per_entity_counts -------------------------------------


def test_seed_data_uses_recipe_per_entity_counts():
    spec = _spec(APPROVAL_REVIEW_QUEUE)
    seed = spec["model"]["seed_data"]
    # approval_review_queue declares Item:5, Reviewer:2, Decision:1.
    assert len(seed["item"]) == 5
    assert len(seed["reviewer"]) == 2
    # Enum values cycle across rows so we never emit an invalid value.
    item_statuses = {row["status"] for row in seed["item"]}
    enum_values = next(
        field["enum_values"]
        for entity in spec["model"]["entities"]
        if entity["name"] == "item"
        for field in entity["fields"]
        if field["name"] == "status"
    )
    assert item_statuses.issubset(set(enum_values))


def test_seed_data_skips_relation_fields():
    spec = _spec(CLIENT_SESSION_MANAGER)
    for entity in spec["model"]["entities"]:
        relation_names = {field["name"] for field in entity["fields"] if field["type"] == "relation"}
        for row in spec["model"]["seed_data"].get(entity["name"], []):
            assert relation_names.isdisjoint(row.keys())


# --- determinism + JSON roundtrip --------------------------------------------


@pytest.mark.parametrize("recipe", [CLIENT_SESSION_MANAGER, PIPELINE_KANBAN, APPROVAL_REVIEW_QUEUE, GENERIC_DASHBOARD])
def test_compile_blueprint_spec_is_deterministic(recipe):
    a = _spec(recipe)
    b = _spec(recipe)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


@pytest.mark.parametrize("recipe", [CLIENT_SESSION_MANAGER, PIPELINE_KANBAN, APPROVAL_REVIEW_QUEUE, GENERIC_DASHBOARD])
def test_compile_blueprint_spec_pages_include_dashboard_and_per_entity_list(recipe):
    spec = _spec(recipe)
    page_types = [page["type"] for page in spec["model"]["pages"]]
    assert page_types[0] == "dashboard"
    entity_lists = {page["entity"] for page in spec["model"]["pages"] if page["type"] == "entity_list"}
    assert entity_lists == _entity_names(spec)


@pytest.mark.parametrize("recipe", [CLIENT_SESSION_MANAGER, PIPELINE_KANBAN, APPROVAL_REVIEW_QUEUE, GENERIC_DASHBOARD])
def test_compile_blueprint_spec_no_unsupported_pack_field_types(recipe):
    valid_types = {"string", "text", "integer", "boolean", "date", "enum", "relation"}
    spec = _spec(recipe)
    for entity in spec["model"]["entities"]:
        for field in entity["fields"]:
            assert field["type"] in valid_types, f"{entity['name']}.{field['name']} -> {field['type']}"
