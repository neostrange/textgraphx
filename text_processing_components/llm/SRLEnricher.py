import requests
from TextProcessor import Neo4jRepository  # Import the Neo4jRepository class
from util.GraphDbBase import GraphDBBase  # Import the GraphDBBase class

"""
**SRLEnricher**

The SRLEnricher module enriches the output of
state-of-the-art Semantic Role Labeling (SRL) models,
specifically those based on PropBank and Allennlp, by
assigning domain-specific labels to events and their
arguments.

Given the SRL output stored in a Neo4j database, the
SRLEnricher first retrieves the relevant nodes and
relationships using a Cypher query. The retrieved data
includes not only the SRL output but also the original
sentence text for contextualized annotations.

The retrieved data is then sent to a Large Language
Model (LLM) via an API call, where it receives
domain-specific labels assigned by the LLM. The output
from the LLM is expected in the form of a dictionary,
where the keys correspond to node IDs and the values
represent the assigned labels.

**Key Functionality:**

1. **Neo4j Data Retrieval**: Write a Cypher query to
retrieve SRL output and sentence text from Neo4j
database.
2. **LLM API Call**: Send retrieved data to LLM via
API call, awaiting response with domain-specific
labels.
3. **LLM Output Processing**: Process the dictionary
output from LLM, mapping node IDs to assigned labels.

**Input/Output:**

* Input:
        + SRL output stored in Neo4j database
        + Sentence text for contextualized annotations
* Output:
        + Enriched SRL output with domain-specific labels

By leveraging both Neo4j's graph database capabilities
and the LLM's language understanding abilities, the
SRLEnricher module provides a comprehensive solution
for enriching SRL output with meaningful
domain-specific labels.
"""

import requests
from TextProcessor import Neo4jRepository  # Import the Neo4jRepository class
from util.GraphDbBase import GraphDBBase  # Import the GraphDBBase class

class SRLEnricher(GraphDBBase):
    def __init__(self, argv, llm_api):
        super().__init__(command=__file__, argv=argv)
        self.llm_api = llm_api  # API endpoint for the LLM

    def retrieve_data(self):
        """
        Retrieve SRL output and sentence text from Neo4j database.
        """
        neo4j_repo = Neo4jRepository(self._driver)  # Create an instance of Neo4jRepository
        query = """
        MATCH (n:TEvent)<-[r:PARTICIPANT]-(participant) 
        return n as event, collect(participant) as participants, collect(r) as relations
        """
        results = list(neo4j_repo.execute_query(query, {}))  # Execute the query using Neo4jRepository
        data = []
        for record in results:
            record = list(record)
            
            # event node information
            event = record[0]
            event_id = event.element_id
            event_dict = dict(record[0])
            
            # participant nodes information
            participants = list(record[1])
            
            # relations information
            relations = list(record[2])
            
            data.append({
                'event_id': event_id,
                'event_properties': event_dict,
                'participants': participants,
                'relations': relations
            })
        return data

    def create_prompt_for_llm(self):
        """
        Create a prompt for the LLM based on the retrieved events and their arguments.
        """
        data = self.retrieve_data()  # Retrieve data from Neo4j
        prompt = "Enrich the following events and their participants:\n"
        
        
        for item in data:
                prompt = prompt + item
                self.call_llm(prompt=prompt)
                
                

        # for item in data:
        #     event_properties = item['event_properties']
        #     event_text = event_properties.get('form')
        #     prompt += f"Event: {event_text} (ID: {item['event_id']})\n"
            
        #     # Assuming arguments are stored in a list
        #     arguments = item.get('arguments', [])
        #     for arg in arguments:
        #         arg_properties = arg['properties']
        #         arg_text = arg_properties.get('head', 'Unknown argument')
        #         prompt += f"  - Argument: {arg_text} (ID: {arg['identity']})\n"
        
        
        return prompt

    def call_llm(self, prompt):
        """
        Send retrieved data to LLM via API call.
        """
        payload = {
            "model": "llama3.1",
            "prompt": prompt
        }
        response = requests.post(self.llm_api, json=payload)
        if response.status_code == 200:
            return response.json()  # Return the JSON response
        else:
            print("Error: Received response with status code", response.status_code)
            print("Response content:", response.text)  # Print the response content for debugging
            response.raise_for_status() 
            

    def process_output(self, llm_response):
        """
        Process the output from LLM and map node IDs to assigned labels.
        """
        # TODO: Implement output processing
        pass

    def enrich_srl_output(self):
        """
        Main method to enrich SRL output with domain-specific labels.
        """
        data = self.retrieve_data()
        llm_response = self.call_llm(data)
        enriched_output = self.process_output(llm_response)
        return enriched_output

def main():
    llm_api = "http://localhost:11434/api/generate"  # Replace with your actual LLM API endpoint
    enricher = SRLEnricher(argv=[], llm_api=llm_api)
    
    prompt = enricher.create_prompt_for_llm()
    print("Generated Prompt for LLM:")
    print(prompt)

if __name__ == "__main__":
    main()
