"""EventEnrichmentPhase

Attach frames to temporalized events and populate participant relationships
between canonical `Entity`/`NUMERIC` nodes and `TEvent` nodes. This phase
assumes frames and TIMEX/TEvent nodes are already present in the graph and
performs idempotent MERGE updates to create `DESCRIBES` and `PARTICIPANT`
edges.
"""

import os
import spacy
import sys

# When run as a script, allow imports by ensuring repo root is available.
if __name__ == '__main__' and __package__ is None:
    from pathlib import Path
    repo_root = Path(__file__).resolve().parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
#import neuralcoref

from textgraphx.util.SemanticRoleLabeler import SemanticRoleLabel
from textgraphx.util.EntityFishingLinker import EntityFishing
from spacy.tokens import Doc, Token, Span
from textgraphx.util.RestCaller import callAllenNlpApi
from textgraphx.util.GraphDbBase import GraphDBBase
from textgraphx.TextProcessor import TextProcessor
import xml.etree.ElementTree as ET
# legacy py2neo imports removed; use bolt-driver wrapper via neo4j_client
import logging

from textgraphx.neo4j_client import make_graph_from_config
from textgraphx.config import get_config
from textgraphx.merge_utils import resolve_attribute_conflict

logger = logging.getLogger(__name__)



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
        }
        return defaults.get(field_name, ("temporal_phase", 0.90))

    def _resolve_tevent_field_conflicts(self, field_name, incoming_source="event_enrichment", incoming_confidence=0.65):
        """Resolve TEvent field conflicts using authority-aware merge policy.

        Existing canonical TEvent values (typically temporal-phase primary)
        are preferred over secondary mention-level backfills. Conflicting
        values are retained as explicit conflict metadata for auditability.
        """
        if field_name not in {"certainty", "aspect", "polarity", "time"}:
            raise ValueError("Unsupported TEvent field for conflict resolution")

        default_existing_source, default_existing_conf = self._tevent_field_defaults(field_name)
        graph = self.graph
        query = f"""
        MATCH (em:EventMention)-[:REFERS_TO]->(te:TEvent)
        WHERE em.{field_name} IS NOT NULL
        RETURN id(te) AS te_id,
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
            WHERE id(te) = $te_id
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

         


    # Link Frame to TEvent via DESCRIBES relationship.
    # Also link Frame to EventMention via INSTANTIATES relationship.
    # Two complementary paths are used to maximise coverage (Item 6 refactor):
    #   Path 1 – direct:   TagOccurrence PARTICIPATES_IN Frame  AND  TRIGGERS TEvent
    #   Path 2 – via args: TagOccurrence PARTICIPATES_IN FrameArgument PARTICIPANT Frame
    #                      AND same TagOccurrence TRIGGERS TEvent
    # Both paths are idempotent (MERGE) so running them together is safe.
    def link_frameArgument_to_event(self):
        logger.debug("link_frameArgument_to_event")
        graph = self.graph
        linked = 0

        # Path 1: token directly participates in Frame and triggers TEvent
        query_direct = """
            MATCH (f:Frame)<-[:PARTICIPATES_IN]-(t:TagOccurrence)-[:TRIGGERS]->(event:TEvent)
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
            MATCH (fa)<-[:PARTICIPATES_IN]-(t:TagOccurrence)-[:TRIGGERS]->(event:TEvent)
            MERGE (f)-[:DESCRIBES]->(event)
            MERGE (f)-[:FRAME_DESCRIBES_EVENT]->(event)
            RETURN count(*) AS linked
        """
        rows = graph.run(query_via_arg).data()
        if rows:
            linked += rows[0].get("linked", 0)

        logger.info("link_frameArgument_to_event: %d DESCRIBES relationships merged", linked)

        # Path 3: Link Frame to EventMention (mention layer)
        # EventMention nodes are created in TemporalPhase and refer to canonical TEvent
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

        # Original query: Link Entity/NUMERIC to canonical TEvent
        query = """    
                                        MATCH (f:Frame)<-[:PARTICIPANT]-(fa:FrameArgument)-[:REFERS_TO]->(e)
                                        WHERE fa.type IN ['ARG0','ARG1','ARG2','ARG3','ARG4']
                                            AND (e:Entity OR e:NUMERIC OR e:VALUE)
                                        CALL {
                                            WITH f
                                            MATCH (f)-[:FRAME_DESCRIBES_EVENT]->(event:TEvent)
                                            RETURN event, 0 AS rel_priority
                                            UNION
                                            WITH f
                                            MATCH (f)-[:DESCRIBES]->(event:TEvent)
                                            RETURN event, 1 AS rel_priority
                                        }
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
                    merge (e)-[r:PARTICIPANT]->(event)
                    set r.type = fa.type, (case when fa.syntacticType in ['IN'] then r END).prep = fa.head
                    merge (e)-[nr:EVENT_PARTICIPANT]->(event)
                    set nr.type = fa.type, (case when fa.syntacticType in ['IN'] then nr END).prep = fa.head
                                        return count(*) AS linked
        
        """
        data= graph.run(query).data()
        
        # New query: Link Entity/NUMERIC to EventMention (mention layer)
        query_mention = """
                                        MATCH (f:Frame)-[:INSTANTIATES]->(em:EventMention)-[:REFERS_TO]->(event:TEvent)
                                        MATCH (f)<-[:PARTICIPANT]-(fa:FrameArgument)-[:REFERS_TO]->(e)
                                        WHERE fa.type IN ['ARG0','ARG1','ARG2','ARG3','ARG4']
                                            AND (e:Entity OR e:NUMERIC OR e:VALUE)
                    merge (e)-[r:PARTICIPANT]->(em)
                    set r.type = fa.type, (case when fa.syntacticType in ['IN'] then r END).prep = fa.head
                    merge (e)-[nr:EVENT_PARTICIPANT]->(em)
                    set nr.type = fa.type, (case when fa.syntacticType in ['IN'] then nr END).prep = fa.head
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
                                        CALL {
                                            WITH f
                                            MATCH (f)-[:FRAME_DESCRIBES_EVENT]->(event:TEvent)
                                            RETURN event, 0 AS rel_priority
                                            UNION
                                            WITH f
                                            MATCH (f)-[:DESCRIBES]->(event:TEvent)
                                            RETURN event, 1 AS rel_priority
                                        }
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
                        (CASE WHEN fa.syntacticType IN ['IN'] THEN r END).prep = fa.head
                    MERGE (fa)-[nr:EVENT_PARTICIPANT]->(event)
                    SET nr.type = fa.type,
                        (CASE WHEN fa.syntacticType IN ['IN'] THEN nr END).prep = fa.head
                    RETURN count(*) AS linked
        
        """
        data= graph.run(query).data()
        
        return ""
    



 # 2nd step where we set the labels for the non-core fa arguments are assigned

    def add_label_to_non_core_fa(self):
        logger.debug("add_label_to_non_core_fa")
        graph = self.graph

        query = """    
                   
                    MATCH (fa:FrameArgument)
                    WHERE fa.argumentType is not NULL
                    CALL apoc.create.addLabels(id(fa), [fa.argumentType]) YIELD node
                    RETURN node     
        
        """
        data= graph.run(query).data()
        
        return ""


    def derive_clinks_from_causal_arguments(self):
        logger.debug("derive_clinks_from_causal_arguments")
        graph = self.graph

        query = """
                    MATCH (f:Frame)<-[:PARTICIPANT]-(fa:FrameArgument {type: 'ARGM-CAU'})
                    OPTIONAL MATCH (f)-[:FRAME_DESCRIBES_EVENT]->(main_event_c:TEvent)
                    OPTIONAL MATCH (f)-[:DESCRIBES]->(main_event_l:TEvent)
                    WITH fa, coalesce(main_event_c, main_event_l) AS main_event
                    WHERE main_event IS NOT NULL
                    MATCH (fa)<-[:PARTICIPATES_IN]-(t:TagOccurrence)-[:TRIGGERS]->(sub_event:TEvent)
                    WHERE main_event <> sub_event
                    MERGE (main_event)-[cl:CLINK]->(sub_event)
                    SET cl.source = 'srl_argm_cau'
                    RETURN count(DISTINCT sub_event) AS linked
        """
        data = graph.run(query).data()
        if data:
            return data[0].get("linked", 0)
        return 0


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
                                            MATCH (fa)<-[:PARTICIPATES_IN]-(t:TagOccurrence)-[:TRIGGERS]->(sub_event:TEvent)
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
                                        END
                    RETURN count(DISTINCT sl) AS linked
        """
        data = graph.run(query).data()
        if data:
            return data[0].get("linked", 0)
        return 0


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

        # MEANTIME noun event mentions are typically underspecified for tense/aspect;
        # drop explicit NONE for noun mentions to avoid over-specification mismatches.
        query_noun_normalization = """
        MATCH (em:EventMention)
        WHERE em.pos IN ['NOUN', 'NN', 'NNS', 'NNP', 'NNPS']
        SET em.tense = CASE WHEN em.tense = 'NONE' THEN NULL ELSE em.tense END,
            em.aspect = CASE WHEN em.aspect = 'NONE' THEN NULL ELSE em.aspect END
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

        # Authority-aware sync for canonical event attributes.
        self._resolve_tevent_field_conflicts("certainty", incoming_source="event_enrichment", incoming_confidence=0.70)
        self._resolve_tevent_field_conflicts("aspect", incoming_source="event_enrichment", incoming_confidence=0.65)
        self._resolve_tevent_field_conflicts("polarity", incoming_source="event_enrichment", incoming_confidence=0.65)
        self._resolve_tevent_field_conflicts("time", incoming_source="event_enrichment", incoming_confidence=0.70)

        # Mark low-confidence event mentions using conservative linguistic evidence.
        # We only down-rank non-verbal mentions that have no supporting frame,
        # participant, or temporal-link evidence.
        query_low_confidence = """
        MATCH (em:EventMention)-[:REFERS_TO]->(te:TEvent)
        OPTIONAL MATCH (f:Frame)-[:INSTANTIATES]->(em)
           WITH em, te, count(DISTINCT f) AS frame_support
           OPTIONAL MATCH (ent:Entity)-[:EVENT_PARTICIPANT|PARTICIPANT]->(te)
           WITH em, te, frame_support, count(DISTINCT ent) AS participant_support
           OPTIONAL MATCH (te)-[:TLINK]-(tl_target)
           WHERE tl_target:TEvent OR tl_target:TIMEX
           WITH em, frame_support, participant_support, count(DISTINCT tl_target) AS tlink_support
        SET em.low_confidence = CASE
            WHEN em.pos IN ['NOUN', 'NN', 'NNS', 'NNP', 'NNPS', 'OTHER', 'JJ']
                 AND frame_support = 0
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
        total = certainty_count + time_count + special_count + aspect_count + polarity_count
        logger.info(
            "enrich_event_mention_properties: enriched %d event mentions "
            "(certainty=%d, time=%d, special_cases=%d, aspect=%d, polarity=%d)",
            total, certainty_count, time_count, special_count, aspect_count, polarity_count
        )
        
        return total



if __name__ == '__main__':
    import time as _time
    tp = EventEnrichmentPhase(sys.argv[1:])

    _phase_start = _time.time()
    tp.link_frameArgument_to_event()
    tp.add_core_participants_to_event()
    tp.add_non_core_participants_to_event()
    tp.add_label_to_non_core_fa()
    tp.derive_clinks_from_causal_arguments()
    tp.derive_slinks_from_reported_speech()
    tp.enrich_event_mention_properties()
    _phase_duration = _time.time() - _phase_start

    # Record a PhaseRun marker in the graph for restart visibility (Item 7)
    try:
        from textgraphx.phase_assertions import record_phase_run
        record_phase_run(
            tp.graph,
            phase_name="event_enrichment",
            duration_seconds=_phase_duration,
            metadata={"passes": "link,core_participants,non_core_participants,label_non_core,derive_clinks,derive_slinks,enrich_mentions"},
        )
    except Exception:
        logger.exception("Failed to write EventEnrichmentRun marker (non-fatal)")










