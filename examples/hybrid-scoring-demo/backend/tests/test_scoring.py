from app.adapters.normalize import NormalizedRecordDTO
from app.adapters.scoring import score


def _dto(value=75.0, category="opportunity"):
    return NormalizedRecordDTO(
        external_id="test-1",
        source="fixture",
        title="Test Record",
        category=category,
        value=value,
        raw_payload={},
    )


def test_high_score():
    s = score(_dto(value=88.0))
    assert s.fit == 0.88
    assert s.label == "high"
    assert s.recommendation == "accept"


def test_medium_score():
    s = score(_dto(value=54.0))
    assert s.fit == 0.54
    assert s.label == "medium"
    assert s.recommendation == "review"


def test_low_score():
    s = score(_dto(value=22.0))
    assert s.fit == 0.22
    assert s.label == "low"
    assert s.recommendation == "skip"


def test_boundary_70_is_high():
    s = score(_dto(value=70.0))
    assert s.label == "high"


def test_boundary_40_is_medium():
    s = score(_dto(value=40.0))
    assert s.label == "medium"


def test_boundary_just_below_40_is_low():
    s = score(_dto(value=39.0))
    assert s.label == "low"


def test_explanation_has_required_fields():
    s = score(_dto())
    assert s.explanation.fit_score == s.fit
    assert isinstance(s.explanation.summary, str)
    assert isinstance(s.explanation.drivers, list)
    assert isinstance(s.explanation.risks, list)
    assert len(s.explanation.drivers) > 0


def test_score_is_deterministic():
    dto = _dto(value=76.0)
    assert score(dto).fit == score(dto).fit
    assert score(dto).label == score(dto).label


def test_low_score_adds_risk_note():
    s = score(_dto(value=20.0))
    assert any("low fit" in r for r in s.explanation.risks)
