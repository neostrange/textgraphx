class EntityDisambiguator:
    #For the purpose of mapping named entities to entity instances in our pipeline, we distinguished between two types of named entities.
#  The first type includes entities that have been successfully disambiguated and assigned a unique KBID by the entity disambiguation module.
#  These entities can be easily mapped by creating instances based on the distinct KBIDs. The second type of named entities, 
# however, are unknown to the entity disambiguation module and are assigned a NULL KBID. To map these named entities, we rely on the text of
#  the named entity's span and its assigned type, which was determined by the NER component. As a result, named entity mentions with the 
# same text value and type are considered to refer to a single entity instance.
# """
#    This class is responsible for building an entity graph by extracting entities from a document
#    and creating relationships between them.
#    """

    def __init__(self, neo4j_repository):
        self.neo4j_repository = neo4j_repository
        pass

    def disambiguate_entities(self, document_id):
        """
        Build an entity graph by extracting direct and indirect entities from a document.

        :param document_id: ID of the document to extract entities from
        """
        extract_direct_entities_query = """
            MATCH (document:AnnotatedText)
            WHERE document.id = $documentId
            WITH document
            MATCH (document)-[*3..3]->(ne:NamedEntity)
            WHERE NOT ne.type IN ['NP', 'TIME', 'ORDINAL', 'NUMBER', 'MONEY', 'DATE', 'CARDINAL', 'QUANTITY', 'PERCENT'] AND ne.kb_id IS NOT NULL
            WITH ne
            MERGE (entity:Entity {type: ne.type, kb_id:ne.kb_id, id: split(ne.kb_id, '/')[-1]})
            MERGE (ne)-[:REFERS_TO {type: "evoke"}]->(entity)
        """

        extract_indirect_entities_query = """
        MATCH (document:AnnotatedText)
            WHERE document.id = $documentId
            WITH document
            MATCH (document)-[*3..3]->(ne:NamedEntity)
            WHERE NOT ne.type IN ['NP', 'TIME', 'ORDINAL', 'MONEY', 'NUMBER', 'DATE', 'CARDINAL', 'QUANTITY', 'PERCENT'] AND ne.kb_id IS NULL
            WITH ne
            MERGE (entity:Entity {type: ne.type, kb_id:ne.value, id:ne.value})
            MERGE (ne)-[:REFERS_TO {type: "evoke"}]->(entity)
        """
        self.execute_query(extract_direct_entities_query, {"documentId": document_id})
        self.execute_query(extract_indirect_entities_query, {"documentId": document_id})


    def execute_query(self, query, params):
        result = self.neo4j_repository.execute_query(query, params)
        return result