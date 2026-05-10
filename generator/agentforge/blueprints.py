"""Helpers for creating starter App Blueprints."""
from __future__ import annotations

import re
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from agentforge.modules import ARCHETYPE_REQUIRED_MODULES
from agentforge.pack import VALID_ARCHETYPES, VALID_MODULES, DomainPack


DEFAULT_ACTION_LABELS = ["accept", "skip", "maybe"]
DEFAULT_WIDGET_TYPES = [
    "summary_card",
    "ranking_list",
    "score_table",
    "run_history_list",
    "notification_preview_card",
    "action_history_list",
]


def sanitize_pack_name(value: str) -> str:
    """Return a filesystem-safe App Blueprint name."""
    normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    return normalized.strip("-") or "new-app"


def _display_name(name: str, display_name: str | None) -> str:
    if display_name:
        return display_name.strip()
    return sanitize_pack_name(name).replace("-", " ").title()


def create_starter_blueprint(
    name: str,
    *,
    display_name: str | None = None,
    description: str = "A local AgentForge app created with the Blueprint Builder.",
    target_user: str = "developer",
    archetype: str = "ingestion_scoring_pipeline",
    optional_modules: list[str] | None = None,
    action_labels: list[str] | None = None,
    workspace_enabled: bool = True,
    fixture_provider_enabled: bool = True,
) -> dict[str, Any]:
    """Create a minimal valid App Blueprint dictionary.

    The shape intentionally matches ``DomainPack`` and the current generator
    module selector so CLI planning remains the validation source of truth.
    """
    if archetype not in VALID_ARCHETYPES:
        raise ValueError(f"unknown app_archetype '{archetype}'")

    clean_name = sanitize_pack_name(name)
    required_modules = sorted(ARCHETYPE_REQUIRED_MODULES.get(archetype, set()))
    optional = sorted({m for m in (optional_modules or []) if m in VALID_MODULES})

    if workspace_enabled and "workspace" not in required_modules and "workspace" not in optional:
        optional.append("workspace")

    if "agent_runtime" in optional and "agent" not in required_modules and archetype == "agent_dashboard_app":
        required_modules.append("agent")

    actions = action_labels or DEFAULT_ACTION_LABELS
    pack: dict[str, Any] = {
        "name": clean_name,
        "display_name": _display_name(clean_name, display_name),
        "version": "0.1.0",
        "domain": {
            "domain_name": _display_name(clean_name, display_name),
            "app_type": archetype,
            "target_users": [target_user.strip() or "developer"],
            "product_purpose": description.strip() or "A local AgentForge app.",
            "main_user_goals": [
                "configure_app_blueprint",
                "run_agentforge_plan",
                "generate_with_cli",
            ],
        },
        "app_archetype": archetype,
        "required_shell_modules": required_modules,
        "optional_shell_modules": optional,
        "capabilities": [
            {
                "name": "ingest_records",
                "purpose": "Load deterministic fixture records through the provider interface.",
                "input_summary": "POST /ingest",
                "output_shape": {"fields": ["raw_records_inserted", "normalized_inserted", "run_id"]},
                "mutates_state": True,
                "data_mode": "fixture_provider" if fixture_provider_enabled else "configured_provider",
                "deterministic_test_safe": fixture_provider_enabled,
                "implementation_status": "planned",
            },
            {
                "name": "score_records",
                "purpose": "Score normalized records with deterministic heuristics.",
                "input_summary": "POST /score",
                "output_shape": {"fields": ["scores_written", "rescore"]},
                "mutates_state": True,
                "data_mode": "deterministic_heuristics",
                "deterministic_test_safe": True,
                "implementation_status": "planned",
            },
        ],
        "ui_surfaces": [
            {
                "surface_type": "operations_panel",
                "renderer": "OpsPanel",
                "data_source": "ingest_records, score_records",
                "section": "operations",
                "expected_data_shape": "Run controls, activity status, and recent results.",
                "empty_state": "Ready. No recent operations.",
            }
        ],
        "providers": {
            "record_sources": [
                {
                    "name": "fixture",
                    "class": "FixtureRecordProvider",
                    "interface": "RecordProvider",
                    "source": "deterministic in-code fixture list",
                    "current_status": "planned" if fixture_provider_enabled else "optional",
                }
            ]
        },
        "adapters": [
            {
                "name": "normalized_dto_from_raw",
                "purpose": "Convert raw provider records into a stable normalized DTO.",
                "normalized_shape": ["external_id", "source", "title", "category", "value", "ingested_at"],
            }
        ],
        "run_history": {
            "enabled": "pipeline" in required_modules or "pipeline" in optional,
            "table_name": "provider_runs",
            "tracked_fields": ["provider_name", "started_at", "finished_at", "status", "stats", "error"],
            "frontend_surface": "run_history_table",
        },
        "notification_actions": [
            {
                "name": "record_decision",
                "trigger": "user chooses an action in the triage UI",
                "delivery_channel": "preview",
                "delivery_mode": "preview_only",
                "decision_states": ["pending", *actions],
                "dedupe_key": "record_id + action_type",
                "persistence_table": "record_actions",
                "history_table": "record_action_events",
                "preview_table": "notification_previews",
            }
        ] if "notification_action" in required_modules or "notification_action" in optional else [],
        "seed_data": {
            "fixture_provider_records": "backend/app/providers/fixture/records.py",
        } if fixture_provider_enabled else {},
        "tests": {
            "expectations": {
                "no_live_provider_in_tests": True,
                "no_live_llm_in_tests": True,
                "deterministic_fixture_data": fixture_provider_enabled,
            },
            "commands": {
                "backend": "pytest",
                "frontend_build": "npm run build",
                "frontend_lint": "npm run lint",
            },
        },
        "future_extensions": {
            "features": [
                "repo_analyzer",
                "deploy_planner",
                "real_delivery_adapters",
                "live_llm_provider",
            ]
        },
        "compatibility_gaps": [],
    }

    if "agent_runtime" in required_modules or "agent_runtime" in optional or "agent" in required_modules:
        pack["agent_runtime"] = {
            "enabled": True,
            "provider_mode": "scripted",
            "scripted_fixture_path": "backend/app/agent/providers.py",
            "conversation_persistence": {"enabled": True, "tables": ["conversations", "conversation_messages"]},
            "streaming": {
                "enabled": True,
                "endpoint": "/agent/chat/stream",
                "events": ["message_start", "text_delta", "tool_call", "tool_result", "error", "done"],
            },
            "guardrails": {"reject_empty_message": True},
            "tools": [
                {
                    "name": "score_records",
                    "purpose": "Run deterministic scoring through the generated tool registry.",
                    "input_schema": {"rescore": {"type": "boolean", "required": False, "default": False}},
                    "output_schema": {"fields": ["scores_written", "rescore"]},
                }
            ],
            "scripted_turns": [
                {
                    "match": "score",
                    "tool_calls": [{"name": "score_records", "arguments": {"rescore": False}}],
                    "final_text": "I scored the fixture records with the deterministic adapter.",
                }
            ],
        }

    if workspace_enabled or "workspace" in required_modules or "workspace" in optional:
        pack["workspace"] = {
            "enabled": True,
            "persistence": {
                "table_name": "workspace_widgets",
                "fields": ["id", "widget_type", "title", "source_tool", "data", "position", "metadata"],
            },
            "default_layout": [],
            "remove_enabled": True,
            "reorder_enabled": True,
            "empty_state": "No widgets yet. Ask the agent to pin a result to the workspace.",
            "frontend_surface": "workspace_panel",
        }
        pack["tool_widget_compatibility"] = {
            "score_records": ["summary_card"],
            "get_scored_records": ["ranking_list", "score_table"],
        }
        pack["widgets"] = [
            {
                "widget_type": widget_type,
                "renderer": "".join(part.title() for part in widget_type.split("_")),
                "compatible_source_tools": ["score_records"] if widget_type == "summary_card" else ["get_scored_records"],
                "section": "workspace",
                "expected_data_shape": "Generic deterministic payload rendered by the workspace.",
                "empty_state": "No widget data.",
                "implementation_status": "planned",
            }
            for widget_type in DEFAULT_WIDGET_TYPES
        ]
        pack["ui_surfaces"].append({
            "surface_type": "workspace_panel",
            "renderer": "WorkspacePanel",
            "data_source": "workspace_widgets",
            "section": "dashboard_workspace",
            "expected_data_shape": "Persisted workspace widgets.",
            "empty_state": "No widgets yet.",
        })

    return pack


def blueprint_to_yaml(blueprint: dict[str, Any]) -> str:
    """Serialize a blueprint with deterministic field order."""
    return yaml.safe_dump(deepcopy(blueprint), sort_keys=False, allow_unicode=False)


def write_starter_blueprint(path: Path, blueprint: dict[str, Any], *, force: bool = False) -> Path:
    """Validate and write a starter App Blueprint."""
    DomainPack.model_validate(blueprint)
    if path.exists() and not force:
        raise FileExistsError(f"refusing to overwrite existing file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(blueprint_to_yaml(blueprint), encoding="utf-8")
    return path
