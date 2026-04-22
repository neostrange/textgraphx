import re

with open('textgraphx/EventEnrichmentPhase.py', 'r') as f:
    content = f.read()

func = """        except Exception:
            logger.exception("Failed to create event mentions for doc_id=%s", doc_id)
            return 0


    def tag_timeml_core_events(self, doc_id):
        \"\"\"Categorize events with 'is_timeml_core' to cleanly segregate true 
        reasoning-layer events (e.g. states, reporting) from MEANTIME 
        high-action evaluation-layer events without destroying graph structure.
        \"\"\"
        logger.debug("tag_timeml_core_events for doc_id=%s", doc_id)
        
        query_events = \"\"\"
        MATCH (em:EventMention {doc_id: toInteger($doc_id)})
        OPTIONAL MATCH (s:Sentence)-[:HAS_TOKEN]->(trig_tok:TagOccurrence)
        WHERE trig_tok.tok_index_doc = em.start_tok AND s.doc_id = toInteger($doc_id)
        WITH em, toLower(coalesce(trig_tok.lemma, em.pred)) AS lemma, trig_tok.pos AS pos
        SET em.is_timeml_core = CASE
            WHEN pos STARTS WITH 'VB' AND lemma IN ['be', 'have', 'do', 'become', 'remain', 'seem', 'look', 'appear', 'continue', 'indicate', 'accord', 'follow', 'say', 'tell', 'report', 'suggest', 'state', 'think', 'find', 'expect', 'believe', 'know', 'consider'] THEN false
            WHEN pos STARTS WITH 'NN' AND lemma IN ['market', 'index', 'inflation', 'power', 'job', 'number', 'system', 'value', 'price', 'percent', 'percentage', 'share', 'fund', 'point', 'level', 'rate', 'record', 'economy', 'growth', 'month', 'year', 'day', 'week'] THEN false
            ELSE true
        END
        RETURN count(em) as tagged_mentions
        \"\"\"
        try:
            result = self.graph.run(query_events, {"doc_id": doc_id}).data()
            tagged = result[0]['tagged_mentions'] if result else 0
            logger.info("tag_timeml_core_events: tagged %d EventMentions for doc_id=%s", tagged, doc_id)
        except Exception:
            logger.exception("Failed to tag TimeML core events for doc_id=%s", doc_id)

        query_tevents = \"\"\"
        MATCH (te:TEvent {doc_id: toInteger($doc_id)})
        OPTIONAL MATCH (em:EventMention)-[:REFERS_TO]->(te)
        WITH te, collect(em.is_timeml_core) as scores
        SET te.is_timeml_core = CASE WHEN size(scores) > 0 THEN any(x IN scores WHERE x = true) ELSE te.is_timeml_core END
        \"\"\"
        try:
            self.graph.run(query_tevents, {"doc_id": doc_id})
        except Exception:
            pass

    def normalize_event_boundaries"""

content = content.replace(
    "        except Exception:\n            logger.exception(\"Failed to create event mentions for doc_id=%s\", doc_id)\n            return 0\n\n\n    def normalize_event_boundaries",
    func
)

with open('textgraphx/EventEnrichmentPhase.py', 'w') as f:
    f.write(content)
