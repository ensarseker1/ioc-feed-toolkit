"""Command-line interface for IOC Feed Toolkit."""

import argparse
from pathlib import Path
import sys
import tempfile
from typing import Optional, Sequence

from . import __version__
from .output import render_csv, render_json
from .pipeline import FeedProcessor
from .readers import InputReadError, read_records


DEFAULT_MAX_BYTES = 10 * 1024 * 1024
DEFAULT_MAX_RECORDS = 100_000


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ioc-feed-toolkit",
        description="Normalize and deduplicate IOC files without network access.",
    )
    parser.add_argument("inputs", nargs="+", help="input paths; use - to read standard input")
    parser.add_argument(
        "--input-format",
        choices=("auto", "text", "csv", "json"),
        default="auto",
        help="input format for all inputs (default: infer from extension/content)",
    )
    parser.add_argument(
        "--output-format",
        choices=("json", "csv"),
        default="json",
        help="output format (default: json)",
    )
    parser.add_argument("-o", "--output", default="-", help="output path (default: stdout)")
    parser.add_argument(
        "--source",
        help="fallback provenance source label; record-level source fields take precedence",
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=DEFAULT_MAX_BYTES,
        help="maximum bytes per input (default: %(default)s)",
    )
    parser.add_argument(
        "--max-records",
        type=int,
        default=DEFAULT_MAX_RECORDS,
        help="maximum records across all inputs (default: %(default)s)",
    )
    parser.add_argument(
        "--fail-on-reject",
        action="store_true",
        help="exit with status 1 when any input record is rejected",
    )
    parser.add_argument("--quiet", action="store_true", help="suppress the stderr summary")
    parser.add_argument("--version", action="version", version="%(prog)s {}".format(__version__))
    return parser


def _write_output(path_label: str, content: str) -> None:
    if path_label == "-":
        sys.stdout.write(content)
        return
    destination = Path(path_label)
    try:
        destination_parent = destination.parent
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=str(destination_parent),
            prefix=".{}-".format(destination.name),
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
        temporary.replace(destination)
    except OSError as error:
        try:
            if "temporary" in locals() and temporary.exists():
                temporary.unlink()
        except OSError:
            pass
        raise InputReadError("cannot write {}: {}".format(path_label, error)) from None


def run(arguments: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(arguments)
    if args.max_bytes <= 0:
        parser.error("--max-bytes must be greater than zero")
    if args.max_records <= 0:
        parser.error("--max-records must be greater than zero")
    if args.inputs.count("-") > 1:
        parser.error("standard input may be specified only once")

    processor = FeedProcessor()
    record_count = 0
    try:
        for input_path in args.inputs:
            records = read_records(
                input_path,
                input_format=args.input_format,
                source=args.source,
                max_bytes=args.max_bytes,
            )
            record_count += len(records)
            if record_count > args.max_records:
                raise InputReadError(
                    "record count exceeds the {} record limit".format(args.max_records)
                )
            processor.add_many(records)
        result = processor.result()
        content = render_json(result) if args.output_format == "json" else render_csv(result)
        _write_output(args.output, content)
    except InputReadError as error:
        print("ioc-feed-toolkit: error: {}".format(error), file=sys.stderr)
        return 2
    except BrokenPipeError:
        return 0

    if not args.quiet:
        print(
            "{} unique indicators from {} observations ({} duplicates); {} rejected".format(
                len(result.indicators),
                result.observations,
                result.duplicate_observations,
                len(result.rejected),
            ),
            file=sys.stderr,
        )
    if args.fail_on_reject and result.rejected:
        return 1
    return 0


def main() -> None:
    raise SystemExit(run())
