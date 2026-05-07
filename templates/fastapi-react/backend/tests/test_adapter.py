from app.adapters.normalize import normalize
from app.providers.interface import RawRecord


def _raw(external_id="test-1", title="Test", category="lead", value=75.0):
    return RawRecord(
        external_id=external_id,
        source="fixture",
        title=title,
        category=category,
        value=value,
        raw_payload={"external_id": external_id},
    )


def test_normalize_maps_fields():
    dto = normalize(_raw())
    assert dto.external_id == "test-1"
    assert dto.source == "fixture"
    assert dto.title == "Test"
    assert dto.category == "lead"
    assert dto.value == 75.0


def test_normalize_strips_title_whitespace():
    dto = normalize(_raw(title="  Padded Title  "))
    assert dto.title == "Padded Title"


def test_normalize_lowercases_category():
    dto = normalize(_raw(category="LEAD"))
    assert dto.category == "lead"


def test_normalize_clamps_value_max():
    dto = normalize(_raw(value=150.0))
    assert dto.value == 100.0


def test_normalize_clamps_value_min():
    dto = normalize(_raw(value=-10.0))
    assert dto.value == 0.0


def test_normalize_preserves_raw_payload():
    raw = _raw()
    dto = normalize(raw)
    assert dto.raw_payload == raw.raw_payload
