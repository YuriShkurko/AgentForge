"""Tests for starter App Blueprint generation and builder YAML output."""
import json
import subprocess
import sys
from argparse import Namespace
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "generator"))

from agentforge.blueprints import create_starter_blueprint, sanitize_pack_name, write_starter_blueprint
from agentforge.cli import cmd_init_blueprint, cmd_plan
from agentforge.modules import select_modules
from agentforge.pack import DomainPack, load_pack

ROOT = Path(__file__).parent.parent.parent

def test_sanitize_pack_name_for_builder_and_cli():
    assert sanitize_pack_name("  My New App!! ") == "my-new-app"
    assert sanitize_pack_name("") == "new-app"


def test_starter_blueprint_loads_and_plans_without_gaps():
    data = create_starter_blueprint(
        "Starter App",
        display_name="Starter App",
        optional_modules=["notification_action", "triage_ui", "agent_runtime", "workspace"],
    )
    pack = DomainPack.model_validate(data)
    selection = select_modules(pack)

    assert pack.name == "starter-app"
    assert pack.agent_runtime is not None
    assert pack.agent_runtime.provider_mode == "scripted"
    assert pack.workspace is not None
    assert pack.workspace.enabled is True
    assert selection.gaps == []


def test_write_starter_blueprint_refuses_overwrite(tmp_path):
    path = tmp_path / "domain-pack.yaml"
    data = create_starter_blueprint("Starter App")

    write_starter_blueprint(path, data)
    try:
        write_starter_blueprint(path, data)
    except FileExistsError as exc:
        assert "refusing to overwrite" in str(exc)
    else:
        raise AssertionError("expected FileExistsError")


def test_init_blueprint_cli_writes_loadable_file_and_plan_passes(tmp_path, capsys):
    output = tmp_path / "pack" / "domain-pack.yaml"
    code = cmd_init_blueprint(
        Namespace(
            name="CLI Starter",
            output=str(output),
            force=False,
            display_name="CLI Starter",
            description="Created from test.",
            target_user="developer",
            archetype="ingestion_scoring_pipeline",
            optional_module=["notification_action", "triage_ui", "agent_runtime", "workspace"],
            no_workspace=False,
            no_fixture_provider=False,
        )
    )
    assert code == 0
    assert "Created App Blueprint" in capsys.readouterr().out

    pack = load_pack(output)
    assert pack.name == "cli-starter"

    plan_code = cmd_plan(Namespace(pack=str(output), json=True))
    assert plan_code == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["gaps"] == []
    assert "workspace" in plan["active_modules"]


def test_builder_generation_preview_and_analyzer_report_helpers():
    report = {
        "repo": {"name": "demo"},
        "detected_stack": {"backend": ["fastapi: app/main.py"], "frontend": ["react: package.json"]},
        "archetype_candidates": [{"archetype": "hybrid_agent_pipeline", "confidence": "high"}],
        "module_compatibility": [
            {"module": "agent_runtime", "status": "partial"},
            {"module": "pipeline", "status": "compatible"},
        ],
        "migration_plan": [{"phase": "Phase 1", "title": "Draft and review App Blueprint"}],
        "blueprint_seed": "# DRAFT ONLY\nname: demo",
    }
    script = f"""
      import {{ getGenerationPreview, parseAnalyzerReport, parseExtensionPlan, analyzerCommandExamples, extensionCommandExamples }} from './builder/blueprint-builder.mjs';
      const preview = getGenerationPreview({{
        name: 'UX App',
        archetype: 'hybrid_agent_pipeline',
        selectedModules: ['agent_runtime', 'workspace'],
      }});
      const parsed = parseAnalyzerReport({json.dumps(json.dumps(report))});
      const extension = parseExtensionPlan(JSON.stringify({{
        target_repo: {{ name: 'demo' }},
        selected_modules: ['agent_runtime'],
        module_plans: [{{ module: 'agent_runtime', status: 'partial' }}],
        migration_phases: [{{ phase: 'Phase 1', title: 'Baseline safety' }}],
        file_impact: {{ likely_files_to_add: ['backend/app/agent/'] }},
        risks: [],
        no_files_modified_statement: 'No files were modified.'
      }}));
      const invalid = parseAnalyzerReport('not json');
      process.stdout.write(JSON.stringify({{ preview, parsed, extension, invalid, analyzerCommandExamples, extensionCommandExamples }}));
    """
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    payload = json.loads(result.stdout)

    assert "FastAPI backend" in payload["preview"]["outputs"]
    assert "agentforge plan domain-packs/ux-app/domain-pack.yaml" in payload["preview"]["commands"]
    assert payload["parsed"]["ok"] is True
    assert payload["parsed"]["archetype"] == "hybrid_agent_pipeline"
    assert payload["parsed"]["blueprintSeed"].startswith("# DRAFT ONLY")
    assert payload["extension"]["ok"] is True
    assert payload["extension"]["modulePlans"][0]["module"] == "agent_runtime"
    assert payload["invalid"]["ok"] is False
    assert "--json --output report.json" in payload["analyzerCommandExamples"][-1]
    assert "plan-extension" in payload["extensionCommandExamples"][0]


def test_builder_html_front_door_copy_present():
    html = (ROOT / "builder" / "index.html").read_text(encoding="utf-8")

    assert "Start from an app idea" in html
    assert "Understand an existing repo" in html
    assert "Blueprint Source" in html
    assert "Live app plan" in html
    assert "./assets/agentforge-mark.png" in html
    assert "./assets/favicon.png" in html
    assert "agentforge-wordmark.png" not in html
    assert "No repo mutation by default" in html
    assert "data-step-target=\"start\"" in html
    assert "data-step=\"start\"" in html
    assert "build-summary" in html
    assert "agentforge analyze-repo ../my-project" in html or "analyzer-commands" in html
    assert "plan-extension" in html


def test_builder_example_ideas_are_plain_language():
    script = """
      import { exampleIdeas } from './builder/blueprint-builder.mjs';
      process.stdout.write(JSON.stringify(exampleIdeas));
    """
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    ideas = json.loads(result.stdout)

    assert len(ideas) >= 5
    assert any("Job triage" in idea for idea in ideas)
    assert any("Customer feedback" in idea for idea in ideas)


def test_browser_builder_project_workspace_yaml_loads_without_scoring(tmp_path):
    script = """
      import { createBlueprintYaml } from "./builder/blueprint-builder.mjs";
      const yaml = createBlueprintYaml({
        name: "Project Workspace App",
        displayName: "Project Workspace App",
        description: "Track projects, tasks, owners, due dates, notes, and activity.",
        targetUser: "project operator",
        archetype: "project_workspace_app",
        selectedModules: ["agent_runtime", "workspace"],
        llmMode: "scripted",
        workspaceEnabled: true,
        fixtureEnabled: true,
      });
      process.stdout.write(yaml);
    """
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    output = tmp_path / "domain-pack.yaml"
    output.write_text(result.stdout, encoding="utf-8")

    raw = yaml.safe_load(result.stdout)
    assert raw["app_archetype"] == "project_workspace_app"
    assert all(item["name"] != "score_records" for item in raw["capabilities"])

    pack = load_pack(output)
    selection = select_modules(pack)
    assert selection.template == "project-workspace-react"
    assert selection.gaps == []


def test_browser_builder_yaml_loads_with_generator_schema(tmp_path):
    script = """
      import { createBlueprintYaml } from "./builder/blueprint-builder.mjs";
      const yaml = createBlueprintYaml({
        name: "Browser Builder App",
        displayName: "Browser Builder App",
        description: "Created in the static builder.",
        targetUser: "developer",
        archetype: "ingestion_scoring_pipeline",
        selectedModules: ["notification_action", "triage_ui", "agent_runtime", "workspace"],
        actionAccept: "accept",
        actionSkip: "skip",
        actionMaybe: "maybe",
        notificationMode: "preview_only",
        llmMode: "scripted",
        workspaceEnabled: true,
        fixtureEnabled: true,
      });
      process.stdout.write(yaml);
    """
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    output = tmp_path / "domain-pack.yaml"
    output.write_text(result.stdout, encoding="utf-8")

    raw = yaml.safe_load(result.stdout)
    assert raw["name"] == "browser-builder-app"
    assert raw["notification_actions"][0]["decision_states"] == ["pending", "accept", "skip", "maybe"]

    pack = load_pack(output)
    selection = select_modules(pack)
    assert pack.agent_runtime is not None
    assert pack.workspace is not None
    assert selection.gaps == []
