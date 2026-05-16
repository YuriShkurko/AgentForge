"""Tests for Builder Assistant phase 1 deterministic state machine."""
import json
import sys
import threading
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "generator"))

from agentforge.pack import DomainPack
from agentforge.planner.assistant import BuilderAssistant
from agentforge.planner.server import PlannerServer


def test_assistant_start_with_vague_idea_asks_clarifying_questions():
    result = BuilderAssistant().start("app")

    assert result["mode"] == "scripted"
    assert result["live_provider"] is False
    assert result["status"] == "needs_clarification"
    assert result["proposal"] is None
    assert len(result["questions"]) >= 2
    assert result["state"]["idea"] == "app"


def test_assistant_message_advances_from_clarification_to_valid_proposal():
    assistant = BuilderAssistant()
    first = assistant.start("app")

    result = assistant.message(
        first["state"],
        "support tickets with title, status, priority, owner, and notes for triage and close workflow",
    )

    assert result["status"] == "proposed"
    proposal = result["proposal"]
    assert proposal["apply_ready"] is True
    assert proposal["validation"]["status"] == "draft"
    assert proposal["blueprint"]["app_archetype"] == "model_driven_app"
    pack = DomainPack.model_validate(proposal["blueprint"])
    assert pack.model is not None
    assert [entity.name for entity in pack.model.entities] == ["ticket"]
    assert pack.model.ui.composition == "board_workspace"


def test_assistant_start_can_propose_model_driven_client_blueprint():
    result = BuilderAssistant().start(
        "client onboarding app to manage clients and onboarding tasks with status, owner, and due dates"
    )

    assert result["status"] == "proposed"
    proposal = result["proposal"]
    assert proposal["changes"]
    pack = DomainPack.model_validate(proposal["blueprint"])
    assert pack.app_archetype == "model_driven_app"
    assert pack.model is not None
    assert [entity.name for entity in pack.model.entities] == ["client", "onboarding_task"]
    assert pack.model.ui.focus.primary_entity == "onboarding_task"
    assert pack.model.ui.focus.secondary_entity == "client"


def test_assistant_apply_preview_validates_proposal_without_mutating_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assistant = BuilderAssistant()
    result = assistant.start("vendor risk register to review findings with severity status owner")

    preview = assistant.apply_preview(result["proposal"])

    assert preview["status"] == "apply_ready"
    assert preview["apply_ready"] is True
    assert preview["validation"]["status"] == "draft"
    assert list(tmp_path.iterdir()) == []


def test_assistant_apply_preview_rejects_invalid_proposal_shape():
    preview = BuilderAssistant().apply_preview({"summary": "missing blueprint"})

    assert preview["status"] == "error"
    assert preview["apply_ready"] is False
    assert preview["errors"]


def test_assistant_start_with_current_blueprint_returns_field_level_changes():
    current = BuilderAssistant().start("task tracker with status owner due date to complete tasks")["proposal"]["blueprint"]

    result = BuilderAssistant().start(
        "vendor risk register to review findings with severity status owner",
        current_blueprint=current,
    )

    assert result["status"] == "proposed"
    changes = result["proposal"]["changes"]
    paths = {change["path"] for change in changes}
    operations = {change["operation"] for change in changes}
    assert "/name" in paths
    assert any(path.startswith("/model/entities/") for path in paths)
    # The new model introduces vendor + risk_finding entities and removes task.
    assert "add" in operations
    assert "remove" in operations


def test_assistant_diff_lists_per_entity_paths_for_fresh_proposal():
    result = BuilderAssistant().start(
        "support ticket triage with title status priority owner notes to close tickets"
    )

    changes = result["proposal"]["changes"]
    paths = [change["path"] for change in changes]
    assert "/" in paths
    assert "/model" in paths
    assert "/model/entities/ticket" in paths
    assert "/model/pages/tickets" in paths
    # Every change must carry a structured operation token.
    assert all(change["operation"] in {"add", "remove", "replace"} for change in changes)


def test_assistant_apply_preview_returns_yaml_for_in_memory_install():
    proposal = BuilderAssistant().start(
        "support ticket triage with title status priority owner notes to close tickets"
    )["proposal"]

    preview = BuilderAssistant().apply_preview(proposal)

    assert preview["status"] == "apply_ready"
    assert preview["proposal"]["yaml"]
    assert preview["proposal"]["yaml"] == preview["validation"]["yaml"]
    # Re-running apply_preview must remain idempotent for the Builder Apply path.
    again = BuilderAssistant().apply_preview(preview["proposal"])
    assert again["status"] == "apply_ready"
    assert again["proposal"]["blueprint"] == preview["proposal"]["blueprint"]


def test_assistant_apply_preview_rejects_tampered_blueprint():
    proposal = BuilderAssistant().start(
        "support ticket triage with title status priority owner notes to close tickets"
    )["proposal"]

    tampered = {**proposal, "blueprint": {**proposal["blueprint"], "app_archetype": "not_a_real_archetype"}}
    preview = BuilderAssistant().apply_preview(tampered)

    assert preview["status"] == "validation_error"
    assert preview["apply_ready"] is False
    assert preview["errors"]


def test_assistant_message_rejects_empty_answer():
    first = BuilderAssistant().start("app")

    result = BuilderAssistant().message(first["state"], "")

    assert result["status"] == "needs_clarification"
    assert result["questions"] == ["Please answer the last question so I can propose a safe Blueprint change."]
    assert result["proposal"] is None


def test_assistant_proposes_csv_import_with_real_upsert_key_when_idea_mentions_csv():
    proposal = BuilderAssistant().start(
        "support ticket triage with title status priority owner notes to close tickets, import tickets from csv"
    )["proposal"]

    pack = DomainPack.model_validate(proposal["blueprint"])
    assert pack.model is not None and pack.model.imports
    spec = pack.model.imports[0]
    assert spec.entity == "ticket"
    assert "csv" in spec.formats
    field_names = {field.name for field in next(entity for entity in pack.model.entities if entity.name == "ticket").fields}
    assert spec.upsert_key in field_names
    for source_label, target_field in spec.field_map.items():
        assert source_label.strip()
        assert target_field in field_names
    assert pack.model.providers == []


def test_assistant_proposes_github_issues_provider_when_idea_mentions_github():
    proposal = BuilderAssistant().start(
        "support ticket triage with title status priority owner notes to close tickets, sync from github issues"
    )["proposal"]

    pack = DomainPack.model_validate(proposal["blueprint"])
    assert pack.model is not None
    assert pack.model.imports and pack.model.providers
    import_id = pack.model.imports[0].id
    provider = pack.model.providers[0]
    assert provider.type == "github_issues"
    assert provider.mode == "read_only"
    assert provider.target_import == import_id
    assert provider.env.token == "GITHUB_TOKEN"
    assert provider.env.repo == "GITHUB_REPO"
    assert pack.model.imports[0].entity == "ticket"
    assert "csv" in pack.model.imports[0].formats and "json" in pack.model.imports[0].formats


def test_assistant_proposes_http_json_provider_when_idea_mentions_external_feed():
    proposal = BuilderAssistant().start(
        "vendor risk register to review findings with severity status owner, ingest from external http json feed"
    )["proposal"]

    pack = DomainPack.model_validate(proposal["blueprint"])
    assert pack.model is not None
    assert pack.model.providers
    provider = next(prov for prov in pack.model.providers if prov.type == "http_json")
    assert provider.mode == "read_only"
    assert provider.env.url and provider.env.url.endswith("_FEED_URL")
    assert provider.env.url.upper() == provider.env.url
    assert provider.source.records_path == "data"
    assert provider.source.auth in {"none", "bearer"}
    assert provider.target_import in {imp.id for imp in pack.model.imports}


def test_assistant_relation_field_targets_resolve_for_client_onboarding():
    proposal = BuilderAssistant().start(
        "client onboarding app to manage clients and onboarding tasks with status, owner, and due dates"
    )["proposal"]

    pack = DomainPack.model_validate(proposal["blueprint"])
    assert pack.model is not None
    entity_names = {entity.name for entity in pack.model.entities}
    relation_fields = [
        (entity.name, field)
        for entity in pack.model.entities
        for field in entity.fields
        if field.type == "relation"
    ]
    assert relation_fields, "expected at least one relation field in the client onboarding model"
    for owning_entity, field in relation_fields:
        assert field.target_entity in entity_names, (
            f"relation {owning_entity}.{field.name} targets unknown entity {field.target_entity}"
        )


def test_assistant_skips_imports_and_providers_when_idea_has_no_ingest_keywords():
    proposal = BuilderAssistant().start(
        "task tracker with status owner due date to complete tasks"
    )["proposal"]

    pack = DomainPack.model_validate(proposal["blueprint"])
    assert pack.model is not None
    assert pack.model.imports == []
    assert pack.model.providers == []


def test_assistant_apply_preview_rejects_dangling_provider_target_import():
    proposal = BuilderAssistant().start(
        "support ticket triage with title status priority owner notes to close tickets, sync from github issues"
    )["proposal"]

    tampered_blueprint = {**proposal["blueprint"]}
    tampered_blueprint["model"] = {
        **tampered_blueprint["model"],
        "providers": [
            {
                **tampered_blueprint["model"]["providers"][0],
                "target_import": "does_not_exist",
            }
        ],
    }
    tampered = {**proposal, "blueprint": tampered_blueprint}

    preview = BuilderAssistant().apply_preview(tampered)

    assert preview["status"] == "validation_error"
    assert preview["apply_ready"] is False
    assert any("target_import" in error for error in preview["errors"])


def test_assistant_apply_preview_rejects_invalid_provider_env_var_name():
    proposal = BuilderAssistant().start(
        "support ticket triage with title status priority owner notes to close tickets, sync from github issues"
    )["proposal"]

    tampered_blueprint = {**proposal["blueprint"]}
    tampered_blueprint["model"] = {
        **tampered_blueprint["model"],
        "providers": [
            {
                **tampered_blueprint["model"]["providers"][0],
                "env": {"token": "github-token", "repo": "GITHUB_REPO"},
            }
        ],
    }
    tampered = {**proposal, "blueprint": tampered_blueprint}

    preview = BuilderAssistant().apply_preview(tampered)

    assert preview["status"] == "validation_error"
    assert preview["apply_ready"] is False
    assert preview["errors"]


def test_assistant_diff_lists_imports_and_providers_paths_when_ingest_requested():
    result = BuilderAssistant().start(
        "support ticket triage with title status priority owner notes to close tickets, sync from github issues"
    )

    changes = result["proposal"]["changes"]
    paths = [change["path"] for change in changes]
    assert any(path.startswith("/model/imports/") for path in paths)
    assert any(path.startswith("/model/providers/") for path in paths)
    assert all(change["operation"] in {"add", "remove", "replace"} for change in changes)


def test_assistant_http_endpoints_round_trip(tmp_path):
    server = PlannerServer(("127.0.0.1", 0), tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        start = _post_json(base + "/api/planner/assistant/start", {"idea": "app"})
        assert start["status"] == "needs_clarification"

        message = _post_json(
            base + "/api/planner/assistant/message",
            {
                "state": start["state"],
                "message": "support tickets with title status priority owner notes to triage and close",
            },
        )
        assert message["status"] == "proposed"

        preview = _post_json(base + "/api/planner/assistant/apply-preview", {"proposal": message["proposal"]})
        assert preview["status"] == "apply_ready"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _post_json(url, payload):
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))
