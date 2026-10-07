"""Data models used by the normalization pipeline."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class Provenance:
    """Where an accepted observation came from."""

    source: str
    location: str
    original: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "source": self.source,
            "location": self.location,
            "original": self.original,
        }


@dataclass(frozen=True)
class Indicator:
    """A unique normalized indicator plus all of its observed provenance."""

    type: str
    value: str
    provenance: Tuple[Provenance, ...]

    def to_dict(self) -> Dict[str, object]:
        return {
            "type": self.type,
            "value": self.value,
            "provenance": [item.to_dict() for item in self.provenance],
        }


@dataclass(frozen=True)
class RejectedIndicator:
    """An input observation that could not be normalized safely."""

    input: str
    source: str
    location: str
    reason: str
    declared_type: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        result: Dict[str, object] = {
            "input": self.input,
            "source": self.source,
            "location": self.location,
            "reason": self.reason,
        }
        if self.declared_type:
            result["declared_type"] = self.declared_type
        return result


@dataclass(frozen=True)
class FeedResult:
    """The complete deterministic output of a feed-processing run."""

    indicators: Tuple[Indicator, ...]
    rejected: Tuple[RejectedIndicator, ...]
    observations: int

    @property
    def duplicate_observations(self) -> int:
        accepted_observations = self.observations - len(self.rejected)
        return max(0, accepted_observations - len(self.indicators))

    def to_dict(self) -> Dict[str, object]:
        return {
            "summary": {
                "observations": self.observations,
                "unique_indicators": len(self.indicators),
                "duplicate_observations": self.duplicate_observations,
                "rejected": len(self.rejected),
            },
            "indicators": [item.to_dict() for item in self.indicators],
            "rejected": [item.to_dict() for item in self.rejected],
        }
