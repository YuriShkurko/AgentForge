"""Recipe: approval / review queue (vendor risk, compliance findings, submissions)."""
from __future__ import annotations

from agentforge.recipes._base import (
    AppRecipe,
    EntityTemplate,
    FieldTemplate,
    SampleDataStyle,
    SelectionSignals,
    WorkflowTemplate,
)


APPROVAL_REVIEW_QUEUE = AppRecipe(
    id="approval_review_queue",
    version=1,
    display_name="Approval / Review Queue",
    summary="Triage pending items and record decisions. For vendor risk, compliance review, request approvals.",
    selection_signals=SelectionSignals(
        keywords=("review", "reviews", "approve", "approval", "approvals", "queue", "pending", "claim", "reject", "escalate", "decision", "rationale"),
        strong_keywords=("vendor risk", "risk finding", "risk findings", "compliance", "audit finding", "audit findings", "review queue", "approval queue", "submissions to review"),
        role_hints=(
            "i review vendor risk findings",
            "i need to review",
            "i need to approve",
            "i'm a reviewer",
            "i am a reviewer",
            "i run a compliance review",
        ),
        anti_signals=("kanban", "pipeline", "session", "lesson", "checklist", "calendar"),
        workflow_tags=("approval_queue",),
        domains=("compliance",),
        entity_tags=("finding", "approval", "review", "submission", "request", "reviewer"),
    ),
    typical_entities=(
        EntityTemplate(
            name="Item",
            label="Pending item",
            fields=(
                FieldTemplate("title", "Title", "string", required=True),
                FieldTemplate("requester", "Requester", "string"),
                FieldTemplate("severity", "Severity", "enum", enum_values=("low", "medium", "high", "critical")),
                FieldTemplate("status", "Status", "enum", enum_values=("pending", "claimed", "approved", "rejected", "needs_changes")),
                FieldTemplate("submitted_at", "Submitted at", "datetime", sample_style="recent_datetime"),
                FieldTemplate("evidence", "Evidence", "text"),
            ),
        ),
        EntityTemplate(
            name="Reviewer",
            label="Reviewer",
            fields=(
                FieldTemplate("name", "Name", "string", required=True, sample_style="person_name"),
            ),
        ),
        EntityTemplate(
            name="Decision",
            label="Decision",
            fields=(
                FieldTemplate("item", "Item", "reference", required=True, references="Item"),
                FieldTemplate("reviewer", "Reviewer", "reference", required=True, references="Reviewer"),
                FieldTemplate("outcome", "Outcome", "enum", required=True, enum_values=("approved", "rejected", "needs_changes")),
                FieldTemplate("rationale", "Rationale", "text"),
                FieldTemplate("decided_at", "Decided at", "datetime", sample_style="recent_datetime"),
            ),
        ),
    ),
    typical_workflows=(
        WorkflowTemplate(
            name="claim_item",
            label="Claim item",
            target_entity="Item",
            trigger="reviewer clicks Claim on a pending item",
            effects=("set Item.status=claimed", "set claimed_by reviewer"),
        ),
        WorkflowTemplate(
            name="approve",
            label="Approve",
            target_entity="Item",
            trigger="reviewer clicks Approve",
            effects=("create Decision(outcome=approved)", "set Item.status=approved"),
        ),
        WorkflowTemplate(
            name="reject",
            label="Reject",
            target_entity="Item",
            trigger="reviewer clicks Reject",
            effects=("create Decision(outcome=rejected)", "set Item.status=rejected"),
        ),
        WorkflowTemplate(
            name="request_changes",
            label="Request changes",
            target_entity="Item",
            trigger="reviewer clicks Request changes",
            effects=("create Decision(outcome=needs_changes)", "set Item.status=needs_changes"),
        ),
    ),
    home_surface="queue",
    demo_moment="Claim a pending item from the queue and approve it with a rationale.",
    sample_data_style=SampleDataStyle(
        per_entity_counts={"Item": 5, "Reviewer": 2, "Decision": 1},
        distribution_hints=("at least three pending items at mixed severity", "one already approved (history)"),
        relation_density="medium",
        demo_seed="One pending item with severity=high submitted in the last 24h",
        name_pool_tag="compliance",
    ),
    what_makes_it_different="Home is a sorted queue with claim/approve/reject inline actions and a decision history, not a CRUD form.",
)


__all__ = ["APPROVAL_REVIEW_QUEUE"]
