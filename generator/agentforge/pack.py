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
    "model_driven_app",
}

VALID_MODULES = {
    "agent", "workspace", "pipeline", "provider_adapter", "scoring_explanation",
    "operations_ui", "persistence", "test", "notification_action", "triage_ui",
    "observability_debug", "agent_runtime", "deploy_planner", "model_driven",
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


_IDENTIFIER_RE = r"^[a-z][a-z0-9_]*$"
_VALID_MODEL_FIELD_TYPES = {"string", "text", "integer", "boolean", "date", "enum", "relation"}
_VALID_MODEL_PAGE_TYPES = {"dashboard", "entity_list", "entity_detail"}
_VALID_MODEL_ACTION_TYPES = {"update_status", "add_note", "mark_complete"}
_VALID_IMPORT_FORMATS = {"csv", "json"}
_VALID_UI_ACCENTS = {"blue", "emerald", "amber", "red", "slate", "violet"}
_VALID_UI_DENSITIES = {"compact", "comfortable", "spacious"}
_VALID_UI_LAYOUTS = {"workspace", "register", "operations"}
_VALID_ENTITY_DISPLAY_LAYOUTS = {"table", "cards", "board_by_status"}
_VALID_DASHBOARD_CARD_TYPES = {"count", "enum_breakdown", "attention_list"}
_VALID_FIELD_SEMANTICS = {"status", "priority", "severity", "owner", "due_date", "title", "description"}
_VALID_UI_COMPOSITIONS = {"standard", "board_workspace", "register_table"}
_VALID_UI_RECIPES = {"standard", "workspace_board", "executive_register", "ops_console"}


class ModelField(BaseModel):
    name: str = Field(pattern=_IDENTIFIER_RE)
    label: str = ""
    type: str
    required: bool = False
    enum_values: list[str] = Field(default_factory=list)
    target_entity: str = ""
    relation_kind: str = "many_to_one"
    semantic: str = ""

    @field_validator("type")
    @classmethod
    def type_must_be_supported(cls, value: str) -> str:
        if value not in _VALID_MODEL_FIELD_TYPES:
            raise ValueError(f"unsupported model field type '{value}'; valid: {sorted(_VALID_MODEL_FIELD_TYPES)}")
        return value

    @field_validator("label")
    @classmethod
    def label_is_safe(cls, value: str) -> str:
        return _clean_custom_text(value, field_name="model field label", max_length=80)

    @field_validator("semantic")
    @classmethod
    def semantic_must_be_supported(cls, value: str) -> str:
        if value and value not in _VALID_FIELD_SEMANTICS:
            raise ValueError(f"unsupported field semantic '{value}'; valid: {sorted(_VALID_FIELD_SEMANTICS)}")
        return value

    @field_validator("enum_values")
    @classmethod
    def enum_values_are_safe(cls, value: list[str]) -> list[str]:
        return _clean_custom_list(value, field_name="enum_values", max_items=12, max_length=40)

    @model_validator(mode="after")
    def validate_type_specific_fields(self) -> "ModelField":
        if self.type == "enum" and not self.enum_values:
            raise ValueError(f"enum field '{self.name}' must define enum_values")
        if self.type != "enum" and self.enum_values:
            raise ValueError(f"non-enum field '{self.name}' must not define enum_values")
        if self.type == "relation":
            if not self.target_entity:
                raise ValueError(f"relation field '{self.name}' must define target_entity")
            if self.relation_kind not in {"many_to_one", "reference"}:
                raise ValueError(f"relation field '{self.name}' supports only many_to_one/reference")
        return self


class ModelEntity(BaseModel):
    name: str = Field(pattern=_IDENTIFIER_RE)
    label_singular: str
    label_plural: str
    fields: list[ModelField]

    @field_validator("label_singular", "label_plural")
    @classmethod
    def labels_are_safe(cls, value: str) -> str:
        text = _clean_custom_text(value, field_name="model entity label", max_length=80)
        if not text:
            raise ValueError("model entity labels are required")
        return text

    @model_validator(mode="after")
    def fields_are_valid(self) -> "ModelEntity":
        if not self.fields:
            raise ValueError(f"model entity '{self.name}' must define at least one field")
        names = [field.name for field in self.fields]
        if len(names) != len(set(names)):
            raise ValueError(f"model entity '{self.name}' has duplicate field names")
        return self


class ModelPage(BaseModel):
    name: str = Field(pattern=_IDENTIFIER_RE)
    type: str
    entity: str | None = None
    title: str = ""

    @field_validator("type")
    @classmethod
    def type_must_be_supported(cls, value: str) -> str:
        if value not in _VALID_MODEL_PAGE_TYPES:
            raise ValueError(f"unsupported model page type '{value}'; valid: {sorted(_VALID_MODEL_PAGE_TYPES)}")
        return value


class ModelAction(BaseModel):
    name: str = Field(pattern=_IDENTIFIER_RE)
    label: str = ""
    type: str
    entity: str
    field: str | None = None
    value: Any | None = None

    @field_validator("type")
    @classmethod
    def type_must_be_supported(cls, value: str) -> str:
        if value not in _VALID_MODEL_ACTION_TYPES:
            raise ValueError(f"unsupported model action type '{value}'; valid: {sorted(_VALID_MODEL_ACTION_TYPES)}")
        return value


class ModelUIStyle(BaseModel):
    accent: str = "blue"
    density: str = "comfortable"
    layout: str = "workspace"

    @field_validator("accent")
    @classmethod
    def accent_must_be_supported(cls, value: str) -> str:
        if value not in _VALID_UI_ACCENTS:
            raise ValueError(f"unknown ui accent '{value}'; valid: {sorted(_VALID_UI_ACCENTS)}")
        return value

    @field_validator("density")
    @classmethod
    def density_must_be_supported(cls, value: str) -> str:
        if value not in _VALID_UI_DENSITIES:
            raise ValueError(f"unknown ui density '{value}'; valid: {sorted(_VALID_UI_DENSITIES)}")
        return value

    @field_validator("layout")
    @classmethod
    def layout_must_be_supported(cls, value: str) -> str:
        if value not in _VALID_UI_LAYOUTS:
            raise ValueError(f"unknown ui layout '{value}'; valid: {sorted(_VALID_UI_LAYOUTS)}")
        return value


class ModelEntityDisplay(BaseModel):
    layout: str = "table"
    title_field: str = ""
    subtitle_field: str = ""
    badge_field: str = ""
    secondary_field: str = ""

    @field_validator("layout")
    @classmethod
    def layout_must_be_supported(cls, value: str) -> str:
        if value not in _VALID_ENTITY_DISPLAY_LAYOUTS:
            raise ValueError(f"unknown entity display layout '{value}'; valid: {sorted(_VALID_ENTITY_DISPLAY_LAYOUTS)}")
        return value


class ModelEntityUI(BaseModel):
    display: ModelEntityDisplay = Field(default_factory=ModelEntityDisplay)


class ModelDashboardCard(BaseModel):
    type: str
    entity: str
    label: str = ""
    field: str = ""
    value: Any | None = None

    @field_validator("type")
    @classmethod
    def type_must_be_supported(cls, value: str) -> str:
        if value not in _VALID_DASHBOARD_CARD_TYPES:
            raise ValueError(f"unknown dashboard card type '{value}'; valid: {sorted(_VALID_DASHBOARD_CARD_TYPES)}")
        return value

    @field_validator("label")
    @classmethod
    def label_is_safe(cls, value: str) -> str:
        return _clean_custom_text(value, field_name="dashboard card label", max_length=80)


class ModelDashboardUI(BaseModel):
    title: str = "Dashboard"
    primary_entity: str = ""
    cards: list[ModelDashboardCard] = Field(default_factory=list)

    @field_validator("title")
    @classmethod
    def title_is_safe(cls, value: str) -> str:
        return _clean_custom_text(value, field_name="dashboard title", max_length=120) or "Dashboard"


class ModelUIFocus(BaseModel):
    primary_entity: str = ""
    secondary_entity: str = ""
    group_by: str = ""
    title_field: str = ""
    badge_field: str = ""
    secondary_field: str = ""


class ModelUI(BaseModel):
    composition: str = "standard"
    recipe: str = "standard"
    style: ModelUIStyle = Field(default_factory=ModelUIStyle)
    focus: ModelUIFocus = Field(default_factory=ModelUIFocus)
    dashboard: ModelDashboardUI = Field(default_factory=ModelDashboardUI)
    entities: dict[str, ModelEntityUI] = Field(default_factory=dict)

    @field_validator("composition")
    @classmethod
    def composition_must_be_supported(cls, value: str) -> str:
        if value not in _VALID_UI_COMPOSITIONS:
            raise ValueError(f"unknown ui composition '{value}'; valid: {sorted(_VALID_UI_COMPOSITIONS)}")
        return value

    @field_validator("recipe")
    @classmethod
    def recipe_must_be_supported(cls, value: str) -> str:
        if value not in _VALID_UI_RECIPES:
            raise ValueError(f"unknown ui recipe '{value}'; valid: {sorted(_VALID_UI_RECIPES)}")
        return value


class ModelImport(BaseModel):
    id: str = Field(pattern=_IDENTIFIER_RE)
    label: str = ""
    entity: str
    formats: list[str] = Field(default_factory=lambda: ["csv", "json"])
    upsert_key: str = ""
    field_map: dict[str, str] = Field(default_factory=dict)

    @field_validator("label")
    @classmethod
    def label_is_safe(cls, value: str) -> str:
        return _clean_custom_text(value, field_name="import label", max_length=120)

    @field_validator("formats")
    @classmethod
    def formats_must_be_supported(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("import formats must include at least one of csv, json")
        unknown = [item for item in value if item not in _VALID_IMPORT_FORMATS]
        if unknown:
            raise ValueError(f"unsupported import formats {unknown}; valid: {sorted(_VALID_IMPORT_FORMATS)}")
        deduped: list[str] = []
        for item in value:
            if item not in deduped:
                deduped.append(item)
        return deduped


class ModelDrivenApp(BaseModel):
    entities: list[ModelEntity]
    pages: list[ModelPage] = Field(default_factory=list)
    actions: list[ModelAction] = Field(default_factory=list)
    seed_data: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    ui: ModelUI = Field(default_factory=ModelUI)
    imports: list[ModelImport] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_references(self) -> "ModelDrivenApp":
        if not self.entities:
            raise ValueError("model_driven_app requires at least one entity")
        entity_names = [entity.name for entity in self.entities]
        if len(entity_names) != len(set(entity_names)):
            raise ValueError("model_driven_app entity names must be unique")
        entity_map = {entity.name: entity for entity in self.entities}
        for entity in self.entities:
            for field in entity.fields:
                if field.type == "relation" and field.target_entity not in entity_map:
                    raise ValueError(f"relation field '{entity.name}.{field.name}' targets unknown entity '{field.target_entity}'")
        for page in self.pages:
            if page.type != "dashboard" and not page.entity:
                raise ValueError(f"page '{page.name}' must define entity")
            if page.entity and page.entity not in entity_map:
                raise ValueError(f"page '{page.name}' references unknown entity '{page.entity}'")
        for action in self.actions:
            entity = entity_map.get(action.entity)
            if not entity:
                raise ValueError(f"action '{action.name}' references unknown entity '{action.entity}'")
            fields = {field.name: field for field in entity.fields}
            if action.type == "update_status":
                if not action.field or action.field not in fields:
                    raise ValueError(f"update_status action '{action.name}' must reference a field on '{action.entity}'")
                field = fields[action.field]
                if field.type != "enum":
                    raise ValueError(f"update_status action '{action.name}' field must be enum")
                if action.value not in field.enum_values:
                    raise ValueError(f"update_status action '{action.name}' value must be one of {field.enum_values}")
            if action.type == "mark_complete":
                field_name = action.field or "complete"
                field = fields.get(field_name)
                if not field or field.type != "boolean":
                    raise ValueError(f"mark_complete action '{action.name}' field must be a boolean field")
        ui = self.ui
        if ui.dashboard.primary_entity and ui.dashboard.primary_entity not in entity_map:
            raise ValueError(f"dashboard primary_entity references unknown entity '{ui.dashboard.primary_entity}'")
        focus = ui.focus
        if ui.composition != "standard" and not focus.primary_entity:
            raise ValueError(f"ui composition '{ui.composition}' requires focus.primary_entity")
        if focus.primary_entity and focus.primary_entity not in entity_map:
            raise ValueError(f"ui focus primary_entity references unknown entity '{focus.primary_entity}'")
        if focus.secondary_entity and focus.secondary_entity not in entity_map:
            raise ValueError(f"ui focus secondary_entity references unknown entity '{focus.secondary_entity}'")
        primary = entity_map.get(focus.primary_entity) if focus.primary_entity else None
        if primary:
            primary_fields = {field.name: field for field in primary.fields}
            for attr in ["group_by", "title_field", "badge_field", "secondary_field"]:
                field_name = getattr(focus, attr)
                if field_name and field_name not in primary_fields:
                    raise ValueError(f"ui focus {attr} references unknown field '{field_name}' on '{focus.primary_entity}'")
            if ui.composition == "board_workspace" and focus.group_by and primary_fields[focus.group_by].type != "enum":
                raise ValueError("ui focus group_by must be an enum field for board_workspace composition")
        for entity_name, entity_ui in ui.entities.items():
            entity = entity_map.get(entity_name)
            if not entity:
                raise ValueError(f"ui entity display references unknown entity '{entity_name}'")
            fields = {field.name for field in entity.fields}
            display = entity_ui.display
            for attr in ["title_field", "subtitle_field", "badge_field", "secondary_field"]:
                field_name = getattr(display, attr)
                if field_name and field_name not in fields:
                    raise ValueError(f"ui entity '{entity_name}' {attr} references unknown field '{field_name}'")
        for card in ui.dashboard.cards:
            entity = entity_map.get(card.entity)
            if not entity:
                raise ValueError(f"dashboard card '{card.label or card.type}' references unknown entity '{card.entity}'")
            fields = {field.name: field for field in entity.fields}
            if card.type in {"enum_breakdown", "attention_list"}:
                if not card.field or card.field not in fields:
                    raise ValueError(f"dashboard card '{card.label or card.type}' references unknown field '{card.field}' on '{card.entity}'")
                if card.type == "enum_breakdown" and fields[card.field].type != "enum":
                    raise ValueError(f"dashboard enum_breakdown card '{card.label or card.type}' field must be enum")
            if card.type == "attention_list":
                if card.value is None:
                    raise ValueError(f"dashboard attention_list card '{card.label or card.type}' requires value")
                field = fields[card.field]
                if field.type == "enum" and card.value not in field.enum_values:
                    raise ValueError(f"dashboard attention_list card '{card.label or card.type}' value must be one of {field.enum_values}")
        import_ids: set[str] = set()
        for spec in self.imports:
            if spec.id in import_ids:
                raise ValueError(f"import id '{spec.id}' is duplicated")
            import_ids.add(spec.id)
            entity = entity_map.get(spec.entity)
            if not entity:
                raise ValueError(f"import '{spec.id}' references unknown entity '{spec.entity}'")
            field_names = {field.name for field in entity.fields}
            if spec.upsert_key and spec.upsert_key not in field_names:
                raise ValueError(f"import '{spec.id}' upsert_key references unknown field '{spec.upsert_key}'")
            for source_key, target_field in spec.field_map.items():
                if not source_key.strip():
                    raise ValueError(f"import '{spec.id}' field_map has empty source key")
                if target_field not in field_names:
                    raise ValueError(f"import '{spec.id}' field_map target field '{target_field}' is not defined on '{spec.entity}'")
        for entity_name, rows in self.seed_data.items():
            if entity_name not in entity_map:
                raise ValueError(f"seed_data references unknown entity '{entity_name}'")
            fields = {field.name: field for field in entity_map[entity_name].fields}
            for row in rows:
                for key, value in row.items():
                    if key not in fields:
                        raise ValueError(f"seed_data for '{entity_name}' includes unknown field '{key}'")
                    field = fields[key]
                    if field.type == "enum" and value not in field.enum_values:
                        raise ValueError(f"seed_data for '{entity_name}.{key}' must be one of {field.enum_values}")
        return self


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
    model: ModelDrivenApp | None = None
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
        if self.app_archetype == "model_driven_app" and self.model is None:
            raise ValueError("model_driven_app must include a model block")
        return self


def load_pack(path: Path) -> DomainPack:
    """Load and validate a domain-pack.yaml file."""
    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return DomainPack.model_validate(raw)
