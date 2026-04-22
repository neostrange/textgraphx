import os, json, glob
latest = max(glob.glob('textgraphx/datastore/evaluation/*/eval_report_strict.json'), key=os.path.getctime)
with open(latest, 'r') as f:
    report = json.load(f)
print(json.dumps(report['reports'][0]['strict']['relation'], indent=2))
