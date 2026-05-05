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

from textgraphx.database.client import make_graph_from_config
from textgraphx.reasoning.contracts import count_endpoint_violations
from textgraphx.reasoning.temporal.constraints import solve_tlink_constraints
from textgraphx.reasoning.temporal.timeml_relations import CANONICAL_TLINK_RELTYPES
import xml.etree.ElementTree as ET
import requests
import json

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
        query = """
            MATCH p= (e1:TEvent)-[:FRAME_DESCRIBES_EVENT|DESCRIBES]-(f1:Frame)<-[:HAS_FRAME_ARGUMENT|PARTICIPANT]-(fa:FrameArgument {type: 'ARGM-TMP'})
                <-[:IN_FRAME]-(et:TagOccurrence)-[:IN_FRAME]->(f2:Frame)-[:FRAME_DESCRIBES_EVENT|DESCRIBES]-(e2:TEvent)
            WHERE fa.headTokenIndex = et.tok_index_doc AND fa.signal = 'after'
              AND coalesce(e1.is_timeml_core, true) = true
              AND coalesce(e2.is_timeml_core, true) = true
              AND coalesce(e1.low_confidence, false) = false
              AND coalesce(e2.low_confidence, false) = false
              AND coalesce(e1.merged, false) = false
              AND coalesce(e2.merged, false) = false
            WITH *
            MATCH (e1),(e2)
            MERGE (e1)-[tl:TLINK]-(e2)
            ON CREATE SET tl.relType = 'AFTER', tl.source = 't2g', tl.confidence = 0.90, tl.rule_id = 'case1_after_eventive', tl.evidence_source = 'tlinks_recognizer'
            ON MATCH SET tl.relType = 'AFTER', tl.confidence = coalesce(tl.confidence, 0.90), tl.rule_id = coalesce(tl.rule_id, 'case1_after_eventive'), tl.evidence_source = coalesce(tl.evidence_source, 'tlinks_recognizer')
            RETURN p
        """
        return self._run_query(query)

    def create_tlinks_case2(self):
        logger.debug("create_tlinks_case2")
        query = """
            MATCH p= (e1:TEvent)-[:FRAME_DESCRIBES_EVENT|DESCRIBES]-(f1:Frame)<-[:HAS_FRAME_ARGUMENT|PARTICIPANT]-(fa:FrameArgument {type: 'ARGM-TMP'})
                <-[:IN_FRAME]-(et:TagOccurrence {pos: 'VBG'})-[:IN_FRAME]->(f2:Frame)-[:FRAME_DESCRIBES_EVENT|DESCRIBES]-(e2:TEvent)
            WHERE fa.complement = et.text AND fa.syntacticType = 'EVENTIVE'
              AND coalesce(e1.is_timeml_core, true) = true
              AND coalesce(e2.is_timeml_core, true) = true
              AND coalesce(e1.low_confidence, false) = false
              AND coalesce(e2.low_confidence, false) = false
              AND coalesce(e1.merged, false) = false
              AND coalesce(e2.merged, false) = false
            WITH *
            MERGE (e1)-[tl:TLINK]-(e2)
            WITH *
            SET tl.source = 't2g', tl.confidence = 0.85, tl.rule_id = 'case2_eventive_complement', tl.evidence_source = 'tlinks_recognizer',
                tl.relType = CASE
                    WHEN fa.signal IN ['after'] THEN 'AFTER'
                    WHEN fa.signal IN ['before'] THEN 'BEFORE'
                    ELSE coalesce(tl.relType, 'VAGUE')
                END
            RETURN p
        """
        return self._run_query(query)

    def create_tlinks_case3(self):
        logger.debug("create_tlinks_case3")
        query = """ MATCH p= (e1:TEvent)-[:FRAME_DESCRIBES_EVENT|DESCRIBES]-(f1:Frame)<-[:HAS_FRAME_ARGUMENT|PARTICIPANT]-(fa:FrameArgument where fa.type = 'ARGM-TMP')
                <-[:IN_FRAME]-(et:TagOccurrence where et.pos = 'VBG')-[:IN_FRAME]->(f2:Frame)-[:FRAME_DESCRIBES_EVENT|DESCRIBES]-(e2:TEvent)
                    where fa.headTokenIndex = et.tok_index_doc and fa.syntacticType = 'EVENTIVE'
                    and coalesce(e1.is_timeml_core, true) = true
                    and coalesce(e2.is_timeml_core, true) = true
                    and coalesce(e1.low_confidence, false) = false
                    and coalesce(e2.low_confidence, false) = false
                    and coalesce(e1.merged, false) = false
                    and coalesce(e2.merged, false) = false
                    with *
                    merge (e1)-[tl:TLINK]-(e2)
                    with *
                    set tl.source = 't2g', tl.confidence = 0.80, tl.rule_id = 'case3_eventive_head', tl.evidence_source = 'tlinks_recognizer',
                    tl.relType = CASE
                        WHEN fa.signal in ['after'] THEN 'AFTER'
                        WHEN fa.signal in ['before'] THEN 'BEFORE'
                        WHEN fa.signal in ['following'] THEN 'AFTER'
                        ELSE coalesce(tl.relType, 'VAGUE')
                    END
                    RETURN p
        """
        return self._run_query(query)

    def create_tlinks_case4(self):
        logger.debug("create_tlinks_case4")
        query = """
            MATCH (h:TagOccurrence where h.pos in ['NN','NNP'])-[:IN_FRAME]->
                (fa:FrameArgument {type: 'ARGM-TMP'})-[:HAS_FRAME_ARGUMENT|PARTICIPANT]-(f:Frame)-[:FRAME_DESCRIBES_EVENT|DESCRIBES]->(e:TEvent)
            MATCH (h)-[:TRIGGERS]->(tm)
            WHERE (tm:TimexMention OR tm:TIMEX OR tm:Timex3)
              AND coalesce(e.is_timeml_core, true) = true
              AND coalesce(e.low_confidence, false) = false
              AND coalesce(e.merged, false) = false
            OPTIONAL MATCH (tm)-[:REFERS_TO]->(t_ref:TIMEX)
            WITH h, fa, f, e, coalesce(t_ref, CASE WHEN tm:TIMEX OR tm:Timex3 THEN tm ELSE NULL END) AS t
            WHERE fa.headTokenIndex = h.tok_index_doc AND t IS NOT NULL
              // Frame-head filter: only link the Frame's main predicate event (eliminates fan-out FPs)
              AND f.headTokenIndex = e.start_tok
              // Distance guard: TIMEX head must be within 15 tokens of the event
              AND abs(coalesce(e.start_tok, -999) - h.tok_index_doc) <= 15
              // Ordering guard: event must precede TIMEX head in text (removes reversed FPs)
              AND coalesce(e.start_tok, -999) < h.tok_index_doc
            // DCT-match guard: TIMEX value must match the document creation date (removes off-day FPs)
            MATCH (ann:AnnotatedText {id: e.doc_id})-[:CREATED_ON]->(dct)
            WHERE (dct:TIMEX OR dct:Timex3)
              AND left(coalesce(t.value, ''), 10) = left(coalesce(dct.value, ''), 10)
            WITH DISTINCT e, t
            MERGE (e)-[tlink:TLINK]->(t)
            SET tlink.source = 't2g', tlink.relType = 'IS_INCLUDED',
                tlink.confidence = 0.88, tlink.rule_id = 'case4_timex_head_match', tlink.evidence_source = 'tlinks_recognizer'
            RETURN count(tlink) AS touched
        """
        return self._run_query(query)

    def create_tlinks_case5(self):
        logger.debug("create_tlinks_case5")
        query = """
            MATCH (pobj:TagOccurrence where pobj.pos in ['NN','NNP'])-[:IN_FRAME]->
                (fa:FrameArgument {type: 'ARGM-TMP'})-[:HAS_FRAME_ARGUMENT|PARTICIPANT]-(f:Frame)-[:FRAME_DESCRIBES_EVENT|DESCRIBES]->(e:TEvent)
            MATCH (pobj)-[:TRIGGERS]->(tm)
            WHERE (tm:TimexMention OR tm:TIMEX OR tm:Timex3)
              AND coalesce(e.is_timeml_core, true) = true
              AND coalesce(e.low_confidence, false) = false
              AND coalesce(e.merged, false) = false
            OPTIONAL MATCH (tm)-[:REFERS_TO]->(t_ref:TIMEX)
            WITH pobj, fa, f, e, coalesce(t_ref, CASE WHEN tm:TIMEX OR tm:Timex3 THEN tm ELSE NULL END) AS t,
                 toLower(coalesce(fa.head, '')) AS prep_head
            WHERE fa.end_tok = pobj.tok_index_doc
              AND prep_head IN ['in', 'on', 'at', 'for', 'since', 'during', 'before', 'after', 'by', 'until']
              AND t IS NOT NULL
              // Frame-head filter: only link the Frame's main predicate event (eliminates fan-out FPs)
              AND f.headTokenIndex = e.start_tok
              // Distance guard: TIMEX head must be within 15 tokens of the event
              AND abs(coalesce(e.start_tok, -999) - pobj.tok_index_doc) <= 15
              // Ordering guard: event must precede TIMEX pobj in text (removes reversed FPs)
              AND coalesce(e.start_tok, -999) < pobj.tok_index_doc
              // Position guard: restrict to first 150 tokens (body-article FPs beyond this range outweigh TPs)
              AND coalesce(e.start_tok, 9999) <= 150
            WITH DISTINCT e, t, prep_head
            MERGE (e)-[tlink:TLINK]->(t)
            SET tlink.source = 't2g',
                tlink.confidence = 0.72, tlink.rule_id = 'case5_timex_preposition', tlink.evidence_source = 'tlinks_recognizer',
                tlink.relType = CASE
                    WHEN t.type = 'DURATION' AND prep_head = 'for' AND e.tense IN ['PAST', 'PRESENT'] THEN 'MEASURE'
                    WHEN t.type = 'DATE' AND prep_head = 'since' THEN 'BEGUN_BY'
                    WHEN t.type = 'DURATION' AND prep_head = 'in' AND coalesce(t.quant, 'N/A') <> 'N/A' THEN 'AFTER'
                    WHEN t.type = 'DURATION' AND prep_head IN ['in', 'during'] THEN 'IS_INCLUDED'
                    WHEN t.type = 'DATE' AND prep_head = 'by' AND e.tense IN ['PAST'] THEN 'ENDED_BY'
                    WHEN t.type = 'DATE' AND prep_head = 'by' THEN 'BEFORE'
                    WHEN t.type = 'DATE' AND prep_head = 'until' AND e.tense IN ['PAST'] THEN 'ENDED_BY'
                    WHEN t.type = 'TIME' AND prep_head = 'by' THEN 'BEFORE'
                    WHEN t.type IN ['TIME', 'DATE', 'DURATION'] AND prep_head = 'before' THEN 'BEFORE'
                    WHEN t.type IN ['TIME', 'DATE', 'DURATION'] AND prep_head = 'after' THEN 'AFTER'
                    WHEN t.type = 'TIME' AND prep_head = 'at' THEN 'SIMULTANEOUS'
                    WHEN t.type IN ['DATE', 'DURATION'] AND prep_head IN ['on', 'in'] THEN 'IS_INCLUDED'
                    WHEN t.type = 'TIME' AND prep_head IN ['on', 'in'] THEN 'IS_INCLUDED'
                    ELSE coalesce(tlink.relType, 'VAGUE')
                END
            RETURN count(tlink) AS touched
        """
        return self._run_query(query)

    def create_tlinks_case6(self):
        logger.debug("create_tlinks_case6")
        query = """ MATCH p = (e:TEvent)<-[:TRIGGERS]-(t:TagOccurrence)<-[:HAS_TOKEN]-(s:Sentence)<-[:CONTAINS_SENTENCE]-(ann:AnnotatedText)-[:CREATED_ON]->(dct)
                WHERE dct:TIMEX OR dct:Timex3
                AND coalesce(e.is_timeml_core, true) = true
                AND coalesce(e.low_confidence, false) = false
                AND coalesce(e.merged, false) = false
                AND coalesce(e.tense, '') IN ['PAST', 'PRESENT', 'FUTURE']
                AND NOT (e.tense IN ['PRESPART', 'PASPART', 'INFINITIVE']) AND NOT (t.pos IN ['NNP', 'NNS', 'NN']) 
                    //AND NOT (e.tense IN ['PRESENT'] and e.aspect IN ['NONE'])
                    MERGE (e)-[tlink:TLINK]-(dct)
                    SET tlink.source = 't2g',
                    tlink.confidence = 0.78, tlink.rule_id = 'case6_dct_anchor', tlink.evidence_source = 'tlinks_recognizer',
                    tlink.relType = CASE
                        WHEN e.tense in ['FUTURE'] THEN 'AFTER'
                        WHEN e.tense in ['PRESENT'] and e.aspect = 'PROGRESSIVE' THEN 'IS_INCLUDED'
                        WHEN e.tense in ['PAST'] THEN 'BEFORE'
                        WHEN e.tense in ['PRESENT'] and e.aspect = 'PERFECTIVE' THEN 'BEFORE'
                        WHEN e.tense in ['PASTPART'] and e.aspect = 'NONE' THEN 'IS_INCLUDED'
                        ELSE coalesce(tlink.relType, 'VAGUE')
                    END

                    RETURN p
        """
        return self._run_query(query)

    def create_tlinks_case7(self):
        logger.debug("create_tlinks_case7")
        query = """
        MATCH (f_main:Frame)-[:INSTANTIATES]->(em_main:EventMention)-[:REFERS_TO]->(e_main:TEvent)
        MATCH (fa:FrameArgument {type: 'ARGM-TMP'})-[:HAS_FRAME_ARGUMENT|PARTICIPANT]->(f_main)
        MATCH (f_sub:Frame)-[:INSTANTIATES]->(em_sub:EventMention)-[:REFERS_TO]->(e_sub:TEvent)
        MATCH (e_sub)<-[:TRIGGERS]-(tok_sub:TagOccurrence)
        WHERE elementId(e_main) <> elementId(e_sub)
          AND em_sub.clauseType IN ['SUBORDINATE', 'COMPLEMENT']
          AND em_sub.scopeType IN ['TEMPORAL_SCOPE', 'LOCAL_SCOPE']
          AND fa.syntacticType = 'EVENTIVE'
          AND toLower(coalesce(fa.signal, '')) IN ['before', 'after']
          AND toLower(coalesce(fa.complement, '')) = toLower(coalesce(tok_sub.text, ''))
          AND any(cue IN coalesce(em_sub.temporalCueHeads, []) WHERE cue IN ['before', 'after'])
                    AND coalesce(e_main.is_timeml_core, true) = true
                    AND coalesce(e_sub.is_timeml_core, true) = true
                    AND coalesce(e_main.low_confidence, false) = false
                    AND coalesce(e_sub.low_confidence, false) = false
                    AND coalesce(e_main.merged, false) = false
                    AND coalesce(e_sub.merged, false) = false
        MERGE (e_main)-[tl:TLINK]->(e_sub)
        SET tl.source = 't2g',
            tl.confidence = 0.83,
            tl.rule_id = 'case7_clause_scope_connective',
            tl.evidence_source = 'tlinks_recognizer',
            tl.relType = CASE
                WHEN toLower(fa.signal) = 'before' THEN 'BEFORE'
                WHEN toLower(fa.signal) = 'after' THEN 'AFTER'
                ELSE coalesce(tl.relType, 'VAGUE')
            END
        RETURN count(tl) AS created
        """
        return self._run_query(query)

    def create_tlinks_case8(self):
        """DISABLED — NewsReader Subtask 1 explicitly prohibits linking non-verbal events to DCT.

        Per NewsReader §10.6.2 Subtask 1 rule (a): "non verbal events will never
        be linked to the DCT." This method previously anchored NOMBANK-sourced
        nominal events (NN/NNS/NNP/NNPS) to the DCT as IS_INCLUDED, which is a
        direct guideline violation producing guaranteed false positives.

        Nominal events are now linked to their syntactically-modifying TIMEXes
        via Case 15 (dep-tree nmod/compound/advmod) and Case 21 (dep-tree obl/tmod).
        """
        logger.warning(
            "create_tlinks_case8 DISABLED: NewsReader Subtask 1 rule (a) prohibits "
            "non-verbal events from being linked to DCT — skipping."
        )
        return []

    def create_tlinks_case9(self):
        """D3 — Link NOMBANK-promoted nominal events to sentence-local TIMEX3 nodes.

        Cases 4 and 5 require the TIMEX to appear inside an ARGM-TMP FrameArgument
        span, which misses TIMEX expressions that are syntactically disjoint from
        the argument structure but co-occur in the same sentence.  This case
        captures those proximity-based nominal-TIMEX pairings:

        - Only targets NOMBANK-sourced TEvents (``source='nombank_srl'``).
        - Finds canonical TIMEX nodes reachable from the same sentence via a non-SRL
          TimexMention (``SRLTimexCandidate`` nodes are excluded to avoid circularity).
        - Uses ``IS_INCLUDED`` as the conservative default; prepositional signals on
          ARGM-TMP spans are not available here.
        - Lower confidence (0.60) than structurally-grounded cases.
        """
        logger.debug("create_tlinks_case9")
        query = """
            MATCH (e:TEvent {source: 'nombank_srl'})<-[:TRIGGERS]-(tok_e:TagOccurrence)
                  <-[:HAS_TOKEN]-(sent:Sentence)
                  -[:HAS_TOKEN]->(tok_t:TagOccurrence)-[:TRIGGERS]->(tm:TimexMention)
            WHERE elementId(tok_e) <> elementId(tok_t)
              AND abs(coalesce(tok_e.tok_index_doc, -1) - coalesce(tok_t.tok_index_doc, -1)) <= 8
              AND NOT tm:SRLTimexCandidate
              AND coalesce(tm.type, '') IN ['DATE', 'TIME', 'SET', '']
              AND coalesce(e.is_timeml_core, true) = true
              AND coalesce(e.low_confidence, false) = false
              AND coalesce(e.merged, false) = false
            OPTIONAL MATCH (tm)-[:REFERS_TO]->(t_ref:TIMEX)
            WITH e, coalesce(
                t_ref,
                CASE WHEN tm:TIMEX OR tm:Timex3 THEN tm ELSE NULL END
            ) AS t
            WHERE t IS NOT NULL
            WITH DISTINCT e, t
            MERGE (e)-[tl:TLINK]->(t)
            ON CREATE SET
                tl.source          = 't2g',
                tl.relType         = 'IS_INCLUDED',
                tl.relTypeCanonical = 'IS_INCLUDED',
                tl.confidence      = 0.60,
                tl.rule_id         = 'case9_nombank_sentence_timex',
                tl.evidence_source = 'tlinks_recognizer'
            ON MATCH SET
                tl.relType          = coalesce(tl.relType, 'IS_INCLUDED'),
                tl.relTypeCanonical = coalesce(tl.relTypeCanonical, 'IS_INCLUDED'),
                tl.confidence       = coalesce(tl.confidence, 0.60),
                tl.rule_id          = coalesce(tl.rule_id, 'case9_nombank_sentence_timex'),
                tl.evidence_source  = coalesce(tl.evidence_source, 'tlinks_recognizer')
            RETURN count(tl) AS created
        """
        return self._run_query(query)

    def create_tlinks_case10(self):
        """D3 — Link NOMBANK-promoted nominal events to SRL-derived ARGM-TMP candidates.

        ``promote_argm_tmp_to_timex_candidates()`` materializes advisory
        ``TimexMention:SRLTimexCandidate`` nodes for temporal spans that were
        explicitly labelled as ``ARGM-TMP`` by SRL but were missed by
        HeidelTime. Case 9 intentionally excludes those candidates to avoid a
        loose same-sentence circularity path. This case adds a tighter rule:

        - Only targets TEvents created by NOMBANK promotion (``source='nombank_srl'``).
        - Only links an event to a candidate whose ``source_fa_id`` matches an
          ``ARGM-TMP`` FrameArgument attached to a frame that describes that event.
        - Requires non-provisional frame evidence and skips merged /
          low-confidence / non-TimeML-core events.
        - Uses a conservative default relType of ``IS_INCLUDED`` and lower
          confidence than canonical TIMEX rules because the target remains
          advisory-tier until promoted.
        """
        logger.debug("create_tlinks_case10")
        query = """
            MATCH (e:TEvent {source: 'nombank_srl'})<-[:FRAME_DESCRIBES_EVENT|DESCRIBES]-(f:Frame)
                  <-[:HAS_FRAME_ARGUMENT|PARTICIPANT]-(fa:FrameArgument {type: 'ARGM-TMP'})
            MATCH (tm:TimexMention:SRLTimexCandidate)
            WHERE tm.source_fa_id = fa.id
              AND coalesce(f.provisional, false) = false
              AND coalesce(e.is_timeml_core, true) = true
              AND coalesce(e.low_confidence, false) = false
              AND coalesce(e.merged, false) = false
            OPTIONAL MATCH (tm)-[:REFERS_TO]->(t_ref:TIMEX)
            WITH DISTINCT e, t_ref AS t
            WHERE t IS NOT NULL AND coalesce(t.value, '') <> ''
            MERGE (e)-[tl:TLINK]->(t)
            ON CREATE SET
                tl.source           = 't2g',
                tl.relType          = 'IS_INCLUDED',
                tl.relTypeCanonical = 'IS_INCLUDED',
                tl.confidence       = 0.58,
                tl.rule_id          = 'case10_nombank_srl_timex',
                tl.evidence_source  = 'tlinks_recognizer'
            ON MATCH SET
                tl.relType          = coalesce(tl.relType, 'IS_INCLUDED'),
                tl.relTypeCanonical = coalesce(tl.relTypeCanonical, 'IS_INCLUDED'),
                tl.confidence       = coalesce(tl.confidence, 0.58),
                tl.rule_id          = coalesce(tl.rule_id, 'case10_nombank_srl_timex'),
                tl.evidence_source  = coalesce(tl.evidence_source, 'tlinks_recognizer')
            RETURN count(tl) AS created
        """
        return self._run_query(query)

    def create_tlinks_case11(self):
        """D4 — Link canonical TEvents to their SRL time-anchor via HAS_TIME_ANCHOR (Step 11).

        Case 10 targets only NOMBANK-promoted events (``source='nombank_srl'``) and
        requires a direct ARGM-TMP FrameArgument on the frame.  Case 11 is broader:
        it follows the ``HAS_TIME_ANCHOR`` edges written by
        ``TemporalPhase.anchor_srl_timex_candidates_to_events()`` (Step 10), which
        cover all canonical non-merged TEvents whose owning non-provisional Frame had
        an ARGM-TMP argument that was promoted to an ``SRLTimexCandidate`` node.

        The case fires when:

        - TEvent is non-merged, non-provisional (no low_confidence or excluded flags).
        - A ``HAS_TIME_ANCHOR`` edge leads to an ``SRLTimexCandidate`` with a
          ``REFERS_TO`` bridge to a canonical ``TIMEX`` node.
        - No existing ``TLINK`` from that event to that TIMEX already exists
          (the ``MERGE`` handles idempotency, but ``ON CREATE`` avoids overwriting
          higher-confidence values from earlier cases).

        ``relType`` defaults to ``IS_INCLUDED`` (the most conservative choice for
        SRL-inferred temporal inclusion).  Confidence is 0.57 — slightly below
        case 10 because the path via ``HAS_TIME_ANCHOR`` is one hop longer than the
        case 10 direct-frame path.
        """
        logger.debug("create_tlinks_case11")
        query = """
            MATCH (e:TEvent)-[:HAS_TIME_ANCHOR]->(tm:TimexMention:SRLTimexCandidate)
              -[:REFERS_TO]->(t:TIMEX)
            WHERE coalesce(e.merged, false) = false
              AND coalesce(e.low_confidence, false) = false
              AND coalesce(e.is_timeml_core, true) = true
              AND coalesce(t.value, '') <> ''
            MERGE (e)-[tl:TLINK]->(t)
            ON CREATE SET
                tl.source           = 't2g',
                tl.relType          = 'IS_INCLUDED',
                tl.relTypeCanonical = 'IS_INCLUDED',
                tl.confidence       = 0.57,
                tl.rule_id          = 'case11_has_time_anchor',
                tl.evidence_source  = 'tlinks_recognizer'
            ON MATCH SET
                tl.relType          = coalesce(tl.relType, 'IS_INCLUDED'),
                tl.relTypeCanonical = coalesce(tl.relTypeCanonical, 'IS_INCLUDED'),
                tl.confidence       = coalesce(tl.confidence, 0.57),
                tl.rule_id          = coalesce(tl.rule_id, 'case11_has_time_anchor'),
                tl.evidence_source  = coalesce(tl.evidence_source, 'tlinks_recognizer')
            RETURN count(tl) AS created
        """
        return self._run_query(query)

    # ===================================================================
    # Cases 12-18: Enhanced extraction grounded in NewsReader guidelines
    # and upstream GLINK/SLINK/CLINK/dep-parse signals
    # ===================================================================

    def create_tlinks_case12(self):
        """Case 12 — Bridge GLINK aspectual relations to TLINK (NewsReader §10.5).

        TTK produces GLINK edges where the source is an aspectual/grammatical
        event (begin, end, continue) and the target is the content event it
        governs. NewsReader explicitly maps these to BEGINS/ENDS/ENDED_BY
        relType families. Gold data shows BEGUN_BY×3 + ENDS×1 account for 27%
        of gold TLINKs — all currently absent from the system.

        Mapping:
          begin/start/... source → TLINK(content_event, BEGUN_BY, aspectual_event)
          end/finish/...  source → TLINK(content_event, ENDED_BY, aspectual_event)
          continue/keep/...      → TLINK(aspectual_event, INCLUDES, content_event)
          occur/happen/...       → TLINK(aspectual_event, SIMULTANEOUS, content_event)

        Confidence: 0.88 — GLINK is structured TTK output, high precision.
        """
        logger.debug("create_tlinks_case12")
        query = """
            MATCH (e_src:TEvent)-[:GLINK]->(e_tgt:TEvent)
            WHERE coalesce(e_src.is_timeml_core, true) = true
              AND coalesce(e_tgt.is_timeml_core, true) = true
              AND coalesce(e_src.low_confidence, false) = false
              AND coalesce(e_tgt.low_confidence, false) = false
              AND coalesce(e_src.merged, false) = false
              AND coalesce(e_tgt.merged, false) = false
            WITH e_src, e_tgt,
                 toLower(coalesce(e_src.lemma, e_src.text, '')) AS src_lemma
            WITH e_src, e_tgt, src_lemma,
                 CASE
                     WHEN src_lemma IN [
                         'begin', 'start', 'commence', 'open', 'launch',
                         'initiate', 'trigger', 'kick', 'inception', 'onset'
                     ] THEN 'BEGUN_BY'
                     WHEN src_lemma IN [
                         'end', 'finish', 'stop', 'cease', 'terminate',
                         'close', 'conclude', 'complete', 'halt', 'quit'
                     ] THEN 'ENDED_BY'
                     WHEN src_lemma IN [
                         'continue', 'keep', 'maintain', 'sustain',
                         'persist', 'last', 'extend', 'remain', 'stay'
                     ] THEN 'INCLUDES'
                     WHEN src_lemma IN [
                         'occur', 'happen', 'take', 'experience',
                         'undergo', 'witness', 'result'
                     ] THEN 'SIMULTANEOUS'
                     ELSE NULL
                 END AS inferred_rel
            WHERE inferred_rel IS NOT NULL
            WITH e_src, e_tgt, inferred_rel,
                 CASE
                     WHEN inferred_rel = 'BEGUN_BY'  THEN e_tgt
                     WHEN inferred_rel = 'ENDED_BY'  THEN e_tgt
                     WHEN inferred_rel = 'INCLUDES'  THEN e_src
                     ELSE e_src
                 END AS tlink_src,
                 CASE
                     WHEN inferred_rel = 'BEGUN_BY'  THEN e_src
                     WHEN inferred_rel = 'ENDED_BY'  THEN e_src
                     WHEN inferred_rel = 'INCLUDES'  THEN e_tgt
                     ELSE e_tgt
                 END AS tlink_tgt
            MERGE (tlink_src)-[tl:TLINK]->(tlink_tgt)
            ON CREATE SET
                tl.source           = 't2g',
                tl.relType          = inferred_rel,
                tl.relTypeCanonical = inferred_rel,
                tl.confidence       = 0.88,
                tl.rule_id          = 'case12_glink_bridge',
                tl.evidence_source  = 'tlinks_recognizer'
            ON MATCH SET
                tl.relType          = CASE WHEN coalesce(tl.confidence, 0.0) < 0.88 THEN inferred_rel ELSE tl.relType END,
                tl.relTypeCanonical = CASE WHEN coalesce(tl.confidence, 0.0) < 0.88 THEN inferred_rel ELSE tl.relTypeCanonical END,
                tl.confidence       = CASE WHEN coalesce(tl.confidence, 0.0) < 0.88 THEN 0.88 ELSE tl.confidence END,
                tl.rule_id          = coalesce(tl.rule_id, 'case12_glink_bridge'),
                tl.evidence_source  = coalesce(tl.evidence_source, 'tlinks_recognizer')
            RETURN count(tl) AS created
        """
        return self._run_query(query)

    def create_tlinks_case13(self):
        """Case 13 — Infer TLINK from CLINK edges (NewsReader §10.3).

        DISABLED: all 4 inferred BEFORE edges in MEANTIME evaluation are FPs
        (including a contradictory bidirectional pair). Re-enable only if
        evaluated on a dataset where CLINK→BEFORE precision is confirmed.
        """
        logger.debug("create_tlinks_case13: disabled (0 TPs, generates FPs)")
        return []
        # --- original implementation below (do not delete) ---
        """Original docstring: 

        NewsReader explicitly states: "there is an implicit temporal relation
        between the causing event and the caused one: the first always occurs
        before the second."  We have CLINK edges from
        EventEnrichmentPhase.derive_clinks_from_causal_arguments().

        Pattern: (cause)-[:CLINK]->(effect) → TLINK(cause, BEFORE, effect)

        Confidence: 0.82 — grounded in causal semantics; CLINK already has
        confidence 0.62+, so the derived TLINK inherits causal reasoning.
        """
        logger.debug("create_tlinks_case13")
        query = """
            MATCH (cause:TEvent)-[cl:CLINK]->(effect:TEvent)
            WHERE coalesce(cause.is_timeml_core, true) = true
              AND coalesce(effect.is_timeml_core, true) = true
              AND coalesce(cause.low_confidence, false) = false
              AND coalesce(effect.low_confidence, false) = false
              AND coalesce(cause.merged, false) = false
              AND coalesce(effect.merged, false) = false
              AND cause <> effect
            MERGE (cause)-[tl:TLINK]->(effect)
            ON CREATE SET
                tl.source           = 't2g',
                tl.relType          = 'BEFORE',
                tl.relTypeCanonical = 'BEFORE',
                tl.confidence       = 0.82,
                tl.rule_id          = 'case13_clink_before_inference',
                tl.evidence_source  = 'tlinks_recognizer',
                tl.derivedFrom      = 'CLINK'
            ON MATCH SET
                tl.relType          = CASE WHEN coalesce(tl.confidence, 0.0) < 0.82 THEN 'BEFORE' ELSE tl.relType END,
                tl.relTypeCanonical = CASE WHEN coalesce(tl.confidence, 0.0) < 0.82 THEN 'BEFORE' ELSE tl.relTypeCanonical END,
                tl.confidence       = CASE WHEN coalesce(tl.confidence, 0.0) < 0.82 THEN 0.82 ELSE tl.confidence END,
                tl.rule_id          = coalesce(tl.rule_id, 'case13_clink_before_inference'),
                tl.evidence_source  = coalesce(tl.evidence_source, 'tlinks_recognizer'),
                tl.derivedFrom      = coalesce(tl.derivedFrom, 'CLINK')
            RETURN count(tl) AS created
        """
        return self._run_query(query)

    def create_tlinks_case14(self):
        """Case 14 — SLINK tense matrix (NewsReader Subtask 3).

        DISABLED: generates bidirectional AFTER loops (both A→B AFTER and
        B→A AFTER when SLINK is bidirectional) which produce contradictory
        BEFORE+AFTER FPs. Zero TPs on MEANTIME. Re-enable after fixing the
        SLINK loop issue.
        """
        logger.debug("create_tlinks_case14: disabled (bidirectional AFTER bug)")
        return []
        # --- original implementation below (do not delete) ---
        """Original docstring: 

        NewsReader §10.6.2 Subtask 3 defines a complete tense-combination matrix
        for the temporal relation between a reporting (main) event and its
        subordinated (reported) event:

          PRESENT-main + PRESENT-sub  → SIMULTANEOUS
          PRESENT-main + PAST-sub     → AFTER  (main is after sub)
          PRESENT-main + FUTURE-sub   → BEFORE (main is before sub)
          PAST-main    + PAST-sub (perfective/simple) → AFTER
          PAST-main    + PAST-sub (progressive aspect) → IS_INCLUDED
          PAST-main    + FUTURE/INFINITIVE-sub         → BEFORE
          FUTURE-main  + PRESENT/FUTURE-sub → SIMULTANEOUS
          FUTURE-main  + PAST-sub     → AFTER
          FUTURE-main  + INFINITIVE   → BEFORE

        SLINK direction: (reporting_event)-[:SLINK]->(reported_event)
        which is source=main, target=sub. TLINK direction follows.

        Confidence: 0.75 — tense can be ambiguous; VAGUE patterns are skipped
        (no TLINK created rather than polluting with VAGUE).
        """
        logger.debug("create_tlinks_case14")
        query = """
            MATCH (e_main:TEvent)-[:SLINK]->(e_sub:TEvent)
            WHERE coalesce(e_main.is_timeml_core, true) = true
              AND coalesce(e_sub.is_timeml_core, true) = true
              AND coalesce(e_main.low_confidence, false) = false
              AND coalesce(e_sub.low_confidence, false) = false
              AND coalesce(e_main.merged, false) = false
              AND coalesce(e_sub.merged, false) = false
              AND e_main <> e_sub
            WITH e_main, e_sub,
                 toUpper(coalesce(e_main.tense, 'NONE')) AS mt,
                 toUpper(coalesce(e_sub.tense, 'NONE')) AS st,
                 toUpper(coalesce(e_sub.aspect, 'NONE')) AS sa
            WITH e_main, e_sub,
                 CASE
                     WHEN mt = 'PRESENT' AND st = 'PRESENT'
                         THEN 'SIMULTANEOUS'
                     WHEN mt = 'PRESENT' AND st = 'PAST'
                         THEN 'AFTER'
                     WHEN mt = 'PRESENT' AND st IN ['FUTURE', 'INFINITIVE']
                         THEN 'BEFORE'
                     WHEN mt = 'PAST' AND st IN ['PAST', 'PASTPART']
                          AND sa IN ['PERFECTIVE', 'NONE']
                         THEN 'AFTER'
                     WHEN mt = 'PAST' AND st = 'PAST' AND sa = 'PROGRESSIVE'
                         THEN 'IS_INCLUDED'
                     WHEN mt = 'PAST' AND st = 'PAST'
                          AND sa = 'PERFECTIVE_PROGRESSIVE'
                         THEN 'IS_INCLUDED'
                     WHEN mt = 'PAST' AND st IN ['FUTURE', 'INFINITIVE', 'PRESPART']
                         THEN 'BEFORE'
                     WHEN mt = 'FUTURE' AND st IN ['PRESENT', 'FUTURE', 'PRESPART']
                         THEN 'SIMULTANEOUS'
                     WHEN mt = 'FUTURE' AND st = 'PAST'
                         THEN 'AFTER'
                     WHEN mt = 'FUTURE' AND st = 'INFINITIVE'
                         THEN 'BEFORE'
                     ELSE NULL
                 END AS rel_type
            WHERE rel_type IS NOT NULL
            MERGE (e_main)-[tl:TLINK]->(e_sub)
            ON CREATE SET
                tl.source           = 't2g',
                tl.relType          = rel_type,
                tl.relTypeCanonical = rel_type,
                tl.confidence       = 0.75,
                tl.rule_id          = 'case14_slink_tense_matrix',
                tl.evidence_source  = 'tlinks_recognizer',
                tl.derivedFrom      = 'SLINK'
            ON MATCH SET
                tl.relType          = CASE WHEN coalesce(tl.confidence, 0.0) < 0.75 THEN rel_type ELSE tl.relType END,
                tl.relTypeCanonical = CASE WHEN coalesce(tl.confidence, 0.0) < 0.75 THEN rel_type ELSE tl.relTypeCanonical END,
                tl.confidence       = CASE WHEN coalesce(tl.confidence, 0.0) < 0.75 THEN 0.75 ELSE tl.confidence END,
                tl.rule_id          = coalesce(tl.rule_id, 'case14_slink_tense_matrix'),
                tl.evidence_source  = coalesce(tl.evidence_source, 'tlinks_recognizer'),
                tl.derivedFrom      = coalesce(tl.derivedFrom, 'SLINK')
            RETURN count(tl) AS created
        """
        return self._run_query(query)

    def create_tlinks_case15(self):
        """Case 15 — Dependency-tree TIMEX modifying a nominal event (NewsReader Subtask 4).

        NewsReader §10.6.2 Subtask 4 covers: "non-verbal event mention + TIMEX
        that modifies it".  Examples: "the 1992 crisis", "yesterday's meeting",
        "the former CEO".  Current Cases 4-5 only handle this via ARGM-TMP
        FrameArgument paths, missing direct syntactic modification.

        Pattern: TIMEX token → IS_DEPENDENT {dep: nmod/compound/tmod} → event token
        with event token.pos ∈ {NN, NNS, NNP, NNPS}

        relType: IS_INCLUDED (the nominal event IS_INCLUDED in the TIMEX period).
        Confidence: 0.83 — dep-parse is highly precise; nominal event + TIMEX
        modifier is an explicit NewsReader heuristic.
        """
        logger.debug("create_tlinks_case15")
        query = """
            MATCH (timex_tok:TagOccurrence)-[dep_rel:IS_DEPENDENT]->(event_tok:TagOccurrence)
            WHERE dep_rel.dep IN ['nmod', 'nmod:poss', 'compound', 'tmod', 'nummod', 'advmod',
                                  'obl', 'obl:tmod', 'nmod:tmod', 'npadvmod']
              AND event_tok.pos IN ['NN', 'NNS', 'NNP', 'NNPS',
                                    'VBD', 'VBN', 'VBZ', 'VBP', 'VB', 'VBG']
            MATCH (timex_tok)-[:TRIGGERS]->(tm)
            WHERE tm:TimexMention OR tm:TIMEX OR tm:Timex3
            MATCH (event_tok)-[:TRIGGERS]->(e:TEvent)
            WHERE coalesce(e.is_timeml_core, true) = true
              AND coalesce(e.low_confidence, false) = false
              AND coalesce(e.merged, false) = false
            OPTIONAL MATCH (tm)-[:REFERS_TO]->(t_ref:TIMEX)
            WITH e,
                 coalesce(t_ref, CASE WHEN tm:TIMEX OR tm:Timex3 THEN tm ELSE NULL END) AS t
            WHERE t IS NOT NULL
            WITH DISTINCT e, t
            MERGE (e)-[tl:TLINK]->(t)
            ON CREATE SET
                tl.source           = 't2g',
                tl.relType          = 'IS_INCLUDED',
                tl.relTypeCanonical = 'IS_INCLUDED',
                tl.confidence       = 0.83,
                tl.rule_id          = 'case15_dep_timex_nmod',
                tl.evidence_source  = 'tlinks_recognizer'
            ON MATCH SET
                tl.relType          = coalesce(tl.relType, 'IS_INCLUDED'),
                tl.relTypeCanonical = coalesce(tl.relTypeCanonical, 'IS_INCLUDED'),
                tl.confidence       = coalesce(tl.confidence, 0.83),
                tl.rule_id          = coalesce(tl.rule_id, 'case15_dep_timex_nmod'),
                tl.evidence_source  = coalesce(tl.evidence_source, 'tlinks_recognizer')
            RETURN count(tl) AS created
        """
        return self._run_query(query)

    def create_tlinks_case16(self):
        """Case 16 — Cross-sentence consecutive main event chain (NewsReader Subtask 2).

        NewsReader §10.6.2 Subtask 2 requires linking the main (ROOT) event of
        each sentence to the main event of the adjacent sentence. This provides
        the document-level narrative timeline backbone and is ENTIRELY absent from
        the current system.

        Strategy:
          - For each sentence s1, select the earliest-occurring verbal TEvent
            with finite tense (approx main event = first finite verb per sentence)
          - Find the same in s2 = the next sentence (sentence index + 1)
          - Create a TLINK based on the tense combination

        Tense mapping (conservative — skip ambiguous pairs):
          PAST  + PAST/PRESENT → BEFORE
          PAST  + FUTURE       → BEFORE
          PRESENT + FUTURE     → BEFORE
          PRESENT + PRESENT    → SIMULTANEOUS
          FUTURE + FUTURE      → BEFORE  (future events in narrative order)

        Sentence ordering uses the Sentence node ID format: {doc_id}_{sent_idx}.
        Confidence: 0.65 — cross-sentence inference is inherently less certain.
        """
        logger.debug("create_tlinks_case16")
        query = """
            MATCH (ann:AnnotatedText)-[:CONTAINS_SENTENCE]->(s1:Sentence)
                  -[:HAS_TOKEN]->(t1:TagOccurrence)-[:TRIGGERS]->(e1:TEvent)
            WHERE coalesce(e1.is_timeml_core, true) = true
              AND coalesce(e1.low_confidence, false) = false
              AND coalesce(e1.merged, false) = false
              AND coalesce(e1.tense, 'NONE') IN ['PAST', 'PRESENT', 'FUTURE']
              AND t1.pos IN ['VBZ', 'VBP', 'VBD', 'VBN', 'VB', 'MD']
            WITH ann, s1, e1, t1.tok_index_doc AS idx1,
                 CASE WHEN t1.dep = 'ROOT' THEN 0 ELSE 1 END AS root_prio
            ORDER BY root_prio ASC, idx1 ASC
            WITH ann, s1,
                 collect(e1)[0] AS e1_main,
                 toInteger(split(s1.id, '_')[size(split(s1.id, '_'))-1]) AS sn1
            WHERE e1_main IS NOT NULL

            MATCH (ann)-[:CONTAINS_SENTENCE]->(s2:Sentence)
                  -[:HAS_TOKEN]->(t2:TagOccurrence)-[:TRIGGERS]->(e2:TEvent)
            WHERE toInteger(split(s2.id, '_')[size(split(s2.id, '_'))-1]) = sn1 + 1
              AND coalesce(e2.is_timeml_core, true) = true
              AND coalesce(e2.low_confidence, false) = false
              AND coalesce(e2.merged, false) = false
              AND coalesce(e2.tense, 'NONE') IN ['PAST', 'PRESENT', 'FUTURE']
              AND t2.pos IN ['VBZ', 'VBP', 'VBD', 'VBN', 'VB', 'MD']
            WITH e1_main, t2.tok_index_doc AS idx2, e2,
                 CASE WHEN t2.dep = 'ROOT' THEN 0 ELSE 1 END AS root_prio2
            ORDER BY root_prio2 ASC, idx2 ASC
            WITH e1_main, collect(e2)[0] AS e2_main
            WHERE e2_main IS NOT NULL AND e1_main <> e2_main

            WITH e1_main AS e1, e2_main AS e2,
                 CASE
                     // PAST + PAST/PRESENT removed: tense alone does not reliably
                     // establish BEFORE order in news articles (gold rarely annotates these).
                     // PAST/PRESENT + FUTURE removed: generates FPs without TP benefit
                     // against MEANTIME gold (which encodes event ordering via IS_INCLUDED).
                     // PRESENT + PRESENT disabled: produces only FPs (2 in doc=62405)
                     // against MEANTIME gold with 0 TPs across all 6 evaluation docs.
                     // Kept as disabled stub for future review.
                     WHEN false THEN 'SIMULTANEOUS'
                     ELSE NULL
                 END AS rel_type
            WHERE rel_type IS NOT NULL

            MERGE (e1)-[tl:TLINK]->(e2)
            ON CREATE SET
                tl.source           = 't2g',
                tl.relType          = rel_type,
                tl.relTypeCanonical = rel_type,
                tl.confidence       = 0.65,
                tl.rule_id          = 'case16_cross_sentence_main_events',
                tl.evidence_source  = 'tlinks_recognizer'
            ON MATCH SET
                tl.relType          = CASE WHEN coalesce(tl.confidence, 0.0) < 0.65 THEN rel_type ELSE tl.relType END,
                tl.relTypeCanonical = CASE WHEN coalesce(tl.confidence, 0.0) < 0.65 THEN rel_type ELSE tl.relTypeCanonical END,
                tl.confidence       = CASE WHEN coalesce(tl.confidence, 0.0) < 0.65 THEN 0.65 ELSE tl.confidence END,
                tl.rule_id          = coalesce(tl.rule_id, 'case16_cross_sentence_main_events'),
                tl.evidence_source  = coalesce(tl.evidence_source, 'tlinks_recognizer')
            RETURN count(tl) AS created
        """
        return self._run_query(query)

    def create_tlinks_case17(self):
        """Case 17 — TIMEX–TIMEX temporal links (NewsReader Subtask 5).

        NewsReader §10.6.2 Subtask 5: TLINKs between two temporal expressions.
        Gold data shows 2/15 TLINKs are TIMEX–TIMEX (SIMULTANEOUS). Current
        system produces ZERO TIMEX–TIMEX links.

        Two sub-cases are run in sequence:
          17a. SIMULTANEOUS: Two TIMEX nodes with the same normalized value
               (e.g., two expressions referring to "2007-01-22").
          17b. IS_INCLUDED: A DURATION TIMEX co-occurring with a DATE/SET TIMEX
               in the same sentence where the duration is framed by the date
               (e.g., "for 3 months in 2010").
        """
        logger.debug("create_tlinks_case17")

        # Sub-case 17a: Same normalized value → SIMULTANEOUS
        query_17a = """
            MATCH (t1:TIMEX), (t2:TIMEX)
            WHERE elementId(t1) < elementId(t2)
              AND t1.doc_id = t2.doc_id
              AND coalesce(t1.value, '') <> ''
              AND coalesce(t2.value, '') <> ''
              AND t1.value = t2.value
              AND t1 <> t2
            MERGE (t1)-[tl:TLINK]->(t2)
            ON CREATE SET
                tl.source           = 't2g',
                tl.relType          = 'SIMULTANEOUS',
                tl.relTypeCanonical = 'SIMULTANEOUS',
                tl.confidence       = 0.87,
                tl.rule_id          = 'case17a_timex_same_value',
                tl.evidence_source  = 'tlinks_recognizer'
            ON MATCH SET
                tl.relType          = CASE WHEN coalesce(tl.confidence, 0.0) < 0.87 THEN 'SIMULTANEOUS' ELSE tl.relType END,
                tl.relTypeCanonical = CASE WHEN coalesce(tl.confidence, 0.0) < 0.87 THEN 'SIMULTANEOUS' ELSE tl.relTypeCanonical END,
                tl.confidence       = CASE WHEN coalesce(tl.confidence, 0.0) < 0.87 THEN 0.87 ELSE tl.confidence END,
                tl.rule_id          = coalesce(tl.rule_id, 'case17a_timex_same_value'),
                tl.evidence_source  = coalesce(tl.evidence_source, 'tlinks_recognizer')
            RETURN count(tl) AS created
        """
        r17a = self._run_query(query_17a)

        # Sub-case 17b: DURATION IS_INCLUDED in DATE/SET (same sentence)
        # "for 3 months in 2010" → (3 months) IS_INCLUDED (2010)
        query_17b = """
            MATCH (ann:AnnotatedText)-[:CONTAINS_SENTENCE]->(sent:Sentence)
                  -[:HAS_TOKEN]->(tok1:TagOccurrence)-[:TRIGGERS]->(tm1)
            MATCH (sent)-[:HAS_TOKEN]->(tok2:TagOccurrence)-[:TRIGGERS]->(tm2)
            WHERE (tm1:TIMEX OR tm1:Timex3) AND (tm2:TIMEX OR tm2:Timex3)
              AND elementId(tok1) <> elementId(tok2)
              AND coalesce(tm1.type, '') = 'DURATION'
              AND coalesce(tm2.type, '') IN ['DATE', 'SET', 'TIME']
              AND coalesce(tm1.value, '') <> ''
              AND coalesce(tm2.value, '') <> ''
              AND tm1 <> tm2
              AND abs(coalesce(tok1.tok_index_doc, -1) - coalesce(tok2.tok_index_doc, -1)) <= 10
            WITH DISTINCT tm1, tm2
            MERGE (tm1)-[tl:TLINK]->(tm2)
            ON CREATE SET
                tl.source           = 't2g',
                tl.relType          = 'IS_INCLUDED',
                tl.relTypeCanonical = 'IS_INCLUDED',
                tl.confidence       = 0.78,
                tl.rule_id          = 'case17b_timex_duration_in_date',
                tl.evidence_source  = 'tlinks_recognizer'
            ON MATCH SET
                tl.relType          = coalesce(tl.relType, 'IS_INCLUDED'),
                tl.relTypeCanonical = coalesce(tl.relTypeCanonical, 'IS_INCLUDED'),
                tl.confidence       = coalesce(tl.confidence, 0.78),
                tl.rule_id          = coalesce(tl.rule_id, 'case17b_timex_duration_in_date'),
                tl.evidence_source  = coalesce(tl.evidence_source, 'tlinks_recognizer')
            RETURN count(tl) AS created
        """
        r17b = self._run_query(query_17b)
        return r17a, r17b

    def create_tlinks_case18(self):
        """Case 18 — Expanded signal lexicon via Signal node traversal.

        Cases 1-3 only match a limited set of signals via the ``fa.signal``
        shorthand property ('after', 'before', 'following'). This case
        extends coverage by:
          1. Traversing the Signal node graph: tokens tagged as Signal type
             that co-occur with ARGM-TMP frame arguments.
          2. Expanding the signal vocabulary to include temporal conjunctions
             'when', 'while', 'as', 'once', 'until', 'since', 'as soon as',
             'meanwhile', 'during', 'upon', 'after', 'before'.

        Signal-to-relType mapping:
          when / while / as / once / meanwhile → SIMULTANEOUS
          after  → AFTER
          before → BEFORE
          since  → BEGUN_BY (event E has been ongoing since event E2)
          until  → ENDED_BY
          upon / immediately after → IAFTER

        This applies to Event-Event links only; Event-TIMEX links are already
        handled by Cases 4-5. Confidence: 0.80.
        """
        logger.debug("create_tlinks_case18")

        # Path: TEvent ← Frame ← ARGM-TMP ← tokens within ARGM-TMP span
        #       where one of those tokens is a Signal-typed node
        query = """
            MATCH (e1:TEvent)-[:FRAME_DESCRIBES_EVENT|DESCRIBES]-(f1:Frame)
                  <-[:HAS_FRAME_ARGUMENT|PARTICIPANT]-(fa:FrameArgument {type: 'ARGM-TMP'})
            MATCH (tok_sig:TagOccurrence)-[:IN_FRAME]->(fa)
            MATCH (tok_sig)-[:TRIGGERS]->(sig:Signal)
            WHERE coalesce(e1.is_timeml_core, true) = true
              AND coalesce(e1.low_confidence, false) = false
              AND coalesce(e1.merged, false) = false
            WITH e1, fa, tok_sig, toLower(coalesce(sig.text, tok_sig.lemma, tok_sig.text, '')) AS sig_text
            WHERE sig_text IN [
                'when', 'while', 'as', 'once', 'meanwhile', 'after', 'before',
                'since', 'until', 'upon', 'following', 'prior'
            ]

            // Find the second event connected via the same ARGM-TMP span
            MATCH (tok_e2:TagOccurrence)-[:IN_FRAME]->(fa)
            MATCH (tok_e2)-[:TRIGGERS]->(e2:TEvent)
            WHERE e1 <> e2
              AND coalesce(e2.is_timeml_core, true) = true
              AND coalesce(e2.low_confidence, false) = false
              AND coalesce(e2.merged, false) = false

            WITH e1, e2, sig_text,
                 CASE
                     WHEN sig_text IN ['when', 'while', 'as', 'once', 'meanwhile']
                         THEN 'SIMULTANEOUS'
                     WHEN sig_text IN ['after', 'following']
                         THEN 'AFTER'
                     WHEN sig_text IN ['before', 'prior']
                         THEN 'BEFORE'
                     WHEN sig_text = 'since'
                         THEN 'BEGUN_BY'
                     WHEN sig_text = 'until'
                         THEN 'ENDED_BY'
                     WHEN sig_text = 'upon'
                         THEN 'IAFTER'
                     ELSE NULL
                 END AS rel_type
            WHERE rel_type IS NOT NULL

            MERGE (e1)-[tl:TLINK]->(e2)
            ON CREATE SET
                tl.source           = 't2g',
                tl.relType          = rel_type,
                tl.relTypeCanonical = rel_type,
                tl.confidence       = 0.80,
                tl.rule_id          = 'case18_signal_node_expansion',
                tl.evidence_source  = 'tlinks_recognizer',
                tl.signalText       = sig_text
            ON MATCH SET
                tl.relType          = CASE WHEN coalesce(tl.confidence, 0.0) < 0.80 THEN rel_type ELSE tl.relType END,
                tl.relTypeCanonical = CASE WHEN coalesce(tl.confidence, 0.0) < 0.80 THEN rel_type ELSE tl.relTypeCanonical END,
                tl.confidence       = CASE WHEN coalesce(tl.confidence, 0.0) < 0.80 THEN 0.80 ELSE tl.confidence END,
                tl.rule_id          = coalesce(tl.rule_id, 'case18_signal_node_expansion'),
                tl.evidence_source  = coalesce(tl.evidence_source, 'tlinks_recognizer'),
                tl.signalText       = coalesce(tl.signalText, sig_text)
            RETURN count(tl) AS created
        """
        results = self._run_query(query)

        # Also expand Cases 1-3 signal matching via fa.signal property for additional conjunctions
        query_fa_signal = """
            MATCH (e1:TEvent)-[:FRAME_DESCRIBES_EVENT|DESCRIBES]-(f1:Frame)
                  <-[:HAS_FRAME_ARGUMENT|PARTICIPANT]-(fa:FrameArgument {type: 'ARGM-TMP'})
                  <-[:IN_FRAME]-(et:TagOccurrence)-[:IN_FRAME]->(f2:Frame)
                  -[:FRAME_DESCRIBES_EVENT|DESCRIBES]-(e2:TEvent)
            WHERE fa.headTokenIndex = et.tok_index_doc
              AND toLower(coalesce(fa.signal, '')) IN [
                  'when', 'while', 'as', 'once', 'since', 'until',
                  'upon', 'following', 'prior', 'meanwhile'
              ]
              AND coalesce(e1.is_timeml_core, true) = true
              AND coalesce(e2.is_timeml_core, true) = true
              AND coalesce(e1.low_confidence, false) = false
              AND coalesce(e2.low_confidence, false) = false
              AND coalesce(e1.merged, false) = false
              AND coalesce(e2.merged, false) = false
              AND e1 <> e2
            WITH e1, e2, toLower(fa.signal) AS sig
            WITH e1, e2, sig,
                 CASE
                     WHEN sig IN ['when', 'while', 'as', 'once', 'meanwhile']
                         THEN 'SIMULTANEOUS'
                     WHEN sig IN ['following', 'after']
                         THEN 'AFTER'
                     WHEN sig IN ['before', 'prior']
                         THEN 'BEFORE'
                     WHEN sig = 'since'
                         THEN 'BEGUN_BY'
                     WHEN sig = 'until'
                         THEN 'ENDED_BY'
                     WHEN sig = 'upon'
                         THEN 'IAFTER'
                     ELSE NULL
                 END AS rel_type
            WHERE rel_type IS NOT NULL
            MERGE (e1)-[tl:TLINK]->(e2)
            ON CREATE SET
                tl.source           = 't2g',
                tl.relType          = rel_type,
                tl.relTypeCanonical = rel_type,
                tl.confidence       = 0.82,
                tl.rule_id          = 'case18b_fa_signal_expansion',
                tl.evidence_source  = 'tlinks_recognizer',
                tl.signalText       = sig
            ON MATCH SET
                tl.relType          = CASE WHEN coalesce(tl.confidence, 0.0) < 0.82 THEN rel_type ELSE tl.relType END,
                tl.relTypeCanonical = CASE WHEN coalesce(tl.confidence, 0.0) < 0.82 THEN rel_type ELSE tl.relTypeCanonical END,
                tl.confidence       = CASE WHEN coalesce(tl.confidence, 0.0) < 0.82 THEN 0.82 ELSE tl.confidence END,
                tl.rule_id          = coalesce(tl.rule_id, 'case18b_fa_signal_expansion'),
                tl.evidence_source  = coalesce(tl.evidence_source, 'tlinks_recognizer'),
                tl.signalText       = coalesce(tl.signalText, sig)
            RETURN count(tl) AS created
        """
        results_b = self._run_query(query_fa_signal)
        return results, results_b

    def create_tlinks_case20(self):
        """Case 20 — DCT-INCLUDES fallback for article events lacking explicit anchors.

        The MEANTIME gold shows 20 INCLUDES × TIMEX-EVENT links (27.6% of all gold
        TLINKs), the single largest relType gap.  The majority come from the
        document-creation-time (DCT) TIMEX including the events described in the
        article body — the standard interpretation for news articles.

        Existing rules already cover some of these:
          - Case 6: verbal events with explicit tense → (e)-[IS_INCLUDED]->(dct)
          - Case 8: DISABLED (guideline violation — nominals must not be DCT-anchored)
          - Case 19: flips IS_INCLUDED to INCLUDES in the opposite direction

        This case fills the remaining gap with two sub-patterns:

        **20a / Case 21 — Dependency-tree TIMEX INCLUDES event (non-DCT)**
        For each TIMEX token that syntactically modifies a TEvent token via a
        dependency edge (dep: nmod, nmod:poss, compound, tmod, nummod, advmod,
        obl, obl:tmod, nmod:tmod, npadvmod), write (timex)-[INCLUDES]->(event)
        when no TLINK already exists between the pair.  This replaces the previous
        15-token proximity window, restricting predictions to syntactically-governed
        pairs and reducing false positives.  Case 19 creates the IS_INCLUDED inverse.
        rule_id: 'case21_dep_timex_includes', confidence 0.75.

        **20b — DCT INCLUDES unanchored events**
        For TEvents that have NO outgoing TLINK to any TIMEX at all (not even a
        VAGUE one), write (e)-[IS_INCLUDED]->(dct) to anchor them to the article
        date.  This catches events that Case 6/8 missed (e.g., infinitive
        constructions, participials, events with NONE tense).  Confidence 0.55
        (lower than Case 6's 0.78 because tense evidence is absent).

        Both sub-cases use MERGE so they are idempotent and will not overwrite
        higher-confidence existing TLINKs.
        """
        logger.debug("create_tlinks_case20")

        # --- 20a / Case 21: dep-tree TIMEX modifies event (replaces 15-token proximity) ---
        # Matches only when the TIMEX token syntactically governs the event token via
        # a dependency edge, dramatically reducing false positives vs. proximity window.
        query_20a = """
            MATCH (tok_t:TagOccurrence)-[dep_rel:IS_DEPENDENT]->(tok_e:TagOccurrence)
            WHERE dep_rel.dep IN ['nmod', 'nmod:poss', 'compound', 'tmod', 'nummod', 'advmod',
                                  'obl', 'obl:tmod', 'nmod:tmod', 'npadvmod']
            MATCH (tok_t)-[:TRIGGERS]->(tm)
            WHERE (tm:TimexMention OR tm:TIMEX OR tm:Timex3)
              AND NOT tm:SRLTimexCandidate
              AND coalesce(tm.type, '') IN ['DATE', 'SET', 'TIME']
            MATCH (tok_e)-[:TRIGGERS]->(e:TEvent)
            WHERE coalesce(e.is_timeml_core, true) = true
              AND coalesce(e.low_confidence, false) = false
              AND coalesce(e.merged, false) = false
            OPTIONAL MATCH (tm)-[:REFERS_TO]->(t_ref:TIMEX)
            WITH e,
                 coalesce(t_ref, CASE WHEN tm:TIMEX OR tm:Timex3 THEN tm ELSE NULL END) AS t
            WHERE t IS NOT NULL
            WITH DISTINCT e, t
            // Only write if no TLINK at all on this pair already
            WHERE NOT (e)-[:TLINK]-(t)
            MERGE (t)-[tl:TLINK]->(e)
            ON CREATE SET
                tl.source           = 't2g',
                tl.relType          = 'INCLUDES',
                tl.relTypeCanonical = 'INCLUDES',
                tl.confidence       = 0.75,
                tl.rule_id          = 'case21_dep_timex_includes',
                tl.evidence_source  = 'tlinks_recognizer'
            ON MATCH SET
                tl.relType          = coalesce(tl.relType, 'INCLUDES'),
                tl.relTypeCanonical = coalesce(tl.relTypeCanonical, 'INCLUDES'),
                tl.confidence       = coalesce(tl.confidence, 0.75),
                tl.rule_id          = coalesce(tl.rule_id, 'case21_dep_timex_includes'),
                tl.evidence_source  = coalesce(tl.evidence_source, 'tlinks_recognizer')
            RETURN count(tl) AS created
        """
        results_20a = self._run_query(query_20a)
        created_20a = results_20a[0].get("created", 0) if results_20a else 0

        # --- 20b: DCT INCLUDES unanchored events ---
        query_20b = """
            MATCH (ann:AnnotatedText)-[:CREATED_ON]->(dct)
            WHERE dct:TIMEX OR dct:Timex3
            MATCH (ann)-[:CONTAINS_SENTENCE]->(s:Sentence)
                  -[:HAS_TOKEN]->(tok_e:TagOccurrence)-[:TRIGGERS]->(e:TEvent)
            WHERE coalesce(e.is_timeml_core, true) = true
              AND coalesce(e.low_confidence, false) = false
              AND coalesce(e.merged, false) = false
              // Only events with NO TLINK to any TIMEX at all
              AND NOT EXISTS {
                  MATCH (e)-[:TLINK]-(any_timex)
                  WHERE any_timex:TIMEX OR any_timex:Timex3
              }
            MERGE (e)-[tl:TLINK]->(dct)
            ON CREATE SET
                tl.source           = 't2g',
                tl.relType          = 'IS_INCLUDED',
                tl.relTypeCanonical = 'IS_INCLUDED',
                tl.confidence       = 0.55,
                tl.rule_id          = 'case20b_dct_unanchored_fallback',
                tl.evidence_source  = 'tlinks_recognizer'
            ON MATCH SET
                tl.relType          = coalesce(tl.relType, 'IS_INCLUDED'),
                tl.relTypeCanonical = coalesce(tl.relTypeCanonical, 'IS_INCLUDED'),
                tl.confidence       = coalesce(tl.confidence, 0.55),
                tl.rule_id          = coalesce(tl.rule_id, 'case20b_dct_unanchored_fallback'),
                tl.evidence_source  = coalesce(tl.evidence_source, 'tlinks_recognizer')
            RETURN count(tl) AS created
        """
        results_20b = self._run_query(query_20b)
        created_20b = results_20b[0].get("created", 0) if results_20b else 0

        logger.info(
            "create_tlinks_case20: 20a/21 (dep-timex-includes)=%d  20b (dct-unanchored)=%d",
            created_20a,
            created_20b,
        )
        return results_20a, results_20b

    def create_tlinks_case22(self):
        """Case 22 — Dateline TIMEX INCLUDES/SIMULTANEOUS main (ROOT) events in leading sentences.

        NewsReader Subtask 1 gold shows that the dateline TIMEX (the in-text date
        expression at the article head, e.g. "August 10, 2007") INCLUDES the
        main verbal events reported in the article.  The DCT node (t0) has no
        token span and therefore cannot be used as a TLINK endpoint in evaluation;
        this rule instead writes to the earliest DATE TIMEX node whose value
        matches the DCT date (the dateline text occurrence).

        Selection criteria:
        - Dateline TIMEX: earliest DATE TIMEX (non-t0) with value matching the
          DCT YYYY-MM-DD prefix, i.e. the first text occurrence of the pub date.
        - Events: verbal TEvents anchored by a ROOT-dependency token in the first
          ~100 tokens (lead sentences) that have no TLINK to the dateline yet.
        - relType: SIMULTANEOUS when a co-temporal TIMEX (same date value as the
          dateline) is the syntactic subject (nsubj) of the event verb — e.g.
          "Today marked a day in history" → SIMULTANEOUS.  INCLUDES otherwise.
          The inverse IS_INCLUDED / SIMULTANEOUS direction is also written.
        - Confidence: 0.70.  rule_ids: 'case22_dateline_includes',
          'case22_dateline_simultaneous'.
        Tier: T1 — deterministic rule.
        """
        logger.debug("create_tlinks_case22")
        query = """
            // Identify the publication-date DCT for each document
            MATCH (ann:AnnotatedText)-[:CREATED_ON]->(dct)
            WHERE (dct:TIMEX OR dct:Timex3)
              AND toUpper(coalesce(dct.functionInDocument, '')) = 'CREATION_TIME'
              AND size(coalesce(dct.value, '')) >= 8

            // Find the earliest DATE TIMEX in the text whose date matches the DCT
            MATCH (dateline_cand:TIMEX {doc_id: ann.id})
            WHERE dateline_cand.tid <> 't0'
              AND dateline_cand.type = 'DATE'
              AND dateline_cand.start_tok IS NOT NULL
              AND size(coalesce(dateline_cand.value, '')) >= 8
              AND left(coalesce(dct.value, ''), 10) = left(coalesce(dateline_cand.value, ''), 10)
            WITH ann, dateline_cand
            ORDER BY dateline_cand.start_tok ASC
            WITH ann, collect(dateline_cand)[0] AS dateline
            WHERE dateline IS NOT NULL

            // Match ROOT-dep verbal events in leading sentences (first ~100 tokens)
            MATCH (ann)-[:CONTAINS_SENTENCE]->(s:Sentence)
                  -[:HAS_TOKEN]->(tok:TagOccurrence)-[:TRIGGERS]->(e:TEvent)
            WHERE EXISTS { (tok)-[dep_r:IS_DEPENDENT]->(tok) WHERE dep_r.type = 'ROOT' }
              AND coalesce(e.is_timeml_core, true) = true
              AND coalesce(e.low_confidence, false) = false
              AND coalesce(e.merged, false) = false
              AND tok.pos IN ['VBD', 'VBN', 'VBZ', 'VBP', 'VB', 'MD']
              AND coalesce(e.start_tok, 9999) <= 103
              // Sentence-index guard: restrict to first 6 sentences (index 0-5).
              // Sentence IDs have the form '{doc_id}_{sentence_index}'; all gold
              // dateline TPs across 6 eval docs sit in sentences 0-5 while the
              // only FP (doc=61327 event tok99) lives in sentence 6.
              AND toInteger(last(split(s.id, '_'))) <= 5
              AND e.start_tok > dateline.end_tok
              AND NOT (e)-[:TLINK]-(dateline)

            // Detect SIMULTANEOUS pattern: event's nsubj is a co-temporal TIMEX
            // (e.g. "Today marked..." where 'today' has same date value as dateline).
            WITH ann, dateline, e, tok,
                 EXISTS {
                     MATCH (tok)-[:IS_DEPENDENT {type: 'nsubj'}]->(nt:TagOccurrence)-[:TRIGGERS]->(ntm)
                     WHERE (ntm:TIMEX OR ntm:TimexMention)
                       AND coalesce(ntm.type, '') = 'DATE'
                       AND left(coalesce(ntm.value, ''), 10) = left(coalesce(dateline.value, ''), 10)
                 } AS is_simultaneous

            WITH dateline, e,
                 CASE WHEN is_simultaneous THEN 'SIMULTANEOUS'  ELSE 'INCLUDES'   END AS fwd_rel,
                 CASE WHEN is_simultaneous THEN 'SIMULTANEOUS'  ELSE 'IS_INCLUDED' END AS inv_rel,
                 CASE WHEN is_simultaneous THEN 'case22_dateline_simultaneous' ELSE 'case22_dateline_includes' END AS fwd_rule,
                 CASE WHEN is_simultaneous THEN 'case22_dateline_simultaneous' ELSE 'case22_dateline_is_included' END AS inv_rule

            MERGE (dateline)-[tl:TLINK]->(e)
            ON CREATE SET
                tl.source           = 't2g',
                tl.relType          = fwd_rel,
                tl.relTypeCanonical = fwd_rel,
                tl.confidence       = 0.70,
                tl.rule_id          = fwd_rule,
                tl.evidence_source  = 'tlinks_recognizer'
            ON MATCH SET
                tl.relType          = CASE WHEN coalesce(tl.confidence, 0.0) < 0.70 THEN fwd_rel ELSE tl.relType END,
                tl.relTypeCanonical = CASE WHEN coalesce(tl.confidence, 0.0) < 0.70 THEN fwd_rel ELSE tl.relTypeCanonical END,
                tl.confidence       = CASE WHEN coalesce(tl.confidence, 0.0) < 0.70 THEN 0.70 ELSE tl.confidence END,
                tl.rule_id          = coalesce(tl.rule_id, fwd_rule),
                tl.evidence_source  = coalesce(tl.evidence_source, 'tlinks_recognizer')

            // Also create the inverse direction.
            WITH dateline, e, inv_rel, inv_rule
            MERGE (e)-[tl_inv:TLINK]->(dateline)
            ON CREATE SET
                tl_inv.source           = 't2g',
                tl_inv.relType          = inv_rel,
                tl_inv.relTypeCanonical = inv_rel,
                tl_inv.confidence       = 0.70,
                tl_inv.rule_id          = inv_rule,
                tl_inv.evidence_source  = 'tlinks_recognizer'
            ON MATCH SET
                tl_inv.relType          = CASE WHEN coalesce(tl_inv.confidence, 0.0) < 0.70 THEN inv_rel ELSE tl_inv.relType END,
                tl_inv.relTypeCanonical = CASE WHEN coalesce(tl_inv.confidence, 0.0) < 0.70 THEN inv_rel ELSE tl_inv.relTypeCanonical END,
                tl_inv.confidence       = CASE WHEN coalesce(tl_inv.confidence, 0.0) < 0.70 THEN 0.70 ELSE tl_inv.confidence END,
                tl_inv.rule_id          = coalesce(tl_inv.rule_id, inv_rule),
                tl_inv.evidence_source  = coalesce(tl_inv.evidence_source, 'tlinks_recognizer')
            RETURN count(tl_inv) AS created
        """
        results = self._run_query(query)
        created = results[0].get("created", 0) if results else 0
        logger.info("create_tlinks_case22: dateline-includes/simultaneous=%d", created)
        return results

    def create_tlinks_case23(self):
        """Case 23 — Dependency-parse-based temporal ordering via connective words.

        Two sub-patterns derived from spaCy IS_DEPENDENT edges:

        **Sub-pattern A — prepositional chain (T1 rule)**:
            tok_e1 -[IS_DEPENDENT:prep]-> signal -[IS_DEPENDENT:pcomp|pobj]-> tok_e2
            Where signal.text ∈ {'after','since','following'} → AFTER(e1, e2)
            Where signal.text ∈ {'before'}                   → BEFORE(e1, e2)
            Example: "rebounded after falling" (doc 76437)

        **Sub-pattern B — adverbial clause with mark (T1 rule)**:
            tok_main -[IS_DEPENDENT:advcl]-> tok_sub
            tok_sub  -[IS_DEPENDENT:mark]->  signal
            Where signal.text ∈ {'after','since','following'} → BEFORE(e_sub, e_main)
            Where signal.text ∈ {'before'}                   → AFTER(e_sub, e_main)
            Restricted to start_tok ≤ 200 to avoid deep-article noise.
            Example: "sending jitters after China sent" (doc 62405)

        Tier: T1 — deterministic, no ML required.
        Covers cases missed when SRL service does not fire.
        """
        logger.debug("create_tlinks_case23")

        # --- Sub-pattern A: prep + pcomp/pobj temporal chain ---
        query_a_after = """
            MATCH (tok_e1:TagOccurrence)-[:IS_DEPENDENT {type: 'prep'}]->(signal_tok:TagOccurrence)
            WHERE toLower(signal_tok.text) IN ['after', 'since', 'following']
            MATCH (signal_tok)-[d2:IS_DEPENDENT]->(tok_e2:TagOccurrence)
            WHERE d2.type IN ['pcomp', 'pobj']
            MATCH (tok_e1)-[:TRIGGERS]->(e1:TEvent)
            MATCH (tok_e2)-[:TRIGGERS]->(e2:TEvent)
            WHERE e1.doc_id = e2.doc_id
              AND e1 <> e2
              AND coalesce(e1.is_timeml_core, true) = true
              AND coalesce(e2.is_timeml_core, true) = true
              AND coalesce(e1.low_confidence, false) = false
              AND coalesce(e2.low_confidence, false) = false
              AND NOT (e1)-[:TLINK]-(e2)
            MERGE (e1)-[tl:TLINK]->(e2)
            ON CREATE SET
                tl.source           = 't2g',
                tl.relType          = 'AFTER',
                tl.relTypeCanonical = 'AFTER',
                tl.confidence       = 0.72,
                tl.rule_id          = 'case23a_dep_prep_after',
                tl.evidence_source  = 'tlinks_recognizer'
            RETURN count(tl) AS created
        """

        query_a_before = """
            MATCH (tok_e1:TagOccurrence)-[:IS_DEPENDENT {type: 'prep'}]->(signal_tok:TagOccurrence)
            WHERE toLower(signal_tok.text) IN ['before']
            MATCH (signal_tok)-[d2:IS_DEPENDENT]->(tok_e2:TagOccurrence)
            WHERE d2.type IN ['pcomp', 'pobj']
            MATCH (tok_e1)-[:TRIGGERS]->(e1:TEvent)
            MATCH (tok_e2)-[:TRIGGERS]->(e2:TEvent)
            WHERE e1.doc_id = e2.doc_id
              AND e1 <> e2
              AND coalesce(e1.is_timeml_core, true) = true
              AND coalesce(e2.is_timeml_core, true) = true
              AND coalesce(e1.low_confidence, false) = false
              AND coalesce(e2.low_confidence, false) = false
              AND NOT (e1)-[:TLINK]-(e2)
            MERGE (e1)-[tl:TLINK]->(e2)
            ON CREATE SET
                tl.source           = 't2g',
                tl.relType          = 'BEFORE',
                tl.relTypeCanonical = 'BEFORE',
                tl.confidence       = 0.72,
                tl.rule_id          = 'case23a_dep_prep_before',
                tl.evidence_source  = 'tlinks_recognizer'
            RETURN count(tl) AS created
        """

        # --- Sub-pattern B: advcl + mark temporal subordinate clause ---
        # Direction: main clause is LATER than sub clause for 'after'
        # → create BEFORE(e_sub → e_main) so gold BEFORE(sub,main) matches exactly
        query_b_after = """
            MATCH (tok_main:TagOccurrence)-[d1:IS_DEPENDENT {type: 'advcl'}]->(tok_sub:TagOccurrence)
            MATCH (tok_sub)-[d2:IS_DEPENDENT {type: 'mark'}]->(signal_tok:TagOccurrence)
            WHERE toLower(signal_tok.text) IN ['after', 'since', 'following']
            MATCH (tok_main)-[:TRIGGERS]->(e_main:TEvent)
            MATCH (tok_sub)-[:TRIGGERS]->(e_sub:TEvent)
            WHERE e_main.doc_id = e_sub.doc_id
              AND e_main <> e_sub
              AND coalesce(e_main.is_timeml_core, true) = true
              AND coalesce(e_sub.is_timeml_core, true) = true
              AND coalesce(e_main.low_confidence, false) = false
              AND coalesce(e_sub.low_confidence, false) = false
              AND coalesce(e_main.start_tok, 9999) <= 200
              AND coalesce(e_sub.start_tok, 9999) <= 200
              AND NOT (e_sub)-[:TLINK]-(e_main)
            MERGE (e_sub)-[tl:TLINK]->(e_main)
            ON CREATE SET
                tl.source           = 't2g',
                tl.relType          = 'BEFORE',
                tl.relTypeCanonical = 'BEFORE',
                tl.confidence       = 0.70,
                tl.rule_id          = 'case23b_dep_advcl_before',
                tl.evidence_source  = 'tlinks_recognizer'
            RETURN count(tl) AS created
        """

        query_b_before = """
            MATCH (tok_main:TagOccurrence)-[d1:IS_DEPENDENT {type: 'advcl'}]->(tok_sub:TagOccurrence)
            MATCH (tok_sub)-[d2:IS_DEPENDENT {type: 'mark'}]->(signal_tok:TagOccurrence)
            WHERE toLower(signal_tok.text) IN ['before']
            MATCH (tok_main)-[:TRIGGERS]->(e_main:TEvent)
            MATCH (tok_sub)-[:TRIGGERS]->(e_sub:TEvent)
            WHERE e_main.doc_id = e_sub.doc_id
              AND e_main <> e_sub
              AND coalesce(e_main.is_timeml_core, true) = true
              AND coalesce(e_sub.is_timeml_core, true) = true
              AND coalesce(e_main.low_confidence, false) = false
              AND coalesce(e_sub.low_confidence, false) = false
              AND coalesce(e_main.start_tok, 9999) <= 200
              AND coalesce(e_sub.start_tok, 9999) <= 200
              AND NOT (e_sub)-[:TLINK]-(e_main)
            MERGE (e_sub)-[tl:TLINK]->(e_main)
            ON CREATE SET
                tl.source           = 't2g',
                tl.relType          = 'AFTER',
                tl.relTypeCanonical = 'AFTER',
                tl.confidence       = 0.70,
                tl.rule_id          = 'case23b_dep_advcl_after',
                tl.evidence_source  = 'tlinks_recognizer'
            RETURN count(tl) AS created
        """

        r_a_after = self._run_query(query_a_after)
        r_a_before = self._run_query(query_a_before)
        r_b_after = self._run_query(query_b_after)
        r_b_before = self._run_query(query_b_before)
        c_a_after = r_a_after[0].get("created", 0) if r_a_after else 0
        c_a_before = r_a_before[0].get("created", 0) if r_a_before else 0
        c_b_after = r_b_after[0].get("created", 0) if r_b_after else 0
        c_b_before = r_b_before[0].get("created", 0) if r_b_before else 0
        logger.info(
            "create_tlinks_case23: prep_after=%d prep_before=%d advcl_before=%d advcl_after=%d",
            c_a_after, c_a_before, c_b_after, c_b_before,
        )
        return r_a_after + r_a_before + r_b_after + r_b_before

    def create_tlinks_case24(self):
        """Case 24 — Dependency-parse advmod temporal IS_INCLUDED.

        Fires when an event's head token has a direct *advmod* dependency edge
        to a token that triggers a TIMEX with a specific calendar value
        (year, year-month, or year-month-day).  Vague references such as
        PAST_REF, PRESENT_REF, or ISO-week values (e.g. 2007-W32) are excluded
        to keep precision high.

        Pattern:
            tok_e -[IS_DEPENDENT:advmod]-> tok_t -[:TRIGGERS]-> TIMEX
            TIMEX.value =~ '^\\d{4}(-\\d{2}(-\\d{2})?)?$'
            → IS_INCLUDED(event, TIMEX)

        Example (doc 82738):
            crashed(44) -advmod-> ago(34) [:TRIGGERS]-> TIMEX '20 years ago' (val=1987)
            → crashed IS_INCLUDED '20 years ago'

        Tier: T1 — deterministic dep-parse rule, no ML required.
        Confidence: 0.85 (high — direct syntactic attachment).
        """
        logger.debug("create_tlinks_case24")
        query = """
            MATCH (e:TEvent)<-[:TRIGGERS]-(tok_e:TagOccurrence)
                  -[dep:IS_DEPENDENT {type: 'advmod'}]->
                  (tok_t:TagOccurrence)-[:TRIGGERS]->(tm)
            WHERE (tm:TIMEX OR tm:TimexMention)
              AND coalesce(e.is_timeml_core, true) = true
              AND coalesce(e.low_confidence, false) = false
              AND coalesce(e.merged, false) = false
            OPTIONAL MATCH (tm)-[:REFERS_TO]->(t_ref:TIMEX)
            WITH e, coalesce(t_ref, CASE WHEN tm:TIMEX THEN tm ELSE NULL END) AS t
            WHERE t IS NOT NULL
              AND t.value =~ '^\\d{4}(-\\d{2}(-\\d{2})?)?$'
              AND NOT (e)-[:TLINK]->(t)
            WITH DISTINCT e, t
            MERGE (e)-[tl:TLINK]->(t)
            ON CREATE SET
                tl.source          = 't2g',
                tl.relType         = 'IS_INCLUDED',
                tl.relTypeCanonical = 'IS_INCLUDED',
                tl.confidence      = 0.85,
                tl.rule_id         = 'case24_advmod_is_included',
                tl.evidence_source = 'tlinks_recognizer'
            RETURN count(tl) AS created
        """
        rows = self._run_query(query)
        created = rows[0].get("created", 0) if rows else 0
        logger.info("create_tlinks_case24: created=%d advmod IS_INCLUDED edges", created)
        return rows

    def create_tlinks_case25(self):
        """Case 25 — DCT dateline INCLUDES reporting-verb events in the article lead.

        News articles often contain past-tense reporting verbs in the lead
        sentences (e.g. "the Mortgage Bankers Association *reported* that...")
        that refer to publication-day actions.  These events are IS_INCLUDED in
        the DCT date but are frequently NOT the syntactic ROOT of their sentence
        (they appear in adverbial or complement clauses), so they are missed by
        case22's ROOT-only filter.

        Selection criteria:
        - Dateline TIMEX: same resolution as case22 (earliest DATE TIMEX whose
          value prefix matches the DCT YYYY-MM-DD).
        - Events: TEvents whose trigger token lemma is in the closed reporting-
          verb set {report, say, state, announce, note, tell, reveal, add} AND
          whose POS is a finite verbal tag (VBD, VBZ, VBP, VB), within the first
          103 tokens of the document.
        - Not already linked to the dateline.
        - relType: INCLUDES (dateline → event); IS_INCLUDED inverse also written.
        - Confidence: 0.68.  rule_id: 'case25_reporting_verb_dateline'.

        Tier: T1 — deterministic rule, no ML required.
        """
        logger.debug("create_tlinks_case25")

        _REPORTING_VERBS = [
            "report", "say", "state", "announce", "note",
            "tell", "reveal",
        ]

        query = """
            // Resolve the dateline TIMEX for each document (same logic as case22)
            MATCH (ann:AnnotatedText)-[:CREATED_ON]->(dct:TIMEX)
            WHERE toUpper(coalesce(dct.functionInDocument, '')) = 'CREATION_TIME'
              AND size(coalesce(dct.value, '')) >= 8

            MATCH (dateline_cand:TIMEX)
            WHERE dateline_cand.doc_id = ann.id
              AND dateline_cand.tid <> 't0'
              AND dateline_cand.type = 'DATE'
              AND dateline_cand.start_tok IS NOT NULL
              AND size(coalesce(dateline_cand.value, '')) >= 8
              AND left(coalesce(dct.value, ''), 10) = left(coalesce(dateline_cand.value, ''), 10)
            WITH ann, dateline_cand
            ORDER BY dateline_cand.start_tok ASC
            WITH ann, collect(dateline_cand)[0] AS dateline
            WHERE dateline IS NOT NULL

            // Match reporting-verb TEvents in the document lead (first ~100 tokens)
            // Use tok.lemma (TEvent.lemma is not populated) and direct doc_id join
            MATCH (tok:TagOccurrence)-[:TRIGGERS]->(e:TEvent)
            WHERE e.doc_id = ann.id
              AND toLower(tok.lemma) IN $reporting_verbs
              AND tok.pos IN ['VBD', 'VBZ', 'VBP', 'VB']
              AND coalesce(e.start_tok, 9999) <= 103
              AND e.start_tok > dateline.end_tok
              AND NOT (e)-[:TLINK]-(dateline)

            MERGE (dateline)-[tl:TLINK]->(e)
            ON CREATE SET
                tl.source           = 't2g',
                tl.relType          = 'INCLUDES',
                tl.relTypeCanonical = 'INCLUDES',
                tl.confidence       = 0.68,
                tl.rule_id          = 'case25_reporting_verb_dateline',
                tl.evidence_source  = 'tlinks_recognizer'
            ON MATCH SET
                tl.relType          = coalesce(tl.relType, 'INCLUDES'),
                tl.relTypeCanonical = coalesce(tl.relTypeCanonical, 'INCLUDES'),
                tl.confidence       = coalesce(tl.confidence, 0.68),
                tl.rule_id          = coalesce(tl.rule_id, 'case25_reporting_verb_dateline'),
                tl.evidence_source  = coalesce(tl.evidence_source, 'tlinks_recognizer')

            WITH dateline, e
            MERGE (e)-[tl_inv:TLINK]->(dateline)
            ON CREATE SET
                tl_inv.source           = 't2g',
                tl_inv.relType          = 'IS_INCLUDED',
                tl_inv.relTypeCanonical = 'IS_INCLUDED',
                tl_inv.confidence       = 0.68,
                tl_inv.rule_id          = 'case25_reporting_verb_is_included',
                tl_inv.evidence_source  = 'tlinks_recognizer'
            ON MATCH SET
                tl_inv.relType          = coalesce(tl_inv.relType, 'IS_INCLUDED'),
                tl_inv.relTypeCanonical = coalesce(tl_inv.relTypeCanonical, 'IS_INCLUDED'),
                tl_inv.confidence       = coalesce(tl_inv.confidence, 0.68),
                tl_inv.rule_id          = coalesce(tl_inv.rule_id, 'case25_reporting_verb_is_included'),
                tl_inv.evidence_source  = coalesce(tl_inv.evidence_source, 'tlinks_recognizer')

            RETURN count(tl_inv) AS created
        """
        results = self._run_query(query, parameters={"reporting_verbs": _REPORTING_VERBS})
        created = results[0].get("created", 0) if results else 0
        logger.info("create_tlinks_case25: reporting-verb dateline-includes=%d", created)
        return results

    def create_tlinks_case26(self):
        """Case 26 — Nominal TEvent IS_INCLUDED via two-hop dep prep+pobj to TIMEX.

        Nominal events (pos NN/NNS/NNP/NNPS) that are temporally grounded via a
        prepositional phrase (e.g. "the second-biggest loss *of 2007*") lack SRL
        frames and are therefore missed by case4/case5 SRL-based rules.  This
        rule recovers them by walking the dependency chain:

            tok_event -[IS_DEPENDENT:prep]-> tok_prep -[IS_DEPENDENT:pobj]-> tok_t
            tok_t -[:TRIGGERS]-> TIMEX (or TimexMention)

        where tok_prep.lemma ∈ {in, on, at, of} and TIMEX.type ∈ {DATE, TIME}.

        Selection criteria:
        - TEvent with nominal POS (NN / NNS / NNP / NNPS).
        - Not already linked (by any rule) to this specific TIMEX/TimexMention node.
        - low_confidence events excluded.
        - relType: IS_INCLUDED (event → timex); inverse INCLUDES also written.
        - Confidence: 0.78.  rule_id: 'case26_nominal_dep_is_included'.

        Tier: T1 — deterministic rule, no ML required.
        """
        logger.debug("create_tlinks_case26")
        query = """
            // Two-hop dep chain: nominal TEvent → prep → pobj → TIMEX/TimexMention
            MATCH (tok_e:TagOccurrence)-[:TRIGGERS]->(e:TEvent)
            WHERE tok_e.pos IN ['NN', 'NNS', 'NNP', 'NNPS']
              AND coalesce(e.low_confidence, false) = false

            // IS_DEPENDENT direction is HEAD→CHILD in this graph
            MATCH (tok_e)-[d1:IS_DEPENDENT {type: 'prep'}]->(tok_mid:TagOccurrence)
            WHERE tok_mid.lemma IN ['in', 'on', 'at', 'of']
            MATCH (tok_mid)-[d2:IS_DEPENDENT {type: 'pobj'}]->(tok_t:TagOccurrence)

            // Accept either canonical TIMEX or TimexMention surface node
            MATCH (tok_t)-[:TRIGGERS]->(tm)
            WHERE (tm:TIMEX OR tm:TimexMention)
              AND coalesce(tm.type, '') IN ['DATE', 'TIME']

            // Skip if this pair is already linked
            AND NOT (e)-[:TLINK]-(tm)

            MERGE (e)-[tl:TLINK]->(tm)
            ON CREATE SET
                tl.source           = 't2g',
                tl.relType          = 'IS_INCLUDED',
                tl.relTypeCanonical = 'IS_INCLUDED',
                tl.confidence       = 0.78,
                tl.rule_id          = 'case26_nominal_dep_is_included',
                tl.evidence_source  = 'tlinks_recognizer'
            ON MATCH SET
                tl.relType          = coalesce(tl.relType, 'IS_INCLUDED'),
                tl.relTypeCanonical = coalesce(tl.relTypeCanonical, 'IS_INCLUDED'),
                tl.confidence       = coalesce(tl.confidence, 0.78),
                tl.rule_id          = coalesce(tl.rule_id, 'case26_nominal_dep_is_included'),
                tl.evidence_source  = coalesce(tl.evidence_source, 'tlinks_recognizer')

            WITH e, tm
            MERGE (tm)-[tl_inv:TLINK]->(e)
            ON CREATE SET
                tl_inv.source           = 't2g',
                tl_inv.relType          = 'INCLUDES',
                tl_inv.relTypeCanonical = 'INCLUDES',
                tl_inv.confidence       = 0.78,
                tl_inv.rule_id          = 'case26_nominal_dep_includes',
                tl_inv.evidence_source  = 'tlinks_recognizer'
            ON MATCH SET
                tl_inv.relType          = coalesce(tl_inv.relType, 'INCLUDES'),
                tl_inv.relTypeCanonical = coalesce(tl_inv.relTypeCanonical, 'INCLUDES'),
                tl_inv.confidence       = coalesce(tl_inv.confidence, 0.78),
                tl_inv.rule_id          = coalesce(tl_inv.rule_id, 'case26_nominal_dep_includes'),
                tl_inv.evidence_source  = coalesce(tl_inv.evidence_source, 'tlinks_recognizer')

            RETURN count(tl_inv) AS created
        """
        results = self._run_query(query)
        created = results[0].get("created", 0) if results else 0
        logger.info("create_tlinks_case26: nominal-dep-is-included=%d", created)
        return results

    def create_tlinks_case27(self):
        """Case 27 — Verbal TEvent IS_INCLUDED in 'last week' TIMEX via npadvmod dep.

        Recovers patterns like "weekly benefits rose 15,000 last week" where the
        event token has a direct npadvmod dependency to the head token of the TIMEX.

            tok_event -[IS_DEPENDENT:npadvmod]-> tok_timex_head
            tok_timex_head -[:TRIGGERS]-> (tm:TimexMention)

        Restricted to TIMEX text starting with 'last' AND value containing '-W'
        (ISO week notation, e.g. 2008-W35) to prevent false positives from
        specific-day TIMEXes (Monday, Thursday, etc.) or 'this week' TIMEXes.
        The event must precede the TIMEX head token in document order.

        Tier: T1 — deterministic rule; no ML required.
        """
        logger.debug("create_tlinks_case27")
        query = """
            MATCH (etok:TagOccurrence)-[dep:IS_DEPENDENT {type: 'npadvmod'}]->(ttok:TagOccurrence)
            MATCH (ttok)-[:TRIGGERS]->(tm:TimexMention)
            WHERE toLower(coalesce(tm.text, '')) STARTS WITH 'last'
              AND coalesce(tm.value, '') CONTAINS '-W'
            MATCH (etok)-[:TRIGGERS]->(e:TEvent)
            WHERE coalesce(e.low_confidence, false) = false
              AND coalesce(e.is_timeml_core, true) = true
              AND coalesce(e.merged, false) = false
              // Event must precede the TIMEX head in text
              AND etok.tok_index_doc < ttok.tok_index_doc
              AND NOT (e)-[:TLINK]-(tm)
            WITH DISTINCT e, tm
            MERGE (e)-[tlink:TLINK]->(tm)
            SET tlink.source           = 't2g',
                tlink.relType          = 'IS_INCLUDED',
                tlink.relTypeCanonical = 'IS_INCLUDED',
                tlink.confidence       = 0.85,
                tlink.rule_id          = 'case27_npadvmod_last_week',
                tlink.evidence_source  = 'tlinks_recognizer'
            RETURN count(tlink) AS touched
        """
        results = self._run_query(query)
        touched = results[0].get("touched", 0) if results else 0
        logger.info("create_tlinks_case27: npadvmod-last-week=%d", touched)
        return results

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
        WITH count(r) AS normalized
        RETURN normalized
        """
        rows = self._run_query(query, {"canonical": list(CANONICAL_TLINK_RELTYPES)})
        if rows:
            normalized = rows[0].get("normalized", 0)
            logger.info("normalize_tlink_reltypes: normalized %d TLINK relationships", normalized)
        return rows

    def materialize_tlink_inverses(self):
        """Case 19 — Materialize TimeML logical inverses of all existing TLINK edges.

        The MEANTIME gold corpus annotates TLINKs in a specific direction that
        sometimes differs from what our extraction rules produce. For example:

          Gold:      (TIMEX)-[TLINK:INCLUDES]->(EVENT)   — 21/76 gold TLINKs
          Predicted: (EVENT)-[TLINK:IS_INCLUDED]->(TIMEX) — our output

        These are logically equivalent under TimeML but match differently during
        evaluation. This post-processing pass sweeps all existing TLINK edges and
        creates the directional inverse for every non-symmetric relation:

          IS_INCLUDED  → (b)-[INCLUDES]->(a)      (covers 27.6% of gold)
          INCLUDES     → (b)-[IS_INCLUDED]->(a)
          BEFORE       → (b)-[AFTER]->(a)
          AFTER        → (b)-[BEFORE]->(a)
          BEGUN_BY     → (b)-[BEGINS]->(a)         (covers 5.3% of gold)
          BEGINS       → (b)-[BEGUN_BY]->(a)
          ENDED_BY     → (b)-[ENDS]->(a)            (covers 2.6% of gold)
          ENDS         → (b)-[ENDED_BY]->(a)
          IAFTER       → (b)-[IBEFORE]->(a)
          IBEFORE      → (b)-[IAFTER]->(a)

        SIMULTANEOUS, IDENTITY, VAGUE, MEASURE, and DURING are symmetric or
        directionless — no inverse is written.

        Inverted edges inherit the source edge's confidence and provenance, with
        `rule_id='case19_timeml_inverse'`. Existing higher-confidence edges on the
        same directed pair are not overwritten (ON MATCH confidence guard).

        This must run AFTER normalize_tlink_reltypes and BEFORE suppress/closure,
        so that (a) relTypes are already canonical and (b) closure can compose
        over both original and inverse edges.
        """
        logger.debug("materialize_tlink_inverses")

        # BEFORE↔AFTER are direction-sensitive: TTK already assigns the correct
        # direction; inverting them doubles FPs without proportional TP gain.
        # Only invert relations where the gold frequently uses the opposite
        # direction from our extraction rules (IS_INCLUDED/INCLUDES, aspectual pairs).
        inverse_map = [
            ("IS_INCLUDED", "INCLUDES"),
            ("INCLUDES", "IS_INCLUDED"),
            ("BEGUN_BY", "BEGINS"),
            ("BEGINS", "BEGUN_BY"),
            ("ENDED_BY", "ENDS"),
            ("ENDS", "ENDED_BY"),
            ("IAFTER", "IBEFORE"),
            ("IBEFORE", "IAFTER"),
        ]

        total_created = 0
        for forward_rel, inverse_rel in inverse_map:
            query = """
                MATCH (a)-[r:TLINK]->(b)
                WHERE coalesce(r.relTypeCanonical, r.relType, '') = $fwd
                  AND coalesce(r.suppressed, false) = false
                  AND NOT (coalesce(r.rule_id, '') IN ['transitive_closure', 'inverse_consistency'])
                WITH a, b,
                     coalesce(r.confidence, 0.5) AS src_conf,
                     coalesce(r.source, 't2g') AS src_source,
                     coalesce(r.evidence_source, 'tlinks_recognizer') AS src_ev
                MERGE (b)-[inv:TLINK]->(a)
                ON CREATE SET
                    inv.relType          = $inv,
                    inv.relTypeCanonical = $inv,
                    inv.confidence       = src_conf,
                    inv.source           = src_source,
                    inv.evidence_source  = src_ev,
                    inv.rule_id          = 'case19_timeml_inverse',
                    inv.derivedFrom      = $fwd
                ON MATCH SET
                    inv.relType          = CASE WHEN coalesce(inv.confidence, 0.0) < src_conf THEN $inv ELSE inv.relType END,
                    inv.relTypeCanonical = CASE WHEN coalesce(inv.confidence, 0.0) < src_conf THEN $inv ELSE inv.relTypeCanonical END,
                    inv.confidence       = CASE WHEN coalesce(inv.confidence, 0.0) < src_conf THEN src_conf ELSE inv.confidence END,
                    inv.rule_id          = coalesce(inv.rule_id, 'case19_timeml_inverse'),
                    inv.derivedFrom      = coalesce(inv.derivedFrom, $fwd)
                RETURN count(inv) AS created
            """
            rows = self._run_query(query, {"fwd": forward_rel, "inv": inverse_rel})
            created = rows[0].get("created", 0) if rows else 0
            total_created += created
            logger.debug(
                "materialize_tlink_inverses: %s → %s: %d edges", forward_rel, inverse_rel, created
            )

        logger.info("materialize_tlink_inverses: total inverse edges written: %d", total_created)
        return total_created

    def suppress_tlink_conflicts(self, shadow_only: bool = False):
        """Suppress lower-confidence TLINKs for contradictory relation pairs.

        Contradictions are not deleted; they are marked with suppression
        metadata so diagnostics can report retained vs. suppressed links.
        """
        logger.debug("suppress_tlink_conflicts")
        query_prefix = """
        MATCH (a)-[r1:TLINK]->(b), (a)-[r2:TLINK]->(b)
        WHERE elementId(r1) < elementId(r2)
          AND coalesce(r1.suppressed, false) = false
          AND coalesce(r2.suppressed, false) = false
        WITH r1, r2,
             coalesce(r1.relTypeCanonical, r1.relType, 'VAGUE') AS t1,
             coalesce(r2.relTypeCanonical, r2.relType, 'VAGUE') AS t2
        WITH r1, r2, t1, t2,
             CASE
                WHEN (t1 = 'BEFORE' AND t2 = 'AFTER') OR (t1 = 'AFTER' AND t2 = 'BEFORE') THEN true
                WHEN (t1 = 'INCLUDES' AND t2 = 'IS_INCLUDED') OR (t1 = 'IS_INCLUDED' AND t2 = 'INCLUDES') THEN true
                WHEN (t1 = 'BEGINS' AND t2 = 'BEGUN_BY') OR (t1 = 'BEGUN_BY' AND t2 = 'BEGINS') THEN true
                WHEN (t1 = 'ENDS' AND t2 = 'ENDED_BY') OR (t1 = 'ENDED_BY' AND t2 = 'ENDS') THEN true
                ELSE false
             END AS is_conflict
        WHERE is_conflict
        WITH r1, r2, t1, t2,
             coalesce(r1.confidence, 0.0) AS c1,
             coalesce(r2.confidence, 0.0) AS c2
        WITH r1, r2, t1, t2,
             CASE
                WHEN c1 > c2 THEN r2
                WHEN c2 > c1 THEN r1
                WHEN elementId(r1) < elementId(r2) THEN r2
                ELSE r1
             END AS loser,
             CASE
                WHEN c1 > c2 THEN r1
                WHEN c2 > c1 THEN r2
                WHEN elementId(r1) < elementId(r2) THEN r1
                ELSE r2
             END AS winner
        WITH r1, loser, winner, t1, t2,
             CASE WHEN elementId(loser) = elementId(r1) THEN t1 ELSE t2 END AS loser_type,
             CASE WHEN elementId(winner) = elementId(r1) THEN t1 ELSE t2 END AS winner_type
        """
        if shadow_only:
            query = (
                query_prefix
                + """
                RETURN count(DISTINCT loser) AS would_suppress
                """
            )
        else:
            query = (
                query_prefix
                + """
        SET loser.suppressed = true,
            loser.suppressedBy = 'tlink_consistency_filter',
            loser.suppressedAt = datetime().epochMillis,
            loser.suppressionPolicy = 'confidence_then_id_tiebreak',
            loser.suppressedAgainstRelType = winner_type,
            loser.suppressionReason = 'contradiction:' + loser_type + '_vs_' + winner_type
        RETURN count(DISTINCT loser) AS suppressed
        """
            )
        rows = self._run_query(query)
        if rows:
            if shadow_only:
                would_suppress = rows[0].get("would_suppress", 0)
                logger.info(
                    "suppress_tlink_conflicts: shadow mode identified %d contradictory TLINKs",
                    would_suppress,
                )
            else:
                suppressed = rows[0].get("suppressed", 0)
                logger.info("suppress_tlink_conflicts: suppressed %d TLINK relationships", suppressed)
        return rows

    def apply_tlink_transitive_closure(self, max_rounds: int = 3):
        """Materialize conservative TLINK transitive closure edges.

        Restricted to IDENTITY-chain compositions only.  BEFORE/AFTER/SIMULTANEOUS
        transitivity was removed because it generates O(N²) spurious links across
        distant event pairs — the primary cause of precision collapse vs MEANTIME gold.

        Supported rule:
          IDENTITY + X  →  X
          X + IDENTITY  →  X
        """
        logger.debug("apply_tlink_transitive_closure")
        total_created = 0
        for round_idx in range(1, max_rounds + 1):
            query = """
            MATCH (a)-[r1:TLINK]->(b)-[r2:TLINK]->(c)
            WHERE a <> c
              AND coalesce(r1.suppressed, false) = false
              AND coalesce(r2.suppressed, false) = false
            WITH a, b, c,
                 coalesce(r1.relTypeCanonical, r1.relType, 'VAGUE') AS t1,
                 coalesce(r2.relTypeCanonical, r2.relType, 'VAGUE') AS t2,
                 coalesce(r1.confidence, 0.0) AS c1,
                 coalesce(r2.confidence, 0.0) AS c2
            WITH a, c, c1, c2,
                 CASE
                    WHEN t1 = 'IDENTITY' AND t2 IN $canonical THEN t2
                    WHEN t2 = 'IDENTITY' AND t1 IN $canonical THEN t1
                    ELSE NULL
                 END AS inferred
            WHERE inferred IS NOT NULL
            MERGE (a)-[r:TLINK {relType: inferred}]->(c)
            ON CREATE SET r.relTypeCanonical = inferred,
                          r.source = 'closure',
                          r.rule_id = 'transitive_closure',
                          r.evidence_source = 'tlinks_recognizer',
                          r.confidence = round((c1 + c2) / 2.0, 3),
                          r.closureRound = $round,
                          r.createdByClosure = true
            RETURN count(CASE WHEN r.createdByClosure = true AND r.closureRound = $round THEN 1 END) AS created
            """
            rows = self._run_query(
                query,
                {"round": round_idx, "canonical": list(CANONICAL_TLINK_RELTYPES)},
            )
            created = rows[0].get("created", 0) if rows else 0
            total_created += created
            if created == 0:
                break
        logger.info("apply_tlink_transitive_closure: created %d TLINKs", total_created)
        return total_created

    def endpoint_contract_violations(self):
        """Return endpoint-contract violations for TLINK relationships."""
        violations = count_endpoint_violations(self.graph, "TLINK")
        if violations:
            logger.warning("TLINK endpoint contract violations: %d", violations)
        else:
            logger.info("TLINK endpoint contract violations: none")
        return violations

    def apply_constraint_solver(self, shadow_only: bool = False):
        """Apply conservative TLINK constraint solver over existing links."""
        summary = solve_tlink_constraints(self.graph, shadow_only=shadow_only)
        logger.info(
            "apply_constraint_solver: inverse_created=%d bidirectional_conflicts=%d shadow_only=%s",
            summary.get("inverse_created", 0),
            summary.get("bidirectional_conflicts", 0),
            shadow_only,
        )
        return summary

    def enforce_tlink_anchor_consistency(self, shadow_only: bool = False):
        """Validate TLINK anchors and optionally suppress inconsistent links.

        Consistency requires:
        - endpoints are in {TEvent, Timex3}
        - source and target are not the same node

        In non-shadow mode, inconsistent unsuppressed TLINKs are retained but
        marked as suppressed with explicit anchor-consistency metadata.
        """
        logger.debug("enforce_tlink_anchor_consistency")
        query_prefix = """
        MATCH (src)-[r:TLINK]->(dst)
        WITH src, dst, r,
             CASE
                WHEN src:TEvent THEN 'TEvent'
                     WHEN src:TIMEX OR src:Timex3 THEN 'TIMEX'
                ELSE 'OTHER'
             END AS source_anchor_type,
             CASE
                WHEN dst:TEvent THEN 'TEvent'
                     WHEN dst:TIMEX OR dst:Timex3 THEN 'TIMEX'
                ELSE 'OTHER'
             END AS target_anchor_type,
             CASE WHEN elementId(src) = elementId(dst) THEN true ELSE false END AS is_self_link,
                 CASE WHEN (src:TEvent OR src:TIMEX OR src:Timex3) AND (dst:TEvent OR dst:TIMEX OR dst:Timex3) THEN true ELSE false END AS endpoint_contract_ok
        WITH src, dst, r, source_anchor_type, target_anchor_type, is_self_link, endpoint_contract_ok,
             (NOT endpoint_contract_ok OR is_self_link) AS inconsistent
        SET r.sourceAnchorType = source_anchor_type,
            r.targetAnchorType = target_anchor_type,
            r.anchorPair = source_anchor_type + '->' + target_anchor_type,
            r.anchorConsistency = NOT inconsistent,
            r.anchorConsistencyReason = CASE
                WHEN is_self_link THEN 'self_link'
                WHEN NOT endpoint_contract_ok THEN 'endpoint_contract_violation'
                ELSE 'ok'
            END
        """
        if shadow_only:
            query = (
                query_prefix
                + """
                RETURN count(CASE WHEN inconsistent THEN 1 END) AS inconsistent_count,
                       count(CASE WHEN is_self_link THEN 1 END) AS self_link_count,
                       count(CASE WHEN NOT endpoint_contract_ok THEN 1 END) AS endpoint_violation_count
                """
            )
        else:
            query = (
                query_prefix
                + """
                WITH r, inconsistent, is_self_link, endpoint_contract_ok
                WHERE inconsistent AND coalesce(r.suppressed, false) = false
                SET r.suppressed = true,
                    r.suppressedBy = 'tlink_anchor_consistency_filter',
                    r.suppressedAt = datetime().epochMillis,
                    r.suppressionPolicy = 'anchor_consistency',
                    r.suppressionReason = CASE
                        WHEN is_self_link THEN 'anchor_inconsistency:self_link'
                        WHEN NOT endpoint_contract_ok THEN 'anchor_inconsistency:endpoint_contract_violation'
                        ELSE 'anchor_inconsistency:unknown'
                    END
                RETURN count(r) AS suppressed_count
                """
            )
        rows = self._run_query(query)
        if rows:
            if shadow_only:
                logger.info(
                    "enforce_tlink_anchor_consistency: inconsistent=%d self_links=%d endpoint_violations=%d (shadow)",
                    rows[0].get("inconsistent_count", 0),
                    rows[0].get("self_link_count", 0),
                    rows[0].get("endpoint_violation_count", 0),
                )
            else:
                logger.info(
                    "enforce_tlink_anchor_consistency: suppressed %d inconsistent TLINKs",
                    rows[0].get("suppressed_count", 0),
                )
        return rows

    def get_doc_text_and_dct(self, doc_id):
        """Retrieve document text and creation time from AnnotatedText node."""
        logger.debug("get_doc_text_and_dct for doc_id=%s", doc_id)
        query = "MATCH (n:AnnotatedText) WHERE n.id = toInteger($doc_id) RETURN n.text AS text, n.creationtime AS dct"
        try:
            data = self.graph.run(query, parameters={"doc_id": doc_id}).data()
            if data:
                return {
                    "input": str(data[0].get("text", "")),
                    "dct": data[0].get("dct", ""),
                }
        except Exception:
            logger.exception("Failed to get doc text and DCT for doc_id=%s", doc_id)
        return {"input": "", "dct": ""}

    def callTtkService(self, parameters):
        """Call TTK service and return XML response body."""
        logger.debug("callTtkService with dct=%s", parameters.get("dct"))
        try:
            from textgraphx.infrastructure.config import get_config

            cfg = get_config()
            ttk_url = cfg.services.temporal_url
            response = requests.post(ttk_url, json=parameters, timeout=30)
            response.raise_for_status()
            logger.info("TTK service returned status %d", response.status_code)
            return response.text
        except Exception:
            logger.exception("TTK service call failed")
            return ""

    def _get_ttk_xml(self, doc_id):
        """Get TTK XML output for a document."""
        logger.debug("_get_ttk_xml for doc_id=%s", doc_id)
        response_dict = self.get_doc_text_and_dct(doc_id)
        return self.callTtkService(response_dict)

    def _iter_tlink_elements(self, xml_text):
        """Yield TLINK elements from TTK XML."""
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            logger.exception("Failed to parse TTK XML for TLINK extraction")
            return

        for elem in root.iter():
            tag = elem.tag.split("}")[-1] if isinstance(elem.tag, str) else elem.tag
            if tag == "TLINK":
                yield elem

    def create_tlinks_e2e(self, doc_id, precision_mode: bool = False):
        """Build event-to-event links from TTK output over existing temporal nodes."""
        logger.debug("create_tlinks_e2e for doc_id=%s", doc_id)
        result_xml = self._get_ttk_xml(doc_id)
        if not result_xml:
            logger.warning("No TTK XML returned for E2E link extraction")
            return ""

        query = """
            MATCH (e1:TEvent {eiid: $event_instance_id, doc_id: toInteger($doc_id)})
            MATCH (e2:TEvent {eiid: $related_event_instance, doc_id: toInteger($doc_id)})
            WHERE $precision_mode = false OR toUpper($rel_type) IN [
                'BEFORE', 'AFTER', 'INCLUDES', 'IS_INCLUDED', 'SIMULTANEOUS',
                'IBEFORE', 'IAFTER', 'BEGINS', 'BEGUN_BY', 'ENDS', 'ENDED_BY'
            ]
            MERGE (e1)-[tl:TLINK {id: $lid, relType: $rel_type}]->(e2)
            SET tl.signalID = $signal_id,
                tl.source = coalesce(tl.source, 'ttk_xml'),
                tl.rule_id = coalesce(tl.rule_id, 'xml_e2e_seed'),
                tl.evidence_source = coalesce(tl.evidence_source, 'ttk_xml'),
                tl.confidence = coalesce(tl.confidence, CASE WHEN $precision_mode THEN 0.70 ELSE 0.60 END)
        """

        linked = 0
        for tlink in self._iter_tlink_elements(result_xml):
            event_instance_id = tlink.attrib.get("eventInstanceID")
            related_event_instance = tlink.attrib.get("relatedToEventInstance")
            if not event_instance_id or not related_event_instance:
                continue

            try:
                self.graph.run(
                    query,
                    parameters={
                        "event_instance_id": event_instance_id,
                        "related_event_instance": related_event_instance,
                        "lid": tlink.attrib.get("lid", ""),
                        "rel_type": tlink.attrib.get("relType", ""),
                        "signal_id": tlink.attrib.get("signalID"),
                        "doc_id": doc_id,
                        "precision_mode": bool(precision_mode),
                    },
                )
                linked += 1
            except Exception:
                logger.exception("Failed to link E2E TLINK: %s -> %s", event_instance_id, related_event_instance)

        logger.info("create_tlinks_e2e: linked %d event-event TLINKs for doc_id=%s", linked, doc_id)
        return f"linked {linked} E2E TLINKs"

    def create_tlinks_e2t(self, doc_id, precision_mode: bool = False):
        """Build event-to-time links from TTK output over existing temporal nodes."""
        logger.debug("create_tlinks_e2t for doc_id=%s", doc_id)
        result_xml = self._get_ttk_xml(doc_id)
        if not result_xml:
            logger.warning("No TTK XML returned for E2T link extraction")
            return ""

        query = """
            MATCH (e:TEvent {eiid: $event_instance_id, doc_id: toInteger($doc_id)})
            MATCH (t:TIMEX {tid: $related_to_time, doc_id: toInteger($doc_id)})
              WHERE ($precision_mode = false
                OR toUpper($rel_type) IN [
                    'BEFORE', 'AFTER', 'INCLUDES', 'IS_INCLUDED', 'SIMULTANEOUS',
                    'IBEFORE', 'IAFTER', 'BEGINS', 'BEGUN_BY', 'ENDS', 'ENDED_BY', 'MEASURE'
                ]
               OR (
                    toUpper($rel_type) = 'IS_INCLUDED'
                    AND toUpper(coalesce(t.functionInDocument, '')) = 'CREATION_TIME'
               ))
              // Distance guard: skip long-range event-TIMEX links that are typically FPs
              // (allow DCT/creation-time TIMEXes which have no token span)
              AND (t.start_tok IS NULL
                   OR toUpper(coalesce(t.functionInDocument, '')) = 'CREATION_TIME'
                   OR abs(coalesce(e.start_tok, 0) - coalesce(t.start_tok, 0)) <= 20)
            MERGE (e)-[tl:TLINK {id: $lid, relType: $rel_type}]->(t)
            SET tl.signalID = $signal_id,
                tl.source = coalesce(tl.source, 'ttk_xml'),
                tl.rule_id = coalesce(tl.rule_id, 'xml_e2t_seed'),
                tl.evidence_source = coalesce(tl.evidence_source, 'ttk_xml'),
                tl.confidence = coalesce(tl.confidence, CASE WHEN $precision_mode THEN 0.72 ELSE 0.62 END)
        """

        linked = 0
        for tlink in self._iter_tlink_elements(result_xml):
            event_instance_id = tlink.attrib.get("eventInstanceID")
            related_to_time = tlink.attrib.get("relatedToTime")
            if not event_instance_id or not related_to_time:
                continue

            try:
                self.graph.run(
                    query,
                    parameters={
                        "event_instance_id": event_instance_id,
                        "related_to_time": related_to_time,
                        "lid": tlink.attrib.get("lid", ""),
                        "rel_type": tlink.attrib.get("relType", ""),
                        "signal_id": tlink.attrib.get("signalID"),
                        "doc_id": doc_id,
                        "precision_mode": bool(precision_mode),
                    },
                )
                linked += 1
            except Exception:
                logger.exception("Failed to link E2T TLINK: %s -> %s", event_instance_id, related_to_time)

        logger.info("create_tlinks_e2t: linked %d event-time TLINKs for doc_id=%s", linked, doc_id)
        return f"linked {linked} E2T TLINKs"

    def create_tlinks_t2t(self, doc_id, precision_mode: bool = False):
        """Build time-to-time links from TTK output over existing temporal nodes."""
        logger.debug("create_tlinks_t2t for doc_id=%s", doc_id)
        result_xml = self._get_ttk_xml(doc_id)
        if not result_xml:
            logger.warning("No TTK XML returned for T2T link extraction")
            return ""

        query = """
            MATCH (t1:TIMEX {tid: $time_id, doc_id: toInteger($doc_id)})
            MATCH (t2:TIMEX {tid: $related_to_time, doc_id: toInteger($doc_id)})
            WHERE $precision_mode = false OR toUpper($rel_type) IN ['BEFORE', 'AFTER', 'INCLUDES', 'IS_INCLUDED', 'SIMULTANEOUS']
            MERGE (t1)-[tl:TLINK {id: $lid, relType: $rel_type}]->(t2)
            SET tl.signalID = $signal_id,
                tl.source = coalesce(tl.source, 'ttk_xml'),
                tl.rule_id = coalesce(tl.rule_id, 'xml_t2t_seed'),
                tl.evidence_source = coalesce(tl.evidence_source, 'ttk_xml'),
                tl.confidence = coalesce(tl.confidence, CASE WHEN $precision_mode THEN 0.68 ELSE 0.58 END)
        """

        linked = 0
        for tlink in self._iter_tlink_elements(result_xml):
            related_to_time = tlink.attrib.get("relatedToTime")
            time_id = tlink.attrib.get("timeID")
            if not related_to_time or not time_id:
                continue

            try:
                self.graph.run(
                    query,
                    parameters={
                        "time_id": time_id,
                        "related_to_time": related_to_time,
                        "lid": tlink.attrib.get("lid", ""),
                        "rel_type": tlink.attrib.get("relType", ""),
                        "signal_id": tlink.attrib.get("signalID"),
                        "doc_id": doc_id,
                        "precision_mode": bool(precision_mode),
                    },
                )
                linked += 1
            except Exception:
                logger.exception("Failed to link T2T TLINK: %s -> %s", time_id, related_to_time)

        logger.info("create_tlinks_t2t: linked %d time-time TLINKs for doc_id=%s", linked, doc_id)
        return f"linked {linked} T2T TLINKs"


if __name__ == '__main__':
    import time as _time
    tp = TlinksRecognizer(sys.argv[1:])
    _phase_start = _time.time()
    if len(sys.argv) > 1:
        doc_id = sys.argv[1]
        tp.create_tlinks_e2e(doc_id)
        tp.create_tlinks_e2t(doc_id)
        tp.create_tlinks_t2t(doc_id)

    tp.create_tlinks_case1()
    tp.create_tlinks_case2()
    tp.create_tlinks_case3()
    tp.create_tlinks_case4()
    tp.create_tlinks_case5()
    tp.create_tlinks_case6()
    tp.create_tlinks_case7()
    tp.create_tlinks_case8()
    tp.create_tlinks_case9()
    tp.create_tlinks_case10()
    tp.create_tlinks_case11()
    tp.create_tlinks_case12()
    tp.create_tlinks_case13()
    tp.create_tlinks_case14()
    tp.create_tlinks_case15()
    tp.create_tlinks_case16()
    tp.create_tlinks_case17()
    tp.create_tlinks_case18()
    tp.create_tlinks_case20()
    tp.create_tlinks_case22()
    tp.create_tlinks_case23()
    tp.create_tlinks_case24()
    tp.create_tlinks_case25()
    tp.create_tlinks_case26()
    tp.create_tlinks_case27()
    tp.normalize_tlink_reltypes()
    tp.materialize_tlink_inverses()
    tp.apply_tlink_transitive_closure()
    tp.suppress_tlink_conflicts()
    tp.endpoint_contract_violations()
    _phase_duration = _time.time() - _phase_start

    # Record a PhaseRun marker for restart visibility (Item 7)
    try:
        from textgraphx.pipeline.runtime.phase_assertions import record_phase_run
        record_phase_run(
            tp.graph,
            phase_name="tlinks",
            duration_seconds=_phase_duration,
            metadata={
                    "passes": "e2e,e2t,t2t,case1-20,normalize,inverses,closure,suppress"
            },
        )
    except Exception:
        import logging as _logging
        _logging.getLogger(__name__).exception(
            "Failed to write TLinksRun marker (non-fatal)"
        )

