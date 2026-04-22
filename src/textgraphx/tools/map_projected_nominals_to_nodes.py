#!/usr/bin/env python3
"""Map projected nominal mentions (from build_document_from_neo4j) to DB nodes and print requested properties.

Runs build_document_from_neo4j to get the projected nominal spans, then searches the graph
for mention nodes matching those spans and prints `value`, `head`, `nominalSemanticHead`,
`nominalEventiveByWordNet`, and other props.
"""
from __future__ import annotations

import json
from textgraphx.neo4j_client import make_graph_from_config
from textgraphx.evaluation.meantime_evaluator import build_document_from_neo4j, _mention_attrs_map


FIND_NODE_QUERY = """
MATCH (m)
WHERE (m.start_tok = $start AND m.end_tok = $end AND (m.doc_id = $doc_id OR EXISTS {
    MATCH (:AnnotatedText {id: $doc_id})-[:CONTAINS_SENTENCE]->(:Sentence)-[:HAS_TOKEN]->(:TagOccurrence)-[:IN_MENTION]->(m)
}))
RETURN id(m) AS node_id, labels(m) AS labels, properties(m) AS props
LIMIT 5
"""


def main():
    graph = make_graph_from_config()
    try:
        doc = build_document_from_neo4j(graph=graph, doc_id=76437, gold_token_sequence=None,
                                       normalize_nominal_boundaries=True, gold_like_nominal_filter=False,
                                       nominal_profile_mode="all")

        nominals = [m for m in doc.entity_mentions if any(k == 'syntactic_type' and v.upper() in ('NOM','NOMINAL') for k,v in _mention_attrs_map(m).items()) or any(k == 'syntacticType' and v.upper() in ('NOM','NOMINAL') for k,v in _mention_attrs_map(m).items())]

        results = []
        for m in nominals:
            start = int(min(m.span)) if m.span else None
            end = int(max(m.span)) if m.span else None
            rows = graph.run(FIND_NODE_QUERY, {"start": start, "end": end, "doc_id": int(doc.doc_id)}).data()
            if not rows:
                results.append({"span": list(m.span), "attrs": dict(m.attrs), "db_node": None})
                continue
            # prefer nodes labeled NominalMention or EntityMention
            chosen = None
            for r in rows:
                labs = r.get("labels") or []
                if "NominalMention" in labs or "EntityMention" in labs:
                    chosen = r
                    break
            if chosen is None:
                chosen = rows[0]
            props = chosen.get("props") or {}
            results.append({
                "span": list(m.span),
                "attrs": dict(m.attrs),
                "db_node": {
                    "node_id": chosen.get("node_id"),
                    "labels": chosen.get("labels"),
                    "value": props.get("value"),
                    "head": props.get("head"),
                    "token_id": props.get("token_id"),
                    "nominalSemanticHead": props.get("nominalSemanticHead"),
                    "nominalSemanticHeadTokenIndex": props.get("nominalSemanticHeadTokenIndex"),
                    "nominalEventiveByWordNet": props.get("nominalEventiveByWordNet"),
                    "syntactic_type": props.get("syntactic_type") or props.get("syntacticType"),
                },
            })

        print(json.dumps({"doc": doc.doc_id, "predicted_nominals_count": len(nominals), "mapping": results}, indent=2, default=str))
    finally:
        try:
            graph.close()
        except Exception:
            pass


if __name__ == '__main__':
    main()
