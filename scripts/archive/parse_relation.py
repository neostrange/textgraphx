import json

path = '/home/neo/environments/textgraphx/textgraphx/datastore/evaluation/cycle_20260416T050808Z/eval_report_strict.json'
with open(path) as f:
    data = json.load(f)

micro = data.get('aggregate', {}).get('micro', {})
print("Relation node:", micro.get('strict', {}).get('relation'))
print("Timex:", micro.get('strict', {}).get('timex'))

