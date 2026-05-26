"""Deterministic scoring of AgentForge recipes against an `IntentSpec`.

This module is the planner's choice-maker: given an `IntentSpec`, it ranks the
recipe registry and returns a structured `RecipeSelection` describing the top
pick, the candidates considered, the per-recipe scoring rationale, and a
clarity verdict (`confident` / `ambiguous` / `fallback`).

It contains no I/O, no network, no LLM, and no mutation. Weights are
constants; thresholds are constants. Adding a new recipe is a data change in
`agentforge.recipes`; this module needs no edits.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from agentforge.app_intent import IntentSpec
from agentforge.recipes import ALL_RECIPES, FALLBACK_RECIPE, AppRecipe


# Scoring weights. Tuned so role hints + strong keywords + workflow tags
# dominate; loose keywords nudge ties.
_WEIGHT_KEYWORD = 1
_WEIGHT_STRONG_KEYWORD = 3
_WEIGHT_ROLE_HINT = 5
_WEIGHT_ENTITY_TAG = 2
_WEIGHT_WORKFLOW_TAG = 4
_WEIGHT_PROVIDER_TAG = 2
_WEIGHT_DOMAIN = 4
_WEIGHT_ANTI = -2

# Selection thresholds. A clear winner above the confident threshold means the
# planner can draft directly; otherwise return 2-4 candidates. Below the
# fallback threshold, return the generic_dashboard fallback with a hint.
CONFIDENT_THRESHOLD = 8
AMBIGUOUS_DELTA = 4
FALLBACK_THRESHOLD = 3
MAX_AMBIGUOUS_CANDIDATES = 4


@dataclass(frozen=True)
class RecipeScore:
    """One recipe's score against an `IntentSpec`, with per-signal evidence."""

    recipe: AppRecipe
    score: int
    reasons: tuple[str, ...]

    @property
    def recipe_id(self) -> str:
        return self.recipe.id


@dataclass(frozen=True)
class RecipeSelection:
    """The planner's verdict for an `IntentSpec`.

    - `picked` is the top-scoring recipe (never None: falls back to
      `generic_dashboard` if no recipe clears the fallback threshold).
    - `candidates` is the ordered (descending score) list of `RecipeScore`s
      worth showing to the user when `verdict == "ambiguous"`. For a confident
      pick or fallback, `candidates` contains only the picked recipe.
    - `verdict` is one of `confident` | `ambiguous` | `fallback`.
    - `all_scores` is every recipe's score (descending) for debugging/tests.
    """

    picked: AppRecipe
    candidates: tuple[RecipeScore, ...]
    verdict: str
    all_scores: tuple[RecipeScore, ...] = field(default_factory=tuple)

    @property
    def picked_score(self) -> RecipeScore:
        return self.candidates[0]


def select_recipe(intent: IntentSpec) -> RecipeSelection:
    """Score every recipe against `intent` and decide what to show the user."""
    scored = tuple(
        sorted(
            (_score_recipe(intent, recipe) for recipe in ALL_RECIPES),
            key=lambda s: (-s.score, s.recipe.id),
        )
    )

    non_fallback = tuple(s for s in scored if not s.recipe.is_fallback)
    top = non_fallback[0] if non_fallback else scored[0]

    if not non_fallback or top.score < FALLBACK_THRESHOLD:
        fallback_score = next(
            (s for s in scored if s.recipe.id == FALLBACK_RECIPE.id),
            RecipeScore(FALLBACK_RECIPE, 0, ("no recipe cleared FALLBACK_THRESHOLD",)),
        )
        return RecipeSelection(
            picked=FALLBACK_RECIPE,
            candidates=(fallback_score,),
            verdict="fallback",
            all_scores=scored,
        )

    if top.score >= CONFIDENT_THRESHOLD:
        second = non_fallback[1] if len(non_fallback) > 1 else None
        if second is None or (top.score - second.score) >= AMBIGUOUS_DELTA:
            return RecipeSelection(
                picked=top.recipe,
                candidates=(top,),
                verdict="confident",
                all_scores=scored,
            )

    candidates = tuple(
        s for s in non_fallback
        if s.score >= FALLBACK_THRESHOLD
        and (top.score - s.score) <= AMBIGUOUS_DELTA
    )[:MAX_AMBIGUOUS_CANDIDATES]
    if len(candidates) < 2:
        candidates = non_fallback[:2]

    return RecipeSelection(
        picked=top.recipe,
        candidates=candidates,
        verdict="ambiguous",
        all_scores=scored,
    )


def _score_recipe(intent: IntentSpec, recipe: AppRecipe) -> RecipeScore:
    text = intent.normalized
    reasons: list[str] = []
    score = 0

    signals = recipe.selection_signals

    for hint in signals.role_hints:
        if hint in text:
            score += _WEIGHT_ROLE_HINT
            reasons.append(f"role_hint('{hint}') +{_WEIGHT_ROLE_HINT}")

    for kw in signals.strong_keywords:
        if _phrase_present(text, kw):
            score += _WEIGHT_STRONG_KEYWORD
            reasons.append(f"strong_keyword('{kw}') +{_WEIGHT_STRONG_KEYWORD}")

    for kw in signals.keywords:
        if _word_present(text, kw):
            score += _WEIGHT_KEYWORD
            reasons.append(f"keyword('{kw}') +{_WEIGHT_KEYWORD}")

    for tag in signals.workflow_tags:
        if tag in intent.workflow_hints:
            score += _WEIGHT_WORKFLOW_TAG
            reasons.append(f"workflow_tag('{tag}') +{_WEIGHT_WORKFLOW_TAG}")

    for tag in signals.provider_tags:
        if tag in intent.provider_hints:
            score += _WEIGHT_PROVIDER_TAG
            reasons.append(f"provider_tag('{tag}') +{_WEIGHT_PROVIDER_TAG}")

    for entity in signals.entity_tags:
        if entity in intent.candidate_entities:
            score += _WEIGHT_ENTITY_TAG
            reasons.append(f"entity_tag('{entity}') +{_WEIGHT_ENTITY_TAG}")

    if signals.domains and intent.domain in signals.domains:
        score += _WEIGHT_DOMAIN
        reasons.append(f"domain('{intent.domain}') +{_WEIGHT_DOMAIN}")

    for anti in signals.anti_signals:
        if _phrase_present(text, anti):
            score += _WEIGHT_ANTI
            reasons.append(f"anti_signal('{anti}') {_WEIGHT_ANTI}")

    return RecipeScore(recipe=recipe, score=score, reasons=tuple(reasons))


def _word_present(text: str, word: str) -> bool:
    """Word-bounded match with naive plural fallback (`client` matches `clients`)."""
    if " " in word:
        return word in text
    return re.search(rf"\b{re.escape(word)}s?\b", text) is not None


def _phrase_present(text: str, phrase: str) -> bool:
    """Phrase substring match. Used for multi-word strong keywords and role hints."""
    return phrase in text


__all__ = [
    "AMBIGUOUS_DELTA",
    "CONFIDENT_THRESHOLD",
    "FALLBACK_THRESHOLD",
    "MAX_AMBIGUOUS_CANDIDATES",
    "RecipeScore",
    "RecipeSelection",
    "select_recipe",
]
