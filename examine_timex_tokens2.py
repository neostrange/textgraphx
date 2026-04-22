import json
import glob
import os
latest = max(glob.glob('textgraphx/datastore/evaluation/*/eval_report_strict.json'), key=os.path.getctime)
with open(latest, 'r') as f:
    report = json.load(f)
for r in report['reports']:
    fns = r['strict']['timex']['examples'].get('false_negatives', [])
    fps = r['strict']['timex']['examples'].get('false_positives', [])
    for fn in fns[:2]: 
        print(fn)
    for fp in fps[:2]:
        print(fp)
