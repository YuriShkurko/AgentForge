"""Domain Pack loading and validation."""
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, field_validator, model_validator

VALID_ARCHETYPES = {
    "agent_dashboard_app",
    "ingestion_scoring_pipeline",
    "notification_triage_app",
    "hybrid_agent_pipeline",
    "deploy_planner_app",
}

VALID_MODULES = {
    "agent", "workspace", "pipeline", "provider_adapter", "scoring_explanation",
    "operations_ui", "persistence", "test", "notification_action", "triage_ui",
    "observability_debug", "agent_runtime", "deploy_planner",
}


class DomainInfo(BaseModel):
    domain_name: str
    app_type: str
    target_users: list[str] = []
    product_purpose: str = ""
    main_user_goals: list[str] = []


class RunHistory(BaseModel):
    enabled: bool = True
    table_name: str = "provider_runs"
    tracked_fields: list[str] = []
    frontend_surface: str = ""


class TestConfig(BaseModel):
    expectations: dict[str, Any] = {}
    commands: dict[str, str] = {}
    backend: dict[str, Any] = {}
    frontend: dict[str, Any] = {}


class AgentRuntimeConfig(BaseModel):
    enabled: bool = False
    provider_mode: str = "scripted"
    scripted_fixture_path: str | None = None
    scripted_turns: list[dict[str, Any]] = []
    tools: list[dict[str, Any]] = []
    conversation_persistence: dict[str, Any] = {}
    streaming: dict[str, Any] = {}
    guardrails: dict[str, Any] = {}


class DomainPack(BaseModel):
    name: str
    display_name: str
    version: str = "0.1.0"
    app_archetype: str
    required_shell_modules: list[str]
    optional_shell_modules: list[str] = []
    domain: DomainInfo
    capabilities: list[dict[str, Any]] = []
    tools: list[dict[str, Any]] = []  # full agent/dashboard archetypes; pipeline agent tools live in agent_runtime
    ui_surfaces: list[dict[str, Any]] = []
    providers: dict[str, Any] = {}
    adapters: list[dict[str, Any]] = []
    run_history: RunHistory | None = None
    agent_runtime: AgentRuntimeConfig | None = None
    notification_actions: list[dict[str, Any]] = []
    workflows: list[dict[str, Any]] = []
    seed_data: dict[str, Any] = {}
    tests: TestConfig | dict[str, Any] = {}
    future_extensions: dict[str, Any] = {}
    compatibility_gaps: list[str] = []

    @field_validator("app_archetype")
    @classmethod
    def archetype_must_be_known(cls, v: str) -> str:
        if v not in VALID_ARCHETYPES:
            raise ValueError(f"unknown app_archetype '{v}'; valid: {sorted(VALID_ARCHETYPES)}")
        return v

    @field_validator("required_shell_modules", "optional_shell_modules")
    @classmethod
    def modules_must_be_known(cls, v: list[str]) -> list[str]:
        unknown = set(v) - VALID_MODULES
        if unknown:
            raise ValueError(f"unknown shell modules: {sorted(unknown)}")
        return v

    @model_validator(mode="after")
    def agent_archetype_needs_agent_module(self) -> "DomainPack":
        if self.app_archetype == "agent_dashboard_app":
            all_modules = set(self.required_shell_modules) | set(self.optional_shell_modules)
            if "agent" not in all_modules:
                raise ValueError("agent_dashboard_app must include 'agent' in required_shell_modules")
        return self


def load_pack(path: Path) -> DomainPack:
    """Load and validate a domain-pack.yaml file."""
    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return DomainPack.model_validate(raw)
