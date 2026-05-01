"""SRL argument-label normalizer.

Converts raw BIO/PropBank/NomBank role labels to a canonical label plus a set
of boolean edge-property flags.  The raw label is always preserved so
provenance is never lost.

Rules
-----
- ``C-<ROLE>``  (continuation)  → canonical=<ROLE>, is_continuation=True
- ``R-<ROLE>``  (relative-ref)  → canonical=<ROLE>, is_relative=True
- ``<ROLE>-PRD`` (predicative)  → canonical=<ROLE>, predicative=True
- Everything else               → canonical=label, no extra flags
- ``ARGM-*`` modifiers are kept as-is (no stripping of the modifier sub-type).

Returns
-------
A ``RoleNormalization`` named-tuple with:

    canonical : str   — normalized label used for matching / statistics
    raw       : str   — original label (persisted as ``raw_role`` on the edge)
    flags     : dict  — extra edge properties; only truthy values included
"""
from __future__ import annotations

from typing import NamedTuple


class RoleNormalization(NamedTuple):
    canonical: str
    raw: str
    flags: dict


def normalize_role(label: str) -> RoleNormalization:
    """Normalize a single SRL argument label.

    Parameters
    ----------
    label:
        Raw label string as returned by the SRL service (e.g. ``"C-ARG1"``,
        ``"R-ARG0"``, ``"ARG1-PRD"``, ``"ARGM-TMP"``).

    Returns
    -------
    :class:`RoleNormalization`
    """
    raw = label
    flags: dict = {}

    # Strip continuation prefix (C-)
    if label.startswith("C-"):
        label = label[2:]
        flags["is_continuation"] = True

    # Strip relative-reference prefix (R-)
    if label.startswith("R-"):
        label = label[2:]
        flags["is_relative"] = True

    # Strip predicative suffix (-PRD)
    if label.endswith("-PRD"):
        label = label[:-4]
        flags["predicative"] = True

    return RoleNormalization(canonical=label, raw=raw, flags=flags)
