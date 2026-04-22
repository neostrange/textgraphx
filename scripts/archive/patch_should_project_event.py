with open("textgraphx/evaluation/meantime_evaluator.py", "r") as f:
    text = f.read()

old = """def _should_project_event(attrs: Tuple[Tuple[str, str], ...]) -> bool:
    return True"""
new = """def _should_project_event(attrs: Tuple[Tuple[str, str], ...]) -> bool:
    for k, v in attrs:
        if k == "pred" and v in _AUXILIARY_EVENT_LEMMAS:
            return False
    return True"""

text = text.replace(old, new)
with open("textgraphx/evaluation/meantime_evaluator.py", "w") as f:
    f.write(text)
print("done")
