import json

path = '/home/neo/environments/textgraphx/textgraphx/datastore/evaluation/cycle_20260416T050808Z/eval_report_strict.json'
with open(path) as f:
    data = json.load(f)

print("Look at the strict layer examples.")
for r in data.get('reports', [])[:5]:
    if 'strict' in r and 'entity' in r['strict']:
        entity = r['strict']['entity']
        bm = entity.get('examples', {}).get('boundary_mismatch', [])
        tm = entity.get('examples', {}).get('type_mismatch', [])
        
        if bm:
            print(f"\nDoc: {r.get('doc_id')}")
            print("  Boundary Mismatches (Top 5):")
            for b in bm[:5]:
                print(f"    - GOLD:   {b.get('gold', {}).get('text')}")
                print(f"    - SYSTEM: {b.get('system', {}).get('text')}")
                print(f"    - Gold Span: {b.get('gold', {}).get('span')} | System Span: {b.get('system', {}).get('span')}\n")
