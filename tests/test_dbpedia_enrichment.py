"""Focused unit tests for DBpedia resolution and enrichment."""

import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.mark.unit
def test_dbpedia_resolver_accepts_near_exact_company_match():
    from textgraphx.phase_wrappers import DBpediaResolver

    resolver = DBpediaResolver(
        lookup_url="https://lookup.dbpedia.org/api/search/KeywordSearch",
        timeout_sec=5,
        max_candidates=5,
        min_similarity=0.93,
        min_margin=0.10,
    )
    resolver.lookup_candidates = lambda surface_form, expected_type: [
        {
            "resource_uri": "http://dbpedia.org/resource/BNP_Paribas",
            "label": "BNP Paribas",
            "classes": ["company", "organisation"],
            "ref_count": 500,
        }
    ]

    result = resolver.resolve("BNP Paribas SA", "ORG")

    assert result["status"] == "resolved"
    assert result["resource_uri"] == "http://dbpedia.org/resource/BNP_Paribas"
    assert result["resolved_label"] == "BNP Paribas"
    assert result["confidence"] is not None


@pytest.mark.unit
def test_dbpedia_resolver_marks_close_candidates_ambiguous():
    from textgraphx.phase_wrappers import DBpediaResolver

    resolver = DBpediaResolver(
        lookup_url="https://lookup.dbpedia.org/api/search/KeywordSearch",
        timeout_sec=5,
        max_candidates=5,
        min_similarity=0.90,
        min_margin=0.10,
    )
    resolver.lookup_candidates = lambda surface_form, expected_type: [
        {
            "resource_uri": "http://dbpedia.org/resource/Mercury_(planet)",
            "label": "Mercury",
            "classes": ["planet", "place"],
            "ref_count": 800,
        },
        {
            "resource_uri": "http://dbpedia.org/resource/Mercury_(mythology)",
            "label": "Mercury",
            "classes": ["person", "agent"],
            "ref_count": 780,
        },
    ]

    result = resolver.resolve("Mercury", None)

    assert result["status"] == "ambiguous"
    assert result["reason"] == "top_candidates_too_close"
    assert result["resource_uri"] is None


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
def test_dbpedia_enrichment_wrapper_resolves_plain_text_entity(monkeypatch):
    from textgraphx.phase_wrappers import DBpediaEnrichmentPhaseWrapper

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

    fake_phase_assertions = types.ModuleType("textgraphx.phase_assertions")
    fake_phase_assertions.record_phase_run = lambda *args, **kwargs: None
    monkeypatch.setitem(sys.modules, "textgraphx.phase_assertions", fake_phase_assertions)
    monkeypatch.setattr("textgraphx.phase_wrappers.get_config", lambda: fake_cfg, raising=False)
    monkeypatch.setattr("textgraphx.config.get_config", lambda: fake_cfg)
    monkeypatch.setattr("textgraphx.neo4j_client.make_graph_from_config", lambda: fake_graph)

    def fake_requests_post(url, data=None, headers=None, timeout=None):
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

    monkeypatch.setattr("textgraphx.phase_wrappers.requests.post", fake_requests_post)
    monkeypatch.setattr("textgraphx.phase_wrappers.requests.get", fake_requests_get)

    wrapper = DBpediaEnrichmentPhaseWrapper()
    result = wrapper.execute()

    assert result["status"] == "success"
    assert result["entities_considered"] == 1
    assert result["documents_annotated"] == 1
    assert result["resolved_spotlight"] == 1
    assert result["resolved_lookup"] == 1
    assert result["entities_enriched"] == 1
    assert fake_graph.resolution_updates[0]["resource_uri"] == "http://dbpedia.org/resource/BNP_Paribas"
    assert fake_graph.resolution_updates[0]["resolution_status"] == "resolved"
    assert fake_graph.resolution_updates[0]["resolution_source"] == "dbpedia_spotlight"
    assert fake_graph.enrichment_updates[0]["types"] == ["Company", "Organisation"]
    assert fake_graph.closed is True