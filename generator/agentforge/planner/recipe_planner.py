"""Recipe-aware planner glue between the assistant and the recipe seam.

The actual conversion from `AppShape` to a model-driven blueprint spec lives
in `agentforge.app_shape_blueprint.compile_blueprint_spec`. This module is the
thin choice-maker: extract intent, score recipes, decide whether the recipe
path should win for *this* prompt, and hand off to the compiler.

No live LLM. No I/O. No randomness. Same prompt -> same output.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from agentforge.app_intent import extract_intent
from agentforge.app_shape import compile_app_shape
from agentforge.app_shape_blueprint import compile_blueprint_spec
from agentforge.recipe_select import FALLBACK_THRESHOLD, RecipeScore, RecipeSelection, select_recipe
from agentforge.recipes import AppRecipe, get_recipe


@dataclass(frozen=True)
class RecipeDirectionChoice:
    """One deterministic planning direction offered before Blueprint drafting."""

    recipe_id: str
    display_name: str
    summary: str
    score: int


def is_recipe_confident(text: str) -> bool:
    """Cheap check: does the scorer return a confident non-fallback recipe?

    Used by the assistant's clarification gate to bypass entity/field/workflow
    prompts when the recipe seam already understands the request. Skips the
    AppShape compilation step that `recipe_aware_spec` does.
    """
    if planning_direction_choices(text):
        return False
    selection = _selection_for(text)
    return selection is not None and selection.verdict == "confident" and not selection.picked.is_fallback


def planning_direction_choices(text: str) -> tuple[RecipeDirectionChoice, ...]:
    """Return deterministic recipe choices when a prompt should ask direction first."""
    selection = _selection_for(text)
    if selection is None:
        return ()
    scores = _forced_composite_scores(text, selection)
    if not scores and selection.verdict == "ambiguous":
        scores = tuple(
            score for score in selection.candidates
            if score.score >= FALLBACK_THRESHOLD and not score.recipe.is_fallback
        )
    if len(scores) < 2:
        return ()
    return tuple(
        RecipeDirectionChoice(
            recipe_id=score.recipe.id,
            display_name=score.recipe.display_name,
            summary=score.recipe.summary,
            score=score.score,
        )
        for score in scores[:4]
    )


def recipe_aware_spec(text: str) -> dict[str, Any] | None:
    """Return a model-driven spec compiled from the recipe registry, or None.

    Returns None when the recipe scorer is not confident in a non-fallback
    pick. Callers should keep their existing logic in that case so we never
    silently override prompts the scripted path handles well.
    """
    if planning_direction_choices(text):
        return None
    selection = _selection_for(text)
    if selection is None or selection.verdict != "confident":
        return None
    recipe = selection.picked
    if recipe.is_fallback:
        return None
    return recipe_aware_spec_for_recipe(text, recipe.id)


def recipe_aware_spec_for_recipe(text: str, recipe_id: str) -> dict[str, Any] | None:
    """Compile a model-driven spec for an explicit user-selected recipe."""
    try:
        recipe = get_recipe(recipe_id)
    except KeyError:
        return None
    if recipe.is_fallback:
        return None
    intent = extract_intent(text)
    shape = compile_app_shape(intent, recipe)
    return compile_blueprint_spec(shape, recipe)


def recipe_metadata_for_recipe(text: str, recipe_id: str, selection: RecipeSelection | None = None) -> dict[str, Any] | None:
    """Return metadata for an explicit recipe choice."""
    try:
        recipe = get_recipe(recipe_id)
    except KeyError:
        return None
    intent = extract_intent(text)
    shape = compile_app_shape(intent, recipe)
    if selection is None:
        selection = RecipeSelection(
            picked=recipe,
            candidates=(),
            verdict="selected",
            all_scores=(),
        )
    return _metadata_payload(selection, shape.home_surface, shape.primary_workflow, shape.demo_moment, picked_override=recipe)


def recipe_metadata(text: str) -> dict[str, Any] | None:
    """Return recipe selection metadata for any prompt, or None if blank.

    Always reports the recipe the scorer would pick (including the
    `generic_dashboard` fallback) so callers can attach it to the blueprint
    regardless of whether they chose to use the recipe-derived spec.
    """
    selection = _selection_for(text)
    if selection is None:
        return None
    intent = extract_intent(text)
    shape = compile_app_shape(intent, selection.picked)
    return _metadata_payload(selection, shape.home_surface, shape.primary_workflow, shape.demo_moment)


def _selection_for(text: str) -> RecipeSelection | None:
    if not (text or "").strip():
        return None
    intent = extract_intent(text)
    return select_recipe(intent)


def _forced_composite_scores(text: str, selection: RecipeSelection) -> tuple[RecipeScore, ...]:
    """Catch clear composite prompts whose top recipe score hides a second direction."""
    compact = f" {re.sub(r'[^a-z0-9]+', ' ', str(text or '').lower()).strip()} "
    if not _has_any(compact, ("repair shop", "repair", "workshop", "garage")):
        return ()
    has_job_pipeline = _has_any(compact, (" job ", " jobs ", " customer ", " customers ", " update ", " updates ", " status ", " pipeline "))
    has_inventory = _has_any(compact, (" part ", " parts ", " inventory ", " stock ", " vendor ", " vendors ", " reorder ", " maintenance ", " supplier ", " suppliers "))
    if not (has_job_pipeline and has_inventory):
        return ()
    by_id = {score.recipe_id: score for score in selection.all_scores}
    pipeline = by_id.get("pipeline_kanban")
    inventory = by_id.get("inventory_asset_tracker")
    if not pipeline or not inventory:
        return ()
    if pipeline.score < FALLBACK_THRESHOLD or inventory.score < FALLBACK_THRESHOLD:
        return ()
    return (pipeline, inventory)


def _has_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _metadata_payload(
    selection: RecipeSelection,
    home_surface: str,
    primary_workflow: Any,
    demo_moment: str,
    *,
    picked_override: AppRecipe | None = None,
) -> dict[str, Any]:
    picked: AppRecipe = picked_override or selection.picked
    return {
        "recipe_id": picked.id,
        "recipe_version": picked.version,
        "display_name": picked.display_name,
        "verdict": selection.verdict,
        "home_surface": home_surface,
        "primary_workflow": primary_workflow.label if primary_workflow else None,
        "demo_moment": demo_moment,
        "candidate_recipe_ids": [score.recipe_id for score in selection.candidates] or [picked.id],
        "is_fallback": picked.is_fallback,
    }


__all__ = [
    "RecipeDirectionChoice",
    "is_recipe_confident",
    "planning_direction_choices",
    "recipe_aware_spec",
    "recipe_aware_spec_for_recipe",
    "recipe_metadata",
    "recipe_metadata_for_recipe",
]
