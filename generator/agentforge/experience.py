"""Deterministic generated-app experience registry.

The experience layer sits above data recipes and below generated surfaces. It
describes the first-screen product experience a future generator can compile
without changing today's AppRecipe -> AppShape -> Blueprint flow.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class EntityRole:
    """Stable, serializable role ids used by experience recipes."""

    PRIMARY_OBJECT = "primary_object"
    CLIENT_OR_CUSTOMER = "client_or_customer"
    WORK_ITEM = "work_item"
    STATUS_AXIS = "status_axis"
    TIMELINE_EVENT = "timeline_event"
    PAYMENT_RECORD = "payment_record"
    INVENTORY_ITEM = "inventory_item"
    VENDOR = "vendor"
    LOCATION = "location"
    DECISION_RECORD = "decision_record"
    DOCUMENT = "document"
    ACTOR = "actor"


ENTITY_ROLES: tuple[str, ...] = (
    EntityRole.PRIMARY_OBJECT,
    EntityRole.CLIENT_OR_CUSTOMER,
    EntityRole.WORK_ITEM,
    EntityRole.STATUS_AXIS,
    EntityRole.TIMELINE_EVENT,
    EntityRole.PAYMENT_RECORD,
    EntityRole.INVENTORY_ITEM,
    EntityRole.VENDOR,
    EntityRole.LOCATION,
    EntityRole.DECISION_RECORD,
    EntityRole.DOCUMENT,
    EntityRole.ACTOR,
)


@dataclass(frozen=True)
class ExperiencePrimitive:
    """Reusable generated-app experience primitive contract."""

    primitive_id: str
    display_name: str
    description: str
    expected_roles: tuple[str, ...]
    required_roles: tuple[str, ...]
    primary_actions: tuple[str, ...]
    layout_intent: str
    seed_story_intent: str
    generated_test_expectations: tuple[str, ...]
    fallback_behavior: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "primitive_id": self.primitive_id,
            "display_name": self.display_name,
            "description": self.description,
            "expected_roles": list(self.expected_roles),
            "required_roles": list(self.required_roles),
            "primary_actions": list(self.primary_actions),
            "layout_intent": self.layout_intent,
            "seed_story_intent": self.seed_story_intent,
            "generated_test_expectations": list(self.generated_test_expectations),
            "fallback_behavior": self.fallback_behavior,
        }


@dataclass(frozen=True)
class ExperienceRecipe:
    """Mapping from an AppRecipe family to a product experience primitive."""

    experience_id: str
    display_name: str
    suitable_recipe_ids: tuple[str, ...]
    primitive_id: str
    primary_user_job: str
    entity_role_hints: tuple[tuple[str, tuple[str, ...]], ...]
    first_screen_goal: str
    demo_scenario: str
    acceptance_focus: tuple[str, ...]
    fallback_behavior: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "experience_id": self.experience_id,
            "display_name": self.display_name,
            "suitable_recipe_ids": list(self.suitable_recipe_ids),
            "primitive_id": self.primitive_id,
            "primary_user_job": self.primary_user_job,
            "entity_role_hints": {
                role: list(entity_names)
                for role, entity_names in self.entity_role_hints
            },
            "first_screen_goal": self.first_screen_goal,
            "demo_scenario": self.demo_scenario,
            "acceptance_focus": list(self.acceptance_focus),
            "fallback_behavior": self.fallback_behavior,
        }


CLIENT_WORKSPACE_PRIMITIVE = ExperiencePrimitive(
    primitive_id="client_workspace",
    display_name="Client Workspace",
    description="A selected client/customer workspace with related work, timeline context, and payments.",
    expected_roles=(
        EntityRole.CLIENT_OR_CUSTOMER,
        EntityRole.WORK_ITEM,
        EntityRole.TIMELINE_EVENT,
        EntityRole.PAYMENT_RECORD,
    ),
    required_roles=(EntityRole.CLIENT_OR_CUSTOMER, EntityRole.WORK_ITEM),
    primary_actions=("inspect_client", "schedule_or_log_work", "log_payment"),
    layout_intent="Open on a client-centered workspace with related work and payment attention in one place.",
    seed_story_intent="One selected client has recent/upcoming work and at least one payment record needing attention.",
    generated_test_expectations=(
        "workspace renders for a selected client/customer",
        "linked work or timeline records are visible",
        "payment records are visible when available",
    ),
    fallback_behavior="Fall back to the standard entity surface when no client/customer role is available.",
)

PIPELINE_BOARD_PRIMITIVE = ExperiencePrimitive(
    primitive_id="pipeline_board",
    display_name="Pipeline Board",
    description="A staged board for moving work items through a status or stage axis.",
    expected_roles=(
        EntityRole.WORK_ITEM,
        EntityRole.STATUS_AXIS,
        EntityRole.ACTOR,
        EntityRole.CLIENT_OR_CUSTOMER,
    ),
    required_roles=(EntityRole.WORK_ITEM, EntityRole.STATUS_AXIS),
    primary_actions=("move_work_item", "assign_actor", "review_attention_items"),
    layout_intent="Open on lanes grouped by status/stage with cards that show ownership and next attention.",
    seed_story_intent="Cards are distributed across stages so the workflow is visible on first open.",
    generated_test_expectations=(
        "lanes render for the status/stage axis",
        "seeded work items appear in lanes",
        "move/status action expectations are declared",
    ),
    fallback_behavior="Fall back to a table/list surface when no status or stage axis can be found.",
)

INVENTORY_OPS_PRIMITIVE = ExperiencePrimitive(
    primitive_id="inventory_ops",
    display_name="Inventory Ops",
    description="An operational inventory view focused on item status, quantity, locations, vendors, and upkeep.",
    expected_roles=(
        EntityRole.INVENTORY_ITEM,
        EntityRole.LOCATION,
        EntityRole.VENDOR,
        EntityRole.TIMELINE_EVENT,
    ),
    required_roles=(EntityRole.INVENTORY_ITEM,),
    primary_actions=("review_low_stock", "update_item_status", "inspect_vendor_or_location"),
    layout_intent="Open on assets/items with low-stock or maintenance attention and supporting vendor/location context.",
    seed_story_intent="At least one inventory item needs low-stock, reorder, or maintenance attention on first open.",
    generated_test_expectations=(
        "inventory or asset items render",
        "low-stock or maintenance attention is visible",
        "vendor and location labels render when available",
    ),
    fallback_behavior="Fall back to the standard entity surface when inventory item semantics are missing.",
)


EXPERIENCE_PRIMITIVES: tuple[ExperiencePrimitive, ...] = (
    CLIENT_WORKSPACE_PRIMITIVE,
    PIPELINE_BOARD_PRIMITIVE,
    INVENTORY_OPS_PRIMITIVE,
)


CLIENT_WORKSPACE_EXPERIENCE = ExperienceRecipe(
    experience_id="client_workspace",
    display_name="Client Workspace",
    suitable_recipe_ids=("client_session_manager",),
    primitive_id="client_workspace",
    primary_user_job="Inspect a client, related work/sessions, and payments in one workspace.",
    entity_role_hints=(
        (EntityRole.CLIENT_OR_CUSTOMER, ("Client", "Customer", "Student")),
        (EntityRole.WORK_ITEM, ("Session", "Project", "WorkItem")),
        (EntityRole.TIMELINE_EVENT, ("Session", "Activity", "Event")),
        (EntityRole.PAYMENT_RECORD, ("Payment", "Invoice")),
    ),
    first_screen_goal="Show the selected client/customer with linked work and payment context.",
    demo_scenario="A client has recent or upcoming work plus at least one payment or invoice to inspect.",
    acceptance_focus=(
        "client workspace opens from the first screen",
        "related work/sessions are visible",
        "payments or invoices are visible when present",
    ),
    fallback_behavior="Use the standard generated app surface if the client/customer role cannot be mapped.",
)

PIPELINE_BOARD_EXPERIENCE = ExperienceRecipe(
    experience_id="pipeline_board",
    display_name="Pipeline Board",
    suitable_recipe_ids=("pipeline_kanban",),
    primitive_id="pipeline_board",
    primary_user_job="Move work through stages and see what needs attention.",
    entity_role_hints=(
        (EntityRole.WORK_ITEM, ("Card", "Opportunity", "Application", "Job")),
        (EntityRole.STATUS_AXIS, ("Stage", "Status")),
        (EntityRole.ACTOR, ("Owner", "Assignee")),
        (EntityRole.CLIENT_OR_CUSTOMER, ("Client", "Customer", "Account")),
    ),
    first_screen_goal="Show work items grouped by stage/status with attention and ownership context.",
    demo_scenario="Cards are spread across stages so moving work through the pipeline is obvious.",
    acceptance_focus=(
        "board lanes render",
        "seeded work items appear in lanes",
        "stage/status movement expectations are declared",
    ),
    fallback_behavior="Use a list/table surface if no stage or status axis exists.",
)

INVENTORY_OPS_EXPERIENCE = ExperienceRecipe(
    experience_id="inventory_ops",
    display_name="Inventory Ops",
    suitable_recipe_ids=("inventory_asset_tracker",),
    primitive_id="inventory_ops",
    primary_user_job="See assets/items, low-stock or maintenance needs, and related vendors/locations.",
    entity_role_hints=(
        (EntityRole.INVENTORY_ITEM, ("Asset", "Item", "InventoryItem")),
        (EntityRole.LOCATION, ("Location", "Warehouse")),
        (EntityRole.VENDOR, ("Vendor", "Supplier")),
        (EntityRole.TIMELINE_EVENT, ("MaintenanceTask", "Movement", "Event")),
    ),
    first_screen_goal="Show inventory/asset items with operational attention and vendor/location context.",
    demo_scenario="One asset/item is low-stock or maintenance-due and linked to a location or vendor.",
    acceptance_focus=(
        "inventory or asset items are visible",
        "low-stock or maintenance attention is visible",
        "vendor/location context is visible when available",
    ),
    fallback_behavior="Use the standard generated app surface if no inventory item role can be mapped.",
)


EXPERIENCE_RECIPES: tuple[ExperienceRecipe, ...] = (
    CLIENT_WORKSPACE_EXPERIENCE,
    PIPELINE_BOARD_EXPERIENCE,
    INVENTORY_OPS_EXPERIENCE,
)


def list_experience_primitives() -> tuple[ExperiencePrimitive, ...]:
    """Return all registered primitives in deterministic order."""
    return EXPERIENCE_PRIMITIVES


def list_experience_recipes() -> tuple[ExperienceRecipe, ...]:
    """Return all registered experience recipes in deterministic order."""
    return EXPERIENCE_RECIPES


def get_primitive(primitive_id: str) -> ExperiencePrimitive | None:
    """Look up a primitive by stable id."""
    return next(
        (primitive for primitive in EXPERIENCE_PRIMITIVES if primitive.primitive_id == primitive_id),
        None,
    )


def get_experience_recipe(experience_id: str) -> ExperienceRecipe | None:
    """Look up an experience recipe by stable id."""
    return next(
        (experience for experience in EXPERIENCE_RECIPES if experience.experience_id == experience_id),
        None,
    )


def choose_experience_for_recipe(recipe_id: str) -> ExperienceRecipe | None:
    """Return the first experience suitable for an AppRecipe id, or None."""
    return next(
        (
            experience
            for experience in EXPERIENCE_RECIPES
            if recipe_id in experience.suitable_recipe_ids
        ),
        None,
    )


__all__ = [
    "ENTITY_ROLES",
    "EXPERIENCE_PRIMITIVES",
    "EXPERIENCE_RECIPES",
    "EntityRole",
    "ExperiencePrimitive",
    "ExperienceRecipe",
    "choose_experience_for_recipe",
    "get_experience_recipe",
    "get_primitive",
    "list_experience_primitives",
    "list_experience_recipes",
]
