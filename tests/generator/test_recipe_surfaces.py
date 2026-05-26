"""Recipe-aware generated frontend surface checks."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "generator"))

from agentforge.blueprints import create_starter_blueprint
from agentforge.generator import generate
from agentforge.pack import DomainPack
from agentforge.planner.assistant import BuilderAssistant


def _generate_from_prompt(tmp_path: Path, prompt: str) -> tuple[dict, str]:
    result = BuilderAssistant().start(prompt)
    assert result["status"] == "proposed", result
    pack = DomainPack.model_validate(result["proposal"]["blueprint"])
    out = tmp_path / pack.name
    generate(pack, out)
    app_model = json.loads((out / "app-model.json").read_text(encoding="utf-8"))
    app_tsx = (out / "frontend/src/App.tsx").read_text(encoding="utf-8")
    return app_model, app_tsx


def test_pipeline_recipe_surface_emphasizes_board_workflow(tmp_path: Path) -> None:
    app_model, app_tsx = _generate_from_prompt(tmp_path, "I want to manage job applications")
    assert app_model["recipe"]["recipe_id"] == "pipeline_kanban"
    assert app_model["ui"]["composition"] == "board_workspace"
    assert "Move work through stages" in app_tsx
    assert "Track active cards across stages" in app_tsx
    assert "Pipeline stages" in app_tsx
    assert "data-ui-layout=\"board_by_relation\"" in app_tsx
    assert "asRows(rowsByEntity[targetEntity.name])" in app_tsx


def test_client_session_recipe_surface_has_sessions_clients_payments_copy(tmp_path: Path) -> None:
    app_model, app_tsx = _generate_from_prompt(
        tmp_path,
        "i am a tutor scheduling student sessions and logging payments",
    )
    assert app_model["recipe"]["recipe_id"] == "client_session_manager"
    assert [entity["name"] for entity in app_model["entities"]][:3] == ["client", "session", "payment"]
    assert "Run sessions, clients, and payments" in app_tsx
    assert "Upcoming sessions" in app_tsx
    assert "Clients / students" in app_tsx
    assert "Payments logged" in app_tsx
    assert "start the session workflow" in app_tsx


def test_approval_review_recipe_surface_has_queue_decision_copy(tmp_path: Path) -> None:
    app_model, app_tsx = _generate_from_prompt(tmp_path, "I need to review vendor risk findings")
    assert app_model["recipe"]["recipe_id"] == "approval_review_queue"
    assert "Review the queue and record decisions" in app_tsx
    assert "Needs review" in app_tsx
    assert "Claim, approve, reject" in app_tsx
    assert "Decisions" in app_tsx
    assert "create a review item to start the queue" in app_tsx


def test_generic_dashboard_surface_stays_generic_and_safe(tmp_path: Path) -> None:
    blueprint = create_starter_blueprint("generic-surface", archetype="model_driven_app")
    pack = DomainPack.model_validate(blueprint)
    out = tmp_path / pack.name
    generate(pack, out)
    app_model = json.loads((out / "app-model.json").read_text(encoding="utf-8"))
    app_tsx = (out / "frontend/src/App.tsx").read_text(encoding="utf-8")
    assert app_model.get("recipe", {}).get("recipe_id") in {None, "", "generic_dashboard"}
    assert app_model["ui"]["composition"] == "standard"
    assert "const heroHeadline" in app_tsx
    assert "recipeHighlightCards" in app_tsx
    assert "Example item" not in app_tsx
