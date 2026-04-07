"""Legacy TemporalPhase compatibility helpers.

These functions preserve older runtime contracts without reassigning ownership
of relation-generation behavior to TemporalPhase source code.

.. deprecated::
    All helpers in this module are scheduled for removal in v2.0.0.
    Migrate callers to the canonical equivalents documented in DEPRECATION.md.
"""

from __future__ import annotations

import warnings
import xml.etree.ElementTree as ET

_DEPRECATION_NOTICE = (
    "The legacy TemporalPhase method '{name}' is deprecated and will be removed "
    "in v2.0.0. {replacement}. See DEPRECATION.md for migration guidance."
)

_REPLACEMENTS = {
    "create_tlinks_e2e":    "Use TlinksRecognizer.create_tlinks_e2e() instead",
    "create_tlinks_e2t":    "Use TlinksRecognizer.create_tlinks_e2t() instead",
    "create_event_mentions2": "Use EventEnrichmentPhase.create_event_mentions() instead",
}


def _iter_relation_elements(xml_text):
    if not xml_text or not xml_text.strip():
        return
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return

    for elem in root.iter():
        tag = elem.tag.split("}")[-1] if isinstance(elem.tag, str) else elem.tag
        if tag == "TLINK":
            yield elem


def legacy_event_to_event_links(phase, doc_id):
    warnings.warn(
        _DEPRECATION_NOTICE.format(
            name="create_tlinks_e2e",
            replacement=_REPLACEMENTS["create_tlinks_e2e"],
        ),
        DeprecationWarning,
        stacklevel=3,
    )
    result_xml = phase._get_ttk_xml(doc_id)
    query = """
        MERGE (e1:TEvent {eiid: $event_instance_id, doc_id: toInteger($doc_id)})
        MERGE (e2:TEvent {eiid: $related_event_instance, doc_id: toInteger($doc_id)})
        MERGE (e1)-[tl:TLINK {id: $lid, relType: $rel_type}]->(e2)
        SET tl.signalID = $signal_id
    """

    for tlink in _iter_relation_elements(result_xml):
        event_instance_id = tlink.attrib.get("eventInstanceID")
        related_event_instance = tlink.attrib.get("relatedToEventInstance")
        if not event_instance_id or not related_event_instance:
            continue
        phase.graph.run(
            query,
            parameters={
                "event_instance_id": event_instance_id,
                "related_event_instance": related_event_instance,
                "lid": tlink.attrib.get("lid", ""),
                "rel_type": tlink.attrib.get("relType", ""),
                "signal_id": tlink.attrib.get("signalID"),
                "doc_id": doc_id,
            },
        )
    return ""


def legacy_event_to_time_links(phase, doc_id):
    warnings.warn(
        _DEPRECATION_NOTICE.format(
            name="create_tlinks_e2t",
            replacement=_REPLACEMENTS["create_tlinks_e2t"],
        ),
        DeprecationWarning,
        stacklevel=3,
    )
    result_xml = phase._get_ttk_xml(doc_id)
    query = """
        MERGE (e:TEvent {eiid: $event_instance_id, doc_id: toInteger($doc_id)})
        MERGE (t:TIMEX {tid: $related_to_time, doc_id: toInteger($doc_id)})
        MERGE (e)-[tl:TLINK {id: $lid, relType: $rel_type}]->(t)
        SET tl.signalID = $signal_id
    """

    for tlink in _iter_relation_elements(result_xml):
        event_instance_id = tlink.attrib.get("eventInstanceID")
        related_to_time = tlink.attrib.get("relatedToTime")
        if not event_instance_id or not related_to_time:
            continue
        phase.graph.run(
            query,
            parameters={
                "event_instance_id": event_instance_id,
                "related_to_time": related_to_time,
                "lid": tlink.attrib.get("lid", ""),
                "rel_type": tlink.attrib.get("relType", ""),
                "signal_id": tlink.attrib.get("signalID"),
                "doc_id": doc_id,
            },
        )
    return ""


def legacy_event_mentions(phase, doc_id):
    warnings.warn(
        _DEPRECATION_NOTICE.format(
            name="create_event_mentions2",
            replacement=_REPLACEMENTS["create_event_mentions2"],
        ),
        DeprecationWarning,
        stacklevel=3,
    )
    query = """
    MATCH (a:AnnotatedText {id: toInteger($doc_id)})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(tok:TagOccurrence)-[:TRIGGERS]->(event:TEvent)
    WITH event, head(collect(tok)) AS trig_tok
    OPTIONAL MATCH (trig_tok)-[:HAS_NEXT]->(next_tok:TagOccurrence)
    WITH event, trig_tok, next_tok,
         toLower(trim(toString(coalesce(trig_tok.lemma, trig_tok.text, '')))) AS trigger_lemma
    WITH event, trig_tok, next_tok,
         CASE
             WHEN trig_tok.pos STARTS WITH 'VB' AND next_tok.pos = 'RP'
             THEN trigger_lemma + ' ' + toLower(trim(toString(next_tok.lemma)))
             ELSE trigger_lemma
         END AS trigger_lemma
    MERGE (em:EventMention {id: event.eiid, doc_id: toInteger($doc_id)})
    SET em.start_tok = event.start_tok,
        em.end_tok = CASE
            WHEN trig_tok.pos STARTS WITH 'VB' AND next_tok.pos = 'RP' THEN coalesce(next_tok.tok_index_doc, event.end_tok)
            ELSE event.end_tok
        END,
        em.lemma = trigger_lemma
    MERGE (em)-[:REFERS_TO]->(event)
    RETURN count(em) AS mentions_created
    """
    phase.graph.run(query, parameters={"doc_id": doc_id}).data()
    return ""


LEGACY_METHODS = {
    "create_tlinks_e2e": legacy_event_to_event_links,
    "create_tlinks_e2t": legacy_event_to_time_links,
    "create_event_mentions2": legacy_event_mentions,
}
