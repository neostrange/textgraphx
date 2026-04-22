import json
try:
    with open('eval_report_strict.json', 'r') as f:
        report = json.load(f)

    scorecards = report.get('scorecards', {})
    
    spurious = []
    
    for doc_id, doc_stats in scorecards.get("document_scorecards", {}).items():
        if "entity" in doc_stats and "spurious" in doc_stats["entity"]:
            spurious.extend([f"Doc:{doc_id} Entity:{e.get('attrs')}" for e in doc_stats["entity"]["spurious"]])
        if "event" in doc_stats and "spurious" in doc_stats["event"]:
            spurious.extend([f"Doc:{doc_id} Event:{e.get('attrs', {}).get('pred', '')}" for e in doc_stats["event"]["spurious"]])

    print(f"\n--- REMAINING SPURIOUS EXAMPLES ({len(spurious)}) ---")
    for e in spurious[:30]: print(" -", e)

except Exception as e:
    print("Error:", e)
