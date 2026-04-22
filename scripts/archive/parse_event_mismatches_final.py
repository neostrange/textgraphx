from textgraphx.neo4j_client import make_graph_from_config
import json

graph = make_graph_from_config()

path = '/home/neo/environments/textgraphx/textgraphx/datastore/evaluation/cycle_20260416T050808Z/eval_report_strict.json'
with open(path) as f:
    data = json.load(f)

for card in data.get('reports', []):
    doc_id = card.get('doc_id')
    
    if 'strict' in card and 'event' in card['strict'] and 'examples' in card['strict']['event']:
        examples = card['strict']['event']['examples']
        missing = examples.get('missing', [])
        spurious = examples.get('spurious', [])
        boundary_mismatch = examples.get('boundary_mismatch', [])

        if not missing and not spurious and not boundary_mismatch:
            continue

        print(f"\n======== Doc: {doc_id} - EVENTS =========")
        
        for item in spurious[:3]:
            # Each item in spurious might be a dict with 'span' or just an array of tokens
            if isinstance(item, dict) and 'span' in item:
                span = item['span']
            elif isinstance(item, list):
                span = item
            else: continue
                
            q = f"MATCH (t:TagOccurrence) WHERE t.id STARTS WITH '{doc_id}_' AND t.tok_index_doc IN {span} RETURN t.tok_index_doc AS id, t.text AS text ORDER BY id"
            res = graph.run(q).data()
            text = ' '.join([x['text'] for x in res])
            print(f"  Spurious (System found this, NOT in Gold): '{text}'")

        for item in missing[:3]:
            if isinstance(item, dict) and 'span' in item:
                span = item['span']
            elif isinstance(item, list):
                span = item
            else: continue
                
            q = f"MATCH (t:TagOccurrence) WHERE t.id STARTS WITH '{doc_id}_' AND t.tok_index_doc IN {span} RETURN t.tok_index_doc AS id, t.text AS text ORDER BY id"
            res = graph.run(q).data()
            text = ' '.join([x['text'] for x in res])
            print(f"  Missing (Gold has this, System missed it completely): '{text}'")
            
        for item in boundary_mismatch[:3]:
           gold_span = item.get('gold_span', [])
           pred_span = item.get('pred_span', [])
           
           if gold_span:
               gq = f"MATCH (t:TagOccurrence) WHERE t.id STARTS WITH '{doc_id}_' AND t.tok_index_doc IN {gold_span} RETURN t.tok_index_doc AS id, t.text AS text ORDER BY id"
               gres = graph.run(gq).data()
               gtext = ' '.join([x['text'] for x in gres])
           else:
               gtext = "N/A"
               
           if pred_span:
               pq = f"MATCH (t:TagOccurrence) WHERE t.id STARTS WITH '{doc_id}_' AND t.tok_index_doc IN {pred_span} RETURN t.tok_index_doc AS id, t.text AS text ORDER BY id"
               pres = graph.run(pq).data()
               ptext = ' '.join([x['text'] for x in pres])
           else:
               ptext = "N/A"
               
           print(f"  Boundary Mismatch:")
           print(f"    Gold Bound: '{gtext}'")
           print(f"    Pred Bound: '{ptext}'")
           
        break # Just do one doc that has something
