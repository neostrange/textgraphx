import logging
from text_processing_components.EntityExtractor import EntityExtractor
from TextProcessor import Neo4jRepository
from py2neo import Graph
from util.GraphDbBase import GraphDBBase

class RunEntityExtractor(GraphDBBase):
    
    def __init__(self, argv, **kwargs):
        super().__init__(command=__file__, argv=argv)
        self.setup_logging()
        self.neo4j_repo = self.setup_neo4j_connection()
        self.api_url = "http://127.0.0.1:11435/process_text"
        self.extractor = EntityExtractor("http://127.0.0.1:11435/process_text", self._driver)

    def setup_logging(self):
        """Configure logging settings."""
        logging.basicConfig(level=logging.INFO)

    def setup_neo4j_connection(self):
        """Establish a connection to the Neo4j database."""
        # Replace with your actual Neo4j connection details
        #driver = Graph("your_neo4j_uri", auth=("your_username", "your_password"))
        return Neo4jRepository(self._driver)

    def extract_entities(self, sample_text):
        """Use the EntityExtractor to extract entities from the provided text."""
        
        try:
            entities = self.extractor.extract_entities(sample_text)
            if not entities:
                logging.warning("No entities extracted.")
            return entities
        except Exception as e:
            logging.error(f"An error occurred during entity extraction: {e}")
            return []

    def integrate_entities(self, entities, document_id):
        """Integrate the extracted entities into the Neo4j database."""
        try:
            if entities:
                self.extractor.integrate_entities_into_db(entities, document_id)
                logging.info("Entities integrated successfully.")
        except Exception as e:
            logging.error(f"An error occurred during entity integration: {e}")

# Sample usage
if __name__ == "__main__":
    sample_text = """Australia has established a healthy digital economy over the last decade, and Aussie businesses have embraced the latest technologies to take advantage of efficiencies and scale. However, to remain healthy and competitive in this crucial space, serious resourcing challenges and fundamental need to be overcome. Technology contributes over $124 billion to the Australian economy each year, and in the past decade IT job growth stands at 60 per cent, which is twice the national average, according to the 10th ACS Digital Pulse by Deloitte Access Economics for the Australian Computer Society. Since 2014, Australia’s IT exports have grown 400 per cent and we’ve spent around $8 billion on R&D. These impressive stats indicate a booming tech industry but there are cracks in the foundations that need to be addressed. “It’s been an incredibly important decade for the Australian tech industry but we need to make changes to continue our healthy growth,” Josh Griggs ACS chief executive said. “It’s alarming that there is a long-term shortage of technical talent and we have serious problems diversifying the tech workforce.” There are over 1 million tech workers in Australia but for the Australian IT industry to maintain healthy growth, it will need an additional 300,000 people by 2035. Mr Griggs said a lack of awareness about the diverse range of tech careers, especially amongst the young, has created an unconscious bias against the industry. “Every company is now a tech company and yet the school curriculum is still largely focussed on computer programming — it’s a bit stale. There are a diverse and fascinating range of careers in IT that do not involve coding or fixing servers,” Mr Griggs said. “If we had an IT school curriculum more aligned to industry needs, then the kids would have the option to walk into a tech job regardless of whether they go to university or not.” The 2024 ACS Digital Pulse discovered that 80 per cent of advertised tech jobs required a university degree, which Mr Griggs stressed isn’t necessary. “A degree is a great pathway but there are very viable alternative pathways — when an industry certification combined with on-the-job experience can make an equally capable employee,” Mr Griggs said. “We could be offering more practical options with training on specific applications for industry verticals.” ACS is active in promoting technology careers. It recently partnered with Supernova for a Level Up career day in Brisbane, where about 1,700 students gathered for an event combining pop culture and tech careers. “Level Up was great — huge credit to Supanova. There were gaming companies explaining potential career paths, and the Australian Defence Force (ADF) brought a flight simulator,” Mr Griggs said. “Young people are already engrossed in using technology, now we need them to get involved and continue our progress for future generations.” More than 5 million Australians already use generative AI at work, a figure that has increased 20 per cent so far this year, but the country is lagging behind the rest of Asia. According to the report, only 15 per cent of Australian businesses use generative AI, putting Australia 12th out of 13 countries in the Asia Pacific region. In AI talent, Australia is dead last, 6th out of 6 markets. “You won’t lose your job to AI but you will lose your job to someone that uses AI. It’s a big opportunity and incredibly important to Australia,” said Mr Griggs. “These numbers are alarming, and actions need to be taken because not enough new talent is coming through.” To be competitive in AI, Griggs said we need to start integrating it nationally into school curriculums, training programs, and any other field of study because it’s already a necessary tool. “Kids should be learning how to use prompts to get the best outcomes and use AI to improve efficiency. There should also be industry specific AI training, and more done to support the responsible use of AI. “We need advisory networks providing guardrails, best practices, and essential security guidelines to increase competence and confidence,” Mr Griggs said. According to ACS Digital Pulse 2024, the number of job adverts requesting cyber skills has increased more than 80 per cent since 2020, and cybersecurity professionals command a wage premium of almost 30 per cent. The report highlights that only 0.1 per cent of job advertisements explicitly offer part-time positions, and cybersecurity adverts were most likely to use stereotypically masculine language. This may be one reason why cybersecurity has the least diverse workforce, with men making up 83 per cent of workers. One option for increasing the pool of tech workers is reskilling and transferring skills from ‘near tech’ roles. The report found that there are 1.1 million people with skills that are transferable to IT, and 60 per cent of them are women. “We can address the skills gap and diversify at the same time by converting project managers, business analysts and mathematicians to tech,” said Mr Griggs. “The IT industry needs a diverse range of skills, there are so many opportunities in tech. It’s vital that we all work together to keep Australia’s digital pulse healthy.”"""
    #sample_text = """Australia has established a healthy digital economy over the last decade, and Aussie businesses have embraced the latest technologies to take advantage of efficiencies and scale. However, to remain healthy and competitive in this crucial space, serious resourcing challenges and fundamental need to be overcome. Technology contributes over $124 billion to the Australian economy each year, and in the past decade IT job growth stands at 60 per cent, which is twice the national average, according to the 10th ACS Digital Pulse by Deloitte Access Economics for the Australian Computer Society. Since 2014, Australia’s IT exports have grown 400 per cent and we’ve spent around $8 billion on R&D. These impressive stats indicate a booming tech industry but there are cracks in the foundations that need to be addressed. “It’s been an incredibly important decade for the Australian tech industry but we need to make changes to continue our healthy growth,” Josh Griggs ACS chief executive said. “It’s alarming that there is a long-term shortage of technical talent and we have serious problems diversifying the tech workforce.” There are over 1 million tech workers in Australia but for the Australian IT industry to maintain healthy growth, it will need an additional 300,000 people by 2035. Mr Griggs said a lack of awareness about the diverse range of tech careers, especially amongst the young, has created an unconscious bias against the industry. “Every company is now a tech company and yet the school curriculum is still largely focussed on computer programming — it’s a bit stale. There are a diverse and fascinating range of careers in IT that do not involve coding or fixing servers,” Mr Griggs said. “If we had an IT school curriculum more aligned to industry needs, then the kids would have the option to walk into a tech job regardless of whether they go to university or not.” The 2024 ACS Digital Pulse discovered that 80 per cent of advertised tech jobs required a university degree, which Mr Griggs stressed isn’t necessary. “A degree is a great pathway but there are very viable alternative pathways — when an industry certification combined with on-the-job experience can make an equally capable employee,” Mr Griggs said. “We could be offering more practical options with training on specific applications for industry verticals.” ACS is active in promoting technology careers. It recently partnered with Supernova for a Level Up career day in Brisbane, where about 1,700 students gathered for an event combining pop culture and tech careers. “Level Up was great — huge credit to Supanova. There were gaming companies explaining potential career paths, and the Australian Defence Force (ADF) brought a flight simulator,” Mr Griggs said. “Young people are already engrossed in using technology, now we need them to get involved and continue our progress for future generations.” More than 5 million Australians already use generative AI at work, a figure that has increased 20 per cent so far this year, but the country is lagging behind the rest of Asia. According to the report, only 15 per cent of Australian businesses use generative AI, putting Australia 12th out of 13 countries in the Asia Pacific region. In AI talent, Australia is dead last, 6th out of 6 markets. “You won’t lose your job to AI but you will lose your job to someone that uses AI. It’s a big opportunity and incredibly important to Australia,” said Mr Griggs. “These numbers are alarming, and actions need to be taken because not enough new talent is coming through.”"""
    extractor = RunEntityExtractor(argv=[])
    entities = extractor.extract_entities(sample_text)
    extractor.integrate_entities(entities, "1")  # Replace with actual document ID
    
    
