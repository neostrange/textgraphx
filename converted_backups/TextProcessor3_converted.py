"""Converted backup TextProcessor3 avoiding py2neo and using the bolt driver.

This file mirrors the same conservative approach used for TextProcessor2_converted.
It focuses on replacing direct py2neo usage while keeping original Cypher helpers.
"""
from __future__ import annotations

import requests
import configparser
import os
import traceback
from typing import Any, Dict, List

from util.RestCaller import callAllenNlpCoref
from nltk.corpus import wordnet31 as wn
from nltk.corpus.reader.wordnet import WordNetError as wn_error


class TextProcessor:
    """Converted TextProcessor class for review.

    The class expects an official neo4j.Driver as `driver` and exposes
    execute_query helpers that use its sessions.
    """

    def __init__(self, nlp, driver):
        self.nlp = nlp
        self._driver = driver
        self.uri = ""
        self.username = ""
        self.password = ""
        config = configparser.ConfigParser()
        config_file = os.path.join(os.path.dirname(__file__), 'config.ini')
        config.read(config_file)
        if 'py2neo' in config:
            py2neo_params = config['py2neo']
            self.uri = py2neo_params.get('uri')
            self.username = py2neo_params.get('username')
            self.password = py2neo_params.get('password')

    def execute_query3(self, query: str, params: Dict[str, Any] = None) -> List[Any]:
        session = None
        results = []
        try:
            session = self._driver.session()
            response = session.run(query, params)
            for item in response:
                results.append(item)
        except Exception as e:
            print("Query Failed: ", e)
            traceback.print_exc()
        finally:
            if session is not None:
                session.close()
        return results

    def execute_query(self, query: str, params: Dict[str, Any] = None) -> List[Any]:
        session = None
        response = None
        results = []
        try:
            session = self._driver.session()
            response = session.run(query, params)
            for items in response:
                if 'result' in items.keys():
                    results.append(items['result'])
                else:
                    results.append(dict(items))
        except Exception as e:
            print("Query Failed: ", str(e))
            traceback.print_exc()
        finally:
            if session is not None:
                session.close()
        return results

    def execute_query2(self, query: str, params: Dict[str, Any] = None) -> List[Any]:
        results = []
        with self._driver.session() as session:
            for items in session.run(query, params):
                if 'result' in items.keys():
                    results.append(items['result'])
                else:
                    results.append(dict(items))
        return results

    # Coref and SRL methods (converted like TextProcessor2_converted)
    def do_coref2(self, doc, textId: int) -> List[Dict[str, Any]]:
        result = callAllenNlpCoref("coreference-resolution", doc.text)
        if not result:
            return []
        mentions_out = []
        for cluster in result.get('clusters', []):
            if not cluster:
                continue
            ant_span = cluster[0]
            ant_start = int(ant_span[0])
            ant_end = int(ant_span[-1])
            ant_text = doc[ant_start:ant_end].text
            self.execute_query3("MERGE (a:Antecedent {text:$text, startIndex:$start, endIndex:$end})", {"text": ant_text, "start": ant_start, "end": ant_end})
            for idx in range(ant_start, ant_end):
                self.execute_query("MATCH (t:TagOccurrence {tok_index_doc: $idx})-[:HAS_TOKEN]-()-[:CONTAINS_SENTENCE]->(doc:AnnotatedText {id: $doc_id}) MERGE (t)-[:PARTICIPATES_IN]->(a)", {"idx": idx, "doc_id": doc._.text_id})
            for span_token_indexes in cluster[1:]:
                m_start = int(span_token_indexes[0])
                m_end = int(span_token_indexes[-1])
                m_text = doc[m_start:m_end].text
                mentions_out.append({"referent": {"start_index": m_start, "end_index": m_end, "text": m_text},
                                     "antecedent": {"start_index": ant_start, "end_index": ant_end, "text": ant_text}})
                self.execute_query3("MERGE (cm:CorefMention {text:$text, startIndex:$start, endIndex:$end}) WITH cm MATCH (a:Antecedent {text:$ant_text, startIndex:$ant_start, endIndex:$ant_end}) MERGE (cm)-[:COREF]->(a)", {"text": m_text, "start": m_start, "end": m_end, "ant_text": ant_text, "ant_start": ant_start, "ant_end": ant_end})
                for idx in range(m_start, m_end):
                    self.execute_query3("MATCH (t:TagOccurrence {tok_index_doc:$idx})-[:HAS_TOKEN]-()-[:CONTAINS_SENTENCE]->(doc:AnnotatedText {id:$doc_id}) MERGE (t)-[:PARTICIPATES_IN]->(cm)", {"idx": idx, "doc_id": doc._.text_id})
        return mentions_out

    def store_coref_mentions(self, doc, mentions: List[Dict[str, Any]]):
        for mention in mentions:
            ref = mention['referent']
            ant = mention['antecedent']
            self.execute_query3("MERGE (cm:CorefMention {text:$text, startIndex:$start, endIndex:$end})", {"text": ref['text'], "start": ref['start_index'], "end": ref['end_index']})
            self.execute_query3("MERGE (a:Antecedent {text:$text, startIndex:$start, endIndex:$end})", {"text": ant['text'], "start": ant['start_index'], "end": ant['end_index']})
            self.execute_query3("MATCH (cm:CorefMention {text:$cm_text, startIndex:$cm_start, endIndex:$cm_end}) MATCH (a:Antecedent {text:$a_text, startIndex:$a_start, endIndex:$a_end}) MERGE (cm)-[:COREF]->(a)", {"cm_text": ref['text'], "cm_start": ref['start_index'], "cm_end": ref['end_index'], "a_text": ant['text'], "a_start": ant['start_index'], "a_end": ant['end_index']})
            for idx in range(ref['start_index'], ref['end_index']):
                self.execute_query3("MATCH (t:TagOccurrence {tok_index_doc:$idx})-[:HAS_TOKEN]-()-[:CONTAINS_SENTENCE]->(doc:AnnotatedText {id:$doc_id}) MERGE (t)-[:PARTICIPATES_IN]->(cm)", {"idx": idx, "doc_id": doc._.text_id})

    def process_srl(self, doc, flag_display: bool = False):
        for tok in doc:
            frame_dict = {}
            tv = None
            for label, indices_list in tok._.SRL.items():
                for indices in indices_list:
                    start = int(indices[0])
                    end = int(indices[-1])
                    span_text = doc[start:end].text
                    if label == 'V':
                        f_q = "MERGE (f:Frame {text:$text, startIndex:$start, endIndex:$end})"
                        self.execute_query3(f_q, {"text": span_text, "start": start, "end": end})
                        for idx in indices:
                            self.execute_query3("MATCH (t:TagOccurrence {tok_index_doc:$idx})-[:HAS_TOKEN]-()-[:CONTAINS_SENTENCE]->(doc:AnnotatedText {id:$doc_id}) MATCH (f:Frame {text:$text, startIndex:$start, endIndex:$end}) MERGE (t)-[:PARTICIPATES_IN]->(f)", {"idx": idx, "doc_id": doc._.text_id, "text": span_text, "start": start, "end": end})
                        tv = (span_text, start, end)
                    else:
                        a_q = "MERGE (a:FrameArgument {type:$type, text:$text, startIndex:$start, endIndex:$end})"
                        self.execute_query3(a_q, {"type": label, "text": span_text, "start": start, "end": end})
                        for idx in indices:
                            self.execute_query3("MATCH (t:TagOccurrence {tok_index_doc:$idx})-[:HAS_TOKEN]-()-[:CONTAINS_SENTENCE]->(doc:AnnotatedText {id:$doc_id}) MATCH (a:FrameArgument {type:$type, text:$text, startIndex:$start, endIndex:$end}) MERGE (t)-[:PARTICIPATES_IN]->(a)", {"idx": idx, "doc_id": doc._.text_id, "type": label, "text": span_text, "start": start, "end": end})
                        frame_dict.setdefault(label, []).append((span_text, start, end))
            if tv is not None:
                f_text, f_start, f_end = tv
                for label, args in frame_dict.items():
                    for arg_text, a_start, a_end in args:
                        self.execute_query3("MATCH (a:FrameArgument {text:$a_text, startIndex:$a_start, endIndex:$a_end}) MATCH (f:Frame {text:$f_text, startIndex:$f_start, endIndex:$f_end}) MERGE (a)-[:PARTICIPANT]->(f)", {"a_text": arg_text, "a_start": a_start, "a_end": a_end, "f_text": f_text, "f_start": f_start, "f_end": f_end})


def filter_spans(spans):
    get_sort_key = lambda span: (span.end - span.start, -span.start)
    sorted_spans = sorted(spans, key=get_sort_key, reverse=True)
    result = []
    seen_tokens = set()
    for span in sorted_spans:
        if span.start not in seen_tokens and span.end - 1 not in seen_tokens:
            result.append(span)
        seen_tokens.update(range(span.start, span.end))
    result = sorted(result, key=lambda span: span.start)
    return result


def filter_extended_spans(items):
    get_sort_key = lambda item: (item['span'].end - item['span'].start, -item['span'].start)
    sorted_spans = sorted(items, key=get_sort_key, reverse=True)
    result = []
    seen_tokens = set()
    for item in sorted_spans:
        if item['span'].start not in seen_tokens and item['span'].end - 1 not in seen_tokens:
            result.append(item)
        seen_tokens.update(range(item['span'].start, item['span'].end))
    result = sorted(result, key=lambda span: span['span'].start)
    return result
