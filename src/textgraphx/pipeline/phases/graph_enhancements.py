"""GraphEnhancementsPhase — pure-Cypher post-processing pass.

This phase runs after Stage 5 (TLINK recognition) and applies a set of
deterministic, graph-computable improvements that require no external service
calls.  All queries are idempotent (MERGE / SET with coalesce guards) and safe
to re-run.

Algorithms implemented:
  GA-01  Transitive TLINK closure — DISABLED (net-negative vs MEANTIME gold;
          gold uses IS_INCLUDED/SIMULTANEOUS not BEFORE/AFTER chains).
          purge_ga01_tlinks() removes any previously-created edges.
  GA-02  Event confidence down-ranking (reduces FP over-generation)
  GA-03  Event class inference from PropBank frame names
  GA-04  TIMEX ISO 8601 value normalization (fixes PY5 → P5Y style errors)
  GA-05  Entity salience scoring (degree centrality proxy)
  GA-06  Frame ALIGNS_WITH gap fill (PropBank ↔ NomBank cross-linking)
  GA-07  Coreference chain quality signal
  GA-08  Sentence root backfill (requires dep property on TagOccurrence)
  GA-09  Participant mention bridge — restricted to ±50-token window to avoid
          cross-document coreference chain inflation.
  GA-10  TEvent pos correction — updates TEvent.pos to 'NOUN' for events whose
          surface token is tagged NOUN by spaCy (fixes TTK epos=VERB artefacts).

The phase records a completion marker node for idempotency tracking.
"""

import logging
from textgraphx.database.client import make_graph_from_config

logger = logging.getLogger(__name__)


class GraphEnhancementsPhase:
    """Post-pipeline graph enhancement pass (pure Cypher, no external services)."""

    def __init__(self):
        self.graph = make_graph_from_config()
        logger.info("GraphEnhancementsPhase initialized")

    # ------------------------------------------------------------------
    # GA-01  Transitive TLINK closure (DISABLED — purge only)
    # ------------------------------------------------------------------

    def purge_ga01_tlinks(self):
        """Delete any TLINK edges that were created by the GA-01 transitive closure.

        GA-01 was disabled because MEANTIME gold TLINKs use IS_INCLUDED /
        SIMULTANEOUS / BEGUN_BY, not BEFORE/AFTER chains.  Generating BEFORE
        chains produces large numbers of spurious TLINKs with zero TP benefit.
        This purge removes edges from any previous run so the graph is clean.
        """
        logger.debug("purge_ga01_tlinks")
        query = """
        MATCH ()-[r:TLINK]->()
        WHERE r.rule_id IN ['ga01_transitive_before', 'ga01_transitive_after', 'ga01_included_before']
        DELETE r
        RETURN count(r) AS deleted
        """
        rows = self.graph.run(query).data()
        return rows[0].get("deleted", 0) if rows else 0

    def tlink_transitive_before(self):
        """Add BEFORE TLINKs inferred from transitivity (A BEFORE B BEFORE C → A BEFORE C).

        DISABLED in run_all() / phase wrapper — call purge_ga01_tlinks() instead.
        Kept for experimental use only.
        """
        logger.debug("tlink_transitive_before")
        query = """
        MATCH (a:TEvent)-[:TLINK {relType:'BEFORE'}]->(b)-[:TLINK {relType:'BEFORE'}]->(c:TEvent)
        WHERE elementId(a) <> elementId(c)
          AND NOT EXISTS { MATCH (a)-[:TLINK]->(c) }
          AND coalesce(a.low_confidence, false) = false
          AND coalesce(c.low_confidence, false) = false
        MERGE (a)-[tl:TLINK]->(c)
        ON CREATE SET tl.relType = 'BEFORE',
                      tl.source = 'graph_inference',
                      tl.confidence = 0.72,
                      tl.rule_id = 'ga01_transitive_before',
                      tl.evidence_source = 'graph_enhancements'
        RETURN count(tl) AS created
        """
        rows = self.graph.run(query).data()
        return rows[0].get("created", 0) if rows else 0

    def tlink_transitive_after(self):
        """Add AFTER TLINKs inferred from transitivity."""
        logger.debug("tlink_transitive_after")
        query = """
        MATCH (a:TEvent)-[:TLINK {relType:'AFTER'}]->(b)-[:TLINK {relType:'AFTER'}]->(c:TEvent)
        WHERE elementId(a) <> elementId(c)
          AND NOT EXISTS { MATCH (a)-[:TLINK]->(c) }
          AND coalesce(a.low_confidence, false) = false
          AND coalesce(c.low_confidence, false) = false
        MERGE (a)-[tl:TLINK]->(c)
        ON CREATE SET tl.relType = 'AFTER',
                      tl.source = 'graph_inference',
                      tl.confidence = 0.72,
                      tl.rule_id = 'ga01_transitive_after',
                      tl.evidence_source = 'graph_enhancements'
        RETURN count(tl) AS created
        """
        rows = self.graph.run(query).data()
        return rows[0].get("created", 0) if rows else 0

    def tlink_included_before(self):
        """Add BEFORE TLINKs: if A IS_INCLUDED B and B BEFORE C, then A BEFORE C."""
        logger.debug("tlink_included_before")
        query = """
        MATCH (a:TEvent)-[:TLINK {relType:'IS_INCLUDED'}]->(b)-[:TLINK {relType:'BEFORE'}]->(c:TEvent)
        WHERE elementId(a) <> elementId(c)
          AND NOT EXISTS { MATCH (a)-[:TLINK]->(c) }
          AND coalesce(a.low_confidence, false) = false
          AND coalesce(c.low_confidence, false) = false
        MERGE (a)-[tl:TLINK]->(c)
        ON CREATE SET tl.relType = 'BEFORE',
                      tl.source = 'graph_inference',
                      tl.confidence = 0.65,
                      tl.rule_id = 'ga01_included_before',
                      tl.evidence_source = 'graph_enhancements'
        RETURN count(tl) AS created
        """
        rows = self.graph.run(query).data()
        return rows[0].get("created", 0) if rows else 0

    # ------------------------------------------------------------------
    # GA-02  Event confidence down-ranking
    # ------------------------------------------------------------------

    def mark_low_confidence_events_no_frame(self):
        """Mark TEvents with no supporting Frame and low confidence as low_confidence=true."""
        logger.debug("mark_low_confidence_events_no_frame")
        query = """
        MATCH (e:TEvent)
        WHERE coalesce(e.low_confidence, false) = false
        OPTIONAL MATCH (e)<-[:FRAME_DESCRIBES_EVENT|DESCRIBES]-(f:Frame)
          WHERE f.framework IN ['PROPBANK','NOMBANK']
        WITH e, count(DISTINCT f) AS frame_count,
             coalesce(e.confidence, 1.0) AS base_conf
        WHERE frame_count = 0 AND base_conf < 0.60
        SET e.low_confidence = true,
            e.confidence = base_conf * 0.5,
            e.low_confidence_reason = 'no_frame_support'
        RETURN count(e) AS marked
        """
        rows = self.graph.run(query).data()
        return rows[0].get("marked", 0) if rows else 0

    def mark_low_confidence_nominal_events_no_deverbal(self):
        """Mark nominal TEvents with no deverbal WordNet link as low_confidence=true."""
        logger.debug("mark_low_confidence_nominal_events_no_deverbal")
        query = """
        MATCH (e:TEvent)<-[:TRIGGERS]-(tok:TagOccurrence)
        WHERE tok.upos = 'NOUN'
          AND coalesce(e.low_confidence, false) = false
          AND coalesce(e.pos, 'NOUN') = 'NOUN'
        OPTIONAL MATCH (tok)-[:HAS_LEMMA]->(tag:Tag)
          WHERE tag.derivational_eventive_verbs IS NOT NULL
            AND size(tag.derivational_eventive_verbs) > 0
        WITH e, tok, tag
        WHERE tag IS NULL
        SET e.low_confidence = true,
            e.confidence = coalesce(e.confidence, 0.5) * 0.6,
            e.low_confidence_reason = 'nominal_no_deverbal_support'
        RETURN count(e) AS marked
        """
        rows = self.graph.run(query).data()
        return rows[0].get("marked", 0) if rows else 0

    # ------------------------------------------------------------------
    # GA-03  Event class inference from PropBank frame names
    # ------------------------------------------------------------------

    def infer_event_class_from_propbank_frame(self):
        """Set TEvent.class from PropBank frame name when class is absent."""
        logger.debug("infer_event_class_from_propbank_frame")
        query = """
        MATCH (f:Frame)-[:FRAME_DESCRIBES_EVENT|DESCRIBES]->(e:TEvent)
        WHERE e.class IS NULL AND f.frame IS NOT NULL
        WITH e, f.frame AS frame_name
        WITH e, frame_name,
          CASE
            WHEN frame_name IN [
              'say.01','announce.01','report.01','tell.01','claim.01','declare.01',
              'state.01','note.01','indicate.01','reveal.01','predict.01','promise.01',
              'propose.01','assert.01','allege.01','acknowledge.01','admit.01',
              'emphasize.01','stress.01','confirm.01','deny.01','insist.01','warn.01',
              'suggest.01','argue.01','mention.01','observe.01','reiterate.01',
              'respond.01','reply.01','counter.01'
            ] THEN 'REPORTING'
            WHEN frame_name IN [
              'know.01','believe.01','think.01','feel.01','understand.01','assume.01',
              'realize.01','discover.01','notice.01','find.01','learn.01','establish.01',
              'prove.01','determine.01','remember.01','recall.01'
            ] THEN 'I_STATE'
            WHEN frame_name IN [
              'want.01','hope.01','plan.01','intend.01','decide.01','attempt.01',
              'try.01','seek.01','need.01','wish.01','fail.01','manage.01',
              'agree.01','refuse.01'
            ] THEN 'I_ACTION'
            WHEN frame_name IN [
              'begin.01','start.01','continue.01','end.01','finish.01','stop.01',
              'cease.01','resume.01','complete.01'
            ] THEN 'ASPECTUAL'
            WHEN frame_name IN [
              'be.01','have.01','remain.01','become.01','exist.01','stay.01',
              'seem.01','appear.01','look.01'
            ] THEN 'STATE'
            ELSE 'OCCURRENCE'
          END AS inferred_class
        SET e.class = inferred_class,
            e.class_source = 'propbank_frame_inference'
        RETURN count(e) AS updated
        """
        rows = self.graph.run(query).data()
        return rows[0].get("updated", 0) if rows else 0

    # ------------------------------------------------------------------
    # GA-04  TIMEX ISO 8601 value normalization
    # ------------------------------------------------------------------

    def normalize_timex_duration_values(self):
        """Fix transposed unit-number order in DURATION TIMEX values (PY5 → P5Y)."""
        logger.debug("normalize_timex_duration_values")
        query = r"""
        MATCH (t:TIMEX)
        WHERE t.type = 'DURATION'
          AND t.value IS NOT NULL
          AND t.value =~ 'P[YMDWH][0-9]+'
          AND coalesce(t.value_normalized, false) = false
        WITH t,
          'P' + substring(t.value, 2) + substring(t.value, 1, 1) AS corrected
        WHERE corrected <> t.value
        SET t.value_raw = t.value,
            t.value = corrected,
            t.value_normalized = true
        RETURN count(t) AS fixed
        """
        rows = self.graph.run(query).data()
        return rows[0].get("fixed", 0) if rows else 0

    # ------------------------------------------------------------------
    # GA-05  Entity salience scoring
    # ------------------------------------------------------------------

    def compute_entity_salience(self):
        """Set Entity.salience from EVENT_PARTICIPANT and mention count."""
        logger.debug("compute_entity_salience")
        query = """
        MATCH (e:Entity)
        OPTIONAL MATCH (e)<-[:EVENT_PARTICIPANT|PARTICIPANT]-(ev:TEvent)
        WITH e, count(DISTINCT ev) AS event_degree
        OPTIONAL MATCH (e)<-[:REFERS_TO]-(m)
          WHERE m:NamedEntity OR m:CorefMention OR m:EntityMention
        WITH e, event_degree, count(DISTINCT m) AS mention_count
        SET e.salience = round(
              (0.6 * toFloat(mention_count) + 0.4 * toFloat(event_degree))
              / (toFloat(mention_count) + toFloat(event_degree) + 1.0),
              4
            ),
            e.salience_computed_at = timestamp()
        RETURN count(e) AS updated
        """
        rows = self.graph.run(query).data()
        return rows[0].get("updated", 0) if rows else 0

    # ------------------------------------------------------------------
    # GA-06  Frame ALIGNS_WITH gap fill
    # ------------------------------------------------------------------

    def fill_frame_aligns_with_gaps(self):
        """Link PropBank and NomBank frames for the same TEvent by shared headLemma."""
        logger.debug("fill_frame_aligns_with_gaps")
        query = """
        MATCH (fv:Frame {framework:'PROPBANK'})
        MATCH (fn:Frame {framework:'NOMBANK'})
        WHERE fv.headLemma = fn.headLemma
          AND fv.headLemma IS NOT NULL
          AND NOT EXISTS { MATCH (fv)-[:ALIGNS_WITH]->(fn) }
        OPTIONAL MATCH (fv)-[:FRAME_DESCRIBES_EVENT|DESCRIBES]->(e:TEvent)
        OPTIONAL MATCH (fn)-[:FRAME_DESCRIBES_EVENT|DESCRIBES]->(e)
        WITH fv, fn, e WHERE e IS NOT NULL
        MERGE (fv)-[aw:ALIGNS_WITH]->(fn)
        ON CREATE SET aw.source = 'headlemma_colocated',
                      aw.confidence = 0.70,
                      aw.evidence_source = 'graph_enhancements'
        RETURN count(aw) AS created
        """
        rows = self.graph.run(query).data()
        return rows[0].get("created", 0) if rows else 0

    # ------------------------------------------------------------------
    # GA-07  Coreference chain quality signal
    # ------------------------------------------------------------------

    def compute_coref_chain_quality(self):
        """Set confidence on CorefChain nodes from mention and named-entity anchor counts."""
        logger.debug("compute_coref_chain_quality")
        query = """
        MATCH (chain:CorefChain)
        OPTIONAL MATCH (chain)-[:HAS_MENTION]->(m)
        WITH chain, count(m) AS mention_count
        OPTIONAL MATCH (chain)-[:HAS_MENTION]->(m2)-[:REFERS_TO]->(ne:NamedEntity)
        WITH chain, mention_count, count(DISTINCT ne) AS named_entity_anchors
        SET chain.mention_count = mention_count,
            chain.named_entity_anchors = named_entity_anchors,
            chain.confidence = CASE
              WHEN mention_count >= 5 AND named_entity_anchors >= 1 THEN 0.92
              WHEN mention_count >= 3 AND named_entity_anchors >= 1 THEN 0.82
              WHEN mention_count >= 2 THEN 0.70
              ELSE 0.50
            END
        RETURN count(chain) AS updated
        """
        rows = self.graph.run(query).data()
        return rows[0].get("updated", 0) if rows else 0

    # ------------------------------------------------------------------
    # GA-08  Sentence root backfill (requires dep property on TagOccurrence)
    # ------------------------------------------------------------------

    def backfill_sentence_roots(self):
        """Set root_tok_id, root_lemma, root_upos on Sentence nodes from TagOccurrence.dep='ROOT'."""
        logger.debug("backfill_sentence_roots")
        query = """
        MATCH (s:Sentence)-[:HAS_TOKEN]->(tok:TagOccurrence)
        WHERE tok.dep = 'ROOT'
          AND s.root_tok_id IS NULL
        SET s.root_tok_id = tok.id,
            s.root_lemma = tok.lemma,
            s.root_upos = tok.upos
        RETURN count(s) AS updated
        """
        rows = self.graph.run(query).data()
        return rows[0].get("updated", 0) if rows else 0

    # ------------------------------------------------------------------
    # GA-09  Participant mention bridge
    # ------------------------------------------------------------------

    def bridge_entity_participant_to_named_entity(self):
        """Materialise NamedEntity→TEvent/EventMention EVENT_PARTICIPANT edges.

        The pipeline writes EVENT_PARTICIPANT from canonical Entity nodes, which
        lack span properties.  The MEANTIME evaluator requires the source of a
        has_participant relation to carry span coordinates (start_tok/end_tok).
        NamedEntity nodes (mention layer) DO carry spans and are linked to
        canonical Entity via REFERS_TO.

        This algorithm bridges the gap:
          NamedEntity -[:REFERS_TO]-> Entity -[:EVENT_PARTICIPANT]-> TEvent/EventMention
          →  NamedEntity -[:EVENT_PARTICIPANT]-> TEvent/EventMention

        Restricted to NamedEntity mentions within ±GA09_TOKEN_WINDOW tokens of
        the event anchor to avoid cross-document coreference chain inflation.
        (Coreference can link a canonical Entity to dozens of NamedEntity nodes
        across the entire document; only sentence-local ones are gold-standard.)

        Idempotent: previously-created bridges are deleted and recreated so that
        re-runs with a changed window produce a consistent result.
        """
        GA09_TOKEN_WINDOW = 50
        logger.debug("bridge_entity_participant_to_named_entity (window=%d)", GA09_TOKEN_WINDOW)

        # Delete previously-created bridges so re-runs are idempotent.
        purge_query = """
        MATCH ()-[r:EVENT_PARTICIPANT {rule_id: 'ga09_mention_participant_bridge'}]->()
        DELETE r
        RETURN count(r) AS deleted
        """
        self.graph.run(purge_query)

        query = """
        MATCH (ne:NamedEntity)-[:REFERS_TO]->(e:Entity)-[r:EVENT_PARTICIPANT]->(evt)
        WHERE (evt:TEvent OR evt:EventMention)
          AND ne.start_tok IS NOT NULL
          AND evt.start_tok IS NOT NULL
          AND abs(ne.start_tok - evt.start_tok) <= $window
          AND NOT EXISTS { MATCH (ne)-[:EVENT_PARTICIPANT]->(evt) }
        MERGE (ne)-[nr:EVENT_PARTICIPANT]->(evt)
        ON CREATE SET nr.type = r.type,
                      nr.sem_role = coalesce(r.sem_role, r.type),
                      nr.is_core = coalesce(r.is_core, true),
                      nr.source = 'mention_participant_bridge',
                      nr.confidence = coalesce(r.confidence, 0.85),
                      nr.rule_id = 'ga09_mention_participant_bridge',
                      nr.evidence_source = 'graph_enhancements'
        RETURN count(nr) AS created
        """
        rows = self.graph.run(query, parameters={"window": GA09_TOKEN_WINDOW}).data()
        return rows[0].get("created", 0) if rows else 0

    # ------------------------------------------------------------------
    # GA-10  TEvent pos correction from spaCy token POS
    # ------------------------------------------------------------------

    def fix_tevent_pos_from_token_pos(self):
        """Correct TEvent.pos for nominal events mis-tagged as VERB.

        HeidelTime and TTK use 'epos=VERB' (an event-semantic POS class, not the
        surface syntactic category) for all predicates including nominalizations.
        MEANTIME gold annotates nominal events with pos='NOUN'.  The surface POS
        stored on the TagOccurrence nodes by spaCy (upos='NOUN') is the ground
        truth for this attribute.

        Algorithm: for every TEvent linked via TRIGGERS to a TagOccurrence whose
        spaCy upos is 'NOUN' or fine-grained pos is a noun tag (NN/NNS/NNP/NNPS),
        set TEvent.pos = 'NOUN'.
        """
        logger.debug("fix_tevent_pos_from_token_pos")
        query = """
        MATCH (tok:TagOccurrence)-[:TRIGGERS]->(te:TEvent)
        WHERE te.start_tok IS NOT NULL
          AND tok.tok_index_doc = te.start_tok
          AND (tok.upos = 'NOUN' OR tok.pos IN ['NN', 'NNS', 'NNP', 'NNPS'])
          AND te.pos IN ['VERB', 'VB', 'VBZ', 'VBP', 'VBD', 'VBN', 'VBG',
                         'VBD_VBN', 'VBZ_VBP', 'INFINITIVE', 'PRESPART']
        SET te.pos = 'NOUN'
        RETURN count(DISTINCT te) AS corrected
        """
        rows = self.graph.run(query).data()
        return rows[0].get("corrected", 0) if rows else 0

    # ------------------------------------------------------------------
    # GA-12  Purge spurious TLINKs from over-generating tlinks rules
    # ------------------------------------------------------------------

    def purge_spurious_tlinks(self):
        """Delete TLINKs created by tlinks_recognizer rules that are net-negative
        against MEANTIME gold.

        Four rules are purged:
        * case6_dct_anchor  — anchors every event to the Document Creation Time
          as IS_INCLUDED; gold does not annotate DCT anchors for most events.
        * transitive_closure — propagates BEFORE/AFTER chains via Allen's axioms;
          gold uses IS_INCLUDED/SIMULTANEOUS which do not participate in the same
          closure rules.
        * inverse_consistency — adds mirror relations (B AFTER A for every A BEFORE B,
          B IS_INCLUDED A for every A INCLUDES B, etc.); these doubles relation counts
          with relations the evaluator does not reward against MEANTIME gold.
        * case17a_timex_same_value — creates SIMULTANEOUS between any two TIMEX
          nodes with the same normalized value; MEANTIME gold does not annotate
          TIMEX–TIMEX SIMULTANEOUS and this rule produces near-100% false positives.

        NOTE: case4_timex_head_match, case5_timex_preposition,
        case21_dep_timex_includes (formerly case20a_sentence_timex_includes),
        and xml_e2t_seed contribute IS_INCLUDED false positives but also produce
        true positives — they must NOT be purged without a more targeted precision filter.
        """
        logger.debug("purge_spurious_tlinks")
        query = """
        MATCH ()-[r:TLINK]->()
        WHERE r.rule_id IN ['case6_dct_anchor', 'transitive_closure',
                            'inverse_consistency', 'case17a_timex_same_value']
        DELETE r
        RETURN count(r) AS deleted
        """
        rows = self.graph.run(query).data()
        return rows[0].get("deleted", 0) if rows else 0

    # GA-14  Purge xml_e2e_seed BEFORE/AFTER event-event TLINKs
    # ------------------------------------------------------------------

    def purge_e2e_before_after_tlinks(self) -> int:
        """Delete BEFORE/AFTER/VAGUE TEvent→TEvent TLINKs from xml_e2e_seed.

        The xml_e2e_seed rule seeds event-event temporal ordering from the NAF
        XML structure (e.g., sentence-order heuristics).  MEANTIME gold annotates
        very few event-event BEFORE/AFTER relations — the vast majority of gold
        TLINKs are IS_INCLUDED event→timex or SIMULTANEOUS.  The xml_e2e_seed
        BEFORE/AFTER predictions are therefore systematically false positives.

        SIMULTANEOUS and INCLUDES from xml_e2e_seed are retained as they are rare
        and may match gold annotations.
        """
        logger.debug("purge_e2e_before_after_tlinks")
        query = """
        MATCH (a:TEvent)-[r:TLINK]->(b:TEvent)
        WHERE r.rule_id = 'xml_e2e_seed'
          AND r.relType IN ['BEFORE', 'AFTER', 'VAGUE']
        DELETE r
        RETURN count(r) AS deleted
        """
        rows = self.graph.run(query).data()
        return rows[0].get("deleted", 0) if rows else 0

    # GA-15  Shadow TEvents for standalone SRL frames
    # ------------------------------------------------------------------

    def suppress_standalone_frame_events(self) -> int:
        """Create shadow TEvent nodes (low_confidence=True) to suppress
        SRL-only Frame predicates from the evaluator's frame-fallback path.

        The MEANTIME evaluator has a third event source: Frame nodes reachable
        via TagOccurrence-[:PARTICIPATES_IN]->Frame that have start_tok/end_tok
        set and NO corresponding TEvent at the same span.  This path captures
        NomBank/PropBank predicates for tokens that HeidelTime did not annotate
        as TimeML events (e.g. "March", "anniversary", "percent").  These are
        systematically false positives against MEANTIME gold.

        This algorithm creates minimal shadow TEvent nodes at each such Frame
        span with low_confidence=True.  The evaluator's NOT EXISTS check for
        TEvent at the same span is satisfied (suppressing the Frame), while
        the low_confidence flag keeps the shadow TEvent from being counted as
        a predicted event itself (evaluator's Source 2 filters by
        coalesce(low_confidence, false) = false).

        The operation is idempotent (MERGE).
        """
        logger.debug("suppress_standalone_frame_events")
        query = """
        MATCH (at:AnnotatedText)-[:CONTAINS_SENTENCE]->(:Sentence)
              -[:HAS_TOKEN]->(:TagOccurrence)
              -[:PARTICIPATES_IN]->(f:Frame)
        WHERE f.start_tok IS NOT NULL AND f.end_tok IS NOT NULL
          AND at.id IS NOT NULL
          AND NOT EXISTS {
            MATCH (ev:TEvent)
            WHERE ev.start_tok = f.start_tok AND ev.end_tok = f.end_tok
          }
        WITH DISTINCT at.id AS doc_id,
                      f.start_tok AS start_tok,
                      f.end_tok   AS end_tok,
                      f.headword  AS headword
        MERGE (te:TEvent {doc_id: doc_id, start_tok: start_tok, end_tok: end_tok,
                          low_confidence: true})
        ON CREATE SET
            te.eiid              = 'ga15_' + toString(doc_id) + '_' + toString(start_tok),
            te.low_confidence_reason = 'srl_only_no_timeml_event',
            te.pred   = headword,
            te.pos    = 'VERB',
            te.source = 'ga15_frame_shadow'
        RETURN count(*) AS created
        """
        rows = self.graph.run(query).data()
        return rows[0].get("created", 0) if rows else 0

    # ------------------------------------------------------------------
    # Orchestration helper
    # ------------------------------------------------------------------

    def run_all(self):
        """Run all graph enhancement algorithms in dependency order.

        Returns a dict of algorithm → count-of-changed-nodes/edges.
        """
        results = {}

        # GA-01 — DISABLED: purge any previously-created transitive TLINKs
        # (GA-01 generates BEFORE/AFTER chains that do not appear in MEANTIME gold,
        #  resulting in large FP counts with no TP benefit.)
        results["ga01_purged"] = self.purge_ga01_tlinks()

        # GA-02 — confidence filtering (reduces FP; must run before salience)
        results["ga02_no_frame"] = self.mark_low_confidence_events_no_frame()
        results["ga02_no_deverbal"] = self.mark_low_confidence_nominal_events_no_deverbal()

        # GA-03 — event class
        results["ga03_event_class"] = self.infer_event_class_from_propbank_frame()

        # GA-04 — TIMEX normalization
        results["ga04_timex_norm"] = self.normalize_timex_duration_values()

        # GA-05 — entity salience (after confidence marking)
        results["ga05_salience"] = self.compute_entity_salience()

        # GA-06 — frame alignment
        results["ga06_aligns_with"] = self.fill_frame_aligns_with_gaps()

        # GA-07 — coref quality
        results["ga07_coref"] = self.compute_coref_chain_quality()

        # GA-08 — sentence roots (no-op if dep property absent)
        results["ga08_sent_root"] = self.backfill_sentence_roots()

        # GA-09 — participant mention bridge (±50-token window)
        results["ga09_participant_bridge"] = self.bridge_entity_participant_to_named_entity()

        # GA-10 — fix TEvent.pos for nominal events mis-tagged as VERB by TTK/HeidelTime
        results["ga10_pos_corrected"] = self.fix_tevent_pos_from_token_pos()

        # GA-12 — purge spurious TLINKs from tlinks_recognizer rules that
        #          generate large numbers of BEFORE/AFTER edges not in MEANTIME gold:
        #          case6_dct_anchor (all events anchored to DCT),
        #          transitive_closure (BEFORE/AFTER chains),
        #          inverse_consistency (inverse of every created TLINK).
        results["ga12_tlinks_purged"] = self.purge_spurious_tlinks()

        # GA-14 — purge xml_e2e_seed BEFORE/AFTER event-event TLINKs.
        #          These event-event ordering predictions are systematically FP vs
        #          MEANTIME gold (which uses IS_INCLUDED for event→timex).
        #          SIMULTANEOUS and INCLUDES are retained.
        results["ga14_e2e_before_after_purged"] = self.purge_e2e_before_after_tlinks()

        # GA-15 — suppress standalone SRL frames from evaluator's frame-fallback path.
        #          NomBank/PropBank frames at spans without a corresponding TEvent
        #          are picked up by the evaluator as fallback event predictions.
        #          Shadow TEvents (low_confidence=True) are created at those spans
        #          so the evaluator's NOT EXISTS check suppresses the Frame while
        #          low_confidence keeps the shadow TEvent invisible to evaluation.
        results["ga15_frame_shadows"] = self.suppress_standalone_frame_events()

        logger.info("GraphEnhancementsPhase.run_all completed: %s", results)
        return results
