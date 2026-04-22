import json

def process(f1):
    with open(f1) as f: d1 = json.load(f)

    # print
    print(f"===========================================================")
    print(f"BATCH METRICS - MEANTIME GOLDEN ALIGNED")
    print(f"Documents Evaluated: {d1.get('aggregate', {}).get('documents')}")
    print(f"===========================================================")
    print("")
    macro1 = d1.get("aggregate", {}).get("relation_by_kind", {}).get("micro", {}).get("strict", {})

    print(f"--- RELATIONS (STRICT MICRO) ---")
    for k in sorted(list(macro1.keys())):
        m1 = macro1.get(k, {})
        f1_score = m1.get("f1", 0)
        tp = m1.get('tp',0)
        fp = m1.get('fp',0)
        fn = m1.get('fn',0)
        print(f"[{k}] F1: {f1_score:.4f} (TP: {tp}, FP: {fp}, FN: {fn})")
        
    print(f"\n--- RELATIONS (RELAXED MICRO) ---")
    macro_rlx = d1.get("aggregate", {}).get("relation_by_kind", {}).get("micro", {}).get("relaxed", {})
    for k in sorted(list(macro_rlx.keys())):
        m1 = macro_rlx.get(k, {})
        f1_score = m1.get("f1", 0)
        tp = m1.get('tp',0)
        fp = m1.get('fp',0)
        fn = m1.get('fn',0)
        print(f"[{k}] F1: {f1_score:.4f} (TP: {tp}, FP: {fp}, FN: {fn})")

    print(f"\n--- NODES (STRICT MACRO) ---")
    macro_nodes = d1.get("aggregate", {}).get("macro", {}).get("strict", {})
    for node_type in ['entity', 'event', 'timex']:
        m1 = macro_nodes.get(node_type, {})
        f1_score = m1.get("f1", 0)
        print(f"[{node_type}] F1: {f1_score:.4f} (Recall: {m1.get('recall',0):.4f}, Precision: {m1.get('precision',0):.4f})")

process("textgraphx/datastore/evaluation/eval_batch_baseline.json")
