import os
import json
import glob

latest = max(glob.glob('textgraphx/datastore/evaluation/*/eval_report_strict.json'), key=os.path.getctime)
with open(latest, 'r') as f:
    report = json.load(f)

for r in report['reports']:
    for rel_kind in ['tlink', 'alink']:
        if rel_kind not in r['strict']:
            continue
        counts = r['strict'][rel_kind].get('counts', {})
        false_negatives = len(r['strict'][rel_kind]['examples'].get('false_negatives', []))
        false_positives = len(r['strict'][rel_kind]['examples'].get('false_positives', []))
        print(f"Doc {r['doc_id']} [{rel_kind}]: counts {counts}, FN={false_negatives}, FP={false_positives}")

        fns = r['strict'][rel_kind]['examples'].get('false_negatives', [])
        fps = r['strict'][rel_kind]['examples'].get('false_positives', [])
        if fns:
            print(f"  Sample FN ({rel_kind}):")
            for fn in fns[:2]:
                print(f"   {fn}")
        if fps:
            print(f"  Sample FP ({rel_kind}):")
            for fp in fps[:2]:
                print(f"   {fp}")

