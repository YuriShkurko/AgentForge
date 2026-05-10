from app.models import NormalizedRecord, RecordScore

AVAILABLE_ACTIONS = ["accept", "skip", "save"]


def build_notification_payload(record: NormalizedRecord, score: RecordScore) -> dict:
    explanation = score.explanation or {}
    return {
        "record_id": str(record.id),
        "title": record.title,
        "score": score.fit,
        "label": score.label,
        "recommendation": score.recommendation,
        "summary": explanation.get("summary", ""),
        "drivers": explanation.get("drivers", []),
        "risks": explanation.get("risks", []),
        "available_actions": AVAILABLE_ACTIONS,
    }
