"""Strict, side-effect-free IOC validation and normalization."""

import ipaddress
import re
from typing import Optional, Tuple
from urllib.parse import SplitResult, urlsplit, urlunsplit


class IndicatorValidationError(ValueError):
    """Raised when an input cannot be normalized as the requested IOC type."""


_DOMAIN_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
_HEX = re.compile(r"^[0-9a-fA-F]+$")
_IPV4_SHAPE = re.compile(r"^\d+(?:\.\d+){3}$")
_PERCENT_ESCAPE = re.compile(r"%[0-9a-fA-F]{2}")
_BAD_PERCENT_ESCAPE = re.compile(r"%(?![0-9a-fA-F]{2})")

_HASH_LENGTHS = {
    32: "hash-md5",
    40: "hash-sha1",
    64: "hash-sha256",
    128: "hash-sha512",
}

_TYPE_ALIASES = {
    "ip": "ip",
    "ip-address": "ip",
    "ipv4": "ipv4",
    "ipv6": "ipv6",
    "domain": "domain",
    "domain-name": "domain",
    "fqdn": "domain",
    "url": "url",
    "uri": "url",
    "hash": "hash",
    "md5": "hash-md5",
    "hash-md5": "hash-md5",
    "sha1": "hash-sha1",
    "sha-1": "hash-sha1",
    "hash-sha1": "hash-sha1",
    "sha256": "hash-sha256",
    "sha-256": "hash-sha256",
    "hash-sha256": "hash-sha256",
    "sha512": "hash-sha512",
    "sha-512": "hash-sha512",
    "hash-sha512": "hash-sha512",
}


def _clean(value: str) -> str:
    if not isinstance(value, str):
        raise IndicatorValidationError("indicator must be a string")
    cleaned = value.strip()
    if not cleaned:
        raise IndicatorValidationError("indicator is empty")
    if any(ord(character) < 32 or ord(character) == 127 for character in cleaned):
        raise IndicatorValidationError("indicator contains a control character")
    try:
        cleaned.encode("utf-8")
    except UnicodeEncodeError:
        raise IndicatorValidationError("indicator is not valid Unicode text") from None
    return cleaned


def _normalize_ip(value: str, version: Optional[int] = None) -> Tuple[str, str]:
    if "%" in value:
        raise IndicatorValidationError("scoped IPv6 addresses are not supported")
    if "/" in value:
        raise IndicatorValidationError("IP networks and prefixes are not individual indicators")
    try:
        address = ipaddress.ip_address(value)
    except ValueError as error:
        raise IndicatorValidationError("invalid IP address: {}".format(error)) from None
    if version is not None and address.version != version:
        raise IndicatorValidationError("expected IPv{}, got IPv{}".format(version, address.version))
    return ("ipv4" if address.version == 4 else "ipv6", address.compressed.lower())


def _normalize_domain(value: str) -> Tuple[str, str]:
    candidate = value.rstrip(".").lower()
    if not candidate:
        raise IndicatorValidationError("domain is empty")
    if "://" in candidate or any(character in candidate for character in "/?#@:"):
        raise IndicatorValidationError("domain contains URL or host syntax")
    try:
        ascii_domain = candidate.encode("idna").decode("ascii").lower()
    except UnicodeError:
        raise IndicatorValidationError("domain cannot be encoded as IDNA") from None
    if len(ascii_domain) > 253:
        raise IndicatorValidationError("domain exceeds 253 characters")
    labels = ascii_domain.split(".")
    if len(labels) < 2:
        raise IndicatorValidationError("domain must contain at least one dot")
    for label in labels:
        if len(label) > 63:
            raise IndicatorValidationError("domain label exceeds 63 characters")
        if not _DOMAIN_LABEL.fullmatch(label):
            raise IndicatorValidationError("domain contains an invalid label")
    if all(label.isdigit() for label in labels):
        raise IndicatorValidationError("numeric dotted value resembles an invalid IP address")
    return "domain", ascii_domain


def _uppercase_percent_escapes(value: str, component: str) -> str:
    if _BAD_PERCENT_ESCAPE.search(value):
        raise IndicatorValidationError("URL {} contains an invalid percent escape".format(component))
    return _PERCENT_ESCAPE.sub(lambda match: match.group(0).upper(), value)


def _normalized_url_host(hostname: str) -> Tuple[str, bool]:
    try:
        indicator_type, normalized = _normalize_ip(hostname)
        return normalized, indicator_type == "ipv6"
    except IndicatorValidationError:
        _, normalized = _normalize_domain(hostname)
        return normalized, False


def _normalize_url(value: str) -> Tuple[str, str]:
    if any(character.isspace() for character in value):
        raise IndicatorValidationError("URL contains whitespace")
    if "\\" in value:
        raise IndicatorValidationError("URL contains a backslash")
    try:
        parsed = urlsplit(value)
    except ValueError as error:
        raise IndicatorValidationError("invalid URL: {}".format(error)) from None
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https", "ftp"}:
        raise IndicatorValidationError("URL scheme must be http, https, or ftp")
    if not parsed.netloc or parsed.hostname is None:
        raise IndicatorValidationError("URL must include a host")
    if parsed.username is not None or parsed.password is not None:
        raise IndicatorValidationError("URL userinfo is not accepted")
    try:
        port = parsed.port
    except ValueError as error:
        raise IndicatorValidationError("invalid URL port: {}".format(error)) from None

    host, is_ipv6 = _normalized_url_host(parsed.hostname)
    rendered_host = "[{}]".format(host) if is_ipv6 else host
    default_ports = {"http": 80, "https": 443, "ftp": 21}
    netloc = rendered_host
    if port is not None and port != default_ports[scheme]:
        netloc = "{}:{}".format(netloc, port)

    path = _uppercase_percent_escapes(parsed.path or "/", "path")
    query = _uppercase_percent_escapes(parsed.query, "query")
    normalized = urlunsplit(SplitResult(scheme, netloc, path, query, ""))
    return "url", normalized


def _normalize_hash(value: str, expected_type: Optional[str] = None) -> Tuple[str, str]:
    if not _HEX.fullmatch(value):
        raise IndicatorValidationError("hash must contain only hexadecimal characters")
    detected_type = _HASH_LENGTHS.get(len(value))
    if detected_type is None:
        raise IndicatorValidationError(
            "unsupported hash length {}; expected MD5, SHA-1, SHA-256, or SHA-512".format(len(value))
        )
    if expected_type is not None and detected_type != expected_type:
        raise IndicatorValidationError(
            "expected {}, got a {}-character value".format(expected_type, len(value))
        )
    return detected_type, value.lower()


def _normalize_auto(value: str) -> Tuple[str, str]:
    if "://" in value:
        return _normalize_url(value)
    if ":" in value or _IPV4_SHAPE.fullmatch(value):
        return _normalize_ip(value)
    if _HEX.fullmatch(value) and len(value) in _HASH_LENGTHS:
        return _normalize_hash(value)
    if _HEX.fullmatch(value) and len(value) >= 16:
        return _normalize_hash(value)
    try:
        return _normalize_domain(value)
    except IndicatorValidationError as domain_error:
        raise IndicatorValidationError(
            "could not infer IOC type; provide an explicit type ({})".format(domain_error)
        ) from None


def normalize_indicator(value: str, declared_type: Optional[str] = None) -> Tuple[str, str]:
    """Validate and normalize one indicator without performing any I/O.

    The return value is ``(canonical_type, canonical_value)``. When
    ``declared_type`` is omitted, conservative syntax-based detection is used.
    """

    cleaned = _clean(value)
    if declared_type is not None and not isinstance(declared_type, str):
        raise IndicatorValidationError("declared type must be a string")
    if declared_type is None or not declared_type.strip() or declared_type.strip().lower() == "auto":
        return _normalize_auto(cleaned)

    requested = _TYPE_ALIASES.get(declared_type.strip().lower())
    if requested is None:
        raise IndicatorValidationError("unsupported declared type: {}".format(declared_type))
    if requested == "ip":
        return _normalize_ip(cleaned)
    if requested == "ipv4":
        return _normalize_ip(cleaned, version=4)
    if requested == "ipv6":
        return _normalize_ip(cleaned, version=6)
    if requested == "domain":
        return _normalize_domain(cleaned)
    if requested == "url":
        return _normalize_url(cleaned)
    if requested == "hash":
        return _normalize_hash(cleaned)
    return _normalize_hash(cleaned, expected_type=requested)
