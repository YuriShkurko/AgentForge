from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class RawRecord:
    external_id: str
    source: str
    title: str
    category: str
    value: float
    raw_payload: dict


class RecordProvider(ABC):
    """Base interface for all record source providers."""

    @abstractmethod
    def fetch(self) -> list[RawRecord]:
        """Return raw records. Must be deterministic when using fixture data."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable provider identifier written to provider_runs.provider_name."""
        ...
