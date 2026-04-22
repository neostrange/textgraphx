from textgraphx.neo4j_client import make_graph_from_config
graph = make_graph_from_config()
q = '''
MATCH (em_noun:EventMention {is_timeml_core: true})
MATCH (tok_noun:TagOccurrence) WHERE tok_noun.tok_index_doc = em_noun.start_tok

MATCH (tok_verb:TagOccurrence)-[dep:IS_DEPENDENT]->(tok_noun)
WHERE dep.type IN ['dobj', 'obj', 'pobj']
  AND toLower(tok_verb.lemma) IN ['make', 'take', 'have', 'give', 'do', 'cause', 'hold', 'set', 'get', 'keep', 'put', 'leave', 'find', 'bring']

MATCH (em_verb:EventMention)
WHERE em_verb.start_tok = tok_verb.tok_index_doc

RETURN em_verb.pred, em_verb.tense, em_noun.pred, dep.type, em_noun.doc_id LIMIT 20
'''
print('Light verb pairs:', graph.run(q).data())
