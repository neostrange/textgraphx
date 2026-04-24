"""Focused wrapper tests for moved temporal support helpers."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import textgraphx.temporal_constraints as legacy_temporal_constraints
import textgraphx.temporal_legacy_compat as legacy_temporal_legacy_compat
import textgraphx.timeml_relations as legacy_timeml_relations
from textgraphx.reasoning.temporal import constraints as canonical_constraints
from textgraphx.reasoning.temporal import legacy_compat as canonical_legacy_compat
from textgraphx.reasoning.temporal import timeml_relations as canonical_timeml_relations


def test_temporal_constraints_wrapper_reexports_canonical_symbols():
    assert legacy_temporal_constraints.solve_tlink_constraints is canonical_constraints.solve_tlink_constraints
    assert legacy_temporal_constraints.INVERSE_REL_MAP is canonical_constraints.INVERSE_REL_MAP


def test_timeml_relations_wrapper_reexports_canonical_symbols():
    assert legacy_timeml_relations.normalize_tlink_reltype is canonical_timeml_relations.normalize_tlink_reltype
    assert legacy_timeml_relations.CANONICAL_TLINK_RELTYPES is canonical_timeml_relations.CANONICAL_TLINK_RELTYPES


def test_temporal_legacy_compat_wrapper_reexports_canonical_symbols():
    assert legacy_temporal_legacy_compat.LEGACY_METHODS is canonical_legacy_compat.LEGACY_METHODS
    assert legacy_temporal_legacy_compat.legacy_event_mentions is canonical_legacy_compat.legacy_event_mentions


def test_legacy_event_mentions_warns_and_executes_query():
    phase = SimpleNamespace(graph=MagicMock())
    phase.graph.run.return_value.data.return_value = [{"mentions_created": 1}]

    with pytest.warns(DeprecationWarning):
        result = canonical_legacy_compat.legacy_event_mentions(phase, 42)

    assert result == ""
    phase.graph.run.assert_called_once()