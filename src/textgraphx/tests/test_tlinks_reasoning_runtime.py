"""Runtime reasoning checks for TLINK closure and endpoint contract observability."""

from unittest.mock import MagicMock

import pytest

from textgraphx.TlinksRecognizer import TlinksRecognizer


@pytest.mark.unit
class TestTlinksReasoningRuntime:
    def test_apply_tlink_transitive_closure_stops_when_no_new_edges(self):
        obj = TlinksRecognizer.__new__(TlinksRecognizer)
        obj.graph = MagicMock()
        obj._run_query = MagicMock(
            side_effect=[
                [{"created": 2}],
                [{"created": 1}],
                [{"created": 0}],
            ]
        )

        created = obj.apply_tlink_transitive_closure(max_rounds=5)

        assert created == 3
        assert obj._run_query.call_count == 3

    def test_apply_tlink_transitive_closure_query_contains_core_rules(self):
        """Transitive closure is restricted to IDENTITY-chain compositions only.
        BEFORE/AFTER/SIMULTANEOUS transitivity was removed because it generates
        O(N²) spurious links across distant event pairs (precision collapse)."""
        obj = TlinksRecognizer.__new__(TlinksRecognizer)
        obj.graph = MagicMock()
        captured = {}

        def _capture(query, parameters=None):
            captured["query"] = query
            return [{"created": 0}]

        obj._run_query = _capture
        obj.apply_tlink_transitive_closure(max_rounds=1)

        query = captured.get("query", "")
        # IDENTITY-chain composition is the only active rule
        assert "IDENTITY" in query, "Closure query must handle IDENTITY chains"
        # BEFORE/AFTER transitivity intentionally removed to prevent precision collapse
        assert "t1 = 'BEFORE' AND t2 = 'BEFORE'" not in query, (
            "BEFORE+BEFORE transitivity must be absent — it generated O(N²) FPs"
        )

    def test_endpoint_contract_violations_uses_contract_counter(self, monkeypatch):
        obj = TlinksRecognizer.__new__(TlinksRecognizer)
        obj.graph = MagicMock()

        monkeypatch.setattr(
            "textgraphx.pipeline.temporal.linking.count_endpoint_violations",
            lambda graph, rel_type: 4 if rel_type == "TLINK" else 0,
        )

        assert obj.endpoint_contract_violations() == 4

    def test_apply_constraint_solver_delegates_to_solver(self, monkeypatch):
        obj = TlinksRecognizer.__new__(TlinksRecognizer)
        obj.graph = MagicMock()

        monkeypatch.setattr(
            "textgraphx.pipeline.temporal.linking.solve_tlink_constraints",
            lambda graph, shadow_only: {"inverse_created": 2, "bidirectional_conflicts": 1}
            if graph is obj.graph and shadow_only
            else {"inverse_created": 0, "bidirectional_conflicts": 0},
        )

        summary = obj.apply_constraint_solver(shadow_only=True)

        assert summary["inverse_created"] == 2
        assert summary["bidirectional_conflicts"] == 1
