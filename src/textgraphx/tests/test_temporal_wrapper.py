"""Unit tests for TemporalPhaseWrapper document-id extraction."""

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.mark.unit
def test_temporal_wrapper_accepts_scalar_document_ids(monkeypatch):
    from textgraphx.phase_wrappers import TemporalPhaseWrapper

    created = []

    class FakeTemporalPhase:
        def __init__(self, argv=None):
            self.graph = MagicMock()

        def get_annotated_text(self):
            return [1]

        def create_DCT_node(self, doc_id):
            created.append(("dct", doc_id))

        def materialize_tevents(self, doc_id):
            created.append(("tevents", doc_id))

        def materialize_signals(self, doc_id):
            created.append(("signals", doc_id))

        def materialize_timexes_fallback(self, doc_id):
            created.append(("timexes", doc_id))

        def materialize_glinks(self, doc_id):
            created.append(("glinks", doc_id))

    fake_module = types.ModuleType("textgraphx.pipeline.temporal.extraction")
    fake_module.TemporalPhase = FakeTemporalPhase
    monkeypatch.setitem(sys.modules, "textgraphx.pipeline.temporal.extraction", fake_module)

    wrapper = TemporalPhaseWrapper()
    result = wrapper.execute()

    assert result["documents"] == 1
    assert created == [
        ("dct", 1),
        ("tevents", 1),
        ("signals", 1),
        ("timexes", 1),
        ("glinks", 1),
    ]


@pytest.mark.regression
def test_temporal_wrapper_accepts_dict_document_ids(monkeypatch):
    from textgraphx.phase_wrappers import TemporalPhaseWrapper

    seen = []

    class FakeTemporalPhase:
        def __init__(self, argv=None):
            self.graph = MagicMock()

        def get_annotated_text(self):
            return [{"doc_id": "7"}]

        def create_DCT_node(self, doc_id):
            seen.append(doc_id)

        def materialize_tevents(self, doc_id):
            pass

        def materialize_signals(self, doc_id):
            pass

        def materialize_timexes_fallback(self, doc_id):
            pass

        def materialize_glinks(self, doc_id):
            pass

    fake_module = types.ModuleType("textgraphx.pipeline.temporal.extraction")
    fake_module.TemporalPhase = FakeTemporalPhase
    monkeypatch.setitem(sys.modules, "textgraphx.pipeline.temporal.extraction", fake_module)

    wrapper = TemporalPhaseWrapper()
    result = wrapper.execute()

    assert result["documents"] == 1
    assert seen == [7]


@pytest.mark.regression
def test_temporal_wrapper_normalizes_numeric_document_ids(monkeypatch):
    from textgraphx.phase_wrappers import TemporalPhaseWrapper

    created = []

    class FakeTemporalPhase:
        def __init__(self, argv=None):
            self.graph = MagicMock()

        def get_annotated_text(self):
            return [{"doc_id": "2"}, {"n.id": "11"}, 3, "5"]

        def create_DCT_node(self, doc_id):
            created.append(doc_id)

        def materialize_tevents(self, doc_id):
            pass

        def materialize_signals(self, doc_id):
            pass

        def materialize_timexes_fallback(self, doc_id):
            pass

        def materialize_glinks(self, doc_id):
            pass

    fake_module = types.ModuleType("textgraphx.pipeline.temporal.extraction")
    fake_module.TemporalPhase = FakeTemporalPhase
    monkeypatch.setitem(sys.modules, "textgraphx.pipeline.temporal.extraction", fake_module)

    wrapper = TemporalPhaseWrapper()
    result = wrapper.execute()

    assert result["documents"] == 4
    assert created == [2, 3, 5, 11]
