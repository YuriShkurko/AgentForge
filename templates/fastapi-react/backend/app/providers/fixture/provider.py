from app.providers.fixture.records import FIXTURE_RECORDS
from app.providers.interface import RawRecord, RecordProvider


class FixtureRecordProvider(RecordProvider):
    """
    Deterministic fixture provider. Returns the same records on every call.
    Used in CI, local dev, and generator tests — no external dependency.
    """

    @property
    def name(self) -> str:
        return "fixture"

    def fetch(self) -> list[RawRecord]:
        return [
            RawRecord(
                external_id=r["external_id"],
                source="fixture",
                title=r["title"],
                category=r["category"],
                value=r["value"],
                raw_payload=r,
            )
            for r in FIXTURE_RECORDS
        ]
