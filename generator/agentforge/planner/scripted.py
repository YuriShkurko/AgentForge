"""Deterministic scripted planner for App Blueprint drafts."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from agentforge.blueprints import create_starter_blueprint
from agentforge.modules import ARCHETYPE_REQUIRED_MODULES
from agentforge.planner import PlannerResult, validate_blueprint_result


CANONICAL_IDEAS: dict[str, str] = {
    "ingestion_scoring_pipeline": "score incoming support tickets from a fixture provider and explain the ranking",
    "notification_triage_app": "triage scored records and create preview notifications for operator decisions",
    "agent_dashboard_app": "agent dashboard that can run tools and pin useful results to a workspace",
    "hybrid_agent_pipeline": "pipeline app with an agent that explains deterministic scoring runs",
    "deploy_planner_app": "deployment planning checklist app with deterministic validation only",
    "project_workspace_app": "project workspace task planner for owners, due dates, notes, activity, and pinned agent widgets",
}

_ARCHETYPE_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("notification_triage_app", ("triage", "notification", "notify", "decision", "approve", "reject")),
    ("project_workspace_app", ("project workspace", "task planner", "task tracker", "project management", "projects", "due date", "owners")),
    ("hybrid_agent_pipeline", ("hybrid", "agent pipeline", "agent explain", "explain pipeline", "with an agent")),
    ("ingestion_scoring_pipeline", ("lead scoring", "account scoring", "best-fit", "best fit", "score", "scoring", "rank", "ingest", "pipeline", "records")),
    ("agent_dashboard_app", ("agent dashboard", "dashboard", "workspace", "pin", "widget")),
    ("deploy_planner_app", ("deploy", "deployment", "release", "infra")),
]

_DEFAULT_OPTIONAL_MODULES: dict[str, list[str]] = {
    "ingestion_scoring_pipeline": ["notification_action", "triage_ui", "agent_runtime", "workspace"],
    "notification_triage_app": ["agent_runtime", "workspace", "pipeline", "provider_adapter", "test"],
    "agent_dashboard_app": ["agent_runtime", "pipeline", "scoring_explanation", "operations_ui", "persistence"],
    "hybrid_agent_pipeline": ["agent_runtime", "workspace", "scoring_explanation", "persistence", "test"],
    "deploy_planner_app": ["operations_ui"],
    "project_workspace_app": [],
}

_CLARIFYING_QUESTIONS = [
    "What kind of records or entities should the app manage?",
    "Who is the primary user or operator?",
    "What decision should the app help that user make?",
    "Should the first version include agent runtime, workspace widgets, or notification previews?",
]


class ScriptedPlanner:
    """Keyword-based planner that never calls network services or writes files."""

    def clarify(self, idea: str) -> PlannerResult:
        """Return targeted clarification questions without drafting a blueprint."""
        text = idea.strip()
        questions = list(_CLARIFYING_QUESTIONS)
        if any(word in text.lower() for word in ["agent", "dashboard", "workspace"]):
            questions[-1] = "Which agent tool results should be pinned to the workspace?"
        elif any(word in text.lower() for word in ["notify", "notification", "triage"]):
            questions[-1] = "Which preview notification decisions should the operator be able to record?"
        return PlannerResult(
            status="needs_clarification",
            questions=questions,
            warnings=["Clarification requested before drafting an App Blueprint."],
        )

    def draft(self, idea: str, prior_answers: dict[str, str] | None = None) -> PlannerResult:
        text = " ".join(str(item or "").strip() for item in [idea, *(prior_answers or {}).values()]).strip()
        if self._needs_clarification(text, prior_answers):
            return self.clarify(idea)

        archetype = infer_archetype(text)
        return self._draft_for_archetype(archetype, text)

    def refine(self, blueprint: dict[str, Any], instruction: str) -> PlannerResult:
        updated = deepcopy(blueprint)
        optional = set(updated.get("optional_shell_modules") or [])
        required = set(updated.get("required_shell_modules") or [])
        changed: list[str] = []
        text = instruction.lower()

        if "agent" in text or "chat" in text:
            if "agent" not in required and "agent_runtime" not in optional:
                optional.add("agent_runtime")
                changed.append("added optional module agent_runtime")
            updated["agent_runtime"] = _agent_runtime_config()
            changed.append("enabled agent_runtime config")

        if "workspace" in text or "widget" in text or "dashboard" in text:
            if "workspace" not in required and "workspace" not in optional:
                optional.add("workspace")
                changed.append("added optional module workspace")
            _ensure_workspace(updated)
            changed.append("enabled workspace config")

        if "notification" in text or "triage" in text:
            for module in ["notification_action", "triage_ui"]:
                if module not in required and module not in optional:
                    optional.add(module)
                    changed.append(f"added optional module {module}")
            _ensure_notification_actions(updated)

        updated["optional_shell_modules"] = sorted(optional)
        return validate_blueprint_result(
            updated,
            assumptions=["Applied deterministic scripted refinement."],
            warnings=changed or ["Instruction did not match a known scripted refinement."],
            suggested_modules=sorted(required | optional),
        )

    def _draft_for_archetype(self, archetype: str, idea: str) -> PlannerResult:
        name = _name_from_idea(idea, archetype)
        optional_modules = _DEFAULT_OPTIONAL_MODULES.get(archetype, [])
        blueprint = create_starter_blueprint(
            name,
            display_name=name.replace("-", " ").title(),
            description=_description_from_idea(idea, archetype),
            target_user=_target_user_from_idea(idea),
            archetype=archetype,
            optional_modules=optional_modules,
            workspace_enabled="workspace" in optional_modules or "workspace" in ARCHETYPE_REQUIRED_MODULES.get(archetype, set()),
            fixture_provider_enabled=True,
            customization=_customization_from_idea(idea, archetype),
        )
        return validate_blueprint_result(
            blueprint,
            assumptions=[f"Assumed {archetype} from the app idea."],
            warnings=_warnings_for_archetype(archetype),
            suggested_modules=sorted(set(blueprint["required_shell_modules"]) | set(blueprint["optional_shell_modules"])),
        )

    @staticmethod
    def _needs_clarification(text: str, prior_answers: dict[str, str] | None) -> bool:
        compact = text.strip().lower()
        if prior_answers:
            return False
        return compact in {"", "app", "build app", "build me an app", "make an app", "tool"}


def infer_archetype(idea: str) -> str:
    text = idea.lower()
    for archetype, keywords in _ARCHETYPE_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            return archetype
    return "ingestion_scoring_pipeline"


def _name_from_idea(idea: str, archetype: str) -> str:
    words = [word.strip(".,:;!?()[]{}").lower() for word in idea.split()]
    clean = [word for word in words if word.isalnum() and word not in {"a", "an", "the", "and", "or", "to", "for", "with"}]
    if len(clean) >= 2:
        return "-".join(clean[:4])
    return archetype.replace("_", "-")


def _description_from_idea(idea: str, archetype: str) -> str:
    text = idea.strip().rstrip(".")
    if not text:
        text = CANONICAL_IDEAS[archetype]
    return f"{text}. Drafted by the scripted AgentForge planner for a deterministic local App Blueprint."


def _target_user_from_idea(idea: str) -> str:
    text = idea.lower()
    if "support" in text:
        return "support operator"
    if "sales" in text:
        return "sales operator"
    if "developer" in text or "dev" in text:
        return "developer"
    return "operator"


def _customization_from_idea(idea: str, archetype: str) -> dict[str, Any]:
    text = idea.lower()
    target_user = _target_user_from_idea(idea)
    description = _description_from_idea(idea, archetype)
    if archetype == "project_workspace_app":
        sample = "game development workspace" if any(term in text for term in ["game", "gaming"]) else "sample workspace"
        return {
            "app": {
                "subtitle": description,
                "target_user_label": target_user,
                "workflow_label": "Project command center",
            },
            "agent_starters": ["list tasks", "summarize project", "pin task list"],
            "workspace": {
                "empty_state": "Ask the agent to pin a project summary or task list.",
                "widget_label": "widgets",
                "pinned_label": "Pinned project context",
            },
            "project_workspace": {
                "project_label": {"singular": "project", "plural": "projects"},
                "task_label": {"singular": "task", "plural": "tasks"},
                "activity_label": "Notes and activity",
                "sample_data_label": sample,
            },
        }

    singular, plural = _record_labels_from_idea(text)
    workflow = _workflow_label_from_idea(text, singular)
    return {
        "app": {
            "subtitle": description,
            "target_user_label": target_user,
            "workflow_label": workflow,
        },
        "agent_starters": [
            f"score the {plural}",
            f"show best {plural}",
            f"pin the scored {plural} to the workspace",
        ],
        "workspace": {
            "empty_state": f"Ask the agent to pin scored {plural}, notification previews, or action history.",
            "widget_label": "widgets",
            "pinned_label": "Pinned context",
        },
        "scoring": {
            "record_label": {"singular": singular, "plural": plural},
            "criteria_labels": ["Fit", "Priority", "Risk"],
            "review_queue_label": f"Scored {plural.title()}",
            "notification_label": "Notification Previews",
            "sample_data_label": f"demo {plural}",
        },
    }


def _record_labels_from_idea(text: str) -> tuple[str, str]:
    candidates = [
        (("support ticket", "ticket", "tickets"), "ticket", "tickets"),
        (("candidate", "candidates", "resume", "applicant"), "candidate", "candidates"),
        (("account", "accounts", "customer success", "renewal"), "account", "accounts"),
        (("lead", "leads", "sales"), "lead", "leads"),
        (("job", "jobs", "opportunity", "opportunities"), "opportunity", "opportunities"),
    ]
    for keywords, singular, plural in candidates:
        if any(keyword in text for keyword in keywords):
            return singular, plural
    return "record", "records"


def _workflow_label_from_idea(text: str, singular: str) -> str:
    if "triage" in text:
        return f"{singular.title()} triage"
    if "review" in text:
        return f"{singular.title()} review"
    return "Review workflow"


def _warnings_for_archetype(archetype: str) -> list[str]:
    warnings = ["Scripted planner output must still be reviewed and validated with agentforge plan."]
    if archetype == "deploy_planner_app":
        warnings.append("deploy_planner_app is planned; generated behavior remains limited to supported modules.")
    return warnings


def _agent_runtime_config() -> dict[str, Any]:
    return {
        "enabled": True,
        "provider_mode": "scripted",
        "scripted_fixture_path": "backend/app/agent/providers.py",
        "conversation_persistence": {"enabled": True, "tables": ["conversations", "conversation_messages"]},
        "streaming": {
            "enabled": True,
            "endpoint": "/agent/chat/stream",
            "events": ["message_start", "text_delta", "tool_call", "tool_result", "error", "done"],
        },
        "guardrails": {"reject_empty_message": True},
        "tools": [],
        "scripted_turns": [],
    }


def _ensure_workspace(blueprint: dict[str, Any]) -> None:
    blueprint["workspace"] = {
        "enabled": True,
        "persistence": {
            "table_name": "workspace_widgets",
            "fields": ["id", "widget_type", "title", "source_tool", "data", "position", "metadata"],
        },
        "default_layout": [],
        "remove_enabled": True,
        "reorder_enabled": True,
        "empty_state": "No widgets yet. Ask the agent to pin a result to the workspace.",
        "frontend_surface": "workspace_panel",
    }
    blueprint.setdefault("tool_widget_compatibility", {"score_records": ["summary_card"]})
    blueprint.setdefault("widgets", [])


def _ensure_notification_actions(blueprint: dict[str, Any]) -> None:
    if blueprint.get("notification_actions"):
        return
    blueprint["notification_actions"] = [
        {
            "name": "record_decision",
            "trigger": "user chooses an action in the triage UI",
            "delivery_channel": "preview",
            "delivery_mode": "preview_only",
            "decision_states": ["pending", "accept", "skip", "maybe"],
            "dedupe_key": "record_id + action_type",
            "persistence_table": "record_actions",
            "history_table": "record_action_events",
            "preview_table": "notification_previews",
        }
    ]


__all__ = ["CANONICAL_IDEAS", "ScriptedPlanner", "infer_archetype"]
