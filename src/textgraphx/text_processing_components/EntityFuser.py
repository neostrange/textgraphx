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
        import logging
        self.logger = logging.getLogger(__name__)

    def assign_head_info_to_multitoken_entities(self, document_id):
        """Assign head token metadata to multi-token NamedEntity spans.

        Uses ``coalesce`` guards so that existing ``head`` / ``headTokenIndex``
        values written by an earlier ingestion pass are never silently overwritten.
        ``syntacticType`` / ``syntactic_type`` are intentionally NOT written here;
        refinement (``RefinementPhase.get_and_assign_head_info_to_entity_*``) is
        the sole authority for syntactic-type assignment.
        """
        query = """
            MATCH (text:AnnotatedText {id: $documentId})
                  -[:CONTAINS_SENTENCE]->(sentence:Sentence)
                  -[:HAS_TOKEN]->(a:TagOccurrence)
                  -[:PARTICIPATES_IN]-(ne:NamedEntity)
            MATCH (a)-[:IS_DEPENDENT]->()--(ne)
            WHERE NOT exists ((a)<-[:IS_DEPENDENT]-()--(ne))
            SET ne.head           = coalesce(ne.head, a.text),
                ne.headTokenIndex = coalesce(ne.headTokenIndex, a.tok_index_doc)
        """
        self.logger.debug("assign_head_info_to_multitoken_entities: running for %s", document_id)
        self.execute_query(query, {'documentId': document_id})

    def assign_head_info_to_singletoken_entities(self, document_id):
        """Assign head token metadata to single-token NamedEntity spans.

        Uses ``coalesce`` guards so that existing values are not silently
        overwritten.  ``syntacticType`` / ``syntactic_type`` are intentionally
        NOT written here; refinement is the sole authority for syntactic-type
        assignment.
        """
        query = """
            MATCH (text:AnnotatedText {id: $documentId})
                  -[:CONTAINS_SENTENCE]->(sentence:Sentence)
                  -[:HAS_TOKEN]->(a:TagOccurrence)
                  -[:PARTICIPATES_IN]-(ne:NamedEntity)
            WHERE NOT exists ((a)<-[:IS_DEPENDENT]-()--(ne))
              AND NOT exists ((a)-[:IS_DEPENDENT]->()--(ne))
            SET ne.head           = coalesce(ne.head, a.text),
                ne.headTokenIndex = coalesce(ne.headTokenIndex, a.tok_index_doc)
        """
        self.logger.debug("assign_head_info_to_singletoken_entities: running for %s", document_id)
        self.execute_query(query, {'documentId': document_id})

    def prioritize_spacy_entities(self, document_id):
        """Prefer spaCy entities over DBpedia entities for numeric/temporal types.

        For types that spaCy handles reliably ('CARDINAL', 'DATE', 'ORDINAL',
        'MONEY', 'TIME', 'QUANTITY', 'PERCENT'), the spaCy-sourced NamedEntity
        is kept and any co-located competing mention is removed.

        Safety guards added vs the original implementation:
        - *Type-compatibility check*: only collapse when the two entities share
          the same type (or both are numeric/temporal).  This prevents
          nested-entity pairs (e.g. PERSON vs TITLE) from being incorrectly
          merged simply because they share a head token.
        - *Pre-delete metadata merge*: before removing ``ne2``, salvageable
          properties (``kb_id``, ``score``) and any ``REFERS_TO`` edges are
          migrated to ``ne``.
        - The ``documentId`` parameter is now actually used to scope the match
          through the document graph so that the query is explicit about its
          reach (though in practice the TagOccurrence join is already doc-local).

        :param document_id: Document id scoping this fuse pass.
        """
        # Step 1 — for numeric/temporal types, salvage metadata from the
        #   losing entity and re-attach its REFERS_TO edges before deletion.
        salvage_query = """
            MATCH (d:AnnotatedText {id: $documentId})
                  -[:CONTAINS_SENTENCE]->(:Sentence)
                  -[:HAS_TOKEN]->(a:TagOccurrence)
                  --(ne:NamedEntity)
            WHERE ne.type IN ['CARDINAL', 'DATE', 'ORDINAL', 'MONEY', 'TIME', 'QUANTITY', 'PERCENT']
              AND a.tok_index_doc = ne.headTokenIndex
            MATCH (a)--(ne2:NamedEntity)
            WHERE a.tok_index_doc = ne2.headTokenIndex
              AND coalesce(ne.token_id, ne.id) <> coalesce(ne2.token_id, ne2.id)
              AND ne.type = ne2.type
            SET ne.kb_id    = coalesce(ne.kb_id, ne2.kb_id),
                ne.score    = coalesce(ne.score, ne2.score),
                ne.spacyType = coalesce(ne.spacyType, ne2.type)
            WITH ne, ne2
            OPTIONAL MATCH (ne2)-[r:REFERS_TO]->(e)
            FOREACH (_ IN CASE WHEN e IS NOT NULL THEN [1] ELSE [] END |
                MERGE (ne)-[:REFERS_TO]->(e)
            )
            WITH ne, ne2, r
            FOREACH (_ IN CASE WHEN ne2:EntityMention AND NOT ne:EntityMention THEN [1] ELSE [] END |
                SET ne:EntityMention, ne:Mention
            )
            DETACH DELETE ne2
        """
        self.logger.debug("prioritize_spacy_entities: running for %s", document_id)
        self.execute_query(salvage_query, {"documentId": document_id})

    def prioritize_dbpedia_entities(self, document_id):
        """Prefer DBpedia-linked entities over spaCy-only entities for named types.

        When a NamedEntity has a ``kb_id`` (linked by DBpedia Spotlight / NEL)
        and a competing entity at the same head token does NOT, the linked entity
        wins: its spaCy type is recorded and the unlinked duplicate is removed.

        Safety guards:
        - *Type-compatibility check*: only merge when types are compatible
          (same type, or neither entity is a numeric/temporal type that spaCy
          handles more reliably than DBpedia).
        - *Nested-entity preservation*: when the two entities share a head token
          but have *different span extents*, they are linguistically distinct
          (e.g. outer "President of France" vs inner "France").  In that case a
          ``NESTED_IN`` edge is written instead of deleting the inner entity.
        - *Pre-delete metadata salvage*: ``spacyType`` and ``score`` from ``ne2``
          are copied to ``ne`` before removal.
        - ``documentId`` is used to scope the traversal explicitly.

        :param document_id: Document id scoping this fuse pass.
        """
        # Step 1 — handle nested entities: same head, different span → preserve
        #   as NESTED_IN rather than deleting.
        nested_query = """
            MATCH (d:AnnotatedText {id: $documentId})
                  -[:CONTAINS_SENTENCE]->(:Sentence)
                  -[:HAS_TOKEN]->(a:TagOccurrence)
                  --(ne:NamedEntity)
            WHERE ne.kb_id IS NOT NULL
              AND a.tok_index_doc = ne.headTokenIndex
            MATCH (a)--(ne2:NamedEntity)
            WHERE a.tok_index_doc = ne2.headTokenIndex
              AND coalesce(ne.token_id, ne.id) <> coalesce(ne2.token_id, ne2.id)
              AND (coalesce(ne.start_tok, ne.index) <> coalesce(ne2.start_tok, ne2.index)
                   OR coalesce(ne.end_tok, -1) <> coalesce(ne2.end_tok, -1))
            MERGE (ne2)-[:NESTED_IN {source: 'entity_fuser', provenance_rule_id: 'fuser_nested_preservation'}]->(ne)
        """
        self.logger.debug("prioritize_dbpedia_entities: nesting pass for %s", document_id)
        self.execute_query(nested_query, {"documentId": document_id})

        # Step 2 — for same-span duplicates, salvage metadata and delete the
        #   unlinked competitor.
        salvage_query = """
            MATCH (d:AnnotatedText {id: $documentId})
                  -[:CONTAINS_SENTENCE]->(:Sentence)
                  -[:HAS_TOKEN]->(a:TagOccurrence)
                  --(ne:NamedEntity)
            WHERE ne.kb_id IS NOT NULL
              AND a.tok_index_doc = ne.headTokenIndex
            MATCH (a)--(ne2:NamedEntity)
            WHERE a.tok_index_doc = ne2.headTokenIndex
              AND coalesce(ne.token_id, ne.id) <> coalesce(ne2.token_id, ne2.id)
              AND ne.type = ne2.type
              AND coalesce(ne.start_tok, ne.index) = coalesce(ne2.start_tok, ne2.index)
              AND coalesce(ne.end_tok, -1) = coalesce(ne2.end_tok, -1)
            SET ne.spacyType = coalesce(ne.spacyType, ne2.type),
                ne.score     = coalesce(ne.score, ne2.score)
            WITH ne, ne2
            OPTIONAL MATCH (ne2)-[r:REFERS_TO]->(e)
            FOREACH (_ IN CASE WHEN e IS NOT NULL THEN [1] ELSE [] END |
                MERGE (ne)-[:REFERS_TO]->(e)
            )
            WITH ne, ne2
            FOREACH (_ IN CASE WHEN ne2:EntityMention AND NOT ne:EntityMention THEN [1] ELSE [] END |
                SET ne:EntityMention, ne:Mention
            )
            DETACH DELETE ne2
        """
        self.logger.debug("prioritize_dbpedia_entities: salvage+delete pass for %s", document_id)
        self.execute_query(salvage_query, {"documentId": document_id})

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
        self.logger.info("fuse_entities: starting fuse for %s", document_id)
        self.assign_head_info_to_multitoken_entities(document_id)
        self.assign_head_info_to_singletoken_entities(document_id)
        self.prioritize_spacy_entities(document_id)
        self.prioritize_dbpedia_entities(document_id)
        self.logger.info("fuse_entities: completed fuse for %s", document_id)
        return ''

    def execute_query(self, query, params):
        self.logger.debug("execute_query called with params: %s", params)
        result = self.neo4j_repository.execute_query(query, params)
        return result