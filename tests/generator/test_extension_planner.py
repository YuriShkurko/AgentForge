"""Tests for the v0.8 planning-only Repo Extension Planner."""
import json
import sys
from argparse import Namespace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "generator"))

from agentforge.analyzer import analyze_repo
from agentforge.cli import cmd_plan_extension
from agentforge.extension_planner import ExtensionPlanOptions, plan_extension, render_extension_plan

FIXTURES = Path(__file__).parent / "fixtures" / "repo_analyzer"


def _module(plan, name):
    return next(item for item in plan["module_plans"] if item["module"] == name)


def test_direct_repo_path_produces_extension_plan_without_modifying_files():
    repo = FIXTURES / "fastapi_react"
    before = sorted((p.relative_to(repo).as_posix(), p.stat().st_size) for p in repo.rglob("*") if p.is_file())

    plan = plan_extension(repo, ExtensionPlanOptions(modules=("agent_runtime", "dashboard_workspace"), include_tests=True))

    after = sorted((p.relative_to(repo).as_posix(), p.stat().st_size) for p in repo.rglob("*") if p.is_file())
    assert before == after
    assert plan["target_repo"]["files_modified"] == 0
    assert plan["target_repo"]["source"] == "repo_path"
    assert plan["no_files_modified_statement"].startswith("No files were modified")
    assert _module(plan, "agent_runtime")["likely_files_to_add"]
    assert "frontend/src/components/WorkspacePanel.tsx" in _module(plan, "dashboard_workspace")["likely_files_to_add"]


def test_analyzer_json_report_input_produces_stable_plan(tmp_path):
    report = analyze_repo(FIXTURES / "pipeline_only")
    report_path = tmp_path / "analysis.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")

    first = plan_extension(report_path, ExtensionPlanOptions(from_report=True, modules=("provider_adapter,pipeline,ci_local_validation",)))
    second = plan_extension(report_path, ExtensionPlanOptions(from_report=True, modules=("provider_adapter,pipeline,ci_local_validation",)))

    assert first["target_repo"]["source"] == "analyzer_report"
    assert first["selected_modules"] == ["provider_adapter", "pipeline", "ci_local_validation"]
    assert first["migration_phases"] == second["migration_phases"]
    assert "backend/app/providers/" in first["file_impact"]["likely_files_to_add"]


def test_unsupported_modules_become_gaps_and_selected_modules_are_honored():
    plan = plan_extension(
        FIXTURES / "unknown_minimal",
        ExtensionPlanOptions(modules=("agent_runtime,live_llm_provider,deploy_planner",)),
    )

    assert plan["selected_modules"] == ["agent_runtime"]
    assert {item["module"] for item in plan["unsupported_items"]} == {"deploy_planner", "live_llm_provider"}
    assert any(risk["risk"] == "unsupported_requested_module" for risk in plan["risks"])
    assert _module(plan, "agent_runtime")["status"] == "blocked"


def test_recommendations_are_conservative_when_modules_omitted():
    plan = plan_extension(FIXTURES / "pipeline_only")

    assert "provider_adapter" in plan["recommended_modules"]
    assert "pipeline" in plan["recommended_modules"]
    assert "deterministic_test_harness" in plan["recommended_modules"]
    assert plan["selected_modules"] == plan["recommended_modules"]


def test_markdown_and_json_reports_include_required_sections():
    plan = plan_extension(FIXTURES / "fastapi_react", ExtensionPlanOptions(modules=("agent_runtime",)))

    md = render_extension_plan(plan, "md")
    assert md.startswith("# AgentForge Repo Extension Plan")
    assert "No files were modified" in md
    assert "## File Impact" in md
    assert "## Migration Phases" in md
    assert "## Validation Commands" in md

    payload = json.loads(render_extension_plan(plan, "json"))
    assert set(payload) >= {"target_repo", "module_plans", "file_impact", "migration_phases", "commands_to_run"}


def test_cli_plan_extension_from_report_and_output_file(tmp_path, capsys):
    report_path = tmp_path / "analysis.json"
    report_path.write_text(json.dumps(analyze_repo(FIXTURES / "fastapi_react")), encoding="utf-8")
    output = tmp_path / "extension-plan.json"

    code = cmd_plan_extension(
        Namespace(
            target=str(report_path),
            from_report=True,
            modules="agent_runtime,dashboard_workspace",
            format="text",
            json=True,
            output=str(output),
            max_files=100,
            include_tests=False,
        )
    )

    assert code == 0
    assert "Wrote repo extension plan" in capsys.readouterr().out
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["selected_modules"] == ["agent_runtime", "dashboard_workspace"]


def test_cli_missing_path_error_is_clear(capsys):
    code = cmd_plan_extension(
        Namespace(
            target=str(FIXTURES / "missing"),
            from_report=False,
            modules=None,
            format="text",
            json=False,
            output=None,
            max_files=100,
            include_tests=False,
        )
    )

    assert code == 1
    assert "repository path not found" in capsys.readouterr().err
