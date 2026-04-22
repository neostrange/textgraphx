with open("textgraphx/evaluation/meantime_evaluator.py", "r") as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if l.startswith("def _align_relation_event_span("):
        print(f"Line {i}:", "".join(lines[i:i+20]))
        break
