"""Domain Pack loading and validation."""
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

VALID_ARCHETYPES = {
    "agent_dashboard_app",
    "ingestion_scoring_pipeline",
    "notification_triage_app",
    "hybrid_agent_pipeline",
    "deploy_planner_app",
    "project_workspace_app",
}

VALID_MODULES = {
    "agent", "workspace", "pipeline", "provider_adapter", "scoring_explanation",
    "operations_ui", "persistence", "test", "notification_action", "triage_ui",
    "observability_debug", "agent_runtime", "deploy_planner",
}

_DANGEROUS_TEXT_CHARS = set("<>{}`$")


def _clean_custom_text(value: str, *, field_name: str, max_length: int = 120) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) > max_length:
        raise ValueError(f"{field_name} must be {max_length} characters or fewer")
    if any(char in text for char in _DANGEROUS_TEXT_CHARS):
        raise ValueError(f"{field_name} contains unsupported characters")
    return text


def _clean_custom_list(values: list[str], *, field_name: str, max_items: int = 6, max_length: int = 80) -> list[str]:
    if len(values) > max_items:
        raise ValueError(f"{field_name} supports at most {max_items} items")
    cleaned = [
        _clean_custom_text(item, field_name=field_name, max_length=max_length)
        for item in values
    ]
    return [item for item in cleaned if item]


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


class WorkspaceConfig(BaseModel):
    enabled: bool = False
    persistence: dict[str, Any] = {}
    default_layout: list[str] = []
    remove_enabled: bool = True
    reorder_enabled: bool = True
    empty_state: str = ""
    frontend_surface: str = "workspace_panel"


class LabelPair(BaseModel):
    singular: str = ""
    plural: str = ""

    @field_validator("singular", "plural")
    @classmethod
    def labels_are_safe(cls, value: str) -> str:
        return _clean_custom_text(value, field_name="label", max_length=40)


class AppCustomization(BaseModel):
    subtitle: str = ""
    target_user_label: str = ""
    workflow_label: str = ""

    @field_validator("subtitle", "target_user_label", "workflow_label")
    @classmethod
    def app_text_is_safe(cls, value: str) -> str:
        return _clean_custom_text(value, field_name="app customization", max_length=240)


class WorkspaceCustomization(BaseModel):
    empty_state: str = ""
    widget_label: str = ""
    pinned_label: str = ""

    @field_validator("empty_state", "widget_label", "pinned_label")
    @classmethod
    def workspace_text_is_safe(cls, value: str) -> str:
        return _clean_custom_text(value, field_name="workspace customization")


class ScoringCustomization(BaseModel):
    record_label: LabelPair = Field(default_factory=lambda: LabelPair(singular="record", plural="records"))
    criteria_labels: list[str] = Field(default_factory=list)
    review_queue_label: str = ""
    notification_label: str = ""
    sample_data_label: str = ""

    @field_validator("criteria_labels")
    @classmethod
    def criteria_are_safe(cls, value: list[str]) -> list[str]:
        return _clean_custom_list(value, field_name="criteria_labels", max_items=5)

    @field_validator("review_queue_label", "notification_label", "sample_data_label")
    @classmethod
    def scoring_text_is_safe(cls, value: str) -> str:
        return _clean_custom_text(value, field_name="scoring customization")


class ProjectWorkspaceCustomization(BaseModel):
    project_label: LabelPair = Field(default_factory=lambda: LabelPair(singular="project", plural="projects"))
    task_label: LabelPair = Field(default_factory=lambda: LabelPair(singular="task", plural="tasks"))
    activity_label: str = ""
    sample_data_label: str = ""

    @field_validator("activity_label", "sample_data_label")
    @classmethod
    def project_text_is_safe(cls, value: str) -> str:
        return _clean_custom_text(value, field_name="project workspace customization")


class BlueprintCustomization(BaseModel):
    app: AppCustomization = Field(default_factory=AppCustomization)
    agent_starters: list[str] = Field(default_factory=list)
    workspace: WorkspaceCustomization = Field(default_factory=WorkspaceCustomization)
    scoring: ScoringCustomization = Field(default_factory=ScoringCustomization)
    project_workspace: ProjectWorkspaceCustomization = Field(default_factory=ProjectWorkspaceCustomization)

    @field_validator("agent_starters")
    @classmethod
    def starters_are_safe(cls, value: list[str]) -> list[str]:
        return _clean_custom_list(value, field_name="agent_starters", max_items=4)


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
    workspace: WorkspaceConfig | None = None
    customization: BlueprintCustomization = Field(default_factory=BlueprintCustomization)
    widgets: list[dict[str, Any]] = []
    tool_widget_compatibility: dict[str, list[str]] = {}
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
