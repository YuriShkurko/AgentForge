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
