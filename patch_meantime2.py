import re

with open('textgraphx/evaluation/meantime_evaluator.py', 'r') as f:
    content = f.read()

content = content.replace(
    "WHERE (m:EntityMention OR m:NamedEntity OR m:CorefMention) {_entity_discourse_clause}",
    "WHERE (m:EntityMention OR m:NamedEntity OR m:CorefMention) {_entity_discourse_clause}\n           AND coalesce(m.is_timeml_core, true) = true"
)

with open('textgraphx/evaluation/meantime_evaluator.py', 'w') as f:
    f.write(content)
