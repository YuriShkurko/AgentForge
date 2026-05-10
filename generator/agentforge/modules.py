"""Shell module selection and template mapping."""
from dataclasses import dataclass, field

from agentforge.pack import DomainPack

# Canonical required modules per archetype (generator enforces these minimums)
ARCHETYPE_REQUIRED_MODULES: dict[str, set[str]] = {
    "agent_dashboard_app": {"agent", "workspace", "provider_adapter", "test"},
    "ingestion_scoring_pipeline": {
        "pipeline", "provider_adapter", "scoring_explanation",
        "operations_ui", "persistence", "test",
    },
    "notification_triage_app": {
        "notification_action", "triage_ui", "persistence", "scoring_explanation",
    },
    "hybrid_agent_pipeline": {"pipeline", "provider_adapter", "operations_ui"},
    "deploy_planner_app": {"pipeline", "persistence", "test"},
}

# Which base template directory to use for each archetype
ARCHETYPE_TEMPLATE: dict[str, str] = {
    "agent_dashboard_app": "fastapi-react",
    "ingestion_scoring_pipeline": "fastapi-react",
    "notification_triage_app": "fastapi-react",
    "hybrid_agent_pipeline": "fastapi-react",
    "deploy_planner_app": "fastapi-react",
}


@dataclass
class ModuleSelection:
    archetype: str
    required: set[str]
    optional: set[str]
    active: set[str]
    template: str
    gaps: list[str] = field(default_factory=list)


def select_modules(pack: DomainPack) -> ModuleSelection:
    """
    Determine which shell modules to wire and which template to use.
    Gaps are modules declared in the pack but not yet supported by any template.
    """
    canonical = ARCHETYPE_REQUIRED_MODULES.get(pack.app_archetype, set())
    declared_required = set(pack.required_shell_modules)
    declared_optional = set(pack.optional_shell_modules)

    # Warn if pack declares fewer required modules than canonical minimum
    missing_from_pack = canonical - declared_required
    gaps = [f"pack missing canonical required module: {m}" for m in sorted(missing_from_pack)]

    # Modules declared but not yet in any template (future extensions)
    unsupported = {"workspace", "observability_debug", "deploy_planner"}
    unresolved = (declared_required | declared_optional) & unsupported
    gaps += [f"module not yet in template: {m}" for m in sorted(unresolved)]
    active = (declared_required | declared_optional) - unsupported

    template = ARCHETYPE_TEMPLATE.get(pack.app_archetype, "fastapi-react")

    return ModuleSelection(
        archetype=pack.app_archetype,
        required=declared_required,
        optional=declared_optional,
        active=active,
        template=template,
        gaps=gaps,
    )
