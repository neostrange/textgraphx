import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = ROOT / "src" / "textgraphx" / "datastore" / "evaluation"
latest_file = EVAL_DIR / "latest" / "eval_report_strict.json"
if not latest_file.exists():
    legacy = sorted(EVAL_DIR.glob("cycle_*/eval_report_strict.json"), key=os.path.getctime)
    if not legacy:
        raise FileNotFoundError("No strict evaluation report found under latest/ or legacy cycle directories")
    latest_file = legacy[-1]

print("Reading from:", latest_file)

with latest_file.open('r') as f:
    report = json.load(f)

def extract_spurious(obj, arr, kind):
    if isinstance(obj, dict):
        if obj.get("category") == "spurious" and "items" in obj:
            for item in obj["items"]:
                if item.get("kind") == kind:
                    arr.append(item)
                    if len(arr) > 20: return
        else:
            for v in obj.values():
                extract_spurious(v, arr, kind)
    elif isinstance(obj, list):
        for item in obj:
            extract_spurious(item, arr, kind)

entities = []
events = []
extract_spurious(report, entities, "entity")
extract_spurious(report, events, "event")

print("=== SPURIOUS ENTITIES ===")
for e in entities[:20]:
    print(" -", e)

print("\n=== SPURIOUS EVENTS ===")
for e in events[:20]:
    print(" -", e)
