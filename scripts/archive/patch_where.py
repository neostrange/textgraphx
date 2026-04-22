with open("textgraphx/evaluation/meantime_evaluator.py", "r") as f:
    text = f.read()

old_where = "WHERE mention:NamedEntity OR mention:EntityMention OR mention:CorefMention OR mention:Concept"
new_where = "WHERE mention IS NULL OR mention:NamedEntity OR mention:EntityMention OR mention:CorefMention OR mention:Concept OR mention:NominalMention"

text = text.replace(old_where, new_where)
with open("textgraphx/evaluation/meantime_evaluator.py", "w") as f:
    f.write(text)
