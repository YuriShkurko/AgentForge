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
