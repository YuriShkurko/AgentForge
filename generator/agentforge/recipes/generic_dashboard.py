"""Recipe: generic dashboard fallback (when no specific recipe scores high enough)."""
from __future__ import annotations

from agentforge.recipes._base import (
    AppRecipe,
    EntityTemplate,
    FieldTemplate,
    SampleDataStyle,
    SelectionSignals,
    WorkflowTemplate,
)


GENERIC_DASHBOARD = AppRecipe(
    id="generic_dashboard",
    version=1,
    display_name="Generic Dashboard",
    summary="Tile dashboard plus entity grids. Selected when no specific workflow recipe is a strong match.",
    selection_signals=SelectionSignals(
        keywords=("dashboard", "records", "list", "manage", "track"),
        strong_keywords=("simple dashboard", "general dashboard", "track random", "manage records", "manage items"),
        role_hints=(),
        anti_signals=(),
        workflow_tags=("generic_crud",),
        domains=(),
        entity_tags=("item",),
    ),
    typical_entities=(
        EntityTemplate(
            name="Item",
            label="Item",
            fields=(
                FieldTemplate("name", "Name", "string", required=True),
                FieldTemplate("notes", "Notes", "text"),
                FieldTemplate("created_at", "Created at", "datetime", sample_style="recent_datetime"),
            ),
        ),
    ),
    typical_workflows=(
        WorkflowTemplate(
            name="add_item",
            label="Add item",
            target_entity="Item",
            trigger="user clicks Add",
            effects=("create Item row",),
        ),
    ),
    home_surface="dashboard",
    demo_moment="See a tile summary plus the most recent items.",
    sample_data_style=SampleDataStyle(
        per_entity_counts={"Item": 4},
        distribution_hints=("spread items across the last 30 days",),
        relation_density="low",
        demo_seed=None,
        name_pool_tag="generic",
    ),
    what_makes_it_different="Explicit fallback: surface a banner so the user can clarify and pick a more specific recipe.",
    is_fallback=True,
)


__all__ = ["GENERIC_DASHBOARD"]
