from textgraphx.neo4j_client import make_graph_from_config
from textgraphx.evaluation.meantime_evaluator import build_document_from_neo4j
import json

g = make_graph_from_config()
doc_id = 96770 # the one with 24 SLINK/CLINKS
doc = build_document_from_neo4j(g, doc_id)

clinks = len([r for r in doc.relations if r.kind == 'clink'])
slinks = len([r for r in doc.relations if r.kind == 'slink'])
print(f"CLINK out of Neo4j doc: {clinks}")
print(f"SLINK out of Neo4j doc: {slinks}")

