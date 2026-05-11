"""Tests for v0.6 planner CLI and local builder server."""
import json
import sys
import threading
import urllib.request
from argparse import Namespace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "generator"))

from agentforge.cli import cmd_draft_blueprint
from agentforge.pack import load_pack
from agentforge.planner.server import PlannerServer

ROOT = Path(__file__).parent.parent.parent


def test_draft_blueprint_cli_writes_valid_yaml(tmp_path, capsys):
    output = tmp_path / "domain-pack.yaml"
    code = cmd_draft_blueprint(
        Namespace(
            idea="triage support tickets and create preview notifications",
            answers=None,
            out=str(output),
            force=False,
            planner="scripted",
            json=False,
        )
    )

    assert code == 0
    assert "Drafted App Blueprint" in capsys.readouterr().out
    pack = load_pack(output)
    assert pack.app_archetype == "notification_triage_app"


def test_draft_blueprint_cli_live_planner_fails_fast(capsys):
    code = cmd_draft_blueprint(
        Namespace(
            idea="score records",
            answers=None,
            out=None,
            force=False,
            planner="live",
            json=False,
        )
    )

    assert code == 1
    assert "only the scripted planner" in capsys.readouterr().err


def test_builder_server_draft_and_validate_endpoints(tmp_path):
    server = PlannerServer(("127.0.0.1", 0), ROOT / "builder")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}/api/planner"
    try:
        draft = post_json(base + "/draft", {"idea": "score incoming records for a support operator"})
        assert draft["status"] == "draft"
        assert draft["blueprint"]["app_archetype"] == "ingestion_scoring_pipeline"

        validation = post_json(base + "/validate", {"blueprint": draft["blueprint"]})
        assert validation["status"] == "draft"
        assert "agentforge plan" in validation["commands"][0]
    finally:
        server.shutdown()
        server.server_close()


def post_json(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))
