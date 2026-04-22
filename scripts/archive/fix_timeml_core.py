with open('textgraphx/EventEnrichmentPhase.py', 'r') as f:
    text = f.read()

old_query = """        WITH em, toLower(em.pred) AS lemma, coalesce(em.pos, '') AS pos
        SET em.is_timeml_core = CASE
            WHEN pos STARTS WITH 'VB' AND lemma IN ['be', 'have', 'do', 'become', 'remain', 'seem', 'look', 'appear', 'continue', 'indicate', 'accord', 'follow', 'say', 'tell', 'report', 'suggest', 'state', 'think', 'find', 'expect', 'believe', 'know', 'consider'] THEN false
            WHEN pos STARTS WITH 'NN' AND lemma IN ['market', 'index', 'inflation', 'power', 'job', 'number', 'system', 'value', 'price', 'percent', 'percentage', 'share', 'fund', 'point', 'level', 'rate', 'record', 'economy', 'growth', 'month', 'year', 'day', 'week'] THEN false
            ELSE true
        END"""

new_query = """        WITH em, toLower(coalesce(em.pred, '')) AS raw_pred, coalesce(em.pos, '') AS pos
        WITH em, split(raw_pred, ' ')[0] AS lemma, pos
        SET em.is_timeml_core = CASE
            WHEN pos STARTS WITH 'VB' AND lemma IN ['be', 'is', 'was', 'are', 'were', 'been', 'being', 'have', 'has', 'had', 'having', 'do', 'does', 'did', 'done', 'doing', 'become', 'becomes', 'became', 'becoming', 'remain', 'remains', 'remained', 'remaining', 'seem', 'seems', 'seemed', 'seeming', 'look', 'looks', 'looked', 'looking', 'appear', 'appears', 'appeared', 'appearing', 'continue', 'continues', 'continued', 'continuing', 'indicate', 'indicates', 'indicated', 'indicating', 'accord', 'accords', 'accorded', 'according', 'follow', 'follows', 'followed', 'following', 'say', 'says', 'said', 'saying', 'tell', 'tells', 'told', 'telling', 'report', 'reports', 'reported', 'reporting', 'suggest', 'suggests', 'suggested', 'suggesting', 'state', 'states', 'stated', 'stating', 'think', 'thinks', 'thought', 'thinking', 'find', 'finds', 'found', 'finding', 'expect', 'expects', 'expected', 'expecting', 'believe', 'believes', 'believed', 'believing', 'know', 'knows', 'knew', 'known', 'knowing', 'consider', 'considers', 'considered', 'considering'] THEN false
            WHEN pos STARTS WITH 'NN' AND lemma IN ['market', 'markets', 'index', 'indexes', 'indices', 'inflation', 'power', 'powers', 'job', 'jobs', 'number', 'numbers', 'system', 'systems', 'value', 'values', 'price', 'prices', 'percent', 'percentage', 'percentages', 'share', 'shares', 'fund', 'funds', 'point', 'points', 'level', 'levels', 'rate', 'rates', 'record', 'records', 'economy', 'economies', 'growth', 'month', 'months', 'year', 'years', 'day', 'days', 'week', 'weeks', 'exchange', 'exchanges'] THEN false
            ELSE true
        END"""

text = text.replace(old_query, new_query)
with open('textgraphx/EventEnrichmentPhase.py', 'w') as f:
    f.write(text)

