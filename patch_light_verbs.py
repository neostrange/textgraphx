import re

with open('textgraphx/EventEnrichmentPhase.py', 'r') as f:
    content = f.read()

func = """        except Exception:
            pass

    def collapse_light_verbs(self, doc_id):
        '''Collapses LightVerb -> Nominal Event structures to reduce redundancy and fix FPs.
        Transfers tense/aspect from the light verb to the nominal event, and marks
        the light verb as is_timeml_core = false.
        '''
        logger.debug("collapse_light_verbs for doc_id=%s", doc_id)
        
        query = '''
        MATCH (em_noun:EventMention {doc_id: toInteger($doc_id), is_timeml_core: true})
        MATCH (tok_noun:TagOccurrence) WHERE tok_noun.tok_index_doc = em_noun.start_tok
        
        MATCH (tok_verb:TagOccurrence)-[dep:IS_DEPENDENT]->(tok_noun)
        WHERE dep.type IN ['dobj', 'obj', 'pobj']
          AND toLower(tok_verb.lemma) IN ['make', 'take', 'have', 'give', 'do', 'cause', 'hold', 'set', 'get', 'keep', 'put', 'leave', 'find', 'bring']
        
        MATCH (em_verb:EventMention {doc_id: toInteger($doc_id)})
        WHERE em_verb.start_tok = tok_verb.tok_index_doc
        
        SET em_noun.tense = coalesce(em_noun.tense, em_verb.tense),
            em_noun.aspect = coalesce(em_noun.aspect, em_verb.aspect),
            em_verb.is_timeml_core = false
        
        WITH em_noun, em_verb
        OPTIONAL MATCH (em_verb)-[:REFERS_TO]->(te_verb:TEvent)
        SET te_verb.is_timeml_core = false
        
        WITH em_noun, em_verb
        OPTIONAL MATCH (em_noun)-[:REFERS_TO]->(te_noun:TEvent)
        SET te_noun.tense = coalesce(te_noun.tense, em_verb.tense),
            te_noun.aspect = coalesce(te_noun.aspect, em_verb.aspect)
            
        RETURN count(em_noun) as collapsed
        '''
        try:
            res = self.graph.run(query, {"doc_id": doc_id}).data()
            if res:
                logger.info("collapse_light_verbs: collapsed %d pairs for doc_id=%s", res[0]['collapsed'], doc_id)
        except Exception:
            logger.exception("Failed to collapse light verbs for doc_id=%s", doc_id)

    def normalize_event_boundaries"""

content = content.replace("        except Exception:\n            pass\n\n    def normalize_event_boundaries", func)

call_patch = "            self.tag_timeml_core_events(doc_id)\n            self.collapse_light_verbs(doc_id)"
content = content.replace("            self.tag_timeml_core_events(doc_id)", call_patch)

with open('textgraphx/EventEnrichmentPhase.py', 'w') as f:
    f.write(content)
