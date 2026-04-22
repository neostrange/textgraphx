
import json
with open("eval_report_strict.json", "r") as f:
    report = json.load(f)

for entity_type in ["entity", "event"]:
    print(f"\n{entity_type.upper()}:")
    stats = report.get(entity_type, {})
    print(f"  TP: {stats.get(\"tp\", 0)}, FP: {stats.get(\"fp\", 0)}, FN: {stats.get(\"fn\", 0)}")
    spurious = stats.get("spurious", [])
    print(f"  Spurious ({len(spurious)}):")
    for s in spurious[:5]:
        print(f"    - {s}")

