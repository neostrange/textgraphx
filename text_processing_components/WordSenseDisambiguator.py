import logging
import re
import requests

class WordSenseDisambiguator:
    """
    A class that performs word sense disambiguation on a given document using the AMuSE-WSD API.
    """

    def __init__(self, amuse_wsd_api_endpoint, neo4j_executor):
        """
        Initializes the WordSenseDisambiguator instance.

        Args:
        amuse_wsd_api_endpoint (str): The endpoint of the AMuSE-WSD API.
        neo4j_executor (object): An instance that provides a method to execute Cypher queries on a Neo4j database.
        """
        self.amuse_wsd_api_endpoint = amuse_wsd_api_endpoint
        self.neo4j_executor = neo4j_executor

    def perform_wsd(self, document_id: str) -> None:
        """
        Perform word sense disambiguation on a given document using the AMuSE-WSD API.

        Args:
        document_id (str): The ID of the document to process.
        """
        # Define the Cypher query as a constant
        SENTENCE_QUERY = """
            MATCH (d:AnnotatedText {id: $doc_id})-[:CONTAINS_SENTENCE]->(s:Sentence)
            RETURN s.id AS sentence_id, s.text AS text
        """

        # Validate the input
        if not document_id:
            raise ValueError("Document ID cannot be empty")

        try:
            # Execute the Cypher query to retrieve sentences
            query_parameters = {"doc_id": document_id}
            sentence_query_result = self.neo4j_executor.execute_query(SENTENCE_QUERY, query_parameters)

            # Extract sentence IDs and texts from the query result
            sentence_ids = [record["sentence_id"] for record in sentence_query_result]
            sentences_to_process = [record["text"] for record in sentence_query_result]

            # Call the AMuSE-WSD API with the sentences
            api_response = self._call_amuse_wsd_api(sentences_to_process)

            if api_response:
                # Update the token nodes in Neo4j with the API response
                for idx, sentence_data in enumerate(api_response):
                    sentence_id = sentence_ids[idx]
                    for token_data in sentence_data['tokens']:
                        token_index = token_data['index']
                        token_attrs = {
                            'bnSynsetId': token_data['bnSynsetId'],
                            'wnSynsetOffset': token_data['wnSynsetOffset'],
                            'nltkSynset': token_data['nltkSynset']
                        }
                        self._update_tokens_in_neo4j(sentence_id, token_index, token_attrs)

            logging.info(f"Word sense disambiguation completed for document {document_id}")

        except Exception as e:
            logging.error(f"Error performing word sense disambiguation: {str(e)}")

    def _call_amuse_wsd_api(self, sentences):
        """
        Calls the AMuSE-WSD API with the given sentences.

        Args:
        sentences (list): A list of sentences to process.

        Returns:
        list: The API response.
        """
        # Implement the API call logic here


        headers = {
            "accept": "application/json",
            "Content-Type": "application/json"
        }

        # Apply replace_hyphens to each sentence in the collection
        # NOTE: its just a workaround for AMUSE-WSD as it does not consider hyphens for multiwords expressions
        updated_sentences = [self.replace_hyphens_to_underscores(sentence) for sentence in sentences]

        data = [{"text": sentence, "lang": "EN"} for sentence in updated_sentences]

        try:
            response = requests.post(self.amuse_wsd_api_endpoint, json=data, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error while calling AMuSE-WSD API: {e}")
            return None
        pass

    def _update_tokens_in_neo4j(self, sentence_id, token_index, token_attrs):
        """
        Updates the token nodes in Neo4j with the given attributes.

        Args:
        sentence_id (str): The ID of the sentence.
        token_index (int): The index of the token.
        token_attrs (dict): A dictionary of token attributes.
        """
        # Implement the token update logic here

        query = """
            MATCH (s:Sentence {id: $sentence_id})-[:HAS_TOKEN]->(t:TagOccurrence {tok_index_sent: $index})
            SET t.bnSynsetId = $bnSynsetId,
                t.wnSynsetOffset = $wnSynsetOffset,
                t.nltkSynset = $nltkSynset
        """

        params = {
            "sentence_id": sentence_id,
            "index": token_index,
            "bnSynsetId": token_attrs['bnSynsetId'],
            "wnSynsetOffset": token_attrs['wnSynsetOffset'],
            "nltkSynset": token_attrs['nltkSynset']
        }

        self.neo4j_executor.execute_query(query, params)

        pass


    def replace_hyphens_to_underscores(self,sentence):
        # Define a regular expression pattern to match hyphens used as infixes
        pattern = re.compile(r'(?<=\w)-(?=\w)')

        # Replace hyphens with underscores
        replaced_sentence = re.sub(pattern, '_', sentence)

        return replaced_sentence