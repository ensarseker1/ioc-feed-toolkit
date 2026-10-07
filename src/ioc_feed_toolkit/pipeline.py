"""Aggregation, provenance tracking, and deterministic deduplication."""

from collections import defaultdict
from dataclasses import dataclass
import json
from typing import DefaultDict, Iterable, List, Optional, Set, Tuple

from .models import FeedResult, Indicator, Provenance, RejectedIndicator
from .normalize import IndicatorValidationError, normalize_indicator


@dataclass(frozen=True)
class InputRecord:
    """One raw observation produced by an input reader."""

    value: object
    source: str
    location: str
    declared_type: Optional[str] = None


def display_input(value: object) -> str:
    if isinstance(value, str):
        return value.encode("utf-8", errors="backslashreplace").decode("utf-8")
    try:
        return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError, RecursionError):
        return repr(value)


class FeedProcessor:
    """Collect records into a deterministic :class:`FeedResult`."""

    def __init__(self) -> None:
        self._accepted: DefaultDict[Tuple[str, str], Set[Provenance]] = defaultdict(set)
        self._rejected: List[RejectedIndicator] = []
        self._observations = 0

    def add(self, record: InputRecord) -> None:
        self._observations += 1
        original = display_input(record.value)
        if not isinstance(record.value, str):
            self.reject(record, "indicator must be a string")
            return
        try:
            indicator_type, normalized = normalize_indicator(record.value, record.declared_type)
        except IndicatorValidationError as error:
            self.reject(record, str(error))
            return
        provenance = Provenance(
            source=record.source,
            location=record.location,
            original=original,
        )
        self._accepted[(indicator_type, normalized)].add(provenance)

    def reject(self, record: InputRecord, reason: str) -> None:
        self._rejected.append(
            RejectedIndicator(
                input=display_input(record.value),
                source=record.source,
                location=record.location,
                reason=reason,
                declared_type=record.declared_type,
            )
        )

    def add_many(self, records: Iterable[InputRecord]) -> None:
        for record in records:
            self.add(record)

    def result(self) -> FeedResult:
        indicators = []
        for (indicator_type, value), provenance in sorted(self._accepted.items()):
            indicators.append(
                Indicator(
                    type=indicator_type,
                    value=value,
                    provenance=tuple(
                        sorted(provenance, key=lambda item: (item.source, item.location, item.original))
                    ),
                )
            )
        rejected = tuple(
            sorted(
                self._rejected,
                key=lambda item: (
                    item.source,
                    item.location,
                    item.input,
                    item.declared_type or "",
                    item.reason,
                ),
            )
        )
        return FeedResult(tuple(indicators), rejected, self._observations)
