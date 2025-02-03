import unittest
from textgraphx.text_processing_components.EntityExtractor import EntityExtractor
from py2neo import Graph

class TestEntityExtractorWithData(unittest.TestCase):

    def setUp(self):
        self.api_url = "http://127.0.0.1:11435/process_text"
        self.driver = Graph("your_neo4j_uri", auth=("your_username", "your_password"))
        self.extractor = EntityExtractor(self.api_url, self.driver)

    def test_integration_with_actual_data(self):
        # Fetch existing NamedEntities from Neo4j
        document_id = "your_document_id"  # Replace with actual document ID
        existing_entities = self.extractor.fetch_named_entities(document_id)

        # Sample text to extract entities from
        sample_text = "This is a test sentence for the spaCy pipeline."

        # Extract entities using the API
        extracted_entities = self.extractor.extract_entities(sample_text)

        # Integrate extracted entities into Neo4j
        self.extractor.integrate_entities_into_db(extracted_entities, document_id)

        # Verify the integration
        # You can add assertions here to check if the entities were added/updated correctly

if __name__ == '__main__':
    unittest.main()
