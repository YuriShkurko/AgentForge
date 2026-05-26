"""Builder Assistant integration tests for the recipe seam.

These prove that the deterministic intent/recipe/AppShape pipeline (added in
the previous slice) is wired into the assistant's model-driven proposals
without regressing scripted-domain prompts. The recipe seam is consulted only
after the existing keyword chain falls through, and recipe selection metadata
is stamped onto every model-driven blueprint's `future_extensions`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "generator"))

from agentforge.pack import DomainPack
from agentforge.planner.assistant import BuilderAssistant


def _propose(prompt: str) -> dict:
    return BuilderAssistant().start(prompt)


def _blueprint(prompt: str) -> dict:
    result = _propose(prompt)
    assert result["status"] == "proposed", result
    return result["proposal"]["blueprint"]


def _recipe_meta(prompt: str) -> dict:
    blueprint = _blueprint(prompt)
    meta = blueprint.get("future_extensions", {}).get("recipe")
    assert isinstance(meta, dict), f"missing recipe metadata; got {blueprint.get('future_extensions')}"
    return meta


# --- new prompts that bypass the scripted chain and exercise the recipe seam --


def test_assistant_recipe_pipeline_prompt():
    blueprint = _blueprint("I want to manage job applications")
    pack = DomainPack.model_validate(blueprint)
    assert pack.model is not None
    entity_names = {entity.name for entity in pack.model.entities}
    # The recipe seam should pick pipeline_kanban and use its entity templates
    # rather than the generic Item/task fallback.
    assert entity_names != {"task"}
    assert entity_names != {"item"}
    assert {"stage", "card", "owner"}.issubset(entity_names)
    meta = blueprint["future_extensions"]["recipe"]
    assert meta["recipe_id"] == "pipeline_kanban"
    assert meta["verdict"] == "confident"


def test_assistant_recipe_approval_queue_prompt():
    blueprint = _blueprint(
        "I run an approval workflow for submissions to review and claim items pending decisions"
    )
    pack = DomainPack.model_validate(blueprint)
    assert pack.model is not None
    entity_names = {entity.name for entity in pack.model.entities}
    assert {"item", "reviewer", "decision"}.issubset(entity_names)
    meta = blueprint["future_extensions"]["recipe"]
    assert meta["recipe_id"] == "approval_review_queue"
    assert meta["verdict"] == "confident"
    # Approval queue exposes an enum status on the primary item, so the
    # adapter should produce a board_workspace composition with status group_by.
    assert pack.model.ui.composition == "board_workspace"
    assert pack.model.ui.focus.primary_entity == "item"
    assert pack.model.ui.focus.group_by == "status"


def test_assistant_recipe_client_session_prompt_bypasses_scripted():
    # "tutor" doesn't trigger the scripted coach/teacher/gym/designer branches,
    # so the recipe seam should fire and produce client_session_manager entities.
    blueprint = _blueprint("i am a tutor scheduling student sessions and logging payments")
    pack = DomainPack.model_validate(blueprint)
    assert pack.model is not None
    entity_names = {entity.name for entity in pack.model.entities}
    assert {"client", "session", "payment"}.issubset(entity_names)
    meta = blueprint["future_extensions"]["recipe"]
    assert meta["recipe_id"] == "client_session_manager"
    assert meta["verdict"] == "confident"


# --- metadata is stamped on every proposal, not just recipe-driven ones --------


def test_recipe_metadata_stamped_on_scripted_proposals():
    # Basketball coach is handled by the scripted coach_booking_model, but the
    # recipe scorer should still report client_session_manager and that should
    # be visible in future_extensions.recipe.
    blueprint = _blueprint(
        "I am a basketball coach, want to track clients, lessons, payments, and court vendors"
    )
    meta = blueprint["future_extensions"]["recipe"]
    assert meta["recipe_id"] == "client_session_manager"
    assert meta["verdict"] == "confident"
    assert meta["home_surface"] == "split"
    assert "candidate_recipe_ids" in meta


def test_recipe_metadata_stamped_on_vendor_risk_proposal():
    blueprint = _blueprint("vendor risk register to review findings with severity status owner")
    meta = blueprint["future_extensions"]["recipe"]
    assert meta["recipe_id"] == "approval_review_queue"
    assert meta["home_surface"] == "queue"


def test_recipe_metadata_is_deterministic():
    prompt = "I want to manage job applications"
    a = _recipe_meta(prompt)
    b = _recipe_meta(prompt)
    assert a == b


# --- vague prompts still ask clarifying questions, no recipe override ---------


def test_vague_prompt_still_asks_clarification_no_recipe_override():
    result = _propose("app")
    assert result["status"] == "needs_clarification"
    assert result["proposal"] is None


def test_generic_dashboard_prompt_does_not_force_recipe_override():
    # Generic prompts that hit the scripted task fallback should leave the
    # generic task_model in place (recipe seam returns None for non-confident
    # picks / fallback recipes).
    blueprint = _blueprint("task tracker with status owner due date to complete tasks")
    pack = DomainPack.model_validate(blueprint)
    assert pack.model is not None
    entity_names = {entity.name for entity in pack.model.entities}
    # Existing scripted task model wins; recipe seam must not replace it.
    assert entity_names == {"task"}
    meta = blueprint["future_extensions"]["recipe"]
    # Recipe metadata is still stamped (for tooling/UI), but the picked recipe
    # is generic_dashboard or a low-confidence non-fallback — either way the
    # actual spec stays scripted.
    assert "recipe_id" in meta


# --- regression: existing good prompts still validate end-to-end --------------


def test_assistant_recipe_approval_queue_includes_decision_actions():
    blueprint = _blueprint(
        "I run an approval workflow for submissions to review and claim items pending decisions"
    )
    pack = DomainPack.model_validate(blueprint)
    assert pack.model is not None
    action_names = {action.name for action in pack.model.actions}
    # The compiler maps each Item-status workflow effect to an update_status action.
    assert {"claim_item", "approve", "reject", "request_changes"}.issubset(action_names)


def test_assistant_recipe_client_session_includes_session_actions():
    blueprint = _blueprint("i am a tutor scheduling student sessions and logging payments")
    pack = DomainPack.model_validate(blueprint)
    assert pack.model is not None
    action_names = {action.name for action in pack.model.actions}
    assert "mark_session_completed" in action_names


def test_assistant_recipe_seed_data_uses_recipe_counts():
    blueprint = _blueprint(
        "I run an approval workflow for submissions to review and claim items pending decisions"
    )
    seed = blueprint["model"]["seed_data"]
    # approval_review_queue.sample_data_style declares Item:5.
    assert len(seed["item"]) == 5


@pytest.mark.parametrize(
    ("prompt", "expected_entities"),
    [
        ("i am a basketball coach, want to track clients and court vendors", {"client", "court_vendor", "lesson_session"}),
        ("i am a music teacher need to track clients, earnings and vendors for equipments", {"client", "equipment_vendor", "lesson_session", "earning"}),
        ("freelance designer tracking clients projects invoices", {"client", "project", "invoice"}),
        ("small gym tracking members classes trainers payments", {"member", "class_session", "trainer", "payment"}),
        ("client onboarding app to manage clients and onboarding tasks with status, owner, and due dates", {"client", "onboarding_task"}),
        ("vendor risk register to review findings with severity status owner", {"vendor", "risk_finding"}),
        ("support ticket triage with title, status, priority, owner, and notes to close tickets", {"ticket"}),
    ],
)
def test_existing_good_prompts_still_propose_their_scripted_entities(prompt, expected_entities):
    blueprint = _blueprint(prompt)
    pack = DomainPack.model_validate(blueprint)
    assert pack.model is not None
    entity_names = {entity.name for entity in pack.model.entities}
    assert expected_entities.issubset(entity_names)
