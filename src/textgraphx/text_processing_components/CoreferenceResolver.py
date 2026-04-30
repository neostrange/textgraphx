"""CoreferenceResolver

Create Antecedent and CorefMention nodes from an external coreference
service output and link mention tokens to the created nodes. The
implementation creates deterministic ids for nodes so other phases can
reference them consistently.
"""

import requests
import json
from textgraphx.database.client import make_graph_from_config
from textgraphx.utils.id_utils import make_coref_uid
import logging

# module logger
logger = logging.getLogger(__name__)


class CoreferenceResolver:
    """Component that persists coreference cluster information into Neo4j.

    Methods:
      - create_node(node_type, text, start_index, end_index, doc_id): create or
        merge a node representing an antecedent or mention.
      - connect_node_to_tag_occurrences(node_id, index_range, doc_id): bulk link
        TagOccurrence tokens to a node via `PARTICIPATES_IN`.
      - resolve_coreference(doc, text_id): call an external coref service and
        persist the returned clusters as nodes and COREF relations.
    """

    def __init__(self, coreference_service_endpoint):
        """Initialize resolver and create a bolt-driver backed graph wrapper.

        Args:
            coreference_service_endpoint (str): URL of the coref service.
        """
        self.graph = make_graph_from_config()
        self.coreference_service_endpoint = coreference_service_endpoint
        logger.debug("CoreferenceResolver initialized with endpoint=%s", coreference_service_endpoint)

    def _find_named_entity_by_span(self, start_index, end_index, doc_id):
        """Return an existing NamedEntity id for an exact token span, if present.

        This is used to avoid creating a parallel CorefMention node when the
        NER pipeline has already materialized a mention for the same span.
        """
        query = """
                MATCH (:AnnotatedText {id: $doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(:TagOccurrence)-[:IN_MENTION]->(ne:NamedEntity)
        WHERE coalesce(ne.start_tok, ne.token_start, ne.index) = $start
          AND coalesce(ne.end_tok, ne.token_end, ne.end_index) = $end
        RETURN ne.id AS node_id
            ORDER BY ne.uid, ne.id
        LIMIT 1
        """
        params = {"doc_id": doc_id, "start": start_index, "end": end_index}
        rows = self.graph.run(query, params).data()
        if rows:
            return rows[0].get("node_id")
        return None

    def create_node(self, node_type, text, start_index, end_index, doc_id):
        """Create or merge a coreference-related node and return its generated id string.

        The created node will have a stable id based on the node_type, document id
        and token span. This lets other code refer to the node deterministically
        without needing the numeric internal node id from Neo4j.

        Args:
            node_type: Label for the node (e.g., 'Antecedent' or 'CorefMention').
            text: Surface text of the span.
            start_index: Start token index (inclusive).
            end_index: End token index (inclusive).
            doc_id: Document identifier used to scope the id.

        Returns:
            The string id assigned to the node (used as the node's `id` property).
        """
        node_uid = make_coref_uid(doc_id, text, start_index, node_type)
        if node_type == "CorefMention":
            existing_named_entity_id = self._find_named_entity_by_span(start_index, end_index, doc_id)
            if existing_named_entity_id is not None:
                query = """
                MATCH (ne:NamedEntity {id: $node_id})
                SET ne:CorefMention,
                    ne:Mention,
                    ne.uid = coalesce(ne.uid, $node_uid),
                    ne.text = coalesce(ne.text, ne.value, $text),
                    ne.start_tok = coalesce(ne.start_tok, $start),
                    ne.end_tok = coalesce(ne.end_tok, $end),
                    ne.startIndex = coalesce(ne.startIndex, $start),
                    ne.endIndex = coalesce(ne.endIndex, $end)
                RETURN ne.id
                """
                params = {
                    "node_id": existing_named_entity_id,
                    "node_uid": node_uid,
                    "text": text,
                    "start": start_index,
                    "end": end_index,
                }
                self.graph.run(query, params)
                logger.debug(
                    "create_node: re-used NamedEntity %s as CorefMention for doc=%s span=%s-%s",
                    existing_named_entity_id,
                    doc_id,
                    start_index,
                    end_index,
                )
                return existing_named_entity_id

        node_id = f"{node_type}_{doc_id}_{start_index}_{end_index}"
        query = """
        MERGE (n:%s {id: $node_id})
        SET n.text = $text,
            n.uid = $node_uid,
            n.start_tok = $start, n.end_tok = $end,
            n.startIndex = $start, n.endIndex = $end
        RETURN n.id
        """ % node_type
        params = {
            "node_id": node_id,
            "node_uid": node_uid,
            "text": text,
            "start": start_index,
            "end": end_index,
        }
        self.graph.run(query, params)
        logger.debug("create_node: created/merged %s for doc=%s span=%s-%s", node_id, doc_id, start_index, end_index)
        return node_id

    def connect_node_to_tag_occurrences(self, node_id, index_range, doc_id):
        """Link TagOccurrence nodes (tokens) to a previously created node.

        This method issues a single UNWIND Cypher query that matches TagOccurrence
        nodes by their tok_index_doc and creates PARTICIPATES_IN relationships to
        the node identified by `node_id`.

        Args:
            node_id: The string id of the previously created node.
            index_range: Iterable of integer token indices (tok_index_doc values).
            doc_id: Document identifier used to scope the matching AnnotatedText.
        """
        query = """
        UNWIND $indices as idx
        MATCH (x:TagOccurrence {tok_index_doc: idx})-[:HAS_TOKEN]-()-[:CONTAINS_SENTENCE]-(:AnnotatedText {id: $doc_id})
        MATCH (n {id: $node_id})
        MERGE (x)-[:PARTICIPATES_IN]->(n)
        MERGE (x)-[:IN_MENTION]->(n)
        """
        params = {"indices": list(index_range), "doc_id": doc_id, "node_id": node_id}
        logger.debug("connect_node_to_tag_occurrences: linking %d indices to node %s in doc %s", len(list(index_range)), node_id, doc_id)
        self.graph.run(query, params)

    def _service_span_to_inclusive_bounds(self, span_token_indexes, doc_length):
        """Normalize a service span to inclusive token boundaries.

        The live coreference service returns two-value spans as half-open
        `[start, end)` boundaries. Longer lists are treated as explicit token
        indices and collapsed to their first/last index.
        """
        if doc_length <= 0:
            raise ValueError("Cannot normalize coreference spans for an empty document")

        values = [int(index) for index in span_token_indexes]
        if not values:
            raise ValueError("Coreference service returned an empty span")

        if len(values) == 1:
            start = end = values[0]
        elif len(values) == 2:
            start, end_exclusive = values
            end = start if end_exclusive <= start else end_exclusive - 1
        else:
            start, end = values[0], values[-1]

        if start < 0 or end < 0 or start >= doc_length or end >= doc_length or start > end:
            raise ValueError(
                f"Invalid coreference span {values!r} for document length {doc_length}"
            )

        return start, end

    def resolve_coreference(self, doc, text_id):
        """Resolve coreference clusters and persist nodes/relations in the graph.

        The method expects the external coreference service to return a JSON
        structure containing a `clusters` key whose value is a list of clusters.
        Each cluster is a sequence of spans where a span is either an explicit
        list of token indices or a two-value half-open token range `[start, end)`.
        The first span in each cluster is treated as the antecedent and
        subsequent spans are treated as mentions referring to it.

        The function will create `Antecedent` and `CorefMention` nodes and
        connect TagOccurrence nodes to them. It also creates `COREF` relations
        from mention nodes to their antecedents.

        Args:
            doc: spaCy Doc object (tokens accessible by index).
            text_id: AnnotatedText document id used to scope graph matches.

        Returns:
            A list of dicts describing created coreference links: each dict has
            keys `referent` and `antecedent` with the created node id strings.
        """
        logger.info("resolve_coreference: resolving coref for text_id=%s", text_id)
        result = self.call_coreference_resolution_api(self.coreference_service_endpoint, doc.text)
        if result is None:
            logger.warning("resolve_coreference: coref service returned no result for text_id=%s", text_id)
            return []

        coref = []
        for cluster in result.get("clusters", []):
            if not cluster:
                continue
            antecedent = cluster[0]
            try:
                ant_start, ant_end = self._service_span_to_inclusive_bounds(antecedent, len(doc))
            except ValueError:
                logger.warning(
                    "resolve_coreference: skipping invalid antecedent span %r for text_id=%s",
                    antecedent,
                    text_id,
                )
                continue
            antecedent_node_id = self.create_node("Antecedent", doc[ant_start:ant_end+1].text, ant_start, ant_end, text_id)
            self.connect_node_to_tag_occurrences(antecedent_node_id, range(ant_start, ant_end + 1), text_id)
            logger.debug("Created antecedent %s for cluster size=%d", antecedent_node_id, len(cluster))

            for span_token_indexes in cluster[1:]:
                try:
                    start, end = self._service_span_to_inclusive_bounds(span_token_indexes, len(doc))
                except ValueError:
                    logger.warning(
                        "resolve_coreference: skipping invalid mention span %r for text_id=%s",
                        span_token_indexes,
                        text_id,
                    )
                    continue
                mention_node_id = self.create_node("CorefMention", doc[start:end+1].text, start, end, text_id)
                self.connect_node_to_tag_occurrences(mention_node_id, range(start, end + 1), text_id)
                # create COREF relation
                q = """
                MATCH (a {id: $mention_id}), (b {id: $ante_id})
                MERGE (a)-[:COREF]->(b)
                """
                self.graph.run(q, {"mention_id": mention_node_id, "ante_id": antecedent_node_id})
                coref.append({"referent": mention_node_id, "antecedent": antecedent_node_id})
                logger.debug("Created mention %s for antecedent %s", mention_node_id, antecedent_node_id)

        return coref

    def call_coreference_resolution_api(self, coreference_service_endpoint, text):
        """
        Calls the coreference resolution API for coreference resolution.

        Args:
            coreference_service_endpoint (str): The endpoint URL for the coreference service.
            text (str): The text to be processed for coreference resolution.

        Returns:
            dict: The response from the coreference resolution API.
        """

        # Define the API endpoint and headers
        url = coreference_service_endpoint
        headers = {"Content-Type": "application/json"}

        # Prepare the payload
        payload = {"document": text}

        try:
            # Send a POST request to the API
            response = requests.post(url, headers=headers, json=payload)

            # Check if the request was successful
            response.raise_for_status()

            # Return the JSON response
            return response.json()

        except requests.exceptions.HTTPError as http_err:
            # Handle HTTP errors
            logger.exception("HTTP error occurred when calling coref service: %s", http_err)
        except Exception as err:
            # Handle any other exceptions
            logger.exception("An error occurred when calling coref service: %s", err)

        # If an error occurs, return None
        return None