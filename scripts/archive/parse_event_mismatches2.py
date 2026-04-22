from textgraphx.neo4j_client import make_graph_from_config
import json

graph = make_graph_from_config()

path = '/home/neo/environments/textgraphx/textgraphx/datastore/evaluation/cycle_20260416T050808Z/eval_report_strict.json'
with open(path) as f:
    data = json.load(f)

for r in data.get('reports', [])[:3]:
    doc_id = r.get('doc_id')
    if 'strict' in r and 'event' in r['strict']:
        event = r['strict']['event']
        
        miss = event.get('missing', [])
        sp = event.get('spurious', [])
        
        if len(miss) > 0 or len(sp) > 0:
            print(f"\nDoc: {doc_id} - EVENTS")
            for b in sp[:3]:
                pred_span = b['span']
                pred_q = f"MATCH (t:TagOccurrence) WHERE t.id STARTS WITH '{doc_id}_' AND t.tok_index_doc IN {pred_span} RETURN t.tok_index_doc AS id, t.text AS text ORDER BY id"
                pred_res = graph.run(pred_q).data()
                pred_text = ' '.join([x['text'] for x in pred_res])
                print(f"  Spurious (Pred didn't match anything strict): '{pred_text}'")

            for b in miss[:3]:
                gold_span = b['span']
                gold_q = f"MATCH (t:TagOccurrence) WHERE t.id STARTS WITH '{doc_id}_' AND t.tok_index_doc IN {gold_span} RETURN t.tok_index_doc AS id, t.text AS text ORDER BY id"
                gold_res = graph.run(gold_q).data()
                gold_text = ' '.join([x['text'] for x in gold_res])
                print(f"  Missing (Gold wasn't matched strictly): '{gold_text}'")


