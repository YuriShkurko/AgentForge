"""Phase 5 validation-guidance tests for the Builder Assistant."""
import sys
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "generator"))

from agentforge.planner.assistant import BuilderAssistant
from agentforge.planner.validation_guidance import summarize_validation_errors


def _ticket_proposal():
    return BuilderAssistant().start(
        "support ticket triage with title status priority owner notes to close tickets"
    )["proposal"]


def _github_ticket_proposal():
    return BuilderAssistant().start(
        "support ticket triage with title status priority owner notes to close tickets, sync from github issues"
    )["proposal"]


def _tamper(proposal, mutator):
    tampered = deepcopy(proposal)
    mutator(tampered["blueprint"])
    return tampered


def test_summarize_classifies_missing_relation_target():
    raw = "invalid App Blueprint: relation field 'order.client_id' targets unknown entity 'client'"
    [entry] = summarize_validation_errors([raw])
    assert entry["category"] == "missing_relation_target"
    assert entry["error"] == raw  # raw text is preserved, never hidden
    assert "client" in entry["suggested_fix"]
    assert entry["follow_up_question"]


def test_summarize_classifies_missing_enum_values():
    raw = "Value error, enum field 'priority' must define enum_values"
    [entry] = summarize_validation_errors([raw])
    assert entry["category"] == "missing_enum_values"
    assert "priority" in entry["message"]
    assert entry["follow_up_question"]


def test_summarize_classifies_invalid_enum_value_for_update_status():
    raw = "update_status action 'close_ticket' value must be one of ['open', 'triage']"
    [entry] = summarize_validation_errors([raw])
    assert entry["category"] == "invalid_enum_value"
    assert "open" in entry["suggested_fix"]


def test_summarize_classifies_bad_provider_env_var_name():
    raw = "provider env.token must be an UPPER_SNAKE_CASE env var name; got 'github-token'"
    [entry] = summarize_validation_errors([raw])
    assert entry["category"] == "bad_provider_env"
    assert "UPPER_SNAKE_CASE" in entry["suggested_fix"]
    assert "names" in entry["suggested_fix"].lower()


def test_summarize_classifies_missing_target_import():
    raw = "provider 'github_issues' target_import references unknown import 'missing_import'"
    [entry] = summarize_validation_errors([raw])
    assert entry["category"] == "missing_target_import"
    assert "missing_import" in entry["suggested_fix"]
    assert entry["follow_up_question"]


def test_summarize_classifies_unsupported_ui_focus_field():
    raw = "ui focus group_by references unknown field 'severity' on 'ticket'"
    [entry] = summarize_validation_errors([raw])
    assert entry["category"] == "unsupported_ui_field"
    assert "severity" in entry["suggested_fix"]


def test_summarize_classifies_unsupported_ui_entity_display_field():
    raw = "ui entity 'ticket' badge_field references unknown field 'severity'"
    [entry] = summarize_validation_errors([raw])
    assert entry["category"] == "unsupported_ui_field"
    assert "badge_field" in entry["message"]


def test_summarize_returns_unknown_for_unrecognized_error_but_keeps_raw_text():
    raw = "some unexpected validation error nobody anticipated"
    [entry] = summarize_validation_errors([raw])
    assert entry["category"] == "unknown"
    assert entry["error"] == raw
    assert entry["suggested_fix"]


def test_apply_preview_attaches_guidance_for_dangling_target_import():
    proposal = _github_ticket_proposal()
    tampered = _tamper(proposal, lambda bp: bp["model"]["providers"].__setitem__(
        0, {**bp["model"]["providers"][0], "target_import": "does_not_exist"}
    ))

    preview = BuilderAssistant().apply_preview(tampered)

    assert preview["status"] == "validation_error"
    assert preview["apply_ready"] is False
    assert preview["errors"], "raw errors must remain visible alongside guidance"
    categories = [entry["category"] for entry in preview["guidance"]]
    assert "missing_target_import" in categories


def test_apply_preview_attaches_guidance_for_bad_env_var_name():
    proposal = _github_ticket_proposal()
    tampered = _tamper(proposal, lambda bp: bp["model"]["providers"].__setitem__(
        0, {**bp["model"]["providers"][0], "env": {"token": "github-token", "repo": "GITHUB_REPO"}}
    ))

    preview = BuilderAssistant().apply_preview(tampered)

    assert preview["status"] == "validation_error"
    assert any(entry["category"] == "bad_provider_env" for entry in preview["guidance"])
    # The Builder must show env-var-name guidance without storing the token value itself.
    for entry in preview["guidance"]:
        assert "github-token" not in entry["suggested_fix"]


def test_apply_preview_attaches_guidance_for_missing_relation_target():
    proposal = _ticket_proposal()
    def _break_relation(bp):
        ticket = bp["model"]["entities"][0]
        ticket["fields"].append({
            "name": "client_id",
            "label": "Client",
            "type": "relation",
            "target_entity": "client_that_does_not_exist",
        })
    tampered = _tamper(proposal, _break_relation)

    preview = BuilderAssistant().apply_preview(tampered)

    assert preview["status"] == "validation_error"
    categories = [entry["category"] for entry in preview["guidance"]]
    assert "missing_relation_target" in categories


def test_apply_preview_attaches_guidance_for_invalid_enum_value():
    proposal = _ticket_proposal()
    def _break_enum(bp):
        action = bp["model"]["actions"][0]
        action["value"] = "not_a_real_state"
    tampered = _tamper(proposal, _break_enum)

    preview = BuilderAssistant().apply_preview(tampered)

    assert preview["status"] == "validation_error"
    assert any(entry["category"] == "invalid_enum_value" for entry in preview["guidance"])


def test_apply_preview_attaches_guidance_for_unsupported_ui_field():
    proposal = _ticket_proposal()
    def _break_ui(bp):
        bp["model"]["ui"]["focus"]["group_by"] = "this_field_does_not_exist"
    tampered = _tamper(proposal, _break_ui)

    preview = BuilderAssistant().apply_preview(tampered)

    assert preview["status"] == "validation_error"
    assert any(entry["category"] == "unsupported_ui_field" for entry in preview["guidance"])


def test_apply_preview_keeps_raw_errors_visible_with_guidance():
    proposal = _github_ticket_proposal()
    tampered = _tamper(proposal, lambda bp: bp["model"]["providers"].__setitem__(
        0, {**bp["model"]["providers"][0], "target_import": "does_not_exist"}
    ))

    preview = BuilderAssistant().apply_preview(tampered)

    assert preview["errors"], "raw error list must persist on the response"
    raw_errors_in_guidance = {entry["error"] for entry in preview["guidance"]}
    assert all(error in raw_errors_in_guidance for error in preview["errors"])


def test_apply_preview_does_not_auto_fix_or_apply_tampered_blueprint():
    proposal = _github_ticket_proposal()
    tampered = _tamper(proposal, lambda bp: bp["model"]["providers"].__setitem__(
        0, {**bp["model"]["providers"][0], "target_import": "does_not_exist"}
    ))

    preview = BuilderAssistant().apply_preview(tampered)

    # No destructive auto-fix: the blueprint inside the verified proposal is the user's
    # tampered input, not a silently repaired copy, and apply_ready stays False.
    assert preview["apply_ready"] is False
    returned_blueprint = preview["proposal"]["blueprint"]
    assert returned_blueprint["model"]["providers"][0]["target_import"] == "does_not_exist"


def test_apply_preview_with_missing_blueprint_emits_guidance():
    preview = BuilderAssistant().apply_preview({"summary": "no blueprint key"})

    assert preview["status"] == "error"
    assert preview["apply_ready"] is False
    assert preview["guidance"]
    assert preview["guidance"][0]["category"] == "missing_blueprint"


def test_assistant_response_carries_empty_guidance_on_happy_path():
    result = BuilderAssistant().start(
        "support ticket triage with title status priority owner notes to close tickets"
    )

    assert result["status"] == "proposed"
    assert result["guidance"] == []
