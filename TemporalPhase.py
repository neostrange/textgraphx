"""TemporalPhase

Responsible for creating temporal expressions (TIMEX) and temporal events
(`TEvent`) in the graph and for wiring TLINK relationships. This module
integrates with external tools (Heideltime/TTK/TARSQI) and expects
document-level XML outputs to be available for parsing.

Important notes:
- The phase relies on `AnnotatedText` and `TagOccurrence` nodes produced by
    upstream tokenization and import phases.
- It uses deterministic ids (e.g., `tid`, `eiid`) and MERGE patterns so runs
    are safe to re-run, but external service availability affects what gets
    created.
"""

import os
import spacy
import sys

if __name__ == '__main__' and __package__ is None:
        repo_root = os.path.dirname(os.path.dirname(__file__))
        if repo_root not in sys.path:
                sys.path.insert(0, repo_root)



from spacy.tokens import Doc, Token, Span
from textgraphx.util.GraphDbBase import GraphDBBase
import xml.etree.ElementTree as ET
# legacy py2neo imports removed; use bolt-driver wrapper via neo4j_client
import requests
import json
import logging

from textgraphx.neo4j_client import make_graph_from_config
from textgraphx.config import get_config

logger = logging.getLogger(__name__)


def _iter_tlink_elements(xml_text):
    """Yield TLINK elements from TTK XML without relying on APOC file import."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        logger.exception("Failed to parse TTK XML for TLINK extraction")
        return

    for elem in root.iter():
        tag = elem.tag.split("}")[-1] if isinstance(elem.tag, str) else elem.tag
        if tag == "TLINK":
            yield elem


def _iter_timex_elements(xml_text):
    """Yield TIMEX3 elements from temporal XML payloads.

    The temporal service may return namespaced XML or fragment-like payloads.
    We try direct parsing first, then a wrapped-root fallback.
    """
    if not xml_text:
        return

    root = None
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        try:
            root = ET.fromstring(f"<root>{xml_text}</root>")
        except ET.ParseError:
            logger.exception("Failed to parse temporal XML for TIMEX extraction")
            return

    for elem in root.iter():
        tag = elem.tag.split("}")[-1] if isinstance(elem.tag, str) else elem.tag
        if tag == "TIMEX3":
            yield elem


# call TTK service which uses TARSQI toolkit and 
# call Heideltime service for temporal expression detection and normalization
# It also stores the DCT i.e., document creation time.
# ORDER of EXECUTION: after refinement phase

class TemporalPhase():

    uri=""
    username =""
    password =""
    graph=""

    def __init__(self, argv):
        # Initialize a shared py2neo Graph from config
        self.graph = make_graph_from_config()
        # keep legacy attrs for compatibility
        self.uri = None
        self.username = None
        self.password = None
        cfg = get_config()
        self.temporal_url = cfg.services.temporal_url
        self.heideltime_url = cfg.services.heideltime_url
        #self.__text_processor = TextProcessor(self.nlp, self._driver)
        #self.create_constraints()
    logger.info("TemporalPhase initialized; graph session ready")

        

    
    def get_annotated_text(self):

        logger.debug("get_annotated_text")
        graph = self.graph

        query = "MATCH (n:AnnotatedText) RETURN n.id"
        data= graph.run(query).data()

        annotatedd_text_docs= list()

        listDocIDs=[]
        for record in data:
            #print(record)
            #print(record.get("n.text"))
            #t = (record.get("n.text"), {'text_id': record.get("n.id")})
            id = record.get('n.id')
            #text = record.get('n.text')
            listDocIDs.append(id)
        
        return listDocIDs


        #CASE 1 - to create a DCT node for a document*******
        #-- this query should be executed in the beginning of the temporal phase. 
        #-- precondition: the annotatedText should be there.
    def create_DCT_node(self, doc_id):
        logger.debug("create_DCT_node %s", doc_id)
        graph = self.graph

        query = """MATCH (ann:AnnotatedText WHERE ann.id = $doc_id)
                    MERGE (DCT:TIMEX {type: 'DATE', value: replace(split(ann.creationtime, 'T')[0],'-','') , tid: 'dct'+ toString(ann.id),
                    doc_id: ann.id})<-[:CREATED_ON]-(ann)
                    SET DCT.functionInDocument = 'CREATION_TIME'
                """

        data = graph.run(query, parameters={'doc_id': doc_id}).data()
        
        return ""


    def create_tlinks_e2e(self, doc_id):
        logger.debug("create_tlinks_e2e %s", doc_id)
        graph = self.graph
        result_xml = self._get_ttk_xml(doc_id)

        query = """
            MERGE (e1:TEvent {eiid: $event_instance_id, doc_id: toInteger($doc_id)})
            MERGE (e2:TEvent {eiid: $related_event_instance, doc_id: toInteger($doc_id)})
            MERGE (e1)-[tl:TLINK {id: $lid, relType: $rel_type}]->(e2)
            SET tl.signalID = $signal_id
        """

        merged = 0
        for tlink in _iter_tlink_elements(result_xml):
            event_instance_id = tlink.attrib.get("eventInstanceID")
            related_event_instance = tlink.attrib.get("relatedToEventInstance")
            if not event_instance_id or not related_event_instance:
                continue

            graph.run(
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
            merged += 1

        logger.info("create_tlinks_e2e: merged %d event-to-event TLINKs", merged)
        return ""


    def create_tlinks_e2t(self, doc_id):
        logger.debug("create_tlinks_e2t %s", doc_id)
        graph = self.graph
        result_xml = self._get_ttk_xml(doc_id)

        query = """
            MERGE (e:TEvent {eiid: $event_instance_id, doc_id: toInteger($doc_id)})
            MERGE (t:TIMEX {tid: $related_to_time, doc_id: toInteger($doc_id)})
            MERGE (e)-[tl:TLINK {id: $lid, relType: $rel_type}]->(t)
            SET tl.signalID = $signal_id
        """

        merged = 0
        for tlink in _iter_tlink_elements(result_xml):
            event_instance_id = tlink.attrib.get("eventInstanceID")
            related_to_time = tlink.attrib.get("relatedToTime")
            if not event_instance_id or not related_to_time:
                continue

            graph.run(
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
            merged += 1

        logger.info("create_tlinks_e2t: merged %d event-to-time TLINKs", merged)
        return ""

        

    def create_tlinks_t2t(self, doc_id):
        logger.debug("create_tlinks_t2t %s", doc_id)
        graph = self.graph

        query = """CALL apoc.load.xml($xml_path)
                    YIELD value as result
                    UNWIND [item in result._children where item._type ="tarsqi_tags"] AS tarsqi
                    UNWIND [item in tarsqi._children where item._type ="TLINK"] AS tlink
                    WITH tlink.lid as lid, tlink.origin as origin, tlink.relType as relType, tlink.relatedToTime as relatedToTime, tlink.timeID as timeID, tlink.eventInstanceID as eventInstanceID, tlink.relatedToEventInstance as relatedToEventInstance, tlink.syntax as syntax, tlink.signalID as signalID
                    foreach(ignoreMe IN CASE WHEN relatedToTime IS NOT NULL and timeID IS NOT NULL THEN [1] ELSE [] END | merge (t1:TIMEX{tid:timeID, doc_id:toInteger($doc_id)}) merge (t2:TIMEX {tid:relatedToTime, doc_id:toInteger($doc_id)}) MERGE (t1)-[tl:TLINK{id:lid, relType:relType}]->(t2) SET tl.signalID = signalID)
                    """
        
        data= graph.run(query, parameters={'xml_path': str(doc_id) + '.xml', 'doc_id': doc_id}).data()
        
        return ""

    def get_doc_text_and_dct(self, doc_id):
        graph = self.graph

        query = "MATCH (n:AnnotatedText) WHERE n.id = $doc_id RETURN n.text, n.creationtime"

        data = graph.run(query, parameters={'doc_id': doc_id}).data()
        result={}

        result["text"] = str(data[0].get('n.text'))
        result["dct"] = data[0].get('n.creationtime')
        
        return result



    def create_timexes2(self, doc_id):
        response_dict = self.get_doc_text_and_dct(doc_id)

        result_xml = self.callHeidelTimeService(response_dict)
        doc_id = str(doc_id)
        graph = self.graph

        merge_query = """
        MERGE (t:TIMEX {tid: $tid, doc_id: toInteger($doc_id)})
        SET t.origin = $origin,
            t.type = $type,
            t.value = $value,
            t.text = $text,
            t.quant = $quant,
            t.start_index = toInteger($start_char),
            t.end_index = toInteger($end_char),
            t.begin = toInteger($start_char),
            t.end = toInteger($end_char),
            t.start_char = toInteger($start_char),
            t.end_char = toInteger($end_char),
            t.functionInDocument = coalesce($functionInDocument, t.functionInDocument, 'NONE')
        WITH t
        MATCH (a:AnnotatedText {id: toInteger($doc_id)})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(ta:TagOccurrence)
        WHERE ta.index >= toInteger($start_char) AND ta.end_index <= toInteger($end_char)
        WITH t, collect(ta) AS tas, min(ta.tok_index_doc) AS min_tok, max(ta.tok_index_doc) AS max_tok
        SET t.start_tok = min_tok,
            t.end_tok = max_tok
        FOREACH (one IN tas | MERGE (one)-[:TRIGGERS]->(t))
        """

        created = 0
        for timex in _iter_timex_elements(result_xml):
            begin = timex.attrib.get("begin") or timex.attrib.get("start_index")
            end = timex.attrib.get("end") or timex.attrib.get("end_index")
            tid = timex.attrib.get("tid") or timex.attrib.get("id")
            if not tid or begin is None or end is None:
                continue
            if not str(begin).isdigit() or not str(end).isdigit():
                continue

            graph.run(
                merge_query,
                parameters={
                    "doc_id": doc_id,
                    "tid": tid,
                    "origin": timex.attrib.get("origin") or "text2graph",
                    "type": timex.attrib.get("type"),
                    "value": timex.attrib.get("value"),
                    "text": (timex.text or "").strip() or timex.attrib.get("text"),
                    "quant": timex.attrib.get("quant") or "N/A",
                    "functionInDocument": timex.attrib.get("functionInDocument"),
                    "start_char": int(begin),
                    "end_char": int(end),
                },
            )
            created += 1

        logger.info("create_timexes2: merged %d TIMEX nodes", created)
        
        return ""


    def callHeidelTimeService(self, parameters):
        dct = parameters.get("dct")
        text = parameters.get("text")
        
        #String.replace(split(ann.creationtime, 'T')[0],'-','')


        dct = dct.split('T')[0]


        data = {"input":text, "dct": dct}

        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}

        response = requests.post(self.heideltime_url, json=data, headers=headers)

        # print(response.content)
        return response.text



    def create_timexes(self, doc_id):
        logger.debug("create_timexes %s", doc_id)
        graph = self.graph

        query = """CALL apoc.load.xml($xml_path)
                    YIELD value as result
                    UNWIND [item in result._children where item._type ="tarsqi_tags"] AS tarsqi
                    UNWIND [item in tarsqi._children where item._type ="TIMEX3"] AS timex
                    WITH timex.begin as begin, timex.end as end, timex.origin as orig, timex.tid as tid, timex.type as typ, timex.value as val
                    MERGE (t:TIMEX {tid:tid, doc_id:$doc_id, begin:toInteger(begin), end:toInteger(end), origin:orig, type:typ, value:val})
                    WITH t
                    MATCH (a:AnnotatedText {id:$doc_id})-[*2]->(ta:TagOccurrence) where ta.index>= toInteger(t.begin) AND ta.end_index <= toInteger(t.end)
                    MERGE (ta)-[:TRIGGERS]->(t)"""

        data = graph.run(query, parameters={'xml_path': str(doc_id) + '.xml', 'doc_id': doc_id}).data()

        return ""




    def callTtkService(self, parameters):
        dct = parameters.get("dct")
        text = parameters.get("text")
        
        #String.replace(split(ann.creationtime, 'T')[0],'-','')


        dct = dct.split('T')[0]

        dct.replace('-','')

        data = {"input":text, "dct": dct}

        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}

        response = requests.post(self.temporal_url, json=data, headers=headers)

        # print(response.content)
        return response.text


    def _get_ttk_xml(self, doc_id):
        response_dict = self.get_doc_text_and_dct(doc_id)
        return self.callTtkService(response_dict)


    def create_signals2(self, doc_id):
        result_xml = self._get_ttk_xml(doc_id)
        doc_id = str(doc_id)
        graph = self.graph

        query = """WITH $result_xml AS xmlString
                    WITH apoc.xml.parse(xmlString) AS result
                    UNWIND [item in result._children where item._type ="tarsqi_tags"] AS tarsqi
                    UNWIND [item in tarsqi._children where item._type ="SIGNAL"] AS signal
                    WITH coalesce(signal.sid, 'sig_' + $doc_id + '_' + coalesce(signal.begin, signal.start_index, 'na') + '_' + coalesce(signal.end, signal.end_index, 'na')) AS sid,
                         coalesce(signal.begin, signal.start_index) AS begin,
                         coalesce(signal.end, signal.end_index) AS end,
                         coalesce(signal._text, signal.text) AS text
                    WHERE begin IS NOT NULL AND end IS NOT NULL
                    MERGE (s:Signal {id: sid, doc_id: toInteger($doc_id)})
                    SET s.type = 'SIGNAL',
                        s.text = text,
                        s.start_char = toInteger(begin),
                        s.end_char = toInteger(end)
                    WITH s
                    MATCH (a:AnnotatedText {id:toInteger($doc_id)})-[*2]->(ta:TagOccurrence)
                    WHERE ta.index >= toInteger(s.start_char) AND ta.end_index <= toInteger(s.end_char)
                    WITH s, collect(ta) AS tas, min(ta.tok_index_doc) AS min_tok, max(ta.tok_index_doc) AS max_tok
                    SET s.start_tok = min_tok,
                        s.end_tok = max_tok
                    FOREACH (one IN tas | MERGE (one)-[:TRIGGERS]->(s))
                """

        graph.run(query, parameters={"result_xml": result_xml, "doc_id": doc_id}).data()
        return ""


    def create_tevents2(self, doc_id):
        result_xml = self._get_ttk_xml(doc_id)
        doc_id = str(doc_id)

        #print(result_xml)
        graph = self.graph


        query = """WITH $result_xml
                    AS xmlString
                    WITH apoc.xml.parse(xmlString) AS result
                    UNWIND [item in result._children where item._type ="tarsqi_tags"] AS tarsqi
                    UNWIND [item in tarsqi._children where item._type ="EVENT"] AS event
                    WITH event.begin as begin, event.end as end, event.aspect as aspect, event.class as class, event.eid as eid, event.eiid as eiid, event.epos as epos, event.form as form, event.pos as pos, event.tense as tense, event.polarity as polarity, event.modality as modality
                    MATCH (a:AnnotatedText {id: toInteger($doc_id)})-[*2]->(ta:TagOccurrence)
                    WHERE ta.index = toInteger(begin)
                    MERGE (event:TEvent {doc_id: toInteger($doc_id), eiid: eiid})
                    SET event.begin = toInteger(begin),
                        event.end = toInteger(end),
                        event.start_char = toInteger(begin),
                        event.end_char = toInteger(end),
                        event.start_tok = ta.tok_index_doc,
                        event.end_tok = coalesce(event.end_tok, ta.tok_index_doc),
                        event.aspect = aspect,
                        event.class = class,
                        event.epos = epos,
                        event.form = form,
                        event.modality = modality,
                        event.polarity = polarity,
                        event.pos = pos,
                        event.tense = tense
                    MERGE (ta)-[:TRIGGERS]->(event)"""
        
        data= graph.run(query,parameters={'result_xml': result_xml, 'doc_id': doc_id}).data()
        
        return ""


    def create_event_mentions2(self, doc_id):
        """Create EventMention nodes for each TEvent created in the temporal phase.
        
        EventMention represents the mention-level event instantiation with properties
        like tense, aspect, polarity, and modality. Each EventMention refers to a 
        canonical TEvent via the REFERS_TO relationship.
        
        This is called after create_tevents2 to ensure TEvent nodes exist.
        """
        doc_id = str(doc_id)
        graph = self.graph
        
        query = """
        MATCH (event:TEvent {doc_id: toInteger($doc_id)})
        WHERE NOT EXISTS { (event)<-[:REFERS_TO]-(em:EventMention) }
        OPTIONAL MATCH (tok:TagOccurrence)-[:TRIGGERS]->(event)
        WITH event, tok
        ORDER BY tok.tok_index_doc
        WITH event, head(collect(tok)) AS trig_tok, event.eiid + '_mention' as mention_id
        OPTIONAL MATCH (s:Sentence)-[:HAS_TOKEN]->(trig_tok)
        WITH event, mention_id, trig_tok,
             head([(s)-[:HAS_TOKEN]->(candidate:TagOccurrence)
                   WHERE candidate.tok_index_doc = trig_tok.tok_index_doc + 1 | candidate]) AS next_tok,
             CASE
                 WHEN trig_tok IS NOT NULL AND trig_tok.lemma IS NOT NULL AND trim(toString(trig_tok.lemma)) <> ''
                 THEN toLower(trim(toString(trig_tok.lemma)))
                 ELSE NULL
             END AS trigger_lemma
        MERGE (em:EventMention {id: mention_id})
        SET em.doc_id = event.doc_id,
            em.pred = CASE
                WHEN trigger_lemma IS NOT NULL
                     AND trig_tok.pos STARTS WITH 'VB'
                     AND next_tok.pos = 'RP'
                     AND next_tok.lemma IS NOT NULL
                     AND trim(toString(next_tok.lemma)) <> ''
                THEN trigger_lemma + ' ' + toLower(trim(toString(next_tok.lemma)))
                ELSE coalesce(trigger_lemma, event.pred, event.form)
            END,
            em.tense = event.tense,
            em.aspect = event.aspect,
            em.pos = event.pos,
            em.epos = event.epos,
            em.form = event.form,
            em.modality = event.modality,
            em.polarity = event.polarity,
            em.class = event.class,
            em.start_tok = event.start_tok,
            em.end_tok = CASE
                WHEN trig_tok.pos STARTS WITH 'VB' AND next_tok.pos = 'RP'
                THEN coalesce(next_tok.tok_index_doc, event.end_tok)
                ELSE event.end_tok
            END,
            em.start_char = event.start_char,
            em.end_char = event.end_char,
            em.begin = event.begin,
            em.end = event.end
        WITH em, event
        MERGE (em)-[:REFERS_TO]->(event)
        RETURN count(*) as mentions_created
        """
        
        result = graph.run(query, parameters={'doc_id': doc_id}).data()
        count = result[0].get('mentions_created', 0) if result else 0
        logger.info("create_event_mentions2: created %d EventMention nodes for doc_id=%s", count, doc_id)
        
        return ""



    def create_tevents(self, doc_id):
        logger.debug("create_tevents %s", doc_id)
        graph = self.graph

        query = """CALL apoc.load.xml($xml_path)
                    YIELD value as result
                    UNWIND [item in result._children where item._type ="tarsqi_tags"] AS tarsqi
                    UNWIND [item in tarsqi._children where item._type ="TLINK"] AS tlink
                    WITH tlink.lid as lid, tlink.origin as origin, tlink.relType as relType, tlink.relatedToTime as relatedToTime, tlink.timeID as timeID, tlink.eventInstanceID as eventInstanceID, tlink.relatedToEventInstance as relatedToEventInstance, tlink.syntax as syntax
                    foreach(ignoreMe IN CASE WHEN relatedToTime IS NOT NULL and timeID IS NOT NULL THEN [1] ELSE [] END | merge (t1:TIMEX{tid:timeID, doc_id:$doc_id}) merge (t2:TIMEX {tid:relatedToTime, doc_id:$doc_id}) MERGE (t1)-[:TLINK{id:lid, relType:relType}]->(t2))
                    """
        
        data= graph.run(query, parameters={'xml_path': str(doc_id) + '.xml', 'doc_id': doc_id}).data()
        
        return ""

if __name__ == '__main__':
    import time as _time
    tp = TemporalPhase(sys.argv[1:])

    # create the filename by getting the id of the document.

    # query for getting all AnnotatedDoc
    ids = tp.get_annotated_text()
    _phase_start = _time.time()
    for id in ids:

        tp.create_DCT_node(id)
        tp.create_tevents2(id)
        tp.create_signals2(id)
        #tp.create_timexes(id)
        tp.create_timexes2(id)
        #tp.create_tlinks_e2e(id)
        #tp.create_tlinks_e2t(id)
        #tp.create_tlinks_t2t(id)

    _phase_duration = _time.time() - _phase_start
    # Record a PhaseRun marker for restart visibility (Item 7)
    try:
        from textgraphx.phase_assertions import record_phase_run
        record_phase_run(
            tp.graph,
            phase_name="temporal",
            duration_seconds=_phase_duration,
            documents_processed=len(ids),
            metadata={"passes": "create_DCT_node,create_tevents2,create_signals2,create_timexes2"},
        )
    except Exception:
        logger.exception("Failed to write TemporalRun marker (non-fatal)")
        
