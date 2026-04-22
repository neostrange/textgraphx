"""RefinementPhase

This module implements the refinement stage of the text→graph pipeline.
It contains a collection of business-rule Cypher updates that enrich and
canonicalize nodes created by earlier phases (tokenization, SRL, NER,
coreference). The operations are intentionally small, idempotent Cypher
passes that can be executed individually during debugging or orchestrated in
sequence as part of a batch refinement step.

Typical usage (from code):
    rp = RefinementPhase()
    rp.get_and_assign_head_info_to_entity_multitoken()

You can also run the module as a script to execute a common sequence of
refinement passes; when executed as `python RefinementPhase.py` the module
adds the repository root to sys.path so the package imports resolve.
"""

import os
import sys
# allow running the module as a script (so `python RefinementPhase.py` works)
# When the module is executed directly the package name is not set and
# imports like `from textgraphx.TextProcessor import ...` will fail. Add
# the repository root to sys.path so package-style imports resolve when
# running the file as a script.
if __package__ is None and __name__ == '__main__':
    repo_root = os.path.dirname(os.path.dirname(__file__))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

#import neuralcoref
#import coreferee
from textgraphx.util.SemanticRoleLabeler import SemanticRoleLabel
from textgraphx.util.EntityFishingLinker import EntityFishing
from textgraphx.util.RestCaller import callAllenNlpApi
from textgraphx.util.GraphDbBase import GraphDBBase
import xml.etree.ElementTree as ET
# py2neo removed: use bolt-driver wrapper via neo4j_client
import logging
import warnings

from textgraphx.neo4j_client import make_graph_from_config
from textgraphx.config import get_config
from textgraphx.utils.id_utils import make_entity_mention_uid

logger = logging.getLogger(__name__)




class RefinementPhase():
    """Graph refinement stage for the text→graph pipeline.

    This class contains a series of targeted refinement operations that are
    executed as individual Cypher updates. Each method implements one
    refinement rule used in the project's business pipeline (for example:
    assigning syntactic heads to `NamedEntity`/`FrameArgument` nodes, linking
    frame arguments to entity instances, and applying heuristic canonical-
    ization steps).

    Business context and contract:
    - Input: a Neo4j graph populated by upstream pipeline steps (tokenization,
        SRL frame extraction, NER/NEL and coreference resolution). Common node
        types used here are `AnnotatedText`, `Sentence`, `TagOccurrence`,
        `Frame`, `FrameArgument`, `NamedEntity`, `Entity`, `CorefMention`, and
        `Antecedent`.
    - Output / side effects: nodes may get new properties (e.g., `head`,
        `headTokenIndex`, `syntacticType`, `complement`) and new relationships
        (e.g., `REFERS_TO`, `PARTICIPANT`, `MENTIONS`) will be created. Methods
        generally return nothing (empty string) and perform in-place updates.
    - Preconditions: many operations assume previous pipeline phases ran and
        populated properties such as `tok_index_doc`, `f.type` and
        `ne.headTokenIndex`. Methods are intentionally idempotent: if the
        preconditions are not satisfied they will be no-ops (zero-row updates).

    Implementation notes:
    - The class delegates Cypher execution to the bolt-driver compatibility
        wrapper available via `neo4j_client.make_graph_from_config()` so code can
        be executed against a running Neo4j instance configured in
        `textgraphx/config.ini` or via environment variables.
    - Methods are named after the refinement rule they implement. Keep in
        mind these are business rules that encode heuristics; they may need to
        be tuned to your data.
    """

    uri = ""
    username = ""
    password = ""
    graph = ""

    # Iteration 3: refinement rules are grouped into families to make the
    # pipeline easier to reason about and selectively execute.
    RULE_FAMILIES = {
        "head_assignment": [
            "get_and_assign_head_info_to_entity_multitoken",
            "get_and_assign_head_info_to_entity_singletoken",
            "get_and_assign_head_info_to_antecedent_multitoken",
            "get_and_assign_head_info_to_antecedent_singletoken",
            "get_and_assign_head_info_to_corefmention_multitoken",
            "get_and_assign_head_info_to_corefmention_singletoken",
            "get_and_assign_head_info_to_all_frameArgument_singletoken",
            "get_and_assign_head_info_to_all_frameArgument_multitoken",
            "get_and_assign_head_info_to_frameArgument_singletoken",
            "get_and_assign_head_info_to_frameArgument_multitoken",
            "get_and_assign_head_info_to_frameArgument_with_preposition",
            "get_and_assign_head_info_to_temporal_frameArgument_singletoken",
            "get_and_assign_head_info_to_temporal_frameArgument_multitoken_mark",
            "get_and_assign_head_info_to_temporal_frameArgument_multitoken_pcomp",
            "get_and_assign_head_info_to_temporal_frameArgument_multitoken_pobj",
            "get_and_assign_head_info_to_eventive_frameArgument_multitoken_pcomp",
        ],
        "linking": [
            "link_antecedent_to_namedEntity",
            "link_frameArgument_to_namedEntity_for_nam_nom",
            "link_frameArgument_to_namedEntity_for_pobj",
            "link_frameArgument_to_namedEntity_for_pobj_entity",
            "link_frameArgument_to_namedEntity_for_pro",
            "link_frameArgument_to_new_entity",
            "link_frameArgument_to_numeric_entities",
            "link_frameArgument_to_entity_via_named_entity",
        ],
        "nel_correction": [
            "detect_correct_NEL_result_for_missing_kb_id",
        ],
        "numeric_value": [
            "tag_value_entities",
            "materialize_canonical_value_nodes",
            "tag_numeric_entities",
            "detect_quantified_entities_from_frameArgument",
        ],
        "nominal_mentions": [
            "materialize_predicate_nominal_mentions",
            "materialize_appositive_mentions",
            "materialize_event_argument_mentions",
            "materialize_nominal_mentions_from_frame_arguments",
            "materialize_nominal_mentions_from_noun_chunks",
            "resolve_nominal_semantic_heads",
            "annotate_nominal_semantic_profiles",
            "assign_meantime_syntactic_types",
        ],
        "mention_cleanup": [
            "trim_trailing_punctuation_from_entity_mentions",
            "tag_discourse_relevant_entities",
        ],
        "meantime_boundary_alignment": [
            "trim_determiners_from_mentions",
            "trim_punctuation_from_mentions",
            "update_mention_span_boundaries",
        ],
        "morphological_projection": [
            "project_event_polarity",
            "project_event_tense_aspect",
        ],
        "syntactic_semantic_coercion": [
            "promote_nominal_events",
            "coerce_role_based_types",
        ],
        "entity_state": [
            "annotate_entity_state_signals",
            "annotate_entity_specificity_classes",
        ],
    }

    def get_rule_families(self):
        """Return the configured refinement rule families.

        Keys are family names and values are ordered method-name lists.
        """
        return self.RULE_FAMILIES

    def iter_rule_names(self):
        """Yield refinement rule method names in execution order."""
        for family, methods in self.RULE_FAMILIES.items():
            for method_name in methods:
                yield family, method_name

    def run_rule_family(self, family_name):
        """Execute one refinement rule family by name."""
        if family_name not in self.RULE_FAMILIES:
            raise ValueError(f"Unknown refinement rule family: {family_name}")
        for method_name in self.RULE_FAMILIES[family_name]:
            logger.info("Running refinement rule [%s]: %s", family_name, method_name)
            getattr(self, method_name)()

    def run_all_rule_families(self):
        """Execute all configured refinement rule families in order."""
        for family_name in self.RULE_FAMILIES:
            self.run_rule_family(family_name)

    def __init__(self, argv=None):
        # Create a bolt-driver backed compatibility graph object.
        # create graph and wrap it with a thin logger that records query text
        # and number of returned rows. This helps debugging when running the
        # refinement steps interactively or as a script.
        _raw_graph = make_graph_from_config()

        class LoggingGraphCompat:
            """Small wrapper around the compat graph to log each run() call.

            It delegates to the provided graph.run(...) but eagerly calls
            `.data()` so we can log the number of returned rows. The returned
            object implements the same `.data()` contract and returns the
            previously collected list so callers behave the same.
            """

            def __init__(self, graph, logger):
                self._graph = graph
                self._logger = logger

            def run(self, query, parameters=None):
                # Truncate long queries in logs for readability
                qshort = (query.strip().replace("\n", " ")[:200] + "...") if len(query) > 200 else query.strip()
                try:
                    inner = self._graph.run(query, parameters)
                    data = inner.data()
                    self._logger.info("Executed query: %s; rows=%d", qshort, len(data))
                except Exception:
                    self._logger.exception("Query failed: %s", qshort)
                    # Re-raise so callers that expect exceptions continue to get them
                    raise

                class _Result:
                    def __init__(self, data):
                        self._data = data

                    def data(self):
                        return self._data

                return _Result(data)

        # instantiate the wrapped graph and keep legacy attributes
        self.graph = LoggingGraphCompat(_raw_graph, logger)
        self.uri = None
        self.username = None
        self.password = None
    logger.info("RefinementPhase initialized; using graph wrapper for query logging")

    @staticmethod
    def _coerce_doc_id(doc_id):
        try:
            return int(doc_id)
        except (TypeError, ValueError):
            return 0

    def _merge_nominal_entity_mentions(self, rows, mention_source, source_key, confidence, provenance_rule_id):
        payload = []
        for row in rows:
            doc_id = self._coerce_doc_id(row.get("doc_id"))
            value = row.get("value", "")
            head_token_index = row.get("headTokenIndex")
            payload.append({
                "mention_uid": make_entity_mention_uid(
                    doc_id=doc_id,
                    value=value,
                    head_token_index=head_token_index,
                    source=mention_source,
                ),
                "mention_id": row["mention_id"],
                "doc_id": doc_id,
                "value": value,
                "head": row.get("head"),
                "headTokenIndex": head_token_index,
                "start_tok": row["start_tok"],
                "end_tok": row["end_tok"],
                "start_char": row.get("start_char"),
                "end_char": row.get("end_char"),
                "syntactic_type": row.get("syntactic_type", "NOM"),
                "mention_source": mention_source,
                "confidence": confidence,
                "provenance_rule_id": provenance_rule_id,
                "source_node_id": row[source_key],
                "entity_id": row["entity_id"],
            })

        if not payload:
            return 0

        _source_labels = {"fa": "frame_argument_nominal", "nc": "noun_chunk_nominal"}  # noqa: E501
        # Sets: em.mention_source = 'frame_argument_nominal' (fa) or em.mention_source = 'noun_chunk_nominal' (nc)
        _batch_cypher = f"""
                 UNWIND $rows AS row
                 MATCH (e:Entity {{id: row.entity_id}})
                 MERGE (em:EntityMention {{uid: row.mention_uid}})
                 SET em:NominalMention,
                    em.uid = row.mention_uid,
                    em.id = row.mention_id,
                    em.legacy_span_id = coalesce(em.legacy_span_id, row.mention_id),
                    em.doc_id = row.doc_id,
                    em.value = row.value,
                    em.head = row.head,
                    em.headTokenIndex = row.headTokenIndex,
                          em.syntacticType = row.syntactic_type,
                          em.syntactic_type = row.syntactic_type,
                    em.start_tok = row.start_tok,
                    em.end_tok = row.end_tok,
                    em.start_char = row.start_char,
                    em.end_char = row.end_char,
                    em.mention_source = row.mention_source,
                    em.confidence = coalesce(em.confidence, row.confidence),
                    em.provenance_rule_id = row.provenance_rule_id,
                    em.{source_key} = row.source_node_id
                 MERGE (em)-[:REFERS_TO]->(e)
                 WITH em, row
                 MATCH (d:AnnotatedText {{id: row.doc_id}})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(tok:TagOccurrence)
                 WHERE tok.tok_index_doc >= row.start_tok AND tok.tok_index_doc <= row.end_tok
                 MERGE (tok)-[:IN_MENTION]->(em)
                 MERGE (tok)-[:PARTICIPATES_IN]->(em)
                 RETURN count(DISTINCT em) AS mentions_materialized
        """
        data = self.graph.run(_batch_cypher, {"rows": payload}).data()
        return data[0].get("mentions_materialized", 0) if data else 0

    def trim_trailing_punctuation_from_entity_mentions(self):
        """Remove trailing punctuation tokens from NamedEntity mention spans.

        When spaCy tokenizes the normalized text, sentence-terminal punctuation
        (period, comma, quotes) is sometimes included in the PARTICIPATES_IN
        span of a NamedEntity. MEANTIME gold annotations never include trailing
        punctuation in entity spans. This rule detects cases where the
        highest-index token participating in a NamedEntity carries a
        punctuation POS tag and removes just that PARTICIPATES_IN edge,
        leaving at least one token in the span.

        Side effects:
        - Removes PARTICIPATES_IN relationships for trailing punct tokens.
        - Does NOT modify NamedEntity.text (that property is not used by the
          evaluator; span is recomputed from remaining token edges).
        - Idempotent: safe to run multiple times.
        """
        query = """
            MATCH (ne:NamedEntity)<-[:PARTICIPATES_IN]-(tok:TagOccurrence)
            WITH ne, max(tok.tok_index_doc) AS max_idx
            MATCH (ne)<-[r:PARTICIPATES_IN]-(pt:TagOccurrence {tok_index_doc: max_idx})
            WHERE pt.pos IN ['.', ',', ':', "''", '``', '"', '-LRB-', '-RRB-']
               OR pt.text IN ['.', ',', ':', '"', '\u201c', '\u201d', "'", ')', '(']
            WITH ne, r, max_idx
            MATCH (ne)<-[:PARTICIPATES_IN]-(other:TagOccurrence)
            WHERE other.tok_index_doc < max_idx
            WITH ne, r, count(other) AS remaining
            WHERE remaining >= 1
            DELETE r
            RETURN count(ne) AS entities_trimmed
        """
        data = self.graph.run(query).data()
        trimmed = data[0].get("entities_trimmed", 0) if data else 0
        logger.info("trim_trailing_punctuation_from_entity_mentions: trimmed %d entity spans", trimmed)
        return ""

    def tag_discourse_relevant_entities(self):
        """Label NamedEntity nodes that participate in a temporal event.

        MEANTIME-style annotation focuses on proper named entities (ORG, GPE,
        PERSON, FAC, LOC) and their nominal/pronominal coreference mentions.
        It does NOT annotate numeric quantities (CARDINAL, MONEY, PERCENT,
        ORDINAL, QUANTITY), temporal expressions (DATE, TIME) — those are
        annotated as TIMEX3/VALUE — or adjectival nationality forms (NORP,
        LANGUAGE).

        This rule stamps :DiscourseEntity on entities whose spaCy NE type
        maps to MEANTIME's ENTITY_MENTION layer, enabling the evaluator's
        --discourse-only mode to compare against gold at the correct semantic
        scope without altering the raw extraction.

        Side effects:
        - Adds the :DiscourseEntity label to qualifying NamedEntity nodes.
        - Idempotent: safe to run multiple times.
        """
        query = """
            MATCH (ne:NamedEntity)-[:PARTICIPATES_IN|IN_RELATION|HAS_STATE|IS_A*1..2]-(ev)
            WHERE ne.type IN ['ORG', 'GPE', 'PERSON', 'FAC', 'LOC',
                              'PRODUCT', 'WORK_OF_ART', 'EVENT', 'LAW', 'PER']
            SET ne:DiscourseEntity
            RETURN count(DISTINCT ne) AS tagged
        """
        data = self.graph.run(query).data()
        tagged_ne = data[0].get("tagged", 0) if data else 0

        nominal_query = """
            MATCH (em)
            WHERE em:NominalMention OR em:CorefMention OR em:EntityMention
            OPTIONAL MATCH (em)-[:REFERS_TO]->(ent:Entity)
            WITH em, coalesce(ent, em) AS anchor
            MATCH (anchor)-[:EVENT_PARTICIPANT|PARTICIPANT|PARTICIPATES_IN|IN_RELATION|HAS_STATE|IS_A*1..2]-(ev)
            SET em:DiscourseEntity
            RETURN count(DISTINCT em) AS tagged
        """
        data_nom = self.graph.run(nominal_query).data()
        tagged_nom = data_nom[0].get("tagged", 0) if data_nom else 0


        fa_query = """
            MATCH (fa:FrameArgument)
            MATCH (fa)-[:EVENT_PARTICIPANT|PARTICIPANT|PARTICIPATES_IN|IN_RELATION|HAS_STATE|IS_A*1..2]-(ev)
            SET fa:DiscourseEntity
            RETURN count(DISTINCT fa) AS tagged
        """
        data_fa = self.graph.run(fa_query).data()
        tagged_fa = data_fa[0].get("tagged", 0) if data_fa else 0

        logger.info(
            "tag_discourse_relevant_entities: tagged %d NamedEntity + %d nominal mentions + %d FrameArgument as :DiscourseEntity",
            tagged_ne,
            tagged_nom,
            tagged_fa,
        )
        return ""

    def annotate_entity_state_signals(self):
        """Annotate situational state hints on entity mentions and canonical entities.

        This pass captures lightweight state semantics from copular and near-copular
        constructions (for example: "company is profitable", "team became ready").
        The intent is to improve situational awareness queries without introducing
        destructive schema changes.
        """
        logger.debug("annotate_entity_state_signals")
        graph = self.graph

        query = """
            CALL {
                MATCH (mention:EntityMention)<-[:IN_MENTION]-(subj_tok:TagOccurrence)-[:IS_DEPENDENT {type: 'nsubj'}]->(pred_tok:TagOccurrence)
                WHERE toLower(coalesce(pred_tok.lemma, pred_tok.text, '')) IN ['be', 'become', 'remain', 'seem', 'appear', 'stay', 'feel']
                OPTIONAL MATCH (state_tok:TagOccurrence)-[dep:IS_DEPENDENT]->(pred_tok)
                WHERE dep.type IN ['acomp', 'attr', 'oprd', 'xcomp']
                  AND (
                      coalesce(state_tok.upos, '') IN ['ADJ', 'NOUN', 'VERB'] OR
                      coalesce(state_tok.pos, '') IN ['JJ', 'JJR', 'JJS', 'NN', 'NNS', 'NNP', 'NNPS', 'VBN']
                  )
                WITH mention, pred_tok, head(collect(state_tok)) AS state_tok
                WHERE state_tok IS NOT NULL
                RETURN mention, pred_tok, state_tok
                UNION
                MATCH (mention:NamedEntity)<-[:IN_MENTION]-(subj_tok:TagOccurrence)-[:IS_DEPENDENT {type: 'nsubj'}]->(pred_tok:TagOccurrence)
                WHERE toLower(coalesce(pred_tok.lemma, pred_tok.text, '')) IN ['be', 'become', 'remain', 'seem', 'appear', 'stay', 'feel']
                OPTIONAL MATCH (state_tok:TagOccurrence)-[dep:IS_DEPENDENT]->(pred_tok)
                WHERE dep.type IN ['acomp', 'attr', 'oprd', 'xcomp']
                  AND (
                      coalesce(state_tok.upos, '') IN ['ADJ', 'NOUN', 'VERB'] OR
                      coalesce(state_tok.pos, '') IN ['JJ', 'JJR', 'JJS', 'NN', 'NNS', 'NNP', 'NNPS', 'VBN']
                  )
                WITH mention, pred_tok, head(collect(state_tok)) AS state_tok
                WHERE state_tok IS NOT NULL
                RETURN mention, pred_tok, state_tok
            }
            OPTIONAL MATCH (mention)-[:REFERS_TO]->(e:Entity)
            WITH mention, e, pred_tok, state_tok,
                 toLower(coalesce(state_tok.lemma, state_tok.text, '')) AS state_lemma,
                 toLower(coalesce(pred_tok.lemma, pred_tok.text, '')) AS pred_lemma
            WHERE state_lemma <> ''
            SET mention.entityState = state_lemma,
                mention.entityStateText = coalesce(state_tok.text, state_tok.lemma, state_lemma),
                mention.entityStateType = CASE
                    WHEN coalesce(state_tok.upos, '') = 'ADJ' OR coalesce(state_tok.pos, '') IN ['JJ', 'JJR', 'JJS'] THEN 'ATTRIBUTE'
                    WHEN coalesce(state_tok.pos, '') = 'VBN' THEN 'CONDITION'
                    WHEN coalesce(state_tok.upos, '') = 'NOUN' OR coalesce(state_tok.pos, '') IN ['NN', 'NNS', 'NNP', 'NNPS'] THEN 'ROLE_OR_CLASS'
                    ELSE 'STATE'
                END,
                mention.entityStatePredicate = pred_lemma,
                mention.entityStateHeadTokenIndex = coalesce(state_tok.tok_index_doc, mention.headTokenIndex),
                mention.entityStateSource = 'copular_predicate',
                mention.entityStateConfidence = 0.70
            SET e.entityState = CASE
                    WHEN e IS NULL THEN NULL
                    WHEN coalesce(e.entityStateHeadTokenIndex, -1) <= coalesce(state_tok.tok_index_doc, -1) THEN state_lemma
                    ELSE e.entityState
                END,
                e.entityStateType = CASE
                    WHEN e IS NULL THEN NULL
                    WHEN coalesce(e.entityStateHeadTokenIndex, -1) <= coalesce(state_tok.tok_index_doc, -1)
                    THEN CASE
                        WHEN coalesce(state_tok.upos, '') = 'ADJ' OR coalesce(state_tok.pos, '') IN ['JJ', 'JJR', 'JJS'] THEN 'ATTRIBUTE'
                        WHEN coalesce(state_tok.pos, '') = 'VBN' THEN 'CONDITION'
                        WHEN coalesce(state_tok.upos, '') = 'NOUN' OR coalesce(state_tok.pos, '') IN ['NN', 'NNS', 'NNP', 'NNPS'] THEN 'ROLE_OR_CLASS'
                        ELSE 'STATE'
                    END
                    ELSE e.entityStateType
                END,
                e.entityStatePredicate = CASE
                    WHEN e IS NULL THEN NULL
                    WHEN coalesce(e.entityStateHeadTokenIndex, -1) <= coalesce(state_tok.tok_index_doc, -1) THEN pred_lemma
                    ELSE e.entityStatePredicate
                END,
                e.entityStateHeadTokenIndex = CASE
                    WHEN e IS NULL THEN NULL
                    WHEN coalesce(e.entityStateHeadTokenIndex, -1) <= coalesce(state_tok.tok_index_doc, -1)
                    THEN coalesce(state_tok.tok_index_doc, e.entityStateHeadTokenIndex)
                    ELSE e.entityStateHeadTokenIndex
                END,
                e.entityStateSource = CASE
                    WHEN e IS NULL THEN NULL
                    WHEN coalesce(e.entityStateHeadTokenIndex, -1) <= coalesce(state_tok.tok_index_doc, -1) THEN 'copular_predicate'
                    ELSE e.entityStateSource
                END,
                e.entityStateConfidence = CASE
                    WHEN e IS NULL THEN NULL
                    WHEN coalesce(e.entityStateHeadTokenIndex, -1) <= coalesce(state_tok.tok_index_doc, -1) THEN 0.70
                    ELSE coalesce(e.entityStateConfidence, 0.70)
                END
            RETURN count(DISTINCT mention) AS mentions_state_annotated
        """
        data = graph.run(query).data()
        annotated = data[0].get("mentions_state_annotated", 0) if data else 0
        logger.info("annotate_entity_state_signals: annotated %d mention-level state hints", annotated)
        return ""

    def annotate_entity_specificity_classes(self):
        """Annotate entity specificity class (ent_class) on mentions and entities.

        Classes follow a lightweight MEANTIME-compatible convention:
        - SPC: specific mention (default for named entities and definite mentions)
        - GEN: generic mention (bare plurals / generic determiners)
        - USP: underspecified or unknown specificity
        - NEG: negated mention context
        """
        logger.debug("annotate_entity_specificity_classes")
        graph = self.graph

        query_mentions = """
            CALL {
                MATCH (m:EntityMention)
                RETURN m
                UNION
                MATCH (m:NamedEntity)
                RETURN m
            }
            OPTIONAL MATCH (tok:TagOccurrence)-[:IN_MENTION]->(m)
            OPTIONAL MATCH (det_tok:TagOccurrence)-[:IS_DEPENDENT {type: 'det'}]->(tok)
            OPTIONAL MATCH (neg_tok:TagOccurrence)-[:IS_DEPENDENT {type: 'neg'}]->(tok)
            WITH m,
                 [d IN collect(DISTINCT toLower(coalesce(det_tok.lemma, det_tok.text, ''))) WHERE d <> ''] AS det_lemmas,
                 count(DISTINCT neg_tok) > 0 AS has_neg,
                 count(DISTINCT tok) AS mention_width,
                 any(p IN collect(DISTINCT coalesce(tok.pos, '')) WHERE p IN ['NNP', 'NNPS']) AS has_proper_pos
            WITH m, det_lemmas, has_neg, mention_width, has_proper_pos,
                 CASE
                     WHEN has_neg THEN 'NEG'
                     WHEN has_proper_pos THEN 'SPC'
                     WHEN any(d IN det_lemmas WHERE d IN ['a', 'an', 'some', 'any']) THEN 'USP'
                     WHEN any(d IN det_lemmas WHERE d IN ['the', 'this', 'that', 'these', 'those']) THEN 'SPC'
                     WHEN mention_width > 1 THEN 'SPC'
                     WHEN any(d IN det_lemmas WHERE d IN ['all', 'every', 'each']) THEN 'GEN'
                     ELSE 'GEN'
                 END AS ent_class
            SET m.ent_class = ent_class,
                m.entClass = ent_class,
                m.entClassSource = 'refinement_specificity_heuristic'
            RETURN count(DISTINCT m) AS mention_count
        """
        mention_rows = graph.run(query_mentions).data()
        mention_count = mention_rows[0].get("mention_count", 0) if mention_rows else 0

        query_entities = """
            MATCH (m)-[:REFERS_TO]->(e:Entity)
            WHERE (m:EntityMention OR m:NamedEntity)
              AND coalesce(m.ent_class, m.entClass, '') <> ''
            WITH e,
                 collect(coalesce(m.ent_class, m.entClass)) AS classes
            WITH e,
                 CASE
                     WHEN any(c IN classes WHERE c = 'NEG') THEN 'NEG'
                     WHEN any(c IN classes WHERE c = 'SPC') THEN 'SPC'
                     WHEN any(c IN classes WHERE c = 'USP') THEN 'USP'
                     WHEN any(c IN classes WHERE c = 'GEN') THEN 'GEN'
                     ELSE 'USP'
                 END AS ent_class
            SET e.ent_class = ent_class,
                e.entClass = ent_class,
                e.entClassSource = 'refinement_specificity_heuristic'
            RETURN count(DISTINCT e) AS entity_count
        """
        entity_rows = graph.run(query_entities).data()
        entity_count = entity_rows[0].get("entity_count", 0) if entity_rows else 0

        logger.info(
            "annotate_entity_specificity_classes: annotated %d mentions and %d entities",
            mention_count,
            entity_count,
        )
        return ""

    def diagnostic_report(self):
        """Run small diagnostics that count important node/relationship types

        This helps determine whether the refinement queries return zero rows
        because the required data isn't present or because of other logic
        issues.
        """
        checks = {
            'TagOccurrence': "MATCH (n:TagOccurrence) RETURN count(n) AS cnt",
            'NamedEntity': "MATCH (n:NamedEntity) RETURN count(n) AS cnt",
            'FrameArgument': "MATCH (n:FrameArgument) RETURN count(n) AS cnt",
            'Frame': "MATCH (n:Frame) RETURN count(n) AS cnt",
            'Antecedent': "MATCH (n:Antecedent) RETURN count(n) AS cnt",
            'CorefMention': "MATCH (n:CorefMention) RETURN count(n) AS cnt",
            'IS_DEPENDENT rels': "MATCH ()-[r:IS_DEPENDENT]-() RETURN count(r) AS cnt",
            'PARTICIPATES_IN rels': "MATCH ()-[r:PARTICIPATES_IN]-() RETURN count(r) AS cnt",
            'FrameArgument with headTokenIndex': "MATCH (f:FrameArgument) WHERE exists(f.headTokenIndex) RETURN count(f) AS cnt",
        }

        report = {}
        for name, q in checks.items():
            try:
                rows = self.graph.run(q).data()
                # rows is a list of mappings with key 'cnt'
                cnt = rows[0].get('cnt') if rows and isinstance(rows[0], dict) else None
                report[name] = cnt
            except Exception as e:
                report[name] = f"ERROR: {e}"

        # print a concise report
        logger.info("RefinementPhase diagnostic report:")
        for k, v in report.items():
            logger.info("  %s: %s", k, v)
        return report

    def tuning_notes(self) -> dict:
        """Return human-friendly tuning notes for the refinement phase.

        This helper is intentionally in-code so maintainers and operators can
        quickly see which rules are brittle, what upstream annotations they
        depend on, and a minimal set of diagnostics to run when a rule
        appears to match zero rows.

        The method returns a small mapping where keys are short rule names and
        values contain a brief rationale and suggested Cypher checks.
        """
        notes = {
            'head_finding': {
                'rationale': (
                    'Many head-finding passes assume dependency edges of type ' 
                    "'IS_DEPENDENT' and specific POS tags (NN, NNP, PRP etc.)."
                ),
                'upstream': ['TagOccurrence.pos', 'IS_DEPENDENT:type', 'tok_index_doc'],
                'diagnostics': [
                    "MATCH (n:TagOccurrence) RETURN count(n) AS cnt",
                    "MATCH ()-[r:IS_DEPENDENT]-() RETURN count(r) AS cnt",
                    "MATCH (f:FrameArgument) WHERE NOT exists(f.headTokenIndex) RETURN count(f) AS cnt",
                ],
            },
            'prepositional_complements': {
                'rationale': (
                    'Rules that extract complements from prepositional heads rely on '
                    'pobj/pcomp dependency labels. Parser label mismatches cause no matches.'
                ),
                'upstream': ['IS_DEPENDENT.type', 'TagOccurrence.pos', 'FrameArgument.type'],
                'diagnostics': [
                    "MATCH (f:FrameArgument) WHERE f.type = 'ARGM-TMP' RETURN count(f) AS cnt",
                    "MATCH ()-[r:IS_DEPENDENT {type: 'pobj'}]-() RETURN count(r) AS cnt",
                ],
            },
            'coref_propagation': {
                'rationale': (
                    'Copying KB metadata from antecedents assumes coref chains and ' 
                    'that antecedent nodes are correctly disambiguated. Verify coref coverage.'
                ),
                'upstream': ['CorefMention', 'Antecedent', 'NamedEntity.kb_id'],
                'diagnostics': [
                    "MATCH (a:Antecedent) RETURN count(a) AS cnt",
                    "MATCH (n:NamedEntity) WHERE n.kb_id IS NOT NULL RETURN count(n) AS cnt",
                ],
            }
        }

        return notes


# PHASE 1
# Identification of HEADWORD and assigning related metadata about headword
# Subjects include, NamedEntity, Antecedent, CorefMention, FrameArgument

    # NamedEntity Multitoken
    def get_and_assign_head_info_to_entity_multitoken(self):
        """Assign grammatical head token for multi-token NamedEntity spans.

        Preconditions:
        - `TagOccurrence` nodes exist and are connected with `PARTICIPATES_IN`
          to `NamedEntity` nodes.
        - Dependency edges `IS_DEPENDENT` exist between TagOccurrences.

        Side effects:
        - Sets `f.head`, `f.headTokenIndex` and `f.syntacticType` on the
          `NamedEntity` node when a head candidate is found.

        Business rationale:
        - Having a canonical head token for multi-token NamedEntity spans
          simplifies matching between different annotations and downstream
          entity linking steps. For instance, 'European Central Bank' should
          provide a single token ('Bank') as the head for consolidation
          and matching.
        """
        logger.debug("get_and_assign_head_info_to_entity_multitoken")
        graph = self.graph
        query = """
                        match p= (a:TagOccurrence)-[:IN_MENTION]->(f:NamedEntity), q= (a)-[:IS_DEPENDENT]->()--(f)
                        where not exists ((a)<-[:IS_DEPENDENT]-()--(f)) and f.headTokenIndex is null
                        WITH f, a, p
                        set f.head = a.text, f.headTokenIndex = a.tok_index_doc,
                            f.syntacticType = CASE
                                WHEN a.pos IN ['NNS', 'NN'] THEN 'NOMINAL'
                                WHEN a.pos IN ['NNP', 'NNPS'] THEN 'NAM'
                                ELSE coalesce(f.syntacticType, 'NAM') END
                        return p

        """
        data = graph.run(query).data()

        return ""


    # NamedEntity Singletoken
    def get_and_assign_head_info_to_entity_singletoken(self):
        """Assign head information for single-token NamedEntity nodes.

        This method is a no-op for multi-token entities and focuses on cases
        where the NamedEntity is a single token; it sets `head`, `headTokenIndex`
        and `syntacticType` to allow consistent downstream comparisons.
        """
        logger.debug("get_and_assign_head_info_to_entity_singletoken")
        graph = self.graph
        query = """
                        match p= (a:TagOccurrence)-[:IN_MENTION]->(c:NamedEntity)
                        where not exists ((a)<-[:IS_DEPENDENT]-()--(c)) and not exists ((a)-[:IS_DEPENDENT]->()--(c)) and c.headTokenIndex is null
                        WITH c, a, p
                        set c.head = a.text, c.headTokenIndex = a.tok_index_doc,
                            c.syntacticType = CASE
                                WHEN a.pos IN ['NNS', 'NN'] THEN 'NOMINAL'
                                WHEN a.pos IN ['NNP', 'NNPS'] THEN 'NAM'
                                WHEN a.pos IN ['PRP', 'PRP$'] THEN 'PRO'
                                ELSE coalesce(c.syntacticType, 'NAM') END
                        return p

        """
        data = graph.run(query).data()

        return ""


    # Antecedent Multitoken
    def get_and_assign_head_info_to_antecedent_multitoken(self):
        """Assign head for multi-token Antecedent nodes created by coref.

        Antecedent nodes are generated by coreference processing and often span
        multiple tokens. This step assigns the most likely head token by
        consulting dependency edges and setting `head`/`headTokenIndex` on the
        Antecedent node to support linking to NamedEntity instances.
        """
        logger.debug("get_and_assign_head_info_to_antecedent_multitoken")
        graph = self.graph
        # TODO: the head for the NAM should include the whole extent of the name. see newsreader annotation guidelines
        # for more information.
        query = """
                        match p= (a:TagOccurrence)-[:IN_MENTION]->(f:Antecedent), q= (a)-[:IS_DEPENDENT]->()--(f)
                        where not exists ((a)<-[:IS_DEPENDENT]-()--(f))
                        WITH f, a, p
                        set f.head = a.text, f.headTokenIndex = a.tok_index_doc, 
                            f.syntacticType = CASE
                                WHEN a.pos IN ['NNS', 'NN'] THEN 'NOMINAL'
                                WHEN a.pos IN ['NNP', 'NNPS'] THEN 'NAM'
                                ELSE coalesce(f.syntacticType, 'NAM') END
                        return p     
        
        """
        data= graph.run(query).data()
        
        return ""


    #Antecedent Singletoken
    def get_and_assign_head_info_to_antecedent_singletoken(self):
                """Assign head info for single-token Antecedent nodes.

                Preconditions:
                - Antecedent nodes exist and are linked to their token `TagOccurrence`
                    via `PARTICIPATES_IN`.
                - Dependency edges `IS_DEPENDENT` may or may not be present; this
                    method targets Antecedent instances where the head is a single
                    token (no dependents within the span).

                Side effects:
                - Sets `head`, `headTokenIndex` and `syntacticType` on the
                    `Antecedent` node to normalise representation for downstream
                    linking to NamedEntity or Entity instances.

                Business rationale:
                - Antecedents are used as authoritative targets for coreference
                    resolution; ensuring they have a canonical head token improves
                    entity linking and corrective NEL heuristics.
                """
                logger.debug("get_and_assign_head_info_to_antecedent_singletoken")
                graph = self.graph

                # query to find the head of an Antecedent when it is a single token
                query = """    
                                                match p= (a:TagOccurrence)-[:IN_MENTION]->(c:Antecedent)
                                                where not exists ((a)<-[:IS_DEPENDENT]-()--(c)) and not exists ((a)-[:IS_DEPENDENT]->()--(c))
                                                WITH c, a, p
                                                set c.head = a.text, c.headTokenIndex = a.tok_index_doc, 
                                                    c.syntacticType = CASE
                                                        WHEN a.pos IN ['NNS', 'NN'] THEN 'NOMINAL'
                                                        WHEN a.pos IN ['NNP', 'NNPS'] THEN 'NAM'
                                                        WHEN a.pos IN ['PRP', 'PRP$'] THEN 'PRO'
                                                        ELSE coalesce(c.syntacticType, 'NAM') END
                                                return p     
        
                """
                data= graph.run(query).data()
        
                return ""
        
    #CorefMention Multitoken    
    def get_and_assign_head_info_to_corefmention_multitoken(self):
        """Assign head info to multi-token CorefMention nodes.

        CorefMention nodes may be multi-token mentions produced by coreference
        resolution. This step selects a representative head token and records
        it so later passes can match mentions against NamedEntity nodes or
        resolve pronouns.
        """
        logger.debug("get_and_assign_head_info_to_corefmention_multitoken")
        graph = self.graph
        # TODO: the head for the NAM should include the whole extent of the name. see newsreader annotation guidelines 
        # for more information. 
        query = """    
                        match p= (a:TagOccurrence)-[:IN_MENTION]->(f:CorefMention), q= (a)-[:IS_DEPENDENT]->()--(f)
                        where not exists ((a)<-[:IS_DEPENDENT]-()--(f))
                        WITH f, a, p
                        set f.head = a.text, f.headTokenIndex = a.tok_index_doc,
                            f.syntacticType = CASE
                                WHEN a.pos IN ['PRP', 'PRP$', 'WP', 'WP$'] THEN 'PRO'
                                WHEN a.pos IN ['NNP', 'NNPS'] THEN 'NAM'
                                WHEN a.pos IN ['NNS', 'NN'] THEN 'NOMINAL'
                                ELSE coalesce(f.syntacticType, 'NAM') END,
                            f.syntactic_type = CASE
                                WHEN a.pos IN ['PRP', 'PRP$', 'WP', 'WP$'] THEN 'PRO'
                                WHEN a.pos IN ['NNP', 'NNPS'] THEN 'NAM'
                                WHEN a.pos IN ['NNS', 'NN'] THEN 'NOM'
                                ELSE coalesce(f.syntactic_type, 'NAM') END
                        return p     
        
        """
        data= graph.run(query).data()
        
        return ""


    #CorefMention Singletoken
    def get_and_assign_head_info_to_corefmention_singletoken(self):
        """Assign head metadata for single-token CorefMention nodes.

        This complements the multi-token corefmention pass by handling cases
        where the mention maps to a single token (no internal dependents). It
        sets `head`, `headTokenIndex` and a coarse `syntacticType` so later
        refinement rules can match coreference mentions against NamedEntity
        instances and propagate KB identifiers.
        """
        logger.debug("get_and_assign_head_info_to_corefmention_singletoken")
        graph = self.graph

        # query to find the head of a NamedEntity. (case is for entitities composed of  single token )
        query = """    
                        match p= (a:TagOccurrence)-[:IN_MENTION]->(c:CorefMention)
                        where not exists ((a)<-[:IS_DEPENDENT]-()--(c)) and not exists ((a)-[:IS_DEPENDENT]->()--(c))
                        WITH c, a, p
                        set c.head = a.text, c.headTokenIndex = a.tok_index_doc,
                            c.syntacticType = CASE
                                WHEN a.pos IN ['PRP', 'PRP$', 'WP', 'WP$'] THEN 'PRO'
                                WHEN a.pos IN ['NNP', 'NNPS'] THEN 'NAM'
                                WHEN a.pos IN ['NNS', 'NN'] THEN 'NOMINAL'
                                ELSE coalesce(c.syntacticType, 'NAM') END,
                            c.syntactic_type = CASE
                                WHEN a.pos IN ['PRP', 'PRP$', 'WP', 'WP$'] THEN 'PRO'
                                WHEN a.pos IN ['NNP', 'NNPS'] THEN 'NAM'
                                WHEN a.pos IN ['NNS', 'NN'] THEN 'NOM'
                                ELSE coalesce(c.syntactic_type, 'NAM') END
                        return p     
        
        """
        data= graph.run(query).data()
        
        return ""

    #To find head info for the FrameArgument i.e., with single token as head
    # here head is noun or pronoun
    def get_and_assign_head_info_to_frameArgument_singletoken(self):
        """Assign head tokens for single-token FrameArgument nodes.

        FrameArgument nodes represent argument spans from SRL. For single-token
        arguments this method records the head token and a syntactic type so
        later modules (entity linking, event enrichment) can match arguments
        to entities or event participants.
        """
        logger.debug("get_and_assign_head_info_to_frameArgument_singletoken")
        graph = self.graph

        query = """    
                        match p= (a:TagOccurrence where a.pos in ['NNS', 'NN', 'NNP', 'NNPS','PRP', 'PRP$'])--(c:FrameArgument)
                        where not exists ((a)<-[:IS_DEPENDENT]-()--(c)) and not exists ((a)-[:IS_DEPENDENT]->()--(c))
                        WITH c, a, p
                        set c.head = a.text, c.headTokenIndex = a.tok_index_doc,
                            c.syntacticType = CASE
                                WHEN a.pos IN ['NNS', 'NN'] THEN 'NOMINAL'
                                WHEN a.pos IN ['NNP', 'NNPS'] THEN 'NAM'
                                WHEN a.pos IN ['PRP', 'PRP$'] THEN 'PRO'
                                ELSE coalesce(c.syntacticType, 'NAM') END
                        return p    
        
        """
        data= graph.run(query).data()
        
        return ""


    #To find head info for the FrameArgument i.e., with single token as head
    # here head is noun or pronoun
    def get_and_assign_head_info_to_all_frameArgument_singletoken(self):
                """Assign head tokens for all single-token FrameArguments.

                This is a broad pass that assigns `head`, `headTokenIndex`, and
                `headPos` for FrameArgument nodes whose head is a single token and
                which do not contain internal dependents. It is intentionally
                general-purpose and should be safe to run early in the refinement
                sequence.

                Preconditions:
                - TagOccurrence nodes are present and connected to FrameArgument via
                    `PARTICIPATES_IN`.

                Side effects:
                - Mutates FrameArgument nodes to record head token metadata used by
                    later linking and canonicalisation steps.
                """
                logger.debug("get_and_assign_head_info_to_all_frameArgument_singletoken")
                graph = self.graph

                query = """    
                                                match p= (a:TagOccurrence where a.pos in ['NNS', 'NN', 'NNP', 'NNPS','PRP', 'PRP$'])--(c:FrameArgument)
                                                where not exists ((a)<-[:IS_DEPENDENT]-()--(c)) and not exists ((a)-[:IS_DEPENDENT]->()--(c))
                                                WITH c, a, p
                                                set c.head = a.text, c.headTokenIndex = a.tok_index_doc, c.headPos = a.pos
                                                return p
    
        
                """
                data= graph.run(query).data()
        
                return ""



        

    #To find head info for the FrameArgument i.e., with single token as head
    # here head is noun or pronoun
    def get_and_assign_head_info_to_temporal_frameArgument_singletoken(self):
        """Handle single-token temporal FrameArguments (ARGM-TMP and alike).

        Temporal frame arguments often use adverbs or nominal expressions as
        single-token signals (e.g., 'yesterday', 'today', or 'soon'). This
        method captures those tokens and assigns `head`, `headTokenIndex` and
        a coarse `syntacticType` so the TemporalPhase can later link FAs to
        TIMEX/TEvent nodes during enrichment.
        """
        logger.debug("get_and_assign_head_info_to_temporal_frameArgument_singletoken")
        graph = self.graph
        # query = """    
        #                 match p= (a:TagOccurrence where a.pos in ['NNS', 'NN', 'NNP', 'NNPS','PRP', 'PRP$', 'RB'])--
        #                 (c:FrameArgument {type:'ARGM-TMP'})
        #                 where not exists ((a)<-[:IS_DEPENDENT]-()--(c)) and not exists ((a)-[:IS_DEPENDENT]->()--(c))
        #                 WITH c, a, p
        #                 set c.head = a.text, c.headTokenIndex = a.tok_index_doc,
        #                 (case when a.pos in ['NNS', 'NN'] then c END).syntacticType ='NOMINAL' , 
        #                 (case when a.pos in ['NNP', 'NNPS'] then c END).syntacticType ='NAM', 
        #                 (case when a.pos in ['PRP', 'PRP$'] then c END).syntacticType ='PRO',
        #                 (case when a.pos in ['RB'] then c END).syntacticType ='ADV'
        #                 return p    
        
        # """

        query = """    
                        match p= (a:TagOccurrence where a.pos in ['NNS', 'NN', 'NNP', 'NNPS','PRP', 'PRP$', 'RB'])--
                        (c:FrameArgument)
                        where not exists ((a)<-[:IS_DEPENDENT]-()--(c)) and not exists ((a)-[:IS_DEPENDENT]->()--(c))
                        WITH c, a, p
                        set c.head = a.text, c.headTokenIndex = a.tok_index_doc,
                            c.syntacticType = CASE
                                WHEN a.pos IN ['NNS', 'NN'] THEN 'NOMINAL'
                                WHEN a.pos IN ['NNP', 'NNPS'] THEN 'NAM'
                                WHEN a.pos IN ['PRP', 'PRP$'] THEN 'PRO'
                                WHEN a.pos IN ['RB'] THEN 'ADV'
                                ELSE coalesce(c.syntacticType, 'NAM') END
                        return p    
        
        """
        data= graph.run(query).data()
        
        return ""


    #To find head info for the FrameArgument i.e., with multi token as head
    #here the head is noun or pronoun
    def get_and_assign_head_info_to_frameArgument_multitoken(self):
                """Assign head tokens for multi-token FrameArgument nodes.

                This pass looks for TagOccurrence tokens that participate in a
                multi-token FrameArgument and which act as the syntactic head (i.e.
                they have outgoing dependency links into the argument but no
                incoming dependents from inside the span). It records head text,
                token index and a coarse `syntacticType` derived from POS.

                Preconditions:
                - FrameArgument and TagOccurrence nodes exist and are linked via
                    `PARTICIPATES_IN`.

                Side effects:
                - Sets `head`, `headTokenIndex` and `syntacticType` on FrameArgument
                    nodes where a head can be determined.
                """
                logger.debug("get_and_assign_head_info_to_frameArgument_multitoken")
                graph = self.graph
        
                query = """    
                                                match p= (a:TagOccurrence where a.pos in ['NNS', 'NN', 'NNP', 'NNPS','PRP', 'PRP$'])-
                                                [:IN_FRAME]->(f:FrameArgument), q= (a)-[:IS_DEPENDENT]->()--(f)
                                                where not exists ((a)<-[:IS_DEPENDENT]-()--(f))
                                                WITH f, a, p
                                                set f.head = a.text, f.headTokenIndex = a.tok_index_doc, 
                                                    f.syntacticType = CASE
                                                        WHEN a.pos IN ['NNS', 'NN'] THEN 'NOMINAL'
                                                        WHEN a.pos IN ['NNP', 'NNPS'] THEN 'NAM'
                                                        WHEN a.pos IN ['PRP', 'PRP$'] THEN 'PRO'
                                                        ELSE coalesce(f.syntacticType, 'NAM') END
                                                return p    
        
                """
                data= graph.run(query).data()
        
                return ""



 




    #General rule to get and assign head of all multi-token framearguments
    def get_and_assign_head_info_to_all_frameArgument_multitoken(self):
        """Assign head token metadata for all multi-token FrameArguments.

        This general pass is similar to the single-type version but records
        the `headPos` as well. Run this after token-level and dependency
        annotation are available. It is idempotent and safe to rerun.
        """
        logger.debug("get_and_assign_head_info_to_all_frameArgument_multitoken")
        graph = self.graph
        
        query = """    
                        match p= (a:TagOccurrence)-[:IN_FRAME]->(f:FrameArgument), q= (a)-[:IS_DEPENDENT]->()--(f)
                        where not exists ((a)<-[:IS_DEPENDENT]-()--(f))
                        WITH f, a, p
                        set f.head = a.text, f.headTokenIndex = a.tok_index_doc, f.headPos = a.pos 
                        return p    
        
        """
        data= graph.run(query).data()
        
        return ""

    # // This query first find out those FrameArguments of type ['ARG1', 'ARG0', 'ARG2', 'ARG3', 'ARG4', 'ARGA', 'ARGM-TMP'] and
    # // which have 'preposition' as a headword. 
    # // Then It finds out the complement (pobj) of the preposition and mark it as 
    # // complement. This complement will be used to refer to the entity. 
    # // NOTE: The preoposition word will help in understanding the type of association between frame and
    # // the frameargument with respect to the preposition and complement (noun) entity. 
    #// UPDATE: ARGM-TMP is added in the list of allowable types. 
    def get_and_assign_head_info_to_frameArgument_with_preposition(self):

        logger.debug("get_and_assign_head_info_to_frameArgument_with_preposition")
        graph = self.graph

        query = """    
                        match p= (a:TagOccurrence where a.pos in ['IN'])--
                        (f:FrameArgument where f.type in ['ARG1', 'ARG0', 'ARG2', 'ARG3', 'ARG4', 'ARGA', 'ARGM-TMP']), q= (a)-[:IS_DEPENDENT]->()--(f)
                        where not exists ((a)<-[:IS_DEPENDENT]-()--(f))
                        set f.head = a.text, f.headTokenIndex = a.tok_index_doc, f.syntacticType ='IN'
                        with *
                        match (a)-[x:IS_DEPENDENT]->(c) where x.type = 'pobj' 
                        set f.complement = c.text, f.complementIndex = c.tok_index_doc, 
                        f.complementFullText = substring(f.text, size(f.head)+1)
                        return p    
        
        """
        data= graph.run(query).data()
        
        return ""





    #To find head info for the FrameArgument i.e., with multi token as head
    #// It shows when an action took place
    # // case: when headword in an FA is a verb connected with preposition via MARK dep-parse relation.
    # // the text is a clause starts with some temporal preposition such as 
    # // after, before, 
    # #// COMMON OBSERVATIONS: 
    # #// - FA has type ARGM-TMP
    #// - FA has some VERB denoting that its refering to some event
    #// - FA has some signal that we could relate to some type of TLINK  
    def get_and_assign_head_info_to_temporal_frameArgument_multitoken_mark(self):

        logger.debug("get_and_assign_head_info_to_temporal_frameArgument_multitoken_mark")
        graph = self.graph
        # Relax POS constraints: allow several verb POS tags (VBD/VB/VBG/VBZ/VBN/VBP)
        # so we don't miss eventive constructions due to tagging variation.
        query = """
                        match p= (s:TagOccurrence where s.pos = 'IN')<-[:IS_DEPENDENT {type: 'mark'}]
                        -(a:TagOccurrence where a.pos in ['VBD','VB','VBG','VBZ','VBN','VBP'])-
                        [:IN_FRAME]->(f:FrameArgument where f.type = 'ARGM-TMP'), q= (a)-[:IS_DEPENDENT]->()--(f)
                        where not exists ((a)<-[:IS_DEPENDENT]-()--(f))
                        WITH f, a, p,s
                        set f.head = a.text, f.headTokenIndex = a.tok_index_doc, f.syntacticType ='EVENTIVE', f.signal = s.text
                        return p

        """
        data= graph.run(query).data()

        return ""



    #To find head info for the FrameArgument which has type of ARGM-TMP i.e., with multi token as head
    #// It shows when an action took place
    # // case: when headword in an FA is a preposition connected with verb gerund (complement) via pcomp dep-parse relation.
    # // the text is a clause starts with some temporal preposition such as 
    # // after, before,    
    #// COMMON OBSERVATIONS:
    #// - FA has type ARGM-TMP
    #// - FA has some VERB denoting that its refering to some event
    #// - FA has some signal that we could relate to some type of TLINK
    def get_and_assign_head_info_to_temporal_frameArgument_multitoken_pcomp(self):
                        """Handle temporal FrameArguments where a preposition links to a VBG via pcomp.

                        Pattern: preposition (IN) participates in a FrameArgument of type
                        'ARGM-TMP' and has a 'pcomp' dependent that is a gerund (VBG).

                        Effect:
                        - Records `head`, `headTokenIndex`, `syntacticType='EVENTIVE'`,
                            `signal` (preposition text) and `complement` (the VBG text).

                        Business rationale:
                        - These constructions commonly express temporal relations (e.g.
                            "in following doing X") and capturing both the signal and the
                            gerund complement supports TLINK detection and event enrichment.
                        """
                        # use shared graph established in __init__
                        graph = self.graph

                        query = """    
                                                        match p= (f)--(v:TagOccurrence {pos: 'VBG'})<-[l:IS_DEPENDENT {type: 'pcomp'}]-
                                                        (a:TagOccurrence where a.pos in ['IN'])-[:IN_FRAME]->(f:FrameArgument where f.type = 'ARGM-TMP')
                                                        where not exists ((a)<-[:IS_DEPENDENT]-()--(f))
                                                        WITH f, a, p, v
                                                        set f.head = a.text, f.headTokenIndex = a.tok_index_doc, f.syntacticType ='EVENTIVE', f.signal = a.text, f.complement = v.text
                                                        return p     
        
                        """
                        data= graph.run(query).data()

                        return ""

#To find head info for the FrameArgument i.e., with multi token as head
    #// It shows when an action took place
    # // case: when headword in an FA is a preposition connected with verb gerund (complement) via pcomp dep-parse relation.  
    #// COMMON OBSERVATIONS:
    #// - FA has some VERB denoting that its refering to some event
    #// - FA has some signal that we could relate to some type of Link
    def get_and_assign_head_info_to_eventive_frameArgument_multitoken_pcomp(self):
        """Assign eventive metadata for FrameArguments with pcomp-linked gerunds.

        This method is a close variant of the temporal pcomp handler. It
        captures cases where a gerund (VBG) is attached through a pcomp
        dependency and records the same set of fields used by temporal
        processing: `head`, `headTokenIndex`, `syntacticType`, `signal`, and
        `complement`.
        """
        logger.debug("get_and_assign_head_info_to_eventive_frameArgument_multitoken_pcomp")
        graph = self.graph

        query = """    
            match p= (f)--(v:TagOccurrence {pos: 'VBG'})<-[l:IS_DEPENDENT {type: 'pcomp'}]-
            (a:TagOccurrence where a.pos in ['IN'])-[:IN_FRAME]->(f:FrameArgument)
            where not exists ((a)<-[:IS_DEPENDENT]-()--(f))
            WITH f, a, p, v
            set f.head = a.text, f.headTokenIndex = a.tok_index_doc, f.syntacticType ='EVENTIVE', f.signal = a.text, f.complement = v.text
            return p    
        
        """
        data= graph.run(query).data()

        return ""

    
    #To find head info for the FrameArgument which has type of ARGM-TMP i.e., with multi token as head
    #// CASE: has root as a verb. But this verb is acting like a preposition as it has POBJ link with an object. 
    #// example can be following in 'following the European Central Bank' 
    #// to see more detail: check pobj in https://downloads.cs.stanford.edu/nlp/software/dependencies_manual.pdf
    #// COMMON OBSERVATIONS: 
    #// - FA has type ARGM-TMP
    #// - FA has some VERB denoting that its refering to some event
    #// - FA has some signal that we could relate to some type of TLINK
    def get_and_assign_head_info_to_temporal_frameArgument_multitoken_pobj(self):
        """Handle temporal FrameArguments where a preposition has a POBJ dependent.

        These patterns capture constructions like 'following the X' where the
        preposition (IN) governs a pobj that is the complement. We record the
        preposition as the `head/signal` and the pobj as the `complement` so
        later entity linking can match the complement against NamedEntities.
        """
        logger.debug("get_and_assign_head_info_to_temporal_frameArgument_multitoken_pobj")
        graph = self.graph
        # The original query filtered on a.text = 'following' which is too strict
        # and caused no matches. Remove that specific filter and accept the POS
        # constraints as-is so commonly observed prepositions (in, on, of, by)
        # are picked up.
        query = """
                        match p= (f)--(v:TagOccurrence)<-[l:IS_DEPENDENT {type: 'pobj'}]-
                        (a:TagOccurrence where a.pos in ['IN', 'VBG'])-[:IN_FRAME]->(f:FrameArgument where f.type = 'ARGM-TMP')
                        where not exists ((a)<-[:IS_DEPENDENT]-()--(f))
                        WITH f, a, p, v
                        set f.head = a.text, f.headTokenIndex = a.tok_index_doc, f.syntacticType ='EVENTIVE', f.signal = a.text, f.complement = v.text
                        return p     
        """
        data= graph.run(query).data()

        return ""








# PHASE 2 
# Linking FA to NamedEntity

    # //WE JUST NEED TO CONNECT FA TO NAMED ENTITY. 
    # //CASE: when FA's headword is either a proper noun or common noun
    # // It is straight forward as the named entity and FA both sharing the same headword
    def link_frameArgument_to_namedEntity_for_nam_nom(self):
        """Link FrameArguments to NamedEntity nodes when heads match.

        This rule creates a REFERS_TO edge for FrameArguments whose head
        token index matches a NamedEntity head token. It targets proper
        noun and common-noun matches where the head token is sufficient to
        identify the entity instance.
        """
        logger.debug("link_frameArgument_to_namedEntity_for_nam_nom")
        graph = self.graph

        query = """    
                        match p= (f:FrameArgument)<-[:IN_FRAME]-(head:TagOccurrence )-[:IN_MENTION]->(ne:NamedEntity)
                        where head.tok_index_doc = f.headTokenIndex and head.tok_index_doc = ne.headTokenIndex
                        merge (f)-[:REFERS_TO]->(ne)
                        return p     
        
        """
        data= graph.run(query).data()
        
        return ""

    # //WE JUST NEED TO CONNECT FA TO NAMED ENTITY. 
    # //CASE: when FA's headword is a prepostion. In this case we gonna see the POBJ headword and match it with namedEntity.
    # TODO: add pobj as type of refers_to relationship
    def link_frameArgument_to_namedEntity_for_pobj(self):
        """Link prepositional FrameArguments to NamedEntity using complement index.

        For FAs whose syntactic head is a preposition, the actual referent is
        often the preposition's object (complement). This rule links the FA
        to a NamedEntity whose headTokenIndex matches the recorded
        `complementIndex`.
        """
        logger.debug("link_frameArgument_to_namedEntity_for_pobj")
        graph = self.graph

        query = """    
                        match p= (f:FrameArgument)<-[:IN_FRAME]-(complementHead:TagOccurrence )-[:IN_MENTION]->(ne:NamedEntity)
                        where complementHead.tok_index_doc = f.complementIndex and complementHead.tok_index_doc = ne.headTokenIndex
                        merge (f)-[:REFERS_TO]->(ne)
                        return p     
        
        """
        data= graph.run(query).data()
        
        return ""



    # //WE JUST NEED TO CONNECT FA (prepositional) TO NAMED ENTITY. 
    # //CASE:  when FA refereing to an entity but not named entity. usually such situation it refering to nominal. 
    # //CASE: when FA's headword is a prepostion. In this case we gonna see the POBJ headword and match it with Entity.
    # // this query try to find those FAs who do not have any entity instance created during NER or NEL.  
    # // MISSING: fields such as extent, type(set here temporarily). Further, entity disambiguation and deduplication may be required. 
    # // coreferencing information can be employed to deduplicate entities.  
    def link_frameArgument_to_namedEntity_for_pobj_entity(self):
        """Create Entity nodes when a complement doesn't map to a NamedEntity.

        Some prepositional complements refer to nominal entities that were not
        recognized by NER/NEL. This rule creates a lightweight `Entity`
        node using the complement's full text and links the FrameArgument to
        it. This is a best-effort step and may require later deduplication or
        KB linking.
        """
        logger.debug("link_frameArgument_to_namedEntity_for_pobj_entity")
        graph = self.graph

        query = """    
                        MATCH p= (f:FrameArgument where f.type in ['ARG0','ARG1','ARG2','ARG3','ARG4'])-[:IN_FRAME]-
                        (complementHead:TagOccurrence)
                        where f.complementIndex = complementHead.tok_index_doc and not exists 
                        ((complementHead)-[]-(:NamedEntity {headTokenIndex: complementHead.tok_index_doc})) and not exists
                        ((f)-[:REFERS_TO]-(:NamedEntity))
                        MERGE (e:Entity {id: f.complementFullText})
                        ON CREATE SET e.type = complementHead.pos, e.syntacticType = complementHead.pos, e.head = f.complement, e.headTokenIndex = f.complementIndex
                        MERGE (complementHead)-[:PARTICIPATES_IN]->(e)
                        MERGE (f)-[:REFERS_TO]->(e)
                        RETURN p   
        
        """
        data= graph.run(query).data()
        
        return ""
    

    # //WE JUST NEED TO CONNECT FA TO NAMED ENTITY. 
    # //CASE: when FA's headword is a pronominal i.e., having pos value as PRP or PRP$
    # // we designed this query because we need to deal with FAs who have pronominal token. 
    # //we need the path to the named entity via coref-antecedent links
    def link_frameArgument_to_namedEntity_for_pro(self):
        """Link pronominal FrameArguments to NamedEntity using coreference.

        For FAs headed by pronouns, we follow CorefMention -> Antecedent ->
        NamedEntity chains to resolve the pronoun to an entity and create a
        REFERS_TO link. This allows pronoun-bearing arguments to participate
        in event enrichment.
        """
        logger.debug("link_frameArgument_to_namedEntity_for_pro")
        graph = self.graph

        query = """    
                        match p= (f:FrameArgument)<-[:IN_FRAME]-(head:TagOccurrence )-[:IN_MENTION]->
                        (crf:CorefMention)--(ant:Antecedent)-[:REFERS_TO]->(ne:NamedEntity)
                        where head.pos in ['PRP','PRP$'] and head.tok_index_doc = f.headTokenIndex and head.tok_index_doc = crf.headTokenIndex
                        merge (f)-[:REFERS_TO]->(ne)
                        return p     
        
        """
        data= graph.run(query).data()
        
        return ""

    # // this query try to find those FAs who do not have any entity instance created during NER or NEL.  
    # // TODO: fields such as extent, type(set here temporarily). Further, entity disambiguation and deduplication may be required. 
    # // coreferencing information can be employed to deduplicate entities.
    # // CASES NOT COVERED: 
    # // 1: when FA has text span which has more than one entity. For example, 'millions of people', here we have million as numeric and millions of people as nominal.
    # //    -- perhaps these overlapping spans denoting multiple entities can be handled using SPANCAT. R&D is required 
    # //    -- presently, the pipeline tag 'millions' as CARDINAL and refers_to connection is establish between FA and CARDINAL entity. However this connection is not
    # //    -- correct as the correct entity is 'millions of people' which is NOMINAL.  Though head of FA is 'millions' in this phrase. 
    def link_frameArgument_to_new_entity(self):
        """Create generic Entity nodes for FrameArguments not mapped to NamedEntity.

        When an FA does not refer to a NamedEntity (e.g., common nouns or
        nominal phrases), this rule creates an `Entity` node and links the
        FA to it. The created Entity uses the FA text as a simple identifier
        and stores syntactic metadata to support later deduplication.
        """
        logger.debug("link_frameArgument_to_new_entity")
        graph = self.graph

        query = """
                        MATCH p= (f:FrameArgument where f.type IN ['ARG0','ARG1','ARG2','ARG3','ARG4'] and f.syntacticType <> 'PRO')
                        -[:IN_FRAME]-(h:TagOccurrence where NOT (h.pos IN ['IN']))
                        WHERE f.headTokenIndex = h.tok_index_doc
                         AND NOT EXISTS ((h)-[]-(:NamedEntity {headTokenIndex: h.tok_index_doc}))
                        OPTIONAL MATCH (d:AnnotatedText)-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(h)
                        WITH p, f, h, d,
                            coalesce(f.start_tok, f.startIndex, h.tok_index_doc) AS start_tok,
                            coalesce(f.end_tok, f.endIndex, h.tok_index_doc) AS end_tok,
                            coalesce(f.headTokenIndex, h.tok_index_doc) AS head_tok,
                            coalesce(toString(d.id), split(f.id, '_')[1], '0') AS doc_part
                        WITH p, f, h, start_tok, end_tok, head_tok,
                            'nominal_' + doc_part + '_' + toString(start_tok) + '_' + toString(end_tok) AS entity_id
                        MERGE (e:Entity {id: entity_id, type: 'NOMINAL'})
                        SET e.syntacticType = 'NOMINAL',
                           e.head = coalesce(f.head, h.text),
                           e.headTokenIndex = head_tok,
                           e.start_tok = start_tok,
                           e.end_tok = end_tok,
                           e.start_char = coalesce(f.start_char, h.index),
                           e.end_char = coalesce(f.end_char, h.end_index),
                           e.text = coalesce(f.text, e.text),
                           e.source = 'frame_argument_nominal',
                           e.source_frame_argument_id = f.id,
                           e.provenance_rule_id = 'refinement.link_frameArgument_to_new_entity'
                        MERGE (f)-[:REFERS_TO]->(e)
                        RETURN p
        """
        data= graph.run(query).data()
        
        return ""

    # //WE JUST NEED TO CONNECT ANTECEDENT TO NAMED ENTITY.
    def link_antecedent_to_namedEntity(self):
        """Link Antecedent nodes to NamedEntity instances when heads match.

        Antecedents produced by coreference resolution often correspond to
        NamedEntity instances. This rule creates a REFERS_TO relation when
        the head token index matches; it is useful to propagate authoritative
        entity identifiers into coreference structures.
        """
        logger.debug("link_antecedent_to_namedEntity")
        graph = self.graph

        query = """    
                        match p= (f:Antecedent)<-[:IN_MENTION]-(head:TagOccurrence )-[:IN_MENTION]->(ne:NamedEntity)
                        where head.tok_index_doc = f.headTokenIndex and head.tok_index_doc = ne.headTokenIndex
                        merge (f)-[:REFERS_TO]->(ne)
                        return p    
        
        """
        data= graph.run(query).data()
        
        return ""

        


    
# //It will add another label to named entities that are qualified as value.
    def tag_numeric_entities(self):
        """Add a `NUMERIC` label to NamedEntity nodes representing numeric values.

        This is a lightweight normalization step that marks certain NE
        semantic types (MONEY, QUANTITY, PERCENT) with an additional label
        to simplify downstream numeric handling and event enrichment.

        DEPRECATED: Write-suppressed by default (features.fill_numeric_labels=False).
        This method is retained only to support operator-triggered backfill for graphs
        predating the default suppression. Canonical participant resolution uses
        `Entity`/`VALUE` node targets. Removal tracked via migration 0019.
        """
        logger.debug("tag_numeric_entities")
        cfg = get_config()
        if not cfg.features.fill_numeric_labels:
            logger.debug(
                "tag_numeric_entities: skipped (features.fill_numeric_labels=False); "
                "set TEXTGRAPHX_FILL_NUMERIC_LABELS=true to enable legacy :NUMERIC writes"
            )
            return ""
        warnings.warn(
            "RefinementPhase.tag_numeric_entities() is deprecated. "
            "Prefer canonical VALUE/Entity-based participant resolution. "
            "Remaining :NUMERIC labels are removed by migration 0019.",
            DeprecationWarning,
            stacklevel=2,
        )
        graph = self.graph

        query = """    
                        match (ne:NamedEntity) where ne.type in ['MONEY', 'QUANTITY', 'PERCENT']
                        set ne:NUMERIC
                        return count(ne) as tagged
        
        """
        data = graph.run(query).data()
        tagged = data[0].get("tagged", 0) if data else 0
        logger.warning(
            "tag_numeric_entities: applied legacy :NUMERIC label to %d NamedEntity nodes; this path remains transitional during VALUE migration",
            tagged,
        )
        
        return ""



    # //It will add another label to named entities that are qualified as value.
    def tag_value_entities(self):
        """Add a `VALUE` label to NamedEntity nodes that represent counted or measured values.

        This includes cardinal/ordinal and other value-like types to make it
        easier to find and operate on numeric or quantified entities during
        enrichment and evaluation.

        DEPRECATED: Write-suppressed by default (features.fill_numeric_labels=False).
        Canonical VALUE nodes are created directly by materialize_canonical_value_nodes().
        This method is retained only for historical operator use. Remaining NamedEntity:VALUE
        dynamic labels are removed by migration 0019.
        """
        logger.debug("tag_value_entities")
        cfg = get_config()
        if not cfg.features.fill_numeric_labels:
            logger.debug(
                "tag_value_entities: skipped (features.fill_numeric_labels=False); "
                "set TEXTGRAPHX_FILL_NUMERIC_LABELS=true to enable legacy :VALUE writes"
            )
            return ""
        warnings.warn(
            "RefinementPhase.tag_value_entities() is deprecated. "
            "Prefer canonical VALUE nodes. Remaining :VALUE dynamic labels "
            "on NamedEntity nodes are removed by migration 0019.",
            DeprecationWarning,
            stacklevel=2,
        )
        graph = self.graph

        query = """    
                        match (ne:NamedEntity) where ne.type in ['CARDINAL', 'ORDINAL', 'MONEY', 'QUANTITY', 'PERCENT']
                        set ne:VALUE
                        return count(ne) as tagged
        
        """
        data = graph.run(query).data()
        tagged = data[0].get("tagged", 0) if data else 0
        logger.warning(
            "tag_value_entities: applied transitional :VALUE label to %d NamedEntity nodes before canonical VALUE materialization",
            tagged,
        )
        
        return ""


    def materialize_canonical_value_nodes(self):
        """Materialize canonical VALUE nodes from value-like NamedEntity mentions.

        VALUE is the canonical schema node for value expressions (MONEY,
        QUANTITY, PERCENT, CARDINAL, ORDINAL, etc). This method creates a
        stable VALUE node keyed by (doc_id, id), links source NamedEntity
        mentions via REFERS_TO, and propagates participant links so VALUE can
        participate directly in event arguments.
        """
        logger.debug("materialize_canonical_value_nodes")
        graph = self.graph

        query_materialize = """
                        MATCH (ne:NamedEntity:VALUE)
                        OPTIONAL MATCH (ne)<-[:PARTICIPATES_IN]-(tok:TagOccurrence)
                        WITH ne,
                             min(tok.tok_index_doc) AS min_tok,
                             max(tok.tok_index_doc) AS max_tok,
                             split(ne.id, '_')[0] AS doc_part
                        WITH ne,
                             CASE WHEN doc_part =~ '^[0-9]+$' THEN toInteger(doc_part) ELSE 0 END AS doc_id,
                             coalesce(min_tok, toInteger(ne.index), 0) AS start_tok,
                             coalesce(max_tok, toInteger(ne.end_index), toInteger(ne.index), 0) AS end_tok,
                             CASE
                               WHEN ne.type IN ['PERCENT', 'MONEY', 'QUANTITY', 'CARDINAL', 'ORDINAL', 'DATE', 'DURATION', 'NUMERIC']
                               THEN ne.type
                               ELSE 'OTHER'
                             END AS value_type
                        MERGE (v:VALUE {doc_id: doc_id, id: ne.id})
                        SET v.type = value_type,
                            v.value = coalesce(ne.value, ne.text, ''),
                            v.start_tok = start_tok,
                            v.end_tok = end_tok,
                            v.start_char = coalesce(ne.index, v.start_char),
                            v.end_char = coalesce(ne.end_index, v.end_char),
                            v.value_normalized = toLower(coalesce(ne.value, ne.text, '')),
                            v.source = 'named_entity_value'
                        MERGE (ne)-[:REFERS_TO]->(v)
                        RETURN count(DISTINCT v) AS values_materialized
        """
        graph.run(query_materialize).data()

        # Let FrameArguments resolve directly to VALUE nodes when they currently
        # resolve through NamedEntity mentions.
        query_link_fa = """
                        MATCH (fa:FrameArgument)-[:REFERS_TO]->(ne:NamedEntity)-[:REFERS_TO]->(v:VALUE)
                        MERGE (fa)-[:REFERS_TO]->(v)
                        RETURN count(DISTINCT fa) AS frame_args_linked
        """
        graph.run(query_link_fa).data()

        # Propagate event participant edges so VALUE appears as a first-class
        # participant source in the evaluation graph.
        query_participants = """
                        MATCH (fa:FrameArgument)-[:REFERS_TO]->(v:VALUE)
                        MATCH (fa)-[p:PARTICIPANT|EVENT_PARTICIPANT]->(ev)
                        MERGE (v)-[vp:EVENT_PARTICIPANT]->(ev)
                        SET vp.type = coalesce(p.type, fa.type),
                            vp.prep = coalesce(p.prep, fa.head),
                            vp.roleFrame = coalesce(vp.roleFrame, 'PROPBANK'),
                            vp.confidence = coalesce(vp.confidence, 1.0)
                        RETURN count(DISTINCT vp) AS value_participants_linked
        """
        graph.run(query_participants).data()

        # VALUE label on NamedEntity was historically used as a convenience
        # tag. Remove it to avoid mixed semantics now that canonical VALUE
        # nodes are materialized explicitly.
        query_cleanup_legacy_label = """
                MATCH (ne:NamedEntity:VALUE)
                REMOVE ne:VALUE
                SET ne.value_tagged = true
                RETURN count(ne) AS cleaned
        """
        graph.run(query_cleanup_legacy_label).data()

        return ""


    #// CASE Incorrect Named Entity Disambiguation (Example 1: JIM CRAMER detected as PIETER CRAMER which is wrong)
    #// 
    #// NED processing has not accurately disambiguated an entity. We are using Coref information to detect and correct the incorrect result
    #// ASSUMPTION: that the antecedent is correctly disambiguated and we should rely on it. d
    #// Here we are giving preference to NamedEntity refered by Antecedent node. Replacing the incorrect with the correct one.  
    #// PRECONDITION: KB_ID attributes of both NamedEntities are not null. This query should be run before the Frameargument linking with NamedEntity
    #// cases - 1. kb_id of both namedEntities are not null (DONE in this query)
    #//         2. ne1 doesnt have kb_id and ne2 has kb_id  (e.g., Fed as a spacy entity but actually refering to dbpedia Federal Researve)(DONE in next query v2)
    #//               

    def filter_orphan_entities(self):
        """Flag isolated pronouns and background nominals as non-core (is_timeml_core=false)."""
        logger.info("filter_orphan_entities: running coreference-gated salience filter")
        query = """
        MATCH (em:EntityMention)
        WHERE em.syntactic_type IN ['pro', 'nom', 'NOMINAL', 'PRONOUN']
        OPTIONAL MATCH (em)-[r:COREFERENT_WITH]-()
        WITH em, count(r) as coref_count
        SET em.is_timeml_core = CASE 
            WHEN coref_count = 0 THEN false
            ELSE true
        END
        """
        self.graph.run(query)

    def detect_correct_NEL_result_for_having_kb_id(self):
        """Correct Named Entity Linking (NEL) when both NE candidates have KB ids.

        Uses coreference chains to prefer the entity linked from the
        Antecedent/coref chain when two different NamedEntity nodes (ne1,
        ne2) with different KB identifiers are observed for the same
        mention. The method copies authoritative KB metadata from ne2 to ne1
        and consolidates Entity nodes.
        """
        logger.debug("detect_correct_NEL_result_for_having_kb_id")
        graph = self.graph

        query = """    
                        match p= (e1:Entity)<-[:REFERS_TO]-(ne1:NamedEntity)<-[:IN_MENTION]-(t1:TagOccurrence)-[:IN_MENTION]->(coref:CorefMention)-[:COREF]->(ant:Antecedent)-[:REFERS_TO]->(ne2:NamedEntity)-[:REFERS_TO]->(e2:Entity)
                        where t1.text = ne1.head and t1.text = coref.head and ne1.kb_id is not null and ne2.kb_id is not null and ne1.kb_id <> ne2.kb_id
                        set ne1.kb_id = ne2.kb_id, ne1.description = ne2.description, ne1.normal_term = ne2.normal_term, ne1.url_wikidata = ne2.url_wikidata,ne1.type = ne2.type
                        detach delete e1
                        merge (ne1)-[:REFERS_TO]->(e2)
                        return p    
        
        """
        data= graph.run(query).data()
        
        return ""




    #// detecting and correcting named entities result. 
    #// Using the coreferencing information, and assuming antecedent refering to correct entity.
    #// CONDITION: if entity of token from any of the corefmention is not equal to entity refered by antecedent.
    #// CONDITION: ne1 doesnt have kb_id and ne2 has kb_id  (e.g., Fed as a spacy entity but actually refering to dbpedia Federal Researve)              
    def detect_correct_NEL_result_for_missing_kb_id(self):
        """Copy KB metadata when a coreferent NE has a KB id and the other lacks it.

        If a NamedEntity `ne1` lacks a KB id but its coreferent `ne2` has one,
        prefer `ne2`'s metadata and link `ne1` to the authoritative Entity.
        This helps salvage disambiguation information from coreference.
        """
        logger.debug("detect_correct_NEL_result_for_missing_kb_id")
        graph = self.graph

        query = """    
                        match p= (e1:Entity)<-[:REFERS_TO]-(ne1:NamedEntity)<-[:IN_MENTION]-(t1:TagOccurrence)-[:IN_MENTION]->(coref:CorefMention)-[:COREF]->(ant:Antecedent)-[:REFERS_TO]->(ne2:NamedEntity)-[:REFERS_TO]->(e2:Entity)
                        where t1.text = ne1.head and t1.text = coref.head and ne1.kb_id is null and ne2.kb_id is not null
                        set ne1.kb_id = ne2.kb_id, ne1.spacyType = ne1.type, ne1.type = ne2.type, ne1.description = ne2.description, ne1.normal_term = ne2.normal_term, ne1.url_wikidata = ne2.url_wikidata
                        detach delete e1
                        merge (ne1)-[:REFERS_TO]->(e2)
                        return p    
        
        """
        data= graph.run(query).data()
        return ""
         



    # // This method detects the presence of quantified entities and create a new instance of it. 
    # // It will first see whether the head token in frameArgument denotes a NUMERIC value (as a namedEntity) or some quantified signal such as all, some, many etc
    # // and it is satisfying the following noun phrase composition:
    # // (head {any quantifier}) --- (preposition {text:'of'}) --- (noun) e.g., millions of people, some of the players etc.
    # // it deletes the existing REFERS_TO relationship between frameArgument and (numeric)NamedEntity. creates a new Entity and link frameArgument with that entity. 
    # // PRECONDITIONS: should be executed after NER, NEL, head-identification, linking FA to namedEntities, entities.    
    # // TODO: currently it only assign a type as NOMINAL to newly created entity. But it needs to be improved to detect PARTITIVE constructions. 
    # // also it should be able to differentiate between partitive and nominal instances. for more detail see page 20 of 
    # // 'NEWSREADER GUIDELINES FOR ANNOTATION AT DOCUMENT LEVEL' NWR-2014-2-2
    def detect_quantified_entities_from_frameArgument(self):
        """Detect and create Entity nodes for quantified constructions.

        Example patterns: 'millions of people', 'some of the players'. The
        method looks for 'head of pobj' constructions where the head is a
        quantifier or linked to a CARDINAL NamedEntity and replaces numeric
        NE links with a new nominal `Entity` representing the quantified
        group.
        """
        logger.debug("detect_quantified_entities_from_frameArgument")
        graph = self.graph

        query = """
                    match p = (pobj:TagOccurrence where pobj.pos in ['NNS','NNP','NN', 'NNPS','PRP', 'PRP$'])<-[dep2:IS_DEPENDENT {type: 'pobj'}]
                    -(prep:TagOccurrence where prep.text= 'of')<-[dep1:IS_DEPENDENT {type: 'prep'}]-(head:TagOccurrence)-
                    [:IN_FRAME]->(fa:FrameArgument), (pobj)--(fa)
                    where head.tok_index_doc = fa.headTokenIndex
                                            and (
                                                exists ((head)-[:IN_MENTION]->(:NamedEntity {type: 'CARDINAL'}))
                                                OR head.lemma in ['all', 'some', 'many', 'most', 'few', 'several', 'none', 'half', 'part', 'portion', 'group', 'majority', 'minority', 'rest', 'number', 'lot', 'lots']
                                            )
                    OPTIONAL MATCH (d:AnnotatedText)-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(head)
                    with distinct fa, p, head, d,
                        coalesce(fa.start_tok, fa.startIndex, head.tok_index_doc) as start_tok,
                        coalesce(fa.end_tok, fa.endIndex, head.tok_index_doc) as end_tok,
                                                coalesce(toString(d.id), split(fa.id, '_')[1], '0') as doc_part,
                                                pobj,
                                                CASE
                                                    WHEN head.lemma in ['all', 'some', 'many', 'most', 'few', 'several', 'none', 'half', 'part', 'portion', 'group', 'majority', 'minority', 'rest', 'number', 'lot', 'lots']
                                                    THEN 'PARTITIVE'
                                                    ELSE 'QUANTIFIED'
                                                END as nominal_subtype
                                        with distinct fa, p, head, pobj, start_tok, end_tok, nominal_subtype,
                        'nominal_quant_' + doc_part + '_' + toString(start_tok) + '_' + toString(end_tok) as entity_id
                    merge (e:Entity {id: entity_id, type: 'NOMINAL'})
                    set e.syntacticType = 'NOMINAL',
                                                e.nominalSubtype = nominal_subtype,
                        e.head = coalesce(fa.head, head.text),
                        e.headTokenIndex = coalesce(fa.headTokenIndex, head.tok_index_doc),
                        e.start_tok = start_tok,
                        e.end_tok = end_tok,
                        e.start_char = coalesce(fa.start_char, head.index),
                        e.end_char = coalesce(fa.end_char, head.end_index),
                        e.text = coalesce(fa.text, e.text),
                                                e.quantifier = coalesce(head.lemma, head.text),
                                                e.partitivePrep = 'of',
                                                e.partitiveObject = pobj.text,
                                                e.partitiveObjectTokenIndex = pobj.tok_index_doc,
                        e.source = 'quantified_frame_argument',
                        e.source_frame_argument_id = fa.id,
                        e.provenance_rule_id = 'refinement.detect_quantified_entities_from_frameArgument'
                    merge (fa)-[:REFERS_TO]->(e)
                    with distinct fa, p
                                        match (fa)-[r:REFERS_TO]->(ne:NamedEntity)
                                        where ne.type in ['CARDINAL', 'QUANTITY', 'PERCENT', 'MONEY', 'ORDINAL']
                    delete r
                    return p    
        
        """
        data= graph.run(query).data()
        
        return ""


    def materialize_nominal_mentions_from_frame_arguments(self):
        """Materialize EntityMention nodes for nominal FrameArgument spans.

        This creates explicit mention-layer nodes with deterministic ids and
        complete span metadata for nominal entities discovered through SRL.
        """
        logger.debug("materialize_nominal_mentions_from_frame_arguments")
        graph = self.graph

        candidate_query = """
                 MATCH (fa:FrameArgument)-[:REFERS_TO]->(e:Entity)
                 WHERE coalesce(e.syntacticType, e.type, '') = 'NOMINAL'
                 OPTIONAL MATCH (tok:TagOccurrence)-[:IN_FRAME]->(fa)
                 OPTIONAL MATCH (d:AnnotatedText)-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(tok)
                 WITH fa, e, d,
                     min(tok.tok_index_doc) AS min_tok,
                     max(tok.tok_index_doc) AS max_tok,
                     min(tok.index) AS min_char,
                     max(tok.end_index) AS max_char
                 WITH fa, e,
                     CASE WHEN coalesce(toString(d.id), split(fa.id, '_')[1], '0') =~ '^[0-9]+$'
                         THEN toInteger(coalesce(toString(d.id), split(fa.id, '_')[1], '0'))
                         ELSE 0 END AS doc_id,
                     coalesce(fa.start_tok, fa.startIndex, min_tok) AS start_tok,
                     coalesce(fa.end_tok, fa.endIndex, max_tok) AS end_tok,
                     coalesce(fa.start_char, min_char) AS start_char,
                     coalesce(fa.end_char, max_char) AS end_char
                 WHERE start_tok IS NOT NULL AND end_tok IS NOT NULL
                 RETURN DISTINCT
                    e.id AS entity_id,
                    fa.id AS source_frame_argument_id,
                    doc_id,
                    coalesce(fa.text, e.text, e.head, '') AS value,
                    coalesce(fa.head, e.head) AS head,
                    coalesce(fa.headTokenIndex, e.headTokenIndex, start_tok) AS headTokenIndex,
                    start_tok,
                    end_tok,
                    start_char,
                    end_char,
                    'nom_mention_fa_' + toString(doc_id) + '_' + toString(start_tok) + '_' + toString(end_tok) AS mention_id
        """
        rows = graph.run(candidate_query).data()
        self._merge_nominal_entity_mentions(
            rows=rows,
            mention_source="fa",
            source_key="source_frame_argument_id",
            confidence=0.90,
            provenance_rule_id="refinement.materialize_nominal_mentions_from_frame_arguments",
        )

        return ""


    def materialize_nominal_mentions_from_noun_chunks(self):
        """Materialize EntityMention nodes for noun chunks not covered by NamedEntity.

        This captures discourse nominals that may never appear as SRL arguments
        while preserving deterministic ids and span metadata.
        """
        logger.debug("materialize_nominal_mentions_from_noun_chunks")
        graph = self.graph

        candidate_query = """
                 MATCH (nc:NounChunk)
                 OPTIONAL MATCH (tok:TagOccurrence)-[:PARTICIPATES_IN]->(nc)
                 OPTIONAL MATCH (d:AnnotatedText)-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(tok)
                 WITH nc, d,
                     min(tok.tok_index_doc) AS min_tok,
                     max(tok.tok_index_doc) AS max_tok,
                     min(tok.index) AS min_char,
                                         max(tok.end_index) AS max_char,
                                         toLower(trim(coalesce(nc.value, ''))) AS chunk_text_lc
                 WHERE min_tok IS NOT NULL AND max_tok IS NOT NULL
                 OPTIONAL MATCH (ne:NamedEntity)
                 WHERE coalesce(ne.start_tok, ne.token_start, ne.index) = min_tok
                   AND coalesce(ne.end_tok, ne.token_end, ne.end_index, ne.index) = max_tok
                                 WITH nc, d, min_tok, max_tok, min_char, max_char, chunk_text_lc,
                                            count(ne) AS ne_count
                                 WHERE ne_count = 0
                                     AND chunk_text_lc <> ''
                                     AND NOT chunk_text_lc IN ['yesterday', 'today', 'tomorrow']
                                     AND NOT chunk_text_lc CONTAINS '%'
                                     AND NOT chunk_text_lc CONTAINS '$'
                                     AND NOT chunk_text_lc CONTAINS '€'
                                     AND NOT chunk_text_lc CONTAINS '£'
                                     AND NOT chunk_text_lc CONTAINS '¥'
                                     AND NOT chunk_text_lc =~ '.*[0-9].*'
                                     AND NOT (chunk_text_lc STARTS WITH 'this ' AND (chunk_text_lc CONTAINS ' day' OR chunk_text_lc CONTAINS ' week' OR chunk_text_lc CONTAINS ' month' OR chunk_text_lc CONTAINS ' year'))
                                     AND NOT (chunk_text_lc STARTS WITH 'that ' AND (chunk_text_lc CONTAINS ' day' OR chunk_text_lc CONTAINS ' week' OR chunk_text_lc CONTAINS ' month' OR chunk_text_lc CONTAINS ' year'))
                                     AND NOT (chunk_text_lc STARTS WITH 'last ' AND (chunk_text_lc CONTAINS ' day' OR chunk_text_lc CONTAINS ' week' OR chunk_text_lc CONTAINS ' month' OR chunk_text_lc CONTAINS ' year'))
                                     AND NOT (chunk_text_lc STARTS WITH 'next ' AND (chunk_text_lc CONTAINS ' day' OR chunk_text_lc CONTAINS ' week' OR chunk_text_lc CONTAINS ' month' OR chunk_text_lc CONTAINS ' year'))
                 WITH nc,
                     CASE WHEN coalesce(toString(d.id), split(nc.id, '_')[1], '0') =~ '^[0-9]+$'
                         THEN toInteger(coalesce(toString(d.id), split(nc.id, '_')[1], '0'))
                         ELSE 0 END AS doc_id,
                     min_tok AS start_tok,
                     max_tok AS end_tok,
                     min_char AS start_char,
                     max_char AS end_char
                 WITH nc, doc_id, start_tok, end_tok, start_char, end_char,
                     'nominal_chunk_' + toString(doc_id) + '_' + toString(start_tok) + '_' + toString(end_tok) AS entity_id,
                     'nom_mention_nc_' + toString(doc_id) + '_' + toString(start_tok) + '_' + toString(end_tok) AS mention_id,
                     coalesce(nc.syntactic_type, nc.syntacticType, 'NOM') AS syntactic_type
                 MERGE (e:Entity {id: entity_id, type: 'NOMINAL'})
                 SET e.syntacticType = syntactic_type,
                                     e.syntactic_type = syntactic_type,
                    e.head = coalesce(e.head, nc.value),
                    e.start_tok = start_tok,
                    e.end_tok = end_tok,
                    e.start_char = start_char,
                    e.end_char = end_char,
                    e.text = coalesce(e.text, nc.value),
                    e.source = 'noun_chunk_nominal',
                    e.source_noun_chunk_id = nc.id,
                    e.provenance_rule_id = 'refinement.materialize_nominal_mentions_from_noun_chunks'
                 RETURN DISTINCT
                    e.id AS entity_id,
                    nc.id AS source_noun_chunk_id,
                    doc_id,
                    coalesce(nc.value, '') AS value,
                    coalesce(e.head, nc.value) AS head,
                    start_tok AS headTokenIndex,
                    start_tok,
                    end_tok,
                    start_char,
                    end_char,
                    syntactic_type,
                    mention_id
        """
        rows = graph.run(candidate_query).data()
        self._merge_nominal_entity_mentions(
            rows=rows,
            mention_source="nc",
            source_key="source_noun_chunk_id",
            confidence=0.75,
            provenance_rule_id="refinement.materialize_nominal_mentions_from_noun_chunks",
        )

        return ""


    def resolve_nominal_semantic_heads(self):
        """Resolve noun-preferred semantic heads for nominal mentions.

        Surface heads from spaCy are preserved in the original `head` fields.
        This pass adds a second, semantics-oriented head profile that prefers
        noun-like tokens over modifiers, quantifiers, and determiners.
        """
        logger.debug("resolve_nominal_semantic_heads")
        graph = self.graph

        query = """
                 MATCH (em:EntityMention:NominalMention)
                 OPTIONAL MATCH (tok:TagOccurrence)-[:IN_MENTION|PARTICIPATES_IN]->(em)
                 WITH em, tok,
                      CASE
                          WHEN tok IS NULL THEN 99
                          WHEN coalesce(tok.upos, '') IN ['NOUN', 'PROPN', 'PRON'] THEN 0
                          WHEN coalesce(tok.pos, '') IN ['NN', 'NNS', 'NNP', 'NNPS', 'PRP', 'PRP$'] THEN 1
                          WHEN coalesce(tok.upos, '') = 'ADJ' OR coalesce(tok.pos, '') IN ['JJ', 'JJR', 'JJS'] THEN 4
                          WHEN coalesce(tok.upos, '') = 'NUM' OR coalesce(tok.pos, '') = 'CD' THEN 5
                          WHEN coalesce(tok.upos, '') = 'DET' OR coalesce(tok.pos, '') IN ['DT', 'PDT', 'WDT'] THEN 6
                          ELSE 3
                      END AS lexical_rank,
                      abs(coalesce(tok.tok_index_doc, coalesce(em.end_tok, em.start_tok)) - coalesce(em.end_tok, em.start_tok)) AS right_edge_distance,
                      CASE
                          WHEN coalesce(tok.tok_index_doc, -1) = coalesce(em.headTokenIndex, em.end_tok, em.start_tok) THEN 0
                          ELSE 1
                      END AS surface_head_penalty
                 ORDER BY em.id, lexical_rank ASC, right_edge_distance ASC, surface_head_penalty ASC, coalesce(tok.tok_index_doc, -1) DESC
                 WITH em, head(collect(tok)) AS semantic_head
                 OPTIONAL MATCH (em)-[:REFERS_TO]->(e:Entity)
                 SET em.nominalSemanticHead = coalesce(semantic_head.lemma, semantic_head.text, em.head, em.value),
                     em.nominalSemanticHeadLemma = coalesce(semantic_head.lemma, semantic_head.text, em.head),
                     em.nominalSemanticHeadText = coalesce(semantic_head.text, em.head, em.value),
                     em.nominalSemanticHeadPos = coalesce(semantic_head.pos, ''),
                     em.nominalSemanticHeadUpos = coalesce(semantic_head.upos, ''),
                     em.nominalSemanticHeadTokenIndex = coalesce(semantic_head.tok_index_doc, em.headTokenIndex, em.end_tok, em.start_tok),
                     em.nominalSemanticHeadSource = CASE
                         WHEN semantic_head IS NULL THEN 'fallback_existing_head'
                         WHEN semantic_head.tok_index_doc = coalesce(em.headTokenIndex, em.end_tok, em.start_tok) THEN 'surface_head'
                         ELSE 'noun_preferred_token'
                     END
                 SET e.nominalSemanticHead = coalesce(e.nominalSemanticHead, coalesce(semantic_head.lemma, semantic_head.text, em.head, em.value)),
                     e.nominalSemanticHeadLemma = coalesce(e.nominalSemanticHeadLemma, coalesce(semantic_head.lemma, semantic_head.text, em.head)),
                     e.nominalSemanticHeadText = coalesce(e.nominalSemanticHeadText, coalesce(semantic_head.text, em.head, em.value)),
                     e.nominalSemanticHeadPos = coalesce(e.nominalSemanticHeadPos, coalesce(semantic_head.pos, '')),
                     e.nominalSemanticHeadUpos = coalesce(e.nominalSemanticHeadUpos, coalesce(semantic_head.upos, '')),
                     e.nominalSemanticHeadTokenIndex = coalesce(e.nominalSemanticHeadTokenIndex, coalesce(semantic_head.tok_index_doc, em.headTokenIndex, em.end_tok, em.start_tok)),
                     e.nominalSemanticHeadSource = coalesce(e.nominalSemanticHeadSource,
                         CASE
                             WHEN semantic_head IS NULL THEN 'fallback_existing_head'
                             WHEN semantic_head.tok_index_doc = coalesce(em.headTokenIndex, em.end_tok, em.start_tok) THEN 'surface_head'
                             ELSE 'noun_preferred_token'
                         END)
                 RETURN count(DISTINCT em) AS nominals_resolved
        """
        graph.run(query).data()

        return ""


    def annotate_nominal_semantic_profiles(self):
        """Annotate nominal mentions/entities with semantic and evaluation hints.

        This is additive metadata only. It does not remove or relabel mentions.
        The goal is to preserve semantic richness in the graph while making it
        possible for evaluation to filter nominal views explicitly.
        """
        logger.debug("annotate_nominal_semantic_profiles")
        graph = self.graph

        query = """
                 MATCH (em:EntityMention:NominalMention)
                 OPTIONAL MATCH (head_tok:TagOccurrence)-[:IN_MENTION|PARTICIPATES_IN]->(em)
                  WHERE head_tok.tok_index_doc = coalesce(em.nominalSemanticHeadTokenIndex, em.headTokenIndex, em.end_tok, em.start_tok)
                 WITH em, head(collect(head_tok)) AS head_tok
                 OPTIONAL MATCH (arg_tok:TagOccurrence)-[:IN_MENTION|PARTICIPATES_IN]->(em)
                 OPTIONAL MATCH (arg_tok)-[:IN_FRAME]->(fa:FrameArgument)
                 WITH em, head_tok,
                      count(DISTINCT CASE WHEN fa.type IN ['ARG0', 'ARG1', 'ARG2'] THEN fa END) AS core_arg_hits
                 OPTIONAL MATCH (head_tok)-[:TRIGGERS]->(evt:TEvent)
                 WHERE evt.doc_id = em.doc_id
                 WITH em, head_tok, core_arg_hits, count(DISTINCT evt) > 0 AS event_trigger
                 OPTIONAL MATCH (em)-[:REFERS_TO]->(e:Entity)<-[:REFERS_TO]-(other:EntityMention)
                 WHERE other <> em
                 WITH em, head_tok, core_arg_hits, event_trigger,
                      count(DISTINCT other) + 1 AS mention_cluster_size
                 OPTIONAL MATCH (em)-[:REFERS_TO]->(e:Entity)<-[:REFERS_TO]-(ne:NamedEntity)
                 WITH em, head_tok, core_arg_hits, event_trigger, mention_cluster_size,
                      count(DISTINCT ne) > 0 AS has_named_link,
                      coalesce(head_tok.wnLexname, '') AS head_wn_lexname,
                                            toLower(coalesce(em.nominalSemanticHeadLemma, head_tok.lemma, head_tok.text, em.head, em.value, '')) AS head_lemma_lc,
                      any(h IN coalesce(head_tok.hypernyms, [])
                          WHERE toLower(h) STARTS WITH 'event.n.'
                             OR toLower(h) STARTS WITH 'act.n.'
                             OR toLower(h) STARTS WITH 'process.n.'
                             OR toLower(h) STARTS WITH 'state.n.'
                             OR toLower(h) STARTS WITH 'phenomenon.n.') AS wordnet_eventive,
                      coalesce(head_tok.pos, '') IN ['NNP', 'NNPS'] AS proper_like
                  WITH em, core_arg_hits, mention_cluster_size, has_named_link,
                                            head_wn_lexname, head_lemma_lc,
                      coalesce(head_tok.pos, '') AS head_pos,
                      coalesce(head_tok.nltkSynset, '') AS head_nltk_synset,
                      coalesce(head_tok.hypernyms, []) AS head_hypernyms,
                                            event_trigger,
                                            wordnet_eventive
                                                OR head_wn_lexname IN ['noun.event', 'noun.act', 'noun.process'] AS eventive_by_wordnet,
                                            false AS eventive_by_argument,
                                            (
                                                size(head_lemma_lc) >= 5
                                                AND head_lemma_lc =~ '.*(tion|sion|ment|ance|ence|ure|ing)$'
                                            ) AS eventive_by_morphology,
                      proper_like
                                 WITH em, core_arg_hits, mention_cluster_size, has_named_link, head_wn_lexname, head_pos, head_nltk_synset, head_hypernyms,
                                            event_trigger, eventive_by_wordnet, eventive_by_argument, eventive_by_morphology,
                                            (event_trigger OR eventive_by_wordnet OR eventive_by_argument OR eventive_by_morphology) AS eventive_head,
                                            proper_like,
                                            (CASE WHEN eventive_by_wordnet THEN 0.45 ELSE 0.0 END
                                                + CASE WHEN event_trigger THEN 0.30 ELSE 0.0 END
                                                + CASE WHEN eventive_by_argument THEN 0.15 ELSE 0.0 END
                                                + CASE WHEN eventive_by_morphology THEN 0.10 ELSE 0.0 END) AS raw_eventive_confidence,
                      CASE
                                                    WHEN (event_trigger OR eventive_by_wordnet OR eventive_by_argument OR eventive_by_morphology) THEN 'EVENT'
                          WHEN proper_like THEN 'NAM'
                          ELSE 'NOM'
                      END AS eval_layer,
                      CASE
                                                    WHEN (event_trigger OR eventive_by_wordnet OR eventive_by_argument OR eventive_by_morphology) THEN 'eventive_nominal'
                          WHEN proper_like THEN 'proper_like_nominal'
                          WHEN has_named_link OR core_arg_hits > 0 OR mention_cluster_size > 1 THEN 'salient_nominal'
                          ELSE 'background_nominal'
                      END AS eval_profile,
                      CASE
                                                    WHEN (event_trigger OR eventive_by_wordnet OR eventive_by_argument OR eventive_by_morphology) THEN false
                          WHEN proper_like THEN false
                          WHEN has_named_link OR core_arg_hits > 0 OR mention_cluster_size > 1 THEN true
                          ELSE false
                      END AS eval_candidate_gold,
                                            CASE
                                                    WHEN ((CASE WHEN eventive_by_wordnet THEN 0.45 ELSE 0.0 END
                                                        + CASE WHEN event_trigger THEN 0.30 ELSE 0.0 END
                                                        + CASE WHEN eventive_by_argument THEN 0.15 ELSE 0.0 END
                                                        + CASE WHEN eventive_by_morphology THEN 0.10 ELSE 0.0 END)) > 1.0 THEN 1.0
                                                    ELSE (CASE WHEN eventive_by_wordnet THEN 0.45 ELSE 0.0 END
                                                        + CASE WHEN event_trigger THEN 0.30 ELSE 0.0 END
                                                        + CASE WHEN eventive_by_argument THEN 0.15 ELSE 0.0 END
                                                        + CASE WHEN eventive_by_morphology THEN 0.10 ELSE 0.0 END)
                                            END AS eventive_confidence,
                      [signal IN [
                                                 CASE WHEN (event_trigger OR eventive_by_wordnet OR eventive_by_argument OR eventive_by_morphology) THEN 'eventive_head' ELSE null END,
                                                 CASE WHEN eventive_by_wordnet THEN 'eventive_wordnet' ELSE null END,
                                                 CASE WHEN eventive_by_argument THEN 'eventive_argument_structure' ELSE null END,
                                                 CASE WHEN eventive_by_morphology THEN 'eventive_morphology' ELSE null END,
                         CASE WHEN head_wn_lexname IN ['noun.event', 'noun.act', 'noun.phenomenon', 'noun.process', 'noun.state'] THEN 'wordnet_eventive_lexname' ELSE null END,
                         CASE WHEN event_trigger THEN 'event_trigger' ELSE null END,
                         CASE WHEN proper_like THEN 'proper_like' ELSE null END,
                         CASE WHEN has_named_link THEN 'named_link' ELSE null END,
                         CASE WHEN core_arg_hits > 0 THEN 'core_argument' ELSE null END,
                         CASE WHEN mention_cluster_size > 1 THEN 'multi_mention_cluster' ELSE null END
                      ] WHERE signal IS NOT NULL] AS semantic_signals
                 OPTIONAL MATCH (em)-[:REFERS_TO]->(e:Entity)
                 SET em.nominalHeadPos = head_pos,
                     em.nominalHeadNltkSynset = head_nltk_synset,
                     em.nominalHeadHypernyms = head_hypernyms,
                     em.nominalHeadWnLexname = head_wn_lexname,
                     em.nominalEventiveHead = eventive_head,
                     em.nominalEventiveByWordNet = eventive_by_wordnet,
                     em.nominalEventiveByTrigger = event_trigger,
                     em.nominalEventiveByArgumentStructure = eventive_by_argument,
                     em.nominalEventiveByMorphology = eventive_by_morphology,
                     em.nominalEventiveConfidence = eventive_confidence,
                     em.nominalProperLike = proper_like,
                     em.nominalHasNamedLink = has_named_link,
                     em.nominalCoreArgument = core_arg_hits > 0,
                     em.nominalClusterSize = mention_cluster_size,
                     em.nominalEvalLayerSuggestion = eval_layer,
                     em.nominalEvalProfile = eval_profile,
                     em.nominalEvalCandidateGold = eval_candidate_gold,
                     em.isSalientNominal = (
                         has_named_link
                         OR event_trigger
                         OR ((core_arg_hits > 0) AND eventive_confidence >= 0.40)
                     ),
                     em.nominalSemanticSignals = semantic_signals
                 SET e.nominalHeadPos = coalesce(e.nominalHeadPos, head_pos),
                     e.nominalHeadNltkSynset = coalesce(e.nominalHeadNltkSynset, head_nltk_synset),
                     e.nominalHeadHypernyms = CASE WHEN size(coalesce(e.nominalHeadHypernyms, [])) > 0 THEN e.nominalHeadHypernyms ELSE head_hypernyms END,
                     e.nominalHeadWnLexname = coalesce(e.nominalHeadWnLexname, head_wn_lexname),
                     e.nominalEventiveHead = coalesce(e.nominalEventiveHead, false) OR eventive_head,
                     e.nominalEventiveByWordNet = coalesce(e.nominalEventiveByWordNet, false) OR eventive_by_wordnet,
                     e.nominalEventiveByTrigger = coalesce(e.nominalEventiveByTrigger, false) OR event_trigger,
                     e.nominalEventiveByArgumentStructure = coalesce(e.nominalEventiveByArgumentStructure, false) OR eventive_by_argument,
                     e.nominalEventiveByMorphology = coalesce(e.nominalEventiveByMorphology, false) OR eventive_by_morphology,
                     e.nominalEventiveConfidence = CASE
                         WHEN coalesce(e.nominalEventiveConfidence, 0.0) > eventive_confidence THEN e.nominalEventiveConfidence
                         ELSE eventive_confidence
                     END,
                     e.nominalProperLike = coalesce(e.nominalProperLike, false) OR proper_like,
                     e.nominalHasNamedLink = coalesce(e.nominalHasNamedLink, false) OR has_named_link,
                     e.nominalCoreArgument = coalesce(e.nominalCoreArgument, false) OR core_arg_hits > 0,
                     e.nominalClusterSize = CASE
                         WHEN coalesce(e.nominalClusterSize, 0) > mention_cluster_size THEN e.nominalClusterSize
                         ELSE mention_cluster_size
                     END,
                     e.nominalEvalLayerSuggestion = coalesce(e.nominalEvalLayerSuggestion, eval_layer),
                     e.nominalEvalProfile = coalesce(e.nominalEvalProfile, eval_profile),
                     e.nominalEvalCandidateGold = coalesce(e.nominalEvalCandidateGold, eval_candidate_gold),
                     e.isSalientNominal = coalesce(e.isSalientNominal, false)
                         OR has_named_link
                         OR event_trigger
                         OR ((core_arg_hits > 0) AND eventive_confidence >= 0.40)
                 RETURN count(DISTINCT em) AS nominals_profiled
        """
        graph.run(query).data()

        eval_span_query = """
                 MATCH (em:EntityMention:NominalMention)
                 WHERE em.start_tok IS NOT NULL AND em.end_tok IS NOT NULL
                 OPTIONAL MATCH (start_tok:TagOccurrence)-[:IN_MENTION|PARTICIPATES_IN]->(em)
                  WHERE start_tok.tok_index_doc = em.start_tok
                 OPTIONAL MATCH (end_tok:TagOccurrence)-[:IN_MENTION|PARTICIPATES_IN]->(em)
                  WHERE end_tok.tok_index_doc = em.end_tok
                 WITH em,
                      coalesce(em.nominalSemanticHeadTokenIndex, em.headTokenIndex, em.end_tok, em.start_tok) AS head_idx,
                      CASE
                          WHEN em.start_tok < em.end_tok
                               AND (
                                   coalesce(start_tok.upos, '') = 'DET'
                                   OR coalesce(start_tok.pos, '') IN ['DT', 'PDT', 'WDT']
                               )
                          THEN em.start_tok + 1
                          ELSE em.start_tok
                      END AS eval_start,
                      CASE
                          WHEN em.end_tok > em.start_tok
                               AND (
                                   coalesce(end_tok.upos, '') = 'PUNCT'
                                   OR coalesce(end_tok.pos, '') IN ['.', ',', ':', ';', '``', "''"]
                               )
                          THEN em.end_tok - 1
                          ELSE em.end_tok
                      END AS eval_end
                 WITH em,
                      CASE WHEN head_idx < eval_start THEN head_idx ELSE eval_start END AS final_start,
                      head_idx AS final_end
                 OPTIONAL MATCH (em)-[:REFERS_TO]->(e:Entity)
                 SET em.nominalEvalStartTok = final_start,
                     em.nominalEvalEndTok = final_end,
                     em.nominalEvalHasContraction = (final_start <> em.start_tok OR final_end <> em.end_tok),
                     e.nominalEvalStartTok = coalesce(e.nominalEvalStartTok, final_start),
                     e.nominalEvalEndTok = coalesce(e.nominalEvalEndTok, final_end)
                 RETURN count(DISTINCT em) AS nominals_eval_spans
        """
        graph.run(eval_span_query).data()

        return ""


    # Link FA to Entity by using their links with NamedEntities. path = FA --> NE --> E  implies FA --> E
    def link_frameArgument_to_entity_via_named_entity(self):
        """Propagate Entity links from NamedEntity targets to FrameArguments.

        If a FrameArgument refers to a NamedEntity which in turn refers to an
        Entity, this method creates a direct REFERS_TO edge between the FA
        and the Entity. Useful to flatten indirection and make entity
        attributes accessible to FA-based enrichment.
        """
        logger.debug("link_frameArgument_to_entity_via_named_entity")
        graph = self.graph

        query = """    
                        match p = (fa:FrameArgument)-[:REFERS_TO]->(ne:NamedEntity)-[:REFERS_TO]-(e:Entity)
                        merge (fa)-[:REFERS_TO]-(e)
                        return p     
        
        """
        data= graph.run(query).data()
        
        return ""


    #//It connects frame argument to numeric entities.
    #//PRECONDITION: query 'detect_quantified_entities_from_frameArgument' in refinment phase must be run before this. 
    #//Because, cases like 'millions of people' actually refering to nominal rather numeric
    #//It checks that frame argument is not yet connected to entity. If it exists it means it is a case about quantified entities. 
    def link_frameArgument_to_numeric_entities(self):
        """Link FrameArguments to numeric NamedEntity nodes.

        Connects FAs whose head token matches a numeric-type NamedEntity
        (MONEY, QUANTITY, PERCENT) and which are not already linked to a
        generic Entity or canonical VALUE node.  Canonical VALUE nodes are
        preferred: when the NamedEntity has a REFERS_TO -> VALUE chain, the FA
        is linked to the VALUE node instead of the NamedEntity directly.

        No longer relies on the legacy :NUMERIC dynamic label.  The type-based
        filter on ``ne.type`` is the canonical way to identify numeric mentions
        without requiring a prior label-writing pass.
        """
        logger.debug("link_frameArgument_to_numeric_entities")
        graph = self.graph

        # Prefer canonical VALUE target; fall back to raw NamedEntity when no
        # VALUE node has been materialized yet (e.g. early-phase runs).
        query = """
            MATCH (f:FrameArgument)<-[:IN_FRAME]-(t:TagOccurrence)
                -[:IN_MENTION]->(ne:NamedEntity)
            WHERE ne.type IN ['MONEY', 'QUANTITY', 'PERCENT']
              AND f.headTokenIndex = t.tok_index_doc
              AND NOT exists((f)-[:REFERS_TO]->(:Entity))
            OPTIONAL MATCH (ne)-[:REFERS_TO]->(v:VALUE)
            WITH f, ne, v
            FOREACH (ignored IN CASE WHEN v IS NOT NULL THEN [1] ELSE [] END |
                MERGE (f)-[:REFERS_TO]->(v)
            )
            FOREACH (ignored IN CASE WHEN v IS NULL THEN [1] ELSE [] END |
                MERGE (f)-[:REFERS_TO]->(ne)
            )
            RETURN count(f) AS linked
        """
        data = graph.run(query).data()
        linked = data[0].get("linked", 0) if data else 0
        logger.debug("link_frameArgument_to_numeric_entities: linked %d frame arguments", linked)
        return ""

    # ------------------------------------------------------------------
    # Phase 3 — NAF-compliant syntactic type correction
    # ------------------------------------------------------------------

    def assign_meantime_syntactic_types(self):
        """Correct syntactic_type on NamedEntity nodes using NAF-compliant rules.

        Rules applied (idempotent — safe to re-run):
        - PRP / PRP$ / WP / WP$ or upos=PRON  → PRO
        - NNP / NNPS                            → NAM
        - NN / NNS                              → NOM
        - DT / PDT / WDT / CD                  → PTV
        Nodes already typed as APP / CONJ / ARC by dep-structure rules are
        intentionally not overridden.
        """
        logger.debug("assign_meantime_syntactic_types")
        graph = self.graph

        query = """
            MATCH (ne:NamedEntity)
            WHERE ne.headTokenIndex IS NOT NULL
              AND NOT coalesce(ne.stale, false)
              AND NOT coalesce(ne.syntactic_type, '') IN ['APP', 'CONJ', 'ARC']
            MATCH (tok:TagOccurrence)-[:IN_MENTION|PARTICIPATES_IN]->(ne)
            WHERE tok.tok_index_doc = ne.headTokenIndex
            WITH ne, head(collect(tok)) AS head_tok
            WITH ne,
                 coalesce(head_tok.pos, '')  AS head_pos,
                 coalesce(head_tok.upos, '') AS upos
            WITH ne, head_pos, upos,
                 CASE
                     WHEN head_pos IN ['PRP', 'PRP$', 'WP', 'WP$'] OR upos = 'PRON' THEN 'PRO'
                     WHEN head_pos IN ['NNP', 'NNPS']                                THEN 'NAM'
                     WHEN head_pos IN ['NN', 'NNS']                                  THEN 'NOM'
                     WHEN head_pos IN ['DT', 'PDT', 'WDT', 'CD']                    THEN 'PTV'
                     ELSE coalesce(ne.syntactic_type, 'NAM')
                 END AS new_stype,
                 CASE
                     WHEN head_pos IN ['PRP', 'PRP$', 'WP', 'WP$'] OR upos = 'PRON' THEN 'PRO'
                     WHEN head_pos IN ['NNP', 'NNPS']                                THEN 'NAM'
                     WHEN head_pos IN ['NN', 'NNS']                                  THEN 'NOMINAL'
                     WHEN head_pos IN ['DT', 'PDT', 'WDT', 'CD']                    THEN 'PTV'
                     ELSE coalesce(ne.syntacticType, 'NAM')
                 END AS new_syntacticType
            SET ne.syntactic_type = new_stype,
                ne.syntacticType  = new_syntacticType
            RETURN count(ne) AS updated
        """
        data = graph.run(query).data()
        updated = data[0].get("updated", 0) if data else 0
        logger.info("assign_meantime_syntactic_types: updated %d NamedEntity nodes", updated)
        return ""

    # ------------------------------------------------------------------
    # Phase 4 — Hybrid dep-parse nominal extraction
    # ------------------------------------------------------------------

    def materialize_predicate_nominal_mentions(self):
        """Create NominalMention nodes for predicate nominatives (attr dep).

        Pattern: [verb: be/become/remain] -[:IS_DEPENDENT {type:'attr'}]-> [noun]
        Creates EntityMention:NominalMention for the noun head when no
        NamedEntity or EntityMention already covers it.  Syntactic type is
        set to NAM for NNP/NNPS heads, NOM otherwise.
        """
        logger.debug("materialize_predicate_nominal_mentions")
        graph = self.graph

        query = """
            MATCH (doc:AnnotatedText)-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(head_tok:TagOccurrence)
            MATCH (verb_tok:TagOccurrence)-[:IS_DEPENDENT {type: 'attr'}]->(head_tok)
            WHERE head_tok.pos IN ['NN', 'NNS', 'NNP', 'NNPS']
              AND toLower(coalesce(verb_tok.lemma, verb_tok.text, '')) IN ['be', 'become', 'remain', 'stay']
            OPTIONAL MATCH (ne:NamedEntity)-[:IN_MENTION|PARTICIPATES_IN]-(head_tok)
            WHERE NOT coalesce(ne.stale, false)
            WITH doc, head_tok, count(ne) AS ne_cov
            WHERE ne_cov = 0
            OPTIONAL MATCH (em:EntityMention)-[:IN_MENTION|PARTICIPATES_IN]-(head_tok)
            WITH doc, head_tok, ne_cov, count(em) AS em_cov
            WHERE em_cov = 0
            WITH doc, head_tok,
                 toInteger(doc.id) AS doc_id,
                 'pred_nom_' + toString(doc.id) + '_' + toString(head_tok.tok_index_doc) AS em_id,
                 CASE WHEN head_tok.pos IN ['NNP', 'NNPS'] THEN 'NAM' ELSE 'NOM' END AS stype
            WITH doc, head_tok, doc_id, em_id, stype,
                 CASE WHEN stype = 'NAM' THEN 'NAM' ELSE 'NOMINAL' END AS legacy_stype
            MERGE (em:EntityMention:NominalMention {id: em_id})
            SET em.doc_id          = doc_id,
                em.value           = head_tok.text,
                em.head            = head_tok.text,
                em.headTokenIndex  = head_tok.tok_index_doc,
                em.start_tok       = head_tok.tok_index_doc,
                em.end_tok         = head_tok.tok_index_doc,
                em.syntactic_type  = stype,
                em.syntacticType   = legacy_stype,
                em.source          = 'pred_nominal',
                em.confidence      = 0.75,
                em.provenance_rule_id = 'refinement.materialize_predicate_nominal_mentions'
            MERGE (head_tok)-[:IN_MENTION]->(em)
            RETURN count(DISTINCT em) AS created
        """
        data = graph.run(query).data()
        created = data[0].get("created", 0) if data else 0
        logger.info("materialize_predicate_nominal_mentions: created %d mentions", created)
        return ""

    def materialize_appositive_mentions(self):
        """Create NominalMention nodes for appositive phrases (appos dep).

        Pattern: [parent noun] -[:IS_DEPENDENT {type:'appos'}]-> [appositive noun]
        The appositive head receives syntactic_type=APP (or NAM if NNP/NNPS).
        Skipped when a NamedEntity or EntityMention already covers the head token.
        """
        logger.debug("materialize_appositive_mentions")
        graph = self.graph

        query = """
            MATCH (doc:AnnotatedText)-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(head_tok:TagOccurrence)
            MATCH (parent_tok:TagOccurrence)-[:IS_DEPENDENT {type: 'appos'}]->(head_tok)
            WHERE head_tok.pos IN ['NN', 'NNS', 'NNP', 'NNPS']
            OPTIONAL MATCH (ne:NamedEntity)-[:IN_MENTION|PARTICIPATES_IN]-(head_tok)
            WHERE NOT coalesce(ne.stale, false)
            WITH doc, head_tok, count(ne) AS ne_cov
            WHERE ne_cov = 0
            OPTIONAL MATCH (em:EntityMention)-[:IN_MENTION|PARTICIPATES_IN]-(head_tok)
            WITH doc, head_tok, ne_cov, count(em) AS em_cov
            WHERE em_cov = 0
            WITH doc, head_tok,
                 toInteger(doc.id) AS doc_id,
                 'appos_' + toString(doc.id) + '_' + toString(head_tok.tok_index_doc) AS em_id,
                 CASE WHEN head_tok.pos IN ['NNP', 'NNPS'] THEN 'NAM' ELSE 'APP' END AS stype
            WITH doc, head_tok, doc_id, em_id, stype,
                 CASE WHEN stype = 'NAM' THEN 'NAM' WHEN stype = 'APP' THEN 'APP' ELSE 'NOMINAL' END AS legacy_stype
            MERGE (em:EntityMention:NominalMention {id: em_id})
            SET em.doc_id          = doc_id,
                em.value           = head_tok.text,
                em.head            = head_tok.text,
                em.headTokenIndex  = head_tok.tok_index_doc,
                em.start_tok       = head_tok.tok_index_doc,
                em.end_tok         = head_tok.tok_index_doc,
                em.syntactic_type  = stype,
                em.syntacticType   = legacy_stype,
                em.source          = 'appositive',
                em.confidence      = 0.80,
                em.provenance_rule_id = 'refinement.materialize_appositive_mentions'
            MERGE (head_tok)-[:IN_MENTION]->(em)
            RETURN count(DISTINCT em) AS created
        """
        data = graph.run(query).data()
        created = data[0].get("created", 0) if data else 0
        logger.info("materialize_appositive_mentions: created %d mentions", created)
        return ""

    def materialize_event_argument_mentions(self):
        """Ensure EventMention arguments (nsubj/dobj/nsubjpass) have EntityMention coverage.

        For every TEvent whose head token governs an nsubj or dobj dependent
        that is a NN/NNS/NNP/NNPS token without existing NamedEntity or EntityMention
        coverage, create a NominalMention.  This is the highest-KG-impact rule since
        event arguments are exactly the entities needed for temporal reasoning.
        """
        logger.debug("materialize_event_argument_mentions")
        graph = self.graph

        query = """
            MATCH (doc:AnnotatedText)-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(evt_tok:TagOccurrence)
            MATCH (evt_tok)-[:TRIGGERS]->(event:TEvent)
            MATCH (evt_tok)-[:IS_DEPENDENT {type: $dep_type}]->(arg_tok:TagOccurrence)
            WHERE arg_tok.pos IN ['NN', 'NNS', 'NNP', 'NNPS']
            OPTIONAL MATCH (ne:NamedEntity)-[:IN_MENTION|PARTICIPATES_IN]-(arg_tok)
            WHERE NOT coalesce(ne.stale, false)
            WITH doc, arg_tok, event, $dep_type AS dep_type, count(ne) AS ne_cov
            WHERE ne_cov = 0
            OPTIONAL MATCH (em:EntityMention)-[:IN_MENTION|PARTICIPATES_IN]-(arg_tok)
            WITH doc, arg_tok, event, dep_type, ne_cov, count(em) AS em_cov
            WHERE em_cov = 0
            WITH doc, arg_tok, event, dep_type,
                 toInteger(doc.id) AS doc_id,
                 'evt_arg_' + dep_type + '_' + toString(doc.id) + '_' + toString(arg_tok.tok_index_doc) AS em_id,
                 CASE WHEN arg_tok.pos IN ['NNP', 'NNPS'] THEN 'NAM' ELSE 'NOM' END AS stype
            WITH doc, arg_tok, event, dep_type, doc_id, em_id, stype,
                 CASE WHEN stype = 'NAM' THEN 'NAM' ELSE 'NOMINAL' END AS legacy_stype
            MERGE (em:EntityMention:NominalMention {id: em_id})
            SET em.doc_id          = doc_id,
                em.value           = arg_tok.text,
                em.head            = arg_tok.text,
                em.headTokenIndex  = arg_tok.tok_index_doc,
                em.start_tok       = arg_tok.tok_index_doc,
                em.end_tok         = arg_tok.tok_index_doc,
                em.syntactic_type  = stype,
                em.syntacticType   = legacy_stype,
                em.source          = 'event_argument_' + dep_type,
                em.confidence      = 0.80,
                em.provenance_rule_id = 'refinement.materialize_event_argument_mentions'
            MERGE (arg_tok)-[:IN_MENTION]->(em)
            MERGE (event)-[:HAS_PARTICIPANT]->(em)
            RETURN count(DISTINCT em) AS created
        """
        total = 0
        for dep_type in ("nsubj", "dobj", "nsubjpass"):
            data = graph.run(query, {"dep_type": dep_type}).data()
            n = data[0].get("created", 0) if data else 0
            total += n
            logger.debug("materialize_event_argument_mentions dep=%s created=%d", dep_type, n)
        logger.info("materialize_event_argument_mentions: total %d mentions created", total)
        return ""



if __name__ == '__main__':
    tp= RefinementPhase(sys.argv[1:])
    tp.run_all_rule_families()

    # Record a lightweight run marker in the database so we can detect that
    # the refinement sequence was executed. This is intentionally minimal: a
    # single node with a timestamp and the list of passes we ran. It is safe
    # to run repeatedly (MERGE by id) and useful for audits / CI checks.
    try:
        try:
            from textgraphx.time_utils import utc_iso_now
        except ImportError:  # pragma: no cover - support script-style execution
            from time_utils import utc_iso_now

        run_id = utc_iso_now()
        passes = [name for _, name in tp.iter_rule_names()]

        marker_q = """
        MERGE (r:RefinementRun {id: $id})
        SET r.timestamp = $ts, r.passes = $passes
        RETURN id(r) as result
        """
        tp.graph.run(marker_q, {"id": run_id, "ts": run_id, "passes": passes}).data()
        logger.info("Recorded RefinementRun %s with %d passes", run_id, len(passes))
    except Exception:
        logger.exception("Failed to write refinement run marker (non-fatal)")






# custom labels for non-core arguments and storing it as a node attribute: argumentType. The second step the value in the fa.argumentType 
# will be set as a label for this node. It will perform event enrichment fucntion as well as attaching propbank modifiers arguments 
# with the event node. 
# TODO: Though we have found fa nodes with duplicates content with same label or arg type but we will deal with it later. 
# 
# 
# MATCH (event:TEvent)<-[:DESCRIBES]-(f:Frame)<-[:PARTICIPANT]-(fa:FrameArgument)
# WHERE NOT (fa.type IN ['ARG0', 'ARG1', 'ARG2', 'ARG3', 'ARG4', 'ARGM-TMP'])
# WITH event, f, fa
# SET fa.argumentType=
#     CASE fa.type
#     WHEN 'ARGM-MNR' THEN 'Manner'
#     WHEN 'ARGM-ADV' THEN 'Adverbial'
#     WHEN 'ARGM-DIR' THEN 'Direction'
#     WHEN 'ARGM-DIS' THEN 'Discourse'
#     WHEN 'ARGM-LOC' THEN 'Location'
#     WHEN 'ARGM-PRP' THEN 'Purpose'
#     WHEN 'ARGM-CAU' THEN 'Cause'
#     WHEN 'ARGM-EXT' THEN 'Extent'
#     ELSE 'NonCore'
#     END
# MERGE (fa)-[r:PARTICIPANT]->(event)
# SET r.type = fa.type,
#     (CASE WHEN fa.syntacticType IN ['IN'] THEN r END).prep = fa.head 
# RETURN event, f, fa, r




#VERSION 2 of the previous query with additional propbank arguments
# MATCH (event:TEvent)<-[:DESCRIBES]-(f:Frame)<-[:PARTICIPANT]-(fa:FrameArgument)
# WHERE NOT (fa.type IN ['ARG0', 'ARG1', 'ARG2', 'ARG3', 'ARG4', 'ARGM-TMP'])
# WITH event, f, fa
# SET fa.argumentType =
#     CASE fa.type
#     WHEN 'ARGM-COM' THEN 'Comitative'
#     WHEN 'ARGM-LOC' THEN 'Locative'
#     WHEN 'ARGM-DIR' THEN 'Directional'
#     WHEN 'ARGM-GOL' THEN 'Goal'
#     WHEN 'ARGM-MNR' THEN 'Manner'
#     WHEN 'ARGM-TMP' THEN 'Temporal'
#     WHEN 'ARGM-EXT' THEN 'Extent'
#     WHEN 'ARGM-REC' THEN 'Reciprocals'
#     WHEN 'ARGM-PRD' THEN 'SecondaryPredication'
#     WHEN 'ARGM-PRP' THEN 'PurposeClauses'
#     WHEN 'ARGM-CAU' THEN 'CauseClauses'
#     WHEN 'ARGM-DIS' THEN 'Discourse'
#     WHEN 'ARGM-MOD' THEN 'Modals'
#     WHEN 'ARGM-NEG' THEN 'Negation'
#     WHEN 'ARGM-DSP' THEN 'DirectSpeech'
#     WHEN 'ARGM-ADV' THEN 'Adverbials'
#     WHEN 'ARGM-ADJ' THEN 'Adjectival'
#     WHEN 'ARGM-LVB' THEN 'LightVerb'
#     WHEN 'ARGM-CXN' THEN 'Construction'
#     ELSE 'NonCore'
#     END
# MERGE (fa)-[r:PARTICIPANT]->(event)
# SET r.type = fa.type,
#     (CASE WHEN fa.syntacticType IN ['IN'] THEN r END).prep = fa.head 
# RETURN event, f, fa, r


# 2nd step where we set the labels for the non-core fa arguments
# MATCH (fa:FrameArgument)
# WHERE fa.argumentType is not NULL
# CALL apoc.create.addLabels(id(fa), [fa.argumentType]) YIELD node
# RETURN node



##
#


#
##










    # =============== NEW LINGUISTIC REFINEMENT RULES ===============

    def project_event_polarity(self):
        """Set event polarity based on dependency graph negation."""
        logger.debug("project_event_polarity")
        query = """
        MATCH (e:EventMention)<-[:IN_MENTION]-(head:TagOccurrence)
        WHERE head.tok_index_doc = e.headTokenIndex OR e.headTokenIndex IS NULL
        MATCH (head)-[dep:IS_DEPENDENT]-(mod:TagOccurrence)
        WHERE dep.type = 'neg'
        SET e.polarity = "NEG"
        """
        self.graph.run(query)

    def project_event_tense_aspect(self):
        """Set event tense based on dependency graph auxiliaries."""
        logger.debug("project_event_tense_aspect")
        query = """
        MATCH (e:EventMention)<-[:IN_MENTION]-(head:TagOccurrence)
        WHERE head.tok_index_doc = e.headTokenIndex OR e.headTokenIndex IS NULL
        MATCH (head)-[dep:IS_DEPENDENT]-(mod:TagOccurrence)
        WHERE dep.type IN ['aux', 'auxpass']
        WITH e, collect(toLower(mod.text)) as aux_words
        SET e.tense = CASE 
            WHEN any(w IN aux_words WHERE w IN ['was', 'were', 'had', 'did', 'been']) THEN 'PAST'
            WHEN any(w IN aux_words WHERE w IN ['will', 'shall', 'would', 'could']) THEN 'FUTURE'
            ELSE coalesce(e.tense, 'PRESENT') END,
            e.aspect = CASE 
            WHEN any(w IN aux_words WHERE w IN ['is', 'are', 'am', 'was', 'were', 'be', 'been']) AND e.value ENDS WITH 'ing' THEN 'PROGRESSIVE'
            WHEN any(w IN aux_words WHERE w IN ['has', 'have', 'had']) THEN 'PERFECTIVE'
            ELSE coalesce(e.aspect, 'NONE') END
        """
        self.graph.run(query)

    def trim_determiners_from_mentions(self):
        """Remove determiner tokens from the boundaries of Mentions."""
        logger.debug("trim_determiners_from_mentions")
        query = """
        MATCH (m)
        WHERE m:EntityMention OR m:EventMention
        MATCH (m)<-[r:IN_MENTION]-(t:TagOccurrence)
        WHERE t.pos IN ['DT', 'PRP$', 'WDT']
        // Only strip if it's currently at the boundaries
        AND (t.tok_index_doc = m.startIndex OR t.tok_index_doc = m.endIndex)
        // And ensure we don't delete the head token
        AND (m.headTokenIndex IS NULL OR t.tok_index_doc <> m.headTokenIndex)
        DELETE r
        """
        self.graph.run(query)

    def trim_punctuation_from_mentions(self):
        """Remove trailing/leading punctuation tokens from the boundaries of Mentions."""
        logger.debug("trim_punctuation_from_mentions")
        query = """
        MATCH (m)
        WHERE m:EntityMention OR m:EventMention
        MATCH (m)<-[r:IN_MENTION]-(t:TagOccurrence)
        WHERE t.pos IN ['.', ',', ':', 'HYPH', '``', "''", '-LRB-', '-RRB-']
           OR t.text =~ '^[\\\\.,;:_\\\'\\"?!\\[\\]()\\\\-]+$'
        AND (t.tok_index_doc = m.startIndex OR t.tok_index_doc = m.endIndex)
        AND (m.headTokenIndex IS NULL OR t.tok_index_doc <> m.headTokenIndex)
        DELETE r
        """
        self.graph.run(query)

    def update_mention_span_boundaries(self):
        """Recompute the startIndex, endIndex, and string value of all Mentions."""
        logger.debug("update_mention_span_boundaries")
        query = """
        MATCH (m)
        WHERE m:EntityMention OR m:EventMention
        MATCH (m)<-[:IN_MENTION]-(t:TagOccurrence)
        WITH m, t ORDER BY t.tok_index_doc
        WITH m, collect(t) AS tokens
        WHERE size(tokens) > 0
        WITH m, tokens, tokens[0].tok_index_doc AS newStart, tokens[-1].tok_index_doc AS newEnd
        WHERE m.startIndex <> newStart OR m.endIndex <> newEnd OR m.span[0] <> newStart
        SET m.startIndex = newStart,
            m.endIndex = newEnd,
            m.span = [x IN tokens | x.tok_index_doc],
            m.value = reduce(s = '', x IN tokens | CASE WHEN s = '' THEN x.text ELSE s + ' ' + x.text END)
        """
        self.graph.run(query)

    def promote_nominal_events(self):
        """Promote nominals that act as Frame heads into EventMentions."""
        logger.debug("promote_nominal_events")
        query = """
        MATCH (f:Frame)-[:IS_FRAME_OF]->(t:TagOccurrence)
        WHERE t.pos IN ['NN', 'NNS']
        AND NOT (t)-[:IN_MENTION]->(:EventMention)
        WITH f, t
        // Create the new EventMention tied to this document
        MERGE (ev:EventMention { uid: 'nom_ev_' + f.uuid })
        ON CREATE SET 
            ev.value = t.text,
            ev.startIndex = t.tok_index_doc,
            ev.endIndex = t.tok_index_doc,
            ev.span = [t.tok_index_doc],
            ev.headTokenIndex = t.tok_index_doc,
            ev.syntacticType = 'NOMINAL',
            ev.doc_id = t.doc_id
        MERGE (t)-[:IN_MENTION]->(ev)
        // Ensure the semantic frame points to this new event representation
        MERGE (f)-[:MENTIONS]->(ev)
        """
        self.graph.run(query)

    def coerce_role_based_types(self):
        """Refine generic EntityMentions serving as LOC or TMP frame arguments."""
        logger.debug("coerce_role_based_types")
        query = """
        MATCH (fa:FrameArgument)-[:PARTICIPATES_IN]->(m:EntityMention)
        WHERE fa.type IN ['ARGM-LOC', 'ARGM-TMP']
        // Only safely coerce if not already a specialized entity class
        // (Avoiding overwriting PERSON or ORGANIZATION without care)
        AND NOT m:Location AND NOT m:Timex
        WITH fa, m
        FOREACH (ignore IN CASE WHEN fa.type = 'ARGM-LOC' THEN [1] ELSE [] END |
            SET m:Location
        )
        FOREACH (ignore IN CASE WHEN fa.type = 'ARGM-TMP' THEN [1] ELSE [] END |
            SET m:Timex
        )
        """
        self.graph.run(query)

