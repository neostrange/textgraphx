import json

path = '/home/neo/environments/textgraphx/textgraphx/datastore/evaluation/cycle_20260416T050808Z/eval_report_strict.json'
with open(path) as f:
    data = json.load(f)

print("Look at the strict layer array.")
for r in data.get('reports', [])[:2]:
    print(f"\nDoc:", r.get('doc_id'))
    if 'strict' in r and 'entity' in r['strict']:
        print("keys", r['strict'].keys())
        for layer_k, layer_v in r['strict'].items():
            print(f"Layer {layer_k}")
            if type(layer_v) is dict:
                for k, v in layer_v.items():
                    if type(v) is list and len(v) > 0:
                         print(f"  {k}: length {len(v)}")
                         for i in range(min(3, len(v))):
                             print("   ", v[i])
