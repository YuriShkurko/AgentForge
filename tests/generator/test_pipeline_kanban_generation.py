"""End-to-end checks for the pipeline_kanban board_by_relation primitive.

Generates a full app from the canonical "manage job applications" prompt and
verifies the generated React surface carries the new board_by_relation render
path with the guards demanded by the slice brief: empty lane source, empty
lane, non-array row state, and missing relation field all degrade gracefully
instead of crashing.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "generator"))

from agentforge.generator import generate
from agentforge.pack import DomainPack
from agentforge.planner.assistant import BuilderAssistant


def _generate_pipeline_app(tmp_path: Path) -> tuple[dict, str]:
    result = BuilderAssistant().start("I want to manage job applications")
    assert result["status"] == "proposed", result
    pack = DomainPack.model_validate(result["proposal"]["blueprint"])
    out = tmp_path / "pipeline-app"
    generate(pack, out)
    app_tsx = (out / "frontend/src/App.tsx").read_text(encoding="utf-8")
    app_model = json.loads((out / "app-model.json").read_text(encoding="utf-8"))
    return app_model, app_tsx


def test_generated_pipeline_app_model_carries_board_by_relation_layout(tmp_path):
    app_model, _ = _generate_pipeline_app(tmp_path)
    ui = app_model["ui"]
    assert ui["composition"] == "board_workspace"
    assert ui["focus"]["primary_entity"] == "card"
    assert ui["focus"]["group_by"] == "stage"
    card_entity_ui = ui.get("entities", {}).get("card") or {}
    assert card_entity_ui.get("display", {}).get("layout") == "board_by_relation"


def test_generated_pipeline_react_contains_board_by_relation_render_path(tmp_path):
    _, app_tsx = _generate_pipeline_app(tmp_path)
    # The new layout branch and its guards must be present.
    assert "board_by_relation" in app_tsx
    assert "No stages yet" in app_tsx or "to see lanes" in app_tsx
    # asRows guards must still wrap row reads inside the new branch.
    assert "asRows(rowsByEntity[targetEntity.name])" in app_tsx


def test_generated_pipeline_react_keeps_existing_board_by_status_branch(tmp_path):
    # Regression: adding board_by_relation must not delete the status-board path
    # that approval_review_queue / client_session_manager / scripted prompts use.
    _, app_tsx = _generate_pipeline_app(tmp_path)
    assert "board_by_status" in app_tsx
    assert "data-ui-layout=\"board_by_status\"" in app_tsx


def test_generated_pipeline_react_guards_against_missing_lane_entity(tmp_path):
    _, app_tsx = _generate_pipeline_app(tmp_path)
    # If the relation field or its target entity is missing we render an
    # EmptyState instead of crashing on undefined.targetEntity.
    assert "Cannot render board:" in app_tsx


def test_generated_pipeline_react_guards_against_empty_lane(tmp_path):
    _, app_tsx = _generate_pipeline_app(tmp_path)
    # Each lane falls back to emptyForLane(entity) when no primary rows match
    # the lane id; that helper already exists in the generated app.
    assert "emptyForLane(entity)" in app_tsx
