import requests
import time
from textgraphx.TextProcessor import Neo4jRepository  # Import the Neo4jRepository class
from textgraphx.utils.id_utils import make_ne_id, make_ne_token_id, make_ne_uid
import logging

# module logger
logger = logging.getLogger(__name__)

class EntityExtractor:
    def __init__(self, api_url, driver):
        self.api_url = api_url
        self.neo4j_repo = Neo4jRepository(driver)  # Instantiate Neo4jRepository

    @staticmethod
    def _resolve_uid_anchor_token_index(entity):
        """Return the stable anchor token index used for extractor-side UIDs.

        Prefer an explicit head token index when the upstream extractor provides
        one. If no head index is available, fall back to the start token index,
        which is a deterministic span anchor and less boundary-sensitive than
        the previous end-index-derived fallback.
        """
        for key in ("head_token_index", "headTokenIndex", "anchor_token_index", "anchorTokenIndex"):
            value = entity.get(key)
            if value is not None:
                return int(value)

        head = entity.get("head")
        if isinstance(head, dict):
            for key in ("token_index", "tokenIndex", "index"):
                value = head.get(key)
                if value is not None:
                    return int(value)

        return int(entity["start"])

    def extract_entities(self, text):
        headers = {"Content-Type": "application/json"}
        data = {"text": text}
        
        logger.debug("Calling entity extraction API: %s", self.api_url)
        response = requests.post(self.api_url, headers=headers, json=data)
        if response.status_code == 200:
            ents = response.json().get("entities", [])
            logger.info("EntityExtractor: extracted %d entities", len(ents))
            return ents
        else:
            logger.error("Error calling the entity extraction API: %s", response.status_code)
            return []

    def integrate_entities_into_db(self, entities, text_id):
        # Fetch existing NamedEntities linked to the AnnotatedText node
        existing_entities = self.fetch_named_entities(text_id)
        logger.debug("Existing Entities: %s", existing_entities)
        current_uids = []

        for entity in entities:
            start_index = entity['start']
            end_index = entity['end']
            label = entity['label']
            uid_anchor_token_index = self._resolve_uid_anchor_token_index(entity)
            matched = False

            # Check for matches with existing NamedEntities
            for existing_entity in existing_entities:
                existing_entity = dict(existing_entity)
                ne = dict(existing_entity.get("ne", {}))
                # prefer token_id when present, fall back to legacy id
                ne_token_id = ne.get('token_id')
                ne_id = ne.get('id')
                ne_uid = ne.get('uid')
                # quick index match guard (keeps behaviour similar to previous code)
                if ne.get('index') == start_index and ne.get('end_index') == end_index:
                    # If a match is found, add a new label. Match by token_id when possible
                    add_label_query = """
                        MATCH (ne:NamedEntity) WHERE (coalesce(ne.token_id, ne.id) = $match_id)
                        SET ne:NewLabel
                        RETURN ne.id AS id
                    """
                    match_val = ne_token_id if ne_token_id is not None else ne_id
                    if match_val is None:
                        continue
                    self.neo4j_repo.execute_query(add_label_query, {"match_id": match_val})
                    derived_uid = ne_uid if ne_uid is not None else make_ne_uid(
                        text_id,
                        entity.get('text', ''),
                        uid_anchor_token_index,
                    )
                    self.neo4j_repo.execute_query(
                        """
                        MATCH (ne:NamedEntity)
                        WHERE coalesce(ne.token_id, ne.id) = $match_id
                        SET ne.uid = coalesce(ne.uid, $uid),
                            ne.legacy_span_id = coalesce(ne.legacy_span_id, ne.id)
                        """,
                        {"match_id": match_val, "uid": derived_uid},
                    )
                    current_uids.append(str(derived_uid))
                    matched = True
                    break

            # If no match was found, create a new NamedEntity node
            if not matched:
                # compute token-index based id (entity.start / entity.end are token positions expected)
                ne_id = make_ne_id(text_id, start_index, end_index - 1, label)
                ne_uid = make_ne_uid(text_id, entity.get('text', ''), uid_anchor_token_index)
                # Compute type-agnostic token_id so it stays stable even if
                # ne_id is later remapped to a canonical/NEL URI.
                ne_token_id = make_ne_token_id(text_id, start_index, end_index - 1)
                create_entity_query = """
                    OPTIONAL MATCH (legacy:NamedEntity {id: $id})
                    WITH legacy
                    CALL {
                        WITH legacy
                        WITH legacy WHERE legacy IS NOT NULL
                        SET legacy.uid = coalesce(legacy.uid, $uid),
                            legacy.legacy_span_id = coalesce(legacy.legacy_span_id, legacy.id)
                        RETURN legacy AS ne
                        UNION
                        WITH legacy
                        WITH legacy WHERE legacy IS NULL
                        MERGE (ne:NamedEntity {uid: $uid})
                        RETURN ne
                    }
                    SET ne.id = $id,
                        ne.legacy_span_id = coalesce(ne.legacy_span_id, $id),
                        ne.uid = $uid,
                        ne.type = $type, 
                        ne.ent_class = $ent_class,
                        ne.value = $value, 
                        ne.start_index = $start_index, 
                        ne.end_index = $end_index,
                        ne.token_id = $token_id, ne.token_start = $start_index, ne.token_end = $end_index
                    WITH ne
                    MATCH (text:AnnotatedText)-[:CONTAINS_SENTENCE]->(sentence:Sentence)-[:HAS_TOKEN]->(tagOccurrence:TagOccurrence)
                    WHERE text.id = $documentId AND tagOccurrence.tok_index_doc >= $start_index AND tagOccurrence.tok_index_doc <= $end_index - 1
                    MERGE (ne)<-[:PARTICIPATES_IN]-(tagOccurrence)
                    MERGE (ne)<-[:IN_MENTION]-(tagOccurrence)
                """
                self.neo4j_repo.execute_query(create_entity_query, {
                    "documentId": text_id,
                    "start_index": start_index,
                    "end_index": end_index,
                    "type": label,
                    "ent_class": label, # Could add full map later, but label protects schema
                    "value": entity['text'],
                    "id": ne_id,
                    "uid": ne_uid,
                    "token_id": ne_token_id,
                })
                current_uids.append(str(ne_uid))

        self._reconcile_stale_named_entities(text_id, current_uids)

    def _reconcile_stale_named_entities(self, document_id, current_uids):
        """Mark unseen NamedEntity nodes stale and retire mention edges.

        Mirrors EntityProcessor reconciliation behavior so API-based extraction
        runs remain resilient to stale duplicate spans across re-extractions.
        """
        current_uids = [str(x) for x in set(current_uids or []) if x is not None]
        run_id = f"ne_reextract_{int(time.time() * 1000)}"

        if current_uids:
            self.neo4j_repo.execute_query(
                """
                UNWIND $current_uids AS uid
                MATCH (ne:NamedEntity {uid: uid})
                SET ne.stale = false,
                    ne.stale_reason = null,
                    ne.stale_run_id = $run_id,
                    ne.last_seen_at = timestamp()
                """,
                {"current_uids": current_uids, "run_id": run_id},
            )

        rows = self.neo4j_repo.execute_query(
            """
            MATCH (text:AnnotatedText {id: $documentId})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(:TagOccurrence)-[:IN_MENTION|PARTICIPATES_IN]->(ne:NamedEntity)
            WITH DISTINCT ne
            WHERE NOT coalesce(ne.uid, '') IN $current_uids
            SET ne.stale = true,
                ne.stale_reason = 'reextract_not_seen',
                ne.stale_run_id = $run_id,
                ne.stale_at = timestamp()
            WITH collect(ne) AS stale_nodes
            CALL {
                WITH stale_nodes
                UNWIND stale_nodes AS ne
                OPTIONAL MATCH (:TagOccurrence)-[r:IN_MENTION|PARTICIPATES_IN]->(ne)
                DELETE r
                RETURN count(r) AS retired_mention_edges
            }
            CALL {
                WITH stale_nodes
                UNWIND stale_nodes AS ne
                OPTIONAL MATCH (ne)-[rr:REFERS_TO]->(:Entity)
                DELETE rr
                RETURN count(rr) AS retired_refers_to_edges
            }
            RETURN size(stale_nodes) AS stale_nodes,
                   retired_mention_edges,
                   retired_refers_to_edges
            """,
            {
                "documentId": document_id,
                "current_uids": current_uids,
                "run_id": run_id,
            },
        )
        if rows:
            stale_nodes = rows[0].get("stale_nodes", 0)
            retired_mention_edges = rows[0].get("retired_mention_edges", 0)
            retired_refers_to_edges = rows[0].get("retired_refers_to_edges", 0)
            if stale_nodes or retired_mention_edges or retired_refers_to_edges:
                logger.info(
                    "EntityExtractor reconciliation: marked %d stale NamedEntity nodes, retired %d mention edges, and retired %d REFERS_TO edges for document %s",
                    stale_nodes,
                    retired_mention_edges,
                    retired_refers_to_edges,
                    document_id,
                )

    def fetch_named_entities(self, document_id):
        logger.debug("Fetching named entities for document ID: %s", document_id)
        # Convert document_id to integer if it's a string
        document_id_int = int(document_id) if isinstance(document_id, str) else document_id
        logger.debug("Fetching named entities for document ID: %s", document_id_int)

        query = """
            MATCH (text:AnnotatedText)-[:CONTAINS_SENTENCE]->(sentence:Sentence)-[:HAS_TOKEN]->(tagOccurrence:TagOccurrence)-[:PARTICIPATES_IN]->(ne:NamedEntity)
            WHERE text.id = $document_id
            RETURN ne
        """
        logger.debug("Query: %s", query)
        return list(self.neo4j_repo.execute_query(query, {"document_id": document_id_int}))
    
    
    def fetch_named_entities2(self, document_id):
        logger.debug("Fetching named entities for document ID: %s", document_id)
        # Convert document_id to integer if it's a string
        document_id_int = int(document_id) if isinstance(document_id, str) else document_id
        logger.debug("Fetching named entities for document ID: %s", document_id_int)

        query = """
            MATCH (text:AnnotatedText)-[:CONTAINS_SENTENCE]->(sentence:Sentence)-[:HAS_TOKEN]->(tagOccurrence:TagOccurrence)-[:PARTICIPATES_IN]->(ne:NamedEntity)
            WHERE text.id = $document_id
            RETURN ne
        """
        logger.debug("Query: %s", query)
        return list(self.neo4j_repo.execute_query(query, {"document_id": document_id_int}))

# Test with a hardcoded document ID
# Uncomment the following lines to test
# test_document_id = 1  # Replace with a valid document ID
# entities = fetch_named_entities(test_document_id)
# print("Fetched entities: ", entities)
