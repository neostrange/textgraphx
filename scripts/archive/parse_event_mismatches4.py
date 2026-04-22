import json

path = '/home/neo/environments/textgraphx/textgraphx/datastore/evaluation/cycle_20260416T050808Z/eval_report_strict.json'
with open(path) as f:
    data = json.load(f)

for r in data.get('reports', [])[:2]:
    doc_id = r.get('doc_id')
    print(f"\nDoc: {doc_id}")
    if 'strict' in r and 'event' in r['strict']:
        print(r['strict']['event'].keys())
