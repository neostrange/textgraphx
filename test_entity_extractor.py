import unittest
from unittest.mock import patch, MagicMock
from text_processing_components.EntityExtractor import EntityExtractor

class TestEntityExtractor(unittest.TestCase):

    @patch('text_processing_components.EntityExtractor.requests.post')
    def test_extract_entities(self, mock_post):
        # Mock the API response
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "entities": [
                {"start": 32, "end": 37, "label": "PERSON", "text": "spaCy"}
            ]
        }

        # Instantiate the EntityExtractor
        extractor = EntityExtractor("http://127.0.0.1:11435/process_text", None)

        # Call the extract_entities method
        entities = extractor.extract_entities("This is a test sentence for the spaCy pipeline.")

        # Assert that the entities are extracted correctly
        self.assertEqual(len(entities), 1)
        self.assertEqual(entities[0]['text'], "spaCy")
        self.assertEqual(entities[0]['label'], "PERSON")

    @patch('text_processing_components.EntityExtractor.Neo4jRepository')
    def test_integrate_entities_into_db(self, mock_neo4j_repo):
        # Mock the Neo4j repository methods
        mock_repo = MagicMock()
        mock_neo4j_repo.return_value = mock_repo

        # Instantiate the EntityExtractor
        extractor = EntityExtractor("http://127.0.0.1:11435/process_text", mock_repo)

        # Define test entities
        entities = [
            {"start": 32, "end": 37, "label": "PERSON", "text": "spaCy"}
        ]
        text_id = "test_document_id"

        # Call the integrate_entities_into_db method
        extractor.integrate_entities_into_db(entities, text_id)

        # Assert that the appropriate Neo4j methods were called
        mock_repo.execute_query.assert_called()  # Check if execute_query was called

if __name__ == '__main__':
    unittest.main()
