"""Unit tests for TLINK temporal constraint solver helpers."""

from unittest.mock import MagicMock

import pytest

from textgraphx.temporal_constraints import (
    materialize_inverse_tlinks,
    solve_tlink_constraints,
    suppress_bidirectional_same_rel_conflicts,
)


@pytest.mark.unit
class TestTemporalConstraints:
    def test_materialize_inverse_tlinks_returns_created_count(self):
        graph = MagicMock()
        graph.run.return_value.data.return_value = [{"created": 3}]

        created = materialize_inverse_tlinks(graph)

        assert created == 3
        graph.run.assert_called_once()

    def test_suppress_bidirectional_same_rel_conflicts_shadow_mode(self):
        graph = MagicMock()
        graph.run.return_value.data.return_value = [{"would_suppress": 5}]

        would_suppress = suppress_bidirectional_same_rel_conflicts(graph, shadow_only=True)

        assert would_suppress == 5

    def test_solve_tlink_constraints_returns_summary(self):
        graph = MagicMock()
        graph.run.return_value.data.side_effect = [
            [{"created": 2}],
            [{"suppressed": 1}],
        ]

        summary = solve_tlink_constraints(graph, shadow_only=False)

        assert summary["inverse_created"] == 2
        assert summary["bidirectional_conflicts"] == 1
