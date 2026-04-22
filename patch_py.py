with open("textgraphx/evaluation/meantime_evaluator.py", "r") as f:
    text = f.read()

import re
p = r"def _align_relation_event_span.*?return span\n\n\n"
new_func = """def _align_relation_event_span(span, event_mentions):
    if not span or not event_mentions:
        return span
    mention_spans = [m.span for m in event_mentions if m.kind == "event"]
    if not mention_spans: return span
    if span in mention_spans: return span
    overlapping = [s for s in mention_spans if set(span).intersection(s)]
    if overlapping:
        return max(overlapping, key=lambda s: len(set(span).intersection(s)))
    
    span_center = sum(span) / len(span)
    closest = min(mention_spans, key=lambda s: abs(span_center - sum(s)/len(s)))
    if abs(span_center - sum(closest)/len(closest)) <= 5:
        return closest
    return span


"""
text = re.sub(p, new_func, text, flags=re.DOTALL)
with open("textgraphx/evaluation/meantime_evaluator.py", "w") as f:
    f.write(text)
