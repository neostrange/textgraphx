"""Unit tests for stable query pack (Iteration 3 item 12)."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from textgraphx.queries.query_pack import available_queries, load_query


@pytest.mark.unit
class TestQueryPack:
    def test_available_queries_contains_expected_entries(self):
        names = available_queries()
        assert "counts_by_label" in names
        assert "recent_phase_runs" in names
        assert "doc_invariants" in names

    def test_available_queries_sorted(self):
        names = available_queries()
        assert names == sorted(names)

    def test_load_query_returns_text(self):
        query = load_query("counts_by_label")
        assert isinstance(query, str)
        assert "MATCH" in query

    def test_load_query_unknown_raises(self):
        with pytest.raises(FileNotFoundError):
            load_query("does_not_exist")

    def test_each_query_is_non_empty(self):
        for name in available_queries():
            text = load_query(name)
            assert text.strip(), f"query '{name}' should not be empty"

    def test_counts_by_label_query_has_labels(self):
        q = load_query("counts_by_label")
        assert "labels(n)" in q

    def test_recent_phase_runs_query_targets_phase_run_label(self):
        q = load_query("recent_phase_runs")
        assert "PhaseRun" in q

    def test_doc_invariants_query_targets_annotated_text(self):
        q = load_query("doc_invariants")
        assert "AnnotatedText" in q
