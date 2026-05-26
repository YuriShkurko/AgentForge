"""AgentForge recipe registry.

Recipes are pure data: a deterministic bundle of selection signals plus the
entity, field, workflow, home-surface, and sample-data defaults the planner
uses when a recipe is picked. Behaviour lives in `agentforge.recipe_select`
(scoring) and `agentforge.app_shape` (compilation).

Adding a new recipe:
  1. Create a module under `agentforge/recipes/` exporting one `AppRecipe`.
  2. Append it to `ALL_RECIPES` in this file.
  3. Add prompt cases to `tests/generator/test_recipe_selection.py`.
"""
from __future__ import annotations

from agentforge.recipes._base import (
    AppRecipe,
    EntityTemplate,
    FieldTemplate,
    SampleDataStyle,
    SelectionSignals,
    WorkflowTemplate,
)
from agentforge.recipes.approval_review_queue import APPROVAL_REVIEW_QUEUE
from agentforge.recipes.client_session_manager import CLIENT_SESSION_MANAGER
from agentforge.recipes.generic_dashboard import GENERIC_DASHBOARD
from agentforge.recipes.pipeline_kanban import PIPELINE_KANBAN


ALL_RECIPES: tuple[AppRecipe, ...] = (
    CLIENT_SESSION_MANAGER,
    PIPELINE_KANBAN,
    APPROVAL_REVIEW_QUEUE,
    GENERIC_DASHBOARD,
)

FALLBACK_RECIPE: AppRecipe = GENERIC_DASHBOARD


def get_recipe(recipe_id: str) -> AppRecipe:
    """Look up a recipe by id. Raises KeyError when not found."""
    for recipe in ALL_RECIPES:
        if recipe.id == recipe_id:
            return recipe
    raise KeyError(recipe_id)


def recipe_ids() -> tuple[str, ...]:
    return tuple(recipe.id for recipe in ALL_RECIPES)


__all__ = [
    "ALL_RECIPES",
    "APPROVAL_REVIEW_QUEUE",
    "AppRecipe",
    "CLIENT_SESSION_MANAGER",
    "EntityTemplate",
    "FALLBACK_RECIPE",
    "FieldTemplate",
    "GENERIC_DASHBOARD",
    "PIPELINE_KANBAN",
    "SampleDataStyle",
    "SelectionSignals",
    "WorkflowTemplate",
    "get_recipe",
    "recipe_ids",
]
