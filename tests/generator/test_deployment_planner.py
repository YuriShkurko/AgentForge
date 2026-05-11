"""Tests for v0.9 planning-only Deployment Planner."""
import json
import shutil
import sys
from argparse import Namespace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "generator"))

from agentforge.analyzer import analyze_repo
from agentforge.cli import cmd_plan_deployment
from agentforge.deployment_planner import DeploymentPlanOptions, plan_deployment, render_deployment_plan

FIXTURES = Path(__file__).parent / "fixtures" / "repo_analyzer"


def _copy(src: Path, dst: Path) -> Path:
    shutil.copytree(src, dst)
    return dst


def _files(repo: Path) -> list[str]:
    return sorted(p.relative_to(repo).as_posix() for p in repo.rglob("*") if p.is_file() and ".git" not in p.parts)


def test_fastapi_react_detection_and_readiness_without_modifying_target(tmp_path):
    repo = _copy(FIXTURES / "fastapi_react", tmp_path / "repo")
    before = _files(repo)

    plan = plan_deployment(repo, DeploymentPlanOptions(include_tests=True, include_cost_notes=True))

    assert _files(repo) == before
    assert plan["target_repo"]["files_modified"] == 0
    assert plan["detected_stack"]["backend"]["framework"] == "fastapi"
    assert plan["detected_stack"]["frontend"]["framework"] == "vite/react"
    assert "sqlite" in plan["detected_stack"]["database"]["types"]
    assert plan["detected_stack"]["docker"]["dockerfiles"] == ["Dockerfile"]
    assert plan["detected_stack"]["ci_cd"]["github_actions"] == [".github/workflows/ci.yml"]
    assert any(item["item"] == ".env.example present" and item["status"] == "present" for item in plan["env_checklist"])
    assert any("No deployment was performed" in plan["not_executed_warning"] for _ in [0])


def test_unknown_minimal_is_needs_work_and_has_checklists():
    plan = plan_deployment(FIXTURES / "unknown_minimal")

    assert plan["readiness_summary"]["status"] in {"needs_work", "blocked"}
    assert any(item["status"] == "missing" for item in plan["env_checklist"])
    assert any(item["item"] == "Dockerfile present" and item["status"] == "missing" for item in plan["docker_checklist"])
    assert any(item["item"] == "GitHub Actions" and item["status"] == "missing" for item in plan["ci_checklist"])


def test_platform_recommendations_can_filter_platform():
    plan = plan_deployment(FIXTURES / "fastapi_react", DeploymentPlanOptions(platform="railway"))

    assert [rec["platform"] for rec in plan["platform_recommendations"]] == ["railway"]
    rec = plan["platform_recommendations"][0]
    assert rec["fit"] in {"high", "medium", "low"}
    assert rec["requirements"]
    assert "intentionally omitted" in rec["cost_risk_notes"]


def test_analyzer_json_input_is_supported(tmp_path):
    report = analyze_repo(FIXTURES / "pipeline_only")
    report_path = tmp_path / "analysis.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")

    plan = plan_deployment(report_path, DeploymentPlanOptions(from_report=True))

    assert plan["target_repo"]["source"] == "analyzer_report"
    assert plan["target_repo"]["name"] == "pipeline_only"
    assert "detected_stack" in plan
    assert plan["readiness_checks"]


def test_markdown_and_json_report_shape():
    plan = plan_deployment(FIXTURES / "fastapi_react", DeploymentPlanOptions(include_tests=True))

    md = render_deployment_plan(plan, "md")
    for section in ["# AgentForge Deployment Readiness Plan", "## Detected Stack", "## Readiness Checks", "## Platform Recommendations", "## Environment Checklist", "## Docker Checklist", "## CI Checklist", "## Phased Deployment Plan"]:
        assert section in md
    assert "No deployment was performed" in md

    payload = json.loads(render_deployment_plan(plan, "json"))
    expected = {"target_repo", "detected_stack", "readiness_summary", "readiness_checks", "platform_recommendations", "env_checklist", "docker_checklist", "ci_checklist", "database_notes", "healthcheck_notes", "cost_risk_notes", "phased_plan", "manual_commands", "not_executed_warning"}
    assert expected <= set(payload)


def test_docs_bundle_generation_writes_output_only(tmp_path, capsys):
    repo = _copy(FIXTURES / "fastapi_react", tmp_path / "repo")
    before = _files(repo)
    out = tmp_path / "deploy-docs"

    code = cmd_plan_deployment(
        Namespace(
            target=str(repo),
            from_report=False,
            format="md",
            json=False,
            output=str(out),
            platform="auto",
            include_cost_notes=True,
            docs_bundle=True,
            max_files=1000,
            include_tests=True,
        )
    )

    assert code == 0
    assert "Wrote deployment docs bundle" in capsys.readouterr().out
    for name in ["README.md", "deployment-plan.md", "env-checklist.md", "docker-readiness.md", "ci-readiness.md", "platform-recommendations.md", "risk-notes.md"]:
        assert (out / name).exists()
    assert _files(repo) == before


def test_cli_output_file_and_missing_path(tmp_path, capsys):
    output = tmp_path / "deploy-plan.json"
    code = cmd_plan_deployment(
        Namespace(
            target=str(FIXTURES / "fastapi_react"),
            from_report=False,
            format="text",
            json=True,
            output=str(output),
            platform="auto",
            include_cost_notes=False,
            docs_bundle=False,
            max_files=1000,
            include_tests=False,
        )
    )
    assert code == 0
    assert "Wrote deployment plan" in capsys.readouterr().out
    assert json.loads(output.read_text(encoding="utf-8"))["not_executed_warning"].startswith("No deployment")

    missing = cmd_plan_deployment(
        Namespace(
            target=str(FIXTURES / "missing"),
            from_report=False,
            format="text",
            json=False,
            output=None,
            platform="auto",
            include_cost_notes=False,
            docs_bundle=False,
            max_files=1000,
            include_tests=False,
        )
    )
    assert missing == 1
    assert "repository path not found" in capsys.readouterr().err


def test_generated_app_path_detection():
    repo = Path(__file__).parent.parent.parent / "examples" / "hybrid-scoring-demo"
    plan = plan_deployment(repo, DeploymentPlanOptions(max_files=1500, include_tests=False))

    assert plan["detected_stack"]["backend"]["framework"] == "fastapi"
    assert plan["detected_stack"]["frontend"]["framework"] in {"vite/react", "react", "vite"}
    assert any("SQLite" in note or "sqlite" in note for note in plan["database_notes"])
