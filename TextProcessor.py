from cgitb import text
import requests
from distutils.command.config import config
import spacy
from spacy.lang.en.stop_words import STOP_WORDS
import json
from tokenize import String
#from allennlp.predictors.predictor import Predictor
#from allennlp_models import pretrained
#import allennlp_models.tagging
from spacy import Language
import GPUtil
import spacy
from spacy.matcher import Matcher, DependencyMatcher
from spacy.tokens import Doc, Token, Span
from spacy.language import Language
import textwrap
from util.RestCaller import callAllenNlpApi
from util.RestCaller import amuse_wsd_api_call
from transformers import logging
logging.set_verbosity_error()
from py2neo import Graph
from py2neo import *
import configparser
import os
from util.RestCaller import callAllenNlpApi
from util.CallAllenNlpCoref import callAllenNlpCoref
import traceback
from nltk.corpus import wordnet31 as wn
from nltk.corpus.reader.wordnet import WordNetError as wn_error
from functools import reduce  # Import reduce function
import logging
from typing import List, Dict
from text_processing_components.WordSenseDisambiguator import WordSenseDisambiguator
from text_processing_components.WordnetTokenEnricher import WordnetTokenEnricher
from text_processing_components.CoreferenceResolver import CoreferenceResolver
from text_processing_components.SRLProcessor import SRLProcessor
from text_processing_components.SentenceCreator import SentenceCreator
from text_processing_components.TagOccurrenceCreator import TagOccurrenceCreator
from text_processing_components.TagOccurrenceDependencyProcessor import TagOccurrenceDependencyProcessor
from text_processing_components.TagOccurrenceQueryExecutor import TagOccurrenceQueryExecutor
from text_processing_components.NounChunkProcessor import NounChunkProcessor
from text_processing_components.EntityProcessor import EntityProcessor
from text_processing_components.EntityFuser import EntityFuser
from text_processing_components.EntityDisambiguator import EntityDisambiguator





class TextProcessor(object):


    # Define constants
    

    # uri=""
    # username =""
    # password =""
    # graph=""
    
    
    
    def __init__(self, nlp, driver):
        self.nlp = nlp
        self._driver = driver
        self.neo4j_repository = Neo4jRepository(self._driver)
        self.uri=""
        self.username =""
        self.password =""
        config = configparser.ConfigParser()
        #config_file = os.path.join(os.path.dirname(__file__), '..', 'config.ini')
        config_file = os.path.join(os.path.dirname(__file__), 'config.ini')
        config.read(config_file)
        py2neo_params = config['py2neo']
        self.uri = py2neo_params.get('uri')
        self.username = py2neo_params.get('username')
        self.password = py2neo_params.get('password')
        #self.graph = Graph(self.uri, auth=(self.username, self.password))
        self.AMUSE_WSD_API_ENDPOINT = "http://localhost:81/api/model"
        self.wsd = WordSenseDisambiguator(self.AMUSE_WSD_API_ENDPOINT, self.neo4j_repository)
        #wsd.perform_wsd("document-123")
        self.wn_token_enricher = WordnetTokenEnricher(self.neo4j_repository)


        self.coreference_service_endpoint = "http://localhost:9999/coreference_resolution"
        self.coref= CoreferenceResolver(self.uri, self.username, self.password, self.coreference_service_endpoint)


        #SRL Processor
        self.srl_processor = SRLProcessor(self.uri, self.username, self.password)

        #Sentence Creator
        self.sentence_creator = SentenceCreator(self.neo4j_repository)

        #TagOccurrenceCreator
        self.tag_occurrence_creator = TagOccurrenceCreator(self.nlp)

        #TagOccurrenceDependencyProcessor
        self.tag_occurrence_dependency_processor= TagOccurrenceDependencyProcessor(self.neo4j_repository)

        #TagOccurrenceQueryExecutor
        self.tag_occurrence_query_executor= TagOccurrenceQueryExecutor(self.neo4j_repository)

        #NounChunkProcessor
        self.noun_chunk_processor = NounChunkProcessor(self.neo4j_repository)

        #EntityProcessor
        self.entity_processor = EntityProcessor(self.neo4j_repository)


        #EntityFuser
        self.entity_fuser = EntityFuser(self.neo4j_repository)

        #EntityDisambiguator
        self.entity_disambiguator = EntityDisambiguator(self.neo4j_repository)

    def do_wsd(self,textId):
        self.wsd.perform_wsd(textId)

    def process_sentences(self, annotated_text, doc, storeTag, text_id):
        i = 0
        for sentence in doc.sents:
            sentence_id = self.sentence_creator.create_sentence_node(annotated_text, text_id, i, sentence)
            sentence_id = sentence_id[0]
            tag_occurrences = self.tag_occurrence_creator.create_tag_occurrences(sentence, text_id, i)
            self.tag_occurrence_query_executor.execute_tag_occurrence_query(tag_occurrences, sentence_id)
            tag_occurrences = self.tag_occurrence_dependency_processor.create_tag_occurrence_dependencies(sentence, text_id, i)
            self.tag_occurrence_dependency_processor.process_dependencies(tag_occurrences)
            i += 1
        return tag_occurrences
    

    def process_entities(self, document_id, nes):
        self.entity_processor.process_entities(document_id,nes)


    def process_noun_chunks(self,doc, text_id):
        self.noun_chunk_processor.process_noun_chunks(doc, text_id)


    def fuse_entities(self, text_id):
        self.entity_fuser.fuse_entities(text_id)



    def disambiguate_entities(self, text_id):
        self.entity_disambiguator.disambiguate_entities(text_id)


    def store_sentence(self, sentence: object, annotated_text: str, text_id: str, sentence_id: int, storeTag: bool) -> int:
        """
        Store a sentence in the database.

        Args:
            sentence (object): The sentence object.
            annotated_text (str): The annotated text.
            text_id (str): The text ID.
            sentence_id (int): The sentence ID.
            storeTag (bool): Whether to store the tag or not.

        Returns:
            int: The node sentence ID.
        """

        tag_occurrence_query = """MATCH (sentence:Sentence) WHERE id(sentence) = $sentence_id
            WITH sentence, $tag_occurrences as tags
            FOREACH ( idx IN range(0,size(tags)-2) |
            MERGE (tagOccurrence1:TagOccurrence {id: tags[idx].id})
            SET tagOccurrence1 = tags[idx]
            MERGE (sentence)-[:HAS_TOKEN]->(tagOccurrence1)
            MERGE (tagOccurrence2:TagOccurrence {id: tags[idx + 1].id})
            SET tagOccurrence2 = tags[idx + 1]
            MERGE (sentence)-[:HAS_TOKEN]->(tagOccurrence2)
            MERGE (tagOccurrence1)-[r:HAS_NEXT {sentence: sentence.id}]->(tagOccurrence2))
            RETURN id(sentence) as result
        """

        tag_occurrence_with_tag_query = """MATCH (sentence:Sentence) WHERE id(sentence) = $sentence_id
            WITH sentence, $tag_occurrences as tags
            FOREACH ( idx IN range(0,size(tags)-2) |
            MERGE (tagOccurrence1:TagOccurrence {id: tags[idx].id})
            SET tagOccurrence1 = tags[idx]
            MERGE (sentence)-[:HAS_TOKEN]->(tagOccurrence1)
            MERGE (tagOccurrence2:TagOccurrence {id: tags[idx + 1].id})
            SET tagOccurrence2 = tags[idx + 1]
            MERGE (sentence)-[:HAS_TOKEN]->(tagOccurrence2)
            MERGE (tagOccurrence1)-[r:HAS_NEXT {sentence: sentence.id}]->(tagOccurrence2))
            FOREACH (tagItem in [tag_occurrence IN $tag_occurrences WHERE tag_occurrence.is_stop = False] | 
            MERGE (tag:Tag {id: tagItem.lemma}) MERGE (tagOccurrence:TagOccurrence {id: tagItem.id}) MERGE (tag)<-[:REFERS_TO]-(tagOccurrence))
            RETURN id(sentence) as result
        """
        
        # Create sentence node
        sentence_query = """
            MATCH (ann:AnnotatedText) WHERE ann.id = $ann_id
            MERGE (sentence:Sentence {id: $sentence_unique_id})
            SET sentence.text = $text
            MERGE (ann)-[:CONTAINS_SENTENCE]->(sentence)
            RETURN id(sentence) as result
        """
        params = {"ann_id": annotated_text, "text": sentence.text, "sentence_unique_id": str(text_id) + "_" + str(sentence_id)}
        results = self.execute_query(sentence_query, params)
        node_sentence_id = results[0]

        # Create tag occurrences
        tag_occurrences = [{"id": str(text_id) + "_" + str(sentence_id) + "_" + str(token.idx),
                            "index": token.idx,
                            "end_index": len(token.text) + token.idx,
                            "text": token.text,
                            "lemma": token.lemma_,
                            "pos": token.tag_,
                            "upos": token.pos_,
                            "tok_index_doc": token.i,
                            "tok_index_sent": token.i - sentence.start,
                            "is_stop": lexeme.is_stop or lexeme.is_punct or lexeme.is_space}
                            for token in sentence
                            for lexeme in [self.nlp.vocab[token.text]]
                            if not lexeme.is_space]

        # Process dependencies
        tag_occurrence_dependencies = [{"source": str(text_id) + "_" + str(sentence_id) + "_" + str(token.head.idx),
                                        "destination": str(text_id) + "_" + str(sentence_id) + "_" + str(token.idx),
                                        "type": token.dep_}
                                        for token in sentence]

        params = {"sentence_id": node_sentence_id, "tag_occurrences": tag_occurrences}
        if storeTag:
            results = self.execute_query(tag_occurrence_with_tag_query, params)
        else:
            results = self.execute_query(tag_occurrence_query, params)

        self.process_dependencies(tag_occurrence_dependencies)
        return results[0]




    def process_sentences2(self, annotated_text, doc, storeTag, text_id):
        i = 0
        for sentence in doc.sents:
            sentence_id = self.store_sentence(sentence, annotated_text, text_id, i, storeTag)
            #spans = list(doc.ents) + list(doc.noun_chunks) - just removed so that only entities get stored.
            #spans = list(doc.ents) - just disabled it as testing dbpedia spotlight
            spans = ''
            if doc.spans.get('ents_original') != None:
                spans = list(doc.ents) + list(doc.spans['ents_original'])
            else:
                spans = list(doc.ents)
            #spans = filter_spans(spans) - just disabled it as testing dbpedia spotlight
            i += 1
        return spans

    def store_sentence2(self, sentence, annotated_text, text_id, sentence_id, storeTag):
        # sentence_query = """MATCH (ann:AnnotatedText) WHERE id(ann) = $ann_id
        #     MERGE (sentence:Sentence {id: $sentence_unique_id})
        #     SET sentence.text = $text
        #     MERGE (ann)-[:CONTAINS_SENTENCE]->(sentence)
        #     RETURN id(sentence) as result
        # """


        sentence_query = """MATCH (ann:AnnotatedText) WHERE ann.id = $ann_id
            MERGE (sentence:Sentence {id: $sentence_unique_id})
            SET sentence.text = $text
            MERGE (ann)-[:CONTAINS_SENTENCE]->(sentence)
            RETURN id(sentence) as result
        """

        tag_occurrence_query = """MATCH (sentence:Sentence) WHERE id(sentence) = $sentence_id
            WITH sentence, $tag_occurrences as tags
            FOREACH ( idx IN range(0,size(tags)-2) |
            MERGE (tagOccurrence1:TagOccurrence {id: tags[idx].id})
            SET tagOccurrence1 = tags[idx]
            MERGE (sentence)-[:HAS_TOKEN]->(tagOccurrence1)
            MERGE (tagOccurrence2:TagOccurrence {id: tags[idx + 1].id})
            SET tagOccurrence2 = tags[idx + 1]
            MERGE (sentence)-[:HAS_TOKEN]->(tagOccurrence2)
            MERGE (tagOccurrence1)-[r:HAS_NEXT {sentence: sentence.id}]->(tagOccurrence2))
            RETURN id(sentence) as result
        """

        tag_occurrence_with_tag_query = """MATCH (sentence:Sentence) WHERE id(sentence) = $sentence_id
            WITH sentence, $tag_occurrences as tags
            FOREACH ( idx IN range(0,size(tags)-2) |
            MERGE (tagOccurrence1:TagOccurrence {id: tags[idx].id})
            SET tagOccurrence1 = tags[idx]
            MERGE (sentence)-[:HAS_TOKEN]->(tagOccurrence1)
            MERGE (tagOccurrence2:TagOccurrence {id: tags[idx + 1].id})
            SET tagOccurrence2 = tags[idx + 1]
            MERGE (sentence)-[:HAS_TOKEN]->(tagOccurrence2)
            MERGE (tagOccurrence1)-[r:HAS_NEXT {sentence: sentence.id}]->(tagOccurrence2))
            FOREACH (tagItem in [tag_occurrence IN $tag_occurrences WHERE tag_occurrence.is_stop = False] | 
            MERGE (tag:Tag {id: tagItem.lemma}) MERGE (tagOccurrence:TagOccurrence {id: tagItem.id}) MERGE (tag)<-[:REFERS_TO]-(tagOccurrence))
            RETURN id(sentence) as result
        """

        params = {"ann_id": annotated_text, "text": sentence.text,
                  "sentence_unique_id": str(text_id) + "_" + str(sentence_id)}
        results = self.execute_query(sentence_query, params)
        node_sentence_id = results[0]
        tag_occurrences = []
        tag_occurrence_dependencies = []
        for token in sentence:
            lexeme = self.nlp.vocab[token.text]
            # edited: included the punctuation as possible token candidates.
            #if not lexeme.is_punct and not lexeme.is_space:
            if not lexeme.is_space:
                tag_occurrence_id = str(text_id) + "_" + str(sentence_id) + "_" + str(token.idx)
                tag_occurrence = {"id": tag_occurrence_id,
                                    "index": token.idx,
                                    "end_index": (len(token.text)+token.idx),
                                    "text": token.text,
                                    "lemma": token.lemma_,
                                    "pos": token.tag_,
                                    "upos": token.pos_,
                                    "tok_index_doc": token.i,
                                    "tok_index_sent": (token.i - sentence.start),
                                    "is_stop": (lexeme.is_stop or lexeme.is_punct or lexeme.is_space)}
                tag_occurrences.append(tag_occurrence)
                tag_occurrence_dependency_source = str(text_id) + "_" + str(sentence_id) + "_" + str(token.head.idx)

                print(token.text, token.dep_, token.head.text, token.head.pos_,
            [child for child in token.children])
                dependency = {"source": tag_occurrence_dependency_source, "destination": tag_occurrence_id,
                                "type": token.dep_}
                tag_occurrence_dependencies.append(dependency)
        params = {"sentence_id": node_sentence_id, "tag_occurrences": tag_occurrences}
        if storeTag:
            results = self.execute_query(tag_occurrence_with_tag_query, params)
        else:
            results = self.execute_query(tag_occurrence_query, params)

        self.process_dependencies(tag_occurrence_dependencies)
        return results[0]


    # # this snippet is for dbpedia-spotlight component
    # def process_entities(self, doc, text_id):
    #     nes = []
    #     i=0
    #     spans = ''
    #     if doc.spans.get('ents_original') != None:
    #         spans = list(doc.ents) + list(doc.spans['ents_original'])
    #     else:
    #         spans = list(doc.ents)
    #     #spans = filter_spans(spans) - just disabled it as testing dbpedia spotlight
    #     i += 1
    #     for entity in spans:
    #         if entity.kb_id_ != '': 
    #             ne = {'value': entity.text, 'type': entity.label_, 'start_index': entity.start_char,
    #                 'end_index': entity.end_char, 
    #                 'kb_id': entity.kb_id_, 'url_wikidata': entity.kb_id_, 'score': entity._.dbpedia_raw_result['@similarityScore'],
    #                 'normal_term': entity.text, 'description': entity._.dbpedia_raw_result.get('@surfaceForm')
    #                 }
    #         else:
    #             ne = {'value': entity.text, 'type': entity.label_, 'start_index': entity.start_char,
    #                 'end_index': entity.end_char
    #                 }

    #         nes.append(ne)
    #     self.store_entities(text_id, nes)
    #     return nes
    # #end of this snippet

    # def store_entities(self, document_id, nes):
    #     ne_query = """
    #         UNWIND $nes as item
    #         MERGE (ne:NamedEntity {id: toString($documentId) + "_" + toString(item.start_index)+ "_" + toString(item.end_index)+ "_" + toString(item.type)})
    #         SET ne.type = item.type, ne.value = item.value, ne.index = item.start_index,
    #         ne.kb_id = item.kb_id, ne.url_wikidata = item.url_wikidata, ne.score = item.score, ne.normal_term = item.normal_term, 
    #         ne.description = item.description
    #         WITH ne, item as neIndex
    #         MATCH (text:AnnotatedText)-[:CONTAINS_SENTENCE]->(sentence:Sentence)-[:HAS_TOKEN]->(tagOccurrence:TagOccurrence)
    #         WHERE text.id = $documentId AND tagOccurrence.index >= neIndex.start_index AND tagOccurrence.index < neIndex.end_index
    #         MERGE (ne)<-[:PARTICIPATES_IN]-(tagOccurrence)
    #     """
    #     self.execute_query(ne_query, {"documentId": document_id, "nes": nes})

    # this snippet is only applicable for entity-fishing component
    # def process_entities(self, spans, text_id):
    #     nes = []
    #     for entity in spans:
    #         ne = {'value': entity.text, 'type': entity.label_, 'start_index': entity.start_char,
    #               'end_index': entity.end_char, 
    #               'kb_id': entity._.kb_qid, 'url_wikidata': entity._.url_wikidata, 'score': entity._.nerd_score,
    #               'normal_term': entity._.normal_term, 'description': entity._.description }
    #         nes.append(ne)
    #     self.store_entities(text_id, nes)
    #     return nes
    # end of this snippet. 



    # def process_noun_chunks(self, doc, text_id):
    #     self.noun_chunk_processor.process_noun_chunks(doc, text_id)


    # def process_noun_chunks2(self, doc, text_id):
    #     ncs = []
    #     for noun_chunk in doc.noun_chunks:
    #         nc = {'value': noun_chunk.text, 'type': noun_chunk.label_, 'start_index': noun_chunk.start_char,
    #               'end_index': noun_chunk.end_char}
    #         ncs.append(nc)
    #     self.store_noun_chunks(text_id, ncs)
    #     return ncs

    # def store_noun_chunks(self, document_id, ncs):
    #     nc_query = """
    #         UNWIND $ncs as item
    #         MERGE (nc:NounChunk {id: toString($documentId) + "_" + toString(item.start_index)})
    #         SET nc.type = item.type, nc.value = item.value, nc.index = item.start_index
    #         WITH nc, item as ncIndex
    #         MATCH (text:AnnotatedText)-[:CONTAINS_SENTENCE]->(sentence:Sentence)-[:HAS_TOKEN]->(tagOccurrence:TagOccurrence)
    #         WHERE text.id = $documentId AND tagOccurrence.index >= ncIndex.start_index AND tagOccurrence.index < ncIndex.end_index
    #         MERGE (nc)<-[:PARTICIPATES_IN]-(tagOccurrence)
    #     """
    #     self.execute_query(nc_query, {"documentId": document_id, "ncs": ncs})



#ne.kb_id = item.kb_id, ne.description = item.description, ne.score = item.score


        #NamedEntity Multitoken
    def get_and_assign_head_info_to_entity_multitoken(self, document_id):

        # print(self.uri)
        # graph = Graph(self.uri, auth=(self.username, self.password))


        # query to find the head of a NamedEntity. (case is for entitities composed of  multitokens )
        # TODO: the head for the NAM should include the whole extent of the name. see newsreader annotation guidelines 
        # for more information. 
        query = """    
                        MATCH p= (text:AnnotatedText where text.id =  $documentId)-[:CONTAINS_SENTENCE]->(sentence:Sentence)-[:HAS_TOKEN]->(a:TagOccurrence)-[:PARTICIPATES_IN]-(ne:NamedEntity),q= (a)-[:IS_DEPENDENT]->()--(ne)
                        where not exists ((a)<-[:IS_DEPENDENT]-()--(ne))
                        WITH ne, a, p
                                                set ne.head = a.text, ne.headTokenIndex = a.tok_index_doc, 
                                                (case when a.pos in ['NNS', 'NN'] then ne END).syntacticType ='NOMINAL' ,
                                                (case when a.pos in ['NNP', 'NNPS'] then ne END).syntacticType ='NAM' 
        
        """
        self.execute_query(query, {'documentId': document_id})
        


    #NamedEntity Singletoken
    def get_and_assign_head_info_to_entity_singletoken(self, document_id):

        # print(self.uri)
        # graph = Graph(self.uri, auth=(self.username, self.password))


        # query to find the head of a NamedEntity. (case is for entitities composed of  single token )
        query = """    
                        MATCH p= (text:AnnotatedText where text.id =  $documentId )-[:CONTAINS_SENTENCE]->(sentence:Sentence)-[:HAS_TOKEN]->(a:TagOccurrence)-[:PARTICIPATES_IN]-(ne:NamedEntity)
                        where not exists ((a)<-[:IS_DEPENDENT]-()--(ne)) and not exists ((a)-[:IS_DEPENDENT]->()--(ne))
                        WITH ne, a, p
                                                set ne.head = a.text, ne.headTokenIndex = a.tok_index_doc, 
                                                (case when a.pos in ['NNS', 'NN'] then ne END).syntacticType ='NOMINAL' ,
                                                (case when a.pos in ['NNP', 'NNPS'] then ne END).syntacticType ='NAM'   
        
        """
        self.execute_query(query, {'documentId': document_id})



    def use_spacy_named_entities(self, document_id):
        # this query keep spacy named entities which have type of 'CARDINAL', 'DATE', 'ORDINAL', 'MONEY', 'TIME', 'QUANTITY', 'PERCENT' 
        query1 = """
                    match p = (ne:NamedEntity where ne.type in ['CARDINAL', 'DATE', 'ORDINAL', 'MONEY', 'TIME', 'QUANTITY', 'PERCENT'])--
                    (a:TagOccurrence )--(ne2:NamedEntity) 
                    where a.tok_index_doc = ne.headTokenIndex and a.tok_index_doc = ne2.headTokenIndex and ne.id <> ne2.id
                    detach delete ne2
        """ 
        self.execute_query(query1, {"documentId": document_id})


    
    def use_dbpedia_named_entities(self, document_id):
            # this query keeps the dbpedia ner entity but copies the spacy ner type information. 
        query2 = """
                    match p = (ne:NamedEntity where ne.kb_id is not null)--(a:TagOccurrence )--(ne2:NamedEntity) 
                    where a.tok_index_doc = ne.headTokenIndex and a.tok_index_doc = ne2.headTokenIndex and ne.id <> ne2.id
                    set ne.spacyType = ne2.type
                    detach delete ne2 
        """
        
        
        self.execute_query(query2, {"documentId": document_id})
     

    #In our pipeline, we employed two named entity recognition (NER) components, 
    # namely the spaCy NER and DBpedia-spotlight. By using both components, we were able 
    # to achieve high accuracy and recall. However, we needed to merge the results from 
    # these two components. To do this, we obtained two lists of named entities, one from
    #  spaCy NER and the other from DBpedia-spotlight. In some instances, we found duplicate
    #  entities or text spans that were classified by both components. 
    # We used the HEAD word to determine duplicate entries and removed them. 
    # We prioritized the results from spaCy NER for certain types of entities, 
    # specifically those classified as 'CARDINAL', 'DATE', 'ORDINAL', 'MONEY', 'TIME', 'QUANTITY', or 'PERCENT'.
    #  For the rest of the entities, we gave priority to the results from DBpedia-spotlight.
    #  However, there were instances where entities were detected by spaCy NER but not by DBpedia-spotlight 
    # and were not part of the preferred list. In such cases, we kept those entities as it is.   

    def deduplicate_named_entities(self, document_id):

        self.get_and_assign_head_info_to_entity_multitoken(document_id)
        self.get_and_assign_head_info_to_entity_singletoken(document_id)
        self.use_spacy_named_entities(document_id)
        self.use_dbpedia_named_entities(document_id)
        return ''

        
    


    
    
    def process_textrank(self, doc, text_id):
        keywords = []
        spans = []
        for p in doc._.phrases:
            for span in p.chunks:
                item = {"span": span, "rank": p.rank}
                spans.append(item)
        spans = filter_extended_spans(spans)
        for item in spans:
            span = item['span']
            lexme = self.nlp.vocab[span.text]
            if lexme.is_stop or lexme.is_digit or lexme.is_bracket or "-PRON-" in span.lemma_:
                continue
            keyword = {"id": span.lemma_, "start_index": span.start_char, "end_index": span.end_char}
            if len(span.ents) > 0:
                keyword['NE'] = span.ents[0].label_
            keyword['rank'] = item['rank']
            keywords.append(keyword)
        self.store_keywords(text_id, keywords)

    # def create_annotated_text(self, doc, id):
    #     query = """MERGE (ann:AnnotatedText {id: $id})
    #         RETURN id(ann) as result
    #     """
    #     params = {"id": id}
    #     results = self.execute_query(query, params)
    #     return results[0]

    def process_dependencies(self, tag_occurrence_dependencies):
        tag_occurrence_query = """UNWIND $dependencies as dependency
            MATCH (source:TagOccurrence {id: dependency.source})
            MATCH (destination:TagOccurrence {id: dependency.destination})
            MERGE (source)-[:IS_DEPENDENT {type: dependency.type}]->(destination)
                """
        self.execute_query(tag_occurrence_query, {"dependencies": tag_occurrence_dependencies})

    def store_keywords(self, document_id, keywords):
        ne_query = """
            UNWIND $keywords as keyword
            MERGE (kw:Keyword {id: keyword.id})
            SET kw.NE = keyword.NE, kw.index = keyword.start_index, kw.endIndex = keyword.end_index
            WITH kw, keyword
            MATCH (text:AnnotatedText)
            WHERE text.id = $documentId
            MERGE (text)<-[:DESCRIBES {rank: keyword.rank}]-(kw)
        """
        self.execute_query(ne_query, {"documentId": document_id, "keywords": keywords})



#For the purpose of mapping named entities to entity instances in our pipeline, we distinguished between two types of named entities.
#  The first type includes entities that have been successfully disambiguated and assigned a unique KBID by the entity disambiguation module.
#  These entities can be easily mapped by creating instances based on the distinct KBIDs. The second type of named entities, 
# however, are unknown to the entity disambiguation module and are assigned a NULL KBID. To map these named entities, we rely on the text of
#  the named entity's span and its assigned type, which was determined by the NER component. As a result, named entity mentions with the 
# same text value and type are considered to refer to a single entity instance.

    def build_entities_inferred_graph(self, document_id):
        extract_direct_entities_query = """
            MATCH (document:AnnotatedText)
            WHERE document.id = $documentId
            WITH document
            MATCH (document)-[*3..3]->(ne:NamedEntity)
            WHERE NOT ne.type IN ['NP', 'TIME', 'ORDINAL', 'NUMBER', 'MONEY', 'DATE', 'CARDINAL', 'QUANTITY', 'PERCENT'] AND ne.kb_id IS NOT NULL
            WITH ne
            MERGE (entity:Entity {type: ne.type, kb_id:ne.kb_id, id: split(ne.kb_id, '/')[-1]})
            MERGE (ne)-[:REFERS_TO {type: "evoke"}]->(entity)
        """


        # Here we have type and id as the unique identfier for Entity instances. It means if a NamedEntity has same type and same value
        # then it will consider unique. Some more investigations into this matter is required. 
        # However Entity deduplication will be performed using coreferencing information. 
        extract_indirect_entities_query = """
        MATCH (document:AnnotatedText)
            WHERE document.id = $documentId
            WITH document
            MATCH (document)-[*3..3]->(ne:NamedEntity)
            WHERE NOT ne.type IN ['NP', 'TIME', 'ORDINAL', 'MONEY', 'NUMBER', 'DATE', 'CARDINAL', 'QUANTITY', 'PERCENT'] AND ne.kb_id IS NULL
            WITH ne
            MERGE (entity:Entity {type: ne.type, kb_id:ne.value, id:ne.value})
            MERGE (ne)-[:REFERS_TO {type: "evoke"}]->(entity)
        """
        self.execute_query(extract_direct_entities_query, {"documentId": document_id})
        self.execute_query(extract_indirect_entities_query, {"documentId": document_id})

    def extract_relationships(self, document_id, rules):
        """
        The function `extract_relationships` extracts relationships between named entities based on
        specified rules from an annotated text document.
        
        :param document_id: The `document_id` parameter is the identifier of the document for which you
        want to extract relationships. It is used to match the specific document in the database based
        on its ID
        :param rules: The `rules` parameter in the `extract_relationships` function is a list of rules
        that define the relationships to be extracted from the document. Each rule in the list contains
        the following information:
        """
        extract_relationships_query = """
            MATCH (document:AnnotatedText)
            WHERE document.id = $documentId
            WITH document
            UNWIND $rules as rule
            MATCH (document)-[*2..2]->(verb:TagOccurrence {pos: "VBD"})
            MATCH (verb:TagOccurrence {pos: "VBD"})
            WHERE verb.lemma IN rule.verbs
            WITH verb, rule
            MATCH (verb)-[:IS_DEPENDENT {type:"nsubj"}]->(subject)-[:PARTICIPATES_IN]->(subjectNe:NamedEntity)
            WHERE subjectNe.type IN rule.subjectTypes
            MATCH (verb)-[:IS_DEPENDENT {type:"dobj"}]->(object)-[:PARTICIPATES_IN]->(objectNe:NamedEntity {type: "WORK_OF_ART"})
            WHERE objectNe.type IN rule.objectTypes
            WITH verb, subjectNe, objectNe, rule
            MERGE (subjectNe)-[:IS_RELATED_TO {root: verb.lemma, type: rule.type}]->(objectNe)
        """
        self.execute_query(extract_relationships_query, {"documentId": document_id, "rules":rules})

    def build_relationships_inferred_graph(self, document_id):
        extract_relationships_query = """
            MATCH (document:AnnotatedText)
            WHERE document.id = $documentId
            WITH document
            MATCH (document)-[*2..3]->(ne1:NamedEntity)
            MATCH (entity1:Entity)<-[:REFERS_TO]-(ne1:NamedEntity)-[r:IS_RELATED_TO]->(ne2:NamedEntity)-[:REFERS_TO]->(entity2:Entity)
            MERGE (evidence:Evidence {id: id(r), type:r.type})
            MERGE (rel:Relationship {id: id(r), type:r.type})
            MERGE (ne1)<-[:SOURCE]-(evidence)
            MERGE (ne2)<-[:DESTINATION]-(evidence)
            MERGE (rel)-[:HAS_EVIDENCE]->(evidence)
            MERGE (entity1)<-[:FROM]-(rel)
            MERGE (entity2)<-[:TO]-(rel)
        """
        self.execute_query(extract_relationships_query, {"documentId": document_id})


    def execute_query3(self, query, params):
        session = None
        results = []

        try:
            session = self._driver.session()
            response = session.run(query, params)
            for item in response:
                results.append(item)
        except Exception as e:
            print("Query Failed: ", e)
        finally:
            if session is not None:
                session.close()
        return results


    def execute_query(self, query, params):
        session = None
        response = None
        results = []

        try:
            session = self._driver.session()
            response =  session.run(query, params)
            for items in response:
                item = items["result"]
                results.append(item)
        except Exception as e:
            print("Query Failed: ", str(e))
            traceback.print_exc()
        finally:
            if session is not None:
                session.close()
        return results


    def execute_query2(self, query, params):
        results = []
        with self._driver.session() as session:
            for items in session.run(query, params):
                item = items["result"]
                results.append(item)
        return results


def filter_spans(spans):
    get_sort_key = lambda span: (span.end - span.start, -span.start)
    sorted_spans = sorted(spans, key=get_sort_key, reverse=True)
    result = []
    seen_tokens = set()
    for span in sorted_spans:
        # Check for end - 1 here because boundaries are inclusive
        if span.start not in seen_tokens and span.end - 1 not in seen_tokens:
            result.append(span)
        seen_tokens.update(range(span.start, span.end))
    result = sorted(result, key=lambda span: span.start)
    return result


def filter_extended_spans(items):
    get_sort_key = lambda item: (item['span'].end - item['span'].start, -item['span'].start)
    sorted_spans = sorted(items, key=get_sort_key, reverse=True)
    result = []
    seen_tokens = set()
    for item in sorted_spans:
        # Check for end - 1 here because boundaries are inclusive
        if item['span'].start not in seen_tokens and item['span'].end - 1 not in seen_tokens:
            result.append(item)
        seen_tokens.update(range(item['span'].start, item['span'].end))
    result = sorted(result, key=lambda span: span['span'].start)
    return result



class Neo4jRepository:
    def __init__(self, driver):
        self._driver = driver

    def execute_query3(self, query, params=None):
        with self._driver.session() as session:
            result = session.run(query, params)
            return result
        
    def execute_query(self, query, params):
        session = None
        results = []

        try:
            session = self._driver.session()
            response = session.run(query, params)
            for item in response:
                results.append(item)
        except Exception as e:
            print("Query Failed: ", e)
            print("Query: ", query)
            print("Params: ", params)
            print("Traceback: ")
            import traceback
            traceback.print_exc()
        finally:
            if session is not None:
                session.close()
        return results
    

    def execute_query_with_result_as_key(self, query, params):
        session = None
        response = None
        results = []

        try:
            session = self._driver.session()
            response =  session.run(query, params)
            for items in response:
                item = items["result"]
                results.append(item)
        except Exception as e:
            print("Query Failed: ", str(e))
            traceback.print_exc()
        finally:
            if session is not None:
                session.close()
        return results
    
    # def get_all_annotated_text_docs(self):
    #     query = "MATCH (n:AnnotatedText) RETURN n.text, n.id, n.creationtime"
    #     data = self.execute_query(query, {})
    #     annotated_text_docs = []

    #     for record in data:
    #         t = (record.get("n.text"), {'text_id': record.get("n.id")})
    #         annotated_text_docs.append(t)
        
    #     return annotated_text_docs
    

    def get_all_annotated_text_docs(self) -> list[tuple[str, dict[str, str]]]:
        query = "MATCH (n:AnnotatedText) RETURN n.text, n.id, n.creationtime"
        try:
            records = self.execute_query(query, {})
        except Exception as e:
            # Handle the exception
            print(f"An error occurred: {e}")
            return []

        annotated_text_docs = [
            (record.get("n.text", ""), {"text_id": record.get("n.id", "")})
            for record in records
        ]

        return annotated_text_docs
    

# class NounChunkProcessor:
#     def __init__(self, db_executor):
#         """
#         Initialize the NounChunkProcessor with a database executor.

#         Args:
#             db_executor: An object responsible for executing database queries.
#         """
#         self.db_executor = db_executor

#     def process_noun_chunks(self, doc, text_id):
#         """
#         Process noun chunks in a given document and store them in the database.

#         Args:
#             doc: A spaCy document object.
#             text_id (str): The ID of the text being processed.

#         Returns:
#             list: A list of noun chunk dictionaries.
#         """
#         ncs = []
#         for noun_chunk in doc.noun_chunks:
#             nc = {
#                 'value': noun_chunk.text,
#                 'type': noun_chunk.label_,
#                 'start_index': noun_chunk.start_char,
#                 'end_index': noun_chunk.end_char
#             }
#             ncs.append(nc)
#         self.store_noun_chunks(text_id, ncs)
#         return ncs

#     def store_noun_chunks(self, document_id, ncs):
#         """
#         Store noun chunks in the database.

#         Args:
#             document_id (str): The ID of the document.
#             ncs (list): A list of noun chunk dictionaries.
#         """
#         nc_query = """
#             UNWIND $ncs as item
#             MERGE (nc:NounChunk {id: toString($documentId) + "_" + toString(item.start_index)})
#             SET nc.type = item.type, nc.value = item.value, nc.index = item.start_index
#             WITH nc, item as ncIndex
#             MATCH (text:AnnotatedText)-[:CONTAINS_SENTENCE]->(sentence:Sentence)-[:HAS_TOKEN]->(tagOccurrence:TagOccurrence)
#             WHERE text.id = $documentId AND tagOccurrence.index >= ncIndex.start_index AND tagOccurrence.index < ncIndex.end_index
#             MERGE (nc)<-[:PARTICIPATES_IN]-(tagOccurrence)
#         """
#         self.db_executor.execute_query(nc_query, {"documentId": document_id, "ncs": ncs})


# class SentenceCreator:
#     def __init__(self, neo4j_repository):
#         self.neo4j_repository = neo4j_repository
#         pass

#     def create_sentence_node(self, annotated_text, text_id, sentence_id, sentence):
#         sentence_query = """
#             MATCH (ann:AnnotatedText) WHERE ann.id = $ann_id
#             MERGE (sentence:Sentence {id: $sentence_unique_id})
#             SET sentence.text = $text
#             MERGE (ann)-[:CONTAINS_SENTENCE]->(sentence)
#             RETURN id(sentence) as result
#         """
#         params = {"ann_id": annotated_text, "text": sentence.text, "sentence_unique_id": str(text_id) + "_" + str(sentence_id)}
#         results = self.execute_query(sentence_query, params)
#         return results[0]

#     def execute_query(self, query, params):
#         # implement the execute_query method
#         return self.neo4j_repository.execute_query(query, params)



# class TagOccurrenceCreator:
#     def __init__(self, nlp):
#         self.nlp = nlp
#         pass


#     def create_tag_occurrences(self, sentence, text_id, sentence_id):

#         tag_occurrences = []
#         for token in sentence:
#             lexeme = self.nlp.vocab[token.text]
#             # edited: included the punctuation as possible token candidates.
#             #if not lexeme.is_punct and not lexeme.is_space:
#             if not lexeme.is_space:
#                 tag_occurrence_id = str(text_id) + "_" + str(sentence_id) + "_" + str(token.idx)
#                 tag_occurrence = {"id": tag_occurrence_id,
#                                     "index": token.idx,
#                                     "end_index": (len(token.text)+token.idx),
#                                     "text": token.text,
#                                     "lemma": token.lemma_,
#                                     "pos": token.tag_,
#                                     "upos": token.pos_,
#                                     "tok_index_doc": token.i,
#                                     "tok_index_sent": (token.i - sentence.start),
#                                     "is_stop": (lexeme.is_stop or lexeme.is_punct or lexeme.is_space)}
#                 tag_occurrences.append(tag_occurrence)
#         return tag_occurrences

#     def create_tag_occurrences2(self, sentence, text_id, sentence_id):
#         tag_occurrences = [{"id": str(text_id) + "_" + str(sentence_id) + "_" + str(token.idx),
#                             "index": token.idx,
#                             "end_index": len(token.text) + token.idx,
#                             "text": token.text,
#                             "lemma": token.lemma_,
#                             "pos": token.tag_,
#                             "upos": token.pos_,
#                             "tok_index_doc": token.i,
#                             "tok_index_sent": token.i - sentence.start,
#                             "is_stop": lexeme.is_stop or lexeme.is_punct or lexeme.is_space}
#                             for token in sentence
#                             for lexeme in [self.nlp.vocab[token.text]]
#                             if not lexeme.is_space]
#         return tag_occurrences
    


# class TagOccurrenceDependencyProcessor:
#     def __init__(self, neo4j_repository):
#         self.neo4j_repository = neo4j_repository
#         pass

#     def process_dependencies2(self, tag_occurrence_dependencies):
#         tag_occurrence_query = """MATCH (source:TagOccurrence {id: $source_id})
#                                     MATCH (destination:TagOccurrence {id: $destination_id})
#                                     MERGE (source)-[:IS_DEPENDENT {type: $type}]->(destination)
#                             """
#         for dependency in tag_occurrence_dependencies:
#             self.neo4j_repository.execute_query(tag_occurrence_query, dependency)

#     def process_dependencies(self, tag_occurrence_dependencies):
#         tag_occurrence_query = """UNWIND $dependencies as dependency
#             MATCH (source:TagOccurrence {id: dependency.source})
#             MATCH (destination:TagOccurrence {id: dependency.destination})
#             MERGE (source)-[:IS_DEPENDENT {type: dependency.type}]->(destination)
#                 """
#         self.neo4j_repository.execute_query_with_result_as_key(tag_occurrence_query, {"dependencies": tag_occurrence_dependencies})

#     def create_tag_occurrence_dependencies(self, sentence, text_id, sentence_id):
#         tag_occurrence_dependencies = [{"source": str(text_id) + "_" + str(sentence_id) + "_" + str(token.head.idx),
#                                         "destination": str(text_id) + "_" + str(sentence_id) + "_" + str(token.idx),
#                                         "type": token.dep_}
#                                         for token in sentence]
#         return tag_occurrence_dependencies
    




# class TagOccurrenceQueryExecutor:
#     def __init__(self, neo4j_repository):
#         self.neo4j_repository = neo4j_repository
#         pass

#     def execute_tag_occurrence_query(self, sentence_tag_occurrences, sentence_id):
#         # implement the execute_tag_occurrence_query method
#         tag_occurrences = []
#         for tag_occurrence in sentence_tag_occurrences:
#             tag_occurrence_dict = dict(tag_occurrence)
#             tag_occurrences.append(tag_occurrence_dict)
#         params = {"sentence_id": sentence_id, "tag_occurrences": sentence_tag_occurrences}
#         query = self.get_tag_occurrence_query(False)

#         return self.neo4j_repository.execute_query_with_result_as_key(query, params)

#     def get_tag_occurrence_query(self, store_tag):
#         if store_tag:
#             return """MATCH (sentence:Sentence) WHERE id(sentence) = $sentence_id
#                 WITH sentence, $tag_occurrences as tags
#                 FOREACH ( idx IN range(0,size(tags)-2) |
#                 MERGE (tagOccurrence1:TagOccurrence {id: tags[idx].id})
#                 SET tagOccurrence1 = tags[idx]
#                 MERGE (sentence)-[:HAS_TOKEN]->(tagOccurrence1)
#                 MERGE (tagOccurrence2:TagOccurrence {id: tags[idx + 1].id})
#                 SET tagOccurrence2 = tags[idx + 1]
#                 MERGE (sentence)-[:HAS_TOKEN]->(tagOccurrence2)
#                 MERGE (tagOccurrence1)-[r:HAS_NEXT {sentence: sentence.id}]->(tagOccurrence2))
#                 FOREACH (tagItem in [tag_occurrence IN $tag_occurrences WHERE tag_occurrence.is_stop = False] | 
#                 MERGE (tag:Tag {id: tagItem.lemma}) MERGE (tagOccurrence:TagOccurrence {id: tagItem.id}) MERGE (tag)<-[:REFERS_TO]-(tagOccurrence))
#                 RETURN id(sentence) as result
#             """
#         else:
#             return """MATCH (sentence:Sentence) WHERE id(sentence) = $sentence_id
#             WITH sentence, $tag_occurrences as tags
#             FOREACH ( idx IN range(0,size(tags)-2) |
#             MERGE (tagOccurrence1:TagOccurrence {id: tags[idx].id})
#             SET tagOccurrence1 = tags[idx]
#             MERGE (sentence)-[:HAS_TOKEN]->(tagOccurrence1)
#             MERGE (tagOccurrence2:TagOccurrence {id: tags[idx + 1].id})
#             SET tagOccurrence2 = tags[idx + 1]
#             MERGE (sentence)-[:HAS_TOKEN]->(tagOccurrence2)
#             MERGE (tagOccurrence1)-[r:HAS_NEXT {sentence: sentence.id}]->(tagOccurrence2))
#             RETURN id(sentence) as result
#         """