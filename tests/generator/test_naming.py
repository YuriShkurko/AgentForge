"""Unit tests for the deterministic naming/copy helpers."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "generator"))

from agentforge.naming import (
    clean_prompt,
    domain_summary,
    empty_state_lane,
    empty_state_list,
    empty_state_related,
    natural_app_name,
    natural_pack_slug,
    section_heading,
)


@pytest.mark.parametrize(
    "prompt,expected",
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
        ("track my running", "Running Tracker"),
        ("invoice tracker for designers", "Invoice Designer Tracker"),
    ],
)
def test_natural_app_name_produces_friendly_titles(prompt: str, expected: str) -> None:
    assert natural_app_name(prompt) == expected


@pytest.mark.parametrize(
    "prompt,acceptable",
    [
        # Spec bad-example #1: a prompt-fragment slop that previously yielded
        # 'Website Control Assets Houses Cash Workspace'.
        (
            "i want a website to control my assets (houses + cash)",
            {"Asset Manager", "Property and Cash Manager", "Asset Control Workspace"},
        ),
        # Spec bad-example #2: previously 'Marketing I Need Assist Me In Work
        # As Marketing Manager Workspace'.
        (
            "i need an app to assist me in my work as a marketing manager",
            {"Marketing Manager Workspace", "Marketing Campaign Workspace", "Marketing Operations Workspace"},
        ),
    ],
)
def test_natural_app_name_handles_wrapper_phrase_prompts(prompt: str, acceptable: set[str]) -> None:
    assert natural_app_name(prompt) in acceptable


@pytest.mark.parametrize(
    "prompt",
    [
        "i want a website to control my assets (houses + cash)",
        "i need an app to assist me in my work as a marketing manager",
        "i want a tool to monitor my expenses",
        "i need a system to manage work orders",
        "help me track my reading list",
        "make me an app to organize my tasks",
    ],
)
def test_natural_app_name_never_contains_filler_fragments(prompt: str) -> None:
    name = natural_app_name(prompt)
    lower = name.lower()
    for filler in ("i want", "i need", "i'd", "assist me", "i am", "i'm", "help me", "make me", "would like"):
        assert filler not in lower, f"{name!r} from {prompt!r} still contains {filler!r}"
    assert "(" not in name and ")" not in name


@pytest.mark.parametrize(
    "prompt,cleaned",
    [
        ("i want a website to control my assets (houses + cash)", "assets"),
        ("i need an app to assist me in my work as a marketing manager", "marketing manager"),
        ("i want a tool to monitor my expenses", "expenses"),
        ("i need a system to manage work orders", "work orders"),
        ("help me track my reading list", "reading list"),
        ("make me an app to organize my tasks", "tasks"),
        ("i'd like a dashboard to oversee my team", "team"),
    ],
)
def test_clean_prompt_strips_wrapper_phrases(prompt: str, cleaned: str) -> None:
    assert clean_prompt(prompt) == cleaned


def test_natural_app_name_uses_entity_umbrella_when_prompt_is_empty() -> None:
    # No prompt, but the model has asset-flavored entities — naming should
    # surface a domain umbrella rather than a generic 'AgentForge App'.
    assert natural_app_name("", entities=["house", "cash_asset"]) == "Asset Manager"


def test_natural_app_name_uses_entity_umbrella_for_marketing_entities() -> None:
    name = natural_app_name(
        "",
        entities=["campaign", "target_audience", "marketing_channel"],
    )
    assert name.startswith("Marketing"), f"expected Marketing umbrella, got {name!r}"
    assert "Workspace" in name or "Manager" in name


def test_natural_app_name_entities_fallback_only_when_prompt_is_empty() -> None:
    # A real prompt always wins over the entity fallback.
    name = natural_app_name(
        "dashboard for musician",
        entities=["house", "cash_asset"],
    )
    assert name == "Musician Dashboard"


def test_natural_app_name_falls_back_to_two_entity_join_without_umbrella() -> None:
    name = natural_app_name("", entities=["course", "student"])
    assert "Workspace" in name
    assert "Course" in name and "Student" in name


def test_natural_app_name_fallbacks_to_primary_entity() -> None:
    assert natural_app_name("", primary_entity="lesson_session") == "Lesson Session Workspace"


def test_natural_app_name_never_returns_awkward_examples() -> None:
    awkward = {"Dashboard Magician", "I Want Manage My", "Dashboard Coaching Nutrition", "Want Manage Personal Finances"}
    for prompt in [
        "dashboard for musician",
        "i want to manage my personal finances",
        "dashboard for coaching nutrition",
        "i want to track clients",
    ]:
        assert natural_app_name(prompt) not in awkward


def test_clean_prompt_strips_common_prefixes() -> None:
    assert clean_prompt("I want to manage my personal finances") == "personal finances"
    assert clean_prompt("Dashboard for musician") == "musician"
    assert clean_prompt("track my running") == "running"
    assert clean_prompt("i am a basketball coach") == "basketball coach"
    assert clean_prompt("") == ""


def test_natural_pack_slug_is_kebab_case_and_natural() -> None:
    assert natural_pack_slug("dashboard for musician") == "musician-dashboard"
    assert natural_pack_slug("i want to manage my personal finances") == "personal-finance-manager"


def test_domain_summary_includes_subject() -> None:
    summary = domain_summary("dashboard for musician", primary_entity_label="Musicians")
    assert "musician" in summary.lower()
    assert summary.endswith(".")


def test_domain_summary_handles_empty_input() -> None:
    summary = domain_summary("", primary_entity_label="Tickets")
    assert "tickets" in summary.lower()


def test_section_heading_titleizes() -> None:
    assert section_heading("court vendors") == "Court Vendors"
    assert section_heading("HR Tasks") == "HR Tasks"


def test_empty_state_helpers_are_domain_aware() -> None:
    assert empty_state_list("Musician", "Musicians") == "No musicians yet — load seed data or create your first musician."
    assert empty_state_related("Performances", parent_singular="Musician") == "No performances yet — add one after you create a musician."
    assert "lane" in empty_state_lane("Lesson Session").lower()


def test_empty_state_helpers_have_fallbacks() -> None:
    assert empty_state_list("", "") == "No records yet — load seed data or create your first record."
    assert empty_state_related("") == "No records yet — they'll appear here once you add some."
