with open('textgraphx/evaluation/meantime_evaluator.py', 'r') as f:
    text = f.read()

old_scoring = """    gold_keys = {_relation_key(r, mode) for r in gold_relations}
    pred_keys = {_relation_key(r, mode) for r in predicted_relations}

    tp = len(gold_keys & pred_keys)
    fp = len(pred_keys - gold_keys)
    fn = len(gold_keys - pred_keys)
    out = precision_recall_f1(tp=tp, fp=fp, fn=fn)
    out["mode"] = mode
    out["errors"] = _bucket_relation_errors(gold_keys, pred_keys)
    out["examples"] = _collect_relation_examples(gold_keys, pred_keys, max_examples=max_examples)
    return out"""

new_scoring = """    if mode == "strict":
        gold_keys = {_relation_key(r, "strict"): r for r in gold_relations}
        pred_keys = {_relation_key(r, "strict"): r for r in predicted_relations}
        
        tp_keys = set(gold_keys.keys()) & set(pred_keys.keys())
        tp = len(tp_keys)
        fp = len(pred_keys) - tp
        fn = len(gold_keys) - tp
        
        out = precision_recall_f1(tp=tp, fp=fp, fn=fn)
        out["mode"] = "strict"
        out["errors"] = _bucket_relation_errors(set(gold_keys.keys()), set(pred_keys.keys()))
        out["examples"] = _collect_relation_examples(set(gold_keys.keys()), set(pred_keys.keys()), max_examples=max_examples)
        return out
        
    else:  # Relaxed Mode
        matched_gold = set()
        matched_pred = set()
        tp_pairs = []
        
        for g in gold_relations:
            for p in predicted_relations:
                if p in matched_pred: continue
                
                # In relaxed mode, relations match if:
                # 1. Kinds match (e.g. has_participant == has_participant)
                # 2. Source kinds match, and source spans OVERLAP
                # 3. Target kinds match, and target spans OVERLAP
                # 4. Canonicalized reltype (if applicable) matches
                
                if g.kind != p.kind: continue
                if g.source_kind != p.source_kind or g.target_kind != p.target_kind: continue
                
                # Check overlapping endpoints
                if _span_iou(g.source_span, p.source_span) == 0.0: continue
                if _span_iou(g.target_span, p.target_span) == 0.0: continue
                
                # Check attributes (in relaxed, only reltype matters if present)
                g_reltype = dict(g.attrs).get("reltype")
                p_reltype = dict(p.attrs).get("reltype")
                if g_reltype != p_reltype: continue
                
                matched_gold.add(g)
                matched_pred.add(p)
                tp_pairs.append({'gold': str(_relation_key(g, "strict")), 'predicted': str(_relation_key(p, "strict"))})
                break
                
        tp = len(matched_gold)
        fp = len(predicted_relations) - tp
        fn = len(gold_relations) - tp
        
        # Prepare examples format
        unmatched_gold = [str(_relation_key(g, "strict")) for g in gold_relations if g not in matched_gold]
        unmatched_pred = [str(_relation_key(p, "strict")) for p in predicted_relations if p not in matched_pred]
        
        out = precision_recall_f1(tp=tp, fp=fp, fn=fn)
        out["mode"] = "relaxed"
        out["errors"] = {"relaxed_mismatch": fp}
        out["examples"] = {
            "matched_pairs": tp_pairs[:max_examples] if max_examples else tp_pairs,
            "missing": [{"gold": g} for g in unmatched_gold[:max_examples] if max_examples] if max_examples else [{"gold": g} for g in unmatched_gold],
            "spurious": [{"predicted": p} for p in unmatched_pred[:max_examples] if max_examples] if max_examples else [{"predicted": p} for p in unmatched_pred]
        }
        return out"""

if old_scoring in text:
    with open('textgraphx/evaluation/meantime_evaluator.py', 'w') as f:
        f.write(text.replace(old_scoring, new_scoring))
    print("Replaced Relation Scoring for Relaxed mode")
else:
    print("FAILED TO FIND OLD")
