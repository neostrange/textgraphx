import os, json, glob
latest = max(glob.glob('textgraphx/datastore/evaluation/*/eval_report_strict.json'), key=os.path.getctime)
with open(latest, 'r') as f:
    report = json.load(f)
r = report['reports'][0]
print(json.dumps(r['strict']['relation']['examples'].get('missing', [])[:3], indent=2))
print(json.dumps(r['strict']['relation']['examples'].get('spurious', [])[:3], indent=2))
