from textgraphx.neo4j_client import make_graph_from_config
import json

graph = make_graph_from_config()

path = '/home/neo/environments/textgraphx/textgraphx/datastore/evaluation/cycle_20260416T050808Z/eval_report_strict.json'
with open(path) as f:
    data = json.load(f)

for r in data.get('reports', [])[:3]:
    doc_id = r.get('doc_id')
    if 'strict' in r and 'entity' in r['strict']:
        entity = r['strict']['entity']
        bm = entity.get('examples', {}).get('boundary_mismatch', [])
        
        if bm:
            print(f"\nDoc: {doc_id}")
            for b in bm[:3]:
                gold_span = b['gold']['span']
                pred_span = b['predicted']['span']
                
                # We see id is mapped like "61327_0_0"  (docId_sentId_tokId)
                # We can fetch everything with matching tok_index_doc, though the id prefix shows doc_id.
                
                # Fetch text for gold span from Neo4j
                gold_q = f"MATCH (t:TagOccurrence) WHERE t.id STARTS WITH '{doc_id}_' AND t.tok_index_doc IN {gold_span} RETURN t.tok_index_doc AS id, t.text AS text ORDER BY id"
                gold_res = graph.run(gold_q).data()
                gold_text = ' '.join([x['text'] for x in gold_res])

                # Fetch text for pred span from Neo4j
                pred_q = f"MATCH (t:TagOccurrence) WHERE t.id STARTS WITH '{doc_id}_' AND t.tok_index_doc IN {pred_span} RETURN t.tok_index_doc AS id, t.text AS text ORDER BY id"
                pred_res = graph.run(pred_q).data()
                pred_text = ' '.join([x['text'] for x in pred_res])

                print(f"  Gold ({b['gold']['attrs'].get('syntactic_type')}): '{gold_text}'")
                print(f"  Pred ({b['predicted']['attrs'].get('syntactic_type')}): '{pred_text}'\n")

