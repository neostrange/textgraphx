"""Compatibility tests for the moved schema constraint helper."""

from textgraphx.database.schema_constraints import create_constraints
from textgraphx.database import schema_constraints as canonical_schema_constraints


def test_utils_wrapper_reexports_canonical_create_constraints():
    assert create_constraints is canonical_schema_constraints.create_constraints