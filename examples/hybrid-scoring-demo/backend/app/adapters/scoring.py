from dataclasses import dataclass

from app.adapters.normalize import NormalizedRecordDTO

_CATEGORY_DRIVERS = {
    "opportunity": ["category is opportunity (high potential)", "value signal present"],
    "lead":        ["category is lead (actionable)", "title indicates follow-up needed"],
    "signal":      ["category is signal (informational)", "value within observable range"],
}

_CATEGORY_RISKS = {
    "opportunity": ["opportunity may be time-sensitive"],
    "lead":        ["lead quality unverified"],
    "signal":      ["signal may be noisy or incomplete"],
}


@dataclass
class ExplanationDTO:
    fit_score: float
    summary: str
    drivers: list[str]
    risks: list[str]


@dataclass
class ScoredRecordDTO:
    fit: float
    label: str         # high / medium / low
    recommendation: str  # accept / review / skip
    explanation: ExplanationDTO


def score(record: NormalizedRecordDTO) -> ScoredRecordDTO:
    """
    Deterministic scoring. fit = value / 100.
    All logic is heuristic — no LLM or external call.
    """
    fit = round(record.value / 100.0, 4)

    if fit >= 0.70:
        label = "high"
        recommendation = "accept"
    elif fit >= 0.40:
        label = "medium"
        recommendation = "review"
    else:
        label = "low"
        recommendation = "skip"

    category = record.category
    drivers = list(_CATEGORY_DRIVERS.get(category, ["value within range"]))
    risks = list(_CATEGORY_RISKS.get(category, ["category unknown"]))

    if fit < 0.40:
        risks.append("low fit score — verify before acting")

    summary = (
        f"{record.title} scores {label} ({fit:.0%} fit). "
        f"Recommendation: {recommendation}."
    )

    return ScoredRecordDTO(
        fit=fit,
        label=label,
        recommendation=recommendation,
        explanation=ExplanationDTO(
            fit_score=fit,
            summary=summary,
            drivers=drivers,
            risks=risks,
        ),
    )
