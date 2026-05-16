"""Deterministic Builder Assistant state machine.

The assistant is deliberately local, stateless between HTTP requests, and side-effect
free. Clients send the returned ``state`` back on the next turn; the server never
persists conversation data or writes blueprint files.
"""
from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from agentforge.blueprints import create_starter_blueprint, sanitize_pack_name
from agentforge.planner import validate_blueprint_result
from agentforge.planner.live_llm import LiveAssistantProvider
from agentforge.planner.validation_guidance import summarize_validation_errors


_STOP_WORDS = {
    "a", "an", "app", "application", "and", "build", "builder", "for", "make", "me", "of", "the", "to", "tool", "with",
}

_VAGUE_TOKENS = {
    "app", "apps", "tool", "tools", "build", "builder", "make", "create", "want", "need",
    "something", "thing", "stuff", "help", "new", "start", "please", "just", "kind",
    "of", "a", "an", "the", "my", "i", "me", "mine", "for", "with", "to", "and",
    "would", "like", "love", "could", "you", "yours",
}

_ENTITY_KEYWORDS = (
    "ticket", "client", "task", "vendor", "risk", "issue", "lead", "candidate", "project",
    "finding", "record", "account",
)
_FIELD_KEYWORDS = (
    "status", "priority", "owner", "due", "date", "email", "severity", "notes", "title",
    "name", "description", "label",
)
_WORKFLOW_KEYWORDS = (
    "track", "review", "triage", "approve", "close", "complete", "onboard", "manage",
    "resolve", "assign", "ship",
)


QUESTION_CATALOG: dict[str, dict[str, Any]] = {
    "idea_seed": {
        "id": "idea_seed",
        "prompt": "What model-driven app should I draft?",
        "helper": "One plain-English sentence is enough. Mention the main record, a couple of fields, and the workflow action.",
        "examples": [
            "Support ticket triage with title, status, priority, owner, and notes to close tickets.",
            "Client onboarding for clients and onboarding tasks with status and due dates.",
            "Vendor risk register to review findings with severity, status, and owner.",
            "Task tracker with status, owner, and due dates to complete tasks.",
        ],
        "chips": [
            {"label": "Support tickets", "value": "Support ticket triage with title, status, priority, owner, and notes to close tickets."},
            {"label": "Client onboarding", "value": "Client onboarding for clients and onboarding tasks with status and due dates."},
            {"label": "Vendor risk", "value": "Vendor risk register to review findings with severity, status, and owner."},
            {"label": "Task tracker", "value": "Task tracker with status, owner, and due dates to complete tasks."},
        ],
        "template": "<record> with <fields> to <workflow action>.",
    },
    "entities": {
        "id": "entities",
        "prompt": "What records should this app manage?",
        "helper": "Pick the main 'noun' the user will create, update, or close. One or two related records work great.",
        "examples": [
            "support tickets",
            "clients and onboarding tasks",
            "vendor risk findings",
        ],
        "chips": [
            {"label": "tickets", "value": "tickets"},
            {"label": "clients", "value": "clients"},
            {"label": "vendors", "value": "vendors"},
            {"label": "risk findings", "value": "risk findings"},
            {"label": "tasks", "value": "tasks"},
            {"label": "leads", "value": "leads"},
            {"label": "projects", "value": "projects"},
        ],
        "template": None,
    },
    "fields": {
        "id": "fields",
        "prompt": "What fields matter for each record?",
        "helper": "Include a status or priority field if you want a workflow board — every model-driven app needs at least one enum-shaped field.",
        "examples": [
            "title, status, priority, owner, notes",
            "name, owner, due date, status",
            "title, severity, status, owner",
        ],
        "chips": [
            {"label": "title", "value": "title"},
            {"label": "status", "value": "status"},
            {"label": "priority", "value": "priority"},
            {"label": "owner", "value": "owner"},
            {"label": "notes", "value": "notes"},
            {"label": "due date", "value": "due date"},
            {"label": "severity", "value": "severity"},
        ],
        "template": None,
    },
    "workflow": {
        "id": "workflow",
        "prompt": "What's the main workflow action the user takes?",
        "helper": "This becomes a one-click action on each record — usually flipping a status field to a final value.",
        "examples": [
            "close tickets",
            "resolve risk findings",
            "complete onboarding tasks",
        ],
        "chips": [
            {"label": "close", "value": "close tickets"},
            {"label": "resolve", "value": "resolve findings"},
            {"label": "complete", "value": "complete tasks"},
            {"label": "approve", "value": "approve clients"},
            {"label": "triage", "value": "triage records"},
            {"label": "review", "value": "review records"},
        ],
        "template": None,
    },
    "needs_answer": {
        "id": "needs_answer",
        "prompt": "Please answer the last question so I can propose a safe Blueprint change.",
        "helper": "A short phrase is enough — you can also click one of the chips above to fill the input.",
        "examples": [],
        "chips": [],
        "template": None,
    },
}


def _is_vague(text: str) -> bool:
    """Treat very short / stopword-only prompts as needing a templated seed question."""
    if not text or not text.strip():
        return True
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    meaningful = [t for t in tokens if t not in _VAGUE_TOKENS and t not in _STOP_WORDS and len(t) > 2]
    return len(meaningful) < 2


def _build_questions_payload(ids: list[str]) -> tuple[list[str], list[dict[str, Any]]]:
    prompts: list[str] = []
    details: list[dict[str, Any]] = []
    for qid in ids:
        entry = QUESTION_CATALOG.get(qid)
        if not entry:
            continue
        prompts.append(entry["prompt"])
        details.append({
            "id": entry["id"],
            "prompt": entry["prompt"],
            "helper": entry["helper"],
            "examples": list(entry["examples"]),
            "chips": [dict(chip) for chip in entry["chips"]],
            "template": entry["template"],
        })
    return prompts, details


@dataclass
class AssistantState:
    """Client-carried state for a deterministic assistant conversation."""

    status: str = "idle"
    idea: str = ""
    answers: list[str] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    pending_question_ids: list[str] = field(default_factory=list)
    proposal: dict[str, Any] | None = None
    errors: list[str] = field(default_factory=list)

    @classmethod
    def from_payload(cls, value: Any) -> "AssistantState":
        if not isinstance(value, dict):
            return cls()
        return cls(
            status=str(value.get("status") or "idle"),
            idea=str(value.get("idea") or ""),
            answers=[str(item) for item in value.get("answers") or [] if str(item).strip()],
            questions=[str(item) for item in value.get("questions") or [] if str(item).strip()],
            pending_question_ids=[str(item) for item in value.get("pending_question_ids") or [] if str(item).strip()],
            proposal=value.get("proposal") if isinstance(value.get("proposal"), dict) else None,
            errors=[str(item) for item in value.get("errors") or [] if str(item).strip()],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "idea": self.idea,
            "answers": self.answers,
            "questions": self.questions,
            "pending_question_ids": self.pending_question_ids,
            "proposal": self.proposal,
            "errors": self.errors,
        }


class BuilderAssistant:
    """Local scripted assistant for model-driven Blueprint proposals.

    A live-LLM provider can be opted in via ``BuilderAssistant.from_env()``
    (or by passing one directly). When configured, the provider is consulted
    first; if it returns no spec, raises, or produces a Blueprint that fails
    ``DomainPack.model_validate``, the assistant falls back to the scripted
    heuristics and reports the fallback in the per-turn response.
    """

    def __init__(self, *, live_provider: LiveAssistantProvider | None = None):
        self._live_provider = live_provider

    @property
    def live_provider_enabled(self) -> bool:
        return self._live_provider is not None

    @property
    def mode(self) -> str:
        return "live" if self.live_provider_enabled else "scripted"

    @property
    def live_provider(self) -> bool:
        return self.live_provider_enabled

    @classmethod
    def from_env(cls) -> "BuilderAssistant":
        """Construct an assistant honoring ``AGENTFORGE_ASSISTANT_PROVIDER``."""
        from agentforge.planner.live_llm import live_assistant_provider_from_env

        return cls(live_provider=live_assistant_provider_from_env())

    def start(self, idea: str, current_blueprint: dict[str, Any] | None = None) -> dict[str, Any]:
        """Start a conversation from a plain-English app idea."""
        clean_idea = str(idea or "").strip()
        if not clean_idea:
            prompts, details = _build_questions_payload(["idea_seed"])
            state = AssistantState(
                status="needs_clarification",
                idea="",
                questions=prompts,
                pending_question_ids=["idea_seed"],
            )
            return self._response(
                state,
                messages=[QUESTION_CATALOG["idea_seed"]["prompt"]],
                question_details=details,
            )
        state = AssistantState(status="collecting", idea=clean_idea)
        return self._advance(state, current_blueprint=current_blueprint)

    def message(
        self,
        state_payload: dict[str, Any] | None,
        message: str,
        current_blueprint: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Advance a conversation with the user's next answer."""
        state = AssistantState.from_payload(state_payload)
        text = str(message or "").strip()
        if not state.idea and text:
            state.idea = text
        elif text:
            state.answers.append(text)
        if not text:
            state.status = "needs_clarification"
            ids = state.pending_question_ids or ["needs_answer"]
            prompts, details = _build_questions_payload(ids)
            state.questions = prompts
            return self._response(
                state,
                messages=["I need a little more detail before proposing changes."],
                question_details=details,
            )
        return self._advance(state, current_blueprint=current_blueprint)

    def apply_preview(self, proposal: dict[str, Any] | None) -> dict[str, Any]:
        """Validate a proposal before the Builder applies it in memory.

        The frontend re-calls this on Apply so a tampered ``proposal.blueprint``
        cannot bypass schema validation. The post-validation YAML is returned
        alongside the proposal so the in-memory Builder draft and the copied
        YAML stay in sync.
        """
        if not isinstance(proposal, dict) or not isinstance(proposal.get("blueprint"), dict):
            errors = ["assistant proposal must include a blueprint object"]
            return {
                "status": "error",
                "apply_ready": False,
                "errors": errors,
                "guidance": summarize_validation_errors(errors),
            }
        result = validate_blueprint_result(proposal["blueprint"])
        verified = deepcopy(proposal)
        if result.yaml is not None:
            verified["yaml"] = result.yaml
        verified["validation"] = result.to_dict()
        verified["apply_ready"] = result.status == "draft"
        guidance = summarize_validation_errors(result.errors) if result.status != "draft" else []
        return {
            "status": "apply_ready" if result.status == "draft" else "validation_error",
            "apply_ready": result.status == "draft",
            "proposal": verified,
            "validation": result.to_dict(),
            "errors": result.errors,
            "guidance": guidance,
        }

    def _advance(self, state: AssistantState, current_blueprint: dict[str, Any] | None) -> dict[str, Any]:
        combined = _combined_text(state.idea, state.answers)
        missing_ids = _missing_requirement_ids(combined)
        # Live mode can interpret prompts that don't match scripted keywords, so
        # only the truly-vague gate ("idea_seed") still blocks live attempts.
        scripted_gate = bool(missing_ids) and len(state.answers) < 2
        live_gate = "idea_seed" in missing_ids and len(state.answers) < 2
        gate = live_gate if self._live_provider is not None else scripted_gate
        if gate:
            state.status = "needs_clarification"
            prompts, details = _build_questions_payload(missing_ids)
            state.questions = prompts
            state.pending_question_ids = missing_ids
            return self._response(
                state,
                messages=[_summary_message(combined), "I can propose a model-driven Blueprint after these details."],
                question_details=details,
            )

        proposal = self._build_proposal(combined, current_blueprint=current_blueprint)
        state.status = proposal["status"]
        state.questions = []
        state.pending_question_ids = []
        state.proposal = proposal if proposal["status"] == "proposed" else None
        state.errors = proposal.get("errors", [])
        turn_mode = proposal.get("turn_mode", "scripted")
        fallback_reason = proposal.get("fallback_reason")
        if proposal["status"] != "proposed":
            guidance = proposal.get("guidance", [])
            messages = ["I could not produce a valid Blueprint proposal yet."]
            if guidance:
                messages.append(guidance[0]["message"])
                follow_up = guidance[0].get("follow_up_question")
                if follow_up:
                    state.questions = [follow_up]
            return self._response(
                state,
                messages=messages,
                proposal=None,
                guidance=guidance,
                turn_mode=turn_mode,
                fallback_reason=fallback_reason,
            )
        messages = [_summary_message(combined)]
        if turn_mode == "live":
            messages.append("I drafted a validated model-driven Blueprint proposal for review using the live LLM adapter.")
        else:
            messages.append("I drafted a validated model-driven Blueprint proposal for review.")
            if fallback_reason:
                messages.append(f"Live-LLM mode is enabled but I fell back to the scripted path: {fallback_reason}.")
        return self._response(
            state,
            messages=messages,
            proposal=proposal,
            turn_mode=turn_mode,
            fallback_reason=fallback_reason,
        )

    def _build_proposal(self, text: str, current_blueprint: dict[str, Any] | None) -> dict[str, Any]:
        turn_mode = "scripted"
        fallback_reason: str | None = None
        blueprint: dict[str, Any] | None = None
        if self._live_provider is not None:
            live_spec: dict[str, Any] | None = None
            try:
                live_spec = self._live_provider.propose_model_spec(text)
            except Exception as exc:
                fallback_reason = f"live provider raised: {exc.__class__.__name__}"
            if live_spec:
                try:
                    candidate = _model_blueprint_from_spec(text, live_spec)
                except Exception as exc:
                    fallback_reason = f"live spec was unusable: {exc.__class__.__name__}"
                else:
                    check = validate_blueprint_result(candidate)
                    if check.status == "draft":
                        blueprint = candidate
                        turn_mode = "live"
                    else:
                        fallback_reason = "live blueprint failed schema validation"
            elif fallback_reason is None:
                fallback_reason = "live provider returned no spec"
        if blueprint is None:
            blueprint = _model_blueprint_from_text(text)

        assumptions = (
            ["Builder Assistant live-LLM mode produced this draft; verify it before Apply."]
            if turn_mode == "live"
            else ["Builder Assistant scripted mode produced this draft."]
        )
        warnings = ["Review the proposed Blueprint diff before applying it to the in-memory Builder draft."]
        if turn_mode == "scripted" and fallback_reason:
            warnings.append(f"Live-LLM mode was enabled but fell back to scripted: {fallback_reason}.")
        validation = validate_blueprint_result(
            blueprint,
            assumptions=assumptions,
            warnings=warnings,
        )
        if validation.status != "draft":
            return {
                "status": "validation_error",
                "errors": validation.errors,
                "validation": validation.to_dict(),
                "guidance": summarize_validation_errors(validation.errors),
                "turn_mode": turn_mode,
                "fallback_reason": fallback_reason,
            }
        changes = _changes(current_blueprint if isinstance(current_blueprint, dict) else None, blueprint)
        model = blueprint.get("model") or {}
        extras: list[str] = []
        if model.get("imports"):
            extras.append(f"{len(model['imports'])} import(s)")
        if model.get("providers"):
            extras.append(f"{len(model['providers'])} read-only provider(s)")
        summary = f"Create a model-driven app with {len(model.get('entities') or [])} entity/relationship model."
        if extras:
            summary += f" Includes {', '.join(extras)}."
        return {
            "status": "proposed",
            "summary": summary,
            "changes": changes,
            "blueprint": blueprint,
            "yaml": validation.yaml,
            "validation": validation.to_dict(),
            "apply_ready": True,
            "turn_mode": turn_mode,
            "fallback_reason": fallback_reason,
        }

    def _response(
        self,
        state: AssistantState,
        *,
        messages: list[str],
        proposal: dict[str, Any] | None = None,
        guidance: list[dict[str, Any]] | None = None,
        question_details: list[dict[str, Any]] | None = None,
        turn_mode: str | None = None,
        fallback_reason: str | None = None,
    ) -> dict[str, Any]:
        capability_mode = self.mode
        return {
            "mode": capability_mode,
            "live_provider": self.live_provider_enabled,
            "turn_mode": turn_mode or ("scripted" if not self.live_provider_enabled else capability_mode),
            "fallback_reason": fallback_reason,
            "status": state.status,
            "messages": messages,
            "questions": state.questions,
            "question_details": question_details or [],
            "state": state.to_dict(),
            "proposal": proposal,
            "errors": state.errors,
            "guidance": guidance or [],
        }


def _combined_text(idea: str, answers: list[str]) -> str:
    return " ".join([idea, *answers]).strip()


def _missing_requirement_ids(text: str) -> list[str]:
    """Return the QUESTION_CATALOG ids that still need answers for *text*."""
    compact = text.lower().strip()
    if _is_vague(compact):
        return ["idea_seed"]
    ids: list[str] = []
    if not any(word in compact for word in _ENTITY_KEYWORDS):
        ids.append("entities")
    if not any(word in compact for word in _FIELD_KEYWORDS):
        ids.append("fields")
    if not any(word in compact for word in _WORKFLOW_KEYWORDS):
        ids.append("workflow")
    return ids[:3]


def _model_blueprint_from_text(text: str) -> dict[str, Any]:
    return _model_blueprint_from_spec(text, _infer_model_spec(text))


def _model_blueprint_from_spec(text: str, spec: dict[str, Any]) -> dict[str, Any]:
    spec = deepcopy(spec)
    _attach_imports_and_providers(spec, text)
    name = sanitize_pack_name(" ".join(_keywords(text)[:4]) or f"{spec['primary']}-workspace")
    display = name.replace("-", " ").title()
    blueprint = create_starter_blueprint(
        name,
        display_name=display,
        description=f"{text.strip().rstrip('.')}. Drafted by the Builder Assistant.",
        target_user=_target_user(text),
        archetype="model_driven_app",
        optional_modules=[],
        workspace_enabled=False,
        fixture_provider_enabled=True,
    )
    blueprint["model"] = spec["model"]
    blueprint["compatibility_gaps"] = []
    blueprint["future_extensions"] = {"features": ["assistant_refinement", "provider_imports"]}
    return blueprint


_GITHUB_KEYWORDS = ("github", "gh issues")
_HTTP_JSON_KEYWORDS = (
    "http json",
    "json feed",
    "json api",
    "rest feed",
    "external feed",
    "external api",
    "api feed",
    "http feed",
    "webhook feed",
)
_IMPORT_KEYWORDS = ("import", "csv", "spreadsheet", "upload", "bulk load", "seed from file")
_UPSERT_PREFERENCE = ("external_id", "title", "name")


def _wants_github_provider(text: str) -> bool:
    compact = text.lower()
    return any(keyword in compact for keyword in _GITHUB_KEYWORDS)


def _wants_http_json_provider(text: str) -> bool:
    compact = text.lower()
    return any(keyword in compact for keyword in _HTTP_JSON_KEYWORDS)


def _wants_csv_import(text: str) -> bool:
    compact = text.lower()
    return any(keyword in compact for keyword in _IMPORT_KEYWORDS)


def _pick_upsert_key(fields: list[dict[str, Any]]) -> str:
    field_names = {str(field.get("name") or ""): field for field in fields if field.get("name")}
    for candidate in _UPSERT_PREFERENCE:
        if candidate in field_names:
            return candidate
    for field in fields:
        if field.get("required") and field.get("type") in {"string", "integer"}:
            return str(field["name"])
    for field in fields:
        if field.get("type") in {"string", "integer"}:
            return str(field["name"])
    return ""


def _label_to_field_map(fields: list[dict[str, Any]]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for field in fields:
        name = str(field.get("name") or "")
        label = str(field.get("label") or name).strip()
        if name and label:
            mapping[label] = name
    return mapping


def _env_prefix(identifier: str) -> str:
    cleaned = re.sub(r"[^A-Z0-9]+", "_", identifier.upper()).strip("_")
    return cleaned or "EXTERNAL"


def _attach_imports_and_providers(spec: dict[str, Any], text: str) -> None:
    """Suggest imports/providers when the user idea implies them.

    The helper is conservative: a provider is only proposed when an import
    that targets the same entity is also proposed, so ``target_import``
    always resolves and the resulting blueprint stays schema-valid.
    """
    needs_github = _wants_github_provider(text)
    needs_http = _wants_http_json_provider(text)
    needs_csv = _wants_csv_import(text)
    if not (needs_github or needs_http or needs_csv):
        return
    entities = spec["model"]["entities"]
    primary = next((entity for entity in entities if entity.get("name") == spec["primary"]), entities[0])
    primary_name = str(primary["name"])
    upsert_key = _pick_upsert_key(primary["fields"])
    if not upsert_key:
        return
    import_id = f"{primary_name}_import"
    formats = ["csv", "json"] if (needs_github or needs_http or "json" in text.lower()) else ["csv"]
    import_entry: dict[str, Any] = {
        "id": import_id,
        "label": f"Import {primary['label_plural']}",
        "entity": primary_name,
        "formats": formats,
        "upsert_key": upsert_key,
        "field_map": _label_to_field_map(primary["fields"]),
    }
    spec["model"]["imports"] = [import_entry]
    providers: list[dict[str, Any]] = []
    if needs_github:
        providers.append({
            "id": "github_issues",
            "label": "GitHub Issues",
            "type": "github_issues",
            "mode": "read_only",
            "target_import": import_id,
            "env": {"token": "GITHUB_TOKEN", "repo": "GITHUB_REPO"},
            "source": {"state": "open", "labels": []},
        })
    if needs_http:
        prefix = _env_prefix(primary_name)
        providers.append({
            "id": f"{primary_name}_feed",
            "label": f"{primary['label_singular']} Feed",
            "type": "http_json",
            "mode": "read_only",
            "target_import": import_id,
            "env": {"url": f"{prefix}_FEED_URL", "token": f"{prefix}_FEED_TOKEN"},
            "source": {"records_path": "data", "auth": "bearer"},
        })
    if providers:
        spec["model"]["providers"] = providers


def _infer_model_spec(text: str) -> dict[str, Any]:
    compact = text.lower()
    if any(word in compact for word in ["client", "onboarding", "onboard"]):
        return _client_onboarding_model()
    if any(word in compact for word in ["vendor", "risk", "finding"]):
        return _vendor_risk_model()
    if any(word in compact for word in ["issue", "ticket", "support"]):
        return _ticket_model()
    return _task_model()


def _ticket_model() -> dict[str, Any]:
    return {
        "primary": "ticket",
        "model": {
            "entities": [
                {
                    "name": "ticket",
                    "label_singular": "Ticket",
                    "label_plural": "Tickets",
                    "fields": [
                        {"name": "title", "label": "Title", "type": "string", "required": True, "semantic": "title"},
                        {"name": "status", "label": "Status", "type": "enum", "required": True, "enum_values": ["open", "triage", "closed"], "semantic": "status"},
                        {"name": "priority", "label": "Priority", "type": "enum", "enum_values": ["low", "medium", "high"], "semantic": "priority"},
                        {"name": "owner", "label": "Owner", "type": "string", "semantic": "owner"},
                        {"name": "notes", "label": "Notes", "type": "text", "semantic": "description"},
                    ],
                }
            ],
            "pages": [{"name": "dashboard", "type": "dashboard", "title": "Dashboard"}, {"name": "tickets", "type": "entity_list", "entity": "ticket", "title": "Tickets"}],
            "actions": [{"name": "close_ticket", "label": "Close ticket", "type": "update_status", "entity": "ticket", "field": "status", "value": "closed"}],
            "seed_data": {"ticket": [{"title": "Example support issue", "status": "open", "priority": "high", "owner": "Support", "notes": "Triage the reported issue."}]},
            "ui": _board_ui("ticket", group_by="status", title_field="title", badge_field="priority"),
        },
    }


def _client_onboarding_model() -> dict[str, Any]:
    return {
        "primary": "onboarding_task",
        "model": {
            "entities": [
                {"name": "client", "label_singular": "Client", "label_plural": "Clients", "fields": [{"name": "name", "label": "Name", "type": "string", "required": True, "semantic": "title"}, {"name": "owner", "label": "Owner", "type": "string", "semantic": "owner"}]},
                {"name": "onboarding_task", "label_singular": "Onboarding Task", "label_plural": "Onboarding Tasks", "fields": [{"name": "title", "label": "Title", "type": "string", "required": True, "semantic": "title"}, {"name": "status", "label": "Status", "type": "enum", "required": True, "enum_values": ["todo", "doing", "done"], "semantic": "status"}, {"name": "due_date", "label": "Due Date", "type": "date", "semantic": "due_date"}, {"name": "client_id", "label": "Client", "type": "relation", "target_entity": "client"}]},
            ],
            "pages": [{"name": "dashboard", "type": "dashboard", "title": "Dashboard"}, {"name": "clients", "type": "entity_list", "entity": "client", "title": "Clients"}, {"name": "tasks", "type": "entity_list", "entity": "onboarding_task", "title": "Tasks"}],
            "actions": [{"name": "complete_task", "label": "Complete task", "type": "update_status", "entity": "onboarding_task", "field": "status", "value": "done"}],
            "seed_data": {"client": [{"name": "Acme Co", "owner": "Taylor"}], "onboarding_task": [{"title": "Collect launch checklist", "status": "todo", "due_date": "2026-06-01"}]},
            "ui": _board_ui("onboarding_task", secondary_entity="client", group_by="status", title_field="title", badge_field="due_date"),
        },
    }


def _vendor_risk_model() -> dict[str, Any]:
    return {
        "primary": "risk_finding",
        "model": {
            "entities": [
                {"name": "vendor", "label_singular": "Vendor", "label_plural": "Vendors", "fields": [{"name": "name", "label": "Name", "type": "string", "required": True, "semantic": "title"}, {"name": "owner", "label": "Owner", "type": "string", "semantic": "owner"}]},
                {"name": "risk_finding", "label_singular": "Risk Finding", "label_plural": "Risk Findings", "fields": [{"name": "title", "label": "Title", "type": "string", "required": True, "semantic": "title"}, {"name": "severity", "label": "Severity", "type": "enum", "required": True, "enum_values": ["low", "medium", "high", "critical"], "semantic": "severity"}, {"name": "status", "label": "Status", "type": "enum", "required": True, "enum_values": ["open", "review", "resolved"], "semantic": "status"}, {"name": "vendor_id", "label": "Vendor", "type": "relation", "target_entity": "vendor"}]},
            ],
            "pages": [{"name": "dashboard", "type": "dashboard", "title": "Dashboard"}, {"name": "vendors", "type": "entity_list", "entity": "vendor", "title": "Vendors"}, {"name": "findings", "type": "entity_list", "entity": "risk_finding", "title": "Risk Findings"}],
            "actions": [{"name": "resolve_finding", "label": "Resolve finding", "type": "update_status", "entity": "risk_finding", "field": "status", "value": "resolved"}],
            "seed_data": {"vendor": [{"name": "Example Vendor", "owner": "Risk Team"}], "risk_finding": [{"title": "Missing review evidence", "severity": "high", "status": "open"}]},
            "ui": _register_ui("risk_finding", secondary_entity="vendor", title_field="title", badge_field="severity"),
        },
    }


def _task_model() -> dict[str, Any]:
    return {
        "primary": "task",
        "model": {
            "entities": [{"name": "task", "label_singular": "Task", "label_plural": "Tasks", "fields": [{"name": "title", "label": "Title", "type": "string", "required": True, "semantic": "title"}, {"name": "status", "label": "Status", "type": "enum", "required": True, "enum_values": ["todo", "doing", "done"], "semantic": "status"}, {"name": "owner", "label": "Owner", "type": "string", "semantic": "owner"}, {"name": "due_date", "label": "Due Date", "type": "date", "semantic": "due_date"}]}],
            "pages": [{"name": "dashboard", "type": "dashboard", "title": "Dashboard"}, {"name": "tasks", "type": "entity_list", "entity": "task", "title": "Tasks"}],
            "actions": [{"name": "complete_task", "label": "Complete task", "type": "update_status", "entity": "task", "field": "status", "value": "done"}],
            "seed_data": {"task": [{"title": "Example task", "status": "todo", "owner": "Owner", "due_date": "2026-06-01"}]},
            "ui": _board_ui("task", group_by="status", title_field="title", badge_field="owner"),
        },
    }


def _board_ui(primary_entity: str, *, secondary_entity: str = "", group_by: str, title_field: str, badge_field: str) -> dict[str, Any]:
    focus = {"primary_entity": primary_entity, "group_by": group_by, "title_field": title_field, "badge_field": badge_field}
    if secondary_entity:
        focus["secondary_entity"] = secondary_entity
    return {
        "composition": "board_workspace",
        "recipe": "workspace_board",
        "style": {"accent": "emerald", "density": "comfortable", "layout": "workspace"},
        "focus": focus,
        "entities": {primary_entity: {"display": {"layout": "board_by_status", "title_field": title_field, "badge_field": badge_field}}},
        "dashboard": {"title": "Dashboard", "primary_entity": primary_entity, "cards": [{"type": "count", "entity": primary_entity, "label": "Total records"}, {"type": "enum_breakdown", "entity": primary_entity, "field": group_by, "label": "By status"}]},
    }


def _register_ui(primary_entity: str, *, secondary_entity: str = "", title_field: str, badge_field: str) -> dict[str, Any]:
    focus = {"primary_entity": primary_entity, "title_field": title_field, "badge_field": badge_field}
    if secondary_entity:
        focus["secondary_entity"] = secondary_entity
    return {
        "composition": "register_table",
        "recipe": "executive_register",
        "style": {"accent": "amber", "density": "comfortable", "layout": "workspace"},
        "focus": focus,
        "entities": {primary_entity: {"display": {"layout": "table", "title_field": title_field, "badge_field": badge_field}}},
        "dashboard": {"title": "Dashboard", "primary_entity": primary_entity, "cards": [{"type": "count", "entity": primary_entity, "label": "Total records"}]},
    }


def _target_user(text: str) -> str:
    compact = text.lower()
    if "support" in compact:
        return "support operator"
    if "risk" in compact or "vendor" in compact:
        return "risk operator"
    if "client" in compact:
        return "customer success operator"
    return "operator"


def _keywords(text: str) -> list[str]:
    words = [re.sub(r"[^a-z0-9]", "", word.lower()) for word in text.split()]
    return [word for word in words if word and word not in _STOP_WORDS]


def _summary_message(text: str) -> str:
    compact = text.strip().rstrip(".")
    return f"I understand you want: {compact}." if compact else "I need an app idea to continue."


def _changes(current: dict[str, Any] | None, proposed: dict[str, Any]) -> list[dict[str, Any]]:
    if current is None:
        archetype = proposed.get("app_archetype") or "model_driven_app"
        changes: list[dict[str, Any]] = [
            {"path": "/", "operation": "add", "from": None, "to": f"new validated {archetype} Blueprint"},
        ]
        changes.extend(_model_changes(None, proposed.get("model") or {}))
        return changes

    changes: list[dict[str, Any]] = []
    for path in ("name", "display_name", "app_archetype"):
        before = current.get(path)
        after = proposed.get(path)
        if before != after:
            changes.append({"path": f"/{path}", "operation": "replace", "from": before, "to": after})
    if current.get("domain") != proposed.get("domain"):
        changes.append({"path": "/domain", "operation": "replace", "from": current.get("domain"), "to": proposed.get("domain")})
    for path in ("required_shell_modules", "optional_shell_modules"):
        before_list = list(current.get(path) or [])
        after_list = list(proposed.get(path) or [])
        if before_list != after_list:
            changes.append({"path": f"/{path}", "operation": "replace", "from": before_list, "to": after_list})
    before_model = current.get("model") if isinstance(current.get("model"), dict) else None
    after_model = proposed.get("model") or {}
    changes.extend(_model_changes(before_model, after_model))
    return changes


def _model_changes(before: dict[str, Any] | None, after: dict[str, Any]) -> list[dict[str, Any]]:
    if not after:
        return []
    if before is None:
        return [
            {
                "path": "/model",
                "operation": "add",
                "from": None,
                "to": _model_summary(after),
            },
            *_named_list_diff([], after.get("entities") or [], "/model/entities"),
            *_named_list_diff([], after.get("pages") or [], "/model/pages"),
            *_named_list_diff([], after.get("actions") or [], "/model/actions"),
            *_id_list_diff([], after.get("imports") or [], "/model/imports"),
            *_id_list_diff([], after.get("providers") or [], "/model/providers"),
        ]
    changes: list[dict[str, Any]] = []
    changes.extend(_named_list_diff(before.get("entities") or [], after.get("entities") or [], "/model/entities"))
    changes.extend(_named_list_diff(before.get("pages") or [], after.get("pages") or [], "/model/pages"))
    changes.extend(_named_list_diff(before.get("actions") or [], after.get("actions") or [], "/model/actions"))
    changes.extend(_id_list_diff(before.get("imports") or [], after.get("imports") or [], "/model/imports"))
    changes.extend(_id_list_diff(before.get("providers") or [], after.get("providers") or [], "/model/providers"))
    if (before.get("ui") or {}) != (after.get("ui") or {}):
        changes.append({"path": "/model/ui", "operation": "replace", "from": before.get("ui"), "to": after.get("ui")})
    return changes


def _model_summary(model: dict[str, Any]) -> str:
    entities = [str(entity.get("name") or "") for entity in model.get("entities") or [] if entity.get("name")]
    parts = [f"entities: {', '.join(entities) if entities else '(none)'}"]
    if model.get("imports"):
        parts.append(f"imports: {len(model['imports'])}")
    if model.get("providers"):
        parts.append(f"providers: {len(model['providers'])}")
    return "model with " + "; ".join(parts)


def _named_list_diff(
    before: list[dict[str, Any]],
    after: list[dict[str, Any]],
    prefix: str,
) -> list[dict[str, Any]]:
    return _keyed_list_diff(before, after, prefix, key="name")


def _id_list_diff(
    before: list[dict[str, Any]],
    after: list[dict[str, Any]],
    prefix: str,
) -> list[dict[str, Any]]:
    return _keyed_list_diff(before, after, prefix, key="id")


def _keyed_list_diff(
    before: list[dict[str, Any]],
    after: list[dict[str, Any]],
    prefix: str,
    *,
    key: str,
) -> list[dict[str, Any]]:
    before_index = {str(item.get(key)): item for item in before if isinstance(item, dict) and item.get(key)}
    after_index = {str(item.get(key)): item for item in after if isinstance(item, dict) and item.get(key)}
    changes: list[dict[str, Any]] = []
    for name, item in after_index.items():
        if name not in before_index:
            changes.append({"path": f"{prefix}/{name}", "operation": "add", "from": None, "to": item})
        elif before_index[name] != item:
            changes.append({"path": f"{prefix}/{name}", "operation": "replace", "from": before_index[name], "to": item})
    for name, item in before_index.items():
        if name not in after_index:
            changes.append({"path": f"{prefix}/{name}", "operation": "remove", "from": item, "to": None})
    return changes


__all__ = ["AssistantState", "BuilderAssistant"]
