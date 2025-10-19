import os
import spacy
import sys
from util.SemanticRoleLabeler import SemanticRoleLabel
from util.EntityFishingLinker import EntityFishing
from spacy.tokens import Doc, Token, Span
from util.RestCaller import callAllenNlpApi
from textgraphx.util.GraphDbBase import GraphDBBase
from textgraphx.TextProcessor import TextProcessor
import xml.etree.ElementTree as ET
from spacy.lang.char_classes import ALPHA, ALPHA_LOWER, ALPHA_UPPER
from spacy.lang.char_classes import CONCAT_QUOTES, LIST_ELLIPSES, LIST_ICONS
from spacy.util import compile_infix_regex
from neo4j import GraphDatabase
from textgraphx.TextProcessor import Neo4jRepository
from textgraphx.text_processing_components.DocumentImporter import MeantimeXMLImporter
from spacy.util import load_config

from spacy_llm.util import assemble
from spacy_llm.registry import registry
from text_processing_components.llm.registry import openai_llama_3_1_8b

# Class representing a graph-based NLP model
class GraphBasedNLP(GraphDBBase):
    # Initializes the NLP model with the given arguments
    def __init__(self, argv):
        # Calls the parent class's constructor
        super().__init__(command=__file__, argv=argv)
        
        self.config_path="/home/neo/environments/text2graphs/textgraphx/config.cfg"  # Default value provided for config_path argument
        self.examples_path="/home/neo/environments/text2graphs/textgraphx/examples.json" 

        # Prefer GPU for processing
        spacy.prefer_gpu()
        
        registry.llm_models.register(openai_llama_3_1_8b)
        # Load the English language model
        self.nlp = spacy.load('en_core_web_trf')

        #config = load_config("/home/neo/environments/text2graphs/textgraphx/config.cfg")


        # Add custom components
        # for component in config["nlp"]["pipeline"]:
        #     if component not in self.nlp.pipe_names:
        #         self.nlp.add_pipe(component, config=config["components"][component])
        
        #self.nlp = assemble(config_path=self.config_path, overrides={"paths.examples": str(self.examples_path)})
        


        
        print("PIPELINE:  ", self.nlp.pipeline)
        # Configure the tokenizer
        self._configure_tokenizer()
        
        # Add pipes to the model
        self._add_pipes()
        """
        Disabled duplicate `GraphBasedNLP copy.py` module.

        This file is a locally kept copy that imports experimental LLM/registry
        components which are not part of the trimmed runtime environment and caused
        import-time failures during package discovery. The canonical implementation is
        `textgraphx/GraphBasedNLP.py`. To avoid breaking imports and automated checks
        we disable this copy; if you need it restored please request the original and
        I'll migrate missing dependencies or move it to an examples/ folder.
        """

        raise ImportError("Disabled duplicate module. Use 'textgraphx.GraphBasedNLP' instead.")