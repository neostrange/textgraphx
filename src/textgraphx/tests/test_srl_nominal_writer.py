"""Unit tests for the nominal SRL write path (process_nominal_srl).

Verifies that CogComp NomBank service responses are correctly persisted as
Frame / FrameArgument nodes with framework=NOMBANK, sense, sense_conf, and
that argument edges carry normalized type + raw_role.
"""
from __future__ import annotations

import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

import pytest


# ---------------------------------------------------------------------------
# Stub spaCy so tests run without a native installation
# ---------------------------------------------------------------------------

def _stub_modules() -> None:
    spacy = types.ModuleType("spacy")
    spacy.Language = MagicMock()
    spacy.Language.has_factory = MagicMock(return_value=True)
    sys.modules.setdefault("spacy", spacy)
    for sub in ("spacy.tokens", "spacy.matcher", "spacy.language"):
        sys.modules.setdefault(sub, types.ModuleType(sub))
    sys.modules["spacy.tokens"].Doc = MagicMock()
    sys.modules["spacy.tokens"].Token = MagicMock()
    sys.modules["spacy.tokens"].Span = MagicMock()
    sys.modules["spacy.matcher"].Matcher = MagicMock()
    sys.modules["spacy.matcher"].DependencyMatcher = MagicMock()
    sys.modules["spacy.language"].Language = MagicMock()
    for mod, attrs in (
        ("GPUtil", {}),
        ("transformers", {"logging": MagicMock()}),
    ):
        if mod not in sys.modules:
            m = types.ModuleType(mod)
            for k, v in attrs.items():
                setattr(m, k, v)
            sys.modules[mod] = m


_stub_modules()


# ---------------------------------------------------------------------------
# Minimal fake graph and doc
# ---------------------------------------------------------------------------

class _FakeGraph:
    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    def run(self, query, params=None):
        self.calls.append((query, params or {}))
        return SimpleNamespace(data=lambda: [])


def _fake_doc(text_id="doc1"):
    doc = MagicMock()
    doc._.text_id = text_id
    return doc


# ---------------------------------------------------------------------------
# Import under test (after stubs are in place)
# ---------------------------------------------------------------------------

with patch("textgraphx.database.client.make_graph_from_config", return_value=_FakeGraph()):
    from textgraphx.text_processing_components.SRLProcessor import SRLProcessor


def _make_processor():
    proc = SRLProcessor.__new__(SRLProcessor)
    proc.graph = _FakeGraph()
    return proc


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

NOMBANK_RESPONSE = {
    "words": ["The", "acquisition", "of", "the", "company", "was", "announced"],
    "frames": [
        {
            "predicate": "acquisition",
            "predicate_index": 1,
            "sense": "acquisition.01",
            "sense_score": 0.97,
            "tags": ["B-ARG0", "B-V", "B-ARG1", "I-ARG1", "I-ARG1", "O", "O"],
            "description": "acquisition.01: act of acquiring",
        }
    ],
}


@pytest.mark.unit
def test_process_nominal_srl__frame_created_with_nombank_framework():
    proc = _make_processor()
    doc = _fake_doc("docX")
    proc.process_nominal_srl(doc, [(0, NOMBANK_RESPONSE)])

    merge_calls = [q for q, _ in proc.graph.calls if "MERGE (f:Frame" in q]
    assert merge_calls, "Expected a Frame MERGE query"
    frame_params = [p for _, p in proc.graph.calls if "framework" in p]
    assert frame_params, "Expected params with 'framework'"
    assert frame_params[0]["framework"] == "NOMBANK"


@pytest.mark.unit
def test_process_nominal_srl__sense_and_sense_conf_persisted():
    proc = _make_processor()
    doc = _fake_doc("docY")
    proc.process_nominal_srl(doc, [(0, NOMBANK_RESPONSE)])

    frame_params = [p for _, p in proc.graph.calls if "sense" in p and "framework" in p]
    assert frame_params, "Expected Frame params containing 'sense'"
    p = frame_params[0]
    assert p["sense"] == "acquisition.01"
    assert abs(p["sense_conf"] - 0.97) < 1e-6


@pytest.mark.unit
def test_process_nominal_srl__frame_argument_created():
    proc = _make_processor()
    doc = _fake_doc("docZ")
    proc.process_nominal_srl(doc, [(0, NOMBANK_RESPONSE)])

    fa_merges = [q for q, _ in proc.graph.calls if "MERGE (a:FrameArgument" in q]
    assert fa_merges, "Expected at least one FrameArgument MERGE"


@pytest.mark.unit
def test_process_nominal_srl__argument_edge_has_normalized_type_and_raw_role():
    proc = _make_processor()
    doc = _fake_doc("docW")

    # Use a response with a continuation-prefix arg to exercise normalization
    response = {
        "words": ["His", "destruction", "of", "the", "city"],
        "frames": [
            {
                "predicate": "destruction",
                "predicate_index": 1,
                "sense": "destruction.01",
                "sense_score": 0.88,
                "tags": ["B-C-ARG0", "B-V", "B-ARG1", "I-ARG1", "I-ARG1"],
            }
        ],
    }
    proc.process_nominal_srl(doc, [(0, response)])

    participant_calls = [
        (q, p) for q, p in proc.graph.calls
        if "MERGE (a)-[r:PARTICIPANT]->(f)" in q
    ]
    assert participant_calls, "Expected PARTICIPANT edge writes"
    _, params = participant_calls[0]
    # canonical label: C-ARG0 → ARG0
    assert params["canonical"] == "ARG0"
    # raw label preserved
    assert params["raw"] == "C-ARG0"
    # continuation flag
    assert params["is_continuation"] is True


@pytest.mark.unit
def test_process_nominal_srl__noop_on_empty_results():
    proc = _make_processor()
    doc = _fake_doc("docEmpty")
    proc.process_nominal_srl(doc, [])
    assert proc.graph.calls == [], "No graph writes expected for empty results"


@pytest.mark.unit
def test_process_nominal_srl__noop_on_empty_frames():
    proc = _make_processor()
    doc = _fake_doc("docNoFrames")
    proc.process_nominal_srl(doc, [(0, {"words": ["hello"], "frames": []})])
    assert proc.graph.calls == [], "No graph writes expected when frames list is empty"


@pytest.mark.unit
def test_process_nominal_srl__sent_offset_applied_correctly():
    """Predicate index in doc must be sent_offset + predicate_index_in_sent."""
    proc = _make_processor()
    doc = _fake_doc("docOffset")

    response = {
        "words": ["The", "attack", "started"],
        "frames": [
            {
                "predicate": "attack",
                "predicate_index": 1,
                "sense": "attack.01",
                "sense_score": 0.92,
                "tags": ["O", "B-V", "O"],
            }
        ],
    }
    # Sentence starts at token 10 in the document
    proc.process_nominal_srl(doc, [(10, response)])

    frame_params = [p for _, p in proc.graph.calls if "framework" in p]
    assert frame_params
    # head_index = sent_offset(10) + pred_index_in_sent(1) = 11
    assert frame_params[0]["head_index"] == 11


@pytest.mark.unit
@pytest.mark.contract
def test_process_nominal_srl__contract_framework_value_is_nombank():
    """Hard contract: any Frame written by process_nominal_srl must have framework=NOMBANK."""
    proc = _make_processor()
    doc = _fake_doc("docContract")
    proc.process_nominal_srl(doc, [(0, NOMBANK_RESPONSE)])

    framework_values = [
        p["framework"] for _, p in proc.graph.calls if "framework" in p
    ]
    assert framework_values, "No framework values written"
    assert all(fw == "NOMBANK" for fw in framework_values), (
        f"Expected all NOMBANK, got: {framework_values}"
    )
