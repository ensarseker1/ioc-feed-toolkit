# Input and output formats

IOC Feed Toolkit reads UTF-8 data. `--input-format auto` uses the `.csv`,
`.json`, or `.txt` extension when available, then conservatively inspects the
content. Use an explicit format for ambiguous input or standard input.

## Plain text

Place one indicator on each line. Blank lines and lines whose first
non-whitespace character is `#` are ignored. Each accepted or rejected record
includes its line number. Plain text does not carry a declared type; detection
is conservative.

```text
# synthetic examples
example.test
203.0.113.5
2001:db8::5
```

## CSV

A header is required. The indicator column can be named `indicator`, `value`,
`ioc`, or `observable`. Optional type columns are `type`, `indicator_type`, or
`ioc_type`. Optional source columns are `source`, `feed`, or `provider`.
Column matching is case-insensitive and surrounding header whitespace is
ignored. Extra columns are ignored.

```csv
indicator,type,source
Example.TEST.,domain,synthetic-feed
203.0.113.5,ipv4,synthetic-feed
```

## JSON

JSON may be a string, an array, one indicator object, or an envelope with an
`indicators` array and optional source:

```json
{
  "source": "synthetic-feed",
  "indicators": [
    "example.test",
    {"value": "203.0.113.5", "type": "ipv4"},
    {"indicator": "2001:db8::5", "source": "another-source"}
  ]
}
```

Indicator objects accept `indicator`, `value`, `ioc`, or `observable`. Type and
source aliases match the CSV names. Non-string values are preserved in rejected
diagnostics instead of being coerced into potentially valid indicators.

## Provenance precedence

An input record's source field takes precedence. Otherwise `--source` supplies
the fallback. If neither is present, the input path is used; standard input is
named `stdin`. Locations are a line, row, or JSON path. The original string is
retained for every distinct accepted observation.

## Types and normalization

Accepted declared types and common aliases:

| Canonical type | Declared values | Normalization |
| --- | --- | --- |
| `ipv4` | `ip`, `ip-address`, `ipv4` | Standard dotted decimal |
| `ipv6` | `ip`, `ip-address`, `ipv6` | Compressed lowercase form |
| `domain` | `domain`, `domain-name`, `fqdn` | Lowercase IDNA ASCII, trailing dot removed |
| `url` | `url`, `uri` | Lowercase scheme/host, normalized host/default port/percent-escape case, fragment removed |
| `hash-md5` | `hash`, `md5`, `hash-md5` | Lowercase hexadecimal |
| `hash-sha1` | `hash`, `sha1`, `sha-1`, `hash-sha1` | Lowercase hexadecimal |
| `hash-sha256` | `hash`, `sha256`, `sha-256`, `hash-sha256` | Lowercase hexadecimal |
| `hash-sha512` | `hash`, `sha512`, `sha-512`, `hash-sha512` | Lowercase hexadecimal |

Domains must contain at least one dot. URLs accept `http`, `https`, and `ftp`.
Query order and path case are preserved because changing them may change URL
meaning. Auto-detection checks URL syntax, IP shape, supported hash lengths, and
then domain syntax; an explicit type gives clearer diagnostics.

## Determinism and deduplication

Accepted values are keyed by canonical type and value. Indicators, provenance,
and rejections are sorted by their data rather than arrival order, so permuting
input files produces the same semantic output. Repeated observations contribute
to the duplicate count; exact duplicate provenance is stored once.

## JSON output

JSON contains:

- `summary`: observation, unique, duplicate, and rejection counts.
- `indicators`: unique normalized indicators with provenance arrays.
- `rejected`: raw display value, source, location, optional declared type, and
  validation reason.

## CSV output

CSV has one row per unique indicator and one row per rejection. Accepted rows
store the complete provenance array as compact JSON in the `provenance` cell.
Rejected rows use the diagnostic columns. Cells beginning with common
spreadsheet formula prefixes are apostrophe-prefixed to reduce formula
injection risk when opened interactively.

## Exit codes

- `0`: processing completed; rejections may still be present.
- `1`: processing completed with rejections and `--fail-on-reject` was used.
- `2`: structural input, limit, read, or write error.
