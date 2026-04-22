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
from textgraphx.reasoning_contracts import count_endpoint_violations
from textgraphx.temporal_constraints import solve_tlink_constraints
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
                    with *
                    merge (e1)-[tl:TLINK]-(e2)
                    with *
                    set tl.source = 't2g', tl.confidence = 0.80, tl.rule_id = 'case3_eventive_head', tl.evidence_source = 'tlinks_recognizer',
                    tl.relType = CASE
                        WHEN fa.signal in ['after'] THEN 'AFTER'
                        WHEN fa.signal in ['before'] THEN 'BEFORE'
                        WHEN fa.signal in ['following'] THEN 'SIMULTANEOUS'
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
            OPTIONAL MATCH (tm)-[:REFERS_TO]->(t_ref:TIMEX)
            WITH h, fa, e, coalesce(t_ref, CASE WHEN tm:TIMEX OR tm:Timex3 THEN tm ELSE NULL END) AS t
            WHERE fa.headTokenIndex = h.tok_index_doc AND t IS NOT NULL
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
            OPTIONAL MATCH (tm)-[:REFERS_TO]->(t_ref:TIMEX)
            WITH pobj, fa, e, coalesce(t_ref, CASE WHEN tm:TIMEX OR tm:Timex3 THEN tm ELSE NULL END) AS t,
                 toLower(coalesce(fa.head, '')) AS prep_head
            WHERE fa.end_tok = pobj.tok_index_doc
              AND prep_head IN ['in', 'on', 'at', 'for', 'since', 'during', 'before', 'after', 'by', 'until']
              AND t IS NOT NULL
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
                    WHEN t.type IN ['TIME', 'DATE', 'DURATION'] AND prep_head IN ['on', 'in'] THEN 'IS_INCLUDED'
                    ELSE coalesce(tlink.relType, 'VAGUE')
                END
            RETURN count(tlink) AS touched
        """
        return self._run_query(query)

    def create_tlinks_case6(self):
        logger.debug("create_tlinks_case6")
        query = """ MATCH p = (e:TEvent)<-[:TRIGGERS]-(t:TagOccurrence)<-[:HAS_TOKEN]-(s:Sentence)<-[:CONTAINS_SENTENCE]-(ann:AnnotatedText)-[:CREATED_ON]->(dct)
                WHERE dct:TIMEX OR dct:Timex3
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
        WHERE id(e_main) <> id(e_sub)
          AND em_sub.clauseType IN ['SUBORDINATE', 'COMPLEMENT']
          AND em_sub.scopeType IN ['TEMPORAL_SCOPE', 'LOCAL_SCOPE']
          AND fa.syntacticType = 'EVENTIVE'
          AND toLower(coalesce(fa.signal, '')) IN ['before', 'after']
          AND toLower(coalesce(fa.complement, '')) = toLower(coalesce(tok_sub.text, ''))
          AND any(cue IN coalesce(em_sub.temporalCueHeads, []) WHERE cue IN ['before', 'after'])
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

    def suppress_tlink_conflicts(self, shadow_only: bool = False):
        """Suppress lower-confidence TLINKs for contradictory relation pairs.

        Contradictions are not deleted; they are marked with suppression
        metadata so diagnostics can report retained vs. suppressed links.
        """
        logger.debug("suppress_tlink_conflicts")
        query_prefix = """
        MATCH (a)-[r1:TLINK]->(b), (a)-[r2:TLINK]->(b)
        WHERE id(r1) < id(r2)
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
                WHEN id(r1) < id(r2) THEN r2
                ELSE r1
             END AS loser,
             CASE
                WHEN c1 > c2 THEN r1
                WHEN c2 > c1 THEN r2
                WHEN id(r1) < id(r2) THEN r1
                ELSE r2
             END AS winner
        WITH r1, loser, winner, t1, t2,
             CASE WHEN id(loser) = id(r1) THEN t1 ELSE t2 END AS loser_type,
             CASE WHEN id(winner) = id(r1) THEN t1 ELSE t2 END AS winner_type
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

        Supports high-precision closure rules:
        BEFORE+BEFORE=>BEFORE, AFTER+AFTER=>AFTER,
        IDENTITY+X=>X, X+IDENTITY=>X.
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
                    WHEN t1 = 'BEFORE' AND t2 = 'BEFORE' THEN 'BEFORE'
                    WHEN t1 = 'AFTER' AND t2 = 'AFTER' THEN 'AFTER'
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
             CASE WHEN id(src) = id(dst) THEN true ELSE false END AS is_self_link,
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
            from textgraphx.config import get_config

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
              WHERE $precision_mode = false
                OR toUpper($rel_type) IN [
                    'BEFORE', 'AFTER', 'INCLUDES', 'IS_INCLUDED', 'SIMULTANEOUS',
                    'IBEFORE', 'IAFTER', 'BEGINS', 'BEGUN_BY', 'ENDS', 'ENDED_BY', 'MEASURE'
                ]
               OR (
                    toUpper($rel_type) = 'IS_INCLUDED'
                    AND toUpper(coalesce(t.functionInDocument, '')) = 'CREATION_TIME'
               )
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
    tp.normalize_tlink_reltypes()
    tp.apply_tlink_transitive_closure()
    tp.suppress_tlink_conflicts()
    tp.endpoint_contract_violations()
    _phase_duration = _time.time() - _phase_start

    # Record a PhaseRun marker for restart visibility (Item 7)
    try:
        from textgraphx.phase_assertions import record_phase_run
        record_phase_run(
            tp.graph,
            phase_name="tlinks",
            duration_seconds=_phase_duration,
            metadata={
                    "passes": "e2e,e2t,t2t,case1,case2,case3,case4,case5,case6"
            },
        )
    except Exception:
        import logging as _logging
        _logging.getLogger(__name__).exception(
            "Failed to write TLinksRun marker (non-fatal)"
        )

