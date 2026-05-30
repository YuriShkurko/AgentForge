"""Recipe-aware planner glue between the assistant and the recipe seam.

The actual conversion from `AppShape` to a model-driven blueprint spec lives
in `agentforge.app_shape_blueprint.compile_blueprint_spec`. This module is the
thin choice-maker: extract intent, score recipes, decide whether the recipe
path should win for *this* prompt, and hand off to the compiler.

No live LLM. No I/O. No randomness. Same prompt -> same output.
"""
from __future__ import annotations

from typing import Any

from agentforge.app_intent import extract_intent
from agentforge.app_shape import compile_app_shape
from agentforge.app_shape_blueprint import compile_blueprint_spec
from agentforge.recipe_select import RecipeSelection, select_recipe
from agentforge.recipes import AppRecipe, get_recipe


def is_recipe_confident(text: str) -> bool:
    """Cheap check: does the scorer return a confident non-fallback recipe?

    Used by the assistant's clarification gate to bypass entity/field/workflow
    prompts when the recipe seam already understands the request. Skips the
    AppShape compilation step that `recipe_aware_spec` does.
    """
    selection = _selection_for(text)
    return selection is not None and selection.verdict == "confident" and not selection.picked.is_fallback


def recipe_aware_spec(text: str) -> dict[str, Any] | None:
    """Return a model-driven spec compiled from the recipe registry, or None.

    Returns None when the recipe scorer is not confident in a non-fallback
    pick. Callers should keep their existing logic in that case so we never
    silently override prompts the scripted path handles well.
    """
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


__all__ = ["is_recipe_confident", "recipe_aware_spec", "recipe_aware_spec_for_recipe", "recipe_metadata", "recipe_metadata_for_recipe"]
