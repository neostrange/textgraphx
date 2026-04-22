import json
import sys

try:
    with open('eval_report_strict.json', 'r') as f:
        report = json.load(f)

    scorecards = report.get('scorecards', {})
    aggregate = scorecards.get('aggregate', {})
    
    print("--- SCORES ---")
    for entity_type in ['entity', 'event', 'timex']:
        stats = aggregate.get(entity_type, {})
        if stats:
            tp, fp, fn = stats.get('tp', 0), stats.get('fp', 0), stats.get('fn', 0)
            precision = tp / (tp + fp) if tp + fp > 0 else 0
            recall = tp / (tp + fn) if tp + fn > 0 else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
            print(f"{entity_type.upper():<7}: F1={f1:.3f} | P={precision:.3f} | R={recall:.3f} | (TP:{tp} FP:{fp} FN:{fn})")

    # Spurious Examples
    entities = []
    events = []
    
    for doc_id, doc_stats in scorecards.get("document_scorecards", {}).items():
        if "entity" in doc_stats and "spurious" in doc_stats["entity"]:
            entities.extend([f"Span: {e.get('span')} Attrs:{e.get('attrs')}" for e in doc_stats["entity"]["spurious"]])
        if "event" in doc_stats and "spurious" in doc_stats["event"]:
            events.extend([f"Span: {e.get('span')} Attrs:{e.get('attrs')} Pred:{e.get('attrs', {}).get('pred')}" for e in doc_stats["event"]["spurious"]])

    print(f"\n--- REMAINING SPURIOUS ENTITIES ({len(entities)}) ---")
    for e in entities[:10]: print(" -", e)

    print(f"\n--- REMAINING SPURIOUS EVENTS ({len(events)}) ---")
    for e in events[:10]: print(" -", e)

except Exception as e:
    print("Error:", e)
