#In our pipeline, we employed two named entity recognition (NER) components, # namely the spaCy NER and DBpedia-spotlight. 
# By using both components, we were able # to achieve high accuracy and recall. However, we needed to merge the results 
# from # these two components. To do this, we obtained two lists of named entities, one from # spaCy NER and the other from 
# DBpedia-spotlight. In some instances, we found duplicate # entities or text spans that were classified by both components. 
# # We used the HEAD word to determine duplicate entries and removed them. # We prioritized the results from spaCy NER for 
# certain types of entities, # specifically those classified as 'CARDINAL', 'DATE', 'ORDINAL', 'MONEY', 'TIME', 'QUANTITY', 
# or 'PERCENT'. # For the rest of the entities, we gave priority to the results from DBpedia-spotlight. # However, there were 
# instances where entities were detected by spaCy NER but not by DBpedia-spotlight # and were not part of the preferred list. 
# In such cases, we kept those entities as it is.

# The `EntityFuser` class in Python contains methods to fuse entity information in a Neo4j database,
# including assigning head information, prioritizing entities based on certain criteria, and fusing
# entities together.
class EntityFuser:
    def __init__(self, neo4j_repository):
        self.neo4j_repository = neo4j_repository

    def assign_head_info_to_multitoken_entities(self, document_id):
        """
        The function assigns head information to multi-token entities in a document using a Cypher query
        in a Python script.
        
        :param document_id: The `document_id` parameter is used to specify the ID of the document for
        which the head information needs to be assigned to multi-token entities in the annotated text.
        This ID is used in the query to identify the specific document in the database
        """
        query = """
            MATCH p= (text:AnnotatedText where text.id =  $documentId)-[:CONTAINS_SENTENCE]->(sentence:Sentence)-[:HAS_TOKEN]->(a:TagOccurrence)-[:PARTICIPATES_IN]-(ne:NamedEntity),q= (a)-[:IS_DEPENDENT]->()--(ne)
            where not exists ((a)<-[:IS_DEPENDENT]-()--(ne))
            WITH ne, a, p
            set ne.head = a.text, ne.headTokenIndex = a.tok_index_doc, 
            (case when a.pos in ['NNS', 'NN'] then ne END).syntacticType ='NOMINAL' ,
            (case when a.pos in ['NNP', 'NNPS'] then ne END).syntacticType ='NAM' 
        """
        self.execute_query(query, {'documentId': document_id})

    def assign_head_info_to_singletoken_entities(self, document_id):
        """
        This Python function assigns head information to single token entities in a given document based
        on certain conditions.
        
        :param document_id: The `document_id` parameter is used to specify the ID of the document for
        which the head information needs to be assigned to single-token entities in the annotated text.
        This ID is used in the query to identify the specific document in the database
        """
        query = """
            MATCH p= (text:AnnotatedText where text.id =  $documentId )-[:CONTAINS_SENTENCE]->(sentence:Sentence)-[:HAS_TOKEN]->(a:TagOccurrence)-[:PARTICIPATES_IN]-(ne:NamedEntity)
            where not exists ((a)<-[:IS_DEPENDENT]-()--(ne)) and not exists ((a)-[:IS_DEPENDENT]->()--(ne))
            WITH ne, a, p
            set ne.head = a.text, ne.headTokenIndex = a.tok_index_doc, 
            (case when a.pos in ['NNS', 'NN'] then ne END).syntacticType ='NOMINAL' ,
            (case when a.pos in ['NNP', 'NNPS'] then ne END).syntacticType ='NAM'   
        """
        self.execute_query(query, {'documentId': document_id})

    def prioritize_spacy_entities(self, document_id):
        """
        The function `prioritize_spacy_entities` deletes certain named entities based on specific
        criteria in a Neo4j database.
        
        :param document_id: The `document_id` parameter is used to specify the unique identifier of the
        document for which you want to prioritize Spacy entities. This identifier is typically used to
        retrieve the specific document from a database or any other data storage system
        """
        query = """
            match p = (ne:NamedEntity where ne.type in ['CARDINAL', 'DATE', 'ORDINAL', 'MONEY', 'TIME', 'QUANTITY', 'PERCENT'])--
            (a:TagOccurrence )--(ne2:NamedEntity) 
            where a.tok_index_doc = ne.headTokenIndex and a.tok_index_doc = ne2.headTokenIndex and ne.id <> ne2.id
            detach delete ne2
        """
        self.execute_query(query, {"documentId": document_id})

    def prioritize_dbpedia_entities(self, document_id):
        """
        The function `prioritize_dbpedia_entities` prioritizes DBpedia entities in a document by updating
        their properties and deleting redundant entities.
        
        :param document_id: The `document_id` parameter is used to specify the ID of the document for which
        you want to prioritize DBpedia entities. This ID is likely used to retrieve the specific document
        from a database or other data source in order to perform the prioritization of DBpedia entities
        based on the provided Cypher query
        """
        query = """
            match p = (ne:NamedEntity where ne.kb_id is not null)--(a:TagOccurrence )--(ne2:NamedEntity) 
            where a.tok_index_doc = ne.headTokenIndex and a.tok_index_doc = ne2.headTokenIndex and ne.id <> ne2.id
            set ne.spacyType = ne2.type
            detach delete ne2 
        """
        self.execute_query(query, {"documentId": document_id})

    def fuse_entities(self, document_id):
        """
        The `fuse_entities` function in Python performs various tasks to prioritize and assign head
        information to entities in a document.
        
        :param document_id: It looks like the `fuse_entities` method in your code is responsible for
        processing entities in a document identified by `document_id`. The method seems to perform several
        tasks such as assigning head information to multitoken and singletoken entities, as well as
        prioritizing entities from Spacy and DBpedia
        :return: An empty string is being returned from the `fuse_entities` method.
        """
        self.assign_head_info_to_multitoken_entities(document_id)
        self.assign_head_info_to_singletoken_entities(document_id)
        self.prioritize_spacy_entities(document_id)
        self.prioritize_dbpedia_entities(document_id)
        return ''

    def execute_query(self, query, params):
        result = self.neo4j_repository.execute_query(query, params)
        return result