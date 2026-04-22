import re

with open("textgraphx/EventEnrichmentPhase.py", "r") as f:
    content = f.read()

method_str_nominal = """
    def normalize_event_boundaries(self, doc_id):
        \"\"\"Expand nominal and verbal event mention boundaries to capture multi-word events.
        
        This aligns pipeline metrics with MEANTIME strict evaluation expectations:
        - Verbal triggers expand rightwards to include particle dependencies (e.g. 'drag' -> 'drag down')
        - Nominal triggers expand leftwards to include compound/amod dependencies (e.g. 'bomb' -> 'car bomb')
        \"\"\"
        logger.debug("normalize_event_boundaries for doc_id=%s", doc_id)
        doc_id = str(doc_id)
        graph = self.graph
        
        # 1. Expand verbal trigger rightwards if it has a 'prt' (particle)
        query_verbal = \"\"\"
        MATCH (em:EventMention {doc_id: toInteger($doc_id)})-[:REFERS_TO]->(te:TEvent)
        MATCH (te)<-[:TRIGGERS]-(trig_tok:TagOccurrence)
        WHERE trig_tok.pos STARTS WITH 'VB'
        MATCH (trig_tok)-[dep:IS_DEPENDENT]->(prt:TagOccurrence)
        WHERE dep.type IN ['prt', 'acomp'] AND prt.tok_index_doc > em.end_tok
        WITH em, trig_tok, max(prt.tok_index_doc) as new_end, max(prt.end_index) as new_end_char, prt
        WHERE new_end <= em.end_tok + 2
        SET em.end_tok = new_end,
            em.end_char = new_end_char,
            em.end = new_end_char,
            em.token_end = new_end,
            em.token_id = 'em_' + toString(em.doc_id) + '_' + toString(em.start_tok) + '_' + toString(new_end),
            em.pred = coalesce(trig_tok.lemma, em.pred) + ' ' + coalesce(prt.text, '')
        \"\"\"
        
        # 2. Expand nominal trigger leftwards if it has contiguous 'compound' or 'amod' modifiers
        query_nominal = \"\"\"
        MATCH (em:EventMention {doc_id: toInteger($doc_id)})-[:REFERS_TO]->(te:TEvent)
        MATCH (te)<-[:TRIGGERS]-(trig_tok:TagOccurrence)
        WHERE trig_tok.pos STARTS WITH 'NN'
        MATCH (trig_tok)-[dep:IS_DEPENDENT]->(mod:TagOccurrence)
        WHERE dep.type IN ['compound', 'amod'] AND mod.tok_index_doc < em.start_tok
        WITH em, min(mod.tok_index_doc) as new_start, min(mod.index) as new_start_char
        WHERE new_start >= em.start_tok - 3
        SET em.start_tok = new_start,
            em.start_char = new_start_char,
            em.begin = new_start_char,
            em.token_start = new_start,
            em.token_id = 'em_' + toString(em.doc_id) + '_' + toString(new_start) + '_' + toString(em.end_tok)
        \"\"\"
        
        # Calculate pred string accurately using the new bounds
        query_nominal_pred = \"\"\"
        MATCH (em:EventMention {doc_id: toInteger($doc_id)})-[:REFERS_TO]->(te:TEvent)
        MATCH (te)<-[:TRIGGERS]-(trig_tok:TagOccurrence)
        WHERE trig_tok.pos STARTS WITH 'NN'
        MATCH (tok:TagOccurrence {doc_id: em.doc_id})
        WHERE tok.tok_index_doc >= em.start_tok AND tok.tok_index_doc <= em.end_tok
        WITH em, tok ORDER BY tok.tok_index_doc
        WITH em, collect(tok.text) as words
        WHERE size(words) > 1
        SET em.pred = reduce(s = head(words), w IN tail(words) | s + ' ' + w)
        \"\"\"
        
        try:
            graph.run(query_verbal, parameters={"doc_id": doc_id})
            graph.run(query_nominal, parameters={"doc_id": doc_id})
            graph.run(query_nominal_pred, parameters={"doc_id": doc_id})
            logger.info("normalize_event_boundaries: updated EventMention bounds for doc_id=%s", doc_id)
        except Exception:
            logger.exception("Failed to normalize event bounds for doc_id=%s", doc_id)
"""

if "def normalize_event_boundaries(" not in content:
    content = content.replace("    def link_frameArgument_to_event(self):", method_str_nominal + "\n    def link_frameArgument_to_event(self):")
    
    # insert self.normalize_event_boundaries(doc_id) inside create_event_mentions before return
    call_str = """        except Exception:
            logger.exception("Failed to create event mentions for doc_id=%s", doc_id)
            return 0

        self.normalize_event_boundaries(doc_id)"""
        
    content = re.sub(
        r'        except Exception:\n            logger.exception\("Failed to create event mentions for doc_id=%s", doc_id\)\n            return 0',
        call_str,
        content
    )

    with open("textgraphx/EventEnrichmentPhase.py", "w") as f:
        f.write(content)
    print("Patched EventEnrichmentPhase.py")
else:
    print("Already patched")
