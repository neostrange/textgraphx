with open('textgraphx/evaluation/meantime_evaluator.py', 'r') as f:
    text = f.read()

# Make sure all events are pulled by the best_head match for TLINK too
import re

old_tlink = """                  coalesce(a.start_tok, a.begin, a_tok_start) AS a_start,
                  coalesce(a.end_tok, a.end, a_tok_end) AS a_end,
                  labels(b) AS target_labels,
                  coalesce(b.start_tok, b.begin, b_tok_start) AS b_start,
                  coalesce(b.end_tok, b.end, b_tok_end) AS b_end,"""

# Actually, the quickest way to fix the tlink endpoints is adding the same alignment in python! We already added the alignment function back:
# `tgt_span = _align_relation_event_span(tgt_span, doc.event_mentions)`
