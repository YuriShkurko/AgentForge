"""Tests for the v0.7 analysis-only Repo Analyzer."""
import json
import sys
from argparse import Namespace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "generator"))

from agentforge.analyzer import AnalyzeOptions, analyze_repo, render_report
from agentforge.cli import cmd_analyze_repo

FIXTURES = Path(__file__).parent / "fixtures" / "repo_analyzer"


def _module(result, name):
    return next(item for item in result["module_compatibility"] if item["module"] == name)


def test_fastapi_react_detection_and_report_sections():
    result = analyze_repo(FIXTURES / "fastapi_react", AnalyzeOptions(include_tests=True))

    assert any("fastapi" in item for item in result["detected_stack"]["backend"])
    assert any("react" in item for item in result["detected_stack"]["frontend"])
    assert any("pytest" in item for item in result["detected_stack"]["testing"])
    assert _module(result, "deterministic_test_harness")["status"] == "compatible"
    assert result["archetype_candidates"][0]["archetype"] in {"hybrid_agent_pipeline", "ingestion_scoring_pipeline", "agent_dashboard_app"}

    text = render_report(result, "text")
    assert "AgentForge Repo Analyzer Report" in text
    assert "Module Compatibility" in text
    assert "Migration Plan" in text
    assert "Suggested App Blueprint Seed" in text


def test_ignored_directories_do_not_create_false_signals():
    result = analyze_repo(FIXTURES / "ignored_noise")

    assert "node_modules" in result["ignored_paths"]
    assert result["detected_stack"]["frontend"] == []
    assert result["detected_stack"]["backend"] == []


def test_pipeline_only_repo_gets_pipeline_archetype_and_no_frontend_risk():
    result = analyze_repo(FIXTURES / "pipeline_only")

    assert _module(result, "provider_adapter")["status"] == "partial"
    assert _module(result, "pipeline")["status"] == "partial"
    assert result["archetype_candidates"][0]["archetype"] == "ingestion_scoring_pipeline"
    assert any(r["risk"] == "no_frontend" for r in result["risks"])


def test_unknown_minimal_repo_is_conservative():
    result = analyze_repo(FIXTURES / "unknown_minimal", AnalyzeOptions(include_blueprint_draft=False))

    assert result["archetype_candidates"][0]["archetype"] == "unknown/custom"
    assert result["blueprint_seed"] is None
    assert _module(result, "agent_runtime")["status"] == "missing"


def test_ai_chat_hints_detect_agent_runtime_and_mark_observability_partial():
    result = analyze_repo(FIXTURES / "ai_chat")

    assert result["detected_stack"]["ai_agent"]
    assert _module(result, "agent_runtime")["status"] == "partial"
    assert _module(result, "observability_debug")["status"] == "partial"


def test_json_output_shape_and_determinism():
    first = analyze_repo(FIXTURES / "fastapi_react")
    second = analyze_repo(FIXTURES / "fastapi_react")

    assert first["scanned_files"] == second["scanned_files"]
    payload = json.loads(render_report(first, "json"))
    assert set(payload) >= {"repo", "detected_stack", "module_compatibility", "migration_plan", "blueprint_seed"}


def test_cli_json_and_output_file(tmp_path, capsys):
    output = tmp_path / "report.json"
    code = cmd_analyze_repo(
        Namespace(
            path=str(FIXTURES / "fastapi_react"),
            format="text",
            json=True,
            output=str(output),
            max_files=200,
            include_tests=True,
            no_blueprint_draft=False,
        )
    )

    assert code == 0
    assert "Wrote repo analysis report" in capsys.readouterr().out
    assert json.loads(output.read_text(encoding="utf-8"))["repo"]["name"] == "fastapi_react"


def test_cli_missing_path_returns_nonzero(capsys):
    code = cmd_analyze_repo(
        Namespace(
            path=str(FIXTURES / "does-not-exist"),
            format="text",
            json=False,
            output=None,
            max_files=100,
            include_tests=False,
            no_blueprint_draft=False,
        )
    )

    assert code == 1
    assert "repository path not found" in capsys.readouterr().err


def test_markdown_report_uses_markdown_heading():
    result = analyze_repo(FIXTURES / "fastapi_react")
    assert render_report(result, "md").startswith("# AgentForge Repo Analyzer Report")
