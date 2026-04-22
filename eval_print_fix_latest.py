import json
import glob
import os

latest_file = max(glob.glob('textgraphx/datastore/evaluation/*/eval_report_strict.json'), key=os.path.getctime)
print("Reading from:", latest_file)

with open(latest_file, 'r') as f:
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
