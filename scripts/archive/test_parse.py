import json

path = '/home/neo/environments/textgraphx/textgraphx/datastore/evaluation/cycle_20260416T050808Z/eval_report_strict.json'
with open(path) as f:
    data = json.load(f)

for x in data.get('diagnostics', [])[:5]:
    print(x)
print("----------")
print(data.keys())
print("Aggregate:", data.get('aggregate', {}).keys())
print("Reports?", 'reports' in data)

