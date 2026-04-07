import logging
from textgraphx.neo4j_client import make_graph_from_config
from textgraphx.utils.id_utils import make_frame_id, make_fa_id

logger = logging.getLogger(__name__)


class SRLProcessor:
    """Semantic Role Labeling (SRL) storage component.

    Purpose:
      - Persist SRL `Frame` and `FrameArgument` nodes created by an SRL tagger.
      - Create deterministic ids for frames and arguments and link token
        `TagOccurrence` nodes to the created nodes via `PARTICIPATES_IN`.

    Expected inputs:
      - spaCy `Doc` objects where SRL annotations are attached as a token-level
        extension `tok._.SRL` mapping predicate/role labels to index spans.

    Notes:
      - All writes use MERGE and deterministic ids so runs are idempotent.
      - The component reads Neo4j config via `make_graph_from_config()` and uses
        the BoltGraphCompat wrapper to preserve `.run(...).data()` semantics.
    """

    def __init__(self, uri=None, username=None, password=None):
        # configuration is read from config.ini inside make_graph_from_config
        self.graph = make_graph_from_config()

    def _merge_frame(self, doc_id, start, end, headword, head_index, text):
        """Create (or merge) a Frame node.

        Args:
            doc_id: Document identifier (used to scope the generated id).
            start: Start token index of the frame span (inclusive).
            end: End token index of the frame span (inclusive).
            headword: The lexical head string for the frame.
            head_index: Token index of the head token.
            text: Surface text of the frame span.

        Returns:
            The generated frame id (string) used as the node's `id` property.
        """

        frame_id = make_frame_id(doc_id, start, end)
        query = """
        MERGE (f:Frame {id: $frame_id})
        SET f.headword = $headword, f.headTokenIndex = $head_index, f.text = $text,
            f.framework = 'PROPBANK',
            f.start_tok = $start, f.end_tok = $end,
            f.startIndex = $start, f.endIndex = $end
        RETURN id(f) as frame_node_id
        """
        params = {"frame_id": frame_id, "headword": headword, "head_index": head_index, "text": text, "start": start, "end": end}
        self.graph.run(query, params)
        logger.debug("_merge_frame created frame_id=%s for doc_id=%s span=%s-%s", frame_id, doc_id, start, end)
        return frame_id

    def _link_indices_to_node(self, doc_id, indices, node_label, node_id_prop, node_id):
        """Link TagOccurrence nodes to a target node via PARTICIPATES_IN.

        Args:
            doc_id: Document id used to scope matching AnnotatedText.
            indices: Iterable of token indices (tok_index_doc) to link.
            node_label: Label of the target node (unused by current cypher but
                left for readability).
            node_id_prop: Property name used to match the node (e.g., 'id').
            node_id: Value of the id property to match the target node.
        """
        query = """
        UNWIND $indices as idx
        MATCH (x:TagOccurrence {tok_index_doc: idx})-[:HAS_TOKEN]-()-[:CONTAINS_SENTENCE]-(:AnnotatedText {id: $doc_id})
        MATCH (n {id: $node_id})
        MERGE (x)-[:PARTICIPATES_IN]->(n)
        MERGE (x)-[:IN_FRAME]->(n)
        """
        params = {"indices": indices, "doc_id": doc_id, "node_id": node_id}
        logger.debug("Linking %d indices to node %s", len(indices), node_id)
        self.graph.run(query, params)

    def _merge_frame_argument(self, doc_id, start, end, head, head_index, arg_type, text):
        """Create (or merge) a FrameArgument node.

        Args:
            doc_id: Document id used to create a unique node id.
            start: Start token index (inclusive).
            end: End token index (inclusive).
            head: Surface text of the head token.
            head_index: Token index of the head token.
            arg_type: SRL label for the argument (e.g., 'ARG0', 'ARGM-TMP').
            text: Surface text of the argument span.

        Returns:
            The generated frame-argument id string.
        """

        arg_id = make_fa_id(doc_id, start, end, arg_type)
        query = """
        MERGE (a:FrameArgument {id: $arg_id})
        SET a.head = $head, a.headTokenIndex = $head_index, a.type = $arg_type, a.text = $text,
            a.start_tok = $start, a.end_tok = $end,
            a.startIndex = $start, a.endIndex = $end
        RETURN id(a) as arg_node_id
        """
        params = {"arg_id": arg_id, "head": head, "head_index": head_index, "arg_type": arg_type, "text": text, "start": start, "end": end}
        self.graph.run(query, params)
        logger.debug("_merge_frame_argument created arg_id=%s type=%s span=%s-%s", arg_id, arg_type, start, end)
        return arg_id

    def process_srl(self, doc, flag_display=False):
        """Process SRL frames for a spaCy document and store frames and
        frame-arguments in the graph.

        The spaCy SRL extension is expected on tokens under `tok._.SRL` where
        each item maps a label (e.g., 'V', 'ARG0') to a list of index spans.
        """
        doc_id = getattr(doc._, "text_id", None)
        if doc_id is None:
            # caller must set doc._.text_id before calling process_srl
            raise ValueError("Document must have ._.text_id set")

        logger.info("process_srl called for doc_id=%s", doc_id)
        for tok in doc:
            frameDict = {}
            sg_id = None

            for x, indices_list in getattr(tok._, "SRL", {}).items():
                for y in indices_list:
                    start = y[0]
                    end = y[-1]
                    span = doc[start:end + 1]
                    token = span.root

                    if x == "V":
                        # create/merge the Frame node
                        sg_id = self._merge_frame(doc_id, start, end, token.text, token.i, span.text)
                        # link tag occurrences to the frame
                        indices = list(range(start, end + 1)) if len(y) == 2 else list(y)
                        self._link_indices_to_node(doc_id, indices, "Frame", "id", sg_id)
                    else:
                        # frame argument
                        arg_id = self._merge_frame_argument(doc_id, start, end, token.text, token.i, x, span.text)
                        indices = list(range(start, end + 1)) if len(y) == 2 else list(y)
                        self._link_indices_to_node(doc_id, indices, "FrameArgument", "id", arg_id)

                        if x not in frameDict:
                            frameDict[x] = []
                        frameDict[x].append(arg_id)

            # after collecting, link frame arguments to the frame via PARTICIPANT
            if sg_id is not None:
                for arg_type, arg_ids in frameDict.items():
                    for arg_id in arg_ids:
                        q = """
                        MATCH (a:FrameArgument {id: $arg_id})
                        MATCH (f:Frame {id: $frame_id})
                        MERGE (a)-[r:PARTICIPANT]->(f)
                        SET r.type = $arg_type
                        MERGE (a)-[cr:HAS_FRAME_ARGUMENT]->(f)
                        SET cr.type = $arg_type
                        RETURN id(r)
                        """
                        params = {"arg_id": arg_id, "frame_id": sg_id, "arg_type": arg_type}
                        self.graph.run(q, params)
                        logger.debug("Linked FrameArgument %s to Frame %s", arg_id, sg_id)