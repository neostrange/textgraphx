import json, glob, os
latest = max(glob.glob('textgraphx/datastore/evaluation/*/eval_report_strict.json'), key=os.path.getctime)
with open(latest, 'r') as f:
    report = json.load(f)

for r in report['reports']:
    fns = r['strict']['relation']['examples'].get('missing', [])
    fps = r['strict']['relation']['examples'].get('spurious', [])
    print(f"Doc {r['doc_id']} FN={len(fns)} FP={len(fps)}")
    if fns:
        print("  Missing examples:")
        for fn in fns[:2]:
            print(f"    {fn}")
    if fps:
        print("  Spurious examples:")
        for fp in fps[:2]:
            print(f"    {fp}")
