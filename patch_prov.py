with open("textgraphx/EventEnrichmentPhase.py", "r") as f:
    text = f.read()

old_block = """                    MERGE (fa)-[nr:EVENT_PARTICIPANT]->(event)
                    SET nr.type = fa.type,
                        nr.is_core = false
                    RETURN count(*) AS linked"""

new_block = """                    MERGE (fa)-[nr:EVENT_PARTICIPANT]->(event)
                    SET nr.type = fa.type,
                        (CASE WHEN fa.syntacticType IN ['IN'] THEN nr END).prep = fa.head,
                        nr.confidence = 0.60,
                        nr.evidence_source = 'event_enrichment',
                        nr.rule_id = 'participant_linking_non_core',
                        nr.authority_tier = 'secondary',
                        nr.source_kind = 'rule',
                        nr.conflict_policy = 'additive',
                        nr.created_at = coalesce(nr.created_at, datetime().epochMillis),
                        nr.is_core = false
                    RETURN count(*) AS linked"""

text = text.replace(old_block, new_block)
with open("textgraphx/EventEnrichmentPhase.py", "w") as f:
    f.write(text)
print("done")
