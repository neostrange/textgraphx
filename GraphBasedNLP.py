import os
import spacy
import sys
from util.SemanticRoleLabeler import SemanticRoleLabel
from util.EntityFishingLinker import EntityFishing
from spacy.tokens import Doc, Token, Span
from util.RestCaller import callAllenNlpApi
from util.GraphDbBase import GraphDBBase
from TextProcessor import TextProcessor
import xml.etree.ElementTree as ET
from spacy.lang.char_classes import ALPHA, ALPHA_LOWER, ALPHA_UPPER
from spacy.lang.char_classes import CONCAT_QUOTES, LIST_ELLIPSES, LIST_ICONS
from spacy.util import compile_infix_regex
from neo4j import GraphDatabase
from TextProcessor import Neo4jRepository
from text_processing_components.DocumentImporter import MeantimeXMLImporter
# from spacy.util import load_config

# from spacy_llm.util import assemble
# from spacy_llm.registry import registry
# from text_processing_components.llm.registry import openai_llama_3_1_8b
# from spacy import util

# Class representing a graph-based NLP model
class GraphBasedNLP(GraphDBBase):
    # Initializes the NLP model with the given arguments
    def __init__(self, argv):
        # Calls the parent class's constructor
        super().__init__(command=__file__, argv=argv)
        
        # self.config_path="/home/neo/environments/text2graphs/textgraphx/config.cfg"  # Default value provided for config_path argument
        # self.examples_path="/home/neo/environments/text2graphs/textgraphx/examples.json" 

        # Prefer GPU for processing
        spacy.prefer_gpu()
        
        #registry.llm_models.register(openai_llama_3_1_8b)
        # Load the English language model
        self.nlp = spacy.load('en_core_web_trf')

        #config = load_config("/home/neo/environments/text2graphs/textgraphx/config.cfg")


        # Add custom components
        # for component in config["nlp"]["pipeline"]:
        #     if component not in self.nlp.pipe_names:
        #         self.nlp.add_pipe(component, config=config["components"][component])
        
        
        
        #self.nlp = assemble(config_path=self.config_path, overrides={"paths.examples": str(self.examples_path)})
        #self.nlp = assemble(config_path=self.config_path)
        print("config: ", self.nlp.config.to_str())
        #llm_component = self.nlp.add_pipe("llm", config=llm_config["components"]["llm"], last=True)


        print("PIPELINE:  ", self.nlp.pipeline)
        # Configure the tokenizer
        self._configure_tokenizer()
        
        # Add pipes to the model
        self._add_pipes()
        
        # Initialize the text processor
        self.__text_processor = TextProcessor(self.nlp, self._driver)

        self.neo4j_repository = Neo4jRepository(self._driver)
        
        # Create constraints in the database
        self.create_constraints()

    # Configures the tokenizer with custom infixes
    def _configure_tokenizer(self):
        # Define custom infixes
        infixes = (
            LIST_ELLIPSES 
            + LIST_ICONS
            + [
                r"(?<=[0-9])[+\\-\\*^](?=[0-9-])",
                r"(?<=[{al}{q}])\\.(?=[{au}{q}])".format(
                    al=ALPHA_LOWER, au=ALPHA_UPPER, q=CONCAT_QUOTES
                ),
                r"(?<=[{a}]),(?=[{a}])".format(a=ALPHA),
                r"(?<=[{a}0-9])[:<>=/](?=[{a}])".format(a=ALPHA),
            ]
        )
        
        # Compile the infix regex
        infix_re = compile_infix_regex(infixes)
        
        # Set the infix finditer for the tokenizer
        self.nlp.tokenizer.infix_finditer = infix_re.finditer

    # Adds pipes to the model
    def _add_pipes(self):
        # Add the dbpedia spotlight pipe
        self.nlp.add_pipe('dbpedia_spotlight', config={'confidence': 0.5, 'overwrite_ents': True})
        
        # Remove and re-add the srl pipe if it exists
        if "srl" in self.nlp.pipe_names:
            self.nlp.remove_pipe("srl")
            _ = self.nlp.add_pipe("srl")
        
        # Add the srl pipe
        self.nlp.add_pipe("srl")

    # Creates constraints in the database
    def create_constraints(self):
        # Define the constraints
        constraints = [
            "CREATE CONSTRAINT for (u:Tag) require u.id IS NODE KEY",
            "CREATE CONSTRAINT for (i:TagOccurrence) require i.id IS NODE KEY",
            "CREATE CONSTRAINT for (t:Sentence) require t.id IS NODE KEY",
            "CREATE CONSTRAINT for (l:AnnotatedText) require l.id IS NODE KEY",
            "CREATE CONSTRAINT for (l:NamedEntity) require l.id IS NODE KEY",
            "CREATE CONSTRAINT for (l:Entity) require (l.type, l.id) IS NODE KEY",
            "CREATE CONSTRAINT for (l:Evidence) require l.id IS NODE KEY",
            "CREATE CONSTRAINT for (l:Relationship) require l.id IS NODE KEY",
            "CREATE CONSTRAINT for (l:NounChunk) require l.id IS NODE KEY",
            "CREATE CONSTRAINT for (l:TEvent) require (l.eiid, l.doc_id) IS NODE KEY",
            "CREATE CONSTRAINT for (l:TIMEX) require (l.tid, l.doc_id) IS NODE KEY"
        ]
        
        # Execute each constraint
        for constraint in constraints:
            self.execute_without_exception(constraint)

    # Stores a corpus of text in the database
    def store_corpus(self, directory):
        
        # Query the database to get the count of AnnotatedText nodes
        query = "MATCH (n:AnnotatedText) RETURN count(n) as count"
        result = self.neo4j_repository.execute_query(query=query, params={})
        count = result[0]['count'] if result else 0
        
        # Initialize the text ID based on the count of documents
        text_id = count + 1
        
        # Initialize the list of text tuples
        text_tuples = []
        
        # Iterate over each file in the directory
        for filename in os.listdir(directory):
            # Construct the full path to the file
            f = os.path.join(directory, filename)
            
            # Check if the file is a file
            if os.path.isfile(f):
                # Print the filename
                print(filename)

                try:
                    # Parse the XML file
                    tree = ET.parse(directory+'/' + filename)
                    root = tree.getroot()
                    
                    # Extract the text from the XML file
                    text = root[1].text
                    # If there is no whitespace in between sentences, usually been observed in web scraped text, then add a whitespace
                    # in between full stop and CRLF. 
                    text = text.replace(".\n", ". \n")
                    # we are replacing newlines with a single-space. It is due to fix incorrect sentence segmentation in spacy
                    # which does not take into the consideration the double quotes as a sentence end. 
                    text = text.replace('”\n', '” ') # some sentences end with a double quote and then there is no space between it and the next sentence. It result in incorrect result.
                    text = text.replace('\n', '')
                    
                    # Read the text file
                    text_file = open(directory+'/'+filename, 'r')
                    data = text_file.read()
                    text_file.close()
                    
                    # Create an annotated text object
                    # # Usage
                    # driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))
                    
                    # document_importer = None
                    # if document_type == "MEANTIME_XML":
                    #     document_importer = MeantimeXMLImporter(id, data, content, neo4j_repository)
                    # elif document_type == "ANOTHER_TYPE":
                    #     document_importer = AnotherDocumentImporter(id, data, content, neo4j_repository)

                    # if document_importer:
                    #     document_importer.import_document()
                    document_importer = MeantimeXMLImporter(text_id, data, text, self.neo4j_repository)
                    document_importer.import_document()
                    #self.__text_processor.create_annotated_text(data, text, text_id)
                    
                    # Increment the text ID
                    text_id += 1
                except Exception as e:
                    print(f"Error processing file {filename}: {e}")
                
                # Append the annotated text to the list of text tuples
               # text_tuples.append(self.__text_processor.get_annotated_text())
        #text_tuples = tuple(self.__text_processor.get_annotated_text())
        text_tuples = tuple(self.neo4j_repository.get_all_annotated_text_docs())
        # Return the list of text tuples
        return tuple(text_tuples)

    # Tokenizes and stores the given text tuples
    def process_text(self, text_tuples, text_id, storeTag):
        # Check if the Doc object has a text_id extension
        if not Doc.has_extension("text_id"):
            # Set the text_id extension
            Doc.set_extension("text_id", default=None)

        # Pipe the text tuples through the model
        doc_tuples = self.nlp.pipe(text_tuples, as_tuples=True)
        
        # Initialize the list of documents
        docs = []
        
        # Iterate over each document and context
        for doc, context in doc_tuples:
            # Set the text_id attribute of the document
            doc._.text_id = context["text_id"]
            
            # Append the document to the list of documents
            docs.append(doc)

        # Iterate over each document
        for doc in docs:
            # Get the text ID from the document
            text_id = doc._.text_id
            
            # Process the sentences in the document
            spans = self.__text_processor.process_sentences(doc._.text_id, doc, storeTag, text_id)


            # Perform word sense disambiguation
           # wsd = self.__text_processor.perform_wsd(doc._.text_id)
            
            wsd = self.__text_processor.do_wsd(doc._.text_id)

            # Assign synset information to tokens
            #wn = self.__text_processor.assign_synset_info_to_tokens(doc._.text_id)
            wn_token_enricher = self.__text_processor.wn_token_enricher.assign_synset_info_to_tokens(text_id)
            # Process noun chunks
            noun_chunks = self.__text_processor.process_noun_chunks(doc, text_id)
            
            # Process entities
            nes = self.__text_processor.process_entities(doc, text_id)
            
            # Deduplicate named entities
            #deduplicate = self.__text_processor.deduplicate_named_entities(text_id)
            deduplicate = self.__text_processor.fuse_entities(text_id)
            
            # Perform coreference resolution
            #coref = self.__text_processor.do_coref2(doc, text_id)
            coref = self.__text_processor.coref.resolve_coreference(doc, text_id)


            # Build the entities inferred graph
            #self.__text_processor.build_entities_inferred_graph(text_id)
            self.__text_processor.disambiguate_entities(text_id)


            # Process SRL tags from spacy doc and store them into neo4j
            #self.__text_processor.process_srl(doc)
            self.__text_processor.srl_processor.process_srl(doc)
            # Define the rules for relationship extraction
            rules = [
                {
                    'type': 'RECEIVE_PRIZE',
                    'verbs': ['receive'],
                    'subjectTypes': ['PERSON', 'NP'],
                    'objectTypes': ['WORK_OF_ART']
                }
            ]
            
            # Extract relationships
            self.__text_processor.extract_relationships(text_id, rules)
            
            # Build the relationships inferred graph
            self.__text_processor.build_relationships_inferred_graph(text_id)







    def execute_cypher_query(self, query):
        try:
            # Connect to the database
            with self._driver.session() as session:
                # Run the Cypher query
                result = session.run(query)
                # Collect results
                records = [record.data() for record in result]
                return records
        except Exception as e:
            raise Exception(f"Error executing Cypher query: {e}")


# Main function
if __name__ == '__main__':
    # Create a GraphBasedNLP object
    basic_nlp = GraphBasedNLP(sys.argv[1:])
    
    # Define the directory path
    directory = r'/../home/neo/environments/text2graphs/textgraphx/datastore/dataset'
    
    # Store the corpus
    text_tuples = basic_nlp.store_corpus(directory)
    
    # Tokenize and store the text tuples
    basic_nlp.process_text(text_tuples=text_tuples, text_id=1, storeTag=False)
    
    # Close the NLP object
    basic_nlp.close()