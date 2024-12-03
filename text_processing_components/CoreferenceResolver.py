from py2neo import Graph
from py2neo import *
import requests
import json



class CoreferenceResolver:

    
    def __init__(self, uri, username, password, coreference_service_endpoint):
        self.uri = uri
        self.username = username
        self.password = password
        self.graph = Graph(self.uri, auth=(self.username, self.password))
        self.coreference_service_endpoint = coreference_service_endpoint

    def create_node(self, node_type, text, start_index, end_index):
        return Node(node_type, text=text, startIndex=start_index, endIndex=end_index)

    def connect_node_to_tag_occurrences(self, node, index_range, doc):
        PARTICIPATES_IN = Relationship.type("PARTICIPATES_IN")
        atg = ""
        for index in index_range:
            query = "match (x:TagOccurrence {tok_index_doc:" + str(index) + "})-[:HAS_TOKEN]-()-[:CONTAINS_SENTENCE]-(:AnnotatedText {id:"+str(doc._.text_id)+"}) return x"
            token_node = self.graph.evaluate(query)
            if token_node is None:
                continue
            token_mention_rel = PARTICIPATES_IN(token_node, node)
            if atg == "":
                atg = token_mention_rel
            else:
                atg = atg | token_mention_rel
        self.graph.create(atg)

    def resolve_coreference(self, doc, text_id):
        result = self.call_coreference_resolution_api(self.coreference_service_endpoint, doc.text)
        print("Coref Result: ", result)

        coref = []
        for cluster in result["clusters"]:
            i = 0
            antecedent_span = ""
            cag = ""  # coreferents - antecedent relationships sub-graph

            for span_token_indexes in cluster:
                if i == 0:
                    i += 1
                    # the first span will be the antecedent for all other references
                    antecedent_span = doc[span_token_indexes[0]:span_token_indexes[-1]]  # updated for index
                    antecedent_node = self.create_node("Antecedent", antecedent_span.text, span_token_indexes[0], span_token_indexes[-1])
                    self.connect_node_to_tag_occurrences(antecedent_node, range(span_token_indexes[0], span_token_indexes[-1]), doc)
                    continue

                coref_mention_span = doc[span_token_indexes[0]:span_token_indexes[-1]]  # updated index
                coref_mention_node = self.create_node("CorefMention", coref_mention_span.text, span_token_indexes[0], span_token_indexes[-1])
                self.connect_node_to_tag_occurrences(coref_mention_node, range(span_token_indexes[0], span_token_indexes[-1]),doc)

                coref_rel = Relationship.type("COREF")(coref_mention_node, antecedent_node)
                if cag == "":
                    cag = coref_rel
                else:
                    cag = cag | coref_rel

                coref.append({"referent": coref_mention_node, "antecedent": antecedent_node})

            self.graph.create(cag)

        print(coref)

    # def call_coreference_resolution_api(self, coreference_service_endpoint, text):
    #     # to integrate spacy-experimental-coref
    #     #URL = "http://localhost:9999/coreference_resolution"

    #     URL = coreference_service_endpoint
    #     PARAMS = {"Content-Type": "application/json"}

    #     payload = ''

    #     payload = {"document":text}

    #     r = requests.post(URL, headers=PARAMS, data=json.dumps(payload))

    #     return json.loads(r.text)
    



    def call_coreference_resolution_api(self, coreference_service_endpoint, text):
        """
        Calls the coreference resolution API for coreference resolution.

        Args:
            coreference_service_endpoint (str): The endpoint URL for the coreference service.
            text (str): The text to be processed for coreference resolution.

        Returns:
            dict: The response from the coreference resolution API.
        """

        # Define the API endpoint and headers
        url = coreference_service_endpoint
        headers = {"Content-Type": "application/json"}

        # Prepare the payload
        payload = {"document": text}

        try:
            # Send a POST request to the API
            response = requests.post(url, headers=headers, json=payload)

            # Check if the request was successful
            response.raise_for_status()

            # Return the JSON response
            return response.json()

        except requests.exceptions.HTTPError as http_err:
            # Handle HTTP errors
            print(f"HTTP error occurred: {http_err}")
        except Exception as err:
            # Handle any other exceptions
            print(f"An error occurred: {err}")

        # If an error occurs, return None
        return None