# IOC Feed Toolkit

IOC Feed Toolkit is a small, offline-first Python CLI and library for cleaning
indicator-of-compromise feeds. It validates and normalizes IPv4, IPv6, domain,
URL, MD5, SHA-1, SHA-256, and SHA-512 values; merges duplicates; keeps every
source observation; and reports rejected records with actionable context.

It never resolves domains, requests URLs, looks up IPs, opens files named by an
indicator, or executes input. The package has no runtime dependencies.

## Why it is useful

Public and internal feeds often use different casing, IPv6 forms, column names,
and provenance fields. A deterministic local cleanup step makes those feeds
easier to review and safer to pass to downstream defensive systems without
silently discarding where each observation came from.

- Read plain text, CSV, or JSON, including several files in one run.
- Normalize conservatively without DNS, HTTP, enrichment, or refanging.
- Deduplicate by canonical `(type, value)` while retaining provenance.
- Emit stable JSON or CSV suitable for diffs and automation.
- Keep malformed records in a rejected section instead of dropping them.
- Bound file size and record count to reduce accidental resource exhaustion.
- Neutralize formula-like rejected values and source labels in CSV output.

## Install

Python 3.9 or newer is required.

```bash
python3 -m pip install .
```

For a checkout without installing it:

```bash
PYTHONPATH=src python3 -m ioc_feed_toolkit --help
```

## Quick start

Normalize one or more files into JSON:

```bash
ioc-feed-toolkit examples/sample-feed.csv examples/sample-feed.json \
  --output normalized.json
```

Write CSV and make rejection fail a CI job after the output is written:

```bash
ioc-feed-toolkit feed.txt --output-format csv --output normalized.csv \
  --fail-on-reject
```

Pipe a small plain-text feed through standard input:

```bash
printf 'Example.TEST.\n2001:0db8::5\n' | \
  ioc-feed-toolkit - --input-format text --source analyst-review
```

The JSON result contains a summary, unique indicators with provenance, and
rejected observations:

```json
{
  "indicators": [
    {
      "provenance": [
        {
          "location": "row 2",
          "original": "Example.TEST.",
          "source": "synthetic-csv"
        }
      ],
      "type": "domain",
      "value": "example.test"
    }
  ],
  "rejected": [],
  "summary": {
    "duplicate_observations": 0,
    "observations": 1,
    "rejected": 0,
    "unique_indicators": 1
  }
}
```

See [docs/FORMATS.md](docs/FORMATS.md) for every accepted input shape,
normalization rule, and output field.

## Library use

```python
from ioc_feed_toolkit import FeedProcessor
from ioc_feed_toolkit.pipeline import InputRecord

processor = FeedProcessor()
processor.add(InputRecord("Example.TEST.", "manual-review", "item 1", "domain"))
processor.add(InputRecord("example.test", "second-feed", "row 4"))

result = processor.result()
assert result.indicators[0].value == "example.test"
assert len(result.indicators[0].provenance) == 2
```

For one value, `normalize_indicator(value, declared_type=None)` returns a
`(canonical_type, canonical_value)` pair or raises `IndicatorValidationError`.
It performs no I/O.

## Safety model and limits

Input is treated only as data. Even so, normalized indicators may be live and
dangerous if another tool makes them clickable or visits them. Review output
before importing it into systems that perform enrichment, blocking, or active
network requests.

Normalization is intentionally conservative:

- Defanged forms such as `example[.]test` are rejected, not silently activated.
- URL fragments are removed; default ports and empty paths are canonicalized.
- URL credentials, IP ranges, scoped IPv6 addresses, and malformed percent
  escapes are rejected.
- Hash validation is syntactic. The tool does not read or hash referenced files.
- Domain validation does not prove registration, ownership, or maliciousness.

The default limit is 10 MiB per input and 100,000 total records. Override these
with `--max-bytes` and `--max-records` only for trusted workloads.

## Development

Run the dependency-free test suite:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

All fixtures use reserved `.test`, TEST-NET IPv4, and documentation IPv6 values.
They are synthetic and do not claim that any real host is malicious.

Please read [CONTRIBUTING.md](CONTRIBUTING.md) before proposing changes. Report
security concerns using [SECURITY.md](SECURITY.md), not a public issue.

## License

Released under the [MIT License](LICENSE).
