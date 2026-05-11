"""Blueprint planner contract for AgentForge v0.6."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from agentforge.blueprints import blueprint_to_yaml
from agentforge.pack import DomainPack


@dataclass
class PlannerResult:
    """Structured output returned by blueprint planners."""

    status: str
    questions: list[str] = field(default_factory=list)
    blueprint: dict[str, Any] | None = None
    yaml: str | None = None
    assumptions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggested_modules: list[str] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class Planner(Protocol):
    """Blueprint-only planner interface."""

    def draft(self, idea: str, prior_answers: dict[str, str] | None = None) -> PlannerResult:
        """Draft a blueprint or ask clarifying questions."""

    def refine(self, blueprint: dict[str, Any], instruction: str) -> PlannerResult:
        """Return an updated blueprint for a bounded refinement instruction."""


def validate_blueprint_result(
    blueprint: dict[str, Any] | None,
    *,
    assumptions: list[str] | None = None,
    warnings: list[str] | None = None,
    suggested_modules: list[str] | None = None,
) -> PlannerResult:
    """Validate a planner blueprint with the generator schema before returning it."""
    if not isinstance(blueprint, dict):
        return PlannerResult(status="error", errors=["planner did not return a blueprint object"])

    try:
        pack = DomainPack.model_validate(blueprint)
    except Exception as exc:
        return PlannerResult(status="error", errors=[f"invalid App Blueprint: {exc}"])

    yaml_text = blueprint_to_yaml(blueprint)
    path = f"./domain-packs/{pack.name}/domain-pack.yaml"
    return PlannerResult(
        status="draft",
        blueprint=blueprint,
        yaml=yaml_text,
        assumptions=assumptions or [],
        warnings=warnings or [],
        suggested_modules=suggested_modules or [],
        commands=[
            f"agentforge plan {path}",
            f"agentforge generate {path} --force",
        ],
    )


__all__ = ["Planner", "PlannerResult", "validate_blueprint_result"]
