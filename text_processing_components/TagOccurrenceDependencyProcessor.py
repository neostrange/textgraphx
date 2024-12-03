
class TagOccurrenceDependencyProcessor:
    def __init__(self, neo4j_repository):
        self.neo4j_repository = neo4j_repository
        pass

    def process_dependencies2(self, tag_occurrence_dependencies):
        tag_occurrence_query = """MATCH (source:TagOccurrence {id: $source_id})
                                    MATCH (destination:TagOccurrence {id: $destination_id})
                                    MERGE (source)-[:IS_DEPENDENT {type: $type}]->(destination)
                            """
        for dependency in tag_occurrence_dependencies:
            self.neo4j_repository.execute_query(tag_occurrence_query, dependency)

    def process_dependencies(self, tag_occurrence_dependencies):
        tag_occurrence_query = """UNWIND $dependencies as dependency
            MATCH (source:TagOccurrence {id: dependency.source})
            MATCH (destination:TagOccurrence {id: dependency.destination})
            MERGE (source)-[:IS_DEPENDENT {type: dependency.type}]->(destination)
                """
        self.neo4j_repository.execute_query_with_result_as_key(tag_occurrence_query, {"dependencies": tag_occurrence_dependencies})

    def create_tag_occurrence_dependencies(self, sentence, text_id, sentence_id):
        tag_occurrence_dependencies = [{"source": str(text_id) + "_" + str(sentence_id) + "_" + str(token.head.idx),
                                        "destination": str(text_id) + "_" + str(sentence_id) + "_" + str(token.idx),
                                        "type": token.dep_}
                                        for token in sentence]
        return tag_occurrence_dependencies
    