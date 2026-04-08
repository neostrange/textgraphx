"""EntityProcessor

Component that converts spaCy entity spans into the graph's NamedEntity
representation and writes them into Neo4j.

This module is intentionally small: it computes deterministic NamedEntity
identifiers using token indices (spaCy span.start/span.end), prepares a
lightweight JSON-like representation for each entity and stores them with a
single UNWIND/MERGE Cypher statement. The produced nodes include both the
legacy `id` value and the newer `token_id`, `token_start` and `token_end`
properties so downstream consumers can migrate gradually.

Contract and side-effects:
- Inputs: a spaCy `Doc` with entity `Span` objects (doc.ents) and a
    `document_id` string used as part of the deterministic id.
- Outputs: creates/merges `NamedEntity` nodes and `PARTICIPATES_IN`
    relationships to `TagOccurrence` nodes. Nodes will include `token_id`,
    `token_start`, `token_end` and commonly used NEL metadata when available.
"""

from textgraphx.utils.id_utils import make_ne_id, make_ne_token_id, make_ne_uid
import logging
import time

# module logger
logger = logging.getLogger(__name__)


class EntityProcessor:
    """Convert spaCy entity spans into NamedEntity nodes and persist them.

    Public methods:
    - process_entities(doc, text_id) -> list[dict]: extract entities from the
      spaCy `Doc` and return a list of dictionaries representing each NE.
    - store_entities(document_id, nes): persist a list of NE dicts into Neo4j.

    The class keeps a reference to a repository object exposing
    `execute_query(query, params)` which is used to run Cypher statements. The
    implementation purposefully precomputes deterministic ids in Python to
    avoid string-concatenated Cypher ids and to make testing easier.
    """

    def __init__(self, neo4j_repository):
        self.neo4j_repository = neo4j_repository

    @staticmethod
    def _normalize_syntactic_type(raw_type):
        t = str(raw_type or "").strip().upper()
        if not t:
            return ""
        aliases = {
            "NOMINAL": "NOM",
            "PROPER": "NAM",
            "PRONOMINAL": "PRO",
        }
        t = aliases.get(t, t)
        allowed = {"NAM", "NOM", "PRO", "PTV", "PRE", "HLS", "CONJ", "APP", "ARC"}
        return t if t in allowed else ""

    @staticmethod
    def _legacy_syntactic_type(canonical_type):
        t = str(canonical_type or "").strip().upper()
        if t == "NOM":
            return "NOMINAL"
        return t or "NOMINAL"

    @classmethod
    def _syntactic_type_from_tag(cls, tag, dep=None, raw_type=None):
        # Prefer upstream syntactic labels when present and valid.
        normalized = cls._normalize_syntactic_type(raw_type)
        if normalized:
            return normalized

        dep = str(dep or "").strip().lower()
        if dep == "appos":
            return "APP"
        if dep == "conj":
            return "CONJ"
        if dep in {"acl", "acl:relcl", "relcl", "rcmod"}:
            return "ARC"
        if dep in {"predet", "det", "nummod", "quantmod"}:
            return "PTV"
        if dep in {"attr", "acomp", "oprd", "xcomp", "ccomp"}:
            return "PRE"

        tag = (tag or "").upper()
        if tag in ("NN", "NNS"):
            return "NOM"
        if tag in ("NNP", "NNPS"):
            return "NAM"
        if tag in ("PRP", "PRP$", "WP", "WP$"):
            return "PRO"
        if tag in ("DT", "WDT", "PDT", "CD"):
            return "PTV"
        return "NOM"

    def process_entities(self, doc, text_id):
        """Extract entities from a spaCy `Doc` and prepare them for storage.

        Args:
            doc: a spaCy `Doc` object containing tokenization and entity spans.
            text_id: the document id used as part of the deterministic NE id.

        Returns:
            A list of dictionaries with keys like `value`, `type`, `start_index`,
            `end_index` and optional NEL fields when available.
        """
        logger.debug("process_entities called for text_id=%s", text_id)
        nes = []
        spans = ''
        if doc.spans.get('ents_original') is not None:
            spans = list(doc.ents) + list(doc.spans['ents_original'])
        else:
            spans = list(doc.ents)
        # spans = filter_spans(spans) - just disabled it as testing dbpedia spotlight
        for entity in spans:
            # Use token indices (spaCy token positions) for deterministic ids.
            # spaCy Span.start is the first token index, Span.end is one-past-last.
            token_start = entity.start
            token_end = entity.end - 1
            head_token = entity.root
            head_text = head_token.text
            head_token_index = head_token.i
            entity_raw_syntactic_type = getattr(entity, "syntactic_type", "")
            if not entity_raw_syntactic_type and hasattr(entity, "_"):
                try:
                    entity_raw_syntactic_type = getattr(entity._, "syntactic_type", "")
                except Exception:
                    entity_raw_syntactic_type = ""
            syntactic_type = self._syntactic_type_from_tag(
                getattr(head_token, "tag_", ""),
                dep=getattr(head_token, "dep_", ""),
                raw_type=entity_raw_syntactic_type,
            )
            legacy_syntactic_type = self._legacy_syntactic_type(syntactic_type)
            start_char = entity.start_char
            end_char = entity.end_char

            if getattr(entity, 'kb_id_', '') != '':
                ne = {
                    'value': entity.text,
                    'type': entity.label_,
                    'start_index': token_start,
                    'end_index': token_end,
                    'start_char': start_char,
                    'end_char': end_char,
                    'head': head_text,
                    'head_token_index': head_token_index,
                    'syntactic_type': syntactic_type,
                    'legacy_syntactic_type': legacy_syntactic_type,
                    'kb_id': entity.kb_id_,
                    'url_wikidata': entity.kb_id_,
                    'score': entity._.dbpedia_raw_result['@similarityScore'],
                    'normal_term': entity.text,
                    'description': entity._.dbpedia_raw_result.get('@surfaceForm')
                }
            else:
                ne = {
                    'value': entity.text,
                    'type': entity.label_,
                    'start_index': token_start,
                    'end_index': token_end,
                    'start_char': start_char,
                    'end_char': end_char,
                    'head': head_text,
                    'head_token_index': head_token_index,
                    'syntactic_type': syntactic_type,
                    'legacy_syntactic_type': legacy_syntactic_type,
                }

            nes.append(ne)
        logger.info("process_entities: extracted %d entities for text_id=%s", len(nes), text_id)
        self.store_entities(text_id, nes)
        return nes

    def store_entities(self, document_id, nes):
        """Persist a list of NamedEntity dicts into Neo4j.

        This method precomputes deterministic ids using `make_ne_id` and then
        performs a single UNWIND/MERGE Cypher update to create or update
        `NamedEntity` nodes and connect them to `TagOccurrence` nodes. The
        method sets both legacy `id` and token-based properties so consumers
        can co-exist during migration.

        Args:
            document_id: The id of the AnnotatedText document in the graph.
            nes: List of dictionaries produced by `process_entities`.
        """
        # Precompute deterministic NamedEntity ids in Python to keep id format
        # consistent and avoid inline Cypher string concatenation.
        logger.debug("store_entities called for document_id=%s with %d items", document_id, len(nes))
        for item in nes:
            start = item.get('start_index')
            end = item.get('end_index')
            ne_type = item.get('type')
            value = item.get('value', '')
            head_token_index = item.get('head_token_index')
            item['id'] = make_ne_id(document_id, start, end, ne_type)
            item['uid'] = make_ne_uid(document_id, value, head_token_index)
            # token_id uses a type-agnostic formula so it stays stable even
            # if `id` is later remapped (e.g., to a NEL canonical URI).
            item['token_id'] = make_ne_token_id(document_id, start, end)
            item['legacy_syntactic_type'] = item.get(
                'legacy_syntactic_type',
                self._legacy_syntactic_type(item.get('syntactic_type')),
            )

        ne_query = """
            UNWIND $nes as item
            OPTIONAL MATCH (legacy:NamedEntity {id: item.id})
            WITH item, legacy
            CALL {
                WITH item, legacy
                WITH item, legacy WHERE legacy IS NOT NULL
                SET legacy.uid = coalesce(legacy.uid, item.uid),
                    legacy.legacy_span_id = coalesce(legacy.legacy_span_id, legacy.id)
                RETURN legacy AS ne
                UNION
                WITH item, legacy
                WITH item WHERE legacy IS NULL
                MERGE (ne:NamedEntity {uid: item.uid})
                RETURN ne
            }
            SET ne.id = item.id, ne.legacy_span_id = coalesce(ne.legacy_span_id, item.id), ne.uid = item.uid,
            ne.type = item.type, ne.value = item.value, ne.index = item.start_index, ne.end_index = item.end_index,
            ne.kb_id = item.kb_id, ne.url_wikidata = item.url_wikidata, ne.score = item.score, ne.normal_term = item.normal_term,
            ne.description = item.description,
            ne.start_tok = item.start_index, ne.end_tok = item.end_index,
            ne.start_char = item.start_char, ne.end_char = item.end_char,
            ne.head = item.head, ne.headTokenIndex = item.head_token_index,
            ne.syntacticType = item.legacy_syntactic_type, ne.syntactic_type = item.syntactic_type,
            ne.token_id = item.token_id, ne.token_start = item.start_index, ne.token_end = item.end_index
            WITH ne, item as neIndex
            MATCH (text:AnnotatedText)-[:CONTAINS_SENTENCE]->(sentence:Sentence)-[:HAS_TOKEN]->(tagOccurrence:TagOccurrence)
            WHERE text.id = $documentId AND tagOccurrence.tok_index_doc >= neIndex.start_index AND tagOccurrence.tok_index_doc <= neIndex.end_index
            MERGE (ne)<-[:PARTICIPATES_IN]-(tagOccurrence)
            MERGE (ne)<-[:IN_MENTION]-(tagOccurrence)
        """
        logger.debug("Executing NE UNWIND query for document %s", document_id)
        self.execute_query(ne_query, {"documentId": document_id, "nes": nes})
        self._reconcile_stale_named_entities(document_id, [item["uid"] for item in nes])

    def _reconcile_stale_named_entities(self, document_id, current_uids):
        """Retire stale mention edges for NamedEntity nodes not seen in latest extraction.

        This pass is intentionally low-disruption:
        - keeps `NamedEntity.id` deterministic MERGE behavior untouched
        - marks unseen entities as stale instead of deleting nodes
        - removes only token mention-participation edges from stale nodes so
          duplicate legacy spans stop participating in downstream mention reads
        """
        current_uids = [str(x) for x in set(current_uids or []) if x is not None]
        run_id = f"ne_reextract_{int(time.time() * 1000)}"

        # Clear stale marker for entities observed in this extraction batch.
        if current_uids:
            clear_query = """
                UNWIND $current_uids AS uid
                MATCH (ne:NamedEntity {uid: uid})
                SET ne.stale = false,
                    ne.stale_reason = null,
                    ne.stale_run_id = $run_id,
                    ne.last_seen_at = timestamp()
            """
            self.execute_query(clear_query, {"current_uids": current_uids, "run_id": run_id})

        # Mark unseen entities as stale and retire mention edges for this document.
        stale_query = """
            MATCH (text:AnnotatedText {id: $documentId})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(:TagOccurrence)-[:IN_MENTION|PARTICIPATES_IN]->(ne:NamedEntity)
            WITH DISTINCT ne
            WHERE NOT coalesce(ne.uid, '') IN $current_uids
            SET ne.stale = true,
                ne.stale_reason = 'reextract_not_seen',
                ne.stale_run_id = $run_id,
                ne.stale_at = timestamp()
            WITH collect(ne) AS stale_nodes
            CALL {
                WITH stale_nodes
                UNWIND stale_nodes AS ne
                OPTIONAL MATCH (:TagOccurrence)-[r:IN_MENTION|PARTICIPATES_IN]->(ne)
                DELETE r
                RETURN count(r) AS retired_mention_edges
            }
            CALL {
                WITH stale_nodes
                UNWIND stale_nodes AS ne
                OPTIONAL MATCH (ne)-[rr:REFERS_TO]->(:Entity)
                DELETE rr
                RETURN count(rr) AS retired_refers_to_edges
            }
            RETURN size(stale_nodes) AS stale_nodes,
                   retired_mention_edges,
                   retired_refers_to_edges
        """
        rows = self.execute_query(
            stale_query,
            {
                "documentId": document_id,
                "current_uids": current_uids,
                "run_id": run_id,
            },
        )
        if rows:
            stale_nodes = rows[0].get("stale_nodes", 0)
            retired_mention_edges = rows[0].get("retired_mention_edges", 0)
            retired_refers_to_edges = rows[0].get("retired_refers_to_edges", 0)
            if stale_nodes or retired_mention_edges or retired_refers_to_edges:
                logger.info(
                    "store_entities reconciliation: marked %d stale NamedEntity nodes, retired %d mention edges, and retired %d REFERS_TO edges for document %s",
                    stale_nodes,
                    retired_mention_edges,
                    retired_refers_to_edges,
                    document_id,
                )

    def execute_query(self, query, params):
        result = self.neo4j_repository.execute_query(query, params)
        return result