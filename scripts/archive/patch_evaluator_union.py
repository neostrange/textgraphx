import re
with open("textgraphx/evaluation/meantime_evaluator.py", "r") as f:
    text = f.read()

# We comment out the UNION part for has_participant
start_idx = text.find("UNION\n            WITH $doc_id AS doc_id")
if start_idx != -1:
    end_idx = text.find("        }", start_idx)
    if end_idx != -1:
        # replace the union block with empty
        new_text = text[:start_idx] + text[end_idx:]
        with open("textgraphx/evaluation/meantime_evaluator.py", "w") as f:
            f.write(new_text)
        print("Removed UNION block")
