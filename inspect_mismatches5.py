import json

path = '/home/neo/environments/textgraphx/textgraphx/datastore/evaluation/cycle_20260416T050808Z/eval_report_strict.json'
with open(path) as f:
    data = json.load(f)

print("Look at the strict layer array.")
for r in data.get('reports', [])[:2]:
    print(f"\nDoc:", r.get('doc_id'))
    if 'strict' in r and 'entity' in r['strict']:
        entity = r['strict']['entity']
        bm = entity.get('boundary_mismatch', [])
        tm = entity.get('type_mismatch', [])
        missing = entity.get('missing', [])
        spurious = entity.get('spurious', [])
        
        print("  Boundary Mismatches:", len(bm))
        for b in bm[:5]:
            print("    ", b)
            
        print("  Spurious (System made up):", len(spurious))
        for s in spurious[:5]:
            print("    ", s)
            
        print("  Missing (System missed entirely):", len(missing))
        for m in missing[:5]:
            print("    ", m)
