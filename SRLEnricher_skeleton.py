import logging
import requests
import json
from TextProcessor import Neo4jRepository  # Import the Neo4jRepository class
from util.GraphDbBase import GraphDBBase  # Import the GraphDBBase class
from typing import Dict, List, Any  # Import Dict, List, and Any from typing module
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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
        MATCH (ann:AnnotatedText )-[:CONTAINS_SENTENCE]-(sent:Sentence)-[:HAS_TOKEN]-(t:TagOccurrence)-[:TRIGGERS]->(n:TEvent)
        <-[r:PARTICIPANT]-(participant) 
        WHERE ann.id in [1,2,5,3,4,6,7,8,9,10,11] // done: 1,2,5,3,4
        RETURN n as event, collect(participant) as participants, collect(r) as relations, sent.text as sentence
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
        print("input: ", data)
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
            "format": "json",
            "options": {"num_ctx": 10000}
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
    def LLM_PROMPT3(self):
        return """
                Role Description
                    You are an expert information extraction specialist focused on the Australian innovation ecosystem. Your task is to meticulously identify and label entities and events within text, using a predefined ontology. You will receive Semantic Role Labeling (SRL) output as input. Analyze this output, identify events, assess participants, and assign structured, domain-specific labels.
                    Your task is to be as thorough as possible in identifying and labeling all relevant entities and events. Do not miss any instances. Your expertise in information extraction is crucial for accurately classifying entities and events within the Australian innovation ecosystem.
                    Don't forget to provide detailed rationales for each label assigned, explaining why the label is appropriate based on the context provided.
                    
                {
                    "eventTypes": {
                        "POLICY_EVENT": {
                        "description": "Government actions/announcements related to innovation",
                        "subtypes": {
                            "POLICY_ANNOUNCEMENT": "Public statements by officials on policies/strategies"
                        }
                        },
                        "FINANCIAL_EVENT": {
                        "description": "Financial transactions/investments in innovation",
                        "subtypes": {
                            "FUNDING_ALLOCATION": "Awarding financial resources to innovation entities"
                        }
                        },
                        "INNOVATION_DEVELOPMENT_EVENT": {
                        "description": "Progress in innovation creation/advancement",
                        "subtypes": {
                            "INNOVATION_ACTIVITY": "Development/research in technology",
                            "TECHNOLOGY_DEPLOYMENT": "Implementation of new technology",
                            "RESEARCH_PUBLICATION": "Publication of research output",
                            "STARTUP_ACTIVITY": "Entrepreneurial activities"
                        }
                        },
                        "COLLABORATION_EVENT": {
                        "description": "Formation/dissolution of innovation collaborations",
                        "subtypes": {
                            "COLLABORATION_INITIATIVE": "Proposals for new collaborations",
                            "COLLABORATION": "Existing partnerships/agreements",
                            "COLLABORATION_BREAKDOWN": "Termination of collaborations"
                        }
                        },
                        "INDUSTRY_EVENT": {
                        "description": "Changes in industry sectors",
                        "subtypes": {
                            "INDUSTRY_DEVELOPMENT": "Growth/transformation in industry sectors"
                        }
                        },
                        "ECONOMIC_EVENT": {
                        "description": "Economic consequences of innovation",
                        "subtypes": {
                            "ECONOMIC_IMPACT": "Measurable economic effects"
                        }
                        },
                        "DISCUSSION_EVENT": {
                        "description": "Public discourse on innovation",
                        "subtypes": {
                            "INNOVATION_DISCUSSION": "Public debates/expert opinions"
                        }
                        },
                        "ECOSYSTEM_EVENT": {
                        "description": "Changes in innovation ecosystem",
                        "subtypes": {
                            "ECOSYSTEM_SHIFT": "Significant ecosystem changes"
                        }
                        }
                    },
                    "entityLabels": {
                        "ACTOR": {
                        "subtypes": {
                            "GOVERNMENT_ORGANIZATION": "Government agencies",
                            "BUSINESS_ORGANIZATION": "Private-sector firms",
                            "ACADEMIC_INSTITUTION": "Universities/research institutes",
                            "STARTUP": "Early-stage businesses",
                            "INVESTOR": "Funding bodies/investors",
                            "SUPPORT_ORGANIZATION": "Support service providers"
                        }
                        },
                        "PERSON": {
                        "subtypes": {
                            "INNOVATOR": "Creators/developers of innovations",
                            "EXPERT": "Domain authorities"
                        }
                        },
                        "AUSTRALIAN_INNOVATION_ELEMENT": {
                        "subtypes": {
                            "TECHNOLOGY": "Innovations/technical systems",
                            "INTELLECTUAL_PROPERTY": "Patents/copyrights",
                            "FUNDING": "Financial resources",
                            "POLICY": "Laws/regulations",
                            "MARKET": "Markets for goods/services",
                            "INDUSTRY": "Groups of similar companies",
                            "LOCAL_DEMAND": "Economic needs/preferences",
                            "PUBLIC_SENTIMENT": "Public attitudes",
                            "STATS": "Statistical data"
                        }
                        },
                        "LOCATION": {
                        "subtypes": {
                            "LOCATION": "Geographic areas",
                            "INNOVATION_HUB": "Innovation precincts"
                        }
                        },
                        "INFRASTRUCTURE": {
                        "subtypes": {
                            "INFRASTRUCTURE": "Supporting systems"
                        }
                        },
                        "PROGRAM_INITIATIVE": {
                        "subtypes": {
                            "PROGRAM_INITIATIVE": "Organized innovation efforts"
                        }
                        }
                    },
                    "inputFormat": {
                        "sentence_as_context": "string",
                        "eventId": "string",
                        "event_trigger": "string",
                        "participants": [{
                        "participant_text": "string",
                        "participant_id": "string",
                        "relation_type": "string"
                        }]
                    },
                    "outputFormat": {
                        "sentence_as_context": "string",
                        "eventId": "string",
                        "event_trigger": "string",
                        "participants": [{
                        "participant_text": "string",
                        "participant_id": "string",
                        "relation_type": "string",
                        "entity_label": "string",
                        "rationale": "string"
                        }],
                        "event_type": "string",
                        "rationale": "string"
                    }
                    }
    ```             
                     The input is: 
    
    """

    @property
    def LLM_PROMPT(self):
        return """ Role Description
                    You are an expert information extraction specialist focused on the Australian innovation ecosystem. Your task is to meticulously identify and label entities and events within text, using a predefined ontology. You will receive Semantic Role Labeling (SRL) output as input. Analyze this output, identify events, assess participants, and assign structured, domain-specific labels.
                    Your task is to be as thorough as possible in identifying and labeling all relevant entities and events. Do not miss any instances. Your expertise in information extraction is crucial for accurately classifying entities and events within the Australian innovation ecosystem.
                    Don't forget to provide detailed rationales for each label assigned, explaining why the label is appropriate based on the context provided.
                    
                    **The Ontology**
                    Use *only* the following predefined categories for event and entity classification. Do *not* generate new labels—use only these provided labels.  Adherence to the ontology is paramount.

                    Event Categories/Types (Action or Discussion Related to Innovation)
                    1. POLICY_EVENT → Encompasses government actions and announcements directly related to innovation in Australia. This includes the creation, modification, or implementation of policies, regulations, strategies, and funding programs. *Example:* "The government announced a new AI strategy."
                        1.1. POLICY_ANNOUNCEMENT → Public statements by government officials outlining new or revised policies, strategies, or regulations impacting Australian innovation. *Example:* "The Minister for Industry announced new tax incentives for R&D."

                    2. FINANCIAL_EVENT → Financial transactions, investments, funding allocations, or economic activities specifically related to innovation.
                        2.1. FUNDING_ALLOCATION → The act of awarding or committing financial resources (grants, investments, etc.) to Australian startups, research institutions, innovation hubs, or specific innovation projects. *Example:* "CSIRO received $5 million in funding from the government."

                    3. INNOVATION_DEVELOPMENT_EVENT → Focuses on progress, activities, and milestones related to the creation and advancement of innovation in Australia.
                        3.1. INNOVATION_ACTIVITY → Development, research, or progress in technology/innovation by Australian entities. *Example:* "Researchers at ANU developed a new battery technology."
                        3.2. TECHNOLOGY_DEPLOYMENT → The practical application or implementation of new technology within Australian industries or organizations. *Example:* "Hospitals are deploying AI-powered diagnostic tools."
                        3.3. RESEARCH_PUBLICATION → The publication of scientific or research output by Australian researchers or institutions, directly contributing to innovation. *Example:* "A new paper on quantum computing was published in Nature by researchers at UNSW."
                        3.4. STARTUP_ACTIVITY → Entrepreneurial activities related to launching, scaling, or exiting startups in Australia, including funding rounds, expansion, acquisitions, and IPOs. *Example:* "A Sydney-based startup raised $2 million in Series A funding."

                    4. COLLABORATION_EVENT → Initiatives, plans, or actions related to forming or dissolving collaborations between entities within the Australian innovation ecosystem.
                        4.1. COLLABORATION_INITIATIVE → Formal proposals, plans, or announcements for new collaborations between Australian government, businesses, or academia. *Example:* "The government launched an initiative to promote university-industry partnerships in AI."
                        4.2. COLLABORATION → Existing partnerships, agreements, or joint ventures between Australian entities focused on innovation-related activities. *Example:* "Two Australian universities are collaborating on AI research."
                        4.3. COLLABORATION_BREAKDOWN → The termination, cancellation, or breakdown of a previously established collaboration within the Australian innovation ecosystem. *Example:* "University cancels mining tech collaboration due to funding issues."

                    5. INDUSTRY_EVENT → Relates to changes and development within specific industry sectors in Australia.
                        5.1. INDUSTRY_DEVELOPMENT → Growth, transformation, restructuring, or significant changes within an industry sector in Australia, particularly those related to innovation. *Example:* "The Australian renewable energy sector is experiencing rapid growth."

                    6. ECONOMIC_EVENT → Economic consequences directly resulting from innovation-related activities in Australia.
                        6.1. ECONOMIC_IMPACT → Measurable economic effects (e.g., job creation, increased GDP, improved competitiveness) resulting from innovation. *Example:* "The growth of the tech sector has created thousands of new jobs."

                    7. DISCUSSION_EVENT → Covers public discourse, debates, and opinions related to innovation in Australia.
                        7.1. INNOVATION_DISCUSSION → Public discussions, debates, expert opinions, or media coverage concerning innovation in Australia. *Example:* "Experts are debating the ethical implications of AI."

                    8. ECOSYSTEM_EVENT → Changes or shifts in the overall Australian innovation ecosystem's health, performance, or structure.
                        8.1. ECOSYSTEM_SHIFT → Significant changes in the Australian innovation ecosystem, such as changes in rankings, investment climate, or overall performance. *Example:* "Australia's global innovation ranking has improved significantly."


                    Entity Labels (Key Actors & Elements in Innovation Ecosystem)
                    1. ACTOR → Entities actively involved in or influencing innovation activities in Australia.
                        1.1. GOVERNMENT_ORGANIZATION → Federal, state, or local government agencies in Australia directly involved in innovation policy, funding, or programs. *Example:* "The Department of Industry, Science and Resources," "The Victorian Department of Jobs, Skills and Industry."
                        1.2. BUSINESS_ORGANIZATION → Established corporations, private-sector firms, or companies of any size operating in Australia and engaged in innovation activities. *Example:* "Atlassian," "BHP," "A small software company in Sydney."
                        1.3. ACADEMIC_INSTITUTION → Universities, research institutes, or other academic bodies in Australia conducting research or contributing to innovation. *Example:* "The University of Sydney," "CSIRO," "The Australian National University."
                        1.4. STARTUP → Emerging or early-stage innovative businesses in Australia, typically with high growth potential. *Example:* "A new fintech startup based in Melbourne," "A spin-off company from a university research lab."
                        1.5. INVESTOR → Venture capitalists, angel investors, or funding bodies actively investing in Australian ventures related to innovation. *Example:* "Square Peg Capital," "A group of angel investors in Sydney."
                        1.6. SUPPORT_ORGANIZATION → Organizations that provide support services to the Australian innovation ecosystem, such as incubators, accelerators, mentors, industry associations, or other support networks. *Example:* "Stone & Chalk," "Tech Council of Australia," "An innovation hub in Brisbane."

                    2. PERSON → Individuals involved in innovation in Australia.
                        2.1. INNOVATOR → Individuals directly involved in creating or developing innovations (e.g., entrepreneurs, researchers, inventors). *Example:* "The founder of a successful startup," "A researcher who developed a new medical device."
                        2.2. EXPERT → Individuals with advanced knowledge and recognized authority in a specific field related to innovation in Australia (e.g., thought leaders, consultants, academics). *Example:* "A leading AI researcher," "A consultant specializing in technology commercialization."

                    3. AUSTRALIAN_INNOVATION_ELEMENT → Abstract or intangible elements related to innovation in Australia.
                        3.1. TECHNOLOGY → Innovations, AI, software, platforms, tools, or technical systems relevant to the Australian innovation ecosystem. *Example:* "Artificial intelligence," "Blockchain," "A new software platform for data analysis."
                        3.2. INTELLECTUAL_PROPERTY → Patents, trademarks, copyrights, and other forms of intellectual property related to Australian innovation. *Example:* "A patent for a new medical device," "A trademark for a new software product."
                        3.3. FUNDING → Grants, capital investments, or financial resources specifically allocated to Australian innovation. *Example:* "$10 million in government grants for AI research," "Venture capital funding for a startup."
                        3.4. POLICY → Laws, regulations, and government strategies directly related to innovation in Australia. *Example:* "The National Innovation and Science Agenda," "A new policy on data privacy."
                        3.5. MARKET → The market for specific goods or services within Australia, particularly those related to innovation. *Example:* "The Australian market for electric vehicles," "The global market for renewable energy technology."
                        3.6. INDUSTRY → A group of companies offering similar products or services within Australia, particularly those involved in innovation. *Example:* "The Australian mining industry," "The Australian software industry," "The Australian space industry."
                        3.7. LOCAL_DEMAND → Local economic needs, market demands, or community requirements and preferences within Australia, especially those driving innovation. *Example:* "The local demand for skilled software engineers in Sydney," "The need for more affordable housing in rural areas."
                        3.8. PUBLIC_SENTIMENT → General feelings, attitudes, and opinions of the Australian public towards a particular issue, event, or entity related to innovation. *Example:* "Public opinion on the use of AI in healthcare," "Public support for government investment in renewable energy."
                        3.9. STATS → Statistical data, figures, or numerical information specifically related to innovation in Australia. *Example:* "Australia's R&D expenditure as a percentage of GDP," "The number of AI startups in Melbourne."

                    4. LOCATION → Geographic areas within Australia.
                        4.1. LOCATION → Geographic areas within Australia, such as suburbs, cities, states, or the country as a whole. *Example:* "Sydney,", "Adelaide", "Brisbane", "Perth", "Victoria," "Australia," "Regional Australia."
                        4.2. INNOVATION_HUB → Physical or digital innovation hubs, precincts, or districts within Australia designed to foster innovation. *Example:* "The Melbourne Biomedical Precinct," "The Sydney Startup Hub," "A technology park in Adelaide."

                    5. INFRASTRUCTURE → Supporting systems for innovation in Australia.
                        5.1. INFRASTRUCTURE → Physical or digital systems that support innovation in Australia (e.g., labs, co-working spaces, broadband networks). *Example:* "National broadband network," "A university research lab," "A co-working space in Sydney."

                    6. PROGRAM_INITIATIVE → Specific projects or organized efforts related to innovation in Australia.
                        6.1. PROGRAM_INITIATIVE → Government or private innovation-related initiatives in Australia (e.g., specific funding programs, research collaborations, government strategies). *Example:* "The Australian Space Agency's Moon to Mars program," "A government program to support small businesses," "A university research collaboration on AI."
                                        
                                        
                **Input & Expected Output Examples (with Rationale)**
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
                    "event_trigger": "announced",
                    "participants": [
                        {"participant_text": "The Australian Government", "participant_id": "5001", "relation_type": "ARG0", "entity_label": "GOVERNMENT_ORGANIZATION", "rationale": "The Australian Government is a specific governmental body directly involved in innovation policy."},
                        {"participant_text": "$10 million investment", "participant_id": "5002", "relation_type": "ARG1", "entity_label": "FUNDING_ALLOCATION", "rationale": "This is a specific allocation of funds, not just general funding."},
                        {"participant_text": "AI startups", "participant_id": "5003", "relation_type": "ARG2", "entity_label": "STARTUP", "rationale": "AI startups are early-stage innovative businesses."}
                    ],
                    "event_type": "FUNDING_ALLOCATION",
                    "rationale": "The event trigger 'announced' and the context of a government investment clearly indicate a funding allocation event."
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
                    "event_trigger": "debated",
                    "participants": [
                        {"participant_text": "Experts", "participant_id": "6010", "relation_type": "ARG0", "entity_label": "EXPERT", "rationale": "Experts are individuals with advanced knowledge in a specific field."},
                        {"participant_text": "the impact of artificial intelligence", "participant_id": "6011", "relation_type": "ARG1", "entity_label": "TECHNOLOGY", "rationale": "Artificial intelligence is a specific technology."},
                        {"participant_text": "the workforce", "participant_id": "6012", "relation_type": "ARG2", "entity_label": "TALENT", "rationale": "The workforce represents skilled individuals, a key aspect of talent within the innovation ecosystem."}
                    ],
                    "event_type": "INNOVATION_DISCUSSION",
                    "rationale": "The event trigger 'debated' and the context of discussing the impact of AI indicate an innovation discussion event."
                    }
                    
                Example 3: Collaboration Initiative (Government & Academia)
                Input: {
                        "sentence_as_context": "The University of Sydney and the NSW Government launched a joint initiative to boost quantum computing research in the state.",
                        "eventId": "301",
                        "event_trigger": "launched",
                        "participants": [
                            {"participant_text": "The University of Sydney", "participant_id": "7001", "relation_type": "ARG0"},
                            {"participant_text": "the NSW Government", "participant_id": "7002", "relation_type": "ARG0"},
                            {"participant_text": "a joint initiative to boost quantum computing research", "participant_id": "7003", "relation_type": "ARG1"}
                        ]
                        }
                    
                Output: {
                            "sentence_as_context": "The University of Sydney and the NSW Government launched a joint initiative to boost quantum computing research in the state.",
                            "eventId": "301",
                            "event_trigger": "launched",
                            "participants": [
                                {"participant_text": "The University of Sydney", "participant_id": "7001", "relation_type": "ARG0", "entity_label": "ACADEMIC_INSTITUTION", "rationale": "The University of Sydney is a recognized academic institution in Australia."},
                                {"participant_text": "the NSW Government", "participant_id": "7002", "relation_type": "ARG0", "entity_label": "GOVERNMENT_ORGANIZATION", "rationale": "The NSW Government is a specific governmental body within Australia."},
                                {"participant_text": "a joint initiative to boost quantum computing research", "participant_id": "7003", "relation_type": "ARG1", "entity_label": "PROGRAM_INITIATIVE", "rationale": "This is a specific, organized effort aimed at promoting research."}
                            ],
                            "event_type": "COLLABORATION_INITIATIVE",
                            "rationale": "The event trigger 'launched' and the context of a joint effort between a university and the government to boost research indicate a collaboration initiative."
                            }
                            
                            
                Example 4: Technology Deployment
                Input: {
                        "sentence_as_context": "Australian hospitals are increasingly adopting AI-powered diagnostic tools to improve patient care.",
                        "eventId": "401",
                        "event_trigger": "adopting",
                        "participants": [
                            {"participant_text": "Australian hospitals", "participant_id": "8001", "relation_type": "ARG0"},
                            {"participant_text": "AI-powered diagnostic tools", "participant_id": "8002", "relation_type": "ARG1"}
                        ]
                        }
                        
                Output: {
                        "sentence_as_context": "Australian hospitals are increasingly adopting AI-powered diagnostic tools to improve patient care.",
                        "eventId": "401",
                        "event_trigger": "adopting",
                        "participants": [
                            {"participant_text": "Australian hospitals", "participant_id": "8001", "relation_type": "ARG0", "entity_label": "BUSINESS_ORGANIZATION", "rationale": "Hospitals, in this context, act as business organizations within the healthcare industry."},
                            {"participant_text": "AI-powered diagnostic tools", "participant_id": "8002", "relation_type": "ARG1", "entity_label": "TECHNOLOGY", "rationale": "AI-powered diagnostic tools are specific technological innovations."}
                        ],
                        "event_type": "TECHNOLOGY_DEPLOYMENT",
                        "rationale": "The event trigger 'adopting' and the context of hospitals using new technology indicate technology deployment."
                        }
                        
                        
                Example 5: Startup Activity (Funding Round)
                Input: {
                        "sentence_as_context": "Melbourne-based fintech startup, 'FinTech Innovations', secured $5 million in Series A funding led by 'Venture Capital Australia'.",
                        "eventId": "501",
                        "event_trigger": "secured",
                        "participants": [
                            {"participant_text": "Melbourne-based fintech startup, 'FinTech Innovations'", "participant_id": "9001", "relation_type": "ARG0"},
                            {"participant_text": "$5 million in Series A funding", "participant_id": "9002", "relation_type": "ARG1"},
                            {"participant_text": "'Venture Capital Australia'", "participant_id": "9003", "relation_type": "ARG2"}
                        ]
                        }
                        
                Output: {
                        "sentence_as_context": "Melbourne-based fintech startup, 'FinTech Innovations', secured $5 million in Series A funding led by 'Venture Capital Australia'.",
                        "eventId": "501",
                        "event_trigger": "secured",
                        "participants": [
                            {"participant_text": "Melbourne-based fintech startup, 'FinTech Innovations'", "participant_id": "9001", "relation_type": "ARG0", "entity_label": "STARTUP", "rationale": "'FinTech Innovations' is a newly established, innovative business in the financial technology sector."},
                            {"participant_text": "$5 million in Series A funding", "participant_id": "9002", "relation_type": "ARG1", "entity_label": "FUNDING_ALLOCATION", "rationale": "Series A funding represents a specific allocation of investment capital."},
                            {"participant_text": "'Venture Capital Australia'", "participant_id": "9003", "relation_type": "ARG2", "entity_label": "INVESTOR", "rationale": "'Venture Capital Australia' is a company that provides investment funding to startups."}
                        ],
                        "event_type": "STARTUP_ACTIVITY",
                        "rationale": "The event trigger 'secured' and the context of a startup receiving funding indicate startup activity (specifically a funding round)."
                        }
                        
                        
                Example 7: Complex Sentence with Multiple Entities
                Input: {
                        "sentence_as_context": "CSIRO, in partnership with several Australian universities and supported by a $2 million government grant, is researching new methods for producing hydrogen fuel.",
                        "eventId": "701",
                        "event_trigger": "researching",
                        "participants": [
                            {"participant_text": "CSIRO", "participant_id": "10001", "relation_type": "ARG0"},
                            {"participant_text": "several Australian universities", "participant_id": "10002", "relation_type": "ARG0"},
                            {"participant_text": "new methods for producing hydrogen fuel", "participant_id": "10003", "relation_type": "ARG1"},
                            {"participant_text": "$2 million government grant", "participant_id": "10004", "relation_type": "ARGM-SUP"}
                        ]
                        }
                        
                Output: {
                        "sentence_as_context": "CSIRO, in partnership with several Australian universities and supported by a $2 million government grant, is researching new methods for producing hydrogen fuel.",
                        "eventId": "701",
                        "event_trigger": "researching",
                        "participants": [
                            {"participant_text": "CSIRO", "participant_id": "10001", "relation_type": "ARG0", "entity_label": "ACADEMIC_INSTITUTION", "rationale": "CSIRO is a prominent Australian research organization."},
                            {"participant_text": "several Australian universities", "participant_id": "10002", "relation_type": "ARG0", "entity_label": "ACADEMIC_INSTITUTION", "rationale": "Universities are academic institutions."},
                            {"participant_text": "new methods for producing hydrogen fuel", "participant_id": "10003", "relation_type": "ARG1", "entity_label": "TECHNOLOGY", "rationale": "Hydrogen fuel and its production methods represent technology."},
                            {"participant_text": "$2 million government grant", "participant_id": "10004", "relation_type": "ARGM-SUP", "entity_label": "FUNDING_ALLOCATION", "rationale": "The grant is a specific allocation of government funds for research."}
                        ],

                Example 3: Industry Development
                Input: 
                {'sentence_as_context': 'Since 2014, Australia’s IT exports have grown 400 per cent and we’ve spent around $8 billion on R&D.', 'eventId': '139', 'event_trigger': 'grown', 'participants': [{'participant_text': 'Australia’s IT exports', 'participant_id': '38', 'relation_type': 'ARG1'}, {'participant_text': '1_639_651_PERCENT', 'participant_id': '6222', 'relation_type': 'ARG2'}]}

                Output:
                {
                    "sentence_as_context": "Since 2014, Australia’s IT exports have grown 400 per cent and we’ve spent around $8 billion on R&D.",
                    "eventId": "139",
                    "event_trigger": "grown",
                    "participants": [
                        {"participant_text": "Australia’s IT exports", "participant_id": "38", "relation_type": "ARG1", "entity_label": "INDUSTRY", "rationale": "IT exports represent the output and growth of the Australian IT industry."},
                        {"participant_text": "400 per cent", "participant_id": "6222", "relation_type": "ARG2", "entity_label": "STATS", "rationale": "Percentage growth is statistical data reflecting industry development."}
                    ],
                    "event_type": "INDUSTRY_DEVELOPMENT",
                    "rationale": "The event trigger 'grown' and the context of IT export growth signify industry development."
                    }
                    
                    
                    
                    **Some More Examples**
                   // Policy Events
                    {
                    input: {
                        "sentence_as_context": "The Australian government announced a new $200 million fund to support the development of green hydrogen projects.",
                        "eventId": "1001",
                        "event_trigger": "announced",
                        "participants": [
                        {"participant_text": "The Australian government", "participant_id": "10001", "relation_type": "ARG0"},
                        {"participant_text": "a new $200 million fund", "participant_id": "10002", "relation_type": "ARG1"},
                        {"participant_text": "the development of green hydrogen projects", "participant_id": "10003", "relation_type": "ARG2"}
                        ]
                    },
                    output: {
                        "sentence_as_context": "The Australian government announced a new $200 million fund to support the development of green hydrogen projects.",
                        "eventId": "1001",
                        "event_trigger": "announced",
                        "participants": [
                        {"participant_text": "The Australian government", "participant_id": "10001", "relation_type": "ARG0", "entity_label": "GOVERNMENT_ORGANIZATION", "rationale": "The Australian government is the governing body of Australia, fitting the definition of GOVERNMENT_ORGANIZATION."},
                        {"participant_text": "a new $200 million fund", "participant_id": "10002", "relation_type": "ARG1", "entity_label": "FUNDING", "rationale": "This is a specific allocation of financial resources, fitting the definition of FUNDING."},
                        {"participant_text": "the development of green hydrogen projects", "participant_id": "10003", "relation_type": "ARG2", "entity_label": "TECHNOLOGY", "rationale": "Green hydrogen projects represent technological development, fitting the definition of TECHNOLOGY."}
                        ],
                        "event_type": "POLICY_ANNOUNCEMENT",
                        "rationale": "The event trigger 'announced' and the context of a new government fund indicate a policy announcement, fitting the definition of POLICY_ANNOUNCEMENT."
                    }
                    }

                    {
                    input: {
                        "sentence_as_context": "Changes to the research and development tax incentive scheme were implemented on July 1st.",
                        "eventId": "1002",
                        "event_trigger": "implemented",
                        "participants": [
                        {"participant_text": "Changes to the research and development tax incentive scheme", "participant_id": "10004", "relation_type": "ARG1"}
                        ]
                    },
                    output: {
                        "sentence_as_context": "Changes to the research and development tax incentive scheme were implemented on July 1st.",
                        "eventId": "1002",
                        "event_trigger": "implemented",
                        "participants": [
                        {"participant_text": "Changes to the research and development tax incentive scheme", "participant_id": "10004", "relation_type": "ARG1", "entity_label": "POLICY", "rationale": "The R&D tax incentive scheme is a government policy, fitting the definition of POLICY."}
                        ],
                        "event_type": "POLICY_EVENT",
                        "rationale": "The event trigger 'implemented' and the context of changes to a government tax incentive scheme indicate a policy event, fitting the definition of POLICY_EVENT."
                    }
                    }

                    // Financial Events
                    {
                    input: {
                        "sentence_as_context": "A Melbourne-based startup, 'BioTech Innovations', secured $10 million in Series B funding led by 'Global Venture Partners'.",
                        "eventId": "1003",
                        "event_trigger": "secured",
                        "participants": [
                        {"participant_text": "BioTech Innovations", "participant_id": "10005", "relation_type": "ARG0"},
                        {"participant_text": "$10 million in Series B funding", "participant_id": "10006", "relation_type": "ARG1"},
                        {"participant_text": "Global Venture Partners", "participant_id": "10007", "relation_type": "ARG2"}
                        ]
                    },
                    output: {
                        "sentence_as_context": "A Melbourne-based startup, 'BioTech Innovations', secured $10 million in Series B funding led by 'Global Venture Partners'.",
                        "eventId": "1003",
                        "event_trigger": "secured",
                        "participants": [
                        {"participant_text": "BioTech Innovations", "participant_id": "10005", "relation_type": "ARG0", "entity_label": "STARTUP", "rationale": "BioTech Innovations is an early-stage innovative business, fitting the definition of STARTUP."},
                        {"participant_text": "$10 million in Series B funding", "participant_id": "10006", "relation_type": "ARG1", "entity_label": "FUNDING", "rationale": "This is a specific amount of financial resources, fitting the definition of FUNDING."},
                        {"participant_text": "Global Venture Partners", "participant_id": "10007", "relation_type": "ARG2", "entity_label": "INVESTOR", "rationale": "Global Venture Partners is a funding body investing in ventures, fitting the definition of INVESTOR."}
                        ],
                        "event_type": "FUNDING_ALLOCATION",
                        "rationale": "The event trigger 'secured' and the context of a startup receiving funding indicate a funding allocation event, fitting the definition of FUNDING_ALLOCATION."
                    }
                    }

                    {
                    input: {
                        "sentence_as_context": "The CSIRO allocated $2 million to a research project focused on developing new drought-resistant crops.",
                        "eventId": "1004",
                        "event_trigger": "allocated",
                        "participants": [
                        {"participant_text": "The CSIRO", "participant_id": "10008", "relation_type": "ARG0"},
                        {"participant_text": "$2 million", "participant_id": "10009", "relation_type": "ARG1"},
                        {"participant_text": "a research project focused on developing new drought-resistant crops", "participant_id": "10010", "relation_type": "ARG2"}
                        ]
                    },
                    output: {
                        "sentence_as_context": "The CSIRO allocated $2 million to a research project focused on developing new drought-resistant crops.",
                        "eventId": "1004",
                        "event_trigger": "allocated",
                        "participants": [
                        {"participant_text": "The CSIRO", "participant_id": "10008", "relation_type": "ARG0", "entity_label": "ACADEMIC_INSTITUTION", "rationale": "CSIRO is a research organization, fitting the definition of ACADEMIC_INSTITUTION."},
                        {"participant_text": "$2 million", "participant_id": "10009", "relation_type": "ARG1", "entity_label": "FUNDING", "rationale": "This is a specific amount of financial resources, fitting the definition of FUNDING."},
                        {"participant_text": "a research project focused on developing new drought-resistant crops", "participant_id": "10010", "relation_type": "ARG2", "entity_label": "PROGRAM_INITIATIVE", "rationale": "This is a specific research project, fitting the definition of PROGRAM_INITIATIVE."}
                        ],
                        "event_type": "FUNDING_ALLOCATION",
                        "rationale": "The event trigger 'allocated' and the context of CSIRO providing funds to a research project indicate a funding allocation event, fitting the definition of FUNDING_ALLOCATION."
                    }
                    }





                    Instructions for the LLM
                    1.  **Strict Ontology Adherence:** Use *only* the provided ontology for labeling.  Do not generate new labels.
                    2.  **Most Specific Label:** Choose the most specific applicable label for each entity/event. If can't be determined, use a more general label.
                    3.  **Single Label per Entity/Event:** Assign only one label per entity/event.
                    4.  **strictly follow the output format as shown in the examples above. And verify always the response whether it complies with the output format as shown in the examples above**
                    
                    The input is: """

    @property
    def LLM_PROMPT2(self):
        return """
                Role Description
                You are an expert in information extraction focused on the Australian innovation ecosystem.  Your task is to identify and label entities and events within text related to this domain. Your task is to analyze Semantic Role Labeling (SRL) output, identify events, assess participants, and assign structured domain-specific labels using a predefined ontology.

                
                
                ** Ontology **
                Use the following predefined categories for event and entity classification. Do not generate new labels—only use these.

                ** Event Categories/Types (Action or Discussion Related to Innovation) **
                1. POLICY_EVENT → Encompasses government actions and announcements related to innovation in Australia. Government policy, strategy, or regulatory updates.
                1.1. POLICY_ANNOUNCEMENT → Government policy, strategy, or regulatory updates impacting Australian innovation, e.g., new funding schemes, changes to tax incentives for R&D.
                2. FINANCIAL_EVENT → Financial transactions, investments, funding allocations, or economic activities related to innovation.
                2.1. FUNDING_ALLOCATION → Financial grants, investments, or funding commitments made to Australian startups, research institutions, or innovation hubs. For example, "Government allocates $10 million to AI research".
                3. INNOVATION_DEVELOPMENT_EVENT → Focuses on progress and activities related to innovation in Australia. For example, Development, research, or progress in technology/innovation, e.g., "New AI technology developed by Australian researchers".
                3.1. INNOVATION_ACTIVITY → Development, research, or progress in technology/innovation by Australian entities, e.g., new software development, advancements in renewable energy research.Development, research, or progress in technology/innovation.
                3.2. TECHNOLOGY_DEPLOYMENT → Implementation of new technology in practice within Australian industries or organizations. For example, "New AI technology deployed in healthcare sector".
                3.3. RESEARCH_PUBLICATION → Scientific or research output contributing to innovation.
                3.4. STARTUP_ACTIVITY → Entrepreneurial activities such as launching or scaling startups in Australia, e.g., new startup creation, successful funding rounds, expansion into new markets, acquisitions, or exits.
                4. COLLABORATION_EVENT → Initiatives or plans to form collaboration between Government, businesses, or academia. Covers interactions and partnerships between entities within the Australian innovation ecosystem. For example, "University partners with industry to develop new technology".
                4.1. COLLABORATION_INITIATIVE → Initiatives or plans to form collaboration between Government, businesses, or academia.
                4.2. COLLABORATION → Partnerships, agreements, or collaborations between Australian entities, e.g., joint ventures, research partnerships, knowledge sharing agreements. For example, "University collaborates with industry on AI research".
                4.3. COLLABORATION_BREAKDOWN →  Indicates breakdown of collaborations within the Australian innovation ecosystem, e.g., "University cancels mining tech collaboration. It indicates breakdown such as "withdrew," "cancels," "dispute," "failed partnership" etc. for example, "University cancels mining tech collaboration".
                5. INDUSTRY_EVENT → Relates to changes and development within industries.   I
                5.1. INDUSTRY_DEVELOPMENT → Growth, transformation, or structuring of an industry sector. For example, "Australian tech industry grows by 10% in 2021".
                6. ECONOMIC_EVENT → Economic consequences of innovation-related activities. e.g., job creation, increased GDP, improved competitiveness. For example, "AI industry creates 1000 new jobs in Australia".
                6.1. ECONOMIC_IMPACT → Economic consequences of innovation-related activities. e.g., job creation, increased GDP, improved competitiveness. For example, "AI industry creates 1000 new jobs in Australia".
                7. DISCUSSION_EVENT → Covers public discourse and debates related to innovation in Australia. Public discourse, expert opinions, or debates about innovation in Australia, e.g., media articles discussing the effectiveness of innovation policies. For example, "Experts debate the impact of AI on the workforce".
                7.1. INNOVATION_DISCUSSION → Covers public discourse and debates related to innovation in Australia. Public discourse, expert opinions, or debates about innovation in Australia, e.g., media articles discussing the effectiveness of innovation policies. For example, "Experts debate the impact of AI on the workforce".
                8. ECOSYSTEM_EVENT → Changes in the Australian innovation ecosystem's health or performance. For example, "declined," "improved," "recommended", e.g., "Cluster development ranking drops to 39th".
                8.1. ECOSYSTEM_SHIFT → Relates to changes in the Australian innovation ecosystem's health or performance. For example, "declined," "improved," "recommended", e.g., "Cluster development ranking drops to 39th". Examples include "Cluster development ranking drops to 39th," "Ecosystem improved," changes in investment climate.
                
                ** Entity Labels (Key Actors & Elements in Innovation Ecosystem) **
                1. ACTOR → Entities directly involved in or influencing innovation activities in Australia.
                1.1. GOVERNMENT_ORGANIZATION → Federal, state, or local government agencies in Australia, directly involved in innovation policy, funding, or programs.
                1.2. BUSINESS_ORGANIZATION → Established corporations or private-sector firms operating in Australia, engaged in innovation activities.
                1.3. ACADEMIC_INSTITUTION → Universities, research institutes, or other academic bodies in Australia.
                1.4. STARTUP → Emerging or early-stage innovative businesses in Australia.
                1.5. INVESTOR → Venture capitalists, angel investors, or funding bodies actively investing in Australian ventures.
                1.6. SUPPORT_ORGANIZATION → Incubators, accelerators, mentors, industry associations, or other organizations that support innovation.

                2. PERSON → Individuals involved in innovation in Australia.
                2.1. INNOVATOR → Individuals directly involved in creating or developing innovations (e.g., entrepreneurs, researchers, inventors).
                2.2. EXPERT → Individuals with advanced knowledge and recognized authority in a specific field of innovation in Australia (e.g., thought leaders, consultants).

                3. AUSTRALIAN_INNOVATION_ELEMENT → Abstract or intangible elements related to innovation in Australia.
                3.1. TECHNOLOGY → Innovations, AI, software, platforms, tools, or technical systems relevant to the Australian context.
                3.2. INTELLECTUAL_PROPERTY → Patents, trademarks, copyrights, and other forms of intellectual property related to Australian innovation.
                3.3. FUNDING → Grants, capital investments, or financial resources available for Australian innovation.
                3.4. POLICY → Laws, regulations, and government strategies related to innovation in Australia.
                3.5. MARKET → The market for specific goods or services within Australia, e.g., the Australian market for electric vehicles.
                3.6. INDUSTRY → A group of companies that offer similar products or services within Australia, e.g., the Australian mining industry.
                3.7. LOCAL_DEMAND → Local economic needs, market demands, or community requirements and preferences within Australia.
                3.8. PUBLIC_SENTIMENT → General feelings, attitudes, and opinions of the Australian public towards a particular issue, event, or entity related to innovation.
                3.9. STATS → Statistical data, figures, or numerical information related to innovation in Australia.

                4. LOCATION → Geographic areas within Australia.
                4.1. LOCATION → Geographic areas within Australia, such as cities, states, or the country as a whole.
                4.2. INNOVATION_HUB → Physical/digital innovation hubs or innovation districts within Australia, e.g., "Sydney Startup Hub," "Perth Innovation Precinct."

                5. INFRASTRUCTURE → Supporting systems for innovation in Australia.
                5.1. INFRASTRUCTURE → Physical or digital systems that support innovation in Australia (e.g., labs, co-working spaces, broadband networks).

                6. PROGRAM_INITIATIVE → Specific projects or organized efforts.
                6.1. PROGRAM_INITIATIVE → Government or private innovation-related initiatives in Australia (e.g., specific funding programs, research collaborations).
                
                ** Input & Expected Output Examples **
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
                    "event_trigger": "announced",
                    "participants": [
                        {"participant_text": "The Australian Government", "participant_id": "5001", "relation_type": "ARG0", "entity_label": "GOVERNMENT_ORGANIZATION", "rationale": "The Australian Government is a specific governmental body directly involved in innovation policy."},
                        {"participant_text": "$10 million investment", "participant_id": "5002", "relation_type": "ARG1", "entity_label": "FUNDING_ALLOCATION", "rationale": "This is a specific allocation of funds, not just general funding."},
                        {"participant_text": "AI startups", "participant_id": "5003", "relation_type": "ARG2", "entity_label": "STARTUP", "rationale": "AI startups are early-stage innovative businesses."}
                    ],
                    "event_type": "FUNDING_ALLOCATION",
                    "rationale": "The event trigger 'announced' and the context of a government investment clearly indicate a funding allocation event."
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
                    "event_trigger": "debated",
                    "participants": [
                        {"participant_text": "Experts", "participant_id": "6010", "relation_type": "ARG0", "entity_label": "EXPERT", "rationale": "Experts are individuals with advanced knowledge in a specific field."},
                        {"participant_text": "the impact of artificial intelligence", "participant_id": "6011", "relation_type": "ARG1", "entity_label": "TECHNOLOGY", "rationale": "Artificial intelligence is a specific technology."},
                        {"participant_text": "the workforce", "participant_id": "6012", "relation_type": "ARG2", "entity_label": "TALENT", "rationale": "The workforce represents skilled individuals, a key aspect of talent within the innovation ecosystem."}
                    ],
                    "event_type": "INNOVATION_DISCUSSION",
                    "rationale": "The event trigger 'debated' and the context of discussing the impact of AI indicate an innovation discussion event."
                    }


                Example 3: Industry Development
                Input: 
                {'sentence_as_context': 'Since 2014, Australia’s IT exports have grown 400 per cent and we’ve spent around $8 billion on R&D.', 'eventId': '139', 'event_trigger': 'grown', 'participants': [{'participant_text': 'Australia’s IT exports', 'participant_id': '38', 'relation_type': 'ARG1'}, {'participant_text': '1_639_651_PERCENT', 'participant_id': '6222', 'relation_type': 'ARG2'}]}

                Output:
                {
                    "sentence_as_context": "Since 2014, Australia’s IT exports have grown 400 per cent and we’ve spent around $8 billion on R&D.",
                    "eventId": "139",
                    "event_trigger": "grown",
                    "participants": [
                        {"participant_text": "Australia’s IT exports", "participant_id": "38", "relation_type": "ARG1", "entity_label": "INDUSTRY", "rationale": "IT exports represent the output and growth of the Australian IT industry."},
                        {"participant_text": "400 per cent", "participant_id": "6222", "relation_type": "ARG2", "entity_label": "STATS", "rationale": "Percentage growth is statistical data reflecting industry development."}
                    ],
                    "event_type": "INDUSTRY_DEVELOPMENT",
                    "rationale": "The event trigger 'grown' and the context of IT export growth signify industry development."
                    }

                 The input is: 
                """
            
 
 
def main():
    #llm_api = "http://localhost:11434/api/generate"  # Replace with your actual LLM API endpoint
    llm_api = "http://10.1.128.128:11434/api/generate"  # Replace with your actual LLM API endpoint
    enricher = SRLEnricher(argv=[],llm_api=llm_api)
    
    # 1. get the dataset from the database i.e., neo4j. 
    # 2. transform each dataitem from dataset into a format that can be used by the LLM model. i.e., remove the unwanted data and keep the necessary data. return transformed data.
    data = enricher.retrieve_data()
    print("Retrieved Data:", data)
    
    # 3. Loop through the transformed data and send each dataitem to the LLM model.
    for item in data:
        #   4. Now for each transformed datatiem, define the prompt for the LLM model.
        prompt = enricher.create_prompt_for_llm(item)
        #print("Generated Prompt for LLM:")
        #print(prompt)
        #   5. send the prompt to the LLM model and get the response.
        max_retries = 2
        attempts = 0
        while attempts < max_retries:
            response = enricher.call_llm(prompt=prompt)
            # 6. process the response and generate the cypher queries. These cypher queries will be used to update the database.
            try:
                cypher_queries = enricher.generate_cypher_queries(response=response)
                break  # Exit the loop if successful
            except ValueError as e:
                logging.error("Error generating Cypher queries: %s", e)
                attempts += 1

        if attempts == max_retries:
            logging.error("Failed to generate Cypher queries after %d attempts", max_retries)
            continue  # ignore this dataitem and move to the next one.

        # logging.info("Generated Cypher Queries: %s", cypher_queries)
        # 7. execute the cypher queries to update the database.
        #for query in cypher_queries:
            #enricher.execute_neo4j_query(query)
            #enricher.neo4j_repo.execute_query(query, {})
            #logging.info("Executed Cypher Query: %s", query)
            
    # 8. Repeat the process for each dataitem in the dataset.
    # 9. Once all dataitems are processed, the database will be updated with the enriched data.
    # 10. The process is complete.
    
           
if __name__ == "__main__":
    main()


