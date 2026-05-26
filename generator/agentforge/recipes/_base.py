"""Data classes shared by every AgentForge AppRecipe.

A recipe is data: a deterministic bundle of selection signals plus the entity,
field, workflow, home-surface, and sample-data defaults the planner uses when
that recipe is picked. There is no recipe-specific Python logic here; behaviour
is owned by `agentforge.recipe_select` (selection) and `agentforge.app_shape`
(compilation).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EntityTemplate:
    name: str
    label: str
    fields: tuple["FieldTemplate", ...]


@dataclass(frozen=True)
class FieldTemplate:
    name: str
    label: str
    kind: str  # "string" | "text" | "number" | "date" | "datetime" | "enum" | "reference"
    required: bool = False
    references: str | None = None  # entity name for "reference" kind
    enum_values: tuple[str, ...] = ()
    sample_style: str | None = None  # e.g. "person_name", "money", "iso_date"


@dataclass(frozen=True)
class WorkflowTemplate:
    name: str
    label: str
    target_entity: str
    trigger: str | None = None
    effects: tuple[str, ...] = ()


@dataclass(frozen=True)
class SampleDataStyle:
    """How the sample-data planner should populate seed rows for this recipe."""

    per_entity_counts: dict[str, int] = field(default_factory=dict)
    distribution_hints: tuple[str, ...] = ()
    relation_density: str = "low"  # "low" | "medium" | "high"
    demo_seed: str | None = None  # one seed row tuned for the demo moment
    name_pool_tag: str | None = None  # which name pool to draw realistic names from


@dataclass(frozen=True)
class SelectionSignals:
    """Pure-data inputs to the recipe scorer.

    `keywords` are weighted +1 each, `strong_keywords` weighted +3, `role_hints`
    weighted +5 (these usually denote a user explicitly stating role and job).
    `anti_signals` subtract -2 each when matched. `workflow_tags` matches
    against `IntentSpec.workflow_hints` and adds +4 per matched tag.
    `provider_tags` matches against `IntentSpec.provider_hints` and adds +2 per
    matched tag. `domains` matches against `IntentSpec.domain` and adds +4 when
    matched. Tunable per-recipe via the dataclass; the scorer enforces the
    weights so all recipes share the same scoring model.
    """

    keywords: tuple[str, ...] = ()
    strong_keywords: tuple[str, ...] = ()
    role_hints: tuple[str, ...] = ()
    anti_signals: tuple[str, ...] = ()
    workflow_tags: tuple[str, ...] = ()
    provider_tags: tuple[str, ...] = ()
    domains: tuple[str, ...] = ()
    entity_tags: tuple[str, ...] = ()  # matched against IntentSpec.candidate_entities, +2 each


@dataclass(frozen=True)
class AppRecipe:
    """A named, deterministic bundle that shapes a generated app."""

    id: str
    version: int
    display_name: str
    summary: str
    selection_signals: SelectionSignals
    typical_entities: tuple[EntityTemplate, ...]
    typical_workflows: tuple[WorkflowTemplate, ...]
    home_surface: str  # "split" | "board" | "queue" | "calendar" | "dashboard" | "table"
    demo_moment: str
    sample_data_style: SampleDataStyle
    what_makes_it_different: str
    is_fallback: bool = False

    def primary_workflow(self) -> WorkflowTemplate | None:
        return self.typical_workflows[0] if self.typical_workflows else None


__all__ = [
    "AppRecipe",
    "EntityTemplate",
    "FieldTemplate",
    "SampleDataStyle",
    "SelectionSignals",
    "WorkflowTemplate",
]
