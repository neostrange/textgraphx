import re

with open('textgraphx/RefinementPhase.py', 'r') as f:
    content = f.read()

# 1. Add the filter_orphan_entities method
method_code = '''
    def filter_orphan_entities(self):
        """Flag isolated pronouns and background nominals as non-core (is_timeml_core=false)."""
        logger.info("filter_orphan_entities: running coreference-gated salience filter")
        query = """
        MATCH (em:EntityMention)
        WHERE em.syntactic_type IN ['pro', 'nom', 'NOMINAL', 'PRONOUN']
        OPTIONAL MATCH (em)-[r:COREFERENT_WITH]-()
        WITH em, count(r) as coref_count
        SET em.is_timeml_core = CASE 
            WHEN coref_count = 0 THEN false
            ELSE true
        END
        """
        self.graph.run(query)
'''

# Find a good place to insert it, maybe before `def detect_correct_NEL_result_for_having_kb_id`
content = content.replace("    def detect_correct_NEL_result_for_having_kb_id", method_code + "\n    def detect_correct_NEL_result_for_having_kb_id")

# 2. Add it to RULE_FAMILIES -> mention_cleanup
new_mention_cleanup = '"mention_cleanup": [\n            "filter_orphan_entities",'
content = re.sub(r'\"mention_cleanup\": \[', new_mention_cleanup, content)

with open('textgraphx/RefinementPhase.py', 'w') as f:
    f.write(content)

