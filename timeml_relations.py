"""TimeML/ISO-TimeML relation normalization helpers."""

from __future__ import annotations

from typing import Optional

# Canonical relation inventory used for TLINK normalization.
CANONICAL_TLINK_RELTYPES = (
    "BEFORE",
    "AFTER",
    "INCLUDES",
    "IS_INCLUDED",
    "SIMULTANEOUS",
    "IBEFORE",
    "IAFTER",
    "BEGINS",
    "BEGUN_BY",
    "ENDS",
    "ENDED_BY",
    "DURING",
    "DURING_INV",
    "IDENTITY",
    "VAGUE",
)

_ALIAS_TO_CANONICAL = {
    "INCLUDE": "INCLUDES",
    "INCLUDED": "IS_INCLUDED",
    "SIMULTANEOUSLY": "SIMULTANEOUS",
    "OVERLAP": "SIMULTANEOUS",
    "EQUAL": "IDENTITY",
    "SAMEAS": "IDENTITY",
    "MEASURE": "DURING",
}


def normalize_tlink_reltype(reltype: Optional[str]) -> str:
    """Normalize arbitrary relation strings to canonical TimeML-style labels."""
    raw = str(reltype or "").strip().upper()
    if not raw:
        return "VAGUE"
    if raw in CANONICAL_TLINK_RELTYPES:
        return raw
    if raw in _ALIAS_TO_CANONICAL:
        return _ALIAS_TO_CANONICAL[raw]
    return "VAGUE"


def is_canonical_tlink_reltype(reltype: Optional[str]) -> bool:
    raw = str(reltype or "").strip().upper()
    return raw in CANONICAL_TLINK_RELTYPES
