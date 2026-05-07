from app.providers.fixture.provider import FixtureRecordProvider


def test_provider_name():
    assert FixtureRecordProvider().name == "fixture"


def test_provider_returns_records():
    records = FixtureRecordProvider().fetch()
    assert len(records) > 0


def test_provider_is_deterministic():
    p = FixtureRecordProvider()
    assert p.fetch() == p.fetch()


def test_provider_records_have_required_fields():
    for r in FixtureRecordProvider().fetch():
        assert r.external_id
        assert r.source == "fixture"
        assert r.title
        assert r.category
        assert isinstance(r.value, float)
        assert isinstance(r.raw_payload, dict)


def test_provider_external_ids_are_unique():
    records = FixtureRecordProvider().fetch()
    ids = [r.external_id for r in records]
    assert len(ids) == len(set(ids))
