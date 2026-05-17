"""Phase 6 live-LLM adapter tests for the Builder Assistant.

The live path is opt-in via ``AGENTFORGE_ASSISTANT_PROVIDER=openai`` and a
``OPENAI_API_KEY``. Tests never reach the network: a ``MockLiveLLMClient`` is
injected directly, and the env-flag behavior is exercised via monkeypatch.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "generator"))

from agentforge.pack import DomainPack
from agentforge.planner.assistant import BuilderAssistant
from agentforge.planner.live_llm import (
    LiveAssistantProvider,
    LiveLLMConfigurationError,
    LiveLLMResponseError,
    OpenAIChatLiveClient,
    live_assistant_provider_from_env,
)


class MockLiveLLMClient:
    """Deterministic stand-in for a live LLM client used by Phase 6 tests."""

    def __init__(self, response: str | Exception, *, expected_system_keyword: str | None = None):
        self.response = response
        self.calls: list[tuple[str, str]] = []
        self.expected_system_keyword = expected_system_keyword

    def complete(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        if self.expected_system_keyword is not None:
            assert self.expected_system_keyword in system
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def _generic_item_spec_json() -> str:
    return json.dumps({
        "primary": "item",
        "entities": [
            {
                "name": "item",
                "label_singular": "Item",
                "label_plural": "Items",
                "fields": [
                    {"name": "title", "label": "Title", "type": "string", "required": True, "semantic": "title"},
                    {"name": "status", "label": "Status", "type": "enum", "required": True,
                     "enum_values": ["open", "closed"], "semantic": "status"},
                    {"name": "notes", "label": "Notes", "type": "text", "semantic": "description"},
                ],
            }
        ],
    })


def _valid_live_spec_json() -> str:
    return json.dumps({
        "primary": "bug_report",
        "entities": [
            {
                "name": "bug_report",
                "label_singular": "Bug Report",
                "label_plural": "Bug Reports",
                "fields": [
                    {"name": "title", "label": "Title", "type": "string", "required": True, "semantic": "title"},
                    {"name": "status", "label": "Status", "type": "enum", "required": True,
                     "enum_values": ["open", "in_review", "fixed"], "semantic": "status"},
                    {"name": "severity", "label": "Severity", "type": "enum",
                     "enum_values": ["low", "high"], "semantic": "severity"},
                    {"name": "owner", "label": "Owner", "type": "string", "semantic": "owner"},
                ],
            }
        ],
    })


# ---------- default-off / env behavior -------------------------------------


def test_default_assistant_has_no_live_provider():
    assistant = BuilderAssistant()
    assert assistant.mode == "scripted"
    assert assistant.live_provider_enabled is False
    assert assistant.live_provider is False


def test_from_env_returns_scripted_when_flag_unset(monkeypatch):
    monkeypatch.delenv("AGENTFORGE_ASSISTANT_PROVIDER", raising=False)
    assistant = BuilderAssistant.from_env()
    assert assistant.mode == "scripted"
    assert assistant.live_provider_enabled is False


@pytest.mark.parametrize("value", ["", "scripted", "local", "off", "SCRIPTED"])
def test_from_env_returns_scripted_for_off_values(monkeypatch, value):
    monkeypatch.setenv("AGENTFORGE_ASSISTANT_PROVIDER", value)
    assistant = BuilderAssistant.from_env()
    assert assistant.live_provider_enabled is False


def test_from_env_rejects_unknown_provider(monkeypatch):
    monkeypatch.setenv("AGENTFORGE_ASSISTANT_PROVIDER", "anthropic")
    with pytest.raises(LiveLLMConfigurationError):
        BuilderAssistant.from_env()


def test_from_env_openai_requires_api_key(monkeypatch):
    monkeypatch.setenv("AGENTFORGE_ASSISTANT_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(LiveLLMConfigurationError):
        BuilderAssistant.from_env()


def test_from_env_openai_builds_provider_when_key_present(monkeypatch):
    monkeypatch.setenv("AGENTFORGE_ASSISTANT_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    provider = live_assistant_provider_from_env()
    assert isinstance(provider, LiveAssistantProvider)
    assert isinstance(provider.client, OpenAIChatLiveClient)
    assert provider.client.api_key == "test-key"


# ---------- live happy path -------------------------------------------------


def test_live_provider_proposal_uses_live_spec_and_passes_schema():
    client = MockLiveLLMClient(_valid_live_spec_json(), expected_system_keyword="live-LLM mode")
    assistant = BuilderAssistant(live_provider=LiveAssistantProvider(client))

    result = assistant.start("track bug reports through triage and fix workflow")

    assert assistant.mode == "live"
    assert result["mode"] == "live"
    assert result["live_provider"] is True
    assert result["status"] == "proposed"
    assert result["turn_mode"] == "live"
    assert result["fallback_reason"] is None
    proposal = result["proposal"]
    assert proposal["apply_ready"] is True
    pack = DomainPack.model_validate(proposal["blueprint"])
    assert pack.model is not None
    assert [entity.name for entity in pack.model.entities] == ["bug_report"]
    field_names = {field.name for field in pack.model.entities[0].fields}
    assert {"title", "status", "severity", "owner"}.issubset(field_names)
    # The live system prompt was actually used.
    assert len(client.calls) == 1


def test_live_proposal_yaml_roundtrips_through_apply_preview():
    client = MockLiveLLMClient(_valid_live_spec_json())
    assistant = BuilderAssistant(live_provider=LiveAssistantProvider(client))

    result = assistant.start("track bug reports through triage and fix workflow")
    preview = BuilderAssistant().apply_preview(result["proposal"])

    assert preview["status"] == "apply_ready"
    assert preview["apply_ready"] is True
    assert preview["proposal"]["yaml"] == result["proposal"]["yaml"]


# ---------- fallback paths --------------------------------------------------


def test_live_provider_falls_back_to_scripted_when_client_raises():
    client = MockLiveLLMClient(RuntimeError("boom"))
    assistant = BuilderAssistant(live_provider=LiveAssistantProvider(client))

    result = assistant.start(
        "support ticket triage with title status priority owner notes to close tickets"
    )

    assert result["status"] == "proposed"
    assert result["mode"] == "live"  # capability mode persists
    assert result["turn_mode"] == "scripted"
    assert result["fallback_reason"] == "live provider completion failed: RuntimeError"
    assert any("fell back to the scripted path" in message for message in result["messages"])
    # Scripted heuristics built a ticket entity.
    pack = DomainPack.model_validate(result["proposal"]["blueprint"])
    assert [entity.name for entity in pack.model.entities] == ["ticket"]


def test_live_prompt_tells_provider_to_prefer_domain_specific_entities():
    client = MockLiveLLMClient(_valid_live_spec_json())
    assistant = BuilderAssistant(live_provider=LiveAssistantProvider(client))

    assistant.start("track bug reports through triage and fix workflow")

    system, _user = client.calls[0]
    assert "Prefer domain-specific entities" in system
    assert "Generic item/record/data entities are allowed only" in system
    assert "session belongs to client" in system
    assert "payment or earning belongs to client/session" in system


def test_live_generic_item_for_domain_prompt_falls_back_to_scripted_domain_model():
    client = MockLiveLLMClient(_generic_item_spec_json())
    assistant = BuilderAssistant(live_provider=LiveAssistantProvider(client))

    result = assistant.start("i am a basketball coach, want to track clients and court vendors")

    assert result["status"] == "proposed"
    assert result["turn_mode"] == "scripted"
    assert result["fallback_reason"] == "live blueprint failed model quality checks"
    pack = DomainPack.model_validate(result["proposal"]["blueprint"])
    assert pack.model is not None
    assert {"client", "court_vendor", "lesson_session"}.issubset({entity.name for entity in pack.model.entities})


def test_live_provider_falls_back_when_response_is_not_json():
    client = MockLiveLLMClient("Sorry, I cannot help with that.")
    assistant = BuilderAssistant(live_provider=LiveAssistantProvider(client))

    result = assistant.start(
        "support ticket triage with title status priority owner notes to close tickets"
    )

    assert result["status"] == "proposed"
    assert result["turn_mode"] == "scripted"
    assert result["fallback_reason"] == "live provider response was not a JSON object"


def test_live_provider_reports_sanitized_openai_status_failure():
    client = MockLiveLLMClient(RuntimeError("OpenAI request failed with status 401"))
    assistant = BuilderAssistant(live_provider=LiveAssistantProvider(client))

    result = assistant.start(
        "support ticket triage with title status priority owner notes to close tickets"
    )

    assert result["turn_mode"] == "scripted"
    assert result["fallback_reason"] == "live provider OpenAI request failed with status 401"
    assert "OPENAI_API_KEY" not in json.dumps(result)


def test_live_provider_direct_error_does_not_include_exception_message():
    client = MockLiveLLMClient(RuntimeError("contains-secret-value"))
    provider = LiveAssistantProvider(client)

    with pytest.raises(LiveLLMResponseError) as raised:
        provider.propose_model_spec("support tickets")

    assert "contains-secret-value" not in str(raised.value)
    assert str(raised.value) == "completion failed: RuntimeError"


def test_live_provider_falls_back_when_spec_is_missing_fields():
    invalid = json.dumps({"primary": "bug", "entities": [{"name": "bug"}]})
    client = MockLiveLLMClient(invalid)
    assistant = BuilderAssistant(live_provider=LiveAssistantProvider(client))

    result = assistant.start(
        "support ticket triage with title status priority owner notes to close tickets"
    )

    assert result["turn_mode"] == "scripted"
    assert result["fallback_reason"]


def test_live_provider_falls_back_when_all_fields_are_invalid():
    """Every field in the primary entity is dropped by the sanitizer."""
    invalid = json.dumps({
        "primary": "thing",
        "entities": [{
            "name": "thing",
            "fields": [
                # Relation to a non-existent entity is stripped by the sanitizer.
                {"name": "owner_id", "type": "relation", "target_entity": "missing_entity"},
                # Enum with too few values is also stripped.
                {"name": "state", "type": "enum", "enum_values": ["one"]},
            ],
        }],
    })
    client = MockLiveLLMClient(invalid)
    assistant = BuilderAssistant(live_provider=LiveAssistantProvider(client))

    result = assistant.start(
        "support ticket triage with title status priority owner notes to close tickets"
    )

    assert result["status"] == "proposed"
    assert result["turn_mode"] == "scripted"
    assert result["fallback_reason"]


def test_live_provider_falls_back_when_blueprint_fails_schema_validation():
    """Spec passes the sanitizer but the resulting Blueprint fails DomainPack."""
    # Duplicate entity names will cause duplicate pages and an invalid Blueprint.
    bad = json.dumps({
        "primary": "alpha",
        "entities": [
            {"name": "alpha", "fields": [
                {"name": "title", "type": "string", "required": True, "semantic": "title"},
                {"name": "status", "type": "enum", "required": True,
                 "enum_values": ["open", "closed"], "semantic": "status"},
            ]},
            {"name": "alpha", "fields": [
                {"name": "title", "type": "string", "required": True, "semantic": "title"},
                {"name": "status", "type": "enum", "required": True,
                 "enum_values": ["open", "closed"], "semantic": "status"},
            ]},
        ],
    })
    client = MockLiveLLMClient(bad)
    assistant = BuilderAssistant(live_provider=LiveAssistantProvider(client))

    result = assistant.start(
        "support ticket triage with title status priority owner notes to close tickets"
    )

    # The duplicate entity should cause DomainPack to reject the Blueprint.
    # Either the spec was sanitized out or DomainPack rejected it — either way: fallback.
    assert result["turn_mode"] == "scripted"
    assert result["fallback_reason"]


# ---------- no real network calls in default mode --------------------------


def test_live_mode_is_off_by_default_so_no_network_function_can_be_called(monkeypatch):
    """Belt-and-suspenders: with env unset, building a fresh assistant must not import or call any network client."""
    monkeypatch.delenv("AGENTFORGE_ASSISTANT_PROVIDER", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    def _explode(*_args, **_kwargs):  # pragma: no cover - defensive
        raise AssertionError("default assistant must not open URLs")

    monkeypatch.setattr(urllib.request, "urlopen", _explode)

    assistant = BuilderAssistant.from_env()
    result = assistant.start("support tickets with title status priority owner notes to close tickets")

    assert assistant.live_provider_enabled is False
    assert result["mode"] == "scripted"
    assert result["status"] == "proposed"


def test_openai_client_does_not_log_api_key_in_repr(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-supersecret-test-only")
    client = OpenAIChatLiveClient.from_env()
    representation = repr(client)
    assert "sk-supersecret-test-only" not in representation


# ---------- status endpoint reflects live capability ------------------------


def test_status_endpoint_reflects_live_capability(monkeypatch, tmp_path):
    """The /api/planner/status response advertises the configured assistant mode."""
    import threading

    from agentforge.planner.server import PlannerServer

    monkeypatch.setenv("AGENTFORGE_ASSISTANT_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    server = PlannerServer(("127.0.0.1", 0), tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with urllib.request.urlopen(base + "/api/planner/status", timeout=5) as response:
            body: dict[str, Any] = json.loads(response.read().decode("utf-8"))
        assert body["mode"] == "live"
        assert body["live_provider"] is True
        assert body["planner_available"] is True
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
