
class TagOccurrenceQueryExecutor:
    def __init__(self, neo4j_repository):
        self.neo4j_repository = neo4j_repository
        pass

    def execute_tag_occurrence_query(self, sentence_tag_occurrences, sentence_id):
        # implement the execute_tag_occurrence_query method
        tag_occurrences = []
        for tag_occurrence in sentence_tag_occurrences:
            tag_occurrence_dict = dict(tag_occurrence)
            tag_occurrences.append(tag_occurrence_dict)
        params = {"sentence_id": sentence_id, "tag_occurrences": sentence_tag_occurrences}
        query = self.get_tag_occurrence_query(False)

        return self.neo4j_repository.execute_query_with_result_as_key(query, params)

    def get_tag_occurrence_query(self, store_tag):
        if store_tag:
            return """MATCH (sentence:Sentence) WHERE id(sentence) = $sentence_id
                WITH sentence, $tag_occurrences as tags
                FOREACH ( idx IN range(0,size(tags)-2) |
                MERGE (tagOccurrence1:TagOccurrence {id: tags[idx].id})
                SET tagOccurrence1 = tags[idx]
                MERGE (sentence)-[:HAS_TOKEN]->(tagOccurrence1)
                MERGE (tagOccurrence2:TagOccurrence {id: tags[idx + 1].id})
                SET tagOccurrence2 = tags[idx + 1]
                MERGE (sentence)-[:HAS_TOKEN]->(tagOccurrence2)
                MERGE (tagOccurrence1)-[r:HAS_NEXT {sentence: sentence.id}]->(tagOccurrence2))
                FOREACH (tagItem in [tag_occurrence IN $tag_occurrences WHERE tag_occurrence.is_stop = False] | 
                MERGE (tag:Tag {id: tagItem.lemma}) MERGE (tagOccurrence:TagOccurrence {id: tagItem.id}) MERGE (tag)<-[:REFERS_TO]-(tagOccurrence))
                RETURN id(sentence) as result
            """
        else:
            return """MATCH (sentence:Sentence) WHERE id(sentence) = $sentence_id
            WITH sentence, $tag_occurrences as tags
            FOREACH ( idx IN range(0,size(tags)-2) |
            MERGE (tagOccurrence1:TagOccurrence {id: tags[idx].id})
            SET tagOccurrence1 = tags[idx]
            MERGE (sentence)-[:HAS_TOKEN]->(tagOccurrence1)
            MERGE (tagOccurrence2:TagOccurrence {id: tags[idx + 1].id})
            SET tagOccurrence2 = tags[idx + 1]
            MERGE (sentence)-[:HAS_TOKEN]->(tagOccurrence2)
            MERGE (tagOccurrence1)-[r:HAS_NEXT {sentence: sentence.id}]->(tagOccurrence2))
            RETURN id(sentence) as result
        """