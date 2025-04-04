import logging
import requests
import json
from TextProcessor import Neo4jRepository  # Import the Neo4jRepository class
from util.GraphDbBase import GraphDBBase  # Import the GraphDBBase class
from typing import Dict, List, Any  # Import Dict, List, and Any from typing module

class SRLEnricher(GraphDBBase):
    
    def __init__(self, argv, llm_api):
        super().__init__(command=__file__, argv=argv)
        self.llm_api = llm_api  # API endpoint for the LLM
        self.neo4j_repo = Neo4jRepository(self._driver)  # Create an instance of Neo4jRepository

    def retrieve_data(self):
        """
        Retrieve SRL output and sentence text from Neo4j database.
        Steps: 
        1. get the dataset from the database i.e., neo4j. 
        2. transform each dataitem from dataset into a format that can be used by the LLM model. i.e., 
        remove the unwanted data and keep the necessary data. return transformed data.
        """
        # neo4j_repo = Neo4jRepository(self._driver)  # Create an instance of Neo4jRepository
        
        query = """
        MATCH (sent:Sentence)-[:HAS_TOKEN]-(t:TagOccurrence)-[:TRIGGERS]->(n:TEvent)<-[r:PARTICIPANT]-(participant) 
        return n as event, collect(participant) as participants, collect(r) as relations, sent.text as sentence
        """
        results = list(self.neo4j_repo.execute_query(query, {}))  # Execute the query using Neo4jRepository
        event_simplified = dict()
        data = []
        
        for record in results:
            record = list(record)
            
            # event node information
            event = record[0]
            event_id =event.element_id
            event_dict = dict(record[0])
            
            event_simplified = {
                'sentence_as_context': record[3],
                'eventId': event_id,
                'event_trigger': event_dict["form"],
            }
            
            # relationships information
            relations = list(record[2])
            
            event_participant = dict()
            participants = list()
            
            for relation in relations:
                #relation_id = relation._element_id
                relation_type = dict(relation)["type"]
                relation_participants = list(relation.nodes)
                
                for relation_participant in relation_participants:
                    relation_participant_id = relation_participant.element_id
                    
                    relation_participant_text = None
                    
                    try:
                        relation_participant_text = dict(relation_participant)["id"]
                    except KeyError as e:
                        print(f"Caught a KeyError: {e}")
                        relation_participant_text = dict(relation_participant)["text"]
                    
                    event_participant = {
                        
                        'participant_text': relation_participant_text,
                        'participant_id': relation_participant_id,
                        'relation_type': relation_type
        
                    }
                    participants.append(event_participant)
                    break
                
            event_simplified["participants"] = participants
                
            data.append(event_simplified)
            
        return data

# Function to generate Cypher queries based on LLM output
    def generate_cypher_queries(self, response: Dict[str, Any]) -> List[str]:
        queries = []
        try:
            response = dict(json.loads(response["response"].strip()))
        except (json.decoder.JSONDecodeError, KeyError) as e:
            logging.error("Error processing JSON response: %s", e)
            raise ValueError(f"Error processing JSON response: {e}")

        logging.info("Response type: %s", type(response))

        participants = response.get('participants', [])
        if participants:
            for participant in participants:
                try:
                    participant_id = participant['participant_id']
                    entity_label = participant.get('entity_label', "UNKNOWN")
                except (TypeError, KeyError) as e:
                    logging.error("Error processing participant data: %s", e)
                    raise ValueError(f"Error processing participant data: {e}")

                query = f"""
                MATCH (n)
                WHERE id(n) = {participant_id}
                SET n:{entity_label}
                """
                queries.append(query)

        try:
            event_id = response['eventId']
            event_type = response.get('event_type', "UNKNOWN")
        except KeyError as e:
            logging.error("Error processing event data: %s", e)
            raise ValueError(f"Error processing event data: {e}")

        event_query = f"""
        MATCH (e)
        WHERE id(e) = {event_id}
        SET e:{event_type}
        """
        queries.append(event_query)

        logging.info("Generated queries: %s", queries)
        return queries


    def create_prompt_for_llm(self, data):
        """
        Create a prompt for the LLM based on the retrieved events and their arguments.
        """
        
        prompt = self.LLM_PROMPT
        
        #data = self.retrieve_data()  # Retrieve data from Neo4j

        #for item in data:
        prompt_task = prompt + str(data)
        print(data)
        print("********************************************************************************************************************************************)")
        
        return prompt_task
    
    
    def execute_neo4j_query(self, query):
        """
        Execute a Cypher query in Neo4j.
        """
        try:
            self.neo4j_repo.execute_query(query, {})
        except Exception as e:
            print("Error executing Cypher query:", e)
            raise ValueError("Error executing Cypher query: {}".format(e))    

    def call_llm(self, prompt):
        """
        Send retrieved data to LLM via API call.
        """
        payload = {
            "model": "llama3.1",
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }
        
        try:
            response = requests.post(self.llm_api, json=payload)
            response.raise_for_status()  # Raise an error for bad responses
            response_data = response.json()  # Parse the JSON response
            #print("Response Data:", response_data)  # Print the response data
            if "response" in response_data:
                print("Response Field:", response_data["response"].strip())  # Print the specific response field
            return response_data  # Return the JSON response
        except requests.exceptions.RequestException as e:
            print("Error during API call:", e)
        except ValueError as e:
            print("Error parsing JSON response:", e) 

    def enrich_srl_output(self):
        """
        Main method to enrich SRL output with domain-specific labels.
        """
        data = self.retrieve_data()
        llm_response = self.call_llm(data)
        enriched_output = self.process_output(llm_response)
        return enriched_output

    @property
    def LLM_PROMPT(self):
        return """
                Role Description
                You are an expert Domain-Specific Entity and Event Labeling Agent, specializing in entity and event classification. Your task is to analyze Semantic Role Labeling (SRL) output, identify events, assess participants, and assign structured domain-specific labels using a predefined ontology.

                
                1. Task Overview
                You are given structured input from a Semantic Role Labeling (SRL) system, which includes:

                A sentence providing context (sentence_as_context).
                An event with a unique identifier (eventId) and its trigger word (event_trigger).
                A list of participants (participants), each with:
                participant_text (the entity phrase in the sentence).
                participant_id (a unique identifier for the entity).
                relation_type (semantic role label assigned by the SRL system).
                
                Your task is to assign labels to:

                - The event → Map the event to the most appropriate event type.
                - Each participant entity → Assign the most relevant entity label.
                
                2. Ontology
                Use the following predefined categories for event and entity classification. Do not generate new labels—only use these.

                Event Types (Action or Discussion Related to Innovation)
                POLICY_ANNOUNCEMENT → Government policy, strategy, or regulatory updates.
                FUNDING_ALLOCATION → Financial grants, investments, or funding commitments.
                INNOVATION_ACTIVITY → Development, research, or progress in technology/innovation.
                COLLABORATION_INITIATIVE → Initiatives or plans to form collaboration between Government, businesses, or academia.
                COLLABORATION → Partnerships, agreements, or collaborations between entities.
                COLLABORATION_BREAKDOWN → indicates breakdown such as "withdrew," "cancels," "dispute," "failed partnership" etc. for example, "University cancels mining tech collaboration".
                INDUSTRY_DEVELOPMENT → Growth, transformation, or structuring of an industry sector.
                RESEARCH_PUBLICATION → Scientific or research output contributing to innovation.
                TECHNOLOGY_DEPLOYMENT → Implementation of new technology in practice.
                STARTUP_ACTIVITY → Entrepreneurial activities such as launching or scaling startups.
                ECONOMIC_IMPACT → Economic consequences of innovation-related activities.
                INNOVATION_DISCUSSION → Public discourse, expert opinions, or debates about innovation.
                ECOSYSTEM_SHIFT → "declined," "improved," "recommended", e.g., "Cluster development ranking drops to 39th".
                
                Entity Labels (Key Actors & Elements in Innovation Ecosystem)
                GOVERNMENT → Federal, state, or local Government agencies.
                BUSINESS → Established corporations or private-sector firms.
                ACADEMIA → Universities, research institutes, academic institutions, or academic bodies, e.g. Universities "ECU", "ANU", "UNSW", research bodies "UNSW", "CSIRO".
                STARTUP → Emerging or early-stage innovative businesses.
                INVESTOR → Venture capitalists, angel investors, or funding bodies.
                RESEARCH → Scientific studies, papers, or research efforts.
                TECHNOLOGY → Innovations, AI, software, platforms, tools, or technical systems.
                INNOVATION_HUB → Physical/digital innovation hubs or innovation districts, e.g., "Sydney Startup Hub", "Silicon Valley", "Perth Innovation Precinct".
                FUNDING → Grants, capital investments, or financial resources.
                POLICY → Laws, regulations, and Government strategies.
                INFRASTRUCTURE → Physical or digital systems that support innovation.
                PROGRAM → Government or private innovation-related initiatives.
                LOCATION → Geographic areas such as cities, states, or countries.
                REGULATION → Compliance, legal, and policy measures.
                MARKET → Economic demand, industries, and consumer trends.
                LOCAL_DEMAND → Local economic needs, market demands, or community requirements.
                PUBLIC_SENTIMENT → Societal perception, media opinions, or general public response.
                EXPERT → refers to individuals with advanced knowledge, significant experience, and recognized authority in a specific field of innovation. They are influential in shaping their domain through research, leadership, or thought leadership.
                TALENT → Skilled individuals driving innovation (e.g., workers, researchers, mathematicians, Quantum physicists).
                PUBLIC_SENTIMENT → general feelings, attitudes, and opinions of the public towards a particular issue, event, or entity.
                STATS → statistical data, figures, or numerical information.
                
                4. Input & Expected Output Examples
                Example 1: Policy Announcement
                Input:
                {
                    "sentence_as_context": "The Australian Government announced a $10 million investment in AI startups.",
                    "eventId": "101",
                    "event_trigger": "announced",
                    "participants": [
                        {"participant_text": "The Australian Government", "participant_id": "5001", "relation_type": "ARG0"},
                        {"participant_text": "$10 million investment", "participant_id": "5002", "relation_type": "ARG1"},
                        {"participant_text": "AI startups", "participant_id": "5003", "relation_type": "ARG2"}
                    ]
                    }

                Output:
                {
                    "sentence_as_context": "The Australian Government announced a $10 million investment in AI startups.",
                    "eventId": "101",
                    "event_type": "FUNDING_ALLOCATION",
                    "event_trigger": "announced",
                    "participants": [
                        {"participant_text": "The Australian Government", "participant_id": "5001", "relation_type": "ARG0", "entity_label": "GOVERNMENT"},
                        {"participant_text": "$10 million investment", "participant_id": "5002", "relation_type": "ARG1", "entity_label": "FUNDING"},
                        {"participant_text": "AI startups", "participant_id": "5003", "relation_type": "ARG2", "entity_label": "STARTUP"}
                    ]
                    }

                Example 2: Innovation Discussion
                Input:
                {
                    "sentence_as_context": "Experts debated the impact of artificial intelligence on the workforce.",
                    "eventId": "205",
                    "event_trigger": "debated",
                    "participants": [
                        {"participant_text": "Experts", "participant_id": "6010", "relation_type": "ARG0"},
                        {"participant_text": "the impact of artificial intelligence", "participant_id": "6011", "relation_type": "ARG1"},
                        {"participant_text": "the workforce", "participant_id": "6012", "relation_type": "ARG2"}
                    ]
                    }

                Output: 
                {
                    "sentence_as_context": "Experts debated the impact of artificial intelligence on the workforce.",
                    "eventId": "205",
                    "event_type": "INNOVATION_DISCUSSION",
                    "event_trigger": "debated",
                    "participants": [
                        {"participant_text": "Experts", "participant_id": "6010", "relation_type": "ARG0", "entity_label": "EXPERT"},
                        {"participant_text": "the impact of artificial intelligence", "participant_id": "6011", "relation_type": "ARG1", "entity_label": "TECHNOLOGY"},
                        {"participant_text": "the workforce", "participant_id": "6012", "relation_type": "ARG2", "entity_label": "MARKET"}
                    ]
                    }


                Example 3: Industry Development
                Input: 
                {'sentence_as_context': 'Since 2014, Australia’s IT exports have grown 400 per cent and we’ve spent around $8 billion on R&D.', 'eventId': '139', 'event_trigger': 'grown', 'participants': [{'participant_text': 'Australia’s IT exports', 'participant_id': '38', 'relation_type': 'ARG1'}, {'participant_text': '1_639_651_PERCENT', 'participant_id': '6222', 'relation_type': 'ARG2'}]}

                Output:
                {
                    "sentence_as_context": "Since 2014, Australia’s IT exports have grown 400 per cent and we’ve spent around $8 billion on R&D.",
                    "eventId": "139",
                    "event_type": "INDUSTRY_DEVELOPMENT",
                    "event_trigger": "grown",
                    "participants": [
                        {
                            "participant_text": "Australia’s IT exports",
                            "participant_id": "38",
                            "relation_type": "ARG1",
                            "entity_label": "TECHNOLOGY"
                        },
                        {
                            "participant_text": "1_639_651_PERCENT",
                            "participant_id": "6222",
                            "relation_type": "ARG2",
                            "entity_label": "ECONOMIC_IMPACT"
                        }
                    ]
                }

                5. Additional Guidelines
                If an entity does not fit a category, assign the closest match.
                Use the event ontology consistently across all cases.
                if something is unknown, label is as UNKNOWN
                Favor general labels over overly specific ones.
                Dont add any comments into the json output
                
                The input is: 
                """
            
 
 
def main():
    llm_api = "http://localhost:11434/api/generate"  # Replace with your actual LLM API endpoint
    enricher = SRLEnricher(argv=[],llm_api=llm_api)
    
    # 1. get the dataset from the database i.e., neo4j. 
    # 2. transform each dataitem from dataset into a format that can be used by the LLM model. i.e., remove the unwanted data and keep the necessary data. return transformed data.
    data = enricher.retrieve_data()
    print("Retrieved Data:", data)
    
    # 3. Loop through the transformed data and send each dataitem to the LLM model.
    for item in data:
        #   4. Now for each transformed datatiem, define the prompt for the LLM model.
        prompt = enricher.create_prompt_for_llm(item)
        print("Generated Prompt for LLM:")
        #print(prompt)
        #   5. send the prompt to the LLM model and get the response.
        max_retries = 2
        attempts = 0
        while attempts < max_retries:
            response = enricher.call_llm(prompt=prompt)
        #   6. process the response and generate the cypher queries. These cypher queries will be used to update the database.
            try:
                cypher_queries = enricher.generate_cypher_queries(response=response)
                break  # Exit the loop if successful
            except ValueError as e:
                print("Error generating Cypher queries:", e)
                attempts += 1
                
        if attempts == max_retries:
            print("Failed to generate Cypher queries after {} attempts")
            continue # ignore this dataitem and move to the next one.
        
        print("Generated Cypher Queries:", cypher_queries)
        #   7. execute the cypher queries to update the database.
        for query in cypher_queries:
            enricher.execute_neo4j_query(query)
            #enricher.neo4j_repo.execute_query(query, {})
            print("Executed Cypher Query:", query)
            
    # 8. Repeat the process for each dataitem in the dataset.
    # 9. Once all dataitems are processed, the database will be updated with the enriched data.
    # 10. The process is complete.
    
           
if __name__ == "__main__":
    main()


