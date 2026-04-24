"""Timezone-safe timestamp helpers used across textgraphx runtime paths."""

from __future__ import annotations

from datetime import datetime, timezone


def utc_iso_now() -> str:
    """Return the current UTC time as an ISO-8601 string with timezone info."""
    return datetime.now(timezone.utc).isoformat()


def utc_timestamp_now() -> float:
    """Return the current UTC Unix timestamp as a float."""
    return datetime.now(timezone.utc).timestamp()