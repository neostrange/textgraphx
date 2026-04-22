import json, glob, os
latest = max(glob.glob('textgraphx/datastore/evaluation/*/eval_report_strict.json'), key=os.path.getctime)
with open(latest, 'r') as f: report = json.load(f)
r = report['reports'][0]
print("Entity counts:", r['strict']['entity']['counts'])
