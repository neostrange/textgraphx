with open("textgraphx/evaluation/meantime_evaluator.py", "r") as f:
    text = f.read()

import re
old_align = """                if not evt_found:
                    continue"""

new_align = """                if not evt_found:
                    print(f"Skipping participant (evt_span not projected): {evt_span}", file=sys.stderr)
                    continue"""

text = text.replace(old_align, new_align)

with open("textgraphx/evaluation/meantime_evaluator.py", "w") as f:
    f.write(text)
