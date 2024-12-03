class NounChunkProcessor:
    def __init__(self, db_executor):
        """
        Initialize the NounChunkProcessor with a database executor.

        Args:
            db_executor: An object responsible for executing database queries.
        """
        self.db_executor = db_executor

    def process_noun_chunks(self, doc, text_id):
        """
        Process noun chunks in a given document and store them in the database.

        Args:
            doc: A spaCy document object.
            text_id (str): The ID of the text being processed.

        Returns:
            list: A list of noun chunk dictionaries.
        """
        ncs = []
        for noun_chunk in doc.noun_chunks:
            nc = {
                'value': noun_chunk.text,
                'type': noun_chunk.label_,
                'start_index': noun_chunk.start_char,
                'end_index': noun_chunk.end_char
            }
            ncs.append(nc)
        self.store_noun_chunks(text_id, ncs)
        return ncs

    def store_noun_chunks(self, document_id, ncs):
        """
        Store noun chunks in the database.

        Args:
            document_id (str): The ID of the document.
            ncs (list): A list of noun chunk dictionaries.
        """
        nc_query = """
            UNWIND $ncs as item
            MERGE (nc:NounChunk {id: toString($documentId) + "_" + toString(item.start_index)})
            SET nc.type = item.type, nc.value = item.value, nc.index = item.start_index
            WITH nc, item as ncIndex
            MATCH (text:AnnotatedText)-[:CONTAINS_SENTENCE]->(sentence:Sentence)-[:HAS_TOKEN]->(tagOccurrence:TagOccurrence)
            WHERE text.id = $documentId AND tagOccurrence.index >= ncIndex.start_index AND tagOccurrence.index < ncIndex.end_index
            MERGE (nc)<-[:PARTICIPATES_IN]-(tagOccurrence)
        """
        self.db_executor.execute_query(nc_query, {"documentId": document_id, "ncs": ncs})

