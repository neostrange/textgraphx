with open('textgraphx/EventEnrichmentPhase.py', 'r') as f:
    text = f.read()

# Add is_core = true to core_participants
old_core = """                        r.created_at = coalesce(r.created_at, datetime().epochMillis)
                    merge (e)-[nr:EVENT_PARTICIPANT]->(event)
                    set nr.type = fa.type,"""
new_core = """                        r.created_at = coalesce(r.created_at, datetime().epochMillis),
                        r.is_core = true
                    merge (e)-[nr:EVENT_PARTICIPANT]->(event)
                    set nr.type = fa.type,
                        nr.is_core = true,"""
text = text.replace(old_core, new_core)

# Add is_core = false to non_core_participants
old_non_core = """                        r.created_at = coalesce(r.created_at, datetime().epochMillis)
                    MERGE (fa)-[nr:EVENT_PARTICIPANT]->(event)
                    SET nr.type = fa.type,"""
new_non_core = """                        r.created_at = coalesce(r.created_at, datetime().epochMillis),
                        r.is_core = false
                    MERGE (fa)-[nr:EVENT_PARTICIPANT]->(event)
                    SET nr.type = fa.type,
                        nr.is_core = false,"""
text = text.replace(old_non_core, new_non_core)

with open('textgraphx/EventEnrichmentPhase.py', 'w') as f:
    f.write(text)
