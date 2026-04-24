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

try:
    from nltk.corpus import wordnet as _wn  # type: ignore
except Exception:
    _wn = None

if __name__ == '__main__' and __package__ is None:
    repo_root = os.path.dirname(os.path.dirname(__file__))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

from textgraphx.config import get_config
from textgraphx.neo4j_client import make_graph_from_config
from textgraphx.reasoning.contracts import normalize_event_attr

logger = logging.getLogger(__name__)

_EVENTIVE_NOMINAL_ALLOWLIST = {
    "crisis",
    "tie",
    "ties",
    "sell-off",
    "selloff",
}

_NON_EVENTIVE_NOMINAL_DENYLIST = {
    "liquidity",
    "statement",
    "out",
    "times",
}

_EVENTIVE_NOUN_LEXNAMES = {"noun.event", "noun.act", "noun.process"}


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


def _iter_timex_elements(xml_text):
    if not xml_text or not xml_text.strip():
        return
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        logger.warning("TIMEX XML parsing failed: %s", exc)
        return

    for elem in root.iter():
        tag = elem.tag.split("}")[-1] if isinstance(elem.tag, str) else str(elem.tag)
        if str(tag).strip().upper() == "TIMEX3":
            yield elem


class TemporalPhase:
    """Materialize TIMEX, TEvent, DCT, and Signal graph nodes."""

    _TIMEX_MENTION_QUERY = """
        MERGE (t:TIMEX {tid: $tid, doc_id: toInteger($doc_id)})
        SET t.type = $type,
            t.value = $value,
            t.text = $text,
            t.start_char = toInteger($start_char),
            t.end_char = toInteger($end_char),
            t.start_index = toInteger($start_char),
            t.end_index = toInteger($end_char),
            t.origin = coalesce($origin, t.origin),
            t.functionInDocument = coalesce($function_in_document, t.functionInDocument),
            t.anchorTimeID = coalesce($anchor_time_id, t.anchorTimeID),
            t.beginPoint = coalesce($begin_point, t.beginPoint),
            t.endPoint = coalesce($end_point, t.endPoint)
        MERGE (tm:TimexMention {id: $mention_id, doc_id: toInteger($doc_id)})
        SET tm.tid = $tid,
            tm.type = $type,
            tm.value = $value,
            tm.text = $text,
            tm.start_char = toInteger($start_char),
            tm.end_char = toInteger($end_char),
            tm.start_index = toInteger($start_char),
            tm.end_index = toInteger($end_char),
            tm.origin = coalesce($origin, tm.origin),
            tm.functionInDocument = coalesce($function_in_document, tm.functionInDocument),
            tm.anchorTimeID = coalesce($anchor_time_id, tm.anchorTimeID),
            tm.beginPoint = coalesce($begin_point, tm.beginPoint),
            tm.endPoint = coalesce($end_point, tm.endPoint)
        MERGE (tm)-[:REFERS_TO]->(t)
        WITH t, tm
        MATCH (a:AnnotatedText {id: toInteger($doc_id)})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(ta:TagOccurrence)
        WHERE ta.index >= toInteger($start_char) AND ta.end_index <= toInteger($end_char)
        WITH t, tm, collect(ta) AS tas, min(ta.tok_index_doc) AS min_tok, max(ta.tok_index_doc) AS max_tok
        SET tm.start_tok = coalesce(min_tok, tm.start_tok),
            tm.end_tok = coalesce(max_tok, tm.end_tok),
            t.start_tok = coalesce(min_tok, t.start_tok),
            t.end_tok = coalesce(max_tok, t.end_tok)
        FOREACH (token IN tas | MERGE (token)-[:TRIGGERS]->(tm))
        RETURN t, tm
    """

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

    @staticmethod
    def _timex_mention_id(doc_id, tid):
        return f"timexmention_{doc_id}_{tid}"

    def _upsert_timex_with_mention(
        self,
        doc_id,
        *,
        tid,
        typ,
        value,
        text,
        start_char,
        end_char,
        function_in_document=None,
        anchor_time_id=None,
        begin_point=None,
        end_point=None,
        origin=None,
    ):
        self.graph.run(
            self._TIMEX_MENTION_QUERY,
            parameters={
                "doc_id": doc_id,
                "mention_id": self._timex_mention_id(doc_id, tid),
                "tid": tid,
                "type": typ,
                "value": value,
                "text": text,
                "start_char": int(start_char),
                "end_char": int(end_char),
                "function_in_document": function_in_document,
                "anchor_time_id": anchor_time_id,
                "begin_point": begin_point,
                "end_point": end_point,
                "origin": origin,
            },
        )

    def callHeidelTimeService(self, parameters):
        dct = parameters.get("dct")
        text = parameters.get("text")
        if not text:
            logger.warning("callHeidelTimeService: missing text payload")
            return ""

        payload = {"input": text}
        if dct:
            # HeidelTime requires YYYY-MM-DD; strip any time component
            payload["dct"] = str(dct).split("T")[0]
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
            t.start_char = toInteger(begin),
            t.end_char = toInteger(end),
            t.start_index = toInteger(begin),
            t.end_index = toInteger(end),
            t.origin = origin,
            t.type = typ,
            t.value = value,
            t.functionInDocument = coalesce(functionInDocument, t.functionInDocument),
            t.anchorTimeID = coalesce(anchorTimeID, t.anchorTimeID),
            t.beginPoint = coalesce(beginPoint, t.beginPoint),
            t.endPoint = coalesce(endPoint, t.endPoint)
        MERGE (tm:TimexMention {id: 'timexmention_' + toString($doc_id) + '_' + toString(tid), doc_id: toInteger($doc_id)})
        SET tm.tid = tid,
            tm.begin = toInteger(begin),
            tm.end = toInteger(end),
            tm.start_char = toInteger(begin),
            tm.end_char = toInteger(end),
            tm.start_index = toInteger(begin),
            tm.end_index = toInteger(end),
            tm.origin = origin,
            tm.type = typ,
            tm.value = value,
            tm.functionInDocument = coalesce(functionInDocument, tm.functionInDocument),
            tm.anchorTimeID = coalesce(anchorTimeID, tm.anchorTimeID),
            tm.beginPoint = coalesce(beginPoint, tm.beginPoint),
            tm.endPoint = coalesce(endPoint, tm.endPoint)
        MERGE (tm)-[:REFERS_TO]->(t)
        WITH t, tm
        MATCH (a:AnnotatedText {id: toInteger($doc_id)})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(ta:TagOccurrence)
        WHERE ta.index >= toInteger(tm.begin) AND ta.end_index <= toInteger(tm.end)
        WITH t, tm, collect(ta) AS tas, min(ta.tok_index_doc) AS min_tok, max(ta.tok_index_doc) AS max_tok
        SET tm.start_tok = coalesce(min_tok, tm.start_tok),
            tm.end_tok = coalesce(max_tok, tm.end_tok),
            t.start_tok = coalesce(min_tok, t.start_tok),
            t.end_tok = coalesce(max_tok, t.end_tok)
        FOREACH (token IN tas | MERGE (token)-[:TRIGGERS]->(tm))
        RETURN count(DISTINCT t) AS timex_count
        """
        rows = self.graph.run(
            query,
            parameters={"xml_path": f"{doc_id}.xml", "doc_id": doc_id},
        ).data()
        merged = int(rows[0].get("timex_count", 0) or 0) if rows else 0
        self._log_timex_diagnostics(doc_id, source="apoc", merged=merged)
        return ""

    def _materialize_timexes_from_heideltime(self, doc_id):
        """Project TIMEX3 nodes from HeidelTime service output onto the token graph."""
        result_xml = self.callHeidelTimeService(self.get_doc_text_and_dct(doc_id))
        parsed = 0
        for timex in _iter_timex_elements(result_xml or ""):
            begin = timex.attrib.get("begin") or timex.attrib.get("start_index")
            end = timex.attrib.get("end") or timex.attrib.get("end_index")
            if begin is None or end is None or not str(begin).isdigit() or not str(end).isdigit():
                continue
            parsed += 1
            self._upsert_timex_with_mention(
                doc_id,
                tid=timex.attrib.get("tid", ""),
                typ=timex.attrib.get("type", ""),
                value=timex.attrib.get("value", ""),
                text=(timex.text or "").strip(),
                start_char=int(begin),
                end_char=int(end),
                function_in_document=timex.attrib.get("functionInDocument"),
                anchor_time_id=timex.attrib.get("anchorTimeID"),
                begin_point=timex.attrib.get("beginPoint"),
                end_point=timex.attrib.get("endPoint"),
            )
        self._log_timex_diagnostics(doc_id, source="heideltime", parsed=parsed)
        return ""

    def materialize_timexes_fallback(self, doc_id):
        logger.debug("materialize_timexes_fallback %s", doc_id)
        apoc_ok = False
        try:
            self.materialize_timexes(doc_id)
            apoc_ok = True
        except Exception as exc:
            logger.warning(
                "materialize_timexes: APOC path failed for doc_id=%s (%s); using HeidelTime fallback",
                doc_id,
                exc,
            )

        if apoc_ok:
            # APOC ran without exception — check whether it actually materialised
            # any non-DCT TIMEX nodes. If not, the TTK XML was unavailable and we
            # need HeidelTime to fill the gap.
            try:
                rows = self.graph.run(
                    """
                    MATCH (t:TIMEX {doc_id: toInteger($doc_id)})
                    WHERE coalesce(t.functionInDocument, '') <> 'CREATION_TIME'
                    RETURN count(t) AS non_dct
                    """,
                    parameters={"doc_id": doc_id},
                ).data()
                non_dct = int((rows[0].get("non_dct") or 0)) if rows else 0
            except Exception:
                non_dct = 0

            if non_dct == 0:
                logger.info(
                    "APOC produced 0 non-DCT TIMEX nodes for doc_id=%s; using HeidelTime fallback",
                    doc_id,
                )
                return self._materialize_timexes_from_heideltime(doc_id)
            return ""

        return self._materialize_timexes_from_heideltime(doc_id)

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
        parsed = 0
        for timex in _iter_timex_elements(result_xml or ""):
            begin = timex.attrib.get("begin") or timex.attrib.get("start_index")
            end = timex.attrib.get("end") or timex.attrib.get("end_index")
            if begin is None or end is None or not str(begin).isdigit() or not str(end).isdigit():
                continue
            parsed += 1
            self._upsert_timex_with_mention(
                doc_id,
                tid=timex.attrib.get("tid", ""),
                typ=timex.attrib.get("type", ""),
                value=timex.attrib.get("value", ""),
                text=(timex.text or "").strip(),
                start_char=int(begin),
                end_char=int(end),
                function_in_document=timex.attrib.get("functionInDocument"),
                anchor_time_id=timex.attrib.get("anchorTimeID"),
                begin_point=timex.attrib.get("beginPoint"),
                end_point=timex.attrib.get("endPoint"),
            )
        self._log_timex_diagnostics(doc_id, source="python_fallback", parsed=parsed)
        return ""

    def _log_timex_diagnostics(self, doc_id, source, merged=None, parsed=None):
        """Log concise TIMEX materialization diagnostics per document."""
        try:
            rows = self.graph.run(
                """
                MATCH (t:TIMEX {doc_id: toInteger($doc_id)})
                OPTIONAL MATCH (tm:TimexMention {doc_id: toInteger($doc_id)})-[:REFERS_TO]->(t)
                OPTIONAL MATCH (tok:TagOccurrence)-[:TRIGGERS]->(tm)
                RETURN count(DISTINCT t) AS timex_nodes,
                       count(DISTINCT tm) AS timex_mentions,
                       count(DISTINCT CASE WHEN tok IS NOT NULL THEN tm END) AS mentions_with_tokens,
                       count(DISTINCT tok) AS trigger_tokens
                """,
                parameters={"doc_id": doc_id},
            ).data()
            stats = rows[0] if rows else {}
            logger.info(
                "TIMEX diagnostics doc=%s source=%s parsed=%s merged=%s timex_nodes=%s timex_mentions=%s mentions_with_tokens=%s trigger_tokens=%s",
                doc_id,
                source,
                parsed if parsed is not None else "n/a",
                merged if merged is not None else "n/a",
                stats.get("timex_nodes", 0),
                stats.get("timex_mentions", 0),
                stats.get("mentions_with_tokens", 0),
                stats.get("trigger_tokens", 0),
            )
        except Exception:
            logger.exception("Failed TIMEX diagnostics logging for doc_id=%s", doc_id)

    def reconcile_spacy_timex_candidates(self, doc_id):
        """Cross-validate SpaCy DATE/TIME candidates against HeidelTime TIMEX output.

        SpaCy DATE/TIME spans were stored as TimexMention:SpacyTimexCandidate nodes
        by EntityProcessor.  This method:
        - Marks candidates whose tokens overlap with a HeidelTime-sourced TimexMention
          as ``confirmed_by_heideltime=true``.
        - Marks remaining candidates (no HeidelTime overlap) as ``needs_review=true``
          so they can be audited or promoted with lower confidence.
        """
        logger.debug("reconcile_spacy_timex_candidates doc_id=%s", doc_id)
        # Confirm candidates that share at least one token with a HeidelTime mention.
        confirm_query = """
            MATCH (:AnnotatedText {id: toInteger($doc_id)})-[:CONTAINS_SENTENCE]->(:Sentence)
                  -[:HAS_TOKEN]->(tok:TagOccurrence)
            MATCH (tok)-[:IN_MENTION]->(tc:SpacyTimexCandidate)
            MATCH (tok)-[:TRIGGERS]->(hm:TimexMention)
            WHERE NOT hm:SpacyTimexCandidate
            WITH DISTINCT tc
            SET tc.confirmed_by_heideltime = true,
                tc.confidence = 0.85
            RETURN count(tc) AS confirmed
        """
        rows = self.graph.run(confirm_query, parameters={"doc_id": doc_id}).data()
        confirmed = int((rows[0].get("confirmed") or 0)) if rows else 0

        # Mark unconfirmed candidates as needing review.
        review_query = """
            MATCH (:AnnotatedText {id: toInteger($doc_id)})-[:CONTAINS_SENTENCE]->(:Sentence)
                  -[:HAS_TOKEN]->(tok:TagOccurrence)
            MATCH (tok)-[:IN_MENTION]->(tc:SpacyTimexCandidate)
            WHERE coalesce(tc.confirmed_by_heideltime, false) = false
            WITH DISTINCT tc
            SET tc.needs_review = true
            RETURN count(tc) AS unconfirmed
        """
        rows2 = self.graph.run(review_query, parameters={"doc_id": doc_id}).data()
        unconfirmed = int((rows2[0].get("unconfirmed") or 0)) if rows2 else 0

        logger.info(
            "reconcile_spacy_timex_candidates doc=%s confirmed=%d needs_review=%d",
            doc_id, confirmed, unconfirmed,
        )

    @staticmethod
    def _is_eventive_nominal(form):
        token = (form or "").strip().lower()
        if not token:
            return False
        if token in _EVENTIVE_NOMINAL_ALLOWLIST:
            return True
        if token in _NON_EVENTIVE_NOMINAL_DENYLIST:
            return False
        if "-" in token and token.endswith("off"):
            return True

        if _wn is None:
            # If lexical resources are unavailable, avoid aggressive filtering.
            return True

        synsets = _wn.synsets(token, pos=_wn.NOUN)
        if not synsets:
            return False
        lexnames = {s.lexname() for s in synsets}
        return bool(lexnames & _EVENTIVE_NOUN_LEXNAMES)

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
        auxiliary_verbs = {
            "be", "am", "is", "are", "was", "were", "been", "being",
            "do", "does", "did", "done",
            "have", "has", "had",
            "will", "would", "shall", "should", "may", "might", "must", "can", "could",
        }
        for event in _iter_event_elements(result_xml):
            begin = event.attrib.get("begin")
            end = event.attrib.get("end")
            if begin is None or end is None or not str(begin).isdigit() or not str(end).isdigit():
                continue

            raw_pos = (event.attrib.get("pos") or "").strip().upper()
            form_lc = (event.attrib.get("form") or "").strip().lower()

            # Drop adjective predicates and bare auxiliaries to reduce event-layer over-generation.
            if raw_pos in {"JJ", "JJR", "JJS"}:
                continue
            if raw_pos.startswith("VB") and form_lc in auxiliary_verbs:
                continue
            if raw_pos in {"NN", "NNS"} and not self._is_eventive_nominal(form_lc):
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
                    "polarity": normalize_event_attr("polarity", event.attrib.get("polarity") or "POS") or "POS",
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
            SET event.eid = coalesce(event.eid, fallback_eiid),
                event.begin = coalesce(event.begin, toInteger(f.start_char), toInteger(f.startIndex)),
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
        phase.reconcile_spacy_timex_candidates(doc_id)
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
