"""Tests for v0.8.1/v0.8.2 safe patch bundles and approved apply."""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "generator"))

from agentforge.analyzer import analyze_repo
from agentforge.patch_bundle import PrepareExtensionOptions, prepare_extension, render_prepare_result

FIXTURES = Path(__file__).parent / "fixtures" / "repo_analyzer"


def _copy_repo(src: Path, dst: Path) -> Path:
    import shutil

    shutil.copytree(src, dst)
    return dst


def _files(repo: Path) -> list[str]:
    return sorted(p.relative_to(repo).as_posix() for p in repo.rglob("*") if p.is_file() and ".git" not in p.parts)


def test_default_bundle_mode_does_not_modify_target_and_creates_expected_files(tmp_path):
    repo = _copy_repo(FIXTURES / "fastapi_react", tmp_path / "repo")
    before = _files(repo)
    out = tmp_path / "bundle"

    result = prepare_extension(repo, PrepareExtensionOptions(output=out, modules=("agent_runtime",)))

    assert _files(repo) == before
    assert result["mode"] == "bundle"
    assert result["no_target_repo_modification"] is True
    for name in ["README.md", "manifest.json", "extension-plan.md", "file-impact.md", "migration-phases.md", "validation-checklist.md", "patch-preview.md"]:
        assert (out / name).exists()
    assert (out / "proposed-files" / "AGENTFORGE_MIGRATION.md").exists()
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["target_repo"]["name"] == "repo"
    assert manifest["selected_modules"] == ["agent_runtime"]
    assert manifest["planned_operations"]
    assert manifest["safety_notes"]


def test_dry_run_reports_planned_writes_without_writing(tmp_path):
    repo = _copy_repo(FIXTURES / "pipeline_only", tmp_path / "repo")
    out = tmp_path / "bundle"

    result = prepare_extension(repo, PrepareExtensionOptions(output=out, dry_run=True, modules=("provider_adapter",)))

    assert result["mode"] == "dry-run"
    assert result["planned_operations"]
    assert not out.exists()
    assert not (repo / "AGENTFORGE_MIGRATION.md").exists()
    assert "dry_run" in render_prepare_result(result, "text")


def test_apply_requires_yes_and_refuses_dirty_git_repo_by_default(tmp_path):
    repo = _copy_repo(FIXTURES / "unknown_minimal", tmp_path / "repo")
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "a@example.test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "A"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)
    (repo / "README.md").write_text("dirty\n", encoding="utf-8")

    missing_yes = prepare_extension(repo, PrepareExtensionOptions(apply=True, modules=("deterministic_test_harness",)))
    assert missing_yes["refused_operations"]
    assert not (repo / "AGENTFORGE_MIGRATION.md").exists()

    dirty = prepare_extension(repo, PrepareExtensionOptions(apply=True, yes=True, modules=("deterministic_test_harness",)))
    assert any(check["check"] == "dirty_git" and check["status"] == "failed" for check in dirty["safety_checks"])
    assert any("README.md" in op["path"] for op in dirty["refused_operations"])
    assert not (repo / "AGENTFORGE_MIGRATION.md").exists()


def test_apply_refuses_overwrites_by_default_and_writes_low_risk_files(tmp_path):
    repo = _copy_repo(FIXTURES / "fastapi_react", tmp_path / "repo")
    (repo / "AGENTFORGE_MIGRATION.md").write_text("existing\n", encoding="utf-8")

    refused = prepare_extension(repo, PrepareExtensionOptions(apply=True, yes=True, allow_dirty=True, modules=("agent_runtime",)))
    assert any(op["path"] == "AGENTFORGE_MIGRATION.md" for op in refused["refused_operations"])
    assert (repo / "AGENTFORGE_MIGRATION.md").read_text(encoding="utf-8") == "existing\n"

    applied = prepare_extension(repo, PrepareExtensionOptions(apply=True, yes=True, allow_dirty=True, overwrite=True, modules=("agent_runtime",)))
    written = {op["path"] for op in applied["applied_operations"]}
    assert "AGENTFORGE_MIGRATION.md" in written
    assert "AGENTFORGE_EXTENSION_PLAN.md" in written
    assert "AGENTFORGE_APPLICATION_MANIFEST.json" in written
    assert not (repo / "backend" / "app" / "api" / "agent.py").exists()
    assert applied["skipped_operations"]


def test_apply_does_not_stage_or_commit(tmp_path):
    repo = _copy_repo(FIXTURES / "unknown_minimal", tmp_path / "repo")
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "a@example.test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "A"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)
    before_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()

    result = prepare_extension(repo, PrepareExtensionOptions(apply=True, yes=True, modules=("deterministic_test_harness",)))

    after_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    status = subprocess.check_output(["git", "status", "--short"], cwd=repo, text=True)
    assert result["applied_operations"]
    assert before_head == after_head
    assert "?? AGENTFORGE_MIGRATION.md" in status


def test_analyzer_json_input_and_selected_unsupported_modules(tmp_path):
    report = analyze_repo(FIXTURES / "pipeline_only")
    report_path = tmp_path / "analysis.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")

    result = prepare_extension(report_path, PrepareExtensionOptions(from_report=True, dry_run=True, modules=("provider_adapter,live_llm_provider",)))

    assert result["selected_modules"] == ["provider_adapter"]
    assert result["plan"]["unsupported_items"][0]["module"] == "live_llm_provider"
    assert result["planned_operations"]
