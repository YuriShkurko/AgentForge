"""Deterministic AppShape compilation from `IntentSpec` + chosen `AppRecipe`.

`AppShape` is the intermediate, fully-validated description of "what the app
is" that the recipe registry produces before any Blueprint or file is written.
It is intentionally a planning object: no React layouts, no file paths, no
generator side-effects. Future slices may compile `AppShape` into a Blueprint
(`generator.agentforge.blueprint_compiler`) and a generated app
(`generator.agentforge.model_driven`); this slice stops at AppShape.

Determinism rules:
  * Same inputs -> byte-identical AppShape (dataclasses are frozen, tuples).
  * No randomness, no clock reads, no environment lookups.
  * Recipe data is authoritative; IntentSpec only refines purpose/target_user.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from agentforge.app_intent import IntentSpec
from agentforge.recipes._base import (
    AppRecipe,
    EntityTemplate,
    SampleDataStyle,
    WorkflowTemplate,
)


@dataclass(frozen=True)
class EntitySpec:
    name: str
    label: str
    fields: tuple["FieldSpec", ...]


@dataclass(frozen=True)
class FieldSpec:
    name: str
    label: str
    kind: str
    required: bool
    references: str | None
    enum_values: tuple[str, ...]
    sample_style: str | None


@dataclass(frozen=True)
class WorkflowSpec:
    name: str
    label: str
    target_entity: str
    trigger: str | None
    effects: tuple[str, ...]


@dataclass(frozen=True)
class ScreenSpec:
    """A planned screen in the future generated app.

    `kind` describes the layout primitive the recipe expects (`home` is always
    present; entity-detail screens follow). `entity` is None for the home
    screen. `home_surface` mirrors the recipe's home_surface for downstream
    consumers.
    """

    kind: str
    label: str
    entity: str | None
    home_surface: str | None = None


@dataclass(frozen=True)
class SampleDataPlan:
    per_entity_counts: tuple[tuple[str, int], ...]
    distribution_hints: tuple[str, ...]
    relation_density: str
    demo_seed: str | None
    name_pool_tag: str | None

    @classmethod
    def from_style(cls, style: SampleDataStyle) -> "SampleDataPlan":
        return cls(
            per_entity_counts=tuple(sorted(style.per_entity_counts.items())),
            distribution_hints=tuple(style.distribution_hints),
            relation_density=style.relation_density,
            demo_seed=style.demo_seed,
            name_pool_tag=style.name_pool_tag,
        )


@dataclass(frozen=True)
class AppShape:
    """Deterministic description of the app the planner intends to generate."""

    recipe_id: str
    recipe_version: int
    purpose: str
    target_user: str | None
    primary_workflow: WorkflowSpec | None
    entities: tuple[EntitySpec, ...]
    workflows: tuple[WorkflowSpec, ...]
    screens: tuple[ScreenSpec, ...]
    home_surface: str
    sample_data_plan: SampleDataPlan
    demo_moment: str
    notes: tuple[str, ...] = field(default_factory=tuple)
    source_intent: IntentSpec | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "recipe_id": self.recipe_id,
            "recipe_version": self.recipe_version,
            "purpose": self.purpose,
            "target_user": self.target_user,
            "primary_workflow": (
                _workflow_to_dict(self.primary_workflow)
                if self.primary_workflow
                else None
            ),
            "entities": [_entity_to_dict(e) for e in self.entities],
            "workflows": [_workflow_to_dict(w) for w in self.workflows],
            "screens": [
                {
                    "kind": s.kind,
                    "label": s.label,
                    "entity": s.entity,
                    "home_surface": s.home_surface,
                }
                for s in self.screens
            ],
            "home_surface": self.home_surface,
            "sample_data_plan": {
                "per_entity_counts": dict(self.sample_data_plan.per_entity_counts),
                "distribution_hints": list(self.sample_data_plan.distribution_hints),
                "relation_density": self.sample_data_plan.relation_density,
                "demo_seed": self.sample_data_plan.demo_seed,
                "name_pool_tag": self.sample_data_plan.name_pool_tag,
            },
            "demo_moment": self.demo_moment,
            "notes": list(self.notes),
        }


def compile_app_shape(intent: IntentSpec, recipe: AppRecipe) -> AppShape:
    """Compile an `IntentSpec` + chosen `AppRecipe` into a deterministic AppShape."""
    notes: list[str] = []
    if recipe.is_fallback:
        notes.append(
            "Recipe is the generic_dashboard fallback. Ask the user to clarify the workflow."
        )
    if intent.clarity == "vague":
        notes.append("Intent was vague; AppShape used recipe defaults verbatim.")

    entities = tuple(_entity_from_template(t) for t in recipe.typical_entities)
    workflows = tuple(_workflow_from_template(w) for w in recipe.typical_workflows)
    primary = workflows[0] if workflows else None

    screens: tuple[ScreenSpec, ...] = (
        ScreenSpec(
            kind="home",
            label=f"{recipe.display_name} home",
            entity=None,
            home_surface=recipe.home_surface,
        ),
        *tuple(
            ScreenSpec(kind="detail", label=f"{entity.label} detail", entity=entity.name)
            for entity in entities
        ),
    )

    purpose = _derive_purpose(intent, recipe)
    target_user = intent.target_user

    sample_plan = SampleDataPlan.from_style(recipe.sample_data_style)

    return AppShape(
        recipe_id=recipe.id,
        recipe_version=recipe.version,
        purpose=purpose,
        target_user=target_user,
        primary_workflow=primary,
        entities=entities,
        workflows=workflows,
        screens=screens,
        home_surface=recipe.home_surface,
        sample_data_plan=sample_plan,
        demo_moment=recipe.demo_moment,
        notes=tuple(notes),
        source_intent=intent,
    )


def _entity_from_template(t: EntityTemplate) -> EntitySpec:
    return EntitySpec(
        name=t.name,
        label=t.label,
        fields=tuple(
            FieldSpec(
                name=f.name,
                label=f.label,
                kind=f.kind,
                required=f.required,
                references=f.references,
                enum_values=tuple(f.enum_values),
                sample_style=f.sample_style,
            )
            for f in t.fields
        ),
    )


def _workflow_from_template(w: WorkflowTemplate) -> WorkflowSpec:
    return WorkflowSpec(
        name=w.name,
        label=w.label,
        target_entity=w.target_entity,
        trigger=w.trigger,
        effects=tuple(w.effects),
    )


def _derive_purpose(intent: IntentSpec, recipe: AppRecipe) -> str:
    jtbd = intent.primary_jtbd
    if jtbd:
        return f"{recipe.display_name}: {jtbd}."
    return f"{recipe.display_name}: {recipe.summary}"


def _entity_to_dict(e: EntitySpec) -> dict[str, object]:
    return {
        "name": e.name,
        "label": e.label,
        "fields": [
            {
                "name": f.name,
                "label": f.label,
                "kind": f.kind,
                "required": f.required,
                "references": f.references,
                "enum_values": list(f.enum_values),
                "sample_style": f.sample_style,
            }
            for f in e.fields
        ],
    }


def _workflow_to_dict(w: WorkflowSpec) -> dict[str, object]:
    return {
        "name": w.name,
        "label": w.label,
        "target_entity": w.target_entity,
        "trigger": w.trigger,
        "effects": list(w.effects),
    }


__all__ = [
    "AppShape",
    "EntitySpec",
    "FieldSpec",
    "SampleDataPlan",
    "ScreenSpec",
    "WorkflowSpec",
    "compile_app_shape",
]
