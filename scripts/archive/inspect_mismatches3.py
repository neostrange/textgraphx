import json

path = '/home/neo/environments/textgraphx/textgraphx/datastore/evaluation/cycle_20260416T050808Z/eval_report_strict.json'
with open(path) as f:
    data = json.load(f)

print("=== ENTITY MISMATCHES (STRICT) ===")
count = 0
for r in data.get('reports', []):
    doc_id = r.get('doc_id', 'unknown')
    layers = r.get('layers', {})
    entities = layers.get('entity', {})
    fps = entities.get('false_positives', [])
    fns = entities.get('false_negatives', [])
    
    if len(fps) > 0 or len(fns) > 0:
        print(f"\nDocument: {doc_id}")
        print("  False Positives (System extracted these):")
        for fp in fps[:5]:
            print(f"    - Details: {fp}")
            
        print("  False Negatives (Gold standard expected these):")
        for fn in fns[:5]:
            print(f"    - Details: {fn}")
        count += 1
        
    if count >= 3:
        break
