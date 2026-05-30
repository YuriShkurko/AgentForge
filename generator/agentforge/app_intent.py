"""Deterministic intent extraction for AgentForge prompts.

This module is the single deterministic seam between a raw user prompt and the
recipe-aware planning pipeline. It produces an `IntentSpec` describing what the
planner has inferred about the user, the domain, the job-to-be-done, the
candidate entities, the likely workflow shape, and any data/import/provider
hints. It is pure data, never calls a network or LLM, and is fully testable.

`IntentSpec` is the contract consumed by `agentforge.recipe_select` (which
scores recipes against the intent) and by `agentforge.app_shape` (which compiles
the chosen recipe into a deterministic `AppShape`). Existing keyword logic
scattered across `naming.py`, `planner/scripted.py`, and `planner/assistant.py`
is intentionally left in place for this first slice; future slices may
consolidate callers onto this module.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Mapping


_ROLE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bi(?:'m| am) (?:a |an )?([a-z][a-z \-]{2,40}?)(?:[,.]|$| who | that | which | and )"), "{0}"),
    (re.compile(r"\bi (?:run|own|manage|lead|operate) (?:a |an |my |the )?([a-z][a-z \-]{2,40}?)(?:[,.]|$| and | that | who )"), "operator of {0}"),
    (re.compile(r"\bas (?:a |an )?([a-z][a-z \-]{2,40}?)(?:[,.]|$| who | that )"), "{0}"),
    (re.compile(r"\bfor (?:a |an )?([a-z][a-z \-]{2,40}?)(?:[,.]|$| who | that )"), "{0}"),
)

# Domain buckets keyed by distinctive terms. Order matters: first match wins.
_DOMAIN_TERMS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("sports_coaching", ("coach", "trainer", "tutor", "instructor", "therapist", "lesson", "training session")),
    ("compliance", ("vendor risk", "compliance", "audit", "finding", "approval", "review queue", "policy", "regulatory")),
    ("sales_crm", ("crm", "sales pipeline", "leads", "deals", "opportunities", "prospects", "accounts")),
    ("hiring_recruiting", ("hiring", "recruiting", "candidate", "applicant", "interview", "job application", "ats")),
    ("engineering_ops", ("bug", "ticket", "issue tracker", "github issue", "incident", "on-call", "sre")),
    ("marketing_ops", ("marketing", "campaign", "content calendar", "editorial", "social post", "newsletter")),
    ("finance", ("invoice", "payment", "expense", "income", "budget", "cash", "ledger", "receipt", "billing")),
    ("agriculture", ("farm", "livestock", "crop", "cattle", "harvest", "barn", "field")),
    ("retail_inventory", ("inventory", "stock", "warehouse", "sku", "reorder", "supply", "supplies", "equipment", "asset", "assets", "maintenance")),
    ("healthcare", ("patient", "clinic", "appointment slot", "medical record", "prescription", "doctor")),
    ("education", ("student", "classroom", "course", "assignment", "syllabus", "grade")),
    ("operations", ("checklist", "sop", "shift handover", "daily routine", "opening procedure", "operations")),
    ("repair_services", ("repair shop", "repair", "workshop", "garage", "service order", "parts")),
    ("personal_finance", ("personal finance", "household", "my assets", "my cash", "my budget", "my expenses")),
    ("real_estate", ("property", "tenant", "lease", "rental", "house listing")),
    ("intake_onboarding", ("intake workflow", "onboarding", "new client intake", "submission", "intake form")),
)

# Common entity nouns we look for explicitly. Match singular or plural.
_ENTITY_NOUNS: tuple[str, ...] = (
    "client", "lesson", "session", "appointment", "payment", "invoice", "vendor",
    "finding", "approval", "review", "submission", "intake", "request",
    "lead", "deal", "opportunity", "candidate", "application", "applicant",
    "ticket", "bug", "issue", "incident", "case",
    "campaign", "post", "channel", "article",
    "account", "transaction", "expense", "budget", "category",
    "livestock", "animal", "crop", "feed", "asset", "item", "part",
    "equipment", "stock", "supply", "property", "house", "cash", "maintenance", "location",
    "patient", "student", "course", "assignment",
    "task", "job", "checklist", "run", "shift",
    "contact", "organization", "interaction",
    "stage", "card", "column", "board",
    "source", "import", "provider", "sync",
    "form", "stage", "queue",
    "owner", "assignee", "reviewer", "customer",
)

# Provider/source hints that map to existing AgentForge providers or known
# import patterns. Used to populate `provider_hints` in the IntentSpec.
_PROVIDER_HINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("github_issues", ("github issue", "github issues", "github bug", "pull request", "github pr")),
    ("http_json", ("http endpoint", "json endpoint", "rest api", "third-party api")),
    ("csv_import", ("csv", "spreadsheet", "excel export")),
    ("manual", ("manual entry", "by hand", "type in")),
)

# Workflow-type tags. These are coarse hints used by the recipe scorer; they do
# not need to map 1:1 onto recipe ids.
_WORKFLOW_HINTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("session_tracking", ("schedule", "book", "appointment", "lesson", "session")),
    ("kanban_pipeline", ("pipeline", "kanban", "stage", "board", "move card", "advance")),
    ("approval_queue", ("approve", "review queue", "claim", "reject", "escalate", "approval", "approval workflow", "to review", "need to review", "vendor risk", "risk finding")),
    ("inventory_tracking", ("stock", "reorder", "warehouse", "issue stock", "receive stock", "count", "inventory", "equipment", "asset", "assets", "maintenance", "supplies", "livestock", "feed")),
    ("calendar_planning", ("calendar", "schedule content", "editorial calendar", "weekly plan")),
    ("checklist_runs", ("checklist", "sop", "routine", "daily check")),
    ("case_timeline", ("case", "investigation", "incident timeline", "patient record")),
    ("finance_ledger", ("ledger", "transaction", "expense", "income", "balance")),
    ("contact_log", ("contact", "log call", "log interaction", "follow-up", "crm")),
    ("intake_pipeline", ("intake workflow", "onboarding flow", "new submission", "intake form")),
    ("provider_sync_triage", ("sync", "import", "pull from", "fetch from")),
    ("generic_crud", ("dashboard", "list", "track records", "manage records", "manage items")),
)

# Tokens that mark a prompt as too thin to act on without clarification.
_VAGUE_TOKENS: frozenset[str] = frozenset({
    "", "app", "an app", "a tool", "tool", "build app", "build me an app",
    "make an app", "build something", "i need an app",
})

_STOP_WORDS: frozenset[str] = frozenset({
    "a", "an", "the", "and", "or", "to", "for", "with", "of", "in", "on", "at",
    "from", "by", "is", "are", "be", "as", "that", "this", "these", "those",
    "my", "our", "their", "your", "his", "her",
})


@dataclass(frozen=True)
class IntentSpec:
    """Deterministic snapshot of what the planner has inferred from a prompt.

    All fields are derived from the raw prompt + optional caller-provided
    `entities` and `hints`. Nothing in this dataclass requires network or LLM
    access. Consumers should treat `IntentSpec` as the only input contract for
    recipe selection and AppShape compilation.
    """

    raw_prompt: str
    normalized: str
    target_user: str | None
    domain: str
    primary_jtbd: str | None
    candidate_entities: tuple[str, ...]
    workflow_hints: tuple[str, ...]
    provider_hints: tuple[str, ...]
    clarity: str  # "clear" | "ambiguous" | "vague"
    evidence: Mapping[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "raw_prompt": self.raw_prompt,
            "normalized": self.normalized,
            "target_user": self.target_user,
            "domain": self.domain,
            "primary_jtbd": self.primary_jtbd,
            "candidate_entities": list(self.candidate_entities),
            "workflow_hints": list(self.workflow_hints),
            "provider_hints": list(self.provider_hints),
            "clarity": self.clarity,
            "evidence": dict(self.evidence),
        }


def extract_intent(
    prompt: str,
    *,
    entities: Iterable[str] | None = None,
    hints: Mapping[str, str] | None = None,
) -> IntentSpec:
    """Extract a deterministic `IntentSpec` from a free-form prompt.

    `entities` lets callers pre-seed candidate entities (e.g., from a Builder
    form). `hints` lets callers pass already-answered clarifying questions; the
    extractor concatenates their values into the text it scans.
    """
    raw = (prompt or "").strip()
    normalized = _normalize(raw)
    text_for_scan = " ".join(
        part for part in [normalized, *(str(v).lower() for v in (hints or {}).values())] if part
    )

    evidence: dict[str, str] = {}

    clarity = _classify_clarity(normalized)
    target_user, role_phrase = _extract_role(text_for_scan)
    if role_phrase:
        evidence["target_user"] = role_phrase

    domain, domain_phrase = _bucket_domain(text_for_scan)
    if domain_phrase:
        evidence["domain"] = domain_phrase

    candidate_entities = _extract_entities(text_for_scan, entities)
    if candidate_entities:
        evidence["candidate_entities"] = ", ".join(candidate_entities)

    workflow_hints = _match_table(text_for_scan, _WORKFLOW_HINTS)
    if workflow_hints:
        evidence["workflow_hints"] = ", ".join(workflow_hints)

    provider_hints = _match_table(text_for_scan, _PROVIDER_HINTS)
    if provider_hints:
        evidence["provider_hints"] = ", ".join(provider_hints)

    primary_jtbd = _derive_jtbd(text_for_scan, candidate_entities, workflow_hints)
    if primary_jtbd:
        evidence["primary_jtbd"] = primary_jtbd

    return IntentSpec(
        raw_prompt=raw,
        normalized=normalized,
        target_user=target_user,
        domain=domain,
        primary_jtbd=primary_jtbd,
        candidate_entities=candidate_entities,
        workflow_hints=workflow_hints,
        provider_hints=provider_hints,
        clarity=clarity,
        evidence=evidence,
    )


def _normalize(prompt: str) -> str:
    text = prompt.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def _classify_clarity(normalized: str) -> str:
    if not normalized or normalized in _VAGUE_TOKENS:
        return "vague"
    word_count = len([w for w in normalized.split() if w not in _STOP_WORDS])
    if word_count <= 2:
        return "vague"
    if word_count <= 5 and not any(noun in normalized for noun in _ENTITY_NOUNS):
        return "ambiguous"
    return "clear"


def _extract_role(text: str) -> tuple[str | None, str | None]:
    for pattern, template in _ROLE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        phrase = match.group(1).strip().rstrip(".,;:")
        # Drop trailing connectors picked up by the loose pattern.
        phrase = re.sub(r"\b(?:and|with|that|who)\b.*$", "", phrase).strip()
        if not phrase or len(phrase) < 3:
            continue
        return template.format(phrase), match.group(0).strip()
    return None, None


def _bucket_domain(text: str) -> tuple[str, str | None]:
    for bucket, terms in _DOMAIN_TERMS:
        for term in terms:
            if term in text:
                return bucket, term
    return "unknown", None


def _extract_entities(text: str, pre_seeded: Iterable[str] | None) -> tuple[str, ...]:
    found: list[str] = []
    seen: set[str] = set()
    for noun in _ENTITY_NOUNS:
        if _word_in(text, noun) or _word_in(text, noun + "s"):
            singular = noun
            if singular not in seen:
                seen.add(singular)
                found.append(singular)
    for extra in pre_seeded or ():
        canonical = str(extra).strip().lower().rstrip("s")
        if canonical and canonical not in seen:
            seen.add(canonical)
            found.append(canonical)
    return tuple(found)


def _match_table(text: str, table: tuple[tuple[str, tuple[str, ...]], ...]) -> tuple[str, ...]:
    matched: list[str] = []
    for tag, terms in table:
        if any(_term_present(text, term) for term in terms):
            matched.append(tag)
    return tuple(matched)


def _term_present(text: str, term: str) -> bool:
    """Phrase substring for multi-word terms, word-bounded with plural for single words."""
    if " " in term or "-" in term:
        return term in text
    return re.search(rf"\b{re.escape(term)}s?\b", text) is not None


def _derive_jtbd(
    text: str,
    entities: tuple[str, ...],
    workflow_hints: tuple[str, ...],
) -> str | None:
    if not text:
        return None
    verb_match = re.search(
        r"\b(track|manage|review|approve|schedule|book|sync|monitor|run|plan|tracking|managing)\b\s+(?:the |my |our |all |new |incoming )?([a-z][a-z \-]{2,40})",
        text,
    )
    if verb_match:
        verb = verb_match.group(1).rstrip("ing")
        tail = verb_match.group(2).strip().rstrip(".,;:")
        tail = re.sub(r"\b(?:and|with|that|who|from|in|on)\b.*$", "", tail).strip()
        if tail:
            return f"{verb} {tail}"
    if entities:
        return f"manage {entities[0]}s"
    if workflow_hints:
        return f"support {workflow_hints[0].replace('_', ' ')}"
    return None


def _word_in(text: str, word: str) -> bool:
    return re.search(rf"\b{re.escape(word)}\b", text) is not None


__all__ = ["IntentSpec", "extract_intent"]
