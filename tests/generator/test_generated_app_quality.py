"""Generated App Quality v1 regression tests.

Covers the assistant + scripted planner naming, dashboard hero copy,
entity-aware empty states, and the absence of placeholder strings in
the generated React app.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "generator"))

from agentforge.generator import generate
from agentforge.pack import DomainPack
from agentforge.planner.assistant import BuilderAssistant, _model_blueprint_from_text
from agentforge.planner.scripted import ScriptedPlanner


def _start_assistant(prompt: str) -> dict:
    result = BuilderAssistant().start(prompt)
    assert result["status"] == "proposed", f"expected proposed status, got {result['status']} for {prompt!r}"
    return result["proposal"]["blueprint"]


@pytest.mark.parametrize(
    "prompt,expected_name",
    [
        ("dashboard for musician", "Musician Dashboard"),
        ("i want to manage my personal finances", "Personal Finance Manager"),
        ("dashboard for coaching nutrition", "Nutrition Coaching Dashboard"),
        ("hr manager dashboard", "HR Manager Dashboard"),
        (
            "i am a basketball coach, want to track clients and court vendors",
            "Basketball Coaching Dashboard",
        ),
        ("dashboard for life coach", "Life Coaching Dashboard"),
    ],
)
def test_blueprint_helper_produces_natural_app_names(prompt: str, expected_name: str) -> None:
    blueprint = _model_blueprint_from_text(prompt)
    assert blueprint["display_name"] == expected_name
    assert "Magician" not in blueprint["display_name"]
    assert not blueprint["display_name"].lower().startswith("i want")
    assert not blueprint["display_name"].lower().startswith("dashboard coaching")


def test_assistant_passes_natural_name_to_blueprint_when_proposing() -> None:
    blueprint = _start_assistant(
        "i am a basketball coach, want to track clients and court vendors"
    )
    assert blueprint["display_name"] == "Basketball Coaching Dashboard"


def test_scripted_planner_also_produces_natural_app_names() -> None:
    planner = ScriptedPlanner()
    result = planner.draft("ticket triage workflow for support operators with status and priority")
    blueprint = result.blueprint
    assert blueprint is not None
    # Scripted planner derives a natural app name from the idea text.
    assert "Triage" in blueprint["display_name"] or "Tracker" in blueprint["display_name"] or "Workspace" in blueprint["display_name"]
    assert blueprint["display_name"][0].isupper()


def test_blueprint_helper_carries_dashboard_headline_and_summary() -> None:
    blueprint = _model_blueprint_from_text(
        "i am a basketball coach, want to track clients and court vendors"
    )
    dashboard = blueprint["model"]["ui"]["dashboard"]
    assert dashboard.get("headline") == blueprint["display_name"]
    assert dashboard.get("summary"), "dashboard should carry a domain summary"
    assert "." in dashboard["summary"]


def test_generated_app_has_natural_hero_and_no_placeholder_text(tmp_path: Path) -> None:
    blueprint = _start_assistant(
        "i am a basketball coach, want to track clients and court vendors"
    )
    pack = DomainPack.model_validate(blueprint)
    out = tmp_path / pack.name
    generate(pack, out)
    app_tsx = (out / "frontend/src/App.tsx").read_text(encoding="utf-8")
    app_model = json.loads((out / "app-model.json").read_text(encoding="utf-8"))

    assert "Basketball Coaching Dashboard" == app_model["app"]["displayName"]
    assert "HeroBanner" in app_tsx
    assert "appName()" in app_tsx
    assert "heroHeadline" in app_tsx
    assert "heroSummary" in app_tsx
    assert "Example item" not in app_tsx
    assert "Replace this model in Blueprint source" not in app_tsx
    assert 'model.ui.dashboard.title' not in app_tsx
    assert "No related records yet." not in app_tsx
    assert "No items yet." not in app_tsx
    assert "No records yet — load seed data or create one." not in app_tsx


def test_entity_empty_states_are_domain_aware(tmp_path: Path) -> None:
    blueprint = _model_blueprint_from_text(
        "client onboarding workflow with clients and onboarding tasks to track status"
    )
    pack = DomainPack.model_validate(blueprint)
    out = tmp_path / pack.name
    generate(pack, out)
    app_tsx = (out / "frontend/src/App.tsx").read_text(encoding="utf-8")

    assert "emptyForList" in app_tsx
    assert "emptyForRelated" in app_tsx
    assert "emptyForLane" in app_tsx
    assert "load seed data or create your first" in app_tsx
    assert "add one after you create a" in app_tsx


def test_section_headings_are_friendly_not_register_or_board(tmp_path: Path) -> None:
    blueprint = _start_assistant(
        "vendor risk register to review findings with severity, status, owner"
    )
    pack = DomainPack.model_validate(blueprint)
    out = tmp_path / pack.name
    generate(pack, out)
    app_tsx = (out / "frontend/src/App.tsx").read_text(encoding="utf-8")

    assert "Risk Findings" in app_tsx
    assert "labelPlural} Board" not in app_tsx
    assert "labelPlural} Register" not in app_tsx


def test_generic_starter_no_longer_uses_example_item_placeholder() -> None:
    from agentforge.blueprints import create_starter_blueprint

    blueprint = create_starter_blueprint("my-app", archetype="model_driven_app")
    seed = blueprint["model"]["seed_data"]["item"][0]
    assert seed["title"] != "Example item"
    assert "Edit the model block" not in seed.get("notes", "")


def test_visual_hierarchy_styles_include_hero_banner(tmp_path: Path) -> None:
    blueprint = _model_blueprint_from_text("dashboard for musician with songs and performances")
    pack = DomainPack.model_validate(blueprint)
    out = tmp_path / pack.name
    generate(pack, out)
    styles = (out / "frontend/src/styles.css").read_text(encoding="utf-8")

    assert ".hero-banner" in styles
    assert "hero-summary" in styles
    assert "hero-actions" in styles
    assert "max-width:1320px" in styles


@pytest.mark.parametrize(
    "prompt,acceptable_names",
    [
        (
            "i want a website to control my assets (houses + cash)",
            {"Asset Manager", "Property and Cash Manager", "Asset Control Workspace"},
        ),
        (
            "i need an app to assist me in my work as a marketing manager",
            {"Marketing Manager Workspace", "Marketing Campaign Workspace", "Marketing Operations Workspace"},
        ),
    ],
)
def test_blueprint_helper_handles_wrapper_phrase_prompts(
    prompt: str, acceptable_names: set[str]
) -> None:
    blueprint = _model_blueprint_from_text(prompt)
    assert blueprint["display_name"] in acceptable_names, (
        f"{blueprint['display_name']!r} from {prompt!r} should be one of {acceptable_names}"
    )
    # The pack slug must follow the cleaned display name, not the raw prompt.
    assert "i-want" not in blueprint["name"]
    assert "i-need" not in blueprint["name"]
    assert "assist" not in blueprint["name"]
    assert "website" not in blueprint["name"]


_BAD_PROMPT_FRAGMENTS = (
    "Website Control Assets Houses Cash Workspace",
    "Marketing I Need Assist Me In Work As Marketing Manager Workspace",
    "I Need Assist Me",
    "I Want",
    "Example item",
    "Replace this model",
)


@pytest.mark.parametrize(
    "prompt",
    [
        "i want a website to control my assets (houses + cash)",
        "i need an app to assist me in my work as a marketing manager",
    ],
)
def test_generated_app_does_not_contain_prompt_fragment_slop(tmp_path: Path, prompt: str) -> None:
    blueprint = _model_blueprint_from_text(prompt)
    pack = DomainPack.model_validate(blueprint)
    out = tmp_path / pack.name
    generate(pack, out)
    surfaces = {
        "app.tsx": (out / "frontend/src/App.tsx").read_text(encoding="utf-8"),
        "app-model.json": (out / "app-model.json").read_text(encoding="utf-8"),
    }
    for surface_name, contents in surfaces.items():
        for fragment in _BAD_PROMPT_FRAGMENTS:
            assert fragment not in contents, (
                f"{surface_name} from {prompt!r} should not contain {fragment!r}"
            )


def test_generated_app_displayname_and_description_use_natural_copy(tmp_path: Path) -> None:
    blueprint = _model_blueprint_from_text(
        "i need an app to assist me in my work as a marketing manager"
    )
    pack = DomainPack.model_validate(blueprint)
    out = tmp_path / pack.name
    generate(pack, out)
    app_model = json.loads((out / "app-model.json").read_text(encoding="utf-8"))

    display_name = app_model["app"]["displayName"]
    description = app_model["app"]["description"]
    assert display_name == blueprint["display_name"]
    # Hero / sidebar copy must never echo the raw wrapper-phrase prompt.
    for surface in (display_name, description):
        lower = surface.lower()
        for filler in ("i need", "i want", "assist me", "(houses", "+ cash", "my work as"):
            assert filler not in lower, f"{surface!r} should not contain {filler!r}"


def test_generated_app_load_function_validates_response_shape(tmp_path: Path) -> None:
    """White-screen runtime regression (2026-05-23): a 404 or non-array response
    from an entity route was assigned to rowsByEntity, then rendered with .filter()
    which crashed React. The generated load() must guard with response.ok and
    Array.isArray.
    """
    blueprint = _model_blueprint_from_text("website for skateboard shop")
    pack = DomainPack.model_validate(blueprint)
    out = tmp_path / pack.name
    generate(pack, out)
    app_tsx = (out / "frontend/src/App.tsx").read_text(encoding="utf-8")

    # The defensive helper is generated.
    assert "const asRows = (value: unknown): Row[] =>" in app_tsx
    assert "Array.isArray(value)" in app_tsx

    # The load function checks response.ok and never stores raw response.json().
    assert "async function load(" in app_tsx
    assert "if (!response.ok)" in app_tsx
    assert "asRows(data)" in app_tsx

    # The previous unsafe pattern is gone everywhere it consumed rowsByEntity.
    assert "rowsByEntity[ctx.primary.name] || []" not in app_tsx
    assert "rowsByEntity[ctx.secondary.name] || []" not in app_tsx
    assert "rowsByEntity[ctx.activeEntity.name] || []" not in app_tsx
    assert "rowsByEntity[entity.name] || []" not in app_tsx
    assert "rowsByEntity[card.entity] || []" not in app_tsx
    assert "(rowsByEntity[field.targetEntity] || [])" not in app_tsx


@pytest.mark.parametrize(
    "prompt",
    [
        "website for skateboard shop",
        "website for managing livestock in a farm",
        "i am a basketball coach, want to track clients and court vendors",
        "vendor risk register to review findings with severity, status, owner",
    ],
)
def test_generated_app_render_helpers_use_asrows_consistently(tmp_path: Path, prompt: str) -> None:
    """For any prompt shape, every place that reads rowsByEntity[<name>] for
    rendering must go through asRows so a 404 / non-list response cannot crash
    React after the first render."""
    blueprint = _model_blueprint_from_text(prompt)
    pack = DomainPack.model_validate(blueprint)
    out = tmp_path / pack.name
    generate(pack, out)
    app_tsx = (out / "frontend/src/App.tsx").read_text(encoding="utf-8")

    # Every consumer is asRows-wrapped.
    assert "asRows(ctx.rowsByEntity[ctx.primary.name])" in app_tsx
    assert "asRows(rowsByEntity[card.entity])" in app_tsx
    assert "asRows(rowsByEntity[field.targetEntity])" in app_tsx


def test_generated_app_does_not_contain_known_runtime_crash_patterns(tmp_path: Path) -> None:
    """Belt-and-suspenders guard against patterns that previously turned the
    generated React app white half a second after first render."""
    blueprint = _model_blueprint_from_text("website for skateboard shop")
    pack = DomainPack.model_validate(blueprint)
    out = tmp_path / pack.name
    generate(pack, out)
    app_tsx = (out / "frontend/src/App.tsx").read_text(encoding="utf-8")

    # The exact crash pattern: response.json() assigned without shape validation.
    assert "[selected.name]: data })" not in app_tsx
    # No top-level .filter on a raw rowsByEntity bucket.
    for token in (
        "(rowsByEntity[card.entity] || []).filter",
        "rowsByEntity[ctx.primary.name].filter",
    ):
        assert token not in app_tsx
