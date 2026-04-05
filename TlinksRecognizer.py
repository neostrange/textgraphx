"""TlinksRecognizer - lightweight TLINK heuristics with logging.

This module provides a small, well-structured class with a module-level
logger. Methods intentionally return lists (empty by default) so the
module can be imported and unit-tested without requiring a running Neo4j
instance.
"""

import logging
import sys
import os

# Allow running this file directly (python TlinksRecognizer.py) by adding
# repository root to sys.path so package-style imports resolve.
if __package__ is None and __name__ == '__main__':
    repo_root = os.path.dirname(os.path.dirname(__file__))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

from textgraphx.neo4j_client import make_graph_from_config
from textgraphx.timeml_relations import CANONICAL_TLINK_RELTYPES

logger = logging.getLogger(__name__)
logger.info("TlinksRecognizer module imported")


class TlinksRecognizer:
    """TLINK recognizer with simple, test-friendly methods.

    The real implementation runs Cypher queries via the graph driver. The
    simplified methods here log their invocation and return empty lists so
    they are safe during unit tests and CI runs.
    """

    def __init__(self, argv=None):
        self.graph = make_graph_from_config()
        logger.info("TlinksRecognizer initialized; graph session ready")

    def _run_query(self, query, parameters=None):
        """Run a Cypher query via the configured graph, log a short preview and row count.

        Returns the list from `.data()` or [] on error.
        """
        qshort = (query.strip().replace("\n", " ")[:200] + "...") if len(query) > 200 else query.strip()
        try:
            result = self.graph.run(query, parameters).data()
            logger.info("Executed query: %s; rows=%d", qshort, len(result))
            return result
        except Exception:
            logger.exception("Query failed: %s", qshort)
            return []

    def get_annotated_text(self):
        logger.debug("get_annotated_text")
        try:
            data = self.graph.run("MATCH (n:AnnotatedText) RETURN n.id").data()
            return [r.get('n.id') for r in data]
        except Exception:
            logger.exception("Failed to fetch annotated text ids; returning empty list")
            return []

    def create_tlinks_case1(self):
        logger.debug("create_tlinks_case1")
        query = """ MATCH p= (e1:TEvent)-[:FRAME_DESCRIBES_EVENT|DESCRIBES]-(f1:Frame)<-[:HAS_FRAME_ARGUMENT|PARTICIPANT]-(fa:FrameArgument where fa.type = 'ARGM-TMP')
                <-[:PARTICIPATES_IN]-(et:TagOccurrence where et.pos = 'VBD')-[:PARTICIPATES_IN]->(f2:Frame)-[:FRAME_DESCRIBES_EVENT|DESCRIBES]-(e2:TEvent)
                    where fa.headTokenIndex = et.tok_index_doc and fa.signal = 'after'
                    with *
                    match (e1),(e2)
                    merge (e1)-[tl:TLINK]-(e2)
                    on create set tl.relType = 'AFTER', tl.source = 't2g'
                    on match set tl.relType = 'AFTER'
                    RETURN p
        """
        return self._run_query(query)

    def create_tlinks_case2(self):
        logger.debug("create_tlinks_case2")
        query = """ MATCH p= (e1:TEvent)-[:FRAME_DESCRIBES_EVENT|DESCRIBES]-(f1:Frame)<-[:HAS_FRAME_ARGUMENT|PARTICIPANT]-(fa:FrameArgument where fa.type = 'ARGM-TMP')
                <-[:PARTICIPATES_IN]-(et:TagOccurrence where et.pos = 'VBG')-[:PARTICIPATES_IN]->(f2:Frame)-[:FRAME_DESCRIBES_EVENT|DESCRIBES]-(e2:TEvent)
                    where fa.complement = et.text and fa.syntacticType = 'EVENTIVE'
                    with *
                    merge (e1)-[tl:TLINK]-(e2)
                    with *
                    set tl.source = 't2g', (case when fa.signal in ['after'] then tl END).relType = 'AFTER',
                    (case when fa.signal in ['before'] then tl END).relType = 'BEFORE'
                    RETURN p
        """
        return self._run_query(query)

    def create_tlinks_case3(self):
        logger.debug("create_tlinks_case3")
        query = """ MATCH p= (e1:TEvent)-[:FRAME_DESCRIBES_EVENT|DESCRIBES]-(f1:Frame)<-[:HAS_FRAME_ARGUMENT|PARTICIPANT]-(fa:FrameArgument where fa.type = 'ARGM-TMP')
                <-[:PARTICIPATES_IN]-(et:TagOccurrence where et.pos = 'VBG')-[:PARTICIPATES_IN]->(f2:Frame)-[:FRAME_DESCRIBES_EVENT|DESCRIBES]-(e2:TEvent)
                    where fa.headTokenIndex = et.tok_index_doc and fa.syntacticType = 'EVENTIVE'
                    with *
                    merge (e1)-[tl:TLINK]-(e2)
                    with *
                    set tl.source = 't2g', 
                    (case when fa.signal in ['after'] then tl END).relType = 'AFTER',
                    (case when fa.signal in ['before'] then tl END).relType = 'BEFORE',
                    (case when fa.signal in ['following'] then tl END).relType = 'SIMULTANEOUS'
                    RETURN p
        """
        return self._run_query(query)

    def create_tlinks_case4(self):
        logger.debug("create_tlinks_case4")
        query = """ MATCH p = (t:TIMEX)<-[:TRIGGERS]-(h:TagOccurrence where h.pos in ['NN','NNP'])-[:PARTICIPATES_IN]->
            (fa:FrameArgument {type: 'ARGM-TMP'})-[:HAS_FRAME_ARGUMENT|PARTICIPANT]-(f:Frame)-[:FRAME_DESCRIBES_EVENT|DESCRIBES]->(e:TEvent)
                    WHERE fa.headTokenIndex = h.tok_index_doc
                    MERGE (e)-[tlink:TLINK]->(t)
                    SET tlink.source = 't2g', tlink.relType = 'IS_INCLUDED'
        """
        return self._run_query(query)

    def create_tlinks_case5(self):
        logger.debug("create_tlinks_case5")
        query = """ MATCH p = (t:TIMEX)<-[:TRIGGERS]-(pobj:TagOccurrence where pobj.pos in ['NN','NNP'])-[:PARTICIPATES_IN]->(fa:FrameArgument {type: 'ARGM-TMP', syntacticType: 'IN'})-[:HAS_FRAME_ARGUMENT|PARTICIPANT]-(f:Frame)-[:FRAME_DESCRIBES_EVENT|DESCRIBES]->(e:TEvent)
                    WHERE fa.complementIndex = pobj.tok_index_doc

                    MERGE (e)-[tlink:TLINK]->(t)
                    SET tlink.source = 't2g',
                    (CASE WHEN t.type = 'DURATION' and toLower(fa.head) = 'for' and e.tense in ['PAST', 'PRESENT'] THEN tlink END).relType = 'MEASURE',
                    (CASE WHEN t.type = 'DURATION' and toLower(fa.head) IN ['in', 'during'] THEN tlink END).relType = 'IS_INCLUDED',
                    (CASE WHEN t.type = 'DURATION' and t.quant <> 'N/A' and fa.head IN ['in'] THEN tlink END).relType = 'AFTER',
                    (CASE WHEN t.type = 'DURATION' and toLower(fa.head) IN ['for'] and e.tense in ['PAST', 'PRESENT'] and e.aspect = 'PERFECTIVE' THEN tlink END).relType = 'BEGUN_BY',
                    (CASE WHEN t.type = 'DATE' and toLower(fa.head) IN ['since'] THEN tlink END).relType = 'BEGUN_BY',
                    (CASE WHEN t.type = 'DURATION' and toLower(fa.head) IN ['in'] THEN tlink END).relType = 'AFTER',
                    (CASE WHEN t.type = 'DATE' and toLower(fa.head) IN ['by'] THEN tlink END).relType = 'ENDED_BY',
                    (CASE WHEN t.type = 'DATE' and toLower(fa.head) IN ['until'] and e.tense in ['PAST'] THEN tlink END).relType = 'ENDED_BY',
                    (CASE WHEN t.type = 'TIME' and toLower(fa.head) IN ['by'] THEN tlink END).relType = 'BEFORE',
                    (CASE WHEN t.type in ['TIME', 'DATE', 'DURATION'] and toLower(fa.head) IN ['before'] THEN tlink END).relType = 'BEFORE',
                    (CASE WHEN t.type in ['TIME', 'DATE', 'DURATION'] and toLower(fa.head) IN ['after'] THEN tlink END).relType = 'AFTER',
                    (CASE WHEN t.type in ['TIME', 'DATE', 'DURATION'] and toLower(fa.head) IN ['on'] THEN tlink END).relType = 'IS_INCLUDED',
                    //case added as per the observation during evaluation for 'in' e.g.,Temporal FA 'in the third quarter of this year' should be mentioned with 'IS_INCLUDED'
                    (CASE WHEN t.type in ['TIME', 'DATE', 'DURATION'] and toLower(fa.head) IN ['in'] THEN tlink END).relType = 'IS_INCLUDED',
                    (CASE WHEN t.type in ['TIME', 'DATE'] and toLower(fa.head) IN ['on'] THEN tlink END).relType = 'IS_INCLUDED'

                    //return p
                    //MERGE (e)-[tlink:TLINK]->(t)
                    //SET tlink.source = 't2g', tlink.relType = 'IS_INCLUDED'
        """
        return self._run_query(query)

    def create_tlinks_case6(self):
        logger.debug("create_tlinks_case6")
        query = """ MATCH p = (e:TEvent)<-[:TRIGGERS]-(t:TagOccurrence)<-[:HAS_TOKEN]-(s:Sentence)<-[:CONTAINS_SENTENCE]-(ann:AnnotatedText)-[:CREATED_ON]->(dct:TIMEX)
                    WHERE NOT (e.tense IN ['PRESPART', 'PASPART', 'INFINITIVE']) AND NOT (t.pos IN ['NNP', 'NNS', 'NN']) 
                    //AND NOT (e.tense IN ['PRESENT'] and e.aspect IN ['NONE'])
                    MERGE (e)-[tlink:TLINK]-(dct)
                    SET tlink.source = 't2g',
                    (CASE WHEN e.tense in ['FUTURE'] THEN tlink END).relType = 'AFTER',
                    (CASE WHEN e.tense in ['PRESENT'] and e.aspect = 'PROGRESSIVE' THEN tlink END).relType = 'IS_INCLUDED',
                    (CASE WHEN e.tense in ['PAST'] THEN tlink END).relType = 'IS_INCLUDED',
                    (CASE WHEN e.tense in ['PRESENT'] and e.aspect = 'PERFECTIVE' THEN tlink END).relType = 'BEFORE',
                    (CASE WHEN e.tense in ['PASTPART'] and e.aspect = 'NONE' THEN tlink END).relType = 'IS_INCLUDED'

                    RETURN p
        """
        return self._run_query(query)

    def normalize_tlink_reltypes(self):
        """Normalize TLINK relType values to canonical TimeML inventory.

        Keeps original values in `relTypeOriginal` and records canonical value
        in `relTypeCanonical` for auditability.
        """
        logger.debug("normalize_tlink_reltypes")
        query = """
        MATCH ()-[r:TLINK]-()
        WITH r, toUpper(coalesce(r.relType, '')) AS raw
        WITH r, raw,
             CASE
                WHEN raw IN $canonical THEN raw
                WHEN raw = 'INCLUDE' THEN 'INCLUDES'
                WHEN raw = 'INCLUDED' THEN 'IS_INCLUDED'
                WHEN raw = 'SIMULTANEOUSLY' THEN 'SIMULTANEOUS'
                WHEN raw = 'OVERLAP' THEN 'SIMULTANEOUS'
                WHEN raw = 'EQUAL' THEN 'IDENTITY'
                WHEN raw = 'SAMEAS' THEN 'IDENTITY'
                WHEN raw = 'MEASURE' THEN 'DURING'
                WHEN raw = '' THEN 'VAGUE'
                ELSE 'VAGUE'
             END AS canonical
        SET r.relTypeOriginal = coalesce(r.relTypeOriginal, r.relType),
            r.relTypeCanonical = canonical,
            r.relType = canonical
        RETURN count(r) AS normalized
        """
        rows = self._run_query(query, {"canonical": list(CANONICAL_TLINK_RELTYPES)})
        if rows:
            normalized = rows[0].get("normalized", 0)
            logger.info("normalize_tlink_reltypes: normalized %d TLINK relationships", normalized)
        return rows


if __name__ == '__main__':
    import time as _time
    tp = TlinksRecognizer(sys.argv[1:])
    _phase_start = _time.time()
    tp.create_tlinks_case1()
    tp.create_tlinks_case2()
    tp.create_tlinks_case3()
    tp.create_tlinks_case4()
    tp.create_tlinks_case5()
    tp.create_tlinks_case6()
    tp.normalize_tlink_reltypes()
    _phase_duration = _time.time() - _phase_start

    # Record a PhaseRun marker for restart visibility (Item 7)
    try:
        from textgraphx.phase_assertions import record_phase_run
        record_phase_run(
            tp.graph,
            phase_name="tlinks",
            duration_seconds=_phase_duration,
            metadata={
                "passes": "case1,case2,case3,case4,case5,case6"
            },
        )
    except Exception:
        import logging as _logging
        _logging.getLogger(__name__).exception(
            "Failed to write TLinksRun marker (non-fatal)"
        )

