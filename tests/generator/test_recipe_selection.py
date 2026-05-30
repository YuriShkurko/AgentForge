"""Tests for the deterministic recipe scorer in `agentforge.recipe_select`."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "generator"))

from agentforge.app_intent import extract_intent
from agentforge.recipe_select import (
    CONFIDENT_THRESHOLD,
    FALLBACK_THRESHOLD,
    RecipeSelection,
    select_recipe,
)
from agentforge.recipes import ALL_RECIPES, FALLBACK_RECIPE


def _select(prompt: str) -> RecipeSelection:
    return select_recipe(extract_intent(prompt))


def test_registry_contains_anchor_recipes():
    ids = {r.id for r in ALL_RECIPES}
    assert {"client_session_manager", "pipeline_kanban", "approval_review_queue", "inventory_asset_tracker", "generic_dashboard"}.issubset(ids)


def test_registry_has_exactly_one_fallback():
    fallbacks = [r for r in ALL_RECIPES if r.is_fallback]
    assert len(fallbacks) == 1
    assert fallbacks[0].id == FALLBACK_RECIPE.id


def test_basketball_coach_selects_client_session_manager():
    selection = _select(
        "I am a basketball coach, want to track clients, lessons, payments, and court vendors"
    )
    assert selection.picked.id == "client_session_manager"
    assert selection.verdict == "confident"
    assert selection.picked_score.score >= CONFIDENT_THRESHOLD


def test_vendor_risk_selects_approval_review_queue():
    selection = _select("I need to review vendor risk findings")
    assert selection.picked.id == "approval_review_queue"
    assert selection.verdict in {"confident", "ambiguous"}
    assert selection.picked_score.score >= FALLBACK_THRESHOLD


def test_job_applications_selects_pipeline_kanban():
    selection = _select("I want to manage job applications in a hiring pipeline")
    assert selection.picked.id == "pipeline_kanban"
    assert selection.verdict in {"confident", "ambiguous"}


def test_generic_prompt_falls_back_to_generic_dashboard():
    selection = _select("simple dashboard for random items")
    assert selection.picked.id == "generic_dashboard"
    assert selection.verdict == "fallback"


def test_unrelated_prompt_falls_back_to_generic_dashboard():
    selection = _select("xyzzy quux foobar")
    assert selection.picked.id == "generic_dashboard"
    assert selection.verdict == "fallback"


@pytest.mark.parametrize("prompt", [
    "I want a website to control my assets, houses and cash",
    "I manage livestock on a farm",
    "I need to track equipment, vendors, and maintenance",
    "I manage office inventory and reorder supplies",
])
def test_inventory_asset_prompts_select_inventory_asset_tracker(prompt):
    selection = _select(prompt)
    assert selection.picked.id == "inventory_asset_tracker"
    assert selection.verdict in {"confident", "ambiguous"}
    assert selection.picked_score.score >= FALLBACK_THRESHOLD


def test_repair_shop_jobs_customer_updates_is_pipeline_or_ambiguous():
    selection = _select("repair shop tracking jobs and customer updates")
    assert selection.picked.id == "pipeline_kanban" or selection.verdict == "ambiguous"
    if selection.verdict == "ambiguous":
        assert "pipeline_kanban" in {candidate.recipe_id for candidate in selection.candidates}


def test_repair_shop_parts_stock_reorder_selects_inventory():
    selection = _select("repair shop tracking parts, stock, inventory, reorder supplies")
    assert selection.picked.id == "inventory_asset_tracker"
    assert selection.verdict == "confident"


def test_repair_shop_jobs_parts_customer_updates_stays_ambiguous():
    selection = _select("I run a repair shop and need to track jobs, parts, and customer updates")
    assert selection.verdict == "ambiguous"
    assert {"inventory_asset_tracker", "pipeline_kanban"}.issubset({candidate.recipe_id for candidate in selection.candidates})


def test_ambiguous_prompt_returns_multiple_candidates():
    selection = _select("track jobs and customer updates")
    if selection.verdict == "ambiguous":
        assert 2 <= len(selection.candidates) <= 4


def test_scoring_reasons_are_traceable():
    selection = _select(
        "I am a basketball coach, want to track clients, lessons, payments, and court vendors"
    )
    top = selection.picked_score
    assert top.reasons, "expected non-empty reasons for the picked recipe"
    # The role hint or strong keyword should be present in evidence.
    reasons_text = " ".join(top.reasons)
    assert "role_hint" in reasons_text or "strong_keyword" in reasons_text


def test_all_scores_are_descending():
    selection = _select(
        "I am a basketball coach, want to track clients, lessons, payments, and court vendors"
    )
    scores = [s.score for s in selection.all_scores]
    assert scores == sorted(scores, reverse=True)


def test_anti_signal_suppresses_unrelated_recipe():
    # "kanban" is an anti-signal for client_session_manager.
    selection = _select("I want a kanban board for tracking clients")
    # client_session_manager should not win here even though "clients" matches.
    assert selection.picked.id != "client_session_manager"


def test_selection_is_deterministic():
    prompt = "I am a basketball coach, want to track clients, lessons, payments, and court vendors"
    a = select_recipe(extract_intent(prompt))
    b = select_recipe(extract_intent(prompt))
    assert a.picked.id == b.picked.id
    assert a.verdict == b.verdict
    assert tuple(s.score for s in a.all_scores) == tuple(s.score for s in b.all_scores)


@pytest.mark.parametrize("prompt", [
    "I am a basketball coach, want to track clients, lessons, payments, and court vendors",
    "I need to review vendor risk findings",
    "I want to manage job applications in a hiring pipeline",
    "I need to track equipment, vendors, and maintenance",
    "simple dashboard for random items",
])
def test_selection_always_picks_a_recipe(prompt):
    selection = _select(prompt)
    assert selection.picked is not None
    assert selection.picked.id in {r.id for r in ALL_RECIPES}
