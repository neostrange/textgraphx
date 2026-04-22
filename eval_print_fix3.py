import json
import glob
import os

with open(max(glob.glob('textgraphx/datastore/evaluation/*/eval_report_strict.json'), key=os.path.getctime), 'r') as f:
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
