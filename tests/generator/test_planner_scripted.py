"""Tests for the v0.6 scripted blueprint planner."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "generator"))

from agentforge.planner import validate_blueprint_result
from agentforge.planner.scripted import CANONICAL_IDEAS, ScriptedPlanner
from agentforge.pack import load_pack


def assert_loads_with_generator_schema(tmp_path, result):
    assert result.status == "draft"
    assert result.blueprint is not None
    assert result.yaml is not None

    output = tmp_path / result.blueprint["name"] / "domain-pack.yaml"
    output.parent.mkdir()
    output.write_text(result.yaml, encoding="utf-8")
    pack = load_pack(output)
    assert pack.name == result.blueprint["name"]
    return pack


@pytest.mark.parametrize("archetype,idea", sorted(CANONICAL_IDEAS.items()))
def test_scripted_planner_draft_for_each_supported_archetype_passes_load_pack(tmp_path, archetype, idea):
    result = ScriptedPlanner().draft(idea)

    pack = assert_loads_with_generator_schema(tmp_path, result)
    assert pack.app_archetype == archetype
    assert result.commands == [
        f"agentforge plan domain-packs/{pack.name}/domain-pack.yaml",
        f"agentforge generate domain-packs/{pack.name}/domain-pack.yaml",
    ]
    assert result.suggested_modules


@pytest.mark.parametrize("idea", ["", "app", "build me an app"])
def test_scripted_planner_vague_idea_returns_clarifying_questions(idea):
    result = ScriptedPlanner().draft(idea)

    assert result.status == "needs_clarification"
    assert 2 <= len(result.questions) <= 5
    assert result.blueprint is None
    assert result.yaml is None


def test_scripted_planner_clarify_returns_targeted_questions():
    result = ScriptedPlanner().clarify("agent dashboard for support work")

    assert result.status == "needs_clarification"
    assert 2 <= len(result.questions) <= 5
    assert any("workspace" in question.lower() for question in result.questions)


def test_scripted_planner_project_workspace_language(tmp_path):
    result = ScriptedPlanner().draft("project workspace task planner for owners and due dates")

    pack = assert_loads_with_generator_schema(tmp_path, result)
    assert pack.app_archetype == "project_workspace_app"
    assert "agent_runtime" in pack.required_shell_modules
    assert all(capability.get("name") != "score_records" for capability in pack.capabilities)
    assert pack.customization.project_workspace.project_label.plural == "projects"
    assert pack.customization.project_workspace.task_label.plural == "tasks"


def test_scripted_planner_lead_scoring_dashboard_maps_to_scoring_family(tmp_path):
    result = ScriptedPlanner().draft("Lead scoring dashboard for sales reps to review the best-fit accounts.")

    pack = assert_loads_with_generator_schema(tmp_path, result)
    assert pack.app_archetype == "ingestion_scoring_pipeline"
    assert pack.customization.scoring.record_label.plural in {"accounts", "leads"}


def test_scripted_planner_support_ticket_customization(tmp_path):
    result = ScriptedPlanner().draft("support ticket triage dashboard for urgent issues")

    pack = assert_loads_with_generator_schema(tmp_path, result)
    assert pack.app_archetype == "notification_triage_app"
    assert pack.customization.scoring.record_label.singular == "ticket"
    assert pack.customization.scoring.record_label.plural == "tickets"
    assert "ticket" in pack.customization.app.workflow_label.lower()


def test_scripted_planner_candidate_review_customization(tmp_path):
    result = ScriptedPlanner().draft("candidate review app for recruiters")

    pack = assert_loads_with_generator_schema(tmp_path, result)
    assert pack.app_archetype == "ingestion_scoring_pipeline"
    assert pack.customization.scoring.record_label.plural == "candidates"


def test_scripted_planner_project_game_workspace_customization(tmp_path):
    result = ScriptedPlanner().draft("project workspace for game development tasks")

    pack = assert_loads_with_generator_schema(tmp_path, result)
    assert pack.app_archetype == "project_workspace_app"
    assert pack.customization.project_workspace.sample_data_label == "game development workspace"


def test_scripted_planner_prior_answers_can_resolve_vague_idea(tmp_path):
    result = ScriptedPlanner().draft(
        "app",
        prior_answers={
            "records": "support tickets",
            "decision": "score and triage urgent issues",
        },
    )

    pack = assert_loads_with_generator_schema(tmp_path, result)
    assert pack.app_archetype == "notification_triage_app"


def test_scripted_planner_refine_add_agent_runtime_returns_valid_blueprint(tmp_path):
    planner = ScriptedPlanner()
    draft = planner.draft("score incoming records")
    assert draft.blueprint is not None

    result = planner.refine(draft.blueprint, "add agent_runtime")

    pack = assert_loads_with_generator_schema(tmp_path, result)
    assert pack.agent_runtime is not None
    assert pack.agent_runtime.enabled is True
    assert "agent_runtime" in pack.optional_shell_modules
    assert any("agent_runtime" in warning for warning in result.warnings)


def test_scripted_planner_refine_add_workspace_returns_valid_blueprint(tmp_path):
    planner = ScriptedPlanner()
    draft = planner.draft("score incoming records")
    assert draft.blueprint is not None
    draft.blueprint["optional_shell_modules"] = [
        module for module in draft.blueprint["optional_shell_modules"] if module != "workspace"
    ]
    draft.blueprint.pop("workspace", None)

    result = planner.refine(draft.blueprint, "add workspace widgets")

    pack = assert_loads_with_generator_schema(tmp_path, result)
    assert pack.workspace is not None
    assert pack.workspace.enabled is True
    assert "workspace" in pack.optional_shell_modules
    assert any("workspace" in warning for warning in result.warnings)


def test_invalid_planner_output_is_rejected_by_validation_layer():
    result = validate_blueprint_result({"name": "broken"})

    assert result.status == "error"
    assert result.errors
    assert result.blueprint is None


def test_scripted_planner_has_no_live_provider_surface():
    assert not hasattr(ScriptedPlanner(), "live_provider")
