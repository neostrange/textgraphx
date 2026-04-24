"""Focused unit tests for DBpedia Spotlight-based enrichment."""

import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.mark.unit
def test_dbpedia_spotlight_resolution_accepts_aligned_annotation():
    from textgraphx.pipeline.runtime.phase_wrappers import DBpediaEnrichmentPhaseWrapper

    wrapper = DBpediaEnrichmentPhaseWrapper()
    row = {
        "value": "BNP Paribas SA",
        "lookup_text": "BNP Paribas SA",
        "entity_type": "ORG",
        "start_char": 6,
        "end_char": 20,
        "kb_id": "",
        "dbpedia_resource": "",
    }
    document_text = "France BNP Paribas SA halted withdrawals."
    annotations = [
        {
            "resource_uri": "http://dbpedia.org/resource/BNP_Paribas",
            "surface_form": "BNP Paribas SA",
            "offset": 6,
            "similarity": 0.95,
            "support": 120,
            "types": "DBpedia:Company,Schema:Organization",
        }
    ]

    result = wrapper._resolve_from_document_annotations(
        row=row,
        document_text=document_text,
        annotations=annotations,
        min_similarity=0.8,
    )

    assert result["status"] == "resolved"
    assert result["reason"] == "spotlight_document_context"
    assert result["resource_uri"] == "http://dbpedia.org/resource/BNP_Paribas"
    assert result["confidence"] == 0.95


@pytest.mark.unit
def test_dbpedia_spotlight_resolution_rejects_type_mismatch():
    from textgraphx.pipeline.runtime.phase_wrappers import DBpediaEnrichmentPhaseWrapper

    wrapper = DBpediaEnrichmentPhaseWrapper()
    row = {
        "value": "Mercury",
        "lookup_text": "Mercury",
        "entity_type": "ORG",
        "start_char": 0,
        "end_char": 7,
        "kb_id": "",
        "dbpedia_resource": "",
    }
    annotations = [
        {
            "resource_uri": "http://dbpedia.org/resource/Mercury_(planet)",
            "surface_form": "Mercury",
            "offset": 0,
            "similarity": 0.99,
            "support": 500,
            "types": "DBpedia:Planet,Schema:Place",
        }
    ]

    result = wrapper._resolve_from_document_annotations(
        row=row,
        document_text="Mercury rose.",
        annotations=annotations,
        min_similarity=0.8,
    )

    assert result["status"] == "no_match"
    assert result["reason"] == "spotlight_type_mismatch"


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def data(self):
        return self._rows


class _FakeGraph:
    def __init__(self):
        self.resolution_updates = []
        self.enrichment_updates = []
        self.closed = False

    def run(self, query, params=None):
        params = params or {}
        if "RETURN d.id AS doc_id" in query:
            return _FakeResult(
                [
                    {
                        "doc_id": 76437,
                        "document_text": "France's largest bank, BNP Paribas SA, halted withdrawals.",
                        "element_id": 4,
                        "entity_type": "ORG",
                        "lookup_text": "BNP Paribas SA",
                        "value": "BNP Paribas SA",
                        "kb_id": "",
                        "dbpedia_resource": "",
                        "start_char": 23,
                        "end_char": 37,
                        "start_tok": 4,
                        "end_tok": 6,
                    }
                ]
            )
        if "SET n.dbpedia_lookup_text" in query:
            self.resolution_updates.append(params)
            return _FakeResult([])
        if "SET n.dbpedia_source = 'dbpedia_sparql'" in query:
            self.enrichment_updates.append(params)
            return _FakeResult([])
        return _FakeResult([])

    def close(self):
        self.closed = True


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


@pytest.mark.unit
def test_dbpedia_enrichment_wrapper_uses_spotlight_document_annotation(monkeypatch):
    from textgraphx.pipeline.runtime.phase_wrappers import DBpediaEnrichmentPhaseWrapper

    fake_cfg = SimpleNamespace(
        features=SimpleNamespace(enable_dbpedia_enrichment=True),
        services=SimpleNamespace(
            dbpedia_sparql_url="https://dbpedia.org/sparql",
            dbpedia_spotlight_url="https://api.dbpedia-spotlight.org/en/annotate",
            dbpedia_timeout_sec=5,
            dbpedia_max_entities_per_run=10,
            dbpedia_spotlight_confidence=0.5,
            dbpedia_spotlight_support=20,
            dbpedia_spotlight_min_similarity=0.8,
        ),
    )
    fake_graph = _FakeGraph()

    fake_phase_assertions = types.ModuleType("textgraphx.pipeline.runtime.phase_assertions")
    fake_phase_assertions.record_phase_run = lambda *args, **kwargs: None
    monkeypatch.setitem(sys.modules, "textgraphx.pipeline.runtime.phase_assertions", fake_phase_assertions)
    monkeypatch.setattr("textgraphx.infrastructure.config.get_config", lambda: fake_cfg)
    monkeypatch.setattr("textgraphx.database.client.make_graph_from_config", lambda: fake_graph)

    def fake_requests_post(url, data=None, headers=None, timeout=None):
        assert url == "https://api.dbpedia-spotlight.org/en/annotate"
        assert data["text"]
        return _FakeResponse(
            {
                "Resources": [
                    {
                        "@URI": "http://dbpedia.org/resource/BNP_Paribas",
                        "@surfaceForm": "BNP Paribas SA",
                        "@offset": "23",
                        "@similarityScore": "0.93",
                        "@support": "250",
                        "@types": "DBpedia:Company,Schema:Organization",
                    }
                ]
            }
        )

    def fake_requests_get(url, params=None, headers=None, timeout=None):
        return _FakeResponse(
            {
                "results": {
                    "bindings": [
                        {
                            "abstract": {"value": "French international banking group."},
                            "types": {"value": "Company|Organisation"},
                        }
                    ]
                }
            }
        )

    monkeypatch.setattr("textgraphx.pipeline.runtime.phase_wrappers.requests.post", fake_requests_post)
    monkeypatch.setattr("textgraphx.pipeline.runtime.phase_wrappers.requests.get", fake_requests_get)

    wrapper = DBpediaEnrichmentPhaseWrapper()
    result = wrapper.execute()

    assert result["status"] == "success"
    assert result["entities_considered"] == 1
    assert result["documents_annotated"] == 1
    assert result["resolved_spotlight"] == 1
    assert result["entities_enriched"] == 1
    assert fake_graph.resolution_updates[0]["resource_uri"] == "http://dbpedia.org/resource/BNP_Paribas"
    assert fake_graph.resolution_updates[0]["resolution_source"] == "dbpedia_spotlight"
    assert fake_graph.enrichment_updates[0]["types"] == ["Company", "Organisation"]
    assert fake_graph.closed is True
