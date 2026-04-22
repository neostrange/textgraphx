import json, glob, os
latest = max(glob.glob('textgraphx/datastore/evaluation/*/eval_report_strict.json'), key=os.path.getctime)
with open(latest, 'r') as f:
    report = json.load(f)
r = report['reports'][0] # doc 112579
pms = [m['span'] for m in r['pred_documents'][r['doc_id']]['mentions'] if m['kind'] == 'event']
print(pms)
