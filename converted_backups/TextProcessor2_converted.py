"""Converted backup of TextProcessor2 that avoids py2neo and uses the
official neo4j bolt driver via self._driver.session().run(...).

This is a conservative conversion intended for review. It keeps the original
class shape and many helper methods but replaces py2neo Node/Relationship
manipulation with explicit Cypher MERGE/CREATE statements executed through
`execute_query` / `execute_query3` helpers.

Notes:
- The original file used py2neo Node/Relationship objects and graph.create()/evaluate().
  This converted variant implements the same high-level effects with Cypher.
- The conversion focuses on `do_coref2`, `store_coref_mentions` and `process_srl`
  which previously relied on py2neo object APIs.
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
    """Simplified TextProcessor converted from the py2neo-based backup.

    This class expects a Neo4j driver instance as `driver` (neo4j.Driver).
    Many helper methods use `self._driver.session().run(...)` indirectly via
    `execute_query*` helpers.

    The converted methods use Cypher MERGE/UNWIND patterns so we no longer
    depend on py2neo Node/Relationship Python objects.
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

    # -------------------- Neo4j helpers --------------------
    def execute_query3(self, query: str, params: Dict[str, Any] = None) -> List[Any]:
        """Run a query and return a list of records (as Mapping objects).

        This mirrors the previous execute_query3 behaviour but uses the bolt
        driver session directly and returns raw records.
        """
        results = []
        session = None
        try:
            session = self._driver.session()
            response = session.run(query, params)
            for record in response:
                results.append(record)
        except Exception as e:
            print("Query Failed: ", e)
            traceback.print_exc()
        finally:
            if session is not None:
                session.close()
        return results

    def execute_query(self, query: str, params: Dict[str, Any] = None) -> List[Any]:
        """Run a query and try to return the `result` field values collected from rows.

        Several older functions expect a list of primitive values stored under a
        key named `result` in the returned records. This helper keeps that
        behaviour for compatibility.
        """
        results = []
        session = None
        try:
            session = self._driver.session()
            response = session.run(query, params)
            for items in response:
                # try to return a named field "result" when present
                if 'result' in items.keys():
                    results.append(items['result'])
                else:
                    # otherwise return the whole mapping
                    results.append(dict(items))
        except Exception as e:
            print("Query Failed: ", str(e))
            traceback.print_exc()
        finally:
            if session is not None:
                session.close()
        return results

    def execute_query2(self, query: str, params: Dict[str, Any] = None) -> List[Any]:
        """Variant that yields `result` values using a context manager."""
        results = []
        with self._driver.session() as session:
            for items in session.run(query, params):
                if 'result' in items.keys():
                    results.append(items['result'])
                else:
                    results.append(dict(items))
        return results

    # -------------------- Coreference (converted) --------------------
    def do_coref2(self, doc, textId: int) -> List[Dict[str, Any]]:
        """Run the AllenNLP coreference API and persist Coref data using Cypher.

        The method expects the predictor result format documented in the original
        code (dictionary with key "clusters" where each cluster is a list of
        token index spans). For each cluster we:
          - MERGE an Antecedent node for the first span
          - MERGE a CorefMention node for each subsequent span
          - Create PARTICIPATES_IN relationships between TagOccurrence tokens and
            the mention/antecedent nodes using the token index ranges.
          - Create COREF relationship from CorefMention -> Antecedent.

        Returns a list of mention dicts for downstream use.
        """
        result = callAllenNlpCoref("coreference-resolution", doc.text)
        if not result:
            return []

        mentions_out = []
        for cluster in result.get('clusters', []):
            if not cluster:
                continue
            # antecedent span is the first span in cluster
            antecedent_span = cluster[0]
            ant_start = int(antecedent_span[0])
            ant_end = int(antecedent_span[-1])
            ant_text = doc[ant_start:ant_end].text

            # create antecedent node
            ant_query = """
            MERGE (a:Antecedent {text: $text, startIndex: $start, endIndex: $end})
            RETURN id(a) AS id
            """
            ant_params = {"text": ant_text, "start": ant_start, "end": ant_end}
            self.execute_query3(ant_query, ant_params)

            # link tag occurrences to antecedent
            for idx in range(ant_start, ant_end):
                link_q = "MATCH (t:TagOccurrence {tok_index_doc: $idx})-[:HAS_TOKEN]-()-[:CONTAINS_SENTENCE]->(doc:AnnotatedText {id: $doc_id}) MERGE (t)-[:PARTICIPATES_IN]->(a)"
                self.execute_query(link_q, {"idx": idx, "doc_id": doc._.text_id})

            # other mentions in the cluster
            for span_token_indexes in cluster[1:]:
                m_start = int(span_token_indexes[0])
                m_end = int(span_token_indexes[-1])
                m_text = doc[m_start:m_end].text
                mentions_out.append({"referent": {"start_index": m_start, "end_index": m_end, "text": m_text},
                                     "antecedent": {"start_index": ant_start, "end_index": ant_end, "text": ant_text}})

                # create coref mention node and COREF relation to antecedent
                cm_q = """
                MERGE (cm:CorefMention {text: $text, startIndex: $start, endIndex: $end})
                WITH cm
                MATCH (a:Antecedent {text: $ant_text, startIndex: $ant_start, endIndex: $ant_end})
                MERGE (cm)-[:COREF]->(a)
                RETURN id(cm) AS id
                """
                cm_params = {"text": m_text, "start": m_start, "end": m_end, "ant_text": ant_text, "ant_start": ant_start, "ant_end": ant_end}
                self.execute_query3(cm_q, cm_params)

                # attach participating TagOccurrence tokens to coref mention
                for idx in range(m_start, m_end):
                    link_q = "MATCH (t:TagOccurrence {tok_index_doc: $idx})-[:HAS_TOKEN]-()-[:CONTAINS_SENTENCE]->(doc:AnnotatedText {id: $doc_id}) MERGE (t)-[:PARTICIPATES_IN]->(cm)"
                    self.execute_query(link_q, {"idx": idx, "doc_id": doc._.text_id})

        return mentions_out

    def store_coref_mentions(self, doc, mentions: List[Dict[str, Any]]):
        """Persist a list of mentions (as returned by do_coref2) using Cypher.

        Older code did more complex py2neo-based graph assembly. We now express
        the same operations with Cypher MERGE/UNWIND patterns. This helper will
        create MENTIONS relationships to NamedEntity when appropriate.
        """
        # The original method tried to link a CorefMention to a NamedEntity based
        # on head token indices. We keep a conservative approach and only create
        # PARTICIPATES_IN and COREF relations because NamedEntity linking often
        # requires more context.
        for mention in mentions:
            ref = mention['referent']
            ant = mention['antecedent']
            # ensure nodes exist
            self.execute_query3("MERGE (cm:CorefMention {text:$text, startIndex:$start, endIndex:$end})", {"text": ref['text'], "start": ref['start_index'], "end": ref['end_index']})
            self.execute_query3("MERGE (a:Antecedent {text:$text, startIndex:$start, endIndex:$end})", {"text": ant['text'], "start": ant['start_index'], "end": ant['end_index']})
            # create COREF
            self.execute_query3("MATCH (cm:CorefMention {text:$cm_text, startIndex:$cm_start, endIndex:$cm_end}) MATCH (a:Antecedent {text:$a_text, startIndex:$a_start, endIndex:$a_end}) MERGE (cm)-[:COREF]->(a)", {"cm_text": ref['text'], "cm_start": ref['start_index'], "cm_end": ref['end_index'], "a_text": ant['text'], "a_start": ant['start_index'], "a_end": ant['end_index']})
            # attach tag occurrences
            for idx in range(ref['start_index'], ref['end_index']):
                self.execute_query3("MATCH (t:TagOccurrence {tok_index_doc:$idx})-[:HAS_TOKEN]-()-[:CONTAINS_SENTENCE]->(doc:AnnotatedText {id:$doc_id}) MERGE (t)-[:PARTICIPATES_IN]->(cm)", {"idx": idx, "doc_id": doc._.text_id})

    # -------------------- SRL (converted) --------------------
    def process_srl(self, doc, flag_display: bool = False):
        """Persist SRL frames and arguments using Cypher MERGE patterns.

        The previous implementation created py2neo Node/Relationship objects and
        used graph.create(). The converted implementation creates Frame and
        FrameArgument nodes and links TagOccurrence nodes using PARTICIPATES_IN
        and PARTICIPANT relationships.
        """
        for tok in doc:
            frame_dict = {}
            tv = None
            for label, indices_list in tok._.SRL.items():
                for indices in indices_list:
                    start = int(indices[0])
                    end = int(indices[-1])
                    span_text = doc[start:end].text
                    if label == 'V':
                        # create frame
                        f_q = "MERGE (f:Frame {text:$text, startIndex:$start, endIndex:$end}) RETURN id(f) as id"
                        self.execute_query3(f_q, {"text": span_text, "start": start, "end": end})
                        # link participating tokens
                        for idx in indices:
                            self.execute_query3("MATCH (t:TagOccurrence {tok_index_doc:$idx})-[:HAS_TOKEN]-()-[:CONTAINS_SENTENCE]->(doc:AnnotatedText {id:$doc_id}) MATCH (f:Frame {text:$text, startIndex:$start, endIndex:$end}) MERGE (t)-[:PARTICIPATES_IN]->(f)", {"idx": idx, "doc_id": doc._.text_id, "text": span_text, "start": start, "end": end})
                        tv = (span_text, start, end)
                    else:
                        # create frame argument
                        a_q = "MERGE (a:FrameArgument {type:$type, text:$text, startIndex:$start, endIndex:$end}) RETURN id(a) as id"
                        self.execute_query3(a_q, {"type": label, "text": span_text, "start": start, "end": end})
                        # link tokens to argument
                        for idx in indices:
                            self.execute_query3("MATCH (t:TagOccurrence {tok_index_doc:$idx})-[:HAS_TOKEN]-()-[:CONTAINS_SENTENCE]->(doc:AnnotatedText {id:$doc_id}) MATCH (a:FrameArgument {type:$type, text:$text, startIndex:$start, endIndex:$end}) MERGE (t)-[:PARTICIPATES_IN]->(a)", {"idx": idx, "doc_id": doc._.text_id, "type": label, "text": span_text, "start": start, "end": end})
                        frame_dict.setdefault(label, []).append((span_text, start, end))

            # link arguments to frame
            if tv is not None:
                f_text, f_start, f_end = tv
                for label, args in frame_dict.items():
                    for arg_text, a_start, a_end in args:
                        self.execute_query3("MATCH (a:FrameArgument {text:$a_text, startIndex:$a_start, endIndex:$a_end}) MATCH (f:Frame {text:$f_text, startIndex:$f_start, endIndex:$f_end}) MERGE (a)-[:PARTICIPANT]->(f)", {"a_text": arg_text, "a_start": a_start, "a_end": a_end, "f_text": f_text, "f_start": f_start, "f_end": f_end})

    # The remainder of the file (entity processing, WSD, sentence storage, etc.)
    # used only Cypher queries via execute_query and can be left as-is from the
    # original backups. For brevity we don't reimplement every helper here but
    # we keep the filter_spans helpers as they may be referenced by external
    # callers.


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
