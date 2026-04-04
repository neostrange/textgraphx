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

from textgraphx.utils.id_utils import make_ne_id
import logging

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
    def _syntactic_type_from_tag(tag):
        tag = (tag or "").upper()
        if tag in ("NN", "NNS"):
            return "NOMINAL"
        if tag in ("NNP", "NNPS"):
            return "NAM"
        if tag in ("PRP", "PRP$"):
            return "PRO"
        return "OTHER"

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
            syntactic_type = self._syntactic_type_from_tag(getattr(head_token, "tag_", ""))
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
            item['id'] = make_ne_id(document_id, start, end, ne_type)

        ne_query = """
            UNWIND $nes as item
            MERGE (ne:NamedEntity {id: item.id})
            SET ne.type = item.type, ne.value = item.value, ne.index = item.start_index, ne.end_index = item.end_index,
            ne.kb_id = item.kb_id, ne.url_wikidata = item.url_wikidata, ne.score = item.score, ne.normal_term = item.normal_term,
            ne.description = item.description,
            ne.start_tok = item.start_index, ne.end_tok = item.end_index,
            ne.start_char = item.start_char, ne.end_char = item.end_char,
            ne.head = item.head, ne.headTokenIndex = item.head_token_index,
            ne.syntacticType = item.syntactic_type, ne.syntactic_type = item.syntactic_type,
            ne.token_id = item.id, ne.token_start = item.start_index, ne.token_end = item.end_index
            WITH ne, item as neIndex
            MATCH (text:AnnotatedText)-[:CONTAINS_SENTENCE]->(sentence:Sentence)-[:HAS_TOKEN]->(tagOccurrence:TagOccurrence)
            WHERE text.id = $documentId AND tagOccurrence.tok_index_doc >= neIndex.start_index AND tagOccurrence.tok_index_doc <= neIndex.end_index
            MERGE (ne)<-[:PARTICIPATES_IN]-(tagOccurrence)
        """
        logger.debug("Executing NE UNWIND query for document %s", document_id)
        self.execute_query(ne_query, {"documentId": document_id, "nes": nes})

    def execute_query(self, query, params):
        result = self.neo4j_repository.execute_query(query, params)
        return result