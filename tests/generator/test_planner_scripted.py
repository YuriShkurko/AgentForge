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
        f"agentforge plan ./domain-packs/{pack.name}/domain-pack.yaml",
        f"agentforge generate ./domain-packs/{pack.name}/domain-pack.yaml --force",
    ]
    assert result.suggested_modules


@pytest.mark.parametrize("idea", ["", "app", "build me an app"])
def test_scripted_planner_vague_idea_returns_clarifying_questions(idea):
    result = ScriptedPlanner().draft(idea)

    assert result.status == "needs_clarification"
    assert 2 <= len(result.questions) <= 5
    assert result.blueprint is None
    assert result.yaml is None


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
