with open('textgraphx/evaluation/meantime_evaluator.py', 'r') as f:
    text = f.read()

old_tlink_filter_1 = """        if src_kind == "event":
            src_span = _align_relation_event_span(src_span, doc.event_mentions)
        if tgt_kind == "event":
            tgt_span = _align_relation_event_span(tgt_span, doc.event_mentions)
        if src_kind == "timex":
            src_span = _align_relation_timex_span(src_span, doc.timex_mentions)
        if tgt_kind == "timex":
            tgt_span = _align_relation_timex_span(tgt_span, doc.timex_mentions)
        if (src_kind == "event" or tgt_kind == "event") and not projected_event_spans:
            continue
        doc.relations.add("""

new_tlink_filter_1 = """        if src_kind == "event":
            src_span = _align_relation_event_span(src_span, doc.event_mentions)
            if src_span not in frozenset(m.span for m in doc.event_mentions): continue
        if tgt_kind == "event":
            tgt_span = _align_relation_event_span(tgt_span, doc.event_mentions)
            if tgt_span not in frozenset(m.span for m in doc.event_mentions): continue
        if src_kind == "timex":
            src_span = _align_relation_timex_span(src_span, doc.timex_mentions)
            if src_span not in frozenset(m.span for m in doc.timex_mentions): continue
        if tgt_kind == "timex":
            tgt_span = _align_relation_timex_span(tgt_span, doc.timex_mentions)
            if tgt_span not in frozenset(m.span for m in doc.timex_mentions): continue
        doc.relations.add("""

if old_tlink_filter_1 in text:
    with open('textgraphx/evaluation/meantime_evaluator.py', 'w') as f:
        f.write(text.replace(old_tlink_filter_1, new_tlink_filter_1))
    print("Replaced.")
else:
    print("Not found.")
