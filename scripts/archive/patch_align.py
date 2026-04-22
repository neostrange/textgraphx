with open("textgraphx/evaluation/meantime_evaluator.py", "r") as f:
    text = f.read()

import re
old_align = """                if evt_span not in frozenset(m.span for m in doc.event_mentions):
                    print(f"Skipping participant (evt_span not projected): original={evt_start}-{evt_end} aligned={evt_span}", file=sys.stderr)
                    continue"""

new_align = """                evt_found = False
                for ev in doc.event_mentions:
                    if set(evt_span).intersection(ev.span):
                        evt_span = ev.span
                        evt_found = True
                        break
                if not evt_found:
                    print(f"Skipping participant (evt_span not projected): original={evt_start}-{evt_end} aligned={evt_span}", file=sys.stderr)
                    continue"""

text = text.replace(old_align, new_align)

old_align2 = """                    if evt_span not in frozenset(m.span for m in doc.event_mentions):
                        continue"""

new_align2 = """                    evt_found = False
                    for ev in doc.event_mentions:
                        if set(evt_span).intersection(ev.span):
                            evt_span = ev.span
                            evt_found = True
                            break
                    if not evt_found:
                        continue"""

text = text.replace(old_align2, new_align2)

with open("textgraphx/evaluation/meantime_evaluator.py", "w") as f:
    f.write(text)
