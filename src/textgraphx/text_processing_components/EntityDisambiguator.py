import logging
from textgraphx.utils.id_utils import make_entity_id

logger = logging.getLogger(__name__)


class EntityDisambiguator:
    #For the purpose of mapping named entities to entity instances in our pipeline, we distinguished between two types of named entities.
#  The first type includes entities that have been successfully disambiguated and assigned a unique KBID by the entity disambiguation module.
#  These entities can be easily mapped by creating instances based on the distinct KBIDs. The second type of named entities, 
# however, are unknown to the entity disambiguation module and are assigned a NULL KBID. To map these named entities, we rely on the text of
#  the named entity's span and its assigned type, which was determined by the NER component. As a result, named entity mentions with the 
# same text value and type are considered to refer to a single entity instance.
# """
#    This class is responsible for building an entity graph by extracting entities from a document
#    and creating relationships between them.
#    """

    def __init__(self, neo4j_repository):
        self.neo4j_repository = neo4j_repository
        self.logger = logger

    def disambiguate_entities(self, document_id):
        """
        Build an entity graph by extracting direct and indirect entities from a document.

        :param document_id: ID of the document to extract entities from
        """
        # KB-linked entities: cross-doc stable id derived from the KB URI fragment.
        # The labeled traversal replaces the fragile wildcard path [*3..3].
        extract_direct_entities_query = """
            MATCH (document:AnnotatedText {id: $documentId})
                  -[:CONTAINS_SENTENCE]->(:Sentence)
                  -[:HAS_TOKEN]->(:TagOccurrence)
                  -[:PARTICIPATES_IN]->(ne:NamedEntity)
            WHERE NOT (ne.type IN ['NP', 'TIME', 'ORDINAL', 'NUMBER', 'MONEY', 'DATE', 'CARDINAL', 'QUANTITY', 'PERCENT'])
              AND ne.kb_id IS NOT NULL
            MERGE (entity:Entity {
                type:  ne.type,
                kb_id: ne.kb_id,
                id:    split(ne.kb_id, '/')[-1]
            })
            MERGE (ne)-[:REFERS_TO {
                type:               'evoke',
                source:             'entity_disambiguator',
                confidence:         1.0,
                provenance_rule_id: 'disambiguate_direct'
            }]->(entity)
        """

        # Unresolved entities: per-document scoped id computed from (doc_id, surface, type).
        collect_unresolved_query = """
            MATCH (document:AnnotatedText {id: $documentId})
                  -[:CONTAINS_SENTENCE]->(:Sentence)
                  -[:HAS_TOKEN]->(:TagOccurrence)
                  -[:PARTICIPATES_IN]->(ne:NamedEntity)
            WHERE NOT (ne.type IN ['NP', 'TIME', 'ORDINAL', 'MONEY', 'NUMBER', 'DATE', 'CARDINAL', 'QUANTITY', 'PERCENT'])
              AND ne.kb_id IS NULL
            RETURN ne.id AS ne_id, ne.value AS surface, ne.type AS ne_type
        """

        self.logger.info("disambiguate_entities: starting for %s", document_id)
        self.execute_query(extract_direct_entities_query, {"documentId": document_id})

        unresolved_rows = self.execute_query(collect_unresolved_query, {"documentId": document_id})
        if unresolved_rows:
            params_list = []
            for row in unresolved_rows:
                entity_id = make_entity_id(document_id, row.get("surface"), row.get("ne_type") or "")
                params_list.append({
                    "ne_id":     row["ne_id"],
                    "entity_id": entity_id,
                    "ne_type":   row.get("ne_type") or "",
                    "surface":   row.get("surface") or "",
                })
            extract_indirect_entities_query = """
                UNWIND $rows AS row
                MATCH (ne:NamedEntity {id: row.ne_id})
                MERGE (entity:Entity {id: row.entity_id})
                ON CREATE SET entity.type  = row.ne_type,
                              entity.kb_id = row.surface
                MERGE (ne)-[:REFERS_TO {
                    type:               'evoke',
                    source:             'entity_disambiguator',
                    confidence:         0.5,
                    provenance_rule_id: 'disambiguate_indirect'
                }]->(entity)
            """
            self.execute_query(extract_indirect_entities_query, {"rows": params_list})

        self.logger.info("disambiguate_entities: completed for %s", document_id)


    def execute_query(self, query, params):
        self.logger.debug("EntityDisambiguator.execute_query called with params: %s", params)
        result = self.neo4j_repository.execute_query(query, params)
        return result