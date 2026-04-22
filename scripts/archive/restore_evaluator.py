import re
with open("textgraphx/evaluation/meantime_evaluator.py", "r") as f:
    text = f.read()

# I will replace the mangled section with the end of the CALL block.
mangled = """                  coalesce(evt.end_tok, evt_tok_end) AS evt_end,
                  r
              WHERE src_start IS NOT NULL AND src_end IS NOT NULL
                AND evt_start IS NOT NULL AND evt_end IS NOT NULL
              RETURN DISTINCT src_start, src_end, evt_start, evt_end,
                   coalesce(r.type, '') AS sem_role,
                   source_labels
                    })
                             }
            OPTIONAL MATCH (fa)-[:REFERS_TO]->(src)
            OPTIONAL MATCH (mention:NamedEntity)-[:REFERS_TO]->(src)
                  OPTIONAL MATCH (:AnnotatedText {id: doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(fa_tok:TagOccurrence)-[:IN_FRAME]->(fa)
                  OPTIONAL MATCH (fa_tok)-[:IN_MENTION]->(em:EntityMention)
                 WITH f, fa, r, coalesce(mention, src, em) AS endpoint, doc_id
            WHERE endpoint IS NOT NULL
              OPTIONAL MATCH (:AnnotatedText {id: doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(src_tok:TagOccurrence)-[:IN_MENTION]->(endpoint)
                 WITH f, fa, r,
                 min(src_tok.tok_index_doc) AS src_start,
                 max(src_tok.tok_index_doc) AS src_end,
                 labels(endpoint) AS source_labels
            WHERE src_start IS NOT NULL AND src_end IS NOT NULL
              AND f.start_tok IS NOT NULL
              AND f.end_tok IS NOT NULL
                        WITH f.start_tok AS evt_start,
                                 f.end_tok AS evt_end,
                                 coalesce(r.type, fa.type, '') AS sem_role,
                                 src_start,
                                 src_end,
                                 source_labels,
                                 (src_end - src_start) AS span_width
                        ORDER BY evt_start, evt_end, sem_role, span_width ASC, src_start ASC
                        WITH evt_start, evt_end, sem_role,
                                 collect({src_start: src_start, src_end: src_end, source_labels: source_labels}) AS cands
                        WITH evt_start, evt_end, sem_role, head(cands) AS best
                        RETURN DISTINCT best.src_start AS src_start,
                                     best.src_end AS src_end,
                                     evt_start,
                                     evt_end,
                                     sem_role,
                                     best.source_labels AS source_labels
        }
        RETURN DISTINCT src_start, src_end, evt_start, evt_end, sem_role, source_labels
        ORDER BY evt_start, src_start"""

fixed = """                  coalesce(evt.end_tok, evt_tok_end) AS evt_end,
                  r
              WHERE src_start IS NOT NULL AND src_end IS NOT NULL
                AND evt_start IS NOT NULL AND evt_end IS NOT NULL
              RETURN DISTINCT src_start, src_end, evt_start, evt_end,
                   coalesce(r.type, '') AS sem_role,
                   source_labels
        }
        RETURN DISTINCT src_start, src_end, evt_start, evt_end, sem_role, source_labels
        ORDER BY evt_start, src_start"""

if mangled in text:
    text = text.replace(mangled, fixed)
    with open("textgraphx/evaluation/meantime_evaluator.py", "w") as f:
        f.write(text)
    print("Repaired meantime_evaluator.py!")
else:
    print("Could not find mangled string.")
