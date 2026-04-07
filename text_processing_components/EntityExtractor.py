import requests
from textgraphx.TextProcessor import Neo4jRepository  # Import the Neo4jRepository class
from textgraphx.utils.id_utils import make_ne_id
import logging

# module logger
logger = logging.getLogger(__name__)

class EntityExtractor:
    def __init__(self, api_url, driver):
        self.api_url = api_url
        self.neo4j_repo = Neo4jRepository(driver)  # Instantiate Neo4jRepository

    def extract_entities(self, text):
        headers = {"Content-Type": "application/json"}
        data = {"text": text}
        
        logger.debug("Calling entity extraction API: %s", self.api_url)
        response = requests.post(self.api_url, headers=headers, json=data)
        if response.status_code == 200:
            ents = response.json().get("entities", [])
            logger.info("EntityExtractor: extracted %d entities", len(ents))
            return ents
        else:
            logger.error("Error calling the entity extraction API: %s", response.status_code)
            return []

    def integrate_entities_into_db(self, entities, text_id):
        # Fetch existing NamedEntities linked to the AnnotatedText node
        existing_entities = self.fetch_named_entities(text_id)
        logger.debug("Existing Entities: %s", existing_entities)

        for entity in entities:
            start_index = entity['start']
            end_index = entity['end']
            label = entity['label']
            matched = False

            # Check for matches with existing NamedEntities
            for existing_entity in existing_entities:
                existing_entity = dict(existing_entity)
                ne = dict(existing_entity.get("ne", {}))
                # prefer token_id when present, fall back to legacy id
                ne_token_id = ne.get('token_id')
                ne_id = ne.get('id')
                # quick index match guard (keeps behaviour similar to previous code)
                if ne.get('index') == start_index and ne.get('end_index') == end_index:
                    # If a match is found, add a new label. Match by token_id when possible
                    add_label_query = """
                        MATCH (ne:NamedEntity) WHERE (coalesce(ne.token_id, ne.id) = $match_id)
                        SET ne:NewLabel
                        RETURN ne.id AS id
                    """
                    match_val = ne_token_id if ne_token_id is not None else ne_id
                    if match_val is None:
                        continue
                    self.neo4j_repo.execute_query(add_label_query, {"match_id": match_val})
                    matched = True
                    break

            # If no match was found, create a new NamedEntity node
            if not matched:
                # compute token-index based id (entity.start / entity.end are token positions expected)
                ne_id = make_ne_id(text_id, start_index, end_index - 1, label)
                # Compute token_id independently so it remains stable even if
                # ne_id is later remapped to a canonical/NEL URI.
                ne_token_id = make_ne_id(text_id, start_index, end_index - 1, label)
                create_entity_query = """
                    MERGE (ne:NamedEntity {id: $id})
                    SET ne.type = $type, 
                        ne.value = $value, 
                        ne.start_index = $start_index, 
                        ne.end_index = $end_index,
                        ne.token_id = $token_id, ne.token_start = $start_index, ne.token_end = $end_index
                    WITH ne
                    MATCH (text:AnnotatedText)-[:CONTAINS_SENTENCE]->(sentence:Sentence)-[:HAS_TOKEN]->(tagOccurrence:TagOccurrence)
                    WHERE text.id = $documentId AND tagOccurrence.tok_index_doc >= $start_index AND tagOccurrence.tok_index_doc <= $end_index - 1
                    MERGE (ne)<-[:PARTICIPATES_IN]-(tagOccurrence)
                    MERGE (ne)<-[:IN_MENTION]-(tagOccurrence)
                """
                self.neo4j_repo.execute_query(create_entity_query, {
                    "documentId": text_id,
                    "start_index": start_index,
                    "end_index": end_index,
                    "type": label,
                    "value": entity['text'],
                    "id": ne_id,
                                    "token_id": ne_token_id,
                })

    def fetch_named_entities(self, document_id):
        logger.debug("Fetching named entities for document ID: %s", document_id)
        # Convert document_id to integer if it's a string
        document_id_int = int(document_id) if isinstance(document_id, str) else document_id
        logger.debug("Fetching named entities for document ID: %s", document_id_int)

        query = """
            MATCH (text:AnnotatedText)-[:CONTAINS_SENTENCE]->(sentence:Sentence)-[:HAS_TOKEN]->(tagOccurrence:TagOccurrence)-[:PARTICIPATES_IN]->(ne:NamedEntity)
            WHERE text.id = $document_id
            RETURN ne
        """
        logger.debug("Query: %s", query)
        return list(self.neo4j_repo.execute_query(query, {"document_id": document_id_int}))
    
    
    def fetch_named_entities2(self, document_id):
        logger.debug("Fetching named entities for document ID: %s", document_id)
        # Convert document_id to integer if it's a string
        document_id_int = int(document_id) if isinstance(document_id, str) else document_id
        logger.debug("Fetching named entities for document ID: %s", document_id_int)

        query = """
            MATCH (text:AnnotatedText)-[:CONTAINS_SENTENCE]->(sentence:Sentence)-[:HAS_TOKEN]->(tagOccurrence:TagOccurrence)-[:PARTICIPATES_IN]->(ne:NamedEntity)
            WHERE text.id = $document_id
            RETURN ne
        """
        logger.debug("Query: %s", query)
        return list(self.neo4j_repo.execute_query(query, {"document_id": document_id_int}))

# Test with a hardcoded document ID
# Uncomment the following lines to test
# test_document_id = 1  # Replace with a valid document ID
# entities = fetch_named_entities(test_document_id)
# print("Fetched entities: ", entities)
