#!/usr/bin/env python3
from __future__ import annotations
from textgraphx.database.client import make_graph_from_config
import json

Q = """
MATCH (:AnnotatedText {id: $doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(tok:TagOccurrence)-[:IN_MENTION]->(m)
WHERE (m:EntityMention OR m:NamedEntity OR m:CorefMention)
WITH m, min(tok.tok_index_doc) AS start_tok, max(tok.tok_index_doc) AS end_tok, head(collect(tok)) AS head_tok
RETURN DISTINCT id(m) AS node_id, labels(m) AS labels, coalesce(m.syntactic_type, m.syntacticType) AS syntactic_type, start_tok, end_tok
ORDER BY start_tok, end_tok
"""

def main():
    g = make_graph_from_config()
    rows = g.run(Q, {"doc_id": 76437}).data()
    print(json.dumps(rows, indent=2, default=str))
    g.close()

if __name__ == '__main__':
    main()
