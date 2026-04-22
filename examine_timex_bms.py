import json
import glob
import os

latest = max(glob.glob('textgraphx/datastore/evaluation/*/eval_report_strict.json'), key=os.path.getctime)
with open(latest, 'r') as f:
    report = json.load(f)

print("TIMEX Boundary Mismatches:")
for r in report['reports']:
    bms = r['strict']['timex']['examples'].get('boundary_mismatch', [])
    for bm in bms:
        print("  Pred:", bm['predicted']['span'], "Gold:", bm['gold']['span'])
