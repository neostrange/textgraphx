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
r = report['reports'][0]
print(list(r['strict']['entity']['counts']))
