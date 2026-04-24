"""Tests for diagnostics-related API endpoints."""

from __future__ import annotations

import asyncio
import importlib
import sys
from dataclasses import dataclass
from types import SimpleNamespace

import pytest
from fastapi import HTTPException


pytestmark = [pytest.mark.unit]


class _FakeExecutionHistory:
    def get_statistics(self):
        return {}

    def get_execution(self, execution_id):
        return None

    def get_by_dataset(self, dataset_path, limit=20):
        return []

    def get_latest(self, limit=20):
        return []

    def store_execution(self, record):
        return None


@dataclass
class _FakeExecutionRecord:
    execution_id: str
    dataset_path: str
    phases: str
    status: str
    total_duration: float
    phase_timings: dict
    documents_processed: int
    error_message: str | None = None
    started_at: str = ""
    completed_at: str = ""


class _FakeExecutionSummary:
    pass


class _FakePipelineOrchestrator:
    def __init__(self, directory=None, model_name=None):
        self.summary = SimpleNamespace(
            start=lambda: None,
            finish=lambda: None,
            failed_count=0,
            total_duration=0.0,
            phases={},
            total_documents=0,
            errors=[],
        )

    def run_selected(self, phases):
        return None


class _FakeGraph:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


def _load_api_module(monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "execution_history",
        SimpleNamespace(ExecutionHistory=_FakeExecutionHistory, ExecutionRecord=_FakeExecutionRecord),
    )
    monkeypatch.setitem(
        sys.modules,
        "execution_summary",
        SimpleNamespace(ExecutionSummary=_FakeExecutionSummary),
    )
    monkeypatch.setitem(
        sys.modules,
        "textgraphx.orchestration.orchestrator",
        SimpleNamespace(PipelineOrchestrator=_FakePipelineOrchestrator),
    )
    monkeypatch.setitem(
        sys.modules,
        "textgraphx.database.client",
        SimpleNamespace(make_graph_from_config=lambda: _FakeGraph()),
    )
    sys.modules.pop("textgraphx.infrastructure.api", None)
    module = importlib.import_module("textgraphx.infrastructure.api")
    return importlib.reload(module)


def test_api_registers_diagnostics_routes(monkeypatch):
    api = _load_api_module(monkeypatch)

    paths = {route.path for route in api.app.routes}
    assert "/diagnostics/runtime" in paths
    assert "/diagnostics/queries" in paths
    assert "/diagnostics/query/{query_name}" in paths


def test_list_runtime_diagnostic_queries_returns_registry(monkeypatch):
    api = _load_api_module(monkeypatch)
    monkeypatch.setattr(
        api,
        "get_registered_diagnostics",
        lambda: [{"name": "phase_execution_summary", "expected_fields": ["phase"]}],
    )

    payload = asyncio.run(api.list_runtime_diagnostic_queries())

    assert payload[0]["name"] == "phase_execution_summary"


def test_get_runtime_diagnostics_supports_totals_only(monkeypatch):
    api = _load_api_module(monkeypatch)
    graph = _FakeGraph()
    monkeypatch.setattr(api, "make_graph_from_config", lambda: graph)
    monkeypatch.setattr(
        api,
        "get_runtime_metrics",
        lambda _graph: {"totals": {"assertion_violation_count": 3}, "phase_execution_summary": []},
    )

    payload = asyncio.run(api.get_runtime_diagnostics(totals_only=True))

    assert payload == {"assertion_violation_count": 3}
    assert graph.closed is True


def test_get_runtime_diagnostic_query_returns_named_rows(monkeypatch):
    api = _load_api_module(monkeypatch)
    graph = _FakeGraph()
    monkeypatch.setattr(api, "make_graph_from_config", lambda: graph)
    monkeypatch.setattr(api, "list_diagnostic_queries", lambda: ["phase_execution_summary"])
    monkeypatch.setattr(
        api,
        "run_registered_diagnostic",
        lambda _graph, query_name: [{"phase": query_name, "execution_count": 2}],
    )

    payload = asyncio.run(api.get_runtime_diagnostic_query("phase_execution_summary"))

    assert payload["query_name"] == "phase_execution_summary"
    assert payload["rows"][0]["execution_count"] == 2
    assert graph.closed is True


def test_get_runtime_diagnostic_query_rejects_unknown_name(monkeypatch):
    api = _load_api_module(monkeypatch)
    monkeypatch.setattr(api, "list_diagnostic_queries", lambda: ["phase_execution_summary"])

    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(api.get_runtime_diagnostic_query("not_a_query"))

    assert excinfo.value.status_code == 404
    assert "Unknown diagnostics query" in excinfo.value.detail