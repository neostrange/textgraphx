import json

path = '/home/neo/environments/textgraphx/textgraphx/datastore/evaluation/cycle_20260416T050808Z/eval_report_strict.json'
with open(path) as f:
    data = json.load(f)

print("Look at the relaxed layer array just to see where lists are.")
for r in data.get('reports', [])[:1]:
    for level in ['strict', 'relaxed']:
        print(f"\nLevel: {level}")
        for layer_k, layer_v in r.get(level, {}).items():
            for k, v in layer_v.items():
                if type(v) is list and len(v) > 0:
                     print(f"  {layer_k}.{k}: length {len(v)}")
                     print("   Example:", v[0])

# also look at data['aggregate']
print("\nAggregate dict keys:", list(data.get('aggregate', {}).keys()))

