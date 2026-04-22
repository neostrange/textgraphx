import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = ROOT / "src" / "textgraphx" / "datastore" / "evaluation"
latest = EVAL_DIR / "latest" / "eval_report_strict.json"
if not latest.exists():
    legacy = sorted(EVAL_DIR.glob("cycle_*/eval_report_strict.json"), key=os.path.getctime)
    if not legacy:
        raise FileNotFoundError("No strict evaluation report found under latest/ or legacy cycle directories")
    latest = legacy[-1]

with latest.open('r') as f:
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
