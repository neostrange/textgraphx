"""Compatibility wrapper for canonical temporal constraint helpers."""

from textgraphx.reasoning.temporal.constraints import (
    INVERSE_REL_MAP,
    materialize_inverse_tlinks,
    solve_tlink_constraints,
    suppress_bidirectional_same_rel_conflicts,
)

__all__ = [
    "INVERSE_REL_MAP",
    "materialize_inverse_tlinks",
    "solve_tlink_constraints",
    "suppress_bidirectional_same_rel_conflicts",
]
