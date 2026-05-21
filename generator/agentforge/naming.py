"""Deterministic naming + copy helpers for generated apps.

Used to transform raw user prompts ("dashboard for musician",
"i want to manage my personal finances") into natural app names
("Musician Dashboard", "Personal Finance Manager"), and to produce
domain-aware dashboard summaries, entity section copy, and empty
states. No live LLM, no network, no flaky output.

The helpers extract intent from common natural-language wrappers
("i want an app to ...", "assist me in my work as a ...", parenthetical
hints like "(houses + cash)") so prompts that talk *about* an app
still yield a tidy domain noun phrase like "Marketing Manager
Workspace" or "Asset Manager" instead of the verbatim wording.
"""
from __future__ import annotations

import re
from typing import Sequence

_ACRONYMS = {
    "hr": "HR",
    "ai": "AI",
    "crm": "CRM",
    "kpi": "KPI",
    "qa": "QA",
    "ux": "UX",
    "ui": "UI",
    "it": "IT",
    "ops": "Ops",
    "us": "US",
    "uk": "UK",
    "eu": "EU",
    "saas": "SaaS",
}

# Sentence-opener prefixes ("i want to ...", "i need an ...", etc).
_PREFIXES = (
    "i would like to ", "i would like a ", "i would like an ", "i would like ",
    "i want to ", "i want a ", "i want an ", "i want ",
    "i'd want to ", "i'd want a ", "i'd want an ",
    "i'd like to ", "i'd like a ", "i'd like an ",
    "i need to ", "i need a ", "i need an ", "i need ",
    "i am trying to ", "i'm trying to ",
    "we would like to ", "we would like a ", "we would like an ",
    "we want to ", "we want a ", "we want an ", "we want ",
    "we need to ", "we need a ", "we need an ", "we need ",
    "let me ", "help me ", "please ",
    "i am a ", "i am an ", "i'm a ", "i'm an ",
    "i am ", "i'm ",
    "build me a ", "build me an ", "build a ", "build an ",
    "make me a ", "make me an ", "make a ", "make an ",
    "create a ", "create an ", "create ",
    "give me a ", "give me an ",
)

_SECONDARY_PREFIXES = (
    "would like to ", "would like a ", "would like an ",
    "want to ", "want a ", "want an ",
    "need to ", "need a ", "need an ",
    "trying to ",
)

# Framings users wrap their domain in: "<vehicle> for X", "<vehicle> to X",
# or bare verb phrases like "track my X" / "control my X" /
# "assist me in my work as a X". Iteration applies the longest match first,
# so longer patterns ("assist me in my work as a ") win over shorter ones
# ("as a ").
_FRAME_PREFIXES = (
    # "<vehicle> for X"
    "dashboard for ", "dashboards for ",
    "app for ", "apps for ",
    "tool for ", "tools for ",
    "workspace for ", "workspaces for ",
    "tracker for ", "trackers for ",
    "manager for ",
    "system for ", "systems for ",
    "platform for ",
    "site for ", "website for ", "websites for ",
    "tracking for ",
    # bare verb framings (no "for")
    "tracking ",
    "track my ", "track ",
    "manage my ", "manage ", "managing ",
    "monitor my ", "monitor ", "monitoring ",
    "organize my ", "organize ", "organizing ",
    "handle my ", "handle ", "handling ",
    "oversee my ", "oversee ", "overseeing ",
    "automate my ", "automate ", "automating ",
    "run my ", "running my ",
    "control my ", "control ", "controlling ",
    # "<vehicle> to <verb> X" — strip vehicle first, then verb
    "website to ", "websites to ",
    "site to ",
    "app to ", "application to ", "apps to ",
    "tool to ", "tools to ",
    "dashboard to ", "dashboards to ",
    "system to ", "systems to ",
    "platform to ",
    "solution to ",
    "page to ",
    "thing to ",
    # "assist me ... as a X" → X
    "assist me in my work as a ", "assist me in my work as an ", "assist me in my work as ",
    "assist me in my role as a ", "assist me in my role as an ", "assist me in my role as ",
    "assist me in ", "assist me with ", "assist me ",
    "help me with ", "help me ",
    "help with ",
    # tiny follow-up clean-up after a longer prefix strips most of the
    # wrapper (e.g. "help me track my reading list" → "my reading list").
    "my ", "our ",
    # standalone "as a/an X" wrappers (e.g. "as a marketing manager")
    "for my work as a ", "for my work as an ", "for my work as ",
    "in my work as a ", "in my work as an ", "in my work as ",
    "for my role as a ", "for my role as an ",
    "in my role as a ", "in my role as an ",
    "as a ", "as an ",
)

_TRIM_AT = (
    ", and ",
    ", with ",
    ", using ",
    ", so ",
    ", to ",
    ", who ",
    ", that ",
    ", which ",
    " and i ",
    " so that ",
)

# Words that almost never carry domain meaning on their own. They become
# part of an app name only as a last resort. "Workspace" / "Tracker" are
# omitted on purpose — they're legitimate domain nouns when the user
# wrote them.
_SUBJECT_NOISE = {
    "dashboard",
    "dashboards",
    "app",
    "apps",
    "application",
    "applications",
    "tool",
    "tools",
    "workspace",
    "workspaces",
    "tracker",
    "trackers",
    "tracking",
    "coach",
    "coaching",
    "coaches",
    "management",
    "website",
    "websites",
    "site",
    "sites",
    "system",
    "systems",
    "platform",
    "platforms",
    "solution",
    "solutions",
    "thing",
    "things",
    "stuff",
    "page",
    "pages",
}

# Plain articles/connectives plus the filler verbs/pronouns that wrap
# natural-language prompts ("i want to ...", "help me ..."). Removing
# them at subject extraction protects against any wrapper phrase that
# slipped past the prefix strippers.
_STOP_WORDS = {
    "a", "an", "the", "my", "our", "for", "of", "to", "and", "or",
    "any", "some",
    "i", "me", "we", "us",
    "want", "need", "would", "like", "love",
    "build", "make", "create", "creating",
    "help", "assist", "assisting",
    "please",
    "as", "in",
    "do", "does", "doing",
}


def _sorted_prefixes() -> tuple[str, ...]:
    """Iteration order: longest prefix first so wrappers win over their tails."""
    return tuple(
        sorted(set((*_PREFIXES, *_SECONDARY_PREFIXES, *_FRAME_PREFIXES)), key=len, reverse=True)
    )


_ALL_PREFIXES_SORTED = _sorted_prefixes()


def clean_prompt(text: str) -> str:
    """Strip filler prefixes like "I want to" / "dashboard for".

    Idempotent and case-insensitive. Returns lowercase text with
    trailing punctuation, surrounding parenthetical hints, and known
    wrapper phrases removed. Used by ``natural_app_name`` and
    ``domain_summary``.
    """
    if not text:
        return ""
    cleaned = text.strip().lower()
    cleaned = re.sub(r"[!?.]+$", "", cleaned)
    # Parenthetical hints like "(houses + cash)" muddle the subject —
    # the domain noun lives outside the parens, so we drop them rather
    # than try to interpret them.
    cleaned = re.sub(r"\([^)]*\)", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    changed = True
    while changed:
        changed = False
        for prefix in _ALL_PREFIXES_SORTED:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].lstrip()
                changed = True
                break
    return cleaned.strip().rstrip(",")


def _trim_clauses(text: str) -> str:
    lower = text.lower()
    for marker in _TRIM_AT:
        i = lower.find(marker)
        if i >= 0:
            return text[:i].strip().rstrip(",")
    i = lower.find(",")
    if i >= 0:
        return text[:i].strip()
    return text.strip()


def _singularize(word: str) -> str:
    lower = word.lower()
    if len(lower) > 4 and lower.endswith("ies"):
        return word[:-3] + "y"
    if len(lower) > 3 and lower.endswith("ses"):
        return word
    if len(lower) > 3 and lower.endswith("s") and not lower.endswith("ss") and not lower.endswith("us"):
        return word[:-1]
    return word


def _titleize_word(word: str) -> str:
    lower = word.lower()
    if lower in _ACRONYMS:
        return _ACRONYMS[lower]
    return lower[:1].upper() + lower[1:]


def _titleize(text: str) -> str:
    parts = [p for p in re.split(r"\s+", text.strip()) if p]
    return " ".join(_titleize_word(part) for part in parts)


def _subject_words(cleaned: str) -> list[str]:
    raw = [token for token in re.findall(r"[a-z0-9']+", cleaned)]
    keep = [token for token in raw if token not in _STOP_WORDS and token not in _SUBJECT_NOISE]
    if keep:
        return keep
    fallback = [token for token in raw if token not in _STOP_WORDS]
    return fallback or raw


def _detect_suffix(text: str, subject: str) -> str:
    compact = text.lower()
    has_coach = "coach" in compact or "coaching" in compact
    subject_lower = subject.lower()
    if has_coach:
        return "Coaching Dashboard"
    if "dashboard" in compact:
        return "Dashboard"
    if (
        "tracker" in compact
        or "tracking" in compact
        or " track " in f" {compact} "
        or "monitor" in compact
    ):
        return "Tracker"
    if "workspace" in compact:
        return "Workspace"
    manage_signals = (
        "manage" in compact
        or "manager" in compact
        or "managing" in compact
        or "control" in compact
        or "controlling" in compact
    )
    if manage_signals and "manager" not in subject_lower:
        return "Manager"
    return "Workspace"


# Entity-token clusters that map to a single umbrella label. Used as a
# fallback when the prompt itself does not yield a subject (e.g. an
# empty idea seed) but the blueprint has entities to lean on.
_ENTITY_UMBRELLAS: tuple[tuple[set[str], str, str], ...] = (
    (
        {"asset", "house", "houses", "property", "properties", "real_estate", "realestate",
         "cash", "investment", "investments", "stock", "stocks", "portfolio", "holding", "holdings"},
        "Asset",
        "Manager",
    ),
    (
        {"marketing", "campaign", "campaigns", "audience", "audiences",
         "channel", "channels"},
        "Marketing",
        "Workspace",
    ),
)


def _entity_tokens(entities: Sequence[str]) -> list[str]:
    tokens: list[str] = []
    for name in entities:
        if not name:
            continue
        readable = re.sub(r"[_\-]+", " ", str(name)).strip()
        if readable:
            tokens.append(readable)
    return tokens


def _entity_umbrella_match(tokens: Sequence[str]) -> tuple[str, str] | None:
    flat = " ".join(token.lower() for token in tokens)
    flat_words = set(re.findall(r"[a-z0-9]+", flat))
    for terms, label, suffix in _ENTITY_UMBRELLAS:
        if flat_words & terms:
            return label, suffix
    return None


def _entity_app_name(entities: Sequence[str]) -> str:
    tokens = _entity_tokens(entities)
    if not tokens:
        return ""
    umbrella = _entity_umbrella_match(tokens)
    if umbrella:
        label, suffix = umbrella
        return f"{label} {suffix}"
    singular = [_titleize(_singularize(token)) for token in tokens]
    singular = [s for s in singular if s]
    if not singular:
        return ""
    if len(singular) == 1:
        return f"{singular[0]} Workspace"
    return f"{singular[0]} and {singular[1]} Workspace"


def natural_app_name(
    text: str,
    primary_entity: str | None = None,
    *,
    entities: Sequence[str] | None = None,
) -> str:
    """Return a natural-sounding app name for the raw prompt.

    Examples:
        "dashboard for musician" -> "Musician Dashboard"
        "i want to manage my personal finances" -> "Personal Finance Manager"
        "i want a website to control my assets (houses + cash)" -> "Asset Manager"
        "i need an app to assist me in my work as a marketing manager"
            -> "Marketing Manager Workspace"
        "dashboard for coaching nutrition" -> "Nutrition Coaching Dashboard"
        "hr manager dashboard" -> "HR Manager Dashboard"
        "i am a basketball coach, want to track clients and court vendors"
            -> "Basketball Coaching Dashboard"

    When the prompt cleans to nothing (empty or pure filler) and an
    ``entities`` list is supplied, the name is derived from the entities
    instead — common asset/marketing clusters collapse to a single
    umbrella label.
    """
    cleaned = clean_prompt(text)
    if cleaned:
        subject = _trim_clauses(cleaned)
        words = _subject_words(subject)
    else:
        words = []
    if words:
        suffix = _detect_suffix(text, " ".join(words))
        if suffix in {"Manager", "Tracker", "Coaching Dashboard", "Dashboard"}:
            words = [*words[:-1], _singularize(words[-1])]
        titled = _titleize(" ".join(words))
        if titled:
            return f"{titled} {suffix}".strip()
        return suffix
    if entities:
        derived = _entity_app_name(entities)
        if derived:
            return derived
    if primary_entity:
        return _titleize(primary_entity.replace("_", " ")) + " Workspace"
    return "AgentForge App"


def natural_pack_slug(
    text: str,
    primary_entity: str | None = None,
    *,
    entities: Sequence[str] | None = None,
) -> str:
    """Return a kebab-case filesystem name derived from the natural app name."""
    name = natural_app_name(text, primary_entity=primary_entity, entities=entities)
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or (primary_entity or "agentforge-app").replace("_", "-")


def domain_summary(text: str, primary_entity_label: str | None = None) -> str:
    """One-line domain-specific summary for the dashboard hero."""
    cleaned = clean_prompt(text)
    primary_label = (primary_entity_label or "").strip()
    if not cleaned and primary_label:
        return f"Manage {primary_label.lower()} from one local workspace."
    if not cleaned:
        return "Local AgentForge app for managing records and workflows."
    subject = _trim_clauses(cleaned)
    subject = re.sub(r"\s+", " ", subject).strip().rstrip(".")
    if not subject:
        if primary_label:
            return f"Manage {primary_label.lower()} from one local workspace."
        return "Local AgentForge app for managing records and workflows."
    if primary_label:
        return f"Track {primary_label.lower()} and related records — {subject}."
    return f"Local workspace for {subject}."


def section_heading(label_plural: str) -> str:
    """Return a friendly section heading for an entity list.

    Used instead of generic 'X Register' / 'X List' patterns.
    """
    if not label_plural:
        return "Records"
    return _titleize(label_plural)


def empty_state_list(label_singular: str, label_plural: str) -> str:
    """Empty-state copy for the primary list of an entity."""
    singular = (label_singular or "record").strip().lower()
    plural = (label_plural or f"{singular}s").strip().lower()
    return f"No {plural} yet — load seed data or create your first {singular}."


def empty_state_related(label_plural: str, parent_singular: str | None = None) -> str:
    """Empty-state copy for a related/secondary entity panel."""
    plural = (label_plural or "records").strip().lower()
    if parent_singular:
        return f"No {plural} yet — add one after you create a {parent_singular.strip().lower()}."
    return f"No {plural} yet — they'll appear here once you add some."


def empty_state_lane(label_singular: str) -> str:
    singular = (label_singular or "record").strip().lower()
    return f"No {singular}s in this lane yet."


__all__ = [
    "clean_prompt",
    "natural_app_name",
    "natural_pack_slug",
    "domain_summary",
    "section_heading",
    "empty_state_list",
    "empty_state_related",
    "empty_state_lane",
]
