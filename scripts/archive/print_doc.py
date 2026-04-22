import sys
from py2neo import Graph
graph = Graph("bolt://localhost:7687")
doc_id = 96770
rows = graph.run("MATCH (a:AnnotatedText)-[:CONTAINS_SENTENCE]->(s:Sentence)-[:HAS_TOKEN]->(t:TagOccurrence) WHERE a.id=96770 RETURN t.tok_index_doc as idx, t.text as text ORDER BY t.tok_index_doc").data()
for r in rows:
    print(f"{r['idx']}: {r['text']}")
