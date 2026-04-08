import logging
from textgraphx.utils.id_utils import make_nounchunk_id

logger = logging.getLogger(__name__)


class NounChunkProcessor:
    def __init__(self, db_executor):
        """
        Initialize the NounChunkProcessor with a database executor.

        Args:
            db_executor: An object responsible for executing database queries.
        """
        self.db_executor = db_executor

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

    def process_noun_chunks(self, doc, text_id):
        """
        Process noun chunks in a given document and store them in the database.

        Args:
            doc: A spaCy document object.
            text_id (str): The ID of the text being processed.

        Returns:
            list: A list of noun chunk dictionaries.
        """
        logger.debug("process_noun_chunks called for text_id=%s", text_id)
        ncs = []
        for noun_chunk in doc.noun_chunks:
            # Use token indices for deterministic ids (Span.start/Span.end are token positions).
            token_start = noun_chunk.start
            token_end = noun_chunk.end - 1
            head_token = noun_chunk.root
            head_text = head_token.text
            head_token_index = head_token.i
            syntactic_type = self._syntactic_type_from_tag(getattr(head_token, "tag_", ""))
            nc = {
                'value': noun_chunk.text,
                'type': getattr(noun_chunk, 'label_', None) or 'NOUN_CHUNK',
                'start_index': token_start,
                'end_index': token_end,
                'start_char': noun_chunk.start_char,
                'end_char': noun_chunk.end_char,
                'head': head_text,
                'head_token_index': head_token_index,
                'syntactic_type': syntactic_type,
            }
            ncs.append(nc)
        logger.info("process_noun_chunks: extracted %d noun chunks for %s", len(ncs), text_id)
        self.store_noun_chunks(text_id, ncs)
        return ncs

    def store_noun_chunks(self, document_id, ncs):
        """
        Store noun chunks in the database.

        Args:
            document_id (str): The ID of the document.
            ncs (list): A list of noun chunk dictionaries.
        """
        # Precompute ids
        for item in ncs:
            item['id'] = make_nounchunk_id(document_id, item['start_index'])

        nc_query = """
            UNWIND $ncs as item
            MERGE (nc:NounChunk {id: item.id})
            SET nc.type = item.type, nc.value = item.value,
                nc.start_tok = item.start_index, nc.end_tok = item.end_index,
                nc.index = item.start_index,
                nc.start_char = item.start_char, nc.end_char = item.end_char,
                nc.head = item.head, nc.headTokenIndex = item.head_token_index,
                nc.syntacticType = item.syntactic_type, nc.syntactic_type = item.syntactic_type
            WITH nc, item as ncIndex
            MATCH (text:AnnotatedText)-[:CONTAINS_SENTENCE]->(sentence:Sentence)-[:HAS_TOKEN]->(tagOccurrence:TagOccurrence)
            WHERE text.id = $documentId AND tagOccurrence.tok_index_doc >= ncIndex.start_index AND tagOccurrence.tok_index_doc <= ncIndex.end_index
            MERGE (nc)<-[:PARTICIPATES_IN]-(tagOccurrence)
            MERGE (nc)<-[:IN_MENTION]-(tagOccurrence)
        """
        logger.debug("Storing %d noun chunks for document %s", len(ncs), document_id)
        self.db_executor.execute_query(nc_query, {"documentId": document_id, "ncs": ncs})

