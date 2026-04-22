#!/usr/bin/env python3
import json
from textgraphx.neo4j_client import make_graph_from_config

def main():
    g = make_graph_from_config()
    query = '''
MATCH (ann:AnnotatedText) WHERE ann.id = 1
MATCH (ann)-[:CONTAINS_SENTENCE]->(s:Sentence)
OPTIONAL MATCH (s)-[:HAS_TOKEN]->(t:TagOccurrence)
WITH s, s.text AS stext, collect(t) AS toks
UNWIND toks AS tok
WITH s, stext, tok
ORDER BY tok.tok_index_doc
WITH s, stext, collect(tok.text) AS tokens, collect(tok.tok_index_doc) AS idxs
RETURN s.id AS sid, stext AS text, tokens, idxs
ORDER BY sid
'''
    rows = g.run(query).data()
    out = []
    for r in rows:
        sid = r.get('sid')
        text = r.get('text')
        tokens = r.get('tokens')
        idxs = r.get('idxs')
        out.append({'sid': sid, 'text': text, 'token_count': len(tokens) if tokens else 0, 'tokens': tokens, 'idxs': idxs})
    print(json.dumps(out, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()
