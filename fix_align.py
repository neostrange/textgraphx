with open('textgraphx/evaluation/meantime_evaluator.py', 'r') as f:
    text = f.read()

import re

def rewrite(func_name, kind):
    return f"""def {func_name}(span: TokenSpan, mentions: Set[Mention]) -> TokenSpan:
    if not span or not mentions: return span
    mention_spans = [m.span for m in mentions if m.kind == "{kind}"]
    if not mention_spans: return span
    if span in mention_spans: return span
    overlapping = [s for s in mention_spans if set(span).intersection(s)]
    if overlapping: return max(overlapping, key=lambda s: len(set(span).intersection(s)))
    span_center = sum(span) / len(span)
    closest = min(mention_spans, key=lambda s: abs(span_center - sum(s)/len(s)))
    if abs(span_center - sum(closest)/len(closest)) <= 5: return closest
    return span
"""

t1 = rewrite("_align_relation_event_span", "event")
t2 = rewrite("_align_relation_entity_span", "entity")
t3 = rewrite("_align_relation_timex_span", "timex3")

start_idx = text.find('def _align_relation_event_span')
end_idx = text.find('def _normalize_sem_role(', start_idx)

new_text = text[:start_idx] + t1 + "\n" + t2 + "\n" + t3 + "\n\n" + text[end_idx:]

with open('textgraphx/evaluation/meantime_evaluator.py', 'w') as f:
    f.write(new_text)
