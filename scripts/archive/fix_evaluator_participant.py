with open('textgraphx/evaluation/meantime_evaluator.py', 'r') as f:
    text = f.read()

old_code = """
        entity_span = _span_from_bounds(int(row["src_start"]), int(row["src_end"]), token_index_alignment)
        entity_span = _align_relation_entity_span(entity_span, doc.entity_mentions)
        sem_role = _normalize_sem_role(row.get("sem_role"))
        doc.relations.add(
            Relation(
"""

new_code = """
        entity_span = _span_from_bounds(int(row["src_start"]), int(row["src_end"]), token_index_alignment)
        entity_span = _align_relation_entity_span(entity_span, doc.entity_mentions)
        if entity_span not in frozenset(m.span for m in doc.entity_mentions):
            continue
        sem_role = _normalize_sem_role(row.get("sem_role"))
        doc.relations.add(
            Relation(
"""
if old_code in text:
    with open('textgraphx/evaluation/meantime_evaluator.py', 'w') as f:
        f.write(text.replace(old_code, new_code))
    print("Replaced.")
else:
    print("Not found.")
