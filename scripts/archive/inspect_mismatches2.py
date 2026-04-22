import json

path = '/home/neo/environments/textgraphx/textgraphx/datastore/evaluation/cycle_20260416T050808Z/eval_report_strict.json'
with open(path) as f:
    data = json.load(f)

print("=== ENTITY MISMATCHES (STRICT) ===")
count = 0
for doc in data.get('documents', []):
    doc_id = doc.get('document_id', 'unknown')
    entities = doc.get('layers', {}).get('entity', {})
    fps = entities.get('false_positives', [])
    fns = entities.get('false_negatives', [])
    
    if len(fps) > 0 or len(fns) > 0:
        print(f"\nDocument: {doc_id}")
        print("  False Positives (System extracted these):")
        for fp in fps[:5]:
            print(f"    - Text: '{fp.get('value', fp.get('text', 'N/A'))}', Span/Tokens: {fp.get('span', fp.get('tokens', []))}, Type: {fp.get('type', 'N/A')}")
            
        print("  False Negatives (Gold standard expected these):")
        for fn in fns[:5]:
            print(f"    - Text: '{fn.get('value', fn.get('text', 'N/A'))}', Span/Tokens: {fn.get('span', fn.get('tokens', []))}, Type: {fn.get('type', 'N/A')}")
        count += 1
        
    if count >= 3:
        break
