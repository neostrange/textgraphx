"""Loader for stable graph-inspection Cypher queries.

The query names are intentionally stable so tests and diagnostics tooling can
rely on them across refactors.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

_QUERY_DIR = Path(__file__).resolve().parent


def available_queries() -> List[str]:
    """Return sorted query names (filename stem) from the query pack."""
    return sorted(p.stem for p in _QUERY_DIR.glob("*.cypher"))


def load_query(name: str) -> str:
    """Load a query by stable name.

    Args:
        name: Query name without extension, for example ``"counts_by_label"``.

    Raises:
        FileNotFoundError: If the named query does not exist.
    """
    path = _QUERY_DIR / f"{name}.cypher"
    if not path.exists():
        raise FileNotFoundError(f"Unknown query pack entry: {name}")
    return path.read_text(encoding="utf-8")
