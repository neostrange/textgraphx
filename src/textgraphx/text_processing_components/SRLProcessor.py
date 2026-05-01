import logging
from textgraphx.database.client import make_graph_from_config
from textgraphx.utils.id_utils import make_frame_id, make_fa_id
from textgraphx.adapters.srl_role_normalizer import normalize_role
from textgraphx.infrastructure.config import get_config

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

    def _merge_frame(self, doc_id, start, end, headword, head_index, text,
                      sense=None, sense_conf=None, framework="PROPBANK"):
        """Create (or merge) a Frame node.

        Args:
            doc_id: Document identifier (used to scope the generated id).
            start: Start token index of the frame span (inclusive).
            end: End token index of the frame span (inclusive).
            headword: The lexical head string for the frame.
            head_index: Token index of the head token.
            text: Surface text of the frame span.
            sense: Optional roleset sense id (e.g. ``"run.02"`` for PropBank or
                ``"acquisition.01"`` for NomBank). Persisted as ``f.sense``
                only when not ``None``. Advisory-tier property (per
                ``docs/schema.md`` §5.5).
            sense_conf: Optional float confidence for ``sense``. Persisted as
                ``f.sense_conf`` only when not ``None``.
            framework: Sense inventory the frame is anchored in. One of
                ``"PROPBANK"`` (default, verb SRL) or ``"NOMBANK"`` (nominal
                SRL via CogComp service).

        Returns:
            The generated frame id (string) used as the node's `id` property.
        """

        frame_id = make_frame_id(doc_id, start, end)
        # Determine provisional flag: a frame is provisional when sense_conf is
        # provided but falls below the configured gating threshold.
        try:
            threshold = get_config().ingestion.frame_confidence_min
        except Exception:
            threshold = 0.50
        provisional = (
            sense_conf is not None and sense_conf < threshold
        )
        query = """
        MERGE (f:Frame {id: $frame_id})
        SET f.headword = $headword, f.headTokenIndex = $head_index, f.text = $text,
            f.framework = $framework,
            f.start_tok = $start, f.end_tok = $end,
            f.startIndex = $start, f.endIndex = $end,
            f.provisional = $provisional
        FOREACH (_ IN CASE WHEN $sense IS NULL THEN [] ELSE [1] END |
            SET f.sense = $sense
        )
        FOREACH (_ IN CASE WHEN $sense_conf IS NULL THEN [] ELSE [1] END |
            SET f.sense_conf = $sense_conf
        )
        RETURN id(f) as frame_node_id
        """
        params = {
            "frame_id": frame_id,
            "headword": headword,
            "head_index": head_index,
            "text": text,
            "start": start,
            "end": end,
            "framework": framework,
            "sense": sense,
            "sense_conf": sense_conf,
            "provisional": provisional,
        }
        self.graph.run(query, params)
        logger.debug(
            "_merge_frame created frame_id=%s for doc_id=%s span=%s-%s framework=%s sense=%s",
            frame_id, doc_id, start, end, framework, sense,
        )
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
            arg_type: Canonical SRL label for the argument (e.g., 'ARG0',
                'ARGM-TMP'). Continuation/relative/predicative prefixes/suffixes
                must already have been stripped by the caller via
                :func:`normalize_role`.
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

    def _link_argument_to_frame(self, arg_id, frame_id, raw_label):
        """Link a FrameArgument to its Frame via PARTICIPANT and HAS_FRAME_ARGUMENT.

        Normalizes the raw label to strip continuation/relative/predicative
        affixes and stores the result as ``r.type``.  The raw label is stored
        as ``r.raw_role`` for provenance.  Extra normalization flags
        (``is_continuation``, ``is_relative``, ``predicative``) are stored as
        edge properties when truthy.
        """
        norm = normalize_role(raw_label)
        q = """
        MATCH (a:FrameArgument {id: $arg_id})
        MATCH (f:Frame {id: $frame_id})
        MERGE (a)-[r:PARTICIPANT]->(f)
        SET r.type = $canonical, r.raw_role = $raw
        FOREACH (_ IN CASE WHEN $is_continuation THEN [1] ELSE [] END | SET r.is_continuation = true)
        FOREACH (_ IN CASE WHEN $is_relative     THEN [1] ELSE [] END | SET r.is_relative     = true)
        FOREACH (_ IN CASE WHEN $predicative      THEN [1] ELSE [] END | SET r.predicative      = true)
        MERGE (a)-[cr:HAS_FRAME_ARGUMENT]->(f)
        SET cr.type = $canonical, cr.raw_role = $raw
        RETURN id(r)
        """
        params = {
            "arg_id": arg_id,
            "frame_id": frame_id,
            "canonical": norm.canonical,
            "raw": norm.raw,
            "is_continuation": norm.flags.get("is_continuation", False),
            "is_relative": norm.flags.get("is_relative", False),
            "predicative": norm.flags.get("predicative", False),
        }
        self.graph.run(q, params)
        logger.debug(
            "Linked FrameArgument %s to Frame %s canonical=%s raw=%s flags=%s",
            arg_id, frame_id, norm.canonical, norm.raw, norm.flags,
        )

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

            srl_data = getattr(tok._, "SRL", {})
            # Extract PropBank sense fields injected by extract_srl (transformer-srl service)
            frame_sense = srl_data.get("__frame__")
            frame_score = srl_data.get("__frame_score__")
            try:
                frame_score = float(frame_score) if frame_score is not None else None
            except (TypeError, ValueError):
                frame_score = None

            for x, indices_list in srl_data.items():
                if x.startswith("__"):
                    # skip internal metadata keys like __frame__ / __frame_score__
                    continue
                for y in indices_list:
                    start = y[0]
                    end = y[-1]
                    span = doc[start:end + 1]
                    token = span.root

                    if x == "V":
                        # create/merge the Frame node, passing PropBank sense if available
                        sg_id = self._merge_frame(
                            doc_id, start, end, token.text, token.i, span.text,
                            sense=frame_sense, sense_conf=frame_score, framework="PROPBANK",
                        )
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
                        self._link_argument_to_frame(arg_id, sg_id, arg_type)
                        logger.debug("Linked FrameArgument %s to Frame %s", arg_id, sg_id)

    @staticmethod
    def _bio_to_spans(tags):
        """Convert a BIO tag sequence to a list of ``(label, start, end)``
        triples with inclusive ``end``. Tags ``"O"`` and ``"B-V"`` are skipped
        (the verb/predicate index is provided separately by the SRL service).
        """
        spans = []
        cur_label = None
        cur_start = None
        for i, raw in enumerate(tags):
            tag = str(raw or "O")
            if tag == "O" or tag.endswith("-V"):
                if cur_label is not None:
                    spans.append((cur_label, cur_start, i - 1))
                    cur_label, cur_start = None, None
                continue
            prefix, _, label = tag.partition("-")
            if prefix == "B" or label != cur_label:
                if cur_label is not None:
                    spans.append((cur_label, cur_start, i - 1))
                cur_label, cur_start = label, i
        if cur_label is not None:
            spans.append((cur_label, cur_start, len(tags) - 1))
        return spans

    def process_nominal_srl(self, doc, sentence_results):
        """Persist nominal-SRL frames returned by the CogComp service.

        Args:
            doc: The spaCy ``Doc`` whose ``._.text_id`` identifies the document.
            sentence_results: Iterable of ``(sentence_token_offset, response)``
                tuples, one per sentence on which the nominal SRL service was
                invoked. ``response`` is the JSON object returned by the
                service ``/predict_nom`` endpoint, expected to contain
                ``words`` and ``frames`` keys. Each frame contributes one
                ``Frame`` node (``framework="NOMBANK"``) plus one
                ``FrameArgument`` per non-V BIO span.

        The method is a no-op if ``sentence_results`` is empty or if every
        response is empty / missing frames -- this lets callers safely invoke
        the service even when it is disabled or unavailable.
        """
        doc_id = getattr(doc._, "text_id", None)
        if doc_id is None:
            raise ValueError("Document must have ._.text_id set")
        if not sentence_results:
            return

        for sent_offset, response in sentence_results:
            if not response:
                continue
            words = response.get("words") or []
            frames = response.get("frames") or []
            if not frames:
                continue
            for fr in frames:
                pred_idx_sent = fr.get("predicate_index")
                if pred_idx_sent is None or not (0 <= pred_idx_sent < len(words)):
                    continue
                pred_idx_doc = sent_offset + pred_idx_sent
                pred_text = str(fr.get("predicate") or words[pred_idx_sent])
                sense = fr.get("sense")
                sense_conf = fr.get("sense_score")
                try:
                    sense_conf = float(sense_conf) if sense_conf is not None else None
                except (TypeError, ValueError):
                    sense_conf = None

                frame_id = self._merge_frame(
                    doc_id, pred_idx_doc, pred_idx_doc, pred_text, pred_idx_doc,
                    pred_text,
                    sense=str(sense) if sense else None,
                    sense_conf=sense_conf,
                    framework="NOMBANK",
                )
                self._link_indices_to_node(
                    doc_id, [pred_idx_doc], "Frame", "id", frame_id,
                )

                tags = fr.get("tags") or []
                arg_spans = self._bio_to_spans(tags)
                for label, s_sent, e_sent in arg_spans:
                    s_doc = sent_offset + s_sent
                    e_doc = sent_offset + e_sent
                    span_text = " ".join(words[s_sent:e_sent + 1])
                    head_text = str(words[e_sent])  # rightmost token as fallback head
                    arg_id = self._merge_frame_argument(
                        doc_id, s_doc, e_doc, head_text, e_doc, label, span_text,
                    )
                    self._link_indices_to_node(
                        doc_id, list(range(s_doc, e_doc + 1)),
                        "FrameArgument", "id", arg_id,
                    )
                    self._link_argument_to_frame(arg_id, frame_id, label)
                logger.debug(
                    "process_nominal_srl: doc=%s pred=%s sense=%s args=%d",
                    doc_id, pred_text, sense, len(arg_spans),
                )