"""Unit tests for nominal coverage probe query semantics."""

from __future__ import annotations

from typing import Any

from textgraphx.tools.nominal_coverage_probe import _snapshot


class _Rows:
    def __init__(self, payload: list[dict[str, Any]]):
        self._payload = payload

    def data(self) -> list[dict[str, Any]]:
        return self._payload


class _FakeGraph:
    def __init__(self):
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def run(self, query: str, params: dict[str, Any]) -> _Rows:
        self.calls.append((query, params))
        # Count queries return a single scalar count; grouped queries return rows with key/count.
        if "AS key" in query:
            return _Rows([])
        return _Rows([{"count": 1}])


def test_snapshot_with_doc_scope_uses_exists_filters_not_optional_match():
    graph = _FakeGraph()

    snapshot = _snapshot(graph, doc_id="76437")

    assert snapshot["named_entities_nominal"] == 1
    assert snapshot["entities_nominal"] == 1
    assert snapshot["entity_mentions_nominal"] == 1
    assert snapshot["nominal_mentions_label"] == 1
    assert snapshot["frame_args_nominal"] == 1
    assert "nominal_entities_by_subtype" in snapshot
    assert "quantified_nominal_entities_by_subtype" in snapshot

    assert graph.calls, "Expected probe to execute Cypher queries"
    for query, params in graph.calls:
        assert params["doc_id"] == "76437"
        assert "OPTIONAL MATCH" not in query
        assert "EXISTS {" in query
        assert "toString(d.id) = $doc_id" in query


def test_snapshot_without_doc_scope_does_not_add_exists_filter():
    graph = _FakeGraph()

    _snapshot(graph, doc_id=None)

    assert graph.calls, "Expected probe to execute Cypher queries"
    for query, params in graph.calls:
        assert params["doc_id"] is None
        assert "EXISTS {" not in query
        assert "$doc_id" not in query
