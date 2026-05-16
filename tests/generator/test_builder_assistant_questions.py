"""Guided-question polish tests for the Builder Assistant.

These tests cover the QUESTION_CATALOG, vague-prompt detection, and the
shape of question_details returned alongside the legacy questions[] list.
The polish is deterministic and scripted — no live LLM, no network.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "generator"))

from agentforge.planner.assistant import (
    QUESTION_CATALOG,
    BuilderAssistant,
    _is_vague,
    _missing_requirement_ids,
)


def test_question_catalog_entries_have_required_keys():
    for qid, entry in QUESTION_CATALOG.items():
        assert entry["id"] == qid
        assert isinstance(entry["prompt"], str) and entry["prompt"].strip()
        assert isinstance(entry["helper"], str)
        assert isinstance(entry["examples"], list)
        assert isinstance(entry["chips"], list)
        for chip in entry["chips"]:
            assert "label" in chip and chip["label"].strip()
            assert "value" in chip and chip["value"].strip()


@pytest.mark.parametrize(
    "idea",
    [
        "",
        "app",
        "build app",
        "build me an app",
        "make an app",
        "tool",
        "help",
        "I want to build something",
        "create a new app please",
        "make me a thing",
        "just want a tool",
    ],
)
def test_is_vague_recognises_low_signal_prompts(idea):
    assert _is_vague(idea) is True


@pytest.mark.parametrize(
    "idea",
    [
        "support tickets",
        "vendor risk register",
        "task tracker with status",
        "clients and onboarding tasks",
    ],
)
def test_is_vague_lets_real_ideas_through(idea):
    assert _is_vague(idea) is False


def test_missing_requirement_ids_routes_vague_input_to_idea_seed():
    assert _missing_requirement_ids("app") == ["idea_seed"]
    assert _missing_requirement_ids("help me build something") == ["idea_seed"]


def test_missing_requirement_ids_picks_focused_questions_for_partial_ideas():
    # Mentions an entity keyword but no field or workflow signals.
    ids = _missing_requirement_ids("support tickets")
    assert "idea_seed" not in ids
    assert "entities" not in ids
    assert ids == ["fields", "workflow"]


def test_start_with_vague_idea_returns_idea_seed_with_chips_and_examples():
    result = BuilderAssistant().start("app")

    assert result["question_details"], "guided questions must include structured details"
    seed = result["question_details"][0]
    assert seed["id"] == "idea_seed"
    assert len(seed["chips"]) >= 3
    assert len(seed["examples"]) >= 3
    # The legacy questions[] list mirrors the prompt for backward compatibility.
    assert result["questions"] == [seed["prompt"]]
    # State persists the pending IDs so the next turn can re-emit if needed.
    assert result["state"]["pending_question_ids"] == ["idea_seed"]


def test_start_with_partial_idea_returns_targeted_question_chips():
    result = BuilderAssistant().start("support tickets")

    assert result["status"] == "needs_clarification"
    ids = [entry["id"] for entry in result["question_details"]]
    assert ids == ["fields", "workflow"]
    fields_chip_values = {chip["value"] for chip in result["question_details"][0]["chips"]}
    assert {"status", "owner", "title"}.issubset(fields_chip_values)
    workflow_chip_values = {chip["value"] for chip in result["question_details"][1]["chips"]}
    assert any("close" in value for value in workflow_chip_values)


def test_full_idea_produces_proposal_with_empty_question_details():
    result = BuilderAssistant().start(
        "support ticket triage with title status priority owner notes to close tickets"
    )

    assert result["status"] == "proposed"
    assert result["question_details"] == []
    assert result["state"]["pending_question_ids"] == []


def test_message_empty_text_reflows_pending_question_details():
    first = BuilderAssistant().start("support tickets")
    pending = first["state"]["pending_question_ids"]
    assert pending == ["fields", "workflow"]

    result = BuilderAssistant().message(first["state"], "")

    assert result["status"] == "needs_clarification"
    assert [entry["id"] for entry in result["question_details"]] == pending


def test_state_round_trips_pending_question_ids_across_turns():
    first = BuilderAssistant().start("app")
    assert first["state"]["pending_question_ids"] == ["idea_seed"]

    # Client sends state back with pending_question_ids intact.
    second = BuilderAssistant().message(first["state"], "")
    assert second["state"]["pending_question_ids"] == ["idea_seed"]


def test_chips_never_contain_placeholder_or_dangerous_markup():
    forbidden = {"<", ">", "{{", "}}", "<script"}
    for entry in QUESTION_CATALOG.values():
        for chip in entry["chips"]:
            for substring in forbidden:
                assert substring not in chip["label"]
                assert substring not in chip["value"]
        for example in entry["examples"]:
            for substring in forbidden:
                assert substring not in example
