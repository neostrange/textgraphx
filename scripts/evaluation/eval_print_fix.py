import json
import sys

try:
    with open('eval_report_strict.json', 'r') as f:
        report = json.load(f)

    # Walk the dictionary specifically looking for 'entity' and 'event' objects with 'spurious' keys
    entities = []
    events = []

    def extract_spurious(obj):
        if not isinstance(obj, dict):
            return
        for k, v in obj.items():
            if k == 'entity' and isinstance(v, dict) and 'spurious' in v:
                entities.extend(v['spurious'])
            elif k == 'event' and isinstance(v, dict) and 'spurious' in v:
                events.extend(v['spurious'])
            elif isinstance(v, dict):
                extract_spurious(v)
            elif isinstance(v, list):
                for item in v:
                    extract_spurious(item)

    extract_spurious(report)
    
    print("Spurious Entities:")
    for e in entities[:10]: print(f" - {e}")
    print("\nSpurious Events:")
    for e in events[:10]: print(f" - {e}")
    
except Exception as e:
    print("Error:", e)
