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


PIPELINE_PROMPT = (
    "I want to manage job applications through a hiring pipeline. Track companies, "
    "application cards, stages, owners, follow-ups, and notes so I can see what needs attention next."
)


def _generate_pipeline_app(tmp_path: Path) -> tuple[dict, str]:
    result = BuilderAssistant().start(PIPELINE_PROMPT)
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
    assert app_model["experience"]["experience_id"] == "pipeline_board"
    assert app_model["experience"]["primitive_id"] == "pipeline_board"
    assert ui["composition"] == "board_workspace"
    assert ui["focus"]["primary_entity"] == "card"
    assert ui["focus"]["group_by"] == "stage"
    card_entity_ui = ui.get("entities", {}).get("card") or {}
    assert card_entity_ui.get("display", {}).get("layout") == "board_by_relation"


def test_generated_pipeline_seed_data_distributes_cards_across_stages(tmp_path):
    app_model, _ = _generate_pipeline_app(tmp_path)
    seed = app_model["seedData"]
    assert len(seed["stage"]) == 3
    assert [row["name"] for row in seed["stage"]] == ["Applied", "Interview", "Offer"]
    assert [row["stage"] for row in seed["card"]] == [1, 2, 3, 1, 2, 3]
    assert [row["company"] for row in seed["card"]] == [1, 2, 3, 4, 5, 6]
    assert len(seed["company"]) >= 2
    assert len(seed["owner"]) >= 2
    assert [row["card"] for row in seed["follow_up"]] == [1, 2, 3]
    assert seed["card"][0]["title"] == "Frontend Engineer — Northstar Labs"
    assert seed["card"][0]["owner"] == 1
    assert seed["card"][0]["due_on"] == "2026-06-01"
    assert seed["card"][0]["notes"] == "Portfolio review due this week."
    serialized = json.dumps(seed)
    assert "Example Job Title" not in serialized
    assert "Example Company Name" not in serialized
    assert "Example Owner" not in serialized


def test_generated_pipeline_react_contains_board_by_relation_render_path(tmp_path):
    _, app_tsx = _generate_pipeline_app(tmp_path)
    # The new layout branch and its guards must be present.
    assert '"experience_id": "pipeline_board"' in app_tsx
    assert "const usePipelineBoard = (): boolean =>" in app_tsx
    assert "function PipelineBoardWorkspace" in app_tsx
    assert "data-ui-layout=\"pipeline-board-workspace\"" in app_tsx
    assert "Applications by stage" in app_tsx
    assert "Applied" in app_tsx
    assert "Interview" in app_tsx
    assert "Offer" in app_tsx
    assert "board_by_relation" in app_tsx
    assert "No stages yet" in app_tsx or "to see lanes" in app_tsx
    # asRows guards must still wrap row reads inside the new branch.
    assert "asRows(rowsByEntity[targetEntity.name])" in app_tsx


def test_generated_pipeline_board_is_before_generic_tables_and_create_form(tmp_path):
    _, app_tsx = _generate_pipeline_app(tmp_path)
    pipeline_idx = app_tsx.index("function PipelineBoardWorkspace")
    board_idx = app_tsx.index('data-ui-surface="pipeline-board"', pipeline_idx)
    support_idx = app_tsx.index('data-ui-surface="pipeline-supporting"', pipeline_idx)
    create_idx = app_tsx.index("pipeline-create", pipeline_idx)
    generic_table_idx = app_tsx.index("function RegisterTable")
    dashboard_call_idx = app_tsx.find("<Dashboard", pipeline_idx, support_idx)

    assert board_idx < support_idx < create_idx
    assert pipeline_idx < generic_table_idx
    assert dashboard_call_idx == -1
    assert "Tables and forms stay available" not in app_tsx
    assert "Companies, owners, and follow-ups stay connected to each application." in app_tsx


def test_generated_pipeline_lane_cards_include_counts_and_context(tmp_path):
    _, app_tsx = _generate_pipeline_app(tmp_path)
    assert "function PipelineRecordCard" in app_tsx
    assert "data-ui-surface=\"pipeline-card\"" in app_tsx
    assert "lane-heading" in app_tsx
    assert "matched.length" in app_tsx
    assert "matched.length === 1 ? entity.labelSingular.toLowerCase() : entity.labelPlural.toLowerCase()" in app_tsx
    assert "Follow-up:" in app_tsx
    assert "Portfolio review due this week." in app_tsx
    assert "Frontend Engineer \\u2014 Northstar Labs" in app_tsx
    assert "Northstar Labs" in app_tsx
    assert "Owner" in app_tsx or "owner" in app_tsx
    assert "Company" in app_tsx or "company" in app_tsx


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
