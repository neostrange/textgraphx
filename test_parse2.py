import json

path = '/home/neo/environments/textgraphx/textgraphx/datastore/evaluation/cycle_20260416T050808Z/eval_report_strict.json'
with open(path) as f:
    data = json.load(f)

for x in data.get('reports', [])[:2]:
    print("Doc", x.get('doc_id'))
    if 'event' in x:
        print("  event keys:", x['event'].keys())
    if 'strict' in x:
        print("  strict event:", x['strict'].get('event', {}).keys())
        if 'examples' in x['strict'].get('event', {}):
             print("  strict event examples:", x['strict']['event']['examples'].keys())
