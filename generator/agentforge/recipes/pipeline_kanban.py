"""Recipe: pipeline / kanban board (sales pipeline, hiring, ticket triage)."""
from __future__ import annotations

from agentforge.recipes._base import (
    AppRecipe,
    EntityTemplate,
    FieldTemplate,
    SampleDataStyle,
    SelectionSignals,
    WorkflowTemplate,
)


PIPELINE_KANBAN = AppRecipe(
    id="pipeline_kanban",
    version=1,
    display_name="Pipeline / Kanban",
    summary="Move cards through ordered stages. For sales pipelines, hiring funnels, ticket triage.",
    selection_signals=SelectionSignals(
        keywords=("pipeline", "kanban", "stage", "stages", "board", "column", "columns", "card", "cards", "funnel"),
        strong_keywords=("sales pipeline", "deal", "deals", "lead", "leads", "opportunity", "opportunities", "candidate", "candidates", "applicant", "applicants", "job application", "job applications", "hiring", "recruiting", "ats"),
        role_hints=(
            "i manage a sales pipeline",
            "i run a sales pipeline",
            "i manage hiring",
            "i'm a recruiter",
            "i am a recruiter",
            "manage job applications",
        ),
        anti_signals=("approve", "approval queue", "review queue", "vendor risk", "lesson", "session", "checklist"),
        workflow_tags=("kanban_pipeline",),
        domains=("sales_crm", "hiring_recruiting", "engineering_ops"),
        entity_tags=("lead", "deal", "opportunity", "candidate", "application", "applicant", "card", "stage", "column"),
    ),
    typical_entities=(
        EntityTemplate(
            name="Stage",
            label="Stage",
            fields=(
                FieldTemplate("name", "Name", "string", required=True),
                FieldTemplate("order", "Order", "number", required=True),
                FieldTemplate("wip_limit", "WIP limit", "number"),
            ),
        ),
        EntityTemplate(
            name="Card",
            label="Card",
            fields=(
                FieldTemplate("title", "Title", "string", required=True),
                FieldTemplate("stage", "Stage", "reference", required=True, references="Stage"),
                FieldTemplate("owner", "Owner", "reference", references="Owner"),
                FieldTemplate("value", "Value", "number", sample_style="money"),
                FieldTemplate("due_on", "Due on", "date", sample_style="upcoming_date"),
                FieldTemplate("notes", "Notes", "text"),
            ),
        ),
        EntityTemplate(
            name="Owner",
            label="Owner",
            fields=(
                FieldTemplate("name", "Name", "string", required=True, sample_style="person_name"),
            ),
        ),
    ),
    typical_workflows=(
        WorkflowTemplate(
            name="move_card",
            label="Move card to next stage",
            target_entity="Card",
            trigger="user clicks Move",
            effects=("set Card.stage to next Stage", "log activity"),
        ),
        WorkflowTemplate(
            name="mark_won_lost",
            label="Mark won or lost",
            target_entity="Card",
            trigger="user clicks Won/Lost on a card",
            effects=("set Card.stage to terminal stage", "log activity"),
        ),
        WorkflowTemplate(
            name="assign_owner",
            label="Assign owner",
            target_entity="Card",
            trigger="user picks an owner on a card",
            effects=("set Card.owner", "log activity"),
        ),
    ),
    home_surface="board",
    demo_moment="Move a card from Qualified to Proposal and see the board update.",
    sample_data_style=SampleDataStyle(
        per_entity_counts={"Stage": 3, "Card": 6, "Owner": 2},
        distribution_hints=("at least one card per stage", "one card due this week"),
        relation_density="medium",
        demo_seed="One card in the first stage with a near-term due date",
        name_pool_tag="business",
    ),
    what_makes_it_different="Home is a kanban board with column-aware move actions, not a flat list.",
)


__all__ = ["PIPELINE_KANBAN"]
