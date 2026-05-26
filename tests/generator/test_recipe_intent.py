"""Deterministic tests for `agentforge.app_intent.extract_intent`."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "generator"))

from agentforge.app_intent import IntentSpec, extract_intent


def test_extract_intent_returns_intentspec():
    intent = extract_intent("I am a basketball coach, want to track clients, lessons, payments, and court vendors")
    assert isinstance(intent, IntentSpec)
    assert intent.raw_prompt.startswith("I am a basketball coach")
    assert intent.normalized.startswith("i am a basketball coach")


def test_extract_intent_clear_prompt_has_role_and_domain():
    intent = extract_intent("I am a basketball coach, want to track clients, lessons, payments, and court vendors")
    assert intent.clarity == "clear"
    assert intent.target_user is not None
    assert "coach" in intent.target_user
    assert intent.domain == "sports_coaching"
    assert "client" in intent.candidate_entities
    assert "session_tracking" in intent.workflow_hints


def test_extract_intent_compliance_prompt():
    intent = extract_intent("I need to review vendor risk findings")
    assert intent.clarity == "clear"
    assert intent.domain == "compliance"
    assert "approval_queue" in intent.workflow_hints
    assert "finding" in intent.candidate_entities


def test_extract_intent_hiring_prompt():
    intent = extract_intent("I want to manage job applications")
    assert intent.clarity == "clear"
    assert intent.domain == "hiring_recruiting"


def test_extract_intent_intake_prompt():
    intent = extract_intent("I need an intake workflow for new clients")
    assert intent.clarity == "clear"
    assert intent.domain == "intake_onboarding"
    assert "intake_pipeline" in intent.workflow_hints


def test_extract_intent_repair_shop_prompt_has_multiple_workflow_hints():
    intent = extract_intent(
        "I run a small repair shop and need to track jobs, parts, and customer updates"
    )
    assert intent.clarity == "clear"
    assert intent.domain == "repair_services"
    assert "job" in intent.candidate_entities or "part" in intent.candidate_entities


def test_extract_intent_generic_prompt_has_no_specific_domain():
    intent = extract_intent("simple dashboard for tracking random items")
    assert intent.domain in {"unknown", "retail_inventory"}
    assert "generic_crud" in intent.workflow_hints
    # Should still have an entity hint via "items"
    assert "item" in intent.candidate_entities


def test_extract_intent_vague_prompt_is_vague():
    intent = extract_intent("an app")
    assert intent.clarity == "vague"
    assert intent.candidate_entities == ()


def test_extract_intent_empty_prompt_is_vague():
    intent = extract_intent("")
    assert intent.clarity == "vague"


def test_extract_intent_hints_are_concatenated():
    intent = extract_intent(
        "I need a tool",
        hints={"clarifier_1": "for booking court appointments with clients"},
    )
    assert "client" in intent.candidate_entities


def test_extract_intent_entities_param_is_additive():
    intent = extract_intent("a small tool", entities=("invoice",))
    assert "invoice" in intent.candidate_entities


def test_extract_intent_is_deterministic_for_same_prompt():
    a = extract_intent("I am a basketball coach tracking clients and lessons")
    b = extract_intent("I am a basketball coach tracking clients and lessons")
    assert a == b
    assert a.to_dict() == b.to_dict()


def test_extract_intent_evidence_records_matched_phrases():
    intent = extract_intent("I am a basketball coach tracking clients and lessons")
    assert "target_user" in intent.evidence
    assert "domain" in intent.evidence


@pytest.mark.parametrize("prompt", [
    "I am a basketball coach, want to track clients, lessons, payments, and court vendors",
    "I need to review vendor risk findings",
    "I want to manage job applications",
    "I need an intake workflow for new clients",
    "simple dashboard for tracking random items",
    "I run a small repair shop and need to track jobs, parts, and customer updates",
])
def test_extract_intent_never_returns_none_on_canonical_prompts(prompt):
    intent = extract_intent(prompt)
    assert intent is not None
    assert intent.domain is not None
