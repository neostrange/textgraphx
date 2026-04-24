"""Compatibility alias for the canonical ingestion TextProcessor module."""

import sys

from textgraphx.pipeline.ingestion import text_processor as _canonical_text_processor


sys.modules[__name__] = _canonical_text_processor
    

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