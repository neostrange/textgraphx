import json

path = '/home/neo/environments/textgraphx/textgraphx/datastore/evaluation/cycle_20260416T050808Z/eval_report_strict.json'
try:
    with open(path) as f:
        data = json.load(f)
    print("KEYS:", data.get('aggregate', {}).get('strict', {}).keys())
    print("RELATION:", data.get('aggregate', {}).get('strict', {}).get('relation'))
except Exception as e:
    print("Error:", e)
