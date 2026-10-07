"""Deterministic JSON and CSV renderers."""

import csv
import io
import json
from .models import FeedResult


_DANGEROUS_CSV_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _safe_csv_cell(value: str) -> str:
    """Prevent values from being interpreted as formulas by spreadsheet software."""

    encodable = value.encode("utf-8", errors="backslashreplace").decode("utf-8")
    if encodable.startswith(_DANGEROUS_CSV_PREFIXES):
        return "'" + encodable
    return encodable


def render_json(result: FeedResult) -> str:
    return json.dumps(result.to_dict(), ensure_ascii=True, indent=2, sort_keys=True) + "\n"


def render_csv(result: FeedResult) -> str:
    buffer = io.StringIO(newline="")
    fieldnames = (
        "status",
        "type",
        "value",
        "provenance",
        "input",
        "declared_type",
        "source",
        "location",
        "reason",
    )
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for indicator in result.indicators:
        provenance = json.dumps(
            [item.to_dict() for item in indicator.provenance],
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        writer.writerow(
            {
                "status": "accepted",
                "type": indicator.type,
                "value": _safe_csv_cell(indicator.value),
                "provenance": _safe_csv_cell(provenance),
                "input": "",
                "declared_type": "",
                "source": "",
                "location": "",
                "reason": "",
            }
        )
    for rejected in result.rejected:
        writer.writerow(
            {
                "status": "rejected",
                "type": "",
                "value": "",
                "provenance": "",
                "input": _safe_csv_cell(rejected.input),
                "declared_type": _safe_csv_cell(rejected.declared_type or ""),
                "source": _safe_csv_cell(rejected.source),
                "location": _safe_csv_cell(rejected.location),
                "reason": _safe_csv_cell(rejected.reason),
            }
        )
    return buffer.getvalue()
