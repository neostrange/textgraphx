from textgraphx.neo4j_client import make_graph_from_config
import json

graph = make_graph_from_config()

path = '/home/neo/environments/textgraphx/textgraphx/datastore/evaluation/cycle_20260416T050808Z/eval_report_strict.json'
with open(path) as f:
    data = json.load(f)

for r in data.get('reports', [])[:2]:
    doc_id = r.get('doc_id')
    if 'strict' in r and 'event' in r['strict']:
         print("DOC:", doc_id)
         for fp in r['strict']['event'].get('spurious', [])[:2]:
             print("Event Spurious:", fp)
         print(graph.run(f"MATCH (t:TagOccurrence) WHERE t.doc_id='{doc_id}' RETURN t.tok_index_doc, t.text LIMIT 3").data())

