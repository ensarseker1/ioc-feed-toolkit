"""Parsers for plain-text, CSV, and JSON indicator inputs."""

import csv
import io
import json
from pathlib import Path
import sys
from typing import List, Optional, Sequence

from .pipeline import InputRecord


class InputReadError(ValueError):
    """Raised for structural input errors that prevent record extraction."""


_VALUE_COLUMNS = ("indicator", "value", "ioc", "observable")
_TYPE_COLUMNS = ("type", "indicator_type", "ioc_type")
_SOURCE_COLUMNS = ("source", "feed", "provider")
_EXTENSION_FORMATS = {".csv": "csv", ".json": "json", ".txt": "text"}


def _single_alias_column(
    fieldnames: Sequence[str], candidates: Sequence[str], label: str
) -> Optional[str]:
    candidate_set = set(candidates)
    matching = [name for name in fieldnames if name.strip().lower() in candidate_set]
    if len(matching) > 1:
        raise InputReadError(
            "CSV header has multiple {} columns: {}".format(label, ", ".join(matching))
        )
    return matching[0] if matching else None


def _record_from_json(value: object, source: str, location: str) -> InputRecord:
    if isinstance(value, str):
        return InputRecord(value=value, source=source, location=location)
    if not isinstance(value, dict):
        return InputRecord(value=value, source=source, location=location)

    indicator_value: object = None
    found = False
    for key in _VALUE_COLUMNS:
        if key in value:
            indicator_value = value[key]
            found = True
            break
    if not found:
        indicator_value = value

    declared_type = None
    for key in _TYPE_COLUMNS:
        if key in value and value[key] is not None:
            declared_type = str(value[key])
            break
    record_source = source
    for key in _SOURCE_COLUMNS:
        if key in value and value[key] is not None and str(value[key]).strip():
            record_source = str(value[key]).strip()
            break
    return InputRecord(
        value=indicator_value,
        source=record_source,
        location=location,
        declared_type=declared_type,
    )


def parse_text(text: str, source: str) -> List[InputRecord]:
    records: List[InputRecord] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        records.append(InputRecord(value=stripped, source=source, location="line {}".format(line_number)))
    return records


def parse_csv(text: str, source: str) -> List[InputRecord]:
    try:
        reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
        if not reader.fieldnames:
            raise InputReadError("CSV input has no header row")
        fieldnames = [name for name in reader.fieldnames if name is not None]
        normalized_fieldnames = [name.strip().lower() for name in fieldnames]
        if any(not name for name in normalized_fieldnames):
            raise InputReadError("CSV header contains an empty column name")
        if len(normalized_fieldnames) != len(set(normalized_fieldnames)):
            raise InputReadError("CSV header contains duplicate column names")
        value_column = _single_alias_column(fieldnames, _VALUE_COLUMNS, "indicator")
        if value_column is None:
            raise InputReadError(
                "CSV header must include one of: {}".format(", ".join(_VALUE_COLUMNS))
            )
        type_column = _single_alias_column(fieldnames, _TYPE_COLUMNS, "type")
        source_column = _single_alias_column(fieldnames, _SOURCE_COLUMNS, "source")

        records: List[InputRecord] = []
        for row in reader:
            if None in row and any(value not in (None, "") for value in row[None]):
                raise InputReadError(
                    "CSV row {} has more fields than the header".format(reader.line_num)
                )
            row_source = source
            if source_column and row.get(source_column) and str(row[source_column]).strip():
                row_source = str(row[source_column]).strip()
            declared_type = None
            if type_column and row.get(type_column) and str(row[type_column]).strip():
                declared_type = str(row[type_column]).strip()
            records.append(
                InputRecord(
                    value=row.get(value_column),
                    source=row_source,
                    location="row {}".format(reader.line_num),
                    declared_type=declared_type,
                )
            )
        return records
    except csv.Error as error:
        raise InputReadError("invalid CSV near line {}: {}".format(reader.line_num, error)) from None


def parse_json(text: str, source: str) -> List[InputRecord]:
    def reject_constant(value: str) -> object:
        raise InputReadError("invalid JSON numeric constant: {}".format(value))

    def reject_duplicate_keys(pairs: object) -> object:
        result = {}
        for key, value in pairs:  # type: ignore[misc]
            if key in result:
                raise InputReadError("JSON object contains duplicate key: {}".format(key))
            result[key] = value
        return result

    try:
        document = json.loads(
            text,
            parse_constant=reject_constant,
            object_pairs_hook=reject_duplicate_keys,
        )
    except json.JSONDecodeError as error:
        raise InputReadError(
            "invalid JSON at line {}, column {}: {}".format(error.lineno, error.colno, error.msg)
        ) from None
    except RecursionError:
        raise InputReadError("JSON nesting is too deep") from None

    container_source = source
    values: object = document
    location_prefix = "$"
    if isinstance(document, dict) and "indicators" in document:
        values = document["indicators"]
        location_prefix = "$.indicators"
        if document.get("source") is not None and str(document["source"]).strip():
            container_source = str(document["source"]).strip()

    if isinstance(values, list):
        return [
            _record_from_json(item, container_source, "{}[{}]".format(location_prefix, index))
            for index, item in enumerate(values)
        ]
    return [_record_from_json(values, container_source, location_prefix)]


def detect_format(path_label: str, text: str) -> str:
    if path_label != "-":
        detected = _EXTENSION_FORMATS.get(Path(path_label).suffix.lower())
        if detected:
            return detected
    stripped = text.lstrip()
    if stripped.startswith("[") or stripped.startswith("{"):
        return "json"
    first_line = stripped.splitlines()[0] if stripped else ""
    header_cells = {cell.strip().lower() for cell in first_line.split(",")}
    if header_cells.intersection(_VALUE_COLUMNS):
        return "csv"
    return "text"


def read_text(path_label: str, max_bytes: int) -> str:
    if max_bytes <= 0:
        raise InputReadError("max_bytes must be greater than zero")
    if path_label == "-":
        data = sys.stdin.buffer.read(max_bytes + 1)
    else:
        path = Path(path_label)
        try:
            if path.stat().st_size > max_bytes:
                raise InputReadError(
                    "{} exceeds the {} byte input limit".format(path_label, max_bytes)
                )
            data = path.read_bytes()
        except OSError as error:
            raise InputReadError("cannot read {}: {}".format(path_label, error)) from None
    if len(data) > max_bytes:
        raise InputReadError("{} exceeds the {} byte input limit".format(path_label, max_bytes))
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise InputReadError("{} is not valid UTF-8: {}".format(path_label, error)) from None


def read_records(
    path_label: str,
    input_format: str = "auto",
    source: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,
) -> List[InputRecord]:
    """Read one source into raw records without resolving or contacting indicators."""

    text = read_text(path_label, max_bytes=max_bytes)
    selected_format = detect_format(path_label, text) if input_format == "auto" else input_format
    record_source = source or ("stdin" if path_label == "-" else path_label)
    if selected_format == "text":
        return parse_text(text, record_source)
    if selected_format == "csv":
        return parse_csv(text, record_source)
    if selected_format == "json":
        return parse_json(text, record_source)
    raise InputReadError("unsupported input format: {}".format(selected_format))
