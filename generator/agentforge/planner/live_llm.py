"""Optional live-LLM adapter for the Builder Assistant.

Off by default. Only opt-in via ``AGENTFORGE_ASSISTANT_PROVIDER=openai`` plus
``OPENAI_API_KEY``. Every model output is parsed strictly as JSON and converted
to a bounded ``model_driven_app`` spec; the caller (``BuilderAssistant``) then
validates the resulting Blueprint with ``DomainPack.model_validate`` before any
proposal is offered for Apply. Live output is never trusted as-is.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Protocol


_VALID_FIELD_TYPES = {"string", "text", "integer", "boolean", "date", "enum", "relation"}
_VALID_SEMANTICS = {"title", "status", "priority", "owner", "severity", "due_date", "description"}

_DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
_OPENAI_ENDPOINT = "https://api.openai.com/v1/chat/completions"

_SYSTEM_PROMPT = (
    "You are AgentForge Builder Assistant in live-LLM mode. "
    "Emit a model-driven application spec as STRICT JSON only. "
    "No prose. No markdown. No code fences.\n"
    "Use snake_case entity and field names. "
    "Every required enum field must list at least two values and one terminal state.\n"
    "Allowed field types: string, text, integer, boolean, date, enum, relation.\n"
    "Field semantic must be one of: title, status, priority, owner, severity, "
    "due_date, description -- or omitted.\n"
    "Schema:\n"
    "{\n"
    "  \"primary\": \"<snake_case entity name>\",\n"
    "  \"entities\": [\n"
    "    {\"name\": \"...\", \"label_singular\": \"...\", \"label_plural\": \"...\",\n"
    "     \"fields\": [{\"name\": \"...\", \"label\": \"...\", \"type\": \"...\",\n"
    "                 \"required\": true|false, \"enum_values\": [...],\n"
    "                 \"semantic\": \"...\", \"target_entity\": \"...\"}]}\n"
    "  ]\n"
    "}"
)


class LiveLLMClient(Protocol):
    """Minimal completion contract that the live provider depends on."""

    def complete(self, system: str, user: str) -> str: ...


class LiveLLMConfigurationError(RuntimeError):
    """Raised when live mode is requested but not configured correctly."""


class LiveAssistantProvider:
    """Bounded live-LLM adapter that returns a model spec or ``None``.

    The provider never proposes a Blueprint directly. It returns the same
    ``{"primary": ..., "model": {...}}`` shape that the scripted heuristics
    return, so the surrounding deterministic scaffolding (imports/providers,
    starter blueprint, validation) stays in charge.
    """

    name = "live"

    def __init__(self, client: LiveLLMClient, *, max_entities: int = 4):
        self.client = client
        self.max_entities = max(1, int(max_entities))

    def propose_model_spec(self, text: str) -> dict[str, Any] | None:
        prompt = (text or "").strip()
        if not prompt:
            return None
        try:
            raw = self.client.complete(_SYSTEM_PROMPT, prompt)
        except Exception:
            return None
        parsed = _safe_parse_json(raw)
        if not isinstance(parsed, dict):
            return None
        entities = parsed.get("entities")
        primary = parsed.get("primary")
        if not isinstance(entities, list) or not entities:
            return None
        if not isinstance(primary, str) or not primary.strip():
            return None
        capped = entities[: self.max_entities]
        model = _spec_to_model(capped, primary.strip())
        if not model:
            return None
        return {"primary": primary.strip(), "model": model}


def _safe_parse_json(raw: str) -> Any:
    text = (raw or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    cleaned = re.sub(r"^```(?:json)?\s*", "", text)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except Exception:
        return None


def _spec_to_model(entities: list[Any], primary: str) -> dict[str, Any]:
    clean_entities: list[dict[str, Any]] = []
    for entity in entities:
        cleaned = _clean_entity(entity)
        if cleaned:
            clean_entities.append(cleaned)
    if not clean_entities:
        return {}
    entity_names = {entity["name"] for entity in clean_entities}
    for entity in clean_entities:
        entity["fields"] = [
            field
            for field in entity["fields"]
            if field["type"] != "relation" or field.get("target_entity") in entity_names
        ]
    primary_entity = next((entity for entity in clean_entities if entity["name"] == primary), clean_entities[0])
    primary_name = primary_entity["name"]
    if not primary_entity["fields"]:
        return {}
    title_field = (
        _find_by_semantic(primary_entity["fields"], "title")
        or primary_entity["fields"][0]
    )
    status_field = _find_by_semantic(primary_entity["fields"], "status")
    badge_field = (
        _find_by_semantic(primary_entity["fields"], "priority")
        or _find_by_semantic(primary_entity["fields"], "severity")
        or _find_by_semantic(primary_entity["fields"], "owner")
        or title_field
    )
    secondary_name = next((entity["name"] for entity in clean_entities if entity["name"] != primary_name), "")
    pages: list[dict[str, Any]] = [{"name": "dashboard", "type": "dashboard", "title": "Dashboard"}]
    for entity in clean_entities:
        pages.append({
            "name": _page_name(entity["name"]),
            "type": "entity_list",
            "entity": entity["name"],
            "title": entity["label_plural"],
        })
    actions: list[dict[str, Any]] = []
    if status_field and status_field["type"] == "enum":
        terminal = status_field["enum_values"][-1]
        actions.append({
            "name": f"advance_{primary_name}",
            "label": f"Advance {primary_entity['label_singular'].lower()}",
            "type": "update_status",
            "entity": primary_name,
            "field": status_field["name"],
            "value": terminal,
        })
    seed_record = {field["name"]: _sample_value(field) for field in primary_entity["fields"] if field["type"] != "relation"}
    seed_data = {primary_name: [seed_record]} if seed_record else {}
    if status_field:
        focus = {
            "primary_entity": primary_name,
            "group_by": status_field["name"],
            "title_field": title_field["name"],
            "badge_field": badge_field["name"],
        }
        if secondary_name:
            focus["secondary_entity"] = secondary_name
        ui = {
            "composition": "board_workspace",
            "recipe": "workspace_board",
            "style": {"accent": "emerald", "density": "comfortable", "layout": "workspace"},
            "focus": focus,
            "entities": {primary_name: {"display": {
                "layout": "board_by_status",
                "title_field": title_field["name"],
                "badge_field": badge_field["name"],
            }}},
            "dashboard": {
                "title": "Dashboard",
                "primary_entity": primary_name,
                "cards": [
                    {"type": "count", "entity": primary_name, "label": "Total records"},
                    {"type": "enum_breakdown", "entity": primary_name, "field": status_field["name"], "label": "By status"},
                ],
            },
        }
    else:
        focus = {
            "primary_entity": primary_name,
            "title_field": title_field["name"],
            "badge_field": badge_field["name"],
        }
        if secondary_name:
            focus["secondary_entity"] = secondary_name
        ui = {
            "composition": "register_table",
            "recipe": "executive_register",
            "style": {"accent": "amber", "density": "comfortable", "layout": "workspace"},
            "focus": focus,
            "entities": {primary_name: {"display": {
                "layout": "table",
                "title_field": title_field["name"],
                "badge_field": badge_field["name"],
            }}},
            "dashboard": {
                "title": "Dashboard",
                "primary_entity": primary_name,
                "cards": [{"type": "count", "entity": primary_name, "label": "Total records"}],
            },
        }
    return {
        "entities": clean_entities,
        "pages": pages,
        "actions": actions,
        "seed_data": seed_data,
        "ui": ui,
    }


def _clean_entity(entity: Any) -> dict[str, Any] | None:
    if not isinstance(entity, dict):
        return None
    name = _snake(str(entity.get("name") or ""))
    if not name:
        return None
    fields = entity.get("fields")
    if not isinstance(fields, list):
        return None
    clean_fields: list[dict[str, Any]] = []
    seen: set[str] = set()
    for field in fields:
        cleaned = _clean_field(field)
        if not cleaned:
            continue
        if cleaned["name"] in seen:
            continue
        seen.add(cleaned["name"])
        clean_fields.append(cleaned)
    if not clean_fields:
        return None
    return {
        "name": name,
        "label_singular": str(entity.get("label_singular") or name.replace("_", " ").title()),
        "label_plural": str(entity.get("label_plural") or (name.replace("_", " ").title() + "s")),
        "fields": clean_fields,
    }


def _clean_field(field: Any) -> dict[str, Any] | None:
    if not isinstance(field, dict):
        return None
    name = _snake(str(field.get("name") or ""))
    if not name:
        return None
    field_type = str(field.get("type") or "string").strip().lower()
    if field_type not in _VALID_FIELD_TYPES:
        return None
    cleaned: dict[str, Any] = {
        "name": name,
        "label": str(field.get("label") or name.replace("_", " ").title()),
        "type": field_type,
    }
    if field.get("required"):
        cleaned["required"] = True
    semantic = str(field.get("semantic") or "").strip().lower()
    if semantic in _VALID_SEMANTICS:
        cleaned["semantic"] = semantic
    if field_type == "enum":
        values = field.get("enum_values")
        if not isinstance(values, list):
            return None
        clean_values = [str(value).strip() for value in values if str(value).strip()]
        if len(clean_values) < 2:
            return None
        cleaned["enum_values"] = clean_values
    if field_type == "relation":
        target = field.get("target_entity")
        if not isinstance(target, str) or not target.strip():
            return None
        cleaned["target_entity"] = _snake(target)
    return cleaned


def _find_by_semantic(fields: list[dict[str, Any]], semantic: str) -> dict[str, Any] | None:
    for field in fields:
        if field.get("semantic") == semantic:
            return field
    return None


def _page_name(entity_name: str) -> str:
    return entity_name if entity_name.endswith("s") else entity_name + "s"


def _sample_value(field: dict[str, Any]) -> Any:
    field_type = field.get("type")
    if field_type == "enum":
        values = field.get("enum_values") or [""]
        return values[0]
    if field_type == "integer":
        return 0
    if field_type == "boolean":
        return False
    if field_type == "date":
        return "2026-06-01"
    label = field.get("label") or field.get("name") or "value"
    return f"Example {label}"


def _snake(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9]+", "_", str(value).strip()).strip("_").lower()
    return text


class OpenAIChatLiveClient:
    """Minimal OpenAI Chat Completions client for live builder assistance."""

    def __init__(self, api_key: str, model: str = _DEFAULT_OPENAI_MODEL, timeout: float = 30.0):
        if not api_key:
            raise LiveLLMConfigurationError(
                "AGENTFORGE_ASSISTANT_PROVIDER=openai requires OPENAI_API_KEY"
            )
        self.api_key = api_key
        self.model = model or _DEFAULT_OPENAI_MODEL
        self.timeout = timeout

    @classmethod
    def from_env(cls) -> "OpenAIChatLiveClient":
        api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
        if not api_key:
            raise LiveLLMConfigurationError(
                "AGENTFORGE_ASSISTANT_PROVIDER=openai requires OPENAI_API_KEY"
            )
        model = (os.environ.get("AGENTFORGE_ASSISTANT_LLM_MODEL") or _DEFAULT_OPENAI_MODEL).strip()
        return cls(api_key=api_key, model=model)

    def complete(self, system: str, user: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            _OPENAI_ENDPOINT,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"OpenAI request failed with status {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"OpenAI request failed: {exc.reason}") from exc
        try:
            return str(data["choices"][0]["message"]["content"]).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("OpenAI response did not include assistant content") from exc


def live_assistant_provider_from_env() -> LiveAssistantProvider | None:
    """Return a configured ``LiveAssistantProvider`` when env opts in, else ``None``."""
    selected = (os.environ.get("AGENTFORGE_ASSISTANT_PROVIDER") or "").strip().lower()
    if selected in {"", "scripted", "local", "off"}:
        return None
    if selected == "openai":
        return LiveAssistantProvider(OpenAIChatLiveClient.from_env())
    raise LiveLLMConfigurationError(
        f"Unsupported AGENTFORGE_ASSISTANT_PROVIDER={selected!r}. Use 'scripted' or 'openai'."
    )


__all__ = [
    "LiveAssistantProvider",
    "LiveLLMClient",
    "LiveLLMConfigurationError",
    "OpenAIChatLiveClient",
    "live_assistant_provider_from_env",
]
