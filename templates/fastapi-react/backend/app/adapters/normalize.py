from dataclasses import dataclass

from app.providers.interface import RawRecord


@dataclass
class NormalizedRecordDTO:
    external_id: str
    source: str
    title: str
    category: str
    value: float
    raw_payload: dict


def normalize(raw: RawRecord) -> NormalizedRecordDTO:
    """Convert a RawRecord from any provider into the stable NormalizedRecordDTO."""
    return NormalizedRecordDTO(
        external_id=raw.external_id,
        source=raw.source,
        title=raw.title.strip(),
        category=raw.category.lower().strip(),
        value=max(0.0, min(100.0, float(raw.value))),  # clamp to [0, 100]
        raw_payload=raw.raw_payload,
    )
