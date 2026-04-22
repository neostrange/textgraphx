with open("textgraphx/evaluation/meantime_evaluator.py", "r") as f:
    text = f.read()

import re
old_align = """    print(f"DOC {doc_id_int} participant_rows count: {len(participant_rows)}", file=sys.stderr)"""

new_align = """    print(f"DOC {doc_id_int} participant_rows count: {len(participant_rows)}", file=sys.stderr)"""

if old_align not in text:
    old_align2 = """    for row in participant_rows:"""
    new_align2 = """    print(f"DOC {doc_id_int} participant_rows count: {len(participant_rows)}", file=sys.stderr)
    for row in participant_rows:"""
    text = text.replace(old_align2, new_align2)

with open("textgraphx/evaluation/meantime_evaluator.py", "w") as f:
    f.write(text)
