import re
with open("textgraphx/evaluation/meantime_evaluator.py", "r") as f:
    text = f.read()

def replacer(match):
    kind = match.group(1)
    return f"""def _align_relation_{kind}_span(span, mentions):
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

pattern = re.compile(r'def _align_relation_([a-z]+)_span\(.*?return max\(.*?\)\s*', re.DOTALL)
text = pattern.sub(replacer, text)

# Just run brute force sub over the whole thing just in case it didn't match the max(...).
# But since I changed event earlier, I'll just write it manually for all 3.

with open("textgraphx/evaluation/meantime_evaluator.py", "w") as f:
    f.write(text)
