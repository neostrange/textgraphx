with open("textgraphx/evaluation/meantime_evaluator.py", "r") as f:
    text = f.read()

import re
old_align = """        if raw_entity_span not in projected_entity_spans:
            continue"""

new_align = """        if raw_entity_span not in projected_entity_spans:
            print(f"Skipping participant (entity_span not projected): {raw_entity_span}", file=sys.stderr)
            continue"""

text = text.replace(old_align, new_align)

with open("textgraphx/evaluation/meantime_evaluator.py", "w") as f:
    f.write(text)
