"""Tests for the runtime diagnostics operator CLI."""

from __future__ import annotations

import json
import sys
from types import SimpleNamespace

import pytest

from textgraphx.tools import runtime_diagnostics


pytestmark = [pytest.mark.unit]


def test_list_queries_mode_prints_registered_metadata(monkeypatch, capsys):
    monkeypatch.setattr(
        runtime_diagnostics,
        "get_registered_diagnostics",
        lambda: [{"name": "phase_execution_summary", "expected_fields": ["phase"]}],
    )

    rc = runtime_diagnostics.main(["--list-queries"])

    assert rc == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload[0]["name"] == "phase_execution_summary"


def test_query_mode_executes_single_registered_query(monkeypatch, capsys):
    class _FakeGraph:
        def close(self):
            return None

    monkeypatch.setattr(runtime_diagnostics, "list_diagnostic_queries", lambda: ["phase_execution_summary"])
    monkeypatch.setattr(
        runtime_diagnostics,
        "run_registered_diagnostic",
        lambda graph, query_name: [{"phase": query_name, "execution_count": 2}],
    )
    monkeypatch.setitem(
        sys.modules,
        "textgraphx.database.client",
        SimpleNamespace(make_graph_from_config=lambda: _FakeGraph()),
    )

    rc = runtime_diagnostics.main(["--query", "phase_execution_summary"])

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["phase"] == "phase_execution_summary"


def test_totals_only_mode_emits_only_totals(monkeypatch, capsys):
    class _FakeGraph:
        def close(self):
            return None

    monkeypatch.setattr(
        runtime_diagnostics,
        "get_runtime_metrics",
        lambda graph: {"totals": {"assertion_violation_count": 3}, "phase_execution_summary": []},
    )
    monkeypatch.setitem(
        sys.modules,
        "textgraphx.database.client",
        SimpleNamespace(make_graph_from_config=lambda: _FakeGraph()),
    )

    rc = runtime_diagnostics.main(["--totals-only"])

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"assertion_violation_count": 3}


def test_output_writes_json_file(monkeypatch, tmp_path, capsys):
    output_path = tmp_path / "diagnostics.json"
    monkeypatch.setattr(
        runtime_diagnostics,
        "get_registered_diagnostics",
        lambda: [{"name": "phase_execution_summary", "expected_fields": ["phase"]}],
    )

    rc = runtime_diagnostics.main(["--list-queries", "--output", str(output_path)])

    assert rc == 0
    assert output_path.exists()
    assert json.loads(output_path.read_text(encoding="utf-8"))[0]["name"] == "phase_execution_summary"
    assert capsys.readouterr().out


def test_invalid_query_returns_error(monkeypatch, capsys):
    monkeypatch.setattr(runtime_diagnostics, "list_diagnostic_queries", lambda: ["phase_execution_summary"])

    rc = runtime_diagnostics.main(["--query", "not_a_query"])

    assert rc == 2
    assert "unknown diagnostics query" in capsys.readouterr().err