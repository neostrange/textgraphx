"""Runtime contract tests for span fields in non-temporal writers."""

from types import SimpleNamespace

from textgraphx.text_processing_components.SRLProcessor import SRLProcessor
from textgraphx.text_processing_components.EntityExtractor import EntityExtractor
from textgraphx.text_processing_components.EntityProcessor import EntityProcessor
from textgraphx.text_processing_components.CoreferenceResolver import CoreferenceResolver
from textgraphx.text_processing_components.NounChunkProcessor import NounChunkProcessor
from textgraphx.RefinementPhase import RefinementPhase
from textgraphx.utils.id_utils import make_coref_uid, make_entity_mention_uid, make_ne_uid


class _FakeGraph:
    def __init__(self):
        self.calls = []
        self.results = []

    def run(self, query, params=None):
        self.calls.append((query, params or {}))
        result = self.results.pop(0) if self.results else []
        return SimpleNamespace(data=lambda: result)


class _FakeRepo:
    def __init__(self):
        self.calls = []

    def execute_query(self, query, params):
        self.calls.append((query, params))
        return []


def test_srl_frame_writer_sets_canonical_and_legacy_token_span_fields():
    graph = _FakeGraph()
    srl = SRLProcessor.__new__(SRLProcessor)
    srl.graph = graph

    frame_id = srl._merge_frame(doc_id=1, start=3, end=8, headword="run", head_index=5, text="ran quickly")

    assert frame_id == "frame_1_3_8"
    assert graph.calls, "expected frame merge query"
    query, params = graph.calls[0]
    assert "f.start_tok = $start" in query
    assert "f.end_tok = $end" in query
    assert "f.startIndex = $start" in query
    assert "f.endIndex = $end" in query
    assert "f.framework = 'PROPBANK'" in query
    assert params["start"] == 3
    assert params["end"] == 8


def test_srl_frame_argument_writer_sets_canonical_and_legacy_token_span_fields():
    graph = _FakeGraph()
    srl = SRLProcessor.__new__(SRLProcessor)
    srl.graph = graph

    arg_id = srl._merge_frame_argument(doc_id=1, start=4, end=6, head="market", head_index=5, arg_type="ARG1", text="the market")

    assert arg_id == "fa_1_4_6_ARG1"
    assert graph.calls, "expected frame-argument merge query"
    query, params = graph.calls[0]
    assert "a.start_tok = $start" in query
    assert "a.end_tok = $end" in query
    assert "a.startIndex = $start" in query
    assert "a.endIndex = $end" in query
    assert params["start"] == 4
    assert params["end"] == 6


def test_named_entity_writer_sets_canonical_and_legacy_token_span_fields():
    repo = _FakeRepo()
    processor = EntityProcessor(repo)

    nes = [{
        "value": "Bank",
        "type": "ORG",
        "start_index": 2,
        "end_index": 4,
        "start_char": 10,
        "end_char": 14,
        "head": "Bank",
        "head_token_index": 4,
        "syntactic_type": "NAM",
    }]
    processor.store_entities(document_id=1, nes=nes)

    assert repo.calls, "expected entity merge query"
    query, params = repo.calls[0]
    assert "ne.start_tok = item.start_index" in query
    assert "ne.end_tok = item.end_index" in query
    assert "ne.start_char = item.start_char" in query
    assert "ne.end_char = item.end_char" in query
    assert "ne.head = item.head" in query
    assert "ne.headTokenIndex = item.head_token_index" in query
    assert "ne.syntacticType = item.legacy_syntactic_type" in query
    assert "ne.syntactic_type = item.syntactic_type" in query
    assert "ne.index = item.start_index" in query
    assert "ne.end_index = item.end_index" in query
    assert params["documentId"] == 1


def test_coreference_writer_sets_canonical_and_legacy_token_span_fields():
    graph = _FakeGraph()
    resolver = CoreferenceResolver.__new__(CoreferenceResolver)
    resolver.graph = graph

    node_id = resolver.create_node(
        node_type="Antecedent",
        text="the company",
        start_index=7,
        end_index=9,
        doc_id=3,
    )

    assert node_id == "Antecedent_3_7_9"
    assert graph.calls, "expected coreference merge query"
    query, params = graph.calls[0]
    assert "n.uid = $node_uid" in query
    assert "n.start_tok = $start" in query
    assert "n.end_tok = $end" in query
    assert "n.startIndex = $start" in query
    assert "n.endIndex = $end" in query
    assert params["node_uid"] == make_coref_uid(3, "the company", 7, "Antecedent")
    assert params["start"] == 7
    assert params["end"] == 9


def test_coreference_writer_reuses_named_entity_for_exact_span_mentions():
    graph = _FakeGraph()
    graph.results = [[{"node_id": "1_4_6_ORG"}], []]
    resolver = CoreferenceResolver.__new__(CoreferenceResolver)
    resolver.graph = graph

    node_id = resolver.create_node(
        node_type="CorefMention",
        text="the bank",
        start_index=4,
        end_index=6,
        doc_id=1,
    )

    assert node_id == "1_4_6_ORG"
    assert len(graph.calls) == 2
    lookup_query, lookup_params = graph.calls[0]
    assert "MATCH (:AnnotatedText {id: $doc_id})" in lookup_query
    assert lookup_params["start"] == 4
    assert lookup_params["end"] == 6
    merge_query, merge_params = graph.calls[1]
    assert "SET ne:CorefMention" in merge_query
    assert "ne.uid = coalesce(ne.uid, $node_uid)" in merge_query
    assert merge_params["node_id"] == "1_4_6_ORG"
    assert merge_params["node_uid"] == make_coref_uid(1, "the bank", 4, "CorefMention")


def test_entity_mention_uid_helper_uses_hashed_source_namespaced_contract():
    uid = make_entity_mention_uid(doc_id=9, value="The Market", head_token_index=12, source="fa")

    assert uid.startswith("em_9_")
    assert uid == make_entity_mention_uid(doc_id=9, value="the  market", head_token_index=12, source="fa")
    assert uid != make_entity_mention_uid(doc_id=9, value="The Market", head_token_index=12, source="nc")


def test_refinement_frame_argument_materializer_uses_helper_derived_entity_mention_uid():
    graph = _FakeGraph()
    graph.results = [[{
        "entity_id": "entity_1",
        "source_frame_argument_id": "fa_9_12_14_ARG1",
        "doc_id": 9,
        "value": "The Market",
        "head": "Market",
        "headTokenIndex": 12,
        "start_tok": 12,
        "end_tok": 14,
        "start_char": 30,
        "end_char": 40,
        "mention_id": "nom_mention_fa_9_12_14",
    }], [{"mentions_materialized": 1}]]
    phase = RefinementPhase.__new__(RefinementPhase)
    phase.graph = graph

    phase.materialize_nominal_mentions_from_frame_arguments()

    assert len(graph.calls) == 2
    merge_query, merge_params = graph.calls[1]
    assert "UNWIND $rows AS row" in merge_query
    row = merge_params["rows"][0]
    assert row["mention_uid"] == make_entity_mention_uid(9, "The Market", 12, "fa")
    assert row["source_node_id"] == "fa_9_12_14_ARG1"


def test_noun_chunk_writer_sets_canonical_and_legacy_token_span_fields():
    repo = _FakeRepo()
    processor = NounChunkProcessor(repo)

    ncs = [{
        "value": "stock market",
        "type": "NOUN_CHUNK",
        "start_index": 1,
        "end_index": 2,
        "start_char": 3,
        "end_char": 15,
        "head": "market",
        "head_token_index": 2,
        "syntactic_type": "NOMINAL",
    }]
    processor.store_noun_chunks(document_id=1, ncs=ncs)

    assert repo.calls, "expected noun chunk merge query"
    query, params = repo.calls[0]
    assert "nc.start_tok = item.start_index" in query
    assert "nc.end_tok = item.end_index" in query
    assert "nc.start_char = item.start_char" in query
    assert "nc.end_char = item.end_char" in query
    assert "nc.head = item.head" in query
    assert "nc.headTokenIndex = item.head_token_index" in query
    assert "nc.syntacticType = item.syntactic_type" in query
    assert "nc.syntactic_type = item.syntactic_type" in query
    assert "nc.index = item.start_index" in query
    assert params["documentId"] == 1


def test_noun_chunk_writer_dual_writes_participation_and_in_mention_edges():
    repo = _FakeRepo()
    processor = NounChunkProcessor(repo)

    ncs = [{
        "value": "market",
        "type": "NOUN_CHUNK",
        "start_index": 2,
        "end_index": 2,
        "start_char": 5,
        "end_char": 11,
        "head": "market",
        "head_token_index": 2,
        "syntactic_type": "NOMINAL",
    }]
    processor.store_noun_chunks(document_id=4, ncs=ncs)

    query, _ = repo.calls[0]
    assert "MERGE (nc)<-[:PARTICIPATES_IN]-(tagOccurrence)" in query
    assert "MERGE (nc)<-[:IN_MENTION]-(tagOccurrence)" in query


def test_coreference_writer_dual_writes_participation_and_in_mention_edges():
    graph = _FakeGraph()
    resolver = CoreferenceResolver.__new__(CoreferenceResolver)
    resolver.graph = graph

    resolver.connect_node_to_tag_occurrences(node_id="CorefMention_1_1_1", index_range=[1], doc_id=1)

    query, params = graph.calls[0]
    assert "MERGE (x)-[:PARTICIPATES_IN]->(n)" in query
    assert "MERGE (x)-[:IN_MENTION]->(n)" in query
    assert params["doc_id"] == 1


def test_entity_processor_syntactic_type_prefers_valid_upstream_meantime_type():
    assert EntityProcessor._syntactic_type_from_tag("NN", raw_type="app") == "APP"
    assert EntityProcessor._syntactic_type_from_tag("NN", raw_type="NOMINAL") == "NOM"


def test_entity_processor_syntactic_type_uses_dependency_rules_for_missing_categories():
    assert EntityProcessor._syntactic_type_from_tag("NN", dep="appos") == "APP"
    assert EntityProcessor._syntactic_type_from_tag("NN", dep="conj") == "CONJ"
    assert EntityProcessor._syntactic_type_from_tag("NN", dep="acl:relcl") == "ARC"
    assert EntityProcessor._syntactic_type_from_tag("NN", dep="det") == "PTV"
    assert EntityProcessor._syntactic_type_from_tag("NN", dep="attr") == "PRE"


def test_entity_processor_syntactic_type_falls_back_to_meantime_core_tags():
    assert EntityProcessor._syntactic_type_from_tag("NN") == "NOM"
    assert EntityProcessor._syntactic_type_from_tag("NNP") == "NAM"
    assert EntityProcessor._syntactic_type_from_tag("PRP") == "PRO"
    assert EntityProcessor._syntactic_type_from_tag("RB") == "NOM"


def test_entity_processor_legacy_syntactic_type_retains_nominal_compatibility():
    assert EntityProcessor._legacy_syntactic_type("NOM") == "NOMINAL"
    assert EntityProcessor._legacy_syntactic_type("NAM") == "NAM"


def test_named_entity_writer_sets_token_id_independently_from_id():
    """B3: token_id must be set from its own span-based computation, not aliased
    to item.id, so that a future NEL pass can update id without stomping
    the original span-based stable identifier."""
    repo = _FakeRepo()
    processor = EntityProcessor(repo)

    nes = [{
        "value": "Apple",
        "type": "ORG",
        "start_index": 5,
        "end_index": 7,
        "start_char": 20,
        "end_char": 25,
        "head": "Apple",
        "head_token_index": 6,
        "syntactic_type": "NAM",
    }]
    processor.store_entities(document_id=2, nes=nes)

    ne = nes[0]
    # Both id and token_id are set in Python before the Cypher call.
    assert "id" in ne
    assert "token_id" in ne
    # token_id now uses a type-agnostic format (<doc>_<start>_<end>) so it is
    # stable across type corrections, unlike id (<doc>_<start>_<end>_<type>).
    assert ne["token_id"] != ne["id"], (
        "token_id must be type-agnostic and therefore differ from id"
    )
    assert ne["token_id"] == "2_5_7", (
        "token_id must preserve document+span identity only"
    )

    # Verify the Cypher writer references item.token_id (not item.id) for ne.token_id.
    query, _ = repo.calls[0]
    assert "ne.token_id = item.token_id" in query, (
        "Cypher must write ne.token_id from item.token_id so the span identity "
        "key is independent of the MERGE key (id)"
    )
    assert "ne.token_id = item.id" not in query, (
        "ne.token_id must NOT be aliased to item.id in the Cypher"
    )


def test_named_entity_writer_reconciles_stale_nodes_after_reextract_batch():
    repo = _FakeRepo()
    processor = EntityProcessor(repo)

    nes = [{
        "value": "Apple",
        "type": "ORG",
        "start_index": 5,
        "end_index": 7,
        "start_char": 20,
        "end_char": 25,
        "head": "Apple",
        "head_token_index": 6,
        "syntactic_type": "NAM",
    }]
    processor.store_entities(document_id=2, nes=nes)

    # Query sequence:
    # 0: MERGE/SET current entities and mention edges
    # 1: clear stale marker for current uids
    # 2: mark unseen entities stale + retire mention edges
    assert len(repo.calls) >= 3

    clear_query, clear_params = repo.calls[1]
    assert "UNWIND $current_uids AS uid" in clear_query
    assert "SET ne.stale = false" in clear_query
    assert len(clear_params["current_uids"]) == 1
    assert clear_params["current_uids"][0].startswith("ne_2_")

    stale_query, stale_params = repo.calls[2]
    assert "WHERE NOT coalesce(ne.uid, '') IN $current_uids" in stale_query
    assert "SET ne.stale = true" in stale_query
    assert "OPTIONAL MATCH (:TagOccurrence)-[r:IN_MENTION|PARTICIPATES_IN]->(ne)" in stale_query
    assert "OPTIONAL MATCH (ne)-[rr:REFERS_TO]->(:Entity)" in stale_query
    assert stale_params["documentId"] == 2


def test_entity_extractor_uses_head_token_index_for_uid_generation():
    repo = _FakeRepo()
    extractor = EntityExtractor.__new__(EntityExtractor)
    extractor.neo4j_repo = repo
    extractor.fetch_named_entities = lambda _document_id: []

    extractor.integrate_entities_into_db(
        entities=[{
            "start": 3,
            "end": 6,
            "label": "ORG",
            "text": "Central Bank",
            "head_token_index": 5,
        }],
        text_id=7,
    )

    create_query, create_params = repo.calls[0]
    assert "MERGE (ne:NamedEntity {uid: $uid})" in create_query
    assert create_params["uid"] == make_ne_uid(7, "Central Bank", 5)


def test_entity_extractor_uid_fallback_uses_start_index_not_end_boundary():
    repo = _FakeRepo()
    extractor = EntityExtractor.__new__(EntityExtractor)
    extractor.neo4j_repo = repo
    extractor.fetch_named_entities = lambda _document_id: [{"ne": {"id": "9_2_4_ORG", "index": 2, "end_index": 5}}]

    extractor.integrate_entities_into_db(
        entities=[{
            "start": 2,
            "end": 5,
            "label": "ORG",
            "text": "Market Watch",
        }],
        text_id=9,
    )

    _, uid_backfill_params = repo.calls[1]
    expected_uid = make_ne_uid(9, "Market Watch", 2)
    boundary_uid = make_ne_uid(9, "Market Watch", 4)
    assert uid_backfill_params["uid"] == expected_uid
    assert uid_backfill_params["uid"] != boundary_uid
