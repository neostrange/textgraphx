import requests
from TextProcessor import Neo4jRepository  # Import the Neo4jRepository class

class EntityExtractor:
    def __init__(self, api_url, driver):
        self.api_url = api_url
        self.neo4j_repo = Neo4jRepository(driver)  # Instantiate Neo4jRepository

    def extract_entities(self, text):
        headers = {"Content-Type": "application/json"}
        data = {"text": text}
        
        response = requests.post(self.api_url, headers=headers, json=data)
        if response.status_code == 200:
            return response.json().get("entities", [])
        else:
            print("Error calling the entity extraction API:", response.status_code)
            return []

    def integrate_entities_into_db(self, entities, text_id):
        # Fetch existing NamedEntities linked to the AnnotatedText node
        existing_entities = self.fetch_named_entities(text_id)
        print("Existing Entities: ", existing_entities)  # Log the existing entities

        for entity in entities:
            start_index = entity['start']
            end_index = entity['end']
            label = entity['label']
            matched = False

            # Check for matches with existing NamedEntities
            for existing_entity in existing_entities:
                #print("Checking existing entity: ", existing_entity)  # Log each existing entity
                existing_entity = dict(existing_entity)
                ne = dict(existing_entity["ne"])
                print("ne: ", ne)
                if ne['index'] == start_index and ne['end_index'] == end_index:
                    # If a match is found, add a new label
                    add_label_query = """
                        MATCH (ne:NamedEntity {id: $id})
                        SET ne:NewLabel
                    """
                    self.neo4j_repo.execute_query(add_label_query, {"id": ne['id']})
                    matched = True
                    break

            # If no match was found, create a new NamedEntity node
            if not matched:
                create_entity_query = """
                    MERGE (ne:NamedEntity {id: toString($documentId) + "_" + toString($start_index) + "_" + toString($end_index) + "_" + toString($type)})
                    SET ne.type = $type, 
                        ne.value = $value, 
                        ne.start_index = $start_index, 
                        ne.end_index = $end_index
                    WITH ne
                    MATCH (text:AnnotatedText)-[:CONTAINS_SENTENCE]->(sentence:Sentence)-[:HAS_TOKEN]->(tagOccurrence:TagOccurrence)
                    WHERE text.id = $documentId AND tagOccurrence.index >= $start_index AND tagOccurrence.index < $end_index
                    MERGE (ne)<-[:PARTICIPATES_IN]-(tagOccurrence)
                """
                self.neo4j_repo.execute_query(create_entity_query, {
                    "documentId": text_id,
                    "start_index": start_index,
                    "end_index": end_index,
                    "type": label,
                    "value": entity['text'],  # Assuming these fields are part of the entity
                })

    def fetch_named_entities(self, document_id):
        print(f"Fetching named entities for document ID: {document_id}")  # Log the document ID
        # Convert document_id to integer if it's a string
        document_id_int = int(document_id) if isinstance(document_id, str) else document_id
        print(f"Fetching named entities for document ID: {document_id_int}")  # Log the document ID
        
        query = """
            MATCH (text:AnnotatedText)-[:CONTAINS_SENTENCE]->(sentence:Sentence)-[:HAS_TOKEN]->(tagOccurrence:TagOccurrence)-[:PARTICIPATES_IN]->(ne:NamedEntity)
            WHERE text.id = $document_id
            RETURN ne
        """
        print("Query: ", query)
        return list(self.neo4j_repo.execute_query(query, {"document_id": document_id_int}))
    
    
    def fetch_named_entities2(self, document_id):
        print(f"Fetching named entities for document ID: {document_id}")  # Log the document ID
        # Convert document_id to integer if it's a string
        document_id_int = int(document_id) if isinstance(document_id, str) else document_id
        print(f"Fetching named entities for document ID: {document_id_int}")  # Log the document ID
        
        query = """
            MATCH (text:AnnotatedText)-[:CONTAINS_SENTENCE]->(sentence:Sentence)-[:HAS_TOKEN]->(tagOccurrence:TagOccurrence)-[:PARTICIPATES_IN]->(ne:NamedEntity)
            WHERE text.id = $document_id
            RETURN ne
        """
        print("Query: ", query)
        return list(self.neo4j_repo.execute_query(query, {"document_id": document_id_int}))

# Test with a hardcoded document ID
# Uncomment the following lines to test
# test_document_id = 1  # Replace with a valid document ID
# entities = fetch_named_entities(test_document_id)
# print("Fetched entities: ", entities)
