import json

path = '/home/neo/environments/textgraphx/textgraphx/datastore/evaluation/cycle_20260416T050808Z/eval_report_strict.json'
with open(path) as f:
    data = json.load(f)

print(len(data.get('reports', [])))
if len(data.get('reports', [])) > 0:
    for n in range(3):
        print("\n", data['reports'][n].keys())
        print("  strict keys:", data['reports'][n].get('strict', {}).keys())
        if 'strict' in data['reports'][n]:
            print("  event keys:", data['reports'][n]['strict'].get('event', {}).keys())
