"""Runtime contract tests for TemporalPhase doc_id consistency."""

import importlib
import sys
import types


class _FakeResult:
    def data(self):
        return []


class _FakeGraph:
    def __init__(self):
        self.calls = []

    def run(self, query, parameters=None):
        self.calls.append((query, parameters or {}))
        return _FakeResult()


def _mk_phase_with_graph(graph):
    temporal_phase_cls = _load_temporal_phase_class()
    phase = temporal_phase_cls.__new__(temporal_phase_cls)
    phase.graph = graph
    return phase


def _load_temporal_phase_class():
    if "spacy" not in sys.modules:
        fake_spacy = types.ModuleType("spacy")
        fake_tokens = types.ModuleType("spacy.tokens")
        fake_tokens.Doc = type("Doc", (), {})
        fake_tokens.Token = type("Token", (), {})
        fake_tokens.Span = type("Span", (), {})
        fake_spacy.tokens = fake_tokens
        sys.modules["spacy"] = fake_spacy
        sys.modules["spacy.tokens"] = fake_tokens

    module = importlib.import_module("textgraphx.TemporalPhase")
    return module.TemporalPhase


def test_create_tlinks_e2e_uses_integer_doc_id_in_merge_pattern():
    graph = _FakeGraph()
    phase = _mk_phase_with_graph(graph)
    phase._get_ttk_xml = lambda doc_id: (
        "<root><TLINK lid='l1' relType='BEFORE' eventInstanceID='ei1' "
        "relatedToEventInstance='ei2' signalID='s1'/></root>"
    )

    phase.create_tlinks_e2e("12")

    assert graph.calls, "expected query execution"
    query, params = graph.calls[0]
    assert "MERGE (e1:TEvent {eiid: $event_instance_id, doc_id: toInteger($doc_id)})" in query
    assert "MERGE (e2:TEvent {eiid: $related_event_instance, doc_id: toInteger($doc_id)})" in query
    assert "SET tl.signalID = $signal_id" in query
    assert params["doc_id"] == "12"
    assert params["event_instance_id"] == "ei1"
    assert params["related_event_instance"] == "ei2"


def test_create_tlinks_e2t_uses_integer_doc_id_in_merge_pattern():
    graph = _FakeGraph()
    phase = _mk_phase_with_graph(graph)
    phase._get_ttk_xml = lambda doc_id: (
        "<root><TLINK lid='l2' relType='IS_INCLUDED' eventInstanceID='ei9' "
        "relatedToTime='t2' signalID='s2'/></root>"
    )

    phase.create_tlinks_e2t("15")

    assert graph.calls, "expected query execution"
    query, params = graph.calls[0]
    assert "MERGE (e:TEvent {eiid: $event_instance_id, doc_id: toInteger($doc_id)})" in query
    assert "MERGE (t:TIMEX {tid: $related_to_time, doc_id: toInteger($doc_id)})" in query
    assert "SET tl.signalID = $signal_id" in query
    assert params["doc_id"] == "15"
    assert params["event_instance_id"] == "ei9"
    assert params["related_to_time"] == "t2"


def test_create_signals2_writes_temporal_signal_nodes_with_span_fields():
    graph = _FakeGraph()
    phase = _mk_phase_with_graph(graph)
    phase.get_doc_text_and_dct = lambda doc_id: {"text": "x", "dct": "2020-01-01T00:00:00"}
    phase.callTtkService = lambda payload: (
        "<root><tarsqi_tags><SIGNAL sid='s1' begin='0' end='5'>After</SIGNAL></tarsqi_tags></root>"
    )

    phase.create_signals2("8")

    assert graph.calls, "expected query execution"
    query, params = graph.calls[0]
    assert "MERGE (s:Signal" in query
    assert "s.start_char" in query
    assert "s.end_char" in query
    assert "s.start_tok" in query
    assert "s.end_tok" in query
    assert params["doc_id"] == "8"


def test_create_timexes2_writes_canonical_and_legacy_span_fields():
    graph = _FakeGraph()
    phase = _mk_phase_with_graph(graph)
    phase.get_doc_text_and_dct = lambda doc_id: {"text": "x", "dct": "2020-01-01T00:00:00"}
    phase.callHeidelTimeService = lambda payload: (
        "<root><TIMEX3 tid='t1' begin='10' end='20' type='DATE' value='20200101' "
        "functionInDocument='NONE' anchorTimeID='t0' beginPoint='t0' endPoint='t2'>"
        "Jan 1, 2020</TIMEX3></root>"
    )

    phase.create_timexes2("9")

    assert graph.calls, "expected query execution"
    query, params = graph.calls[0]
    assert "MERGE (t:TIMEX {tid: $tid, doc_id: toInteger($doc_id)})" in query
    assert "MERGE (tm:TimexMention {id: $mention_id, doc_id: toInteger($doc_id)})" in query
    assert "MERGE (tm)-[:REFERS_TO]->(t)" in query
    assert "start_char" in query
    assert "end_char" in query
    assert "start_tok" in query
    assert "end_tok" in query
    assert "start_index" in query
    assert "end_index" in query
    assert "functionInDocument" in query
    assert "anchorTimeID" in query
    assert "beginPoint" in query
    assert "endPoint" in query
    assert "MERGE (token)-[:TRIGGERS]->(tm)" in query
    assert params["doc_id"] == "9"
    assert params["tid"] == "t1"
    assert params["mention_id"] == "timexmention_9_t1"
    assert params["anchor_time_id"] == "t0"
    assert params["begin_point"] == "t0"
    assert params["end_point"] == "t2"


def test_create_tevents2_writes_canonical_and_legacy_span_fields():
    graph = _FakeGraph()
    phase = _mk_phase_with_graph(graph)
    phase.get_doc_text_and_dct = lambda doc_id: {"text": "x", "dct": "2020-01-01T00:00:00"}
    phase.callTtkService = lambda payload: (
        "<root><tarsqi_tags><EVENT eid='e1' eiid='ei1' begin='10' end='12' "
        "aspect='NONE' class='OCCURRENCE' epos='VERB' form='fell' pos='VERB' tense='PAST' polarity='POS' external_ref='ev:1'/></tarsqi_tags></root>"
    )

    phase.create_tevents2("10")

    assert graph.calls, "expected query execution"
    query, params = graph.calls[0]
    assert "event.start_char" in query
    assert "event.end_char" in query
    assert "event.start_tok" in query
    assert "event.end_tok" in query
    assert "event.begin" in query
    assert "event.end" in query
    assert "event.polarity =" in query
    assert "event.modality =" in query
    assert "event.external_ref =" in query
    assert params["doc_id"] == "10"
    assert params["external_ref"] == "ev:1"


def test_create_dct_node_marks_document_creation_time():
    graph = _FakeGraph()
    phase = _mk_phase_with_graph(graph)

    phase.create_DCT_node("3")

    assert graph.calls, "expected query execution"
    query, params = graph.calls[0]
    assert "DCT.functionInDocument = 'CREATION_TIME'" in query
    assert "MERGE (a)-[:CREATED_ON]->(DCT)" in query
    assert "TimexMention" not in query
    assert "TRIGGERS" not in query
    assert params["doc_id"] == "3"
