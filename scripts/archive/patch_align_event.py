with open("textgraphx/evaluation/meantime_evaluator.py", "r") as f:
    text = f.read()

import re
old_func = """def _align_relation_event_span(span: TokenSpan, event_mentions: Set[Mention]) -> TokenSpan:
    \"\"\"Align relation-side event span to the nearest projected event mention span.\"\"\"
    if not span or not event_mentions:
        return span

    mention_spans = [m.span for m in event_mentions if m.kind == "event"]
    if not mention_spans:
        return span
    if span in mention_spans:
        return span

    overlapping = [s for s in mention_spans if _span_iou(span, s) > 0.0]
    if not overlapping:
        return span

    return max(overlapping, key=lambda s: (_span_iou(span, s), len(s)))"""

new_func = """def _align_relation_event_span(span: TokenSpan, event_mentions: Set[Mention]) -> TokenSpan:
    \"\"\"Align relation-side event span to the nearest projected event mention span.\"\"\"
    if not span or not event_mentions:
        return span

    mention_spans = [m.span for m in event_mentions if m.kind == "event"]
    if not mention_spans:
        return span
    if span in mention_spans:
        return span

    overlapping = [s for s in mention_spans if _span_iou(span, s) > 0.0]
    if overlapping:
        return max(overlapping, key=lambda s: (_span_iou(span, s), len(s)))

    # If no overlap, find the closest event span within 3 tokens
    span_center = sum(span) / len(span)
    closest = min(mention_spans, key=lambda s: abs(span_center - sum(s)/len(s)))
    if abs(span_center - sum(closest)/len(closest)) <= 3:
        return closest
    return span"""

if old_func in text:
    text = text.replace(old_func, new_func)
    with open("textgraphx/evaluation/meantime_evaluator.py", "w") as f:
        f.write(text)
    print("Patched event align.")
else:
    print("Could not find old func.", file=sys.stderr)
