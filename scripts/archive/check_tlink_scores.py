import json

path = '/home/neo/environments/textgraphx/textgraphx/datastore/evaluation/cycle_20260416T050808Z/eval_report_strict.json'
try:
    with open(path) as f:
        data = json.load(f)
    
    print("Aggregate TLINK scores:")
    agg = data.get('aggregate', {})
    if 'strict' in agg and 'tlink' in agg['strict']:
        print(agg['strict']['tlink'])
    else:
        print("Not found in strict")
        
except Exception as e:
    print("Error:", e)
