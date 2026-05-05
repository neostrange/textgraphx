"""EventEnrichmentPhase

Attach frames to temporalized events and populate participant relationships
between canonical `Entity`/`VALUE` nodes and `TEvent` nodes, with explicit
fallback support for legacy `NamedEntity:NUMERIC|VALUE` sources during the
current transition period. This phase assumes frames and TIMEX/TEvent nodes
are already present in the graph and performs idempotent MERGE updates to
create `DESCRIBES` and `PARTICIPANT` edges.
"""

import os
import spacy
import sys

# When run as a script, allow imports by ensuring repo root is available.
if __name__ == '__main__' and __package__ is None:
    from pathlib import Path
    repo_root = Path(__file__).resolve().parents[3]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
#import neuralcoref

from textgraphx.util.SemanticRoleLabeler import SemanticRoleLabel
from textgraphx.util.EntityFishingLinker import EntityFishing
from spacy.tokens import Doc, Token, Span
from textgraphx.util.RestCaller import callAllenNlpApi
from textgraphx.util.GraphDbBase import GraphDBBase
import xml.etree.ElementTree as ET
# legacy py2neo imports removed; use bolt-driver wrapper via neo4j_client
import logging

from textgraphx.database.client import make_graph_from_config
from textgraphx.infrastructure.config import get_config
from textgraphx.reasoning.contracts import (
    canonical_event_attribute_vocabulary,
    count_endpoint_violations,
    normalize_event_attr,
)
from textgraphx.reasoning.merge_utils import resolve_attribute_conflict

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SLINK predicate inventories (lemma-level, lower-case, PropBank-grounded)
# ---------------------------------------------------------------------------
# Predicates whose ARG1/ARG2 complement introduces a subordinate event.
# Grouped by TimeML slink_type semantics.

_SLINK_EVIDENTIAL_LEMMAS: frozenset = frozenset({
    # Reporting / speech-act
    "say", "report", "announce", "state", "note", "claim", "tell",
    "confirm", "deny", "insist", "warn", "suggest", "argue", "mention",
    "indicate", "reveal", "predict", "promise", "propose", "assert",
    "allege", "acknowledge", "admit", "emphasize", "stress", "observe",
    "reiterate", "repeat", "respond", "reply", "counter",
    # Non-factive cognition
    "think", "believe", "expect", "assume", "consider", "suppose",
    "suspect", "guess", "conclude", "speculate", "estimate",
})

_SLINK_FACTIVE_LEMMAS: frozenset = frozenset({
    # Veridical cognition / discovery
    "know", "realize", "discover", "notice", "find", "learn",
    "understand", "recognize", "remember", "recall", "establish",
    "prove", "determine",
})

_SLINK_MODAL_LEMMAS: frozenset = frozenset({
    # Desire / intent / ability
    "want", "hope", "plan", "intend", "decide", "attempt", "try",
    "seek", "need", "wish", "fail", "manage", "agree", "refuse",
})

# Union used by Cypher WHERE clause
_SLINK_ALL_LEMMAS: frozenset = (
    _SLINK_EVIDENTIAL_LEMMAS | _SLINK_FACTIVE_LEMMAS | _SLINK_MODAL_LEMMAS
)


# ---------------------------------------------------------------------------
# CLINK predicate inventories (lemma-level, lower-case, PropBank-grounded)
# ---------------------------------------------------------------------------
# Predicates whose ARG1/ARG2/ARG2 structure encodes a causal relation between
# two events.  Divided by the direction of causality in the CLINK relation:
#   - CAUSE  : subject/agent causes the object/complement event
#   - ENABLE : agent enables or allows the complement event (permissive)
#   - PREVENT: agent blocks or prevents the complement event

_CLINK_CAUSE_LEMMAS: frozenset = frozenset({
    "cause", "lead", "trigger", "result", "produce", "generate",
    "create", "bring", "force", "make", "drive", "prompt", "spur",
    "give", "yield", "induce", "provoke", "spark", "precipitate",
    "contribute", "result", "stem",
})

_CLINK_ENABLE_LEMMAS: frozenset = frozenset({
    "allow", "enable", "permit", "let", "support", "help", "facilitate",
    "encourage", "ensure", "guarantee", "provide", "offer",
})

_CLINK_PREVENT_LEMMAS: frozenset = frozenset({
    "prevent", "stop", "block", "ban", "prohibit", "restrict", "limit",
    "hinder", "hamper", "impede", "obstruct", "avoid", "deter",
})

_CLINK_ALL_LEMMAS: frozenset = (
    _CLINK_CAUSE_LEMMAS | _CLINK_ENABLE_LEMMAS | _CLINK_PREVENT_LEMMAS
)


# This phase will run after the TemporalPhase.
# NOTES: 
## 
class EventEnrichmentPhase():

    uri=""
    username =""
    password =""
    graph=""

    def __init__(self, argv):
        # Initialize a shared py2neo Graph from config
        self.graph = make_graph_from_config()
        # keep legacy attrs for compatibility
        self.uri = None
        self.username = None
        self.password = None
        #self.__text_processor = TextProcessor(self.nlp, self._driver)
        #self.create_constraints()
    logger.info("EventEnrichmentPhase initialized; graph session ready")

    @staticmethod
    def _tevent_field_defaults(field_name):
        defaults = {
            "certainty": ("temporal_phase", 0.90),
            "aspect": ("temporal_phase", 0.90),
            "polarity": ("temporal_phase", 0.90),
            "time": ("temporal_phase", 0.90),
            "factuality": ("event_enrichment", 0.70),
        }
        return defaults.get(field_name, ("temporal_phase", 0.90))

    @staticmethod
    def _participant_source_subquery(
        frame_argument_alias="fa",
        source_alias="participant",
        include_frame_argument=False,
        include_general_namedentity=False,
        prefer_namedentity_over_entity=False,
    ):
        """Return a Cypher subquery resolving participant sources with canonical preference.

        Resolution order is:
             1. canonical `Entity` (or fallback if no preferred NamedEntity)
        2. canonical `VALUE`
                 3. legacy fallback NamedEntity of numeric/value semantic type (CARDINAL,
                     ORDINAL, MONEY, QUANTITY, PERCENT)
                 4. optional guarded fallback to general NamedEntity when canonical
                    Entity/VALUE is unavailable for the FrameArgument

        Some semantic-relation paths also allow `FrameArgument` as a direct
        source during the maintained transition period.
        """
        if prefer_namedentity_over_entity:
            entity_guard = (
                "AND NOT EXISTS { "
                f"MATCH ({frame_argument_alias})-[:REFERS_TO]->(ne_pref:NamedEntity) "
                "WHERE NOT (coalesce(ne_pref.type, '') IN ['CARDINAL', 'ORDINAL', 'MONEY', 'QUANTITY', 'PERCENT']) "
                "}"
            )
        else:
            entity_guard = ""

        branches = [
            f"""
                    WITH {frame_argument_alias}
                    MATCH ({frame_argument_alias})-[:REFERS_TO]->({source_alias}:Entity)
                    WHERE true {entity_guard}
                    RETURN {source_alias}
            """,
            f"""
                    WITH {frame_argument_alias}
                    MATCH ({frame_argument_alias})-[:REFERS_TO]->({source_alias}:VALUE)
                    RETURN {source_alias}
            """,
            f"""
                    WITH {frame_argument_alias}
                    MATCH ({frame_argument_alias})-[:REFERS_TO]->({source_alias}:NamedEntity)
                    WHERE {source_alias}.type IN ['CARDINAL', 'ORDINAL', 'MONEY', 'QUANTITY', 'PERCENT']
                    RETURN {source_alias}
            """,
        ]
        if include_general_namedentity:
            if prefer_namedentity_over_entity:
                general_namedentity_guard = ""
            else:
                general_namedentity_guard = (
                    f"AND NOT EXISTS {{ MATCH ({frame_argument_alias})-[:REFERS_TO]->(:Entity) }}\n"
                    f"                      AND NOT EXISTS {{ MATCH ({frame_argument_alias})-[:REFERS_TO]->(:VALUE) }}"
                )
            branches.append(
                f"""
                    WITH {frame_argument_alias}
                    MATCH ({frame_argument_alias})-[:REFERS_TO]->({source_alias}:NamedEntity)
                    WHERE NOT (coalesce({source_alias}.type, '') IN ['CARDINAL', 'ORDINAL', 'MONEY', 'QUANTITY', 'PERCENT'])
                      AND coalesce({source_alias}.syntactic_type, {source_alias}.syntacticType, '') IN ['NAM', 'NOM', 'PRO', 'CONJ', 'PRE.NOM', 'APP', 'HLS']
                      {general_namedentity_guard}
                    RETURN {source_alias}
                """
            )
        if include_frame_argument:
            branches.append(
                f"""
                    WITH {frame_argument_alias}
                    MATCH ({frame_argument_alias})-[:REFERS_TO]->({source_alias}:FrameArgument)
                    RETURN {source_alias}
                """
            )
        return "CALL {\n" + "\n                    UNION\n".join(branches) + "\n                }"

    @staticmethod
    def _event_participant_support_subquery(event_alias="event", source_alias="participant_source"):
        """Return a Cypher subquery collecting participant-support sources with canonical preference.

        Support evidence is counted across canonical `Entity`, canonical `VALUE`,
        and legacy fallback NamedEntity of numeric/value type.
        The subquery returns list batches so outer rows remain available even when
        an event has no participants.
        """
        branches = [
            f"""
                    WITH {event_alias}
                    OPTIONAL MATCH ({source_alias}:Entity)-[:EVENT_PARTICIPANT|PARTICIPANT]->({event_alias})
                    RETURN collect(DISTINCT {source_alias}) AS matched_sources
            """,
            f"""
                    WITH {event_alias}
                    OPTIONAL MATCH ({source_alias}:VALUE)-[:EVENT_PARTICIPANT|PARTICIPANT]->({event_alias})
                    RETURN collect(DISTINCT {source_alias}) AS matched_sources
            """,
            f"""
                    WITH {event_alias}
                    OPTIONAL MATCH ({source_alias}:NamedEntity)-[:EVENT_PARTICIPANT|PARTICIPANT]->({event_alias})
                    WHERE {source_alias}.type IN ['CARDINAL', 'ORDINAL', 'MONEY', 'QUANTITY', 'PERCENT']
                    RETURN collect(DISTINCT {source_alias}) AS matched_sources
            """,
        ]
        return "CALL {\n" + "\n                    UNION\n".join(branches) + "\n                }"

    def _resolve_tevent_field_conflicts(self, field_name, incoming_source="event_enrichment", incoming_confidence=0.65):
        """Resolve TEvent field conflicts using authority-aware merge policy.

        Existing canonical TEvent values (typically temporal-phase primary)
        are preferred over secondary mention-level backfills. Conflicting
        values are retained as explicit conflict metadata for auditability.
        """
        if field_name not in {"certainty", "aspect", "polarity", "time", "factuality"}:
            raise ValueError("Unsupported TEvent field for conflict resolution")

        default_existing_source, default_existing_conf = self._tevent_field_defaults(field_name)
        graph = self.graph
        query = f"""
        MATCH (em:EventMention)-[:REFERS_TO]->(te:TEvent)
        WHERE em.{field_name} IS NOT NULL
        RETURN elementId(te) AS te_id,
               te.{field_name} AS existing_value,
               em.{field_name} AS incoming_value,
               te.{field_name}Source AS existing_source,
               te.{field_name}Confidence AS existing_confidence,
               te.{field_name}AuthorityTier AS existing_tier
        """
        rows = graph.run(query).data()
        if not rows:
            return 0

        updates = []
        for row in rows:
            existing_value = row.get("existing_value")
            incoming_value = row.get("incoming_value")
            if incoming_value is None:
                continue
            resolved = resolve_attribute_conflict(
                existing_value,
                incoming_value,
                existing_source=row.get("existing_source") or default_existing_source,
                incoming_source=incoming_source,
                existing_confidence=float(row.get("existing_confidence") or default_existing_conf),
                incoming_confidence=float(incoming_confidence),
                existing_tier=row.get("existing_tier") or None,
                incoming_tier="secondary",
                conflict_policy="additive",
            )
            updates.append({"te_id": row.get("te_id"), "resolved": resolved})

        if not updates:
            return 0

        for item in updates:
            te_id = item["te_id"]
            resolved = item["resolved"]
            update_query = f"""
            MATCH (te:TEvent)
            WHERE elementId(te) = $te_id
            SET te.{field_name} = $value,
                te.{field_name}Source = $source,
                te.{field_name}Confidence = $confidence,
                te.{field_name}AuthorityTier = $authority_tier,
                te.{field_name}ConflictPolicy = 'additive',
                te.{field_name}ConflictValue = $conflict_value,
                te.{field_name}ConflictSource = $conflict_source,
                te.{field_name}ConflictConfidence = $conflict_confidence,
                te.{field_name}ConflictAuthorityTier = $conflict_tier,
                te.{field_name}ConflictFlag = $has_conflict
            """
            graph.run(
                update_query,
                {
                    "te_id": te_id,
                    "value": resolved.get("value"),
                    "source": resolved.get("source"),
                    "confidence": resolved.get("confidence"),
                    "authority_tier": resolved.get("authority_tier"),
                    "conflict_value": resolved.get("conflict_value"),
                    "conflict_source": resolved.get("conflict_source"),
                    "conflict_confidence": resolved.get("conflict_confidence"),
                    "conflict_tier": resolved.get("conflict_tier"),
                    "has_conflict": bool(resolved.get("has_conflict")),
                },
            ).data()

        return len(updates)

    def normalize_eventmention_vocabulary(self):
        """Normalize EventMention core attributes to ontology vocabulary."""
        graph = self.graph
        vocab = canonical_event_attribute_vocabulary()

        tense_allowed = [str(v) for v in vocab.get("tense", [])]
        aspect_allowed = [str(v) for v in vocab.get("aspect", [])]
        polarity_allowed = [str(v) for v in vocab.get("polarity", [])]
        certainty_allowed = [str(v) for v in vocab.get("certainty", [])]

        # Keep normalization in Cypher so it can be rerun idempotently on existing graphs.
        query = """
        MATCH (em:EventMention)
        SET em.tense = CASE
                WHEN em.tense IS NULL OR trim(toString(em.tense)) = '' THEN 'NONE'
                WHEN toUpper(toString(em.tense)) IN $tense_allowed THEN toUpper(toString(em.tense))
                ELSE 'NONE'
            END,
            em.aspect = CASE
                WHEN em.aspect IS NULL OR trim(toString(em.aspect)) = '' THEN 'NONE'
                WHEN toUpper(toString(em.aspect)) IN $aspect_allowed THEN toUpper(toString(em.aspect))
                ELSE 'NONE'
            END,
            em.polarity = CASE
                WHEN em.polarity IS NULL OR trim(toString(em.polarity)) = '' THEN 'POS'
                WHEN toUpper(toString(em.polarity)) IN $polarity_allowed THEN toUpper(toString(em.polarity))
                ELSE 'POS'
            END,
            em.certainty = CASE
                WHEN em.certainty IS NULL OR trim(toString(em.certainty)) = '' THEN 'UNCERTAIN'
                WHEN toUpper(toString(em.certainty)) IN $certainty_allowed THEN toUpper(toString(em.certainty))
                ELSE 'UNCERTAIN'
            END
        RETURN count(em) AS normalized
        """
        rows = graph.run(
            query,
            {
                "tense_allowed": tense_allowed,
                "aspect_allowed": aspect_allowed,
                "polarity_allowed": polarity_allowed,
                "certainty_allowed": certainty_allowed,
            },
        ).data()
        normalized = rows[0].get("normalized", 0) if rows else 0
        logger.info("normalize_eventmention_vocabulary: normalized %d EventMention nodes", normalized)
        return normalized

    def endpoint_contract_violations(self):
        """Return endpoint-contract violation counts for critical event relations."""
        rels = [
            "EVENT_PARTICIPANT",
            "INSTANTIATES",
            "HAS_FRAME_ARGUMENT",
            "FRAME_DESCRIBES_EVENT",
            "REFERS_TO",
            "MODIFIES",
            "AFFECTS",
        ]
        violations = {rel: count_endpoint_violations(self.graph, rel) for rel in rels}
        total = sum(violations.values())
        if total > 0:
            logger.warning("endpoint_contract_violations: %s", violations)
        else:
            logger.info("endpoint_contract_violations: no violations")
        violations["total"] = total
        return violations

         


    # Link Frame to TEvent via DESCRIBES relationship.
    # Also link Frame to EventMention via INSTANTIATES relationship.
    # Two complementary paths are used to maximise coverage (Item 6 refactor):
    #   Path 1 – direct:   TagOccurrence PARTICIPATES_IN Frame  AND  TRIGGERS TEvent
    #   Path 2 – via args: TagOccurrence PARTICIPATES_IN FrameArgument PARTICIPANT Frame
    #                      AND same TagOccurrence TRIGGERS TEvent
    # Both paths are idempotent (MERGE) so running them together is safe.
    def create_event_mentions(self, doc_id):
        """Create EventMention nodes for each TEvent in the document.
        
        EventMention represents the mention-level event instantiation with temporal
        properties like tense, aspect, polarity, and modality. Each EventMention 
        refers to a canonical TEvent via the REFERS_TO relationship.
        
        This method was moved from TemporalPhase to EventEnrichmentPhase as part of
        Item 4 (temporal ownership split) to clarify that event mention materialization
        is an enrichment responsibility, not pure temporal extraction.
        
        Precondition: TEvent nodes already exist (created by TemporalPhase)
        Postcondition: EventMention nodes created, each with REFERS_TO link to TEvent
        """
        logger.debug("create_event_mentions for doc_id=%s", doc_id)
        doc_id = str(doc_id)
        graph = self.graph
        
        query = """
        MATCH (event:TEvent {doc_id: toInteger($doc_id)})
        WHERE NOT EXISTS { (event)<-[:REFERS_TO]-(em:EventMention) }
        OPTIONAL MATCH (tok:TagOccurrence)-[:TRIGGERS]->(event)
        WITH event, tok
        ORDER BY tok.tok_index_doc
        WITH event, head(collect(tok)) AS trig_tok, toString(event.doc_id) + '_' + event.eiid + '_mention' as mention_id
        OPTIONAL MATCH (s:Sentence)-[:HAS_TOKEN]->(trig_tok)
        WITH event, mention_id, trig_tok,
             head([(s)-[:HAS_TOKEN]->(candidate:TagOccurrence)
                   WHERE candidate.tok_index_doc = trig_tok.tok_index_doc + 1 | candidate]) AS next_tok,
             CASE
                 WHEN trig_tok IS NOT NULL AND trig_tok.lemma IS NOT NULL AND trim(toString(trig_tok.lemma)) <> ''
                 THEN toLower(trim(toString(trig_tok.lemma)))
                 ELSE NULL
             END AS trigger_lemma
        MERGE (em:EventMention {id: mention_id})
        SET em.doc_id = event.doc_id,
            em.pred = CASE
                WHEN trigger_lemma IS NOT NULL
                     AND trig_tok.pos STARTS WITH 'VB'
                     AND next_tok.pos = 'RP'
                     AND next_tok.lemma IS NOT NULL
                     AND trim(toString(next_tok.lemma)) <> ''
                THEN trigger_lemma + ' ' + toLower(trim(toString(next_tok.lemma)))
                ELSE coalesce(trigger_lemma, event.pred, event.form)
            END,
            em.tense = event.tense,
            em.aspect = event.aspect,
            em.pos = event.pos,
            em.epos = event.epos,
            em.form = event.form,
            em.modality = event.modality,
            em.polarity = event.polarity,
            em.class = event.class,
            em.external_ref = coalesce(event.external_ref, event.eid, em.external_ref),
            em.start_tok = event.start_tok,
            em.end_tok = CASE
                WHEN trig_tok.pos STARTS WITH 'VB' AND next_tok.pos = 'RP'
                THEN coalesce(next_tok.tok_index_doc, event.end_tok)
                ELSE event.end_tok
            END,
            em.start_char = event.start_char,
            em.end_char = event.end_char,
            em.begin = event.begin,
            em.end = event.end,
            em.token_id = 'em_' + toString(event.doc_id) + '_' + toString(event.start_tok) + '_' + toString(CASE
                WHEN trig_tok.pos STARTS WITH 'VB' AND next_tok.pos = 'RP'
                THEN coalesce(next_tok.tok_index_doc, event.end_tok)
                ELSE event.end_tok
            END),
            em.token_start = event.start_tok,
            em.token_end = CASE
                WHEN trig_tok.pos STARTS WITH 'VB' AND next_tok.pos = 'RP'
                THEN coalesce(next_tok.tok_index_doc, event.end_tok)
                ELSE event.end_tok
            END
        WITH em, event
        MERGE (em)-[:REFERS_TO]->(event)
        RETURN count(*) as mentions_created
        """
        
        try:
            result = graph.run(query, parameters={"doc_id": doc_id}).data()
            mentions_created = result[0].get("mentions_created", 0) if result else 0
            logger.info("create_event_mentions: created %d EventMention nodes for doc_id=%s", mentions_created, doc_id)
            self.normalize_event_boundaries(doc_id)
            self.tag_timeml_core_events(doc_id)
            self.tag_timeml_core_events(doc_id)
            self.collapse_light_verbs(doc_id)
            self.collapse_light_verbs(doc_id)
            return mentions_created
        except Exception:
            logger.exception("Failed to create event mentions for doc_id=%s", doc_id)
            return 0


    def tag_timeml_core_events(self, doc_id):
        """Categorize events with 'is_timeml_core' to cleanly segregate true 
        reasoning-layer events (e.g. states, reporting) from MEANTIME 
        high-action evaluation-layer events without destroying graph structure.
        """
        logger.debug("tag_timeml_core_events for doc_id=%s", doc_id)
        
        query_events = """
        MATCH (em:EventMention {doc_id: toInteger($doc_id)})
        WITH em, toLower(coalesce(em.pred, '')) AS raw_pred, coalesce(em.pos, '') AS pos
        WITH em, split(raw_pred, ' ')[0] AS lemma, pos
        SET em.is_timeml_core = CASE
            WHEN pos STARTS WITH 'VB' AND lemma IN ['be', 'is', 'was', 'are', 'were', 'been', 'being', 'have', 'has', 'had', 'having', 'do', 'does', 'did', 'done', 'doing', 'become', 'becomes', 'became', 'becoming', 'remain', 'remains', 'remained', 'remaining', 'seem', 'seems', 'seemed', 'seeming', 'look', 'looks', 'looked', 'looking', 'appear', 'appears', 'appeared', 'appearing', 'continue', 'continues', 'continued', 'continuing', 'indicate', 'indicates', 'indicated', 'indicating', 'accord', 'accords', 'accorded', 'according', 'follow', 'follows', 'followed', 'following', 'say', 'says', 'said', 'saying', 'tell', 'tells', 'told', 'telling', 'report', 'reports', 'reported', 'reporting', 'suggest', 'suggests', 'suggested', 'suggesting', 'state', 'states', 'stated', 'stating', 'think', 'thinks', 'thought', 'thinking', 'find', 'finds', 'found', 'finding', 'expect', 'expects', 'expected', 'expecting', 'believe', 'believes', 'believed', 'believing', 'know', 'knows', 'knew', 'known', 'knowing', 'consider', 'considers', 'considered', 'considering'] THEN false
            WHEN pos STARTS WITH 'NN' AND lemma IN ['market', 'markets', 'index', 'indexes', 'indices', 'inflation', 'power', 'powers', 'job', 'jobs', 'number', 'numbers', 'system', 'systems', 'value', 'values', 'price', 'prices', 'percent', 'percentage', 'percentages', 'share', 'shares', 'fund', 'funds', 'point', 'points', 'level', 'levels', 'rate', 'rates', 'record', 'records', 'economy', 'economies', 'growth', 'month', 'months', 'year', 'years', 'day', 'days', 'week', 'weeks', 'exchange', 'exchanges'] THEN false
            ELSE true
        END
        RETURN count(em) as tagged_mentions
        """
        try:
            result = self.graph.run(query_events, {"doc_id": doc_id}).data()
            tagged = result[0]['tagged_mentions'] if result else 0
            logger.info("tag_timeml_core_events: tagged %d EventMentions for doc_id=%s", tagged, doc_id)
        except Exception:
            logger.exception("Failed to tag TimeML core events for doc_id=%s", doc_id)

        query_tevents = """
        MATCH (te:TEvent {doc_id: toInteger($doc_id)})
        OPTIONAL MATCH (em:EventMention)-[:REFERS_TO]->(te)
        WITH te, collect(em.is_timeml_core) as scores
        SET te.is_timeml_core = CASE WHEN size(scores) > 0 THEN any(x IN scores WHERE x = true) ELSE te.is_timeml_core END
        """
        try:
            self.graph.run(query_tevents, {"doc_id": doc_id})
        except Exception:
            pass

    def collapse_light_verbs(self, doc_id):
        '''Collapses LightVerb -> Nominal Event structures to reduce redundancy and fix FPs.
        Transfers tense/aspect from the light verb to the nominal event, and marks
        the light verb as is_timeml_core = false.
        '''
        logger.debug("collapse_light_verbs for doc_id=%s", doc_id)
        
        query = '''
        MATCH (em_noun:EventMention {doc_id: toInteger($doc_id), is_timeml_core: true})
        MATCH (tok_noun:TagOccurrence) WHERE tok_noun.tok_index_doc = em_noun.start_tok
        
        MATCH (tok_verb:TagOccurrence)-[dep:IS_DEPENDENT]->(tok_noun)
        WHERE dep.type IN ['dobj', 'obj', 'pobj']
          AND toLower(tok_verb.lemma) IN ['make', 'take', 'have', 'give', 'do', 'cause', 'hold', 'set', 'get', 'keep', 'put', 'leave', 'find', 'bring']
        
        MATCH (em_verb:EventMention {doc_id: toInteger($doc_id)})
        WHERE em_verb.start_tok = tok_verb.tok_index_doc
        
        SET em_noun.tense = coalesce(em_noun.tense, em_verb.tense),
            em_noun.aspect = coalesce(em_noun.aspect, em_verb.aspect),
            em_verb.is_timeml_core = false
        
        WITH em_noun, em_verb
        OPTIONAL MATCH (em_verb)-[:REFERS_TO]->(te_verb:TEvent)
        OPTIONAL MATCH (em_noun)-[:REFERS_TO]->(te_noun:TEvent)
        SET te_verb.is_timeml_core = false,
            te_verb.merged = CASE WHEN te_noun IS NOT NULL THEN true ELSE te_verb.merged END,
            te_verb.merged_into = CASE WHEN te_noun IS NOT NULL THEN te_noun.id ELSE te_verb.merged_into END,
            te_verb.merged_by = CASE WHEN te_noun IS NOT NULL THEN 'collapse_light_verbs' ELSE te_verb.merged_by END
        SET te_noun.tense = coalesce(te_noun.tense, em_verb.tense),
            te_noun.aspect = coalesce(te_noun.aspect, em_verb.aspect)
            
        RETURN count(em_noun) as collapsed
        '''
        try:
            res = self.graph.run(query, {"doc_id": doc_id}).data()
            if res:
                logger.info("collapse_light_verbs: collapsed %d pairs for doc_id=%s", res[0]['collapsed'], doc_id)
        except Exception:
            logger.exception("Failed to collapse light verbs for doc_id=%s", doc_id)

    def normalize_event_boundaries(self, doc_id):
        """Expand nominal and verbal event mention boundaries to capture multi-word events.
        
        This aligns pipeline metrics with MEANTIME strict evaluation expectations:
        - Verbal triggers expand rightwards to include particle dependencies (e.g. 'drag' -> 'drag down')
        - Nominal triggers expand leftwards to include compound/amod dependencies (e.g. 'bomb' -> 'car bomb')
        """
        logger.debug("normalize_event_boundaries for doc_id=%s", doc_id)
        doc_id = str(doc_id)
        graph = self.graph
        
        # 1. Expand verbal trigger rightwards if it has a 'prt' (particle)
        query_verbal = """
        MATCH (em:EventMention {doc_id: toInteger($doc_id)})-[:REFERS_TO]->(te:TEvent)
        MATCH (te)<-[:TRIGGERS]-(trig_tok:TagOccurrence)
        WHERE trig_tok.pos STARTS WITH 'VB'
        MATCH (trig_tok)-[dep:IS_DEPENDENT]->(prt:TagOccurrence)
        WHERE dep.type IN ['prt', 'acomp'] AND prt.tok_index_doc > em.end_tok
        WITH em, trig_tok, max(prt.tok_index_doc) as new_end, max(prt.end_index) as new_end_char, prt
        WHERE new_end <= em.end_tok + 2
        SET em.end_tok = new_end,
            em.end_char = new_end_char,
            em.end = new_end_char,
            em.token_end = new_end,
            em.token_id = 'em_' + toString(em.doc_id) + '_' + toString(em.start_tok) + '_' + toString(new_end),
            em.pred = coalesce(trig_tok.lemma, em.pred) + ' ' + coalesce(prt.text, '')
        """
        
        # 2. Expand nominal trigger leftwards if it has contiguous 'compound' or 'amod' modifiers
        query_nominal = """
        MATCH (em:EventMention {doc_id: toInteger($doc_id)})-[:REFERS_TO]->(te:TEvent)
        MATCH (te)<-[:TRIGGERS]-(trig_tok:TagOccurrence)
        WHERE trig_tok.pos STARTS WITH 'NN'
        MATCH (trig_tok)-[dep:IS_DEPENDENT]->(mod:TagOccurrence)
        WHERE dep.type IN ['compound', 'amod'] AND mod.tok_index_doc < em.start_tok
        WITH em, min(mod.tok_index_doc) as new_start, min(mod.index) as new_start_char
        WHERE new_start >= em.start_tok - 3
        SET em.start_tok = new_start,
            em.start_char = new_start_char,
            em.begin = new_start_char,
            em.token_start = new_start,
            em.token_id = 'em_' + toString(em.doc_id) + '_' + toString(new_start) + '_' + toString(em.end_tok)
        """
        
        # Calculate pred string accurately using the new bounds
        query_nominal_pred = """
        MATCH (em:EventMention {doc_id: toInteger($doc_id)})-[:REFERS_TO]->(te:TEvent)
        MATCH (te)<-[:TRIGGERS]-(trig_tok:TagOccurrence)
        WHERE trig_tok.pos STARTS WITH 'NN'
        MATCH (tok:TagOccurrence {doc_id: em.doc_id})
        WHERE tok.tok_index_doc >= em.start_tok AND tok.tok_index_doc <= em.end_tok
        WITH em, tok ORDER BY tok.tok_index_doc
        WITH em, collect(tok.text) as words
        WHERE size(words) > 1
        SET em.pred = reduce(s = head(words), w IN tail(words) | s + ' ' + w)
        """
        
        try:
            graph.run(query_verbal, parameters={"doc_id": doc_id})
            graph.run(query_nominal, parameters={"doc_id": doc_id})
            graph.run(query_nominal_pred, parameters={"doc_id": doc_id})
            logger.info("normalize_event_boundaries: updated EventMention bounds for doc_id=%s", doc_id)
        except Exception:
            logger.exception("Failed to normalize event bounds for doc_id=%s", doc_id)

    def link_frameArgument_to_event(self):
        logger.debug("link_frameArgument_to_event")
        graph = self.graph
        linked = 0

        # Path 1: token directly participates in Frame and triggers TEvent
        # Guard: skip provisional frames (low-confidence sense assignment) to avoid
        # polluting the event layer with speculative SRL evidence.
        query_direct = """
            MATCH (f:Frame)<-[:PARTICIPATES_IN|IN_FRAME]-(t:TagOccurrence)-[:TRIGGERS]->(event:TEvent)
            WHERE coalesce(f.provisional, false) = false
            MERGE (f)-[:DESCRIBES]->(event)
            MERGE (f)-[:FRAME_DESCRIBES_EVENT]->(event)
            RETURN count(*) AS linked
        """
        rows = graph.run(query_direct).data()
        if rows:
            linked += rows[0].get("linked", 0)

        # Path 2: token participates in FrameArgument whose Frame triggers TEvent
        query_via_arg = """
            MATCH (f:Frame)<-[:PARTICIPANT]-(fa:FrameArgument)
            WHERE coalesce(f.provisional, false) = false
            MATCH (fa)<-[:PARTICIPATES_IN|IN_FRAME]-(t:TagOccurrence)-[:TRIGGERS]->(event:TEvent)
            MERGE (f)-[:DESCRIBES]->(event)
            MERGE (f)-[:FRAME_DESCRIBES_EVENT]->(event)
            RETURN count(*) AS linked
        """
        rows = graph.run(query_via_arg).data()
        if rows:
            linked += rows[0].get("linked", 0)

        logger.info("link_frameArgument_to_event: %d DESCRIBES relationships merged", linked)

        # Path 3: Link Frame to EventMention (mention layer)
        # EventMention nodes are created in EventEnrichmentPhase and refer to canonical TEvent
        query_instantiates = """
            MATCH (f:Frame)-[:DESCRIBES|:FRAME_DESCRIBES_EVENT]->(event:TEvent)
            MATCH (em:EventMention)-[:REFERS_TO]->(event)
            MERGE (f)-[:INSTANTIATES]->(em)
            RETURN count(*) AS instantiates
        """
        rows = graph.run(query_instantiates).data()
        if rows:
            instantiates = rows[0].get("instantiates", 0)
            logger.info("link_frameArgument_to_event: %d INSTANTIATES relationships merged (Frame -> EventMention)", instantiates)

        return linked


    def promote_nombank_frames_to_tevents(self):
        """Promote eventive-nominal NOMBANK frames to TEvent nodes (D2).

        NOMBANK captures event semantics expressed through nouns (e.g., "the acquisition",
        "the merger", "his resignation").  Standard ``materialize_tevents()`` skips NOMBANK
        frames because it focuses on verbal predicates.  This method bridges the gap:

        1. Find NOMBANK Frame nodes that pass the eventive-nominal filter (re-uses
           ``TemporalPhase._is_eventive_nominal``).
        2. For each qualifying frame that does *not* yet have a ``DESCRIBES``/
           ``FRAME_DESCRIBES_EVENT`` edge to any ``TEvent``, create a new ``TEvent``
           and wire it.
        3. Link head tokens via ``TRIGGERS``.

        Non-fatal: any exception is logged and the method returns 0 without re-raising.
        """
        logger.debug("promote_nombank_frames_to_tevents")

        try:
            from textgraphx.pipeline.phases.temporal import TemporalPhase as _TP
            from textgraphx.pipeline.phases.temporal import _wn as _temporal_wn
            _is_eventive = _TP._is_eventive_nominal
        except Exception:
            logger.warning(
                "promote_nombank_frames_to_tevents: could not import _is_eventive_nominal; skipping"
            )
            return 0

        # Pull all NOMBANK frames not yet linked to a TEvent.
        # Extra columns: sense_conf (for the confidence gate) and has_verbal_alignment
        # (whether a PropBank frame for the same predicate already exists via ALIGNS_WITH).
        candidate_query = """
        MATCH (a:AnnotatedText)-[:CONTAINS_SENTENCE]->(:Sentence)
              -[:HAS_TOKEN]->(tok:TagOccurrence)
              -[:PARTICIPATES_IN]->(f:Frame {framework: 'NOMBANK'})
        WHERE coalesce(f.provisional, false) = false
          AND NOT exists((f)-[:DESCRIBES|FRAME_DESCRIBES_EVENT]->(:TEvent))
            AND exists {
                MATCH (fa_core:FrameArgument)-[:HAS_FRAME_ARGUMENT|PARTICIPANT]->(f)
                WHERE toUpper(coalesce(fa_core.type, '')) IN ['ARG0', 'ARG1', 'A0', 'A1']
            }
        WITH f, a, tok
        ORDER BY tok.tok_index_doc
        WITH f, a, collect(DISTINCT tok)[0] AS head_tok,
             min(tok.tok_index_doc) AS min_tok,
             max(tok.tok_index_doc) AS max_tok
        RETURN f.id AS frame_id,
               coalesce(f.predicate, f.frame) AS headword,
               a.id AS doc_id,
               head_tok.id AS head_tok_id,
               min_tok, max_tok,
               coalesce(f.sense_conf, 0.0) AS sense_conf,
               exists((f)-[:ALIGNS_WITH]->(:Frame {framework: 'PROPBANK'})) AS has_verbal_alignment
        """
        try:
            rows = self.graph.run(candidate_query).data()
        except Exception:
            logger.exception("promote_nombank_frames_to_tevents: candidate query failed")
            return 0

        promoted = 0
        import hashlib as _hashlib
        for row in rows:
            headword = (row.get("headword") or "").strip().lower()
            if not headword:
                continue

            sense_conf = float(row.get("sense_conf") or 0.0)
            has_verbal = bool(row.get("has_verbal_alignment", False))

            # --- Eventive-evidence gate (two-branch) ---
            # Branch A: WordNet unavailable — fail-open is too permissive.
            #   Require verbal alignment OR high sense confidence instead.
            # Branch B: WordNet available — lexname must pass, then apply a
            #   secondary confidence gate when no verbal counterpart exists.
            if _temporal_wn is None:
                if not (has_verbal or sense_conf >= 0.65):
                    continue
            else:
                if not _is_eventive(headword):
                    continue
                # Borderline eventive nominals without verbal support need
                # at least moderate sense confidence to avoid false positives.
                if not has_verbal and sense_conf < 0.55:
                    continue

            # Confidence is calibrated: verbally-aligned nominals inherit the
            # higher-confidence verbal evidence; standalone nominals stay at 0.70.
            confidence = 0.80 if has_verbal else 0.70

            frame_id = row["frame_id"]
            doc_id = row["doc_id"]
            min_tok = row["min_tok"]
            max_tok = row["max_tok"]
            # Deterministic TEvent id: same scheme as materialize_tevents fallback
            raw = f"nombank:{doc_id}:{min_tok}:{max_tok}:{headword}"
            event_id = int(_hashlib.md5(raw.encode()).hexdigest(), 16) % (10 ** 9)

            upsert_query = """
            MERGE (event:TEvent {id: $event_id, doc_id: toInteger($doc_id)})
            ON CREATE SET
                event.text       = $headword,
                event.class      = 'OCCURRENCE',
                event.pos        = 'NN',
                event.source     = 'nombank_srl',
                event.start_tok  = $min_tok,
                event.end_tok    = $max_tok,
                event.confidence = $confidence,
                event.is_timeml_core = true,
                event.low_confidence = false
            WITH event
            MATCH (f:Frame {id: $frame_id})
            MERGE (f)-[:DESCRIBES]->(event)
            MERGE (f)-[:FRAME_DESCRIBES_EVENT]->(event)
            WITH event, f
            MATCH (tok:TagOccurrence {id: $head_tok_id})
            MERGE (tok)-[:TRIGGERS]->(event)
            RETURN event.id AS eid
            """
            try:
                self.graph.run(
                    upsert_query,
                    parameters={
                        "event_id": event_id,
                        "doc_id": doc_id,
                        "headword": headword,
                        "min_tok": min_tok,
                        "max_tok": max_tok,
                        "frame_id": frame_id,
                        "head_tok_id": row.get("head_tok_id"),
                        "confidence": confidence,
                    },
                )
                promoted += 1
            except Exception:
                logger.exception(
                    "promote_nombank_frames_to_tevents: upsert failed for frame_id=%s", frame_id
                )

        logger.info(
            "promote_nombank_frames_to_tevents: %d nominal TEvent nodes created", promoted
        )
        return promoted


    def merge_aligns_with_event_clusters(self):
        """Consolidate TEvent pairs that represent the same predication via ALIGNS_WITH.

        When Phase C (cross-framework alignment) creates ``ALIGNS_WITH`` edges between
        a PROPBANK frame (verbal) and a NOMBANK frame (nominal), and D2 has promoted the
        NOMBANK frame's headword to a TEvent, the graph can contain two separate TEvent
        nodes for the same real-world predication.  This method collapses that duplication:

        Pass 1 — Sense-conflict marking
            ALIGNS_WITH pairs whose frames carry non-null, *different* senses are flagged
            with ``sense_conflict=true`` on the ALIGNS_WITH edge.  They are never merged
            (conflicting sense evidence means the two frames likely describe distinct
            events that happen to share a surface form).

        Pass 2 — EventMention REFERS_TO redirect
            For sense-compatible pairs, any EventMention that currently points to the
            secondary (lower-confidence / NOMBANK) TEvent is redirected to point to the
            canonical (higher-confidence / PROPBANK) TEvent via a new ``REFERS_TO`` edge.

        Pass 3 — TLINK transfer (both directions)
            TLINKs anchored at the secondary TEvent are re-created with the canonical TEvent
            as the endpoint.  Confidence is scaled by 0.9 to reflect the extra inference
            hop.  Already-existing TLINKs are left unchanged (``ON CREATE SET`` only).

        Pass 4 — Secondary TEvent marked as merged
            ``merged=true`` and ``merged_into=<canonical_id>`` are set on the secondary TEvent
            so it is excluded from future merge passes and is visible in diagnostics.

        Non-fatal: each pass is individually wrapped; a failure in one pass does not
        prevent subsequent passes from running.
        """
        logger.debug("merge_aligns_with_event_clusters")
        graph = self.graph

        # ------------------------------------------------------------------
        # Pass 0: light-verb inversion
        # For frames where f_verbal.is_light_verb_host = true the NOMINAL
        # frame carries the semantically canonical event.  Redirect EventMention
        # REFERS_TO from the verbal TEvent to the nominal TEvent and transfer
        # tense/aspect, then mark the verbal TEvent as merged.  This must run
        # BEFORE the general ALIGNS_WITH merge pass so the general pass skips
        # already-merged events.
        # ------------------------------------------------------------------
        lv_redirect_query = """
        MATCH (f_verbal:Frame {is_light_verb_host: true})-[:ALIGNS_WITH]->(f_nominal:Frame)
        WHERE coalesce(f_verbal.provisional, false) = false
          AND coalesce(f_nominal.provisional, false) = false
        MATCH (f_verbal)-[:DESCRIBES|FRAME_DESCRIBES_EVENT]->(e_verbal:TEvent)
        MATCH (f_nominal)-[:DESCRIBES|FRAME_DESCRIBES_EVENT]->(e_nominal:TEvent)
        WHERE elementId(e_verbal) <> elementId(e_nominal)
          AND coalesce(e_verbal.merged, false) = false
        SET e_nominal.tense  = coalesce(e_nominal.tense,  e_verbal.tense),
            e_nominal.aspect = coalesce(e_nominal.aspect, e_verbal.aspect)
        WITH e_verbal, e_nominal
        MATCH (em:EventMention)-[:REFERS_TO]->(e_verbal)
        MERGE (em)-[new_ref:REFERS_TO {source: 'light_verb_canonicalization'}]->(e_nominal)
        ON CREATE SET
            new_ref.merged_from = e_verbal.id,
            new_ref.confidence  = 0.85
        RETURN count(em) AS redirected
        """
        try:
            rows = graph.run(lv_redirect_query).data()
            lv_redirected = rows[0].get("redirected", 0) if rows else 0
            logger.info(
                "merge_aligns_with_event_clusters: light-verb pass redirected %d EventMention refs",
                lv_redirected,
            )
        except Exception:
            logger.exception("merge_aligns_with_event_clusters: light-verb redirect pass failed")

        lv_mark_query = """
        MATCH (f_verbal:Frame {is_light_verb_host: true})-[:ALIGNS_WITH]->(f_nominal:Frame)
        MATCH (f_verbal)-[:DESCRIBES|FRAME_DESCRIBES_EVENT]->(e_verbal:TEvent)
        MATCH (f_nominal)-[:DESCRIBES|FRAME_DESCRIBES_EVENT]->(e_nominal:TEvent)
        WHERE elementId(e_verbal) <> elementId(e_nominal)
          AND coalesce(e_verbal.merged, false) = false
        SET e_verbal.merged      = true,
            e_verbal.merged_into = e_nominal.id,
            e_verbal.merged_by   = 'light_verb_canonicalization'
        RETURN count(e_verbal) AS marked
        """
        try:
            rows = graph.run(lv_mark_query).data()
            lv_marked = rows[0].get("marked", 0) if rows else 0
            logger.info(
                "merge_aligns_with_event_clusters: light-verb pass marked %d verbal TEvents as merged",
                lv_marked,
            )
        except Exception:
            logger.exception("merge_aligns_with_event_clusters: light-verb mark pass failed")

        # ------------------------------------------------------------------
        # Pass 1: flag ALIGNS_WITH pairs with sense-contradicting frames
        # ------------------------------------------------------------------
        sense_conflict_query = """
        MATCH (f_canonical:Frame)-[aw:ALIGNS_WITH]->(f_secondary:Frame)
        WITH f_canonical, f_secondary, aw,
             coalesce(f_canonical.sense, '') AS s1,
             coalesce(f_secondary.sense, '') AS s2
        WHERE s1 <> '' AND s2 <> '' AND s1 <> s2
        SET aw.sense_conflict   = true,
            aw.sense_canonical  = s1,
            aw.sense_secondary  = s2
        RETURN count(aw) AS conflicts
        """
        try:
            rows = graph.run(sense_conflict_query).data()
            conflicts = rows[0].get("conflicts", 0) if rows else 0
            if conflicts:
                logger.info(
                    "merge_aligns_with_event_clusters: %d ALIGNS_WITH pairs have sense conflicts (skipped)",
                    conflicts,
                )
        except Exception:
            logger.exception("merge_aligns_with_event_clusters: sense-conflict pass failed")

        # ------------------------------------------------------------------
        # Pass 2: redirect EventMention REFERS_TO from secondary → canonical
        # ------------------------------------------------------------------
        redirect_query = """
        MATCH (f_canonical:Frame)-[aw:ALIGNS_WITH]->(f_secondary:Frame)
        WHERE coalesce(aw.sense_conflict, false) = false
          AND coalesce(f_canonical.provisional, false) = false
          AND coalesce(f_secondary.provisional, false) = false
        MATCH (f_canonical)-[:DESCRIBES|FRAME_DESCRIBES_EVENT]->(e_canonical:TEvent)
        MATCH (f_secondary)-[:DESCRIBES|FRAME_DESCRIBES_EVENT]->(e_secondary:TEvent)
        WHERE elementId(e_canonical) <> elementId(e_secondary)
          AND coalesce(e_secondary.merged, false) = false
        WITH e_canonical, e_secondary
        MATCH (em:EventMention)-[:REFERS_TO]->(e_secondary)
        MERGE (em)-[new_ref:REFERS_TO {source: 'aligns_with_merge'}]->(e_canonical)
        ON CREATE SET
            new_ref.merged_from = e_secondary.id,
            new_ref.confidence  = 0.80
        RETURN count(em) AS redirected
        """
        redirected = 0
        try:
            rows = graph.run(redirect_query).data()
            redirected = rows[0].get("redirected", 0) if rows else 0
            logger.info(
                "merge_aligns_with_event_clusters: %d EventMention REFERS_TO edges redirected",
                redirected,
            )
        except Exception:
            logger.exception("merge_aligns_with_event_clusters: EventMention redirect pass failed")

        # ------------------------------------------------------------------
        # Pass 4: mark secondary TEvents as merged
        # ------------------------------------------------------------------
        # NOTE: Passes 3a/3b (TLINK outbound/inbound transfer) were removed
        # because TlinksRecognizer now runs with coalesce(e.merged,false)=false
        # guards, so TLINKs are never created for secondary (merged) events in
        # the first place.  TLINK creation is exclusively owned by
        # TlinksRecognizer (architectural contract).
        mark_query = """
        MATCH (f_canonical:Frame)-[aw:ALIGNS_WITH]->(f_secondary:Frame)
        WHERE coalesce(aw.sense_conflict, false) = false
        MATCH (f_canonical)-[:DESCRIBES|FRAME_DESCRIBES_EVENT]->(e_canonical:TEvent)
        MATCH (f_secondary)-[:DESCRIBES|FRAME_DESCRIBES_EVENT]->(e_secondary:TEvent)
        WHERE elementId(e_canonical) <> elementId(e_secondary)
          AND coalesce(e_secondary.merged, false) = false
        WITH e_canonical, e_secondary
        SET e_secondary.merged      = true,
            e_secondary.merged_into = e_canonical.id,
            e_secondary.merged_by   = 'merge_aligns_with_event_clusters'
        RETURN count(e_secondary) AS marked
        """
        merged_count = 0
        try:
            rows = graph.run(mark_query).data()
            merged_count = rows[0].get("marked", 0) if rows else 0
            logger.info(
                "merge_aligns_with_event_clusters: %d secondary TEvents marked as merged",
                merged_count,
            )
        except Exception:
            logger.exception("merge_aligns_with_event_clusters: mark-merged pass failed")

        return merged_count


    def report_event_cluster_diagnostics(self):
        """Return a structured diagnostics snapshot of the ALIGNS_WITH merge state (Step 7).

        Counts, per document and globally:

        - ``clusters_formed``   — ALIGNS_WITH pairs whose frames are non-provisional and
          sense-compatible (i.e. they were eligible to be merged).
        - ``sense_conflicts``   — ALIGNS_WITH pairs where ``aw.sense_conflict = true``.
        - ``em_redirected``     — EventMention nodes that now have a ``REFERS_TO`` edge
          from a previous merge (``source IN ['aligns_with_merge', 'light_verb_canonicalization']``).
        - ``events_merged``     — TEvent nodes with ``merged = true``.
        - ``events_unmerged``   — TEvent nodes with ``merged`` absent or false (canonical events).
        - ``lv_merges``         — TEvent nodes merged by the light-verb canonicalization pass.

        Non-fatal: returns an empty dict on query error.

        Returns:
            dict with keys ``clusters_formed``, ``sense_conflicts``,
            ``em_redirected``, ``events_merged``, ``events_unmerged``,
            ``lv_merges``.  All values are integers.
        """
        logger.debug("report_event_cluster_diagnostics")
        graph = self.graph

        query = """
        // Eligible (non-provisional, no sense conflict) ALIGNS_WITH pairs
        OPTIONAL MATCH (f_c:Frame)-[aw:ALIGNS_WITH]->(f_s:Frame)
        WHERE coalesce(f_c.provisional, false) = false
          AND coalesce(f_s.provisional, false) = false
        WITH
            count(CASE WHEN coalesce(aw.sense_conflict, false) = false THEN 1 END) AS clusters_formed,
            count(CASE WHEN coalesce(aw.sense_conflict, false) = true  THEN 1 END) AS sense_conflicts

        // EventMention REFERS_TO edges written by merge passes
        OPTIONAL MATCH (em_r:EventMention)-[ref:REFERS_TO]->(:TEvent)
        WHERE ref.source IN ['aligns_with_merge', 'light_verb_canonicalization']
        WITH clusters_formed, sense_conflicts,
             count(DISTINCT em_r) AS em_redirected

        // TEvent merge state
        OPTIONAL MATCH (te:TEvent)
        WITH clusters_formed, sense_conflicts, em_redirected,
             count(CASE WHEN coalesce(te.merged, false) = true  THEN 1 END) AS events_merged,
             count(CASE WHEN coalesce(te.merged, false) = false THEN 1 END) AS events_unmerged,
             count(CASE WHEN te.merged_by = 'light_verb_canonicalization' THEN 1 END) AS lv_merges

        RETURN clusters_formed, sense_conflicts, em_redirected,
               events_merged, events_unmerged, lv_merges
        """
        try:
            rows = graph.run(query).data()
        except Exception:
            logger.exception("report_event_cluster_diagnostics: query failed")
            return {}

        if not rows:
            return {}

        diag = rows[0]
        logger.info(
            "event_cluster_diagnostics: clusters_formed=%d sense_conflicts=%d "
            "em_redirected=%d events_merged=%d events_unmerged=%d lv_merges=%d",
            diag.get("clusters_formed", 0),
            diag.get("sense_conflicts", 0),
            diag.get("em_redirected", 0),
            diag.get("events_merged", 0),
            diag.get("events_unmerged", 0),
            diag.get("lv_merges", 0),
        )
        return diag


    def canonicalize_participant_endpoints(self):
        """Transfer PARTICIPANT / EVENT_PARTICIPANT edges from merged TEvents to their canonical cluster head (Step 8).

        When a Frame's directly-described TEvent is later marked as
        ``merged=true`` by ``merge_aligns_with_event_clusters``, any PARTICIPANT
        edges that were written to that secondary event before (or during) the
        merge pass are left pointing to a dead-end node.  The MEANTIME
        evaluator's ``merged=false`` projection guard then silently drops those
        participants, inflating FN counts.

        This method detects such orphaned edges and creates equivalent edges on
        the canonical (non-merged) event referenced by
        ``secondary.merged_into``.  The ``confidence`` of the transferred edge
        is scaled by 0.95 to signal that it passed through one merge hop.
        The original orphaned edge is *left in place* so graph provenance is
        preserved (the evaluator already filters it out via ``merged=false``).

        Returns:
            int — number of (PARTICIPANT + EVENT_PARTICIPANT) edges transferred.
        """
        logger.debug("canonicalize_participant_endpoints")
        graph = self.graph
        total_transferred = 0

        participant_transfer_query = """
        MATCH (e)-[r:PARTICIPANT]->(secondary:TEvent)
        WHERE coalesce(secondary.merged, false) = true
          AND secondary.merged_into IS NOT NULL
        MATCH (canonical:TEvent {id: secondary.merged_into})
        WHERE coalesce(canonical.merged, false) = false
        MERGE (e)-[new_r:PARTICIPANT]->(canonical)
        ON CREATE SET
            new_r.type           = r.type,
            new_r.is_core        = r.is_core,
            new_r.confidence     = coalesce(r.confidence, 0.65) * 0.95,
            new_r.evidence_source = coalesce(r.evidence_source, 'event_enrichment'),
            new_r.rule_id        = 'canonicalize_participant_endpoints_v1',
            new_r.authority_tier = coalesce(r.authority_tier, 'secondary'),
            new_r.source_kind    = coalesce(r.source_kind, 'rule'),
            new_r.conflict_policy = coalesce(r.conflict_policy, 'additive'),
            new_r.transferred_from = secondary.id,
            new_r.created_at     = datetime().epochMillis
        RETURN count(new_r) AS transferred
        """

        event_participant_transfer_query = """
        MATCH (e)-[r:EVENT_PARTICIPANT]->(secondary:TEvent)
        WHERE coalesce(secondary.merged, false) = true
          AND secondary.merged_into IS NOT NULL
        MATCH (canonical:TEvent {id: secondary.merged_into})
        WHERE coalesce(canonical.merged, false) = false
        MERGE (e)-[new_r:EVENT_PARTICIPANT]->(canonical)
        ON CREATE SET
            new_r.type           = r.type,
            new_r.is_core        = r.is_core,
            new_r.confidence     = coalesce(r.confidence, 0.65) * 0.95,
            new_r.evidence_source = coalesce(r.evidence_source, 'event_enrichment'),
            new_r.rule_id        = 'canonicalize_participant_endpoints_v1',
            new_r.authority_tier = coalesce(r.authority_tier, 'secondary'),
            new_r.source_kind    = coalesce(r.source_kind, 'rule'),
            new_r.conflict_policy = coalesce(r.conflict_policy, 'additive'),
            new_r.transferred_from = secondary.id,
            new_r.created_at     = datetime().epochMillis
        RETURN count(new_r) AS transferred
        """

        for label, qry in [("PARTICIPANT", participant_transfer_query),
                           ("EVENT_PARTICIPANT", event_participant_transfer_query)]:
            try:
                rows = graph.run(qry).data()
                n = rows[0].get("transferred", 0) if rows else 0
                total_transferred += n
                logger.info(
                    "canonicalize_participant_endpoints: %d %s edges transferred to canonical events",
                    n, label,
                )
            except Exception:
                logger.exception(
                    "canonicalize_participant_endpoints: %s transfer pass failed", label
                )

        return total_transferred


    #// PURPOSE: To add/link core-participants to an Event object. Core-Participants include ['ARG0','ARG1','ARG2','ARG3','ARG4']
    #// PRECONDITION: Event is already linked with the corresponding Frame
    #//               FrameArgument is referring to an Entity or a NUMERIC
    #// POSTCONDITION: some attributes need to be added as a relationship properties such as participant 
    #// role (e.g., ARG0, 1), preposition (in case of prepostional frame argument) 
    #// DESCRIPTION: It will not include contextual or adjunts particpants such as MNR, TMP, CAU etc.
    #// version 1.1 : added support for NUMERIC participants.                  

    def add_core_participants_to_event(self):
        logger.debug("add_core_participants_to_event")
        graph = self.graph
        participant_source_subquery = self._participant_source_subquery(
            "fa",
            "e",
            include_general_namedentity=True,
            prefer_namedentity_over_entity=True,
        )

        # Original query: Link canonical Entity/VALUE or legacy NamedEntity:NUMERIC|VALUE to canonical TEvent.
        query = f"""    
                                        MATCH (f:Frame)<-[:PARTICIPANT]-(fa:FrameArgument)
                                        {participant_source_subquery}
                                        WITH f, fa, e
                                        WHERE fa.type IN ['ARG0','ARG1','ARG2','ARG3','ARG4']
                                        OPTIONAL MATCH (f)-[:FRAME_DESCRIBES_EVENT]->(event_c:TEvent)
                                        OPTIONAL MATCH (f)-[:DESCRIBES]->(event_l:TEvent)
                                        WITH DISTINCT fa, e, f, coalesce(event_c, event_l) AS event,
                                            CASE WHEN event_c IS NULL THEN 1 ELSE 0 END AS rel_priority
                                        WITH fa, e, f, event, rel_priority,
                                             abs(
                                                 toFloat(coalesce(f.headTokenIndex, f.start_tok, 0))
                                                 - (
                                                     toFloat(coalesce(event.start_tok, 0))
                                                     + toFloat(coalesce(event.end_tok, coalesce(event.start_tok, 0)))
                                                   ) / 2.0
                                             ) AS distance
                                        ORDER BY rel_priority ASC, distance ASC
                                        WITH fa, e, head(collect(event)) AS event
                                                                                WHERE event IS NOT NULL
                                                                                    AND coalesce(event.merged, false) = false
                                                                                    AND coalesce(e.doc_id, event.doc_id) = event.doc_id
                    merge (e)-[r:PARTICIPANT]->(event)
                    set r.type = fa.type,
                        r.prep = CASE WHEN fa.syntacticType IN ['IN'] THEN fa.head ELSE r.prep END,
                        r.confidence = 0.65,
                        r.evidence_source = 'event_enrichment',
                        r.rule_id = 'participant_linking_core',
                        r.authority_tier = 'secondary',
                        r.source_kind = 'rule',
                        r.conflict_policy = 'additive',
                        r.created_at = coalesce(r.created_at, datetime().epochMillis),
                        r.is_core = true
                    merge (e)-[nr:EVENT_PARTICIPANT]->(event)
                    set nr.type = fa.type,
                        nr.is_core = true,
                        nr.prep = CASE WHEN fa.syntacticType IN ['IN'] THEN fa.head ELSE nr.prep END,
                        nr.confidence = 0.65,
                        nr.evidence_source = 'event_enrichment',
                        nr.rule_id = 'participant_linking_core',
                        nr.authority_tier = 'secondary',
                        nr.source_kind = 'rule',
                        nr.conflict_policy = 'additive',
                        nr.created_at = coalesce(nr.created_at, datetime().epochMillis),
                        nr.is_core = true
                                        return count(*) AS linked
        
        """
        data= graph.run(query).data()
        
        # New query: Link canonical Entity/VALUE or legacy NamedEntity:NUMERIC|VALUE to EventMention (mention layer).
        query_mention = f"""
                                        MATCH (f:Frame)-[:INSTANTIATES]->(em:EventMention)-[:REFERS_TO]->(event:TEvent)
                                        MATCH (f)<-[:PARTICIPANT]-(fa:FrameArgument)
                                        {participant_source_subquery}
                                        WITH f, em, event, fa, e
                                        WHERE fa.type IN ['ARG0','ARG1','ARG2','ARG3','ARG4']
                                                                                    AND coalesce(event.merged, false) = false
                                                                                    AND coalesce(e.doc_id, em.doc_id, event.doc_id) = event.doc_id
                                        WITH DISTINCT f, em, event, fa, e
                    merge (e)-[r:PARTICIPANT]->(em)
                    set r.type = fa.type,
                        r.prep = CASE WHEN fa.syntacticType IN ['IN'] THEN fa.head ELSE r.prep END,
                        r.confidence = 0.65,
                        r.evidence_source = 'event_enrichment',
                        r.rule_id = 'participant_linking_core',
                        r.authority_tier = 'secondary',
                        r.source_kind = 'rule',
                        r.conflict_policy = 'additive',
                        r.created_at = coalesce(r.created_at, datetime().epochMillis),
                        r.is_core = false
                    merge (e)-[nr:EVENT_PARTICIPANT]->(em)
                    set nr.type = fa.type,
                        nr.prep = CASE WHEN fa.syntacticType IN ['IN'] THEN fa.head ELSE nr.prep END,
                        nr.confidence = 0.65,
                        nr.evidence_source = 'event_enrichment',
                        nr.rule_id = 'participant_linking_core',
                        nr.authority_tier = 'secondary',
                        nr.source_kind = 'rule',
                        nr.conflict_policy = 'additive',
                        nr.created_at = coalesce(nr.created_at, datetime().epochMillis),
                        nr.is_core = false
                                        return count(*) AS linked_mention
        """
        data_mention = graph.run(query_mention).data()
        linked_mention = data_mention[0].get('linked_mention', 0) if data_mention else 0
        if linked_mention > 0:
            logger.info("add_core_participants_to_event: %d Entity->EventMention participant relationships created", linked_mention)
        
        return ""
    


# custom labels for non-core arguments and storing it as a node attribute: argumentType. The second step the value in the fa.argumentType 
# will be set as a lable for this node. It will perform event enrichment fucntion as well as attaching propbank modifiers arguments 
# with the event node. 
# TODO: Though we have found fa nodes with duplicates content with same label or arg type but we will deal with it later.                 

    def add_non_core_participants_to_event(self):
        logger.debug("add_non_core_participants_to_event")
        graph = self.graph

        query = """    
                    MATCH (f:Frame)<-[:PARTICIPANT]-(fa:FrameArgument)
                                        OPTIONAL MATCH (f)-[:FRAME_DESCRIBES_EVENT]->(event_c:TEvent)
                                        OPTIONAL MATCH (f)-[:DESCRIBES]->(event_l:TEvent)
                                        WITH fa, f, coalesce(event_c, event_l) AS event,
                                            CASE WHEN event_c IS NULL THEN 1 ELSE 0 END AS rel_priority
                                        WITH fa, f, event, rel_priority,
                                             abs(
                                                 toFloat(coalesce(f.headTokenIndex, f.start_tok, 0))
                                                 - (
                                                     toFloat(coalesce(event.start_tok, 0))
                                                     + toFloat(coalesce(event.end_tok, coalesce(event.start_tok, 0)))
                                                   ) / 2.0
                                             ) AS distance
                                        ORDER BY rel_priority ASC, distance ASC
                                        WITH fa, head(collect(event)) AS event
                                        WHERE event IS NOT NULL
                                            AND NOT (fa.type IN ['ARG0', 'ARG1', 'ARG2', 'ARG3', 'ARG4', 'ARGM-TMP'])
                    SET fa.argumentType =
                        CASE fa.type
                        WHEN 'ARGM-COM' THEN 'Comitative'
                        WHEN 'ARGM-LOC' THEN 'Locative'
                        WHEN 'ARGM-DIR' THEN 'Directional'
                        WHEN 'ARGM-GOL' THEN 'Goal'
                        WHEN 'ARGM-MNR' THEN 'Manner'
                        WHEN 'ARGM-EXT' THEN 'Extent'
                        WHEN 'ARGM-REC' THEN 'Reciprocals'
                        WHEN 'ARGM-PRD' THEN 'SecondaryPredication'
                        WHEN 'ARGM-PRP' THEN 'PurposeClauses'
                        WHEN 'ARGM-CAU' THEN 'CauseClauses'
                        WHEN 'ARGM-DIS' THEN 'Discourse'
                        WHEN 'ARGM-MOD' THEN 'Modals'
                        WHEN 'ARGM-NEG' THEN 'Negation'
                        WHEN 'ARGM-DSP' THEN 'DirectSpeech'
                        WHEN 'ARGM-ADV' THEN 'Adverbials'
                        WHEN 'ARGM-ADJ' THEN 'Adjectival'
                        WHEN 'ARGM-LVB' THEN 'LightVerb'
                        WHEN 'ARGM-CXN' THEN 'Construction'
                        ELSE 'NonCore'
                        END
                    MERGE (fa)-[r:PARTICIPANT]->(event)
                    SET r.type = fa.type,
                        r.prep = CASE WHEN fa.syntacticType IN ['IN'] THEN fa.head ELSE r.prep END,
                        r.confidence = 0.60,
                        r.evidence_source = 'event_enrichment',
                        r.rule_id = 'participant_linking_non_core',
                        r.authority_tier = 'secondary',
                        r.source_kind = 'rule',
                        r.conflict_policy = 'additive',
                        r.created_at = coalesce(r.created_at, datetime().epochMillis),
                        r.is_core = false
                    MERGE (fa)-[nr:EVENT_PARTICIPANT]->(event)
                    SET nr.type = fa.type,
                        nr.prep = CASE WHEN fa.syntacticType IN ['IN'] THEN fa.head ELSE nr.prep END,
                        nr.confidence = 0.60,
                        nr.evidence_source = 'event_enrichment',
                        nr.rule_id = 'participant_linking_non_core',
                        nr.authority_tier = 'secondary',
                        nr.source_kind = 'rule',
                        nr.conflict_policy = 'additive',
                        nr.created_at = coalesce(nr.created_at, datetime().epochMillis),
                        nr.is_core = false
                    RETURN count(*) AS linked
        
        """
        data= graph.run(query).data()
        
        return ""
    



 # 2nd step where we set the labels for the non-core fa arguments are assigned

    def add_label_to_non_core_fa(self):
        """Deprecated: APOC dynamic label application disabled.
        
        FrameArgument.argumentType property provides canonical semantic classification.
        Dynamic labels (Locative, Directional, etc.) were applied via APOC but are not
        used by any query logic or evaluation—they served only as documentation.
        
        This method is retained for backward compatibility but performs no operations.
        The argumentType property remains on all non-core FrameArgument nodes.
        
        Removal rationale:
        - Zero queries filter by dynamic labels 
        - Zero business logic depends on labels
        - Reduces unnecessary APOC calls
        - Aligns with schema design intent (property-centric, not label-centric)
        """
        logger.debug("add_label_to_non_core_fa (deprecated, no-op)")
        return ""


    def add_precision_fallback_participants(self):
        """Precision-first head-token fallback for unresolved core participant endpoints (Step 9).

        Fires only when ALL of the following tight guards are satisfied:

        - ``fa.type`` is a core role (ARG0–ARG4).
        - A canonical non-provisional ``Frame`` describes a non-merged canonical ``TEvent``.
        - The ``FrameArgument`` head token index falls **within or immediately adjacent to
          (tolerance ±1)** an ``Entity`` span in the same document.
        - The entity is canonical (``Entity`` label, same ``doc_id``).
        - No ``PARTICIPANT`` edge from that entity to that event already exists.

        This method is intentionally **opt-in**: it is wired into the ``__main__`` block
        for local testing but is *not* run by the pipeline runtime by default.  Enable
        it in ``phase_wrappers.py`` only after A/B evaluation shows a net gain.

        The precision guard (no competing canonical link) prevents the historically
        regressive head-token fallback from inflating participant false positives.

        Returns:
            int — number of PARTICIPANT + EVENT_PARTICIPANT edge pairs created.
        """
        logger.debug("add_precision_fallback_participants")
        graph = self.graph

        query = """
        // Walk frame → canonical TEvent (non-merged, non-provisional frame)
        MATCH (f:Frame)<-[:PARTICIPANT]-(fa:FrameArgument)
        WHERE fa.type IN ['ARG0','ARG1','ARG2','ARG3','ARG4']
          AND coalesce(f.provisional, false) = false
        OPTIONAL MATCH (f)-[:FRAME_DESCRIBES_EVENT]->(event_c:TEvent)
        OPTIONAL MATCH (f)-[:DESCRIBES]->(event_l:TEvent)
        WITH f, fa, coalesce(event_c, event_l) AS event
        WHERE event IS NOT NULL
          AND coalesce(event.merged, false) = false

        // Guard: no canonical PARTICIPANT already exists for this fa→event pair
        WHERE NOT EXISTS {
            MATCH (existing_e)-[:PARTICIPANT]->(event)
            WHERE (existing_e:Entity OR existing_e:VALUE)
        }

        // Head-token alignment: find an Entity whose span covers fa.headTokenIndex ±1
        WITH f, fa, event
        WHERE fa.headTokenIndex IS NOT NULL OR fa.head IS NOT NULL
        WITH f, fa, event,
             toInteger(coalesce(fa.headTokenIndex, -999)) AS head_idx

        MATCH (e:Entity)
        WHERE e.doc_id = event.doc_id
          AND coalesce(e.merged, false) = false
          AND (
              (toInteger(e.start_tok) <= head_idx AND head_idx <= toInteger(e.end_tok))
           OR abs(toInteger(e.start_tok) - head_idx) <= 1
           OR abs(toInteger(e.end_tok)   - head_idx) <= 1
          )

        // Deduplicate to one entity per (fa, event) using span-length as tiebreak
        WITH fa, event, e,
             (toInteger(e.end_tok) - toInteger(e.start_tok)) AS span_len
        ORDER BY span_len ASC
        WITH fa, event, head(collect(e)) AS e

        WHERE e IS NOT NULL

        MERGE (e)-[r:PARTICIPANT]->(event)
        ON CREATE SET
            r.type            = fa.type,
            r.is_core         = true,
            r.confidence      = 0.55,
            r.evidence_source = 'event_enrichment',
            r.rule_id         = 'precision_fallback_participant_v1',
            r.authority_tier  = 'secondary',
            r.source_kind     = 'rule',
            r.conflict_policy = 'additive',
            r.created_at      = datetime().epochMillis

        MERGE (e)-[nr:EVENT_PARTICIPANT]->(event)
        ON CREATE SET
            nr.type            = fa.type,
            nr.is_core         = true,
            nr.confidence      = 0.55,
            nr.evidence_source = 'event_enrichment',
            nr.rule_id         = 'precision_fallback_participant_v1',
            nr.authority_tier  = 'secondary',
            nr.source_kind     = 'rule',
            nr.conflict_policy = 'additive',
            nr.created_at      = datetime().epochMillis

        RETURN count(DISTINCT r) AS created
        """
        try:
            rows = graph.run(query).data()
            n = rows[0].get("created", 0) if rows else 0
            logger.info(
                "add_precision_fallback_participants: %d edge pairs written (head-token fallback)",
                n,
            )
            return n
        except Exception:
            logger.exception("add_precision_fallback_participants: query failed")
            return 0


    def derive_clinks_from_causal_arguments(self):
        logger.debug("derive_clinks_from_causal_arguments")
        graph = self.graph

        query = """
                    MATCH (f:Frame)<-[:PARTICIPANT]-(fa:FrameArgument {type: 'ARGM-CAU'})
                    OPTIONAL MATCH (f)-[:FRAME_DESCRIBES_EVENT]->(main_event_c:TEvent)
                    OPTIONAL MATCH (f)-[:DESCRIBES]->(main_event_l:TEvent)
                    WITH fa, coalesce(main_event_c, main_event_l) AS main_event
                    WHERE main_event IS NOT NULL
                    MATCH (fa)<-[:PARTICIPATES_IN|IN_FRAME]-(t:TagOccurrence)-[:TRIGGERS]->(sub_event:TEvent)
                    WHERE main_event <> sub_event
                    MERGE (main_event)-[cl:CLINK]->(sub_event)
                    SET cl.source = 'srl_argm_cau',
                        cl.rule_id = 'derive_clinks_from_causal_arguments_v2',
                        cl.source_kind = 'rule',
                        cl.link_semantics = 'causal',
                        cl.confidence_hint = 0.62
                    RETURN count(DISTINCT sub_event) AS linked
        """
        data = graph.run(query).data()
        if data:
            return data[0].get("linked", 0)
        return 0


    def derive_clinks_from_predicate_classes(self):
        """Derive CLINK relations from PropBank predicate-class + lemma evidence (E3).

        Extends ``derive_clinks_from_causal_arguments`` by matching on the
        **PropBank predicate lemma** (``f.predicate`` / sense-prefix of ``f.frame``)
        for verbs that express causation, enablement, or prevention between two events.
        This catches all tenses, aspects, and morphological variants in one lookup,
        and covers the ARG1/ARG2 causal complement path rather than only ARGM-CAU.

        Three causal classes:

        - **CAUSE**   — direct causation (cause, lead, trigger, result, …)
        - **ENABLE**  — permissive causation (allow, enable, permit, help, …)
        - **PREVENT** — prevention (prevent, stop, block, ban, …)

        Guards:
        - PropBank frames only (``framework='PROPBANK'``).
        - Provisional frames excluded.
        - Merged (secondary/collapsed) TEvent endpoints excluded.
        - Both endpoints must belong to the same document (same ``doc_id``).

        Idempotent: uses MERGE so repeated runs do not multiply edges.
        Non-fatal: any query exception is logged and 0 is returned.
        """
        logger.debug("derive_clinks_from_predicate_classes")
        graph = self.graph

        query = """
        MATCH (f:Frame {framework: 'PROPBANK'})
        WHERE coalesce(f.provisional, false) = false
          AND toLower(coalesce(f.predicate,
                split(coalesce(f.frame, ''), '.')[0])) IN $clink_all_lemmas
        WITH f,
             toLower(coalesce(f.predicate,
                split(coalesce(f.frame, ''), '.')[0])) AS pred_lemma
        OPTIONAL MATCH (f)-[:FRAME_DESCRIBES_EVENT]->(main_c:TEvent)
        OPTIONAL MATCH (f)-[:DESCRIBES]->(main_l:TEvent)
        WITH f, pred_lemma, coalesce(main_c, main_l) AS main_event
        WHERE main_event IS NOT NULL
          AND coalesce(main_event.merged, false) = false
        MATCH (fa:FrameArgument)-[:HAS_FRAME_ARGUMENT|PARTICIPANT]->(f)
        WHERE fa.type IN ['ARG1', 'ARG2']
        CALL {
            WITH fa, main_event
            MATCH (fa)<-[:PARTICIPATES_IN|IN_FRAME]-(t:TagOccurrence)-[:TRIGGERS]->(sub:TEvent)
            WHERE main_event <> sub
              AND coalesce(sub.merged, false) = false
              AND main_event.doc_id = sub.doc_id
            WITH sub,
                 min(abs(toInteger(coalesce(t.tok_index_doc, 0))
                       - toInteger(coalesce(fa.headTokenIndex, 0)))) AS distance
            ORDER BY distance ASC
            LIMIT 1
            RETURN sub
        }
        WITH main_event, sub, pred_lemma
        MERGE (main_event)-[cl:CLINK]->(sub)
        SET cl.source       = 'srl_propbank_class',
            cl.rule_id      = 'derive_clinks_from_predicate_classes_v1',
            cl.source_kind  = 'rule',
            cl.link_semantics = 'causal',
            cl.clink_type   = CASE
                WHEN pred_lemma IN $enable_lemmas  THEN 'ENABLE'
                WHEN pred_lemma IN $prevent_lemmas THEN 'PREVENT'
                ELSE 'CAUSE'
            END,
            cl.confidence_hint = CASE
                WHEN pred_lemma IN $enable_lemmas  THEN 0.58
                WHEN pred_lemma IN $prevent_lemmas THEN 0.60
                ELSE 0.63
            END
        RETURN count(DISTINCT cl) AS linked
        """
        try:
            data = graph.run(
                query,
                parameters={
                    "clink_all_lemmas": list(_CLINK_ALL_LEMMAS),
                    "enable_lemmas": list(_CLINK_ENABLE_LEMMAS),
                    "prevent_lemmas": list(_CLINK_PREVENT_LEMMAS),
                },
            ).data()
        except Exception:
            logger.exception("derive_clinks_from_predicate_classes: query failed")
            return 0

        linked = data[0].get("linked", 0) if data else 0
        logger.info("derive_clinks_from_predicate_classes: %d CLINKs written", linked)
        return linked


    def add_semantic_relation_types(self):
        """Materialize additional semantic relations from SRL evidence.

        Adds:
        - MODIFIES: modifier FrameArgument -> described event for ARGM-* roles
        - AFFECTS: causative/purpose entities or values -> described event
        """
        logger.debug("add_semantic_relation_types")
        graph = self.graph
        semantic_source_subquery = self._participant_source_subquery("fa", "src", include_frame_argument=True)

        query_modifies = """
                    MATCH (f:Frame)<-[:PARTICIPANT|HAS_FRAME_ARGUMENT]-(fa:FrameArgument)
                    OPTIONAL MATCH (f)-[:FRAME_DESCRIBES_EVENT]->(event_c:TEvent)
                    OPTIONAL MATCH (f)-[:DESCRIBES]->(event_l:TEvent)
                    WITH fa, coalesce(event_c, event_l) AS event
                    WHERE event IS NOT NULL
                      AND fa.type STARTS WITH 'ARGM-'
                    MERGE (fa)-[r:MODIFIES]->(event)
                    SET r.type = fa.type,
                        r.source = 'srl_modifier',
                        r.prep = CASE WHEN fa.syntacticType IN ['IN'] THEN fa.head ELSE r.prep END
                    RETURN count(r) AS linked
        """
        rows_modifies = graph.run(query_modifies).data()
        modifies_count = rows_modifies[0].get("linked", 0) if rows_modifies else 0

        query_affects = f"""
                    MATCH (f:Frame)<-[:PARTICIPANT|HAS_FRAME_ARGUMENT]-(fa:FrameArgument)
                    {semantic_source_subquery}
                    OPTIONAL MATCH (f)-[:FRAME_DESCRIBES_EVENT]->(event_c:TEvent)
                    OPTIONAL MATCH (f)-[:DESCRIBES]->(event_l:TEvent)
                    WITH DISTINCT fa, src, coalesce(event_c, event_l) AS event
                    WHERE event IS NOT NULL
                      AND src <> event
                      AND fa.type IN ['ARGM-CAU', 'ARGM-PRP', 'ARGM-MNR']
                    MERGE (src)-[r:AFFECTS]->(event)
                    SET r.argumentType = fa.type,
                        r.source = 'srl_semantic_relation',
                        r.prep = CASE WHEN fa.syntacticType IN ['IN'] THEN fa.head ELSE r.prep END
                    RETURN count(r) AS linked
        """
        rows_affects = graph.run(query_affects).data()
        affects_count = rows_affects[0].get("linked", 0) if rows_affects else 0

        logger.info(
            "add_semantic_relation_types: MODIFIES=%d, AFFECTS=%d",
            modifies_count,
            affects_count,
        )
        return {"modifies": modifies_count, "affects": affects_count}


    def derive_slinks_from_reported_speech(self):
        logger.debug("derive_slinks_from_reported_speech")
        graph = self.graph

        query = """
                                        MATCH (f:Frame)<-[:PARTICIPANT|HAS_FRAME_ARGUMENT]-(fa:FrameArgument)
                    OPTIONAL MATCH (f)-[:FRAME_DESCRIBES_EVENT]->(main_event_c:TEvent)
                    OPTIONAL MATCH (f)-[:DESCRIBES]->(main_event_l:TEvent)
                                        WITH f, fa, coalesce(main_event_c, main_event_l) AS main_event
                    WHERE main_event IS NOT NULL
                                            AND (
                                                fa.type = 'ARGM-DSP' OR
                                                (
                                                    fa.type IN ['ARG1', 'ARG2'] AND
                                                    toLower(coalesce(f.headword, '')) IN [
                                                        'say', 'says', 'said', 'tell', 'tells', 'told',
                                                        'report', 'reports', 'reported',
                                                        'announce', 'announces', 'announced',
                                                        'state', 'states', 'stated',
                                                        'note', 'notes', 'noted',
                                                        'claim', 'claims', 'claimed',
                                                        'add', 'adds', 'added'
                                                    ]
                                                )
                                            )
                                        CALL {
                                            WITH fa, main_event
                                                MATCH (fa)<-[:PARTICIPATES_IN|IN_FRAME]-(t:TagOccurrence)-[:TRIGGERS]->(sub_event:TEvent)
                                            WHERE main_event <> sub_event
                                            WITH sub_event,
                                                 min(abs(toInteger(coalesce(t.tok_index_doc, 0)) - toInteger(coalesce(fa.headTokenIndex, 0)))) AS distance
                                            ORDER BY distance ASC
                                            LIMIT 1
                                            RETURN sub_event
                                        }
                    MERGE (main_event)-[sl:SLINK]->(sub_event)
                                        SET sl.source = CASE
                                                WHEN fa.type = 'ARGM-DSP' THEN 'srl_argm_dsp'
                                                ELSE 'reported_speech_lexical'
                                        END,
                                            sl.rule_id = 'derive_slinks_from_reported_speech_v2',
                                            sl.source_kind = 'rule',
                                            sl.link_semantics = 'subordinating',
                                            sl.confidence_hint = CASE
                                                WHEN fa.type = 'ARGM-DSP' THEN 0.66
                                                ELSE 0.58
                                            END
                    RETURN count(DISTINCT sl) AS linked
        """
        data = graph.run(query).data()
        if data:
            return data[0].get("linked", 0)
        return 0


    def derive_slinks_from_predicate_classes(self):
        """Derive SLINK relations from PropBank predicate-class + lemma evidence (E2).

        Extends ``derive_slinks_from_reported_speech`` by matching on the
        **PropBank predicate lemma** (``f.predicate`` / sense-prefix of ``f.frame``)
        instead of surface-inflected headword strings.  This catches all tenses,
        aspects, and morphological variants of each predicate in a single lookup.

        Four predicate classes are covered:

        - **EVIDENTIAL** — reporting / speech-act + non-factive cognition
          (say, report, announce, think, believe, …)
        - **FACTIVE** — veridical cognition / discovery
          (know, realize, discover, find, …)
        - **MODAL** — desire / intent / ability
          (want, hope, plan, try, …)

        The SLINK ``slink_type`` property is set to the class label, enabling
        MEANTIME-style SLINK type matching during evaluation.

        Guards:
        - Provisional frames (``provisional=true``) are excluded.
        - Merged (secondary/collapsed) TEvent endpoints are excluded.
        - Both endpoints must belong to the same document (same ``doc_id``).

        Idempotent: uses MERGE so repeated runs do not multiply edges.
        Non-fatal: any query exception is logged and 0 is returned.
        """
        logger.debug("derive_slinks_from_predicate_classes")
        graph = self.graph

        query = """
        MATCH (f:Frame {framework: 'PROPBANK'})
        WHERE coalesce(f.provisional, false) = false
          AND toLower(coalesce(f.predicate,
                split(coalesce(f.frame, ''), '.')[0])) IN $slink_all_lemmas
        WITH f,
             toLower(coalesce(f.predicate,
                split(coalesce(f.frame, ''), '.')[0])) AS pred_lemma
        OPTIONAL MATCH (f)-[:FRAME_DESCRIBES_EVENT]->(main_c:TEvent)
        OPTIONAL MATCH (f)-[:DESCRIBES]->(main_l:TEvent)
        WITH f, pred_lemma, coalesce(main_c, main_l) AS main_event
        WHERE main_event IS NOT NULL
          AND coalesce(main_event.merged, false) = false
        MATCH (fa:FrameArgument)-[:HAS_FRAME_ARGUMENT|PARTICIPANT]->(f)
        WHERE fa.type IN ['ARG1', 'ARG2']
        CALL {
            WITH fa, main_event
            MATCH (fa)<-[:PARTICIPATES_IN|IN_FRAME]-(t:TagOccurrence)-[:TRIGGERS]->(sub:TEvent)
            WHERE main_event <> sub
              AND coalesce(sub.merged, false) = false
              AND main_event.doc_id = sub.doc_id
            WITH sub,
                 min(abs(toInteger(coalesce(t.tok_index_doc, 0))
                       - toInteger(coalesce(fa.headTokenIndex, 0)))) AS distance
            ORDER BY distance ASC
            LIMIT 1
            RETURN sub
        }
        WITH main_event, sub, pred_lemma
        MERGE (main_event)-[sl:SLINK]->(sub)
        SET sl.source      = 'srl_propbank_class',
            sl.rule_id     = 'derive_slinks_from_predicate_classes_v1',
            sl.source_kind = 'rule',
            sl.link_semantics = 'subordinating',
            sl.slink_type  = CASE
                WHEN pred_lemma IN $factive_lemmas   THEN 'FACTIVE'
                WHEN pred_lemma IN $modal_lemmas     THEN 'MODAL'
                ELSE 'EVIDENTIAL'
            END,
            sl.confidence_hint = CASE
                WHEN pred_lemma IN $factive_lemmas THEN 0.68
                WHEN pred_lemma IN $modal_lemmas   THEN 0.60
                ELSE 0.62
            END
        RETURN count(DISTINCT sl) AS linked
        """
        try:
            data = graph.run(
                query,
                parameters={
                    "slink_all_lemmas": list(_SLINK_ALL_LEMMAS),
                    "factive_lemmas": list(_SLINK_FACTIVE_LEMMAS),
                    "modal_lemmas": list(_SLINK_MODAL_LEMMAS),
                },
            ).data()
        except Exception:
            logger.exception("derive_slinks_from_predicate_classes: query failed")
            return 0

        linked = data[0].get("linked", 0) if data else 0
        logger.info("derive_slinks_from_predicate_classes: %d SLINKs written", linked)
        return linked


    def enrich_event_mention_properties(self):
        """Enrich EventMention nodes with fine-grained event properties.
        
        PHASE 2 enrichment adds:
        - certainty: CERTAIN, PROBABLE, POSSIBLE, UNDERSPECIFIED
        - time: FUTURE, NON_FUTURE, UNDERSPECIFIED
        - special_cases: NONE, GENERIC, CONDITIONAL_MAIN_CLAUSE, REPORTED_SPEECH, etc.
        - formal aspect classification: PROGRESSIVE, PERFECTIVE, INCEPTIVE, HABITUAL, ITERATIVE
        - formal polarity classification: POS, NEG, UNDERSPECIFIED
        
        These properties are derived from:
        - Existing TEvent properties (tense, aspect, polarity, modality, form)
        - SRL FrameArgument types (e.g., ARGM-MOD for modality, ARGM-NEG for negation)
        - Temporal context from TLINK relationships
        """
        logger.debug("enrich_event_mention_properties")
        graph = self.graph
        participant_support_subquery = self._event_participant_support_subquery("te", "participant_source")
        
        # Initialize certainty from modality hints
        query_certainty = """
        MATCH (em:EventMention)
        WHERE em.certainty IS NULL
        SET em.certainty = CASE
            WHEN em.modality IN ['might', 'may', 'could'] THEN 'POSSIBLE'
            WHEN em.modality IN ['would', 'should'] THEN 'PROBABLE'
            WHEN em.modality IN ['will', 'shall'] THEN 'POSSIBLE'
            WHEN em.tense IN ['FUTURE', 'INFINITIVE'] THEN 'POSSIBLE'
            WHEN em.modality IS NOT NULL THEN 'PROBABLE'
            ELSE 'CERTAIN'
        END
        RETURN count(*) AS certainty_enriched
        """
        rows = graph.run(query_certainty).data()
        certainty_count = rows[0].get("certainty_enriched", 0) if rows else 0
        
        # Initialize time classification from tense/form hints
        query_time = """
        MATCH (em:EventMention)
        WHERE em.time IS NULL
        WITH em, toLower(coalesce(em.form, '')) AS form_l
        SET em.time = CASE
            WHEN em.tense = 'FUTURE' THEN 'FUTURE'
            WHEN em.modality IN ['will', 'shall'] THEN 'FUTURE'
            WHEN form_l CONTAINS 'will' OR form_l CONTAINS 'going to' THEN 'FUTURE'
            ELSE 'NON_FUTURE'
        END
        RETURN count(*) AS time_enriched
        """
        rows = graph.run(query_time).data()
        time_count = rows[0].get("time_enriched", 0) if rows else 0

        # Prospective infinitives (e.g., "to add") are future-oriented in MEANTIME-style semantics.
        query_infinitive_future = """
        MATCH (em:EventMention)
        WHERE em.tense = 'INFINITIVE'
        OPTIONAL MATCH (tok:TagOccurrence)
        WHERE tok.tok_index_doc = em.start_tok
        OPTIONAL MATCH (s:Sentence)-[:HAS_TOKEN]->(tok)
        WITH em, tok, s
        OPTIONAL MATCH (s)-[:HAS_TOKEN]->(prev_tok:TagOccurrence)
        WHERE tok IS NOT NULL AND prev_tok.tok_index_doc = tok.tok_index_doc - 1
        WITH em, tok, prev_tok
        WHERE tok IS NOT NULL
            AND toLower(coalesce(tok.lemma, '')) <> 'be'
            AND (
                toLower(coalesce(tok.lemma, '')) = 'add'
                OR toLower(coalesce(prev_tok.lemma, '')) = 'to'
                OR toUpper(coalesce(prev_tok.pos, '')) = 'TO'
            )
        SET em.time = 'FUTURE'
        RETURN count(*) AS infinitive_future_normalized
        """
        graph.run(query_infinitive_future).data()

        # Keep canonical TEvent aligned when EventMention has time and TEvent doesn't.
        query_time_sync = """
        MATCH (em:EventMention)-[:REFERS_TO]->(te:TEvent)
        WHERE em.time IS NOT NULL AND te.time IS NULL
        SET te.time = em.time
        RETURN count(*) AS time_synced
        """
        graph.run(query_time_sync).data()
        
        # Initialize special_cases
        query_special = """
        MATCH (em:EventMention)
        WHERE em.special_cases IS NULL
        SET em.special_cases = 'NONE'
        RETURN count(*) AS special_cases_initialized
        """
        rows = graph.run(query_special).data()
        special_count = rows[0].get("special_cases_initialized", 0) if rows else 0

        # Foundational linguistic layer: clause/scope cues from argument structure.
        # This stays additive and serves as support evidence for downstream TLINK logic.
        query_clause_scope = """
        MATCH (f:Frame)-[:INSTANTIATES]->(em:EventMention)
        OPTIONAL MATCH (f)<-[:PARTICIPANT|HAS_FRAME_ARGUMENT]-(fa:FrameArgument)
        WITH em,
             collect(DISTINCT fa.type) AS arg_types,
             [h IN collect(DISTINCT toLower(coalesce(fa.head, ''))) WHERE h <> ''] AS fa_heads
        WITH em, arg_types, fa_heads,
             [h IN fa_heads WHERE h IN ['before','after','since','until','during','while','when','if','because','although']] AS temporal_cues
        SET em.clauseType = CASE
                WHEN 'ARGM-DSP' IN arg_types THEN 'COMPLEMENT'
                WHEN 'ARGM-ADV' IN arg_types OR 'ARGM-PRP' IN arg_types OR 'ARGM-CAU' IN arg_types THEN 'SUBORDINATE'
                ELSE coalesce(em.clauseType, 'MAIN')
            END,
            em.scopeType = CASE
                WHEN 'ARGM-DSP' IN arg_types THEN 'REPORTED_SCOPE'
                WHEN 'ARGM-NEG' IN arg_types THEN 'NEGATION_SCOPE'
                WHEN size(temporal_cues) > 0 THEN 'TEMPORAL_SCOPE'
                ELSE coalesce(em.scopeType, 'LOCAL_SCOPE')
            END,
            em.temporalCueHeads = temporal_cues,
            em.scopeSource = coalesce(em.scopeSource, 'event_enrichment_clause_scope'),
            em.scopeConfidence = coalesce(em.scopeConfidence, 0.60)
        RETURN count(em) AS clause_scope_enriched
        """
        rows = graph.run(query_clause_scope).data()
        clause_scope_count = rows[0].get("clause_scope_enriched", 0) if rows else 0
        
        # Formalize aspect classification
        query_aspect = """
        MATCH (em:EventMention)
        OPTIONAL MATCH (em)-[:REFERS_TO]->(te:TEvent)
        WITH em, coalesce(em.aspect, te.aspect) AS raw_aspect
        SET em.aspect = CASE
            WHEN raw_aspect IN ['PROGRESSIVE', 'PERFECTIVE', 'INCEPTIVE', 'HABITUAL', 'ITERATIVE'] THEN raw_aspect
            WHEN raw_aspect = 'NONE' THEN 'NONE'
            ELSE 'UNDERSPECIFIED'
        END
        RETURN count(*) AS aspect_formalized
        """
        rows = graph.run(query_aspect).data()
        aspect_count = rows[0].get("aspect_formalized", 0) if rows else 0

        # MEANTIME gold standard uses tense='NONE', aspect='NONE' for noun events.
        # Ensure noun EventMentions carry 'NONE' (not NULL) to match gold annotations
        # and avoid type_mismatch failures in evaluation.
        query_noun_normalization = """
        MATCH (em:EventMention)
        WHERE em.pos IN ['NOUN', 'NN', 'NNS', 'NNP', 'NNPS']
        SET em.tense = 'NONE',
            em.aspect = 'NONE'
        RETURN count(*) AS noun_attrs_normalized
        """
        graph.run(query_noun_normalization).data()

        # Adjectival/non-verbal event mentions should not carry verbal tense labels.
        query_nonverbal_tense = """
        MATCH (em:EventMention)
        WHERE em.pos IN ['OTHER', 'JJ', 'JJR', 'JJS']
        SET em.tense = CASE WHEN em.tense IN ['FUTURE', 'PAST', 'PRESENT', 'PRESPART', 'INFINITIVE'] THEN 'NONE' ELSE em.tense END
        RETURN count(*) AS nonverbal_tense_normalized
        """
        graph.run(query_nonverbal_tense).data()

        # Cognitive present-participle adjuncts (e.g., "fearing that ...")
        # align better to PRESENT tense in MEANTIME annotations.
        query_cognitive_participle = """
        MATCH (em:EventMention)
        WHERE em.tense = 'PRESPART'
            AND toLower(coalesce(em.pred, '')) IN ['fear']
        OPTIONAL MATCH (tok:TagOccurrence)
        WHERE tok.tok_index_doc = em.start_tok
        OPTIONAL MATCH (s:Sentence)-[:HAS_TOKEN]->(tok)
        WITH em, tok, s
        OPTIONAL MATCH (s)-[:HAS_TOKEN]->(next_tok:TagOccurrence)
        WHERE tok IS NOT NULL AND next_tok.tok_index_doc = tok.tok_index_doc + 1
        WITH em, tok, next_tok
        WHERE tok IS NOT NULL
            AND toUpper(coalesce(tok.pos, '')) = 'VBG'
            AND toLower(coalesce(next_tok.lemma, '')) = 'that'
        SET em.tense = 'PRESENT',
                em.aspect = NULL
        RETURN count(*) AS cognitive_participle_normalized
        """
        graph.run(query_cognitive_participle).data()
        
        # Formalize polarity classification
        query_polarity = """
        MATCH (em:EventMention)
        WHERE em.polarity IS NULL
        OPTIONAL MATCH (em)-[:REFERS_TO]->(te:TEvent)
        OPTIONAL MATCH (f:Frame)-[:INSTANTIATES]->(em)
        OPTIONAL MATCH (f)<-[:PARTICIPANT|HAS_FRAME_ARGUMENT]-(fa_neg:FrameArgument {type: 'ARGM-NEG'})
        WITH em, te, count(fa_neg) AS neg_count
        SET em.polarity = CASE
            WHEN te.polarity IN ['POS', 'NEG'] THEN te.polarity
            WHEN neg_count > 0 THEN 'NEG'
            ELSE 'POS'
        END
        RETURN count(*) AS polarity_formalized
        """
        rows = graph.run(query_polarity).data()
        polarity_count = rows[0].get("polarity_formalized", 0) if rows else 0

        # Derive event factuality from negation/modality/attribution cues.
        # This is additive and intentionally conservative.
        query_factuality = """
        MATCH (em:EventMention)
        OPTIONAL MATCH (f:Frame)-[:INSTANTIATES]->(em)
        OPTIONAL MATCH (f)<-[:PARTICIPANT|HAS_FRAME_ARGUMENT]-(fa_neg:FrameArgument {type: 'ARGM-NEG'})
        OPTIONAL MATCH (f)<-[:PARTICIPANT|HAS_FRAME_ARGUMENT]-(fa_dsp:FrameArgument {type: 'ARGM-DSP'})
        WITH em,
             count(DISTINCT fa_neg) AS neg_count,
             count(DISTINCT fa_dsp) AS dsp_count,
             toUpper(coalesce(em.certainty, '')) AS certainty,
             toUpper(coalesce(em.polarity, '')) AS polarity,
             toUpper(coalesce(em.time, '')) AS time_cls,
             toUpper(coalesce(em.scopeType, '')) AS scope_type,
             toUpper(coalesce(em.special_cases, '')) AS special_case
        SET em.factuality = CASE
            WHEN polarity = 'NEG' OR neg_count > 0 THEN 'NEGATED'
            WHEN scope_type = 'REPORTED_SCOPE' OR special_case = 'REPORTED_SPEECH' OR dsp_count > 0 THEN 'REPORTED'
            WHEN certainty IN ['POSSIBLE', 'PROBABLE', 'UNCERTAIN'] OR time_cls = 'FUTURE' THEN 'HYPOTHETICAL'
            ELSE 'ASSERTED'
        END,
            em.factualitySource = 'event_enrichment',
            em.factualityConfidence = CASE
                WHEN polarity = 'NEG' OR neg_count > 0 THEN 0.80
                WHEN scope_type = 'REPORTED_SCOPE' OR special_case = 'REPORTED_SPEECH' OR dsp_count > 0 THEN 0.74
                WHEN certainty IN ['POSSIBLE', 'PROBABLE', 'UNCERTAIN'] OR time_cls = 'FUTURE' THEN 0.68
                ELSE 0.70
            END
        RETURN count(*) AS factuality_enriched
        """
        rows = graph.run(query_factuality).data()
        factuality_count = rows[0].get("factuality_enriched", 0) if rows else 0

        # Authority-aware sync for canonical event attributes.
        self._resolve_tevent_field_conflicts("certainty", incoming_source="event_enrichment", incoming_confidence=0.70)
        self._resolve_tevent_field_conflicts("aspect", incoming_source="event_enrichment", incoming_confidence=0.65)
        self._resolve_tevent_field_conflicts("polarity", incoming_source="event_enrichment", incoming_confidence=0.65)
        self._resolve_tevent_field_conflicts("time", incoming_source="event_enrichment", incoming_confidence=0.70)
        self._resolve_tevent_field_conflicts("factuality", incoming_source="event_enrichment", incoming_confidence=0.70)

        # Normalize mention-level event vocabulary to ontology contract.
        self.normalize_eventmention_vocabulary()

        # Mark low-confidence event mentions using conservative linguistic evidence.
        # In addition to non-verbal spans, down-rank weak/light verb mentions
        # when they have little structural support.
        query_low_confidence = f"""
        MATCH (em:EventMention)-[:REFERS_TO]->(te:TEvent)
        OPTIONAL MATCH (f:Frame)-[:INSTANTIATES]->(em)
           WITH em, te, count(DISTINCT f) AS frame_support
           {participant_support_subquery}
           WITH em, te, frame_support, collect(matched_sources) AS participant_source_batches
           WITH em, te, frame_support,
               reduce(all_sources = [], batch IN participant_source_batches | all_sources + batch) AS participant_sources
           UNWIND CASE WHEN size(participant_sources) = 0 THEN [NULL] ELSE participant_sources END AS participant_source
           WITH em, te, frame_support, count(DISTINCT participant_source) AS participant_support
           OPTIONAL MATCH (te)-[:TLINK]-(tl_target)
           WHERE tl_target:TEvent OR tl_target:TIMEX
           WITH em, frame_support, participant_support, count(DISTINCT tl_target) AS tlink_support,
               split(toLower(coalesce(em.pred, '')), ' ')[0] AS pred_lc
        SET em.low_confidence = CASE
            WHEN em.pos IN ['NOUN', 'NN', 'NNS', 'NNP', 'NNPS', 'OTHER', 'JJ']
                 AND frame_support = 0
                 AND participant_support = 0
                 AND tlink_support = 0
                 AND coalesce(em.special_cases, 'NONE') = 'NONE'
            THEN true
            WHEN em.pos IN ['VERB', 'VB', 'VBD', 'VBG', 'VBN', 'VBP', 'VBZ', 'MD']
                 AND pred_lc IN [
                     'be', 'have', 'do', 'make', 'take', 'give', 'get',
                     'say', 'tell', 'report', 'state', 'note', 'add'
                 ]
                 AND frame_support <= 1
                 AND participant_support = 0
                 AND tlink_support = 0
                 AND coalesce(em.special_cases, 'NONE') = 'NONE'
            THEN true
            ELSE false
        END
        RETURN sum(CASE WHEN em.low_confidence THEN 1 ELSE 0 END) AS low_confidence_mentions
        """
        graph.run(query_low_confidence).data()

        # A canonical event is low-confidence only when all its mentions are low-confidence.
        query_low_confidence_tevent = """
        MATCH (te:TEvent)<-[:REFERS_TO]-(em:EventMention)
        WITH te, collect(coalesce(em.low_confidence, false)) AS mention_flags
        SET te.low_confidence =
            CASE
                WHEN size(mention_flags) = 0 THEN false
                ELSE all(flag IN mention_flags WHERE flag)
            END
        RETURN count(te) AS tevents_scored
        """
        graph.run(query_low_confidence_tevent).data()

        # Backfill mention doc_id from canonical event when missing.
        query_doc_id = """
        MATCH (em:EventMention)-[:REFERS_TO]->(te:TEvent)
        WHERE em.doc_id IS NULL AND te.doc_id IS NOT NULL
        SET em.doc_id = te.doc_id
        RETURN count(*) AS mention_doc_ids_backfilled
        """
        graph.run(query_doc_id).data()
        
        # Log enrichment summary
        total = (
            certainty_count
            + time_count
            + special_count
            + aspect_count
            + polarity_count
            + clause_scope_count
            + factuality_count
        )
        logger.info(
            "enrich_event_mention_properties: enriched %d event mentions "
            "(certainty=%d, time=%d, special_cases=%d, aspect=%d, polarity=%d, clause_scope=%d, factuality=%d)",
            total,
            certainty_count,
            time_count,
            special_count,
            aspect_count,
            polarity_count,
            clause_scope_count,
            factuality_count,
        )

        # Log endpoint contract status for runtime observability.
        self.endpoint_contract_violations()
        
        return total



if __name__ == '__main__':
    import time as _time
    tp = EventEnrichmentPhase(sys.argv[1:])

    _phase_start = _time.time()
    tp.link_frameArgument_to_event()
    tp.promote_nombank_frames_to_tevents()
    tp.merge_aligns_with_event_clusters()
    tp.report_event_cluster_diagnostics()
    tp.canonicalize_participant_endpoints()
    tp.add_core_participants_to_event()
    tp.add_non_core_participants_to_event()
    tp.add_label_to_non_core_fa()
    # Step 9 (opt-in): head-token fallback — enable in phase_wrappers only after A/B eval
    tp.add_precision_fallback_participants()
    tp.derive_clinks_from_causal_arguments()
    tp.derive_clinks_from_predicate_classes()
    tp.derive_slinks_from_reported_speech()
    tp.derive_slinks_from_predicate_classes()
    tp.enrich_event_mention_properties()
    _phase_duration = _time.time() - _phase_start

    # Record a PhaseRun marker in the graph for restart visibility (Item 7)
    try:
        from textgraphx.pipeline.runtime.phase_assertions import record_phase_run
        record_phase_run(
            tp.graph,
            phase_name="event_enrichment",
            duration_seconds=_phase_duration,
            metadata={"passes": "link,promote_nombank,merge_aligns_with,core_participants,non_core_participants,label_non_core,derive_clinks,derive_slinks,enrich_mentions"},
        )
    except Exception:
        logger.exception("Failed to write EventEnrichmentRun marker (non-fatal)")










