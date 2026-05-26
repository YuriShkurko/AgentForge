"""Recipe: client/session manager (coaches, tutors, trainers, therapists)."""
from __future__ import annotations

from agentforge.recipes._base import (
    AppRecipe,
    EntityTemplate,
    FieldTemplate,
    SampleDataStyle,
    SelectionSignals,
    WorkflowTemplate,
)


CLIENT_SESSION_MANAGER = AppRecipe(
    id="client_session_manager",
    version=1,
    display_name="Client & Session Manager",
    summary="Track clients, schedule sessions, log payments. For coaches, tutors, trainers, and therapists.",
    selection_signals=SelectionSignals(
        keywords=("client", "clients", "session", "sessions", "lesson", "lessons", "appointment", "payment", "payments"),
        strong_keywords=("coach", "trainer", "tutor", "therapist", "instructor", "training session", "court"),
        role_hints=(
            "i am a coach", "i'm a coach",
            "i am a trainer", "i'm a trainer",
            "i am a tutor", "i'm a tutor",
            "i am a therapist", "i'm a therapist",
            "basketball coach", "tennis coach", "fitness coach",
        ),
        anti_signals=("kanban", "pipeline", "approval queue", "vendor risk"),
        workflow_tags=("session_tracking",),
        domains=("sports_coaching", "healthcare", "education"),
        entity_tags=("client", "session", "lesson", "payment"),
    ),
    typical_entities=(
        EntityTemplate(
            name="Client",
            label="Client",
            fields=(
                FieldTemplate("name", "Name", "string", required=True, sample_style="person_name"),
                FieldTemplate("contact", "Contact", "string"),
                FieldTemplate("level", "Level", "enum", enum_values=("beginner", "intermediate", "advanced")),
                FieldTemplate("notes", "Notes", "text"),
            ),
        ),
        EntityTemplate(
            name="Session",
            label="Session",
            fields=(
                FieldTemplate("client", "Client", "reference", required=True, references="Client"),
                FieldTemplate("starts_at", "Starts at", "datetime", required=True, sample_style="upcoming_datetime"),
                FieldTemplate("duration_minutes", "Duration (min)", "number"),
                FieldTemplate("location", "Location", "string"),
                FieldTemplate("status", "Status", "enum", enum_values=("scheduled", "completed", "no_show", "cancelled")),
                FieldTemplate("fee", "Fee", "number", sample_style="money"),
            ),
        ),
        EntityTemplate(
            name="Payment",
            label="Payment",
            fields=(
                FieldTemplate("client", "Client", "reference", required=True, references="Client"),
                FieldTemplate("amount", "Amount", "number", required=True, sample_style="money"),
                FieldTemplate("paid_on", "Paid on", "date", sample_style="recent_date"),
                FieldTemplate("method", "Method", "enum", enum_values=("cash", "card", "transfer")),
                FieldTemplate("session", "Session", "reference", references="Session"),
            ),
        ),
    ),
    typical_workflows=(
        WorkflowTemplate(
            name="schedule_session",
            label="Schedule session",
            target_entity="Session",
            trigger="user clicks Schedule",
            effects=("create Session row", "set status=scheduled"),
        ),
        WorkflowTemplate(
            name="mark_session_completed",
            label="Mark session completed",
            target_entity="Session",
            trigger="user clicks Complete on a session",
            effects=("set status=completed", "log activity"),
        ),
        WorkflowTemplate(
            name="log_payment",
            label="Log payment",
            target_entity="Payment",
            trigger="user clicks Log payment",
            effects=("create Payment row", "optionally link to Session"),
        ),
    ),
    home_surface="split",
    demo_moment="See two upcoming sessions today, mark one Completed, log a payment against it.",
    sample_data_style=SampleDataStyle(
        per_entity_counts={"Client": 3, "Session": 5, "Payment": 2},
        distribution_hints=("at least one session today", "one session this week", "one payment this week"),
        relation_density="medium",
        demo_seed="One session scheduled for today with status=scheduled and fee>0",
        name_pool_tag="coaching",
    ),
    what_makes_it_different="Home is an upcoming-session list with quick Complete + Log payment actions, not a generic entity grid.",
)


__all__ = ["CLIENT_SESSION_MANAGER"]
