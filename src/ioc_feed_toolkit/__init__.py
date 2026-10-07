"""Normalize and deduplicate indicators of compromise without network access."""

from .models import FeedResult, Indicator, Provenance, RejectedIndicator
from .normalize import IndicatorValidationError, normalize_indicator
from .pipeline import FeedProcessor

__all__ = [
    "FeedProcessor",
    "FeedResult",
    "Indicator",
    "IndicatorValidationError",
    "Provenance",
    "RejectedIndicator",
    "normalize_indicator",
]

__version__ = "0.1.0"
