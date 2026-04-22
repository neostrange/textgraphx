with open("textgraphx/evaluation/meantime_evaluator.py", "r") as f:
    text = f.read()

old_1 = "MATCH (tok)-[:IN_MENTION|PARTICIPATES_IN]->(m)\n        WHERE (m:EntityMention OR m:NamedEntity OR m:NominalMention OR m:CorefMention OR m:Entity OR m:Concept) {_entity_discourse_clause}"
new_1 = "MATCH (tok)-[:IN_MENTION|PARTICIPATES_IN|IN_FRAME]->(m)\n        WHERE (m:EntityMention OR m:NamedEntity OR m:NominalMention OR m:CorefMention OR m:Entity OR m:Concept OR m:FrameArgument) {_entity_discourse_clause}"

text = text.replace(old_1, new_1)
with open("textgraphx/evaluation/meantime_evaluator.py", "w") as f:
    f.write(text)

