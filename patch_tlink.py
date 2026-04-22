with open("textgraphx/evaluation/meantime_evaluator.py", "r") as f:
    text = f.read()

old_tlink = """        if tgt_kind == "timex":
            tgt_span = _align_relation_timex_span(tgt_span, doc.timex_mentions)
            pass
        
        print(f"ADDING TLINK: src={src_kind}:{src_span} tgt={tgt_kind}:{tgt_span} rel={row.get('reltype')}", file=sys.stderr)
        doc.relations.add("""

new_tlink = """        if tgt_kind == "timex":
            tgt_span = _align_relation_timex_span(tgt_span, doc.timex_mentions)
            pass
            
        if (src_kind == "event" and src_span not in projected_event_spans) or (tgt_kind == "event" and tgt_span not in projected_event_spans):
            continue
        
        print(f"ADDING TLINK: src={src_kind}:{src_span} tgt={tgt_kind}:{tgt_span} rel={row.get('reltype')}", file=sys.stderr)
        doc.relations.add("""

text = text.replace(old_tlink, new_tlink)

old_glink = """        if tgt_kind == "timex":
            tgt_span = _align_relation_timex_span(tgt_span, doc.timex_mentions)
            pass
        doc.relations.add("""

new_glink = """        if tgt_kind == "timex":
            tgt_span = _align_relation_timex_span(tgt_span, doc.timex_mentions)
            pass
        if (src_kind == "event" and src_span not in projected_event_spans) or (tgt_kind == "event" and tgt_span not in projected_event_spans):
            continue
        doc.relations.add("""

text = text.replace(old_glink, new_glink)


with open("textgraphx/evaluation/meantime_evaluator.py", "w") as f:
    f.write(text)
print("done")
