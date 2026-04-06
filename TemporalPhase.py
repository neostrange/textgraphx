"""Temporal extraction phase.

This module materializes temporal expressions, temporal events, document
creation-time anchors, and temporal signal spans in Neo4j. Relation linking is
delegated to TlinksRecognizer so this phase stays focused on extraction and
node materialization.
"""

import logging
import os
import sys
import warnings
import xml.etree.ElementTree as ET

import requests

if __name__ == '__main__' and __package__ is None:
    repo_root = os.path.dirname(os.path.dirname(__file__))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

from textgraphx.config import get_config
from textgraphx.neo4j_client import make_graph_from_config
from textgraphx.reasoning_contracts import normalize_event_attr

logger = logging.getLogger(__name__)


def _iter_signal_elements(xml_text):
    if not xml_text or not xml_text.strip():
        return
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        logger.warning("Signal XML parsing failed: %s", exc)
        return

    for elem in root.iter():
        if elem.tag.endswith("SIGNAL") or elem.tag.endswith("Signal"):
            yield elem


def _iter_event_elements(xml_text):
    if not xml_text or not xml_text.strip():
        return
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        logger.warning("Event XML parsing failed: %s", exc)
        return

    for elem in root.iter():
        if elem.tag.endswith("EVENT"):
            yield elem


def _iter_relation_elements(xml_text, relation_name):
    if not xml_text or not xml_text.strip():
        return
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        logger.warning("Relation XML parsing failed: %s", exc)
        return

    relation_name = str(relation_name or "").strip().upper()
    for elem in root.iter():
        tag = elem.tag.split("}")[-1] if isinstance(elem.tag, str) else str(elem.tag)
        if str(tag).strip().upper() == relation_name:
            yield elem


class TemporalPhase:
    """Materialize TIMEX, TEvent, DCT, and Signal graph nodes."""

    def __init__(self, argv):
        del argv
        self.graph = make_graph_from_config()
        cfg = get_config()
        services = getattr(cfg, "services", None)
        self.temporal_url = getattr(services, "temporal_url", None)
        if not self.temporal_url and hasattr(cfg, "get"):
            self.temporal_url = cfg.get("temporal_service_url", "http://localhost:8080/ttk")
        if not self.temporal_url:
            self.temporal_url = "http://localhost:8080/ttk"

        self.heideltime_url = getattr(services, "heideltime_url", None)
        if not self.heideltime_url:
            self.heideltime_url = "http://localhost:5000/annotate"

    def __getattr__(self, name):
        from textgraphx.temporal_legacy_compat import LEGACY_METHODS

        legacy_impl = LEGACY_METHODS.get(name)
        if legacy_impl is not None:
            return lambda doc_id: legacy_impl(self, doc_id)
        raise AttributeError(name)

    def get_annotated_text(self):
        query = "MATCH (a:AnnotatedText) RETURN a.id AS doc_id ORDER BY a.id"
        rows = self.graph.run(query).data()
        return [row["doc_id"] for row in rows if row.get("doc_id") is not None]

    def get_doc_text_and_dct(self, doc_id):
        query = """
        MATCH (a:AnnotatedText {id: toInteger($doc_id)})
        RETURN a.text AS text,
               coalesce(a.dct, a.creationtime, a.documentCreationTime) AS dct
        """
        rows = self.graph.run(query, parameters={"doc_id": doc_id}).data()
        if not rows:
            return {"text": "", "dct": ""}
        row = rows[0]
        return {"text": row.get("text") or "", "dct": row.get("dct") or ""}

    def callTtkService(self, parameters):
        dct = parameters.get("dct")
        text = parameters.get("text")
        if not dct or not text:
            logger.warning("callTtkService: missing dct/text payload")
            return ""

        normalized_dct = str(dct).split("T")[0].replace("-", "")
        data = {"input": text, "dct": normalized_dct}
        headers = {"Content-type": "application/json", "Accept": "text/plain"}

        try:
            response = requests.post(self.temporal_url, json=data, headers=headers, timeout=20)
            response.raise_for_status()
            return response.text
        except requests.RequestException as exc:
            logger.warning("callTtkService failed: %s", exc)
            return ""

    def _get_ttk_xml(self, doc_id):
        return self.callTtkService(self.get_doc_text_and_dct(doc_id))

    def create_DCT_node(self, doc_id):
        logger.debug("create_DCT_node %s", doc_id)
        query = """
        MATCH (a:AnnotatedText {id: toInteger($doc_id)})
        WITH a, coalesce(a.dct, a.creationtime, a.documentCreationTime) AS dct_value
        WHERE dct_value IS NOT NULL AND trim(toString(dct_value)) <> ''
        MERGE (DCT:TIMEX {doc_id: toInteger($doc_id), tid: 't0'})
        SET DCT.type = 'DATE',
            DCT.value = toString(dct_value),
            DCT.functionInDocument = 'CREATION_TIME',
            DCT.origin = 'annotated_text'
        MERGE (a)-[:CREATED_ON]->(DCT)
        RETURN count(DCT) AS created
        """
        self.graph.run(query, parameters={"doc_id": doc_id}).data()
        return ""

    def callHeidelTimeService(self, parameters):
        dct = parameters.get("dct")
        text = parameters.get("text")
        if not text:
            logger.warning("callHeidelTimeService: missing text payload")
            return ""

        payload = {"input": text}
        if dct:
            payload["dct"] = str(dct)
        headers = {"Content-type": "application/json", "Accept": "text/plain"}

        try:
            response = requests.post(self.heideltime_url, json=payload, headers=headers, timeout=20)
            response.raise_for_status()
            return response.text
        except requests.RequestException as exc:
            logger.warning("callHeidelTimeService failed: %s", exc)
            return ""

    def materialize_timexes(self, doc_id):
        logger.debug("materialize_timexes %s", doc_id)
        query = """
        CALL apoc.load.xml($xml_path)
        YIELD value AS result
        UNWIND [item IN result._children WHERE item._type = 'tarsqi_tags'] AS tarsqi
        UNWIND [item IN tarsqi._children WHERE item._type = 'TIMEX3'] AS timex
        WITH timex.begin AS begin,
             timex.end AS end,
             timex.origin AS origin,
             timex.tid AS tid,
             timex.type AS typ,
             timex.value AS value,
             timex.functionInDocument AS functionInDocument,
             timex.anchorTimeID AS anchorTimeID,
             timex.beginPoint AS beginPoint,
             timex.endPoint AS endPoint
        MERGE (t:TIMEX {tid: tid, doc_id: toInteger($doc_id)})
        SET t.begin = toInteger(begin),
            t.end = toInteger(end),
            t.origin = origin,
            t.type = typ,
            t.value = value,
            t.functionInDocument = coalesce(functionInDocument, t.functionInDocument),
            t.anchorTimeID = coalesce(anchorTimeID, t.anchorTimeID),
            t.beginPoint = coalesce(beginPoint, t.beginPoint),
            t.endPoint = coalesce(endPoint, t.endPoint)
        WITH t
        MATCH (a:AnnotatedText {id: toInteger($doc_id)})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(ta:TagOccurrence)
        WHERE ta.index >= toInteger(t.begin) AND ta.end_index <= toInteger(t.end)
        MERGE (ta)-[:TRIGGERS]->(t)
        RETURN count(DISTINCT t) AS timex_count
        """
        self.graph.run(
            query,
            parameters={"xml_path": f"{doc_id}.xml", "doc_id": doc_id},
        ).data()
        return ""

    def materialize_timexes_fallback(self, doc_id):
        logger.debug("materialize_timexes_fallback %s", doc_id)
        return self.materialize_timexes(doc_id)

    # Backward-compatible API used by existing runtime tests.
    def create_timexes2(self, doc_id):
        warnings.warn(
            "TemporalPhase.create_timexes2() is deprecated and will be removed in v2.0.0. "
            "Use TemporalPhase.materialize_timexes() instead. See DEPRECATION.md.",
            DeprecationWarning,
            stacklevel=2,
        )
        logger.debug("create_timexes2 %s", doc_id)
        result_xml = self.callHeidelTimeService(self.get_doc_text_and_dct(doc_id))
        query = """
        MERGE (t:TIMEX {tid: $tid, doc_id: toInteger($doc_id)})
        SET t.type = $type,
            t.value = $value,
            t.text = $text,
            t.start_char = toInteger($start_char),
            t.end_char = toInteger($end_char),
            t.start_tok = toInteger($start_tok),
            t.end_tok = toInteger($end_tok),
            t.start_index = toInteger($start_char),
            t.end_index = toInteger($end_char),
            t.functionInDocument = coalesce($function_in_document, t.functionInDocument),
            t.anchorTimeID = coalesce($anchor_time_id, t.anchorTimeID),
            t.beginPoint = coalesce($begin_point, t.beginPoint),
            t.endPoint = coalesce($end_point, t.endPoint)
        WITH t
        MATCH (a:AnnotatedText {id: toInteger($doc_id)})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(ta:TagOccurrence)
        WHERE ta.index >= toInteger(t.start_char) AND ta.end_index <= toInteger(t.end_char)
        FOREACH (token IN collect(ta) | MERGE (token)-[:TRIGGERS]->(t))
        """

        for timex in _iter_event_elements(result_xml or ""):
            # _iter_event_elements does not emit TIMEX entries; keep loop here for defensive compatibility.
            del timex

        if result_xml and result_xml.strip():
            try:
                root = ET.fromstring(result_xml)
            except ET.ParseError:
                logger.warning("TIMEX XML parsing failed in create_timexes2")
                return ""

            for elem in root.iter():
                tag = elem.tag.split("}")[-1] if isinstance(elem.tag, str) else elem.tag
                if tag != "TIMEX3":
                    continue
                begin = elem.attrib.get("begin")
                end = elem.attrib.get("end")
                if begin is None or end is None or not str(begin).isdigit() or not str(end).isdigit():
                    continue
                self.graph.run(
                    query,
                    parameters={
                        "doc_id": doc_id,
                        "tid": elem.attrib.get("tid", ""),
                        "type": elem.attrib.get("type", ""),
                        "value": elem.attrib.get("value", ""),
                        "text": (elem.text or "").strip(),
                        "start_char": int(begin),
                        "end_char": int(end),
                        "start_tok": int(begin),
                        "end_tok": int(end),
                        "function_in_document": elem.attrib.get("functionInDocument"),
                        "anchor_time_id": elem.attrib.get("anchorTimeID"),
                        "begin_point": elem.attrib.get("beginPoint"),
                        "end_point": elem.attrib.get("endPoint"),
                    },
                )
        return ""

    def materialize_signals(self, doc_id):
        logger.debug("materialize_signals %s", doc_id)
        result_xml = self._get_ttk_xml(doc_id)
        query = """
        MERGE (s:Signal {id: $sid, doc_id: toInteger($doc_id)})
        SET s.type = 'SIGNAL',
            s.text = $text,
            s.start_char = toInteger($start_char),
            s.end_char = toInteger($end_char)
        WITH s
        MATCH (a:AnnotatedText {id: toInteger($doc_id)})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(ta:TagOccurrence)
        WHERE ta.index >= toInteger(s.start_char) AND ta.end_index <= toInteger(s.end_char)
        WITH s, collect(ta) AS tas, min(ta.tok_index_doc) AS min_tok, max(ta.tok_index_doc) AS max_tok
        SET s.start_tok = min_tok,
            s.end_tok = max_tok
        FOREACH (token IN tas | MERGE (token)-[:TRIGGERS]->(s))
        """

        created = 0
        for signal in _iter_signal_elements(result_xml):
            begin = signal.attrib.get("begin") or signal.attrib.get("start_index")
            end = signal.attrib.get("end") or signal.attrib.get("end_index")
            if begin is None or end is None or not str(begin).isdigit() or not str(end).isdigit():
                continue
            sid = signal.attrib.get("sid") or f"sig_{doc_id}_{begin}_{end}"
            self.graph.run(
                query,
                parameters={
                    "doc_id": doc_id,
                    "sid": sid,
                    "text": (signal.text or "").strip() or signal.attrib.get("text") or "",
                    "start_char": int(begin),
                    "end_char": int(end),
                },
            )
            created += 1

        logger.info("materialize_signals: merged %d Signal nodes", created)
        return ""

    # Backward-compatible API used by existing runtime tests.
    def create_signals2(self, doc_id):
        warnings.warn(
            "TemporalPhase.create_signals2() is deprecated and will be removed in v2.0.0. "
            "Use TemporalPhase.materialize_signals() instead. See DEPRECATION.md.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.materialize_signals(doc_id)

    def materialize_tevents(self, doc_id):
        logger.debug("materialize_tevents %s", doc_id)
        result_xml = self._get_ttk_xml(doc_id)
        query = """
        MERGE (event:TEvent {eiid: $eiid, doc_id: toInteger($doc_id)})
        SET event.begin = toInteger($begin),
            event.end = toInteger($end),
            event.start_char = toInteger($begin),
            event.end_char = toInteger($end),
            event.start_index = toInteger($begin),
            event.end_index = toInteger($end),
            event.class = $class,
            event.eid = $eid,
            event.epos = $epos,
            event.form = $form,
            event.modality = $modality,
            event.polarity = $polarity,
            event.pos = $pos,
            event.pred = $pred,
            event.tense = $tense,
            event.aspect = $aspect,
            event.external_ref = coalesce($external_ref, event.external_ref)
        WITH event
        MATCH (a:AnnotatedText {id: toInteger($doc_id)})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(ta:TagOccurrence)
        WHERE ta.index >= toInteger(event.begin) AND ta.end_index <= toInteger(event.end)
        WITH event, collect(DISTINCT ta) AS tas, min(ta.tok_index_doc) AS min_tok, max(ta.tok_index_doc) AS max_tok
        SET event.start_tok = min_tok,
            event.end_tok = max_tok
        FOREACH (token IN tas | MERGE (token)-[:TRIGGERS]->(event))
        """

        created = 0
        for event in _iter_event_elements(result_xml):
            begin = event.attrib.get("begin")
            end = event.attrib.get("end")
            if begin is None or end is None or not str(begin).isdigit() or not str(end).isdigit():
                continue
            eid = event.attrib.get("eid") or "unknown"
            eiid = event.attrib.get("eiid") or f"e_{eid}_{begin}"
            self.graph.run(
                query,
                parameters={
                    "doc_id": doc_id,
                    "eiid": eiid,
                    "begin": int(begin),
                    "end": int(end),
                    "aspect": normalize_event_attr("aspect", event.attrib.get("aspect")),
                    "class": event.attrib.get("class"),
                    "eid": eid,
                    "epos": event.attrib.get("epos"),
                    "form": event.attrib.get("form"),
                    "modality": event.attrib.get("modality"),
                    "polarity": normalize_event_attr("polarity", event.attrib.get("polarity")),
                    "pos": event.attrib.get("pos"),
                    "pred": event.attrib.get("form"),
                    "tense": normalize_event_attr("tense", event.attrib.get("tense")),
                    "external_ref": event.attrib.get("external_ref")
                        or event.attrib.get("externalRef")
                        or event.attrib.get("ext_ref")
                        or event.attrib.get("eid"),
                },
            )
            created += 1

        if created == 0:
            fallback_query = """
            MATCH (a:AnnotatedText {id: toInteger($doc_id)})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(:TagOccurrence)-[:PARTICIPATES_IN]->(f:Frame)
            WITH DISTINCT f
            WHERE f.start_tok IS NOT NULL AND f.end_tok IS NOT NULL
            WITH f, 'frame_' + toString(toInteger($doc_id)) + '_' + toString(f.start_tok) + '_' + toString(f.end_tok) AS fallback_eiid
            MERGE (event:TEvent {doc_id: toInteger($doc_id), eiid: fallback_eiid})
            SET event.begin = coalesce(event.begin, toInteger(f.start_char), toInteger(f.startIndex)),
                event.end = coalesce(event.end, toInteger(f.end_char), toInteger(f.endIndex)),
                event.start_char = coalesce(event.start_char, toInteger(f.start_char), toInteger(f.startIndex)),
                event.end_char = coalesce(event.end_char, toInteger(f.end_char), toInteger(f.endIndex)),
                event.start_tok = coalesce(event.start_tok, f.start_tok),
                event.end_tok = coalesce(event.end_tok, f.end_tok),
                event.form = coalesce(event.form, f.text),
                event.pred = coalesce(event.pred, f.headword),
                event.pos = coalesce(event.pos, 'VERB'),
                event.tense = coalesce(event.tense, ''),
                event.aspect = coalesce(event.aspect, ''),
                event.polarity = coalesce(event.polarity, ''),
                event.modality = coalesce(event.modality, ''),
                event.external_ref = coalesce(event.external_ref, f.id)
            WITH event, f
            MATCH (a:AnnotatedText {id: toInteger($doc_id)})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(ta:TagOccurrence)-[:PARTICIPATES_IN]->(f)
            MERGE (ta)-[:TRIGGERS]->(event)
            RETURN count(DISTINCT event) AS tevent_count
            """
            rows = self.graph.run(fallback_query, parameters={"doc_id": doc_id}).data()
            fallback_count = rows[0].get("tevent_count", 0) if rows else 0
            logger.info("materialize_tevents: fallback merged %d TEvent nodes", fallback_count)
        else:
            logger.info("materialize_tevents: merged %d TEvent nodes", created)

        return ""

    def materialize_glinks(self, doc_id):
        """Materialize GLINK relations between existing TEvent nodes.

        This is additive and only links already materialized events; it does
        not create temporal/event nodes.
        """
        logger.debug("materialize_glinks %s", doc_id)
        result_xml = self._get_ttk_xml(doc_id)
        query = """
        MATCH (source:TEvent {doc_id: toInteger($doc_id), eiid: $source_eiid})
        MATCH (target:TEvent {doc_id: toInteger($doc_id), eiid: $target_eiid})
        MERGE (source)-[gl:GLINK {id: $gid}]->(target)
        SET gl.relType = $rel_type,
            gl.signalID = coalesce($signal_id, gl.signalID),
            gl.origin = coalesce($origin, gl.origin),
            gl.rule = coalesce($rule, gl.rule)
        RETURN count(gl) AS glinks_merged
        """

        created = 0
        for glink in _iter_relation_elements(result_xml, "GLINK"):
            source = glink.attrib.get("eventInstanceID") or glink.attrib.get("sourceEventInstance")
            target = glink.attrib.get("relatedToEventInstance") or glink.attrib.get("targetEventInstance")
            if not source or not target:
                continue
            gid = glink.attrib.get("lid") or f"glink_{doc_id}_{source}_{target}"
            rows = self.graph.run(
                query,
                parameters={
                    "doc_id": doc_id,
                    "gid": gid,
                    "source_eiid": source,
                    "target_eiid": target,
                    "rel_type": glink.attrib.get("relType", "") or "",
                    "signal_id": glink.attrib.get("signalID"),
                    "origin": glink.attrib.get("origin"),
                    "rule": glink.attrib.get("rule"),
                },
            ).data()
            created += int(rows[0].get("glinks_merged", 0) or 0) if rows else 0

        logger.info("materialize_glinks: merged %d GLINK relationships", created)
        return ""

    # Backward-compatible API used by existing runtime tests.
    def create_tevents2(self, doc_id):
        warnings.warn(
            "TemporalPhase.create_tevents2() is deprecated and will be removed in v2.0.0. "
            "Use TemporalPhase.materialize_tevents() instead. See DEPRECATION.md.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.materialize_tevents(doc_id)

if __name__ == '__main__':
    import time as _time

    phase = TemporalPhase(sys.argv[1:])
    doc_ids = phase.get_annotated_text()
    start = _time.time()

    for doc_id in doc_ids:
        phase.create_DCT_node(doc_id)
        phase.materialize_tevents(doc_id)
        phase.materialize_signals(doc_id)
        phase.materialize_timexes_fallback(doc_id)
        phase.materialize_glinks(doc_id)

    duration = _time.time() - start
    try:
        from textgraphx.phase_assertions import record_phase_run

        record_phase_run(
            phase.graph,
            phase_name="temporal",
            duration_seconds=duration,
            documents_processed=len(doc_ids),
            metadata={"passes": "create_DCT_node,materialize_tevents,materialize_signals,materialize_timexes_fallback,materialize_glinks"},
        )
    except Exception:
        logger.exception("Failed to write TemporalRun marker (non-fatal)")
