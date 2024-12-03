class SentenceCreator:
    def __init__(self, neo4j_repository):
        self.neo4j_repository = neo4j_repository
        pass

    def create_sentence_node(self, annotated_text, text_id, sentence_id, sentence):
        sentence_query = """
            MATCH (ann:AnnotatedText) WHERE ann.id = $ann_id
            MERGE (sentence:Sentence {id: $sentence_unique_id})
            SET sentence.text = $text
            MERGE (ann)-[:CONTAINS_SENTENCE]->(sentence)
            RETURN id(sentence) as result
        """
        params = {"ann_id": annotated_text, "text": sentence.text, "sentence_unique_id": str(text_id) + "_" + str(sentence_id)}
        results = self.execute_query(sentence_query, params)
        return results[0]

    def execute_query(self, query, params):
        # implement the execute_query method
        return self.neo4j_repository.execute_query(query, params)