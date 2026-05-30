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


def _blueprint_from_prompt(prompt: str) -> dict:
    result = BuilderAssistant().start(prompt)
    assert result["status"] == "proposed", result
    return result["proposal"]["blueprint"]


def _generate_blueprint(tmp_path: Path, blueprint: dict) -> tuple[dict, str]:
    pack = DomainPack.model_validate(blueprint)
    out = tmp_path / pack.name
    generate(pack, out)
    app_model = json.loads((out / "app-model.json").read_text(encoding="utf-8"))
    app_tsx = (out / "frontend/src/App.tsx").read_text(encoding="utf-8")
    return app_model, app_tsx


def _generate_from_prompt(tmp_path: Path, prompt: str) -> tuple[dict, str]:
    return _generate_blueprint(tmp_path, _blueprint_from_prompt(prompt))


PIPELINE_PROMPT = (
    "I want to manage job applications through a hiring pipeline. Track companies, "
    "application cards, stages, owners, follow-ups, and notes so I can see what needs attention next."
)


def test_pipeline_recipe_surface_emphasizes_board_workflow(tmp_path: Path) -> None:
    app_model, app_tsx = _generate_from_prompt(tmp_path, PIPELINE_PROMPT)
    assert app_model["recipe"]["recipe_id"] == "pipeline_kanban"
    assert app_model["experience"]["experience_id"] == "pipeline_board"
    assert app_model["experience"]["primitive_id"] == "pipeline_board"
    assert app_model["ui"]["composition"] == "board_workspace"
    assert "Hiring Pipeline" in app_tsx
    assert "Move candidates through stages" in app_tsx
    assert "See what needs attention next" not in app_tsx
    assert "see what needs attention next" in app_tsx
    assert "Applications by stage" in app_tsx
    assert "Review active applications by stage" in app_tsx
    assert "Companies, owners, and follow-ups stay connected to each application." in app_tsx
    assert "Tables and forms stay available" not in app_tsx
    assert "Applications" in app_tsx
    assert "Companies / owners" in app_tsx
    assert "function PipelineBoardWorkspace" in app_tsx
    assert "function PipelineRecordCard" in app_tsx
    assert "data-ui-layout=\"board_by_relation\"" in app_tsx
    assert "data-ui-layout=\"pipeline-board-workspace\"" in app_tsx
    assert "data-ui-surface=\"pipeline-board\"" in app_tsx
    assert "data-ui-surface=\"pipeline-supporting\"" in app_tsx
    assert "asRows(rowsByEntity[targetEntity.name])" in app_tsx
    pipeline_idx = app_tsx.index("function PipelineBoardWorkspace")
    board_idx = app_tsx.index('data-ui-surface="pipeline-board"', pipeline_idx)
    support_idx = app_tsx.index('data-ui-surface="pipeline-supporting"', pipeline_idx)
    assert app_tsx.find("<Dashboard", pipeline_idx, support_idx) == -1
    assert board_idx < support_idx
    assert '"experience_id": "pipeline_board"' in app_tsx
    assert '"primitive_id": "pipeline_board"' in app_tsx
    assert "isPipelineBoardExperience()" in app_tsx
    assert "usePipelineBoard()" in app_tsx


def test_pipeline_surface_uses_experience_metadata_without_recipe_id(tmp_path: Path) -> None:
    blueprint = _blueprint_from_prompt(PIPELINE_PROMPT)
    experience = blueprint["future_extensions"]["experience"]
    blueprint["future_extensions"] = {
        "features": ["assistant_refinement", "provider_imports"],
        "experience": experience,
    }
    app_model, app_tsx = _generate_blueprint(tmp_path, blueprint)

    assert app_model["recipe"] == {}
    assert app_model["experience"]["experience_id"] == "pipeline_board"
    assert app_model["experience"]["primitive_id"] == "pipeline_board"
    assert '"experience_id": "pipeline_board"' in app_tsx
    assert "if (usePipelineBoard()) return pipelineVocabulary().title" in app_tsx
    assert "if (usePipelineBoard()) return pipelineVocabulary().summary" in app_tsx
    assert "isPrimaryActive && usePipelineBoard() ? <PipelineBoardWorkspace" in app_tsx
    assert "Applications by stage" in app_tsx
    assert "data-ui-layout=\"board_by_relation\"" in app_tsx


def test_pipeline_surface_keeps_no_experience_recipe_fallback(tmp_path: Path) -> None:
    blueprint = _blueprint_from_prompt(PIPELINE_PROMPT)
    blueprint["future_extensions"].pop("experience", None)
    app_model, app_tsx = _generate_blueprint(tmp_path, blueprint)

    assert app_model["recipe"]["recipe_id"] == "pipeline_kanban"
    assert app_model["experience"] == {}
    assert '"experience_id": "pipeline_board"' not in app_tsx
    assert "const usePipelineBoard = (): boolean => isPipelineBoardExperience() || (!hasExperienceMetadata() && (recipeId() === 'pipeline_kanban' || isRelationBoardLayout()))" in app_tsx
    assert "Hiring Pipeline" in app_tsx
    assert "Applications by stage" in app_tsx


def test_pipeline_surface_has_no_slop_copy_for_canonical_prompt(tmp_path: Path) -> None:
    app_model, app_tsx = _generate_from_prompt(tmp_path, PIPELINE_PROMPT)
    surfaces = [app_model["app"]["displayName"], app_model["app"]["description"], app_tsx, json.dumps(app_model["seedData"])]
    bad_fragments = [
        "Job Through Hiring Pipeline Track",
        "Application Cards Register",
        "Create Application Card",
        "Job Through Hiring",
        "Example Job Title",
        "Example Company Name",
        "Tables and forms stay available",
    ]
    for surface in surfaces:
        for fragment in bad_fragments:
            assert fragment not in surface


def test_pipeline_renderer_does_not_affect_non_pipeline_apps(tmp_path: Path) -> None:
    app_model, app_tsx = _generate_from_prompt(tmp_path, "I need to track equipment, vendors, and maintenance")
    assert app_model["experience"]["primitive_id"] == "inventory_ops"
    assert app_model["ui"]["focus"]["primary_entity"] == "asset"
    assert app_model["recipe"]["recipe_id"] == "inventory_asset_tracker"
    assert "Track assets, stock, and upkeep" in app_tsx


def test_client_session_recipe_surface_has_sessions_clients_payments_copy(tmp_path: Path) -> None:
    app_model, app_tsx = _generate_from_prompt(
        tmp_path,
        "i am a tutor scheduling student sessions and logging payments",
    )
    assert app_model["recipe"]["recipe_id"] == "client_session_manager"
    assert app_model["experience"]["experience_id"] == "client_workspace"
    assert app_model["experience"]["primitive_id"] == "client_workspace"
    assert '"experience_id": "client_workspace"' in app_tsx
    assert '"primitive_id": "client_workspace"' in app_tsx
    assert "isClientWorkspaceExperience()" in app_tsx
    assert "recipeId() === 'client_session_manager'" in app_tsx
    assert [entity["name"] for entity in app_model["entities"]][:3] == ["client", "session", "payment"]
    assert "Manage students, sessions, and payments" in app_tsx
    assert "client-workspace" in app_tsx
    assert "Session and payment timeline" in app_tsx
    assert "Upcoming / recent sessions" in app_tsx
    assert "Unpaid / pending payments" in app_tsx
    assert "start the session workflow" in app_tsx


def test_client_session_recipe_surface_has_freelance_work_payment_workspace(tmp_path: Path) -> None:
    app_model, app_tsx = _generate_from_prompt(
        tmp_path,
        "I am a freelance web designer and I want help managing clients, work history, payments and more",
    )
    assert app_model["recipe"]["recipe_id"] == "client_session_manager"
    assert app_model["experience"]["experience_id"] == "client_workspace"
    assert [entity["name"] for entity in app_model["entities"]][:3] == ["client", "project", "invoice"]
    assert "Manage clients, work, and payments" in app_tsx
    assert "client-workspace" in app_tsx
    assert "Work and payment timeline" in app_tsx
    assert "Recent work" in app_tsx
    assert "Unpaid / pending payments" in app_tsx
    assert "Inspect the client, completed work, open projects, and invoice/payment status" in app_tsx


def test_client_session_recipe_surface_keeps_non_array_guards(tmp_path: Path) -> None:
    _app_model, app_tsx = _generate_from_prompt(
        tmp_path,
        "I am a freelance web designer and I want help managing clients, work history, payments and more",
    )
    assert "const asRows = (value: unknown): Row[] =>" in app_tsx
    assert "Array.isArray(value)" in app_tsx
    assert "asRows(rowsByEntity[field.targetEntity])" in app_tsx
    assert "asRows(ctx.rowsByEntity[clientEntity.name])" in app_tsx


def test_client_workspace_surface_uses_experience_metadata_without_recipe_id(tmp_path: Path) -> None:
    blueprint = _blueprint_from_prompt(
        "i am a tutor scheduling student sessions and logging payments",
    )
    experience = blueprint["future_extensions"]["experience"]
    blueprint["future_extensions"] = {
        "features": ["assistant_refinement", "provider_imports"],
        "experience": experience,
    }
    app_model, app_tsx = _generate_blueprint(tmp_path, blueprint)

    assert app_model["recipe"] == {}
    assert app_model["experience"]["experience_id"] == "client_workspace"
    assert app_model["experience"]["primitive_id"] == "client_workspace"
    assert '"experience_id": "client_workspace"' in app_tsx
    assert "const recipeId = (): string => String(model.recipe?.recipe_id || '')" in app_tsx
    assert "isPrimaryActive && useClientWorkspace() ? <ClientWorkWorkspace" in app_tsx
    assert "if (useClientWorkspace()) return clientWorkHeroHeadline()" in app_tsx


def test_client_workspace_surface_keeps_no_experience_recipe_fallback(tmp_path: Path) -> None:
    blueprint = _blueprint_from_prompt(
        "i am a tutor scheduling student sessions and logging payments",
    )
    blueprint["future_extensions"].pop("experience", None)
    app_model, app_tsx = _generate_blueprint(tmp_path, blueprint)

    assert app_model["recipe"]["recipe_id"] == "client_session_manager"
    assert app_model["experience"] == {}
    assert '"experience": {' in app_tsx
    assert '"experience_id": "client_workspace"' not in app_tsx
    assert "const useClientWorkspace = (): boolean => isClientWorkspaceExperience() || (!hasExperienceMetadata() && recipeId() === 'client_session_manager')" in app_tsx
    assert "Manage students, sessions, and payments" in app_tsx


def test_approval_review_recipe_surface_has_queue_decision_copy(tmp_path: Path) -> None:
    app_model, app_tsx = _generate_from_prompt(tmp_path, "I need to review vendor risk findings")
    assert app_model["recipe"]["recipe_id"] == "approval_review_queue"
    assert "Review the queue and record decisions" in app_tsx
    assert "Needs review" in app_tsx
    assert "Claim, approve, reject" in app_tsx
    assert "Decisions" in app_tsx
    assert "create a review item to start the queue" in app_tsx


def test_inventory_asset_recipe_surface_has_asset_stock_maintenance_copy(tmp_path: Path) -> None:
    app_model, app_tsx = _generate_from_prompt(tmp_path, "I need to track equipment, vendors, and maintenance")
    assert app_model["recipe"]["recipe_id"] == "inventory_asset_tracker"
    assert app_model["experience"]["experience_id"] == "inventory_ops"
    assert app_model["experience"]["primitive_id"] == "inventory_ops"
    assert app_model["ui"]["composition"] == "board_workspace"
    assert [entity["name"] for entity in app_model["entities"]][:5] == ["asset", "category", "location", "vendor", "maintenance_task"]
    assert '"experience_id": "inventory_ops"' in app_tsx
    assert '"primitive_id": "inventory_ops"' in app_tsx
    assert '"expected_roles"' not in app_tsx
    assert '"primary_actions"' not in app_tsx
    assert "isInventoryOpsExperience()" in app_tsx
    assert "useInventoryOps()" in app_tsx
    assert "Track assets, stock, and upkeep" in app_tsx
    assert "Tracked assets / stock" in app_tsx
    assert "Maintenance or reorder" in app_tsx
    assert "Locations / vendors" in app_tsx
    assert "start tracking assets, stock, and maintenance" in app_tsx
    assert "Example item" not in app_tsx


def test_inventory_surface_uses_experience_metadata_without_recipe_id(tmp_path: Path) -> None:
    blueprint = _blueprint_from_prompt("I need to track equipment, vendors, and maintenance")
    experience = blueprint["future_extensions"]["experience"]
    blueprint["future_extensions"] = {
        "features": ["assistant_refinement", "provider_imports"],
        "experience": experience,
    }
    app_model, app_tsx = _generate_blueprint(tmp_path, blueprint)

    assert app_model["recipe"] == {}
    assert app_model["experience"]["experience_id"] == "inventory_ops"
    assert app_model["experience"]["primitive_id"] == "inventory_ops"
    assert '"experience_id": "inventory_ops"' in app_tsx
    assert "if (useInventoryOps()) return 'Track assets, stock, and upkeep'" in app_tsx
    assert "if (useInventoryOps()) return 'Monitor assets or inventory by status" in app_tsx
    assert "Tracked assets / stock" in app_tsx
    assert "start tracking assets, stock, and maintenance" in app_tsx


def test_inventory_surface_uses_primitive_metadata_without_experience_id(tmp_path: Path) -> None:
    blueprint = _blueprint_from_prompt("I manage office inventory and reorder supplies")
    experience = dict(blueprint["future_extensions"]["experience"])
    experience["experience_id"] = ""
    blueprint["future_extensions"] = {
        "features": ["assistant_refinement", "provider_imports"],
        "experience": experience,
    }
    app_model, app_tsx = _generate_blueprint(tmp_path, blueprint)

    assert app_model["recipe"] == {}
    assert app_model["experience"]["experience_id"] == ""
    assert app_model["experience"]["primitive_id"] == "inventory_ops"
    assert '"primitive_id": "inventory_ops"' in app_tsx
    assert "const isInventoryOpsExperience = (): boolean => experienceId() === 'inventory_ops' || primitiveId() === 'inventory_ops'" in app_tsx
    assert "Tracked assets / stock" in app_tsx


def test_inventory_surface_keeps_no_experience_recipe_fallback(tmp_path: Path) -> None:
    blueprint = _blueprint_from_prompt("I need to track equipment, vendors, and maintenance")
    blueprint["future_extensions"].pop("experience", None)
    app_model, app_tsx = _generate_blueprint(tmp_path, blueprint)

    assert app_model["recipe"]["recipe_id"] == "inventory_asset_tracker"
    assert app_model["experience"] == {}
    assert '"experience_id": "inventory_ops"' not in app_tsx
    assert "const useInventoryOps = (): boolean => isInventoryOpsExperience() || (!hasExperienceMetadata() && (recipeId() === 'inventory_asset_tracker' || hasInventorySurfaceMetadata()))" in app_tsx
    assert "Track assets, stock, and upkeep" in app_tsx
    assert "Tracked assets / stock" in app_tsx


def test_generic_dashboard_surface_stays_generic_and_safe(tmp_path: Path) -> None:
    blueprint = create_starter_blueprint("generic-surface", archetype="model_driven_app")
    pack = DomainPack.model_validate(blueprint)
    out = tmp_path / pack.name
    generate(pack, out)
    app_model = json.loads((out / "app-model.json").read_text(encoding="utf-8"))
    app_tsx = (out / "frontend/src/App.tsx").read_text(encoding="utf-8")
    assert app_model.get("recipe", {}).get("recipe_id") in {None, "", "generic_dashboard"}
    assert app_model.get("experience") == {}
    assert app_model["ui"]["composition"] == "standard"
    assert "const heroHeadline" in app_tsx
    assert '"experience": {' in app_tsx
    assert '"experience_id": "client_workspace"' not in app_tsx
    assert "const useClientWorkspace = (): boolean => isClientWorkspaceExperience() || (!hasExperienceMetadata() && recipeId() === 'client_session_manager')" in app_tsx
    assert '"experience_id": "pipeline_board"' not in app_tsx
    assert "if (usePipelineBoard()) return pipelineVocabulary().title" in app_tsx
    assert '"experience_id": "inventory_ops"' not in app_tsx
    assert "const hasInventorySurfaceMetadata = (): boolean => Boolean(model.entities.find((entity) => ['asset','inventory_item'].includes(entity.name)) && model.entities.some((entity) => ['category','location','vendor','supplier','maintenance_task','warehouse'].includes(entity.name)))" in app_tsx
    assert [entity["name"] for entity in app_model["entities"]] == ["item"]
    assert "recipeHighlightCards" in app_tsx
    assert "Example item" not in app_tsx
