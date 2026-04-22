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

entities = []
events = []

def extract(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == 'entity' and isinstance(v, dict) and 'examples' in v and 'spurious' in v['examples']:
                for s in v['examples']['spurious']:
                    entities.append(s.get('predicted', {}))
            elif k == 'event' and isinstance(v, dict) and 'examples' in v and 'spurious' in v['examples']:
                for s in v['examples']['spurious']:
                    events.append(s.get('predicted', {}))
            else:
                extract(v)
    elif isinstance(obj, list):
        for item in obj:
            extract(item)

extract(report)

print("=== SPURIOUS ENTITIES ===")
for e in entities[:20]: print(f" - {e}")
print("\n=== SPURIOUS EVENTS ===")
for e in events[:20]: print(f" - {e}")
